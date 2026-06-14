"""
dashboard/app.py
Main Streamlit dashboard for Indo-Pacific SST mapping.
Reads precomputed outputs from Azure Blob Storage.
Loads full zarr store once at startup — slider changes are instant.
"""

import os
import io
import calendar
import tempfile
from pathlib import Path
from dotenv import load_dotenv

import numpy as np
import pandas as pd
import xarray as xr
import streamlit as st
from azure.storage.blob import BlobServiceClient

from map_panel import render_map
from chart_panel import render_nino34_chart

load_dotenv()

CONN_STR  = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER = "processed"

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Indo-Pacific SST Explorer",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric label { font-size: 11px !important; color: #aaaaaa !important; }
</style>
""", unsafe_allow_html=True)


# ── Cached data loaders ──────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to Azure Blob Storage...")
def get_blob_client():
    return BlobServiceClient.from_connection_string(CONN_STR)


@st.cache_data(show_spinner="Loading Niño 3.4 index...")
def load_nino34() -> pd.DataFrame:
    client = get_blob_client()
    buf = io.BytesIO()
    buf.write(
        client.get_blob_client(
            container=CONTAINER, blob="nino34_index.parquet"
        ).download_blob().readall()
    )
    buf.seek(0)
    df = pd.read_parquet(buf)
    df.index = pd.to_datetime(df.index)
    return df


@st.cache_data(show_spinner="Loading SST anomaly data — first load only, please wait...")
def load_full_ssta() -> dict:
    """
    Downloads entire zarr store from blob once at startup.
    Returns a plain dict of numpy arrays keyed by (year, month)
    so Streamlit can cache it cleanly without xarray pickling issues.
    """
    client = get_blob_client()
    container_client = client.get_container_client(CONTAINER)

    with tempfile.TemporaryDirectory() as tmp:
        zarr_path = Path(tmp) / "ssta.zarr"
        blobs = [
            b.name for b in container_client.list_blobs()
            if b.name.startswith("ssta.zarr/")
        ]

        for blob_name in blobs:
            rel  = blob_name.replace("ssta.zarr/", "")
            dest = zarr_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            client.get_blob_client(
                container=CONTAINER, blob=blob_name
            ).download_blob().readinto(
                open(dest, "wb")
            )

        ds = xr.open_zarr(str(zarr_path)).load()

        # Extract coordinate arrays
        lats = ds.lat.values
        lons = ds.lon.values

        # Build dict keyed by (year, month) for instant lookup
        ssta_dict = {}
        for t in ds.time.values:
            key = (t.year, t.month)
            ssta_dict[key] = ds["ssta"].sel(time=t).values

        return {
            "ssta"  : ssta_dict,
            "lats"  : lats,
            "lons"  : lons,
        }


@st.cache_data(show_spinner=False)
def cached_map(year: int, month: int,
               mode: str, show_box: bool,
               _lats, _lons) -> object:
    """Renders Cartopy map — cached per (year, month, mode)."""
    data   = load_full_ssta()
    arr    = data["ssta"].get((year, month))
    if arr is None:
        return None

    # Wrap as a lightweight object render_map can use
    import xarray as xr
    da = xr.DataArray(
        arr,
        dims=["lat", "lon"],
        coords={"lat": _lats, "lon": _lons}
    )
    title = (
        f"SST Anomaly — {calendar.month_name[month]} {year}"
        if mode == "anomaly"
        else f"Raw SST — {calendar.month_name[month]} {year}"
    )
    return render_map(da, title=title,
                      mode=mode, show_nino34=show_box)


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌊 SST Explorer")
    st.caption("Indo-Pacific · 1975–2025")
    st.divider()

    year  = st.slider("Year",  1975, 2025, 2023, step=1)
    month = st.slider("Month", 1,    12,   9,    step=1)
    st.caption(f"Selected: **{calendar.month_name[month]} {year}**")

    st.divider()
    mode = st.radio(
        "Display mode",
        ["Anomaly (SSTA)", "Raw SST"],
        index=0,
    )
    show_nino34_box = st.checkbox("Show Niño 3.4 box", value=True)

    st.divider()
    st.markdown("""
    **Data source**
    NOAA ERSST v5 · Monthly · 2°×2°
    Anomaly baseline: 1975–2014

    **Built with**
    Python · xarray · Cartopy · Streamlit
    """)


# ── Main content ─────────────────────────────────────────────────
st.title("🌊 Indo-Pacific Sea Surface Temperature Explorer")
st.caption(
    "51 years of ocean surface temperature data across the "
    "Indo-Pacific. Anomalies vs 1975–2014 climatological baseline. "
    "El Niño forecast context: 2026 🔴"
)

# Load data (cached after first run)
df_nino    = load_nino34()
data_store = load_full_ssta()
lats       = data_store["lats"]
lons       = data_store["lons"]
display_mode = "anomaly" if "Anomaly" in mode else "raw"

# ── Map ──────────────────────────────────────────────────────────
fig_map = cached_map(
    year, month, display_mode,
    show_nino34_box, lats, lons
)

if fig_map is not None:
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.warning(f"No data for {calendar.month_name[month]} {year}.")

# ── Chart + Stats ────────────────────────────────────────────────
col_chart, col_stats = st.columns([3, 1])

with col_chart:
    selected_str = f"{year}-{month:02d}-01"
    fig_chart = render_nino34_chart(df_nino, selected_time=selected_str)
    st.plotly_chart(fig_chart, use_container_width=True)

with col_stats:
    st.subheader("📊 Stats")

    arr = data_store["ssta"].get((year, month))
    if arr is not None:
        st.metric("Mean anomaly", f"{np.nanmean(arr):+.2f} °C")
        st.metric("Max anomaly",  f"{np.nanmax(arr):+.2f} °C")
        st.metric("Min anomaly",  f"{np.nanmin(arr):+.2f} °C")

    st.divider()

    sel_date = pd.Timestamp(f"{year}-{month:02d}-01")
    if sel_date in df_nino.index:
        row      = df_nino.loc[sel_date]
        nino_val = float(row["nino34_smooth"].iloc[0]) \
                   if hasattr(row["nino34_smooth"], "iloc") \
                   else float(row["nino34_smooth"])
        phase    = str(row["enso_phase"].iloc[0]) \
                   if hasattr(row["enso_phase"], "iloc") \
                   else str(row["enso_phase"])
        icon = {"El Nino": "🔴", "La Nina": "🔵",
                "Neutral": "⚪"}.get(phase, "⚪")

        st.metric("Niño 3.4",    f"{nino_val:+.2f} °C")
        st.metric("ENSO phase",  f"{icon} {phase}")

    st.divider()
    st.caption("**Notable El Niño events**")
    st.caption("1982–83 · 1997–98")
    st.caption("2015–16 · 2023–24")
    st.caption("**2026 forecast 🔴**")

# ── Footer ────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Data: NOAA ERSST v5 · "
    "Analysis: Python / xarray / Cartopy · "
    "Tyler, 2026"
)
