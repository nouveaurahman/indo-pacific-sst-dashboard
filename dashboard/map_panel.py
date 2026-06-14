"""
dashboard/map_panel.py
Renders Indo-Pacific SST or SSTA maps using Plotly.
No Cartopy dependency — works on any Python version.
"""

import numpy as np
import plotly.graph_objects as go


VMIN_ANOM, VMAX_ANOM = -3.0, 3.0

# Nino 3.4 box corners (lat/lon for rectangle)
NINO34_LON = [-170, -120, -120, -170, -170]
NINO34_LAT = [-5,   -5,    5,    5,   -5]


def render_map(
    sst_slice,
    title: str,
    mode: str = "anomaly",
    show_nino34: bool = True,
    figsize: tuple = (14, 6),
) -> go.Figure:
    """
    Renders a single SST or SSTA map for the Indo-Pacific region.

    Parameters
    ----------
    sst_slice   : 2D xarray DataArray with dims (lat, lon)
    title       : Map title string
    mode        : 'anomaly' uses RdBu diverging cmap
                  'raw' uses sequential YlOrRd cmap
    show_nino34 : Whether to draw the Nino 3.4 bounding box

    Returns
    -------
    plotly.graph_objects.Figure
    """
    lons = sst_slice.lon.values
    lats = sst_slice.lat.values
    data = sst_slice.values.squeeze()

    # Convert 0-360 longitudes to -180-180
    lons_180 = np.where(lons > 180, lons - 360, lons)
    sort_idx = np.argsort(lons_180)
    lons_180 = lons_180[sort_idx]
    data     = data[:, sort_idx]

    if mode == "anomaly":
        colorscale = "RdBu_r"
        zmin, zmax = VMIN_ANOM, VMAX_ANOM
        colorbar_title = "Anomaly (°C)"
    else:
        colorscale = "YlOrRd"
        zmin = float(np.nanpercentile(data, 2))
        zmax = float(np.nanpercentile(data, 98))
        colorbar_title = "SST (°C)"

    fig = go.Figure()

    # ── SST heatmap layer ──
    fig.add_trace(go.Heatmap(
        z=data,
        x=lons_180,
        y=lats,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(
            title=colorbar_title,
            titlefont=dict(color="#cccccc", size=11),
            tickfont=dict(color="#cccccc", size=9),
            thickness=15,
        ),
        hovertemplate=(
            "Lon: %{x:.1f}°<br>"
            "Lat: %{y:.1f}°<br>"
            "Value: %{z:.2f}°C<extra></extra>"
        ),
    ))

    # ── Nino 3.4 bounding box ──
    if show_nino34:
        fig.add_trace(go.Scatter(
            x=NINO34_LON,
            y=NINO34_LAT,
            mode="lines",
            line=dict(color="#FFD700", width=2, dash="dash"),
            name="Niño 3.4 region",
            hoverinfo="skip",
        ))
        fig.add_annotation(
            x=-145, y=7,
            text="Niño 3.4",
            showarrow=False,
            font=dict(color="#FFD700", size=10),
        )

    # ── Layout ──
    fig.update_layout(
        title=dict(text=title, font=dict(color="#eeeeee", size=13)),
        template="plotly_dark",
        xaxis=dict(
            title="Longitude",
            range=[-180, 110],
            tickfont=dict(size=9),
            showgrid=True,
            gridcolor="#333333",
            dtick=30,
        ),
        yaxis=dict(
            title="Latitude",
            range=[-60, 60],
            tickfont=dict(size=9),
            showgrid=True,
            gridcolor="#333333",
            dtick=20,
            scaleanchor="x",
            scaleratio=1,
        ),
        margin=dict(l=50, r=20, t=50, b=50),
        height=420,
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
    )

    return fig
