"""
dashboard/map_panel.py
Renders Indo-Pacific SST or SSTA maps using Cartopy + Matplotlib.
Returns a Matplotlib Figure for use with st.pyplot().
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for Streamlit
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature


# Nino 3.4 box for overlay (in -180 to 180 convention)
NINO34_LON = (-170, -120)
NINO34_LAT = (-5, 5)

# Colour map settings
CMAP_ANOM = "RdBu_r"
CMAP_RAW  = "thermal" if False else "plasma"
VMIN_ANOM, VMAX_ANOM = -3.0, 3.0


def render_map(
    sst_slice,          # 2D xarray DataArray (lat, lon)
    title: str,
    mode: str = "anomaly",   # "anomaly" or "raw"
    show_nino34: bool = True,
    figsize: tuple = (14, 6),
) -> plt.Figure:
    """
    Renders a single SST or SSTA map for the Indo-Pacific region.

    Parameters
    ----------
    sst_slice   : 2D xarray DataArray with dims (lat, lon)
    title       : Map title string
    mode        : 'anomaly' uses RdBu_r diverging cmap ±3°C
                  'raw' uses sequential plasma cmap
    show_nino34 : Whether to draw the Nino 3.4 bounding box
    figsize     : Matplotlib figure size in inches

    Returns
    -------
    matplotlib.figure.Figure
    """
    lons = sst_slice.lon.values
    lats = sst_slice.lat.values
    data = sst_slice.values.squeeze()

    # Convert longitudes from 0-360 to -180-180 for Cartopy
    lons_180 = np.where(lons > 180, lons - 360, lons)

    # Sort by converted longitudes
    sort_idx = np.argsort(lons_180)
    lons_180 = lons_180[sort_idx]
    data = data[:, sort_idx]

    # ── Figure and projection ──
    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(
        1, 1,
        figsize=figsize,
        subplot_kw={"projection": proj},
        facecolor="#0e1117",  # dark background matches Streamlit dark theme
    )
    ax.set_facecolor("#0e1117")

    # ── Colour map and normalisation ──
    if mode == "anomaly":
        cmap = CMAP_ANOM
        vmin, vmax = VMIN_ANOM, VMAX_ANOM
        cbar_label = "SST Anomaly (°C)"
    else:
        cmap = "YlOrRd"
        vmin = float(np.nanpercentile(data, 2))
        vmax = float(np.nanpercentile(data, 98))
        cbar_label = "SST (°C)"

    # ── Plot SST data ──
    im = ax.pcolormesh(
        lons_180, lats, data,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        transform=proj,
        shading="auto",
    )

    # ── Map features ──
    ax.add_feature(cfeature.LAND,
                   facecolor="#2a2a2a",
                   edgecolor="#555555",
                   linewidth=0.5,
                   zorder=3)
    ax.add_feature(cfeature.COASTLINE,
                   edgecolor="#888888",
                   linewidth=0.6,
                   zorder=4)
    ax.add_feature(cfeature.BORDERS,
                   edgecolor="#444444",
                   linewidth=0.3,
                   zorder=4)

    # ── Gridlines ──
    gl = ax.gridlines(
        crs=proj,
        draw_labels=True,
        linewidth=0.4,
        color="#444444",
        alpha=0.8,
        linestyle="--",
    )
    gl.top_labels    = False
    gl.right_labels  = False
    gl.xlabel_style  = {"size": 8, "color": "#aaaaaa"}
    gl.ylabel_style  = {"size": 8, "color": "#aaaaaa"}
    gl.xlocator = mticker.FixedLocator(range(-180, 181, 30))
    gl.ylocator = mticker.FixedLocator(range(-60, 61, 20))

    # ── Nino 3.4 bounding box ──
    if show_nino34:
        from matplotlib.patches import Rectangle
        nino_rect = Rectangle(
            (NINO34_LON[0], NINO34_LAT[0]),
            NINO34_LON[1] - NINO34_LON[0],
            NINO34_LAT[1] - NINO34_LAT[0],
            linewidth=1.5,
            edgecolor="#FFD700",
            facecolor="none",
            linestyle="--",
            transform=proj,
            zorder=5,
        )
        ax.add_patch(nino_rect)
        ax.text(
            NINO34_LON[0] + 1,
            NINO34_LAT[1] + 1.5,
            "Niño 3.4",
            transform=proj,
            fontsize=8,
            color="#FFD700",
            zorder=6,
        )

    # ── Set extent to Indo-Pacific ──
    ax.set_extent([-180, 110, -60, 60], crs=proj)

    # ── Colorbar ──
    cbar = fig.colorbar(
        im, ax=ax,
        orientation="vertical",
        pad=0.02,
        fraction=0.025,
        extend="both",
    )
    cbar.set_label(cbar_label, color="#cccccc", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="#cccccc", labelsize=8)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#cccccc")

    # ── Title ──
    ax.set_title(title, color="#eeeeee", fontsize=12, pad=10)

    fig.tight_layout()
    return fig
