"""
src/ingest.py
Opens ERSST v5 .nc files from Azure Blob Storage,
combines into one xarray Dataset, slices to Indo-Pacific.
"""

import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
import xarray as xr
import cftime

load_dotenv()

CONN_STR  = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER = "raw"

LAT_MIN, LAT_MAX = -60,  60
LON_MIN, LON_MAX =  20, 290


def list_nc_blobs(client) -> list:
    cc = client.get_container_client(CONTAINER)
    return sorted([b.name for b in cc.list_blobs() if b.name.endswith(".nc")])


def open_dataset(year_start: int = 1975,
                 year_end:   int = 2025,
                 verbose:    bool = True) -> xr.Dataset:
    assert CONN_STR, "AZURE_STORAGE_CONNECTION_STRING not set in .env"
    client = BlobServiceClient.from_connection_string(CONN_STR)

    all_blobs = list_nc_blobs(client)
    blobs = [
        b for b in all_blobs
        if year_start <= int(b.split(".")[2][:4]) <= year_end
    ]

    if verbose:
        print(f"Found {len(blobs)} .nc files ({year_start}-{year_end})")

    time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)

    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i, blob_name in enumerate(blobs):
            dest = Path(tmp) / blob_name
            blob = client.get_blob_client(container=CONTAINER, blob=blob_name)
            dest.write_bytes(blob.download_blob().readall())
            paths.append(str(dest))
            if verbose and (i + 1) % 60 == 0:
                print(f"  Loaded {i+1}/{len(blobs)} files...")

        if verbose:
            print("Building combined dataset...")

        ds = xr.open_mfdataset(
            sorted(paths),
            combine="nested",
            concat_dim="time",
            engine="netcdf4",
            decode_times=time_coder,
        )[["sst"]]

        # Normalise mixed calendar types to uniform cftime.datetime
        times = [
            cftime.datetime(t.year, t.month, t.day)
            for t in ds.time.values
        ]
        ds = ds.assign_coords(time=("time", times))

        # Drop the lev (depth level) dimension — always 1 for surface data
        if "lev" in ds.dims:
            ds = ds.isel(lev=0, drop=True)

        ds["sst"] = ds["sst"].where(ds["sst"] > -100)

        ds = ds.sel(
            lat=slice(LAT_MIN, LAT_MAX),
            lon=slice(LON_MIN, LON_MAX),
        )

        # Load into memory inside the temp dir context
        # so dask can read the files before they're deleted
        if verbose:
            print("Loading data into memory...")
        ds = ds.load()

        if verbose:
            print(f"\nDataset ready:")
            print(f"  Dimensions : {dict(ds.sizes)}")
            print(f"  Time range : {str(ds.time.values[0])[:10]} "
                  f"-> {str(ds.time.values[-1])[:10]}")
            print(f"  Lat range  : {float(ds.lat.min()):.1f} "
                  f"-> {float(ds.lat.max()):.1f}")
            print(f"  Lon range  : {float(ds.lon.min()):.1f} "
                  f"-> {float(ds.lon.max()):.1f}")

        return ds


if __name__ == "__main__":
    ds = open_dataset()
    print("\nSample SST (Jan 2000, first 3x3 grid):")
    print(ds["sst"].sel(time="2000-01").values[:3, :3])
