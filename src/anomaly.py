"""
src/anomaly.py
Computes SST anomalies (SSTA) against a 1975-2014 climatological
baseline. Also extracts the Nino 3.4 index and saves both outputs
to Azure Blob Storage (container: processed).
"""

import os
import io
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import xarray as xr
import numpy as np
import pandas as pd

load_dotenv()

CONN_STR       = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER      = "processed"
BASELINE_START = "1975"
BASELINE_END   = "2014"

# Nino 3.4 region — 5S-5N, 170W-120W (in 0-360 convention: 190-240)
NINO34_LAT = slice(-5, 5)
NINO34_LON = slice(190, 240)


def compute_anomaly(ds: xr.Dataset,
                    verbose: bool = True) -> xr.Dataset:
    """
    Computes monthly SST anomalies against the 1975-2014 baseline.

    For each grid cell, subtracts the average SST for that calendar
    month (Jan mean, Feb mean... Dec mean) computed over 1975-2014.

    Returns xr.Dataset with variable 'ssta' (same dims as input sst).
    """
    if verbose:
        print(f"Computing climatology ({BASELINE_START}-{BASELINE_END})...")

    # Select baseline period
    baseline = ds["sst"].sel(
        time=slice(BASELINE_START, BASELINE_END)
    )

    # Monthly climatology — mean SST per calendar month per grid cell
    # Result shape: (12, lat, lon)
    climatology = baseline.groupby("time.month").mean("time")

    if verbose:
        print(f"  Climatology shape : {climatology.shape}")
        print(f"  Jan baseline mean : "
              f"{float(climatology.sel(month=1).mean()):.2f} °C")

    # Subtract climatology from full dataset
    if verbose:
        print("Computing anomalies (full 1975-2025)...")

    ssta = ds["sst"].groupby("time.month") - climatology

    # Package as Dataset
    ds_anom = xr.Dataset(
        {"ssta": ssta},
        attrs={
            "description": "SST anomalies vs 1975-2014 climatological baseline",
            "baseline"   : f"{BASELINE_START}-{BASELINE_END}",
            "units"      : "degC",
            "source"     : "NOAA ERSST v5",
        }
    )

    if verbose:
        print(f"  Anomaly shape : {dict(ds_anom['ssta'].sizes)}")
        print(f"  Sample (Jan 1998 equatorial mean): "
              f"{float(ds_anom['ssta'].sel(time='1998-01', lat=slice(-5,5), lon=slice(190,240)).mean()):.2f} °C")

    return ds_anom


def compute_nino34(ds_anom: xr.Dataset,
                   verbose: bool = True) -> pd.DataFrame:
    """
    Extracts the Nino 3.4 index from SSTA.
    Applies cosine-latitude weighting and 3-month rolling mean
    to match NOAA ONI methodology.

    Returns pd.DataFrame with columns: [time, nino34_raw, nino34_smooth]
    """
    if verbose:
        print("\nComputing Nino 3.4 index...")

    # Slice to Nino 3.4 region
    region = ds_anom["ssta"].sel(
        lat=NINO34_LAT,
        lon=NINO34_LON,
    )

    # Cosine latitude weights — corrects for grid cell size shrinking at poles
    weights = np.cos(np.deg2rad(region.lat))
    weights.name = "weights"

    # Weighted spatial mean -> monthly time series
    nino34_raw = region.weighted(weights).mean(dim=["lat", "lon"])
    nino34_raw = nino34_raw.compute()

    # Convert time to pandas datetime for DataFrame
    times = pd.to_datetime([
        f"{t.year}-{t.month:02d}-01"
        for t in nino34_raw.time.values
    ])

    df = pd.DataFrame({
        "time"         : times,
        "nino34_raw"   : nino34_raw.values,
    })
    df = df.set_index("time")

    # 3-month rolling mean (centred) — matches NOAA ONI smoothing
    df["nino34_smooth"] = df["nino34_raw"].rolling(3, center=True).mean()

    # ENSO phase classification
    df["enso_phase"] = "Neutral"
    df.loc[df["nino34_smooth"] >  0.5, "enso_phase"] = "El Nino"
    df.loc[df["nino34_smooth"] < -0.5, "enso_phase"] = "La Nina"

    if verbose:
        el_nino_months = (df["enso_phase"] == "El Nino").sum()
        la_nina_months = (df["enso_phase"] == "La Nina").sum()
        print(f"  El Nino months : {el_nino_months}")
        print(f"  La Nina months : {la_nina_months}")
        print(f"  Peak index     : {df['nino34_smooth'].max():.2f} °C "
              f"({df['nino34_smooth'].idxmax().strftime('%Y-%m')})")
        print(f"  Trough index   : {df['nino34_smooth'].min():.2f} °C "
              f"({df['nino34_smooth'].idxmin().strftime('%Y-%m')})")

    return df


def save_to_blob(ds_anom: xr.Dataset,
                 df_nino: pd.DataFrame,
                 verbose: bool = True):
    """
    Saves SSTA dataset as .zarr and Nino 3.4 index as .parquet
    to Azure Blob Storage (container: processed).
    """
    assert CONN_STR, "AZURE_STORAGE_CONNECTION_STRING not set in .env"
    client = BlobServiceClient.from_connection_string(CONN_STR)

    # ── Save Nino 3.4 index as parquet ──
    if verbose:
        print("\nSaving Nino 3.4 index to blob (processed/nino34_index.parquet)...")

    parquet_buf = io.BytesIO()
    df_nino.to_parquet(parquet_buf)
    parquet_buf.seek(0)
    client.get_blob_client(
        container=CONTAINER, blob="nino34_index.parquet"
    ).upload_blob(parquet_buf, overwrite=True)

    if verbose:
        print("  Saved.")

    # ── Save SSTA as zarr via temp directory ──
    if verbose:
        print("Saving SSTA dataset to blob (processed/ssta.zarr)...")

    with tempfile.TemporaryDirectory() as tmp:
        zarr_path = Path(tmp) / "ssta.zarr"
        ds_anom.to_zarr(str(zarr_path), mode="w")

        # Upload all zarr chunk files
        zarr_files = list(zarr_path.rglob("*"))
        file_count = 0
        for f in zarr_files:
            if f.is_file():
                blob_name = "ssta.zarr/" + f.relative_to(zarr_path).as_posix()
                with open(f, "rb") as fh:
                    client.get_blob_client(
                        container=CONTAINER, blob=blob_name
                    ).upload_blob(fh, overwrite=True)
                file_count += 1

        if verbose:
            print(f"  Uploaded {file_count} zarr chunk files.")

    if verbose:
        print("\nAll outputs saved to processed container.")


if __name__ == "__main__":
    from src.ingest import open_dataset

    # Load full dataset
    ds = open_dataset(verbose=True)

    # Compute anomalies
    ds_anom = compute_anomaly(ds, verbose=True)

    # Compute Nino 3.4 index
    df_nino = compute_nino34(ds_anom, verbose=True)

    # Preview the index around known El Nino events
    print("\nNino 3.4 index around key El Nino events:")
    for date in ["1997-11", "1998-01", "2015-11", "2023-09", "2024-01"]:
        try:
            val = df_nino.loc[date, "nino34_smooth"]
            phase = df_nino.loc[date, "enso_phase"]
            print(f"  {date} : {val:.2f} °C  ({phase})")
        except KeyError:
            pass

    # Save to Azure Blob Storage
    save_to_blob(ds_anom, df_nino, verbose=True)

    print("\nStage 3 complete.")
