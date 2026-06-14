"""
dashboard/chart_panel.py
Renders the interactive Nino 3.4 index time series using Plotly.
"""

import pandas as pd
import plotly.graph_objects as go


def render_nino34_chart(
    df: pd.DataFrame,
    selected_time: str = None,
) -> go.Figure:
    """
    Renders the Nino 3.4 index chart with ENSO event shading.

    Parameters
    ----------
    df            : DataFrame with columns [nino34_raw, nino34_smooth, enso_phase]
                    indexed by datetime
    selected_time : Optional 'YYYY-MM' string — draws a vertical marker

    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = go.Figure()

    # ── Raw index (thin, muted) ──
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["nino34_raw"],
        mode="lines",
        name="Monthly raw",
        line=dict(color="rgba(150,150,150,0.4)", width=1),
        hovertemplate="%{x|%Y-%m}<br>Raw: %{y:.2f}°C<extra></extra>",
    ))

    # ── Smoothed index (main line) ──
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["nino34_smooth"],
        mode="lines",
        name="3-month smooth",
        line=dict(color="#ffffff", width=2),
        hovertemplate="%{x|%Y-%m}<br>ONI: %{y:.2f}°C<extra></extra>",
    ))

    # ── El Nino shading (smooth > +0.5) ──
    el_nino = df[df["enso_phase"] == "El Nino"]
    fig.add_trace(go.Scatter(
        x=pd.concat([el_nino.index.to_series(),
                     el_nino.index.to_series()[::-1]]),
        y=pd.concat([el_nino["nino34_smooth"],
                     pd.Series([0.5] * len(el_nino),
                                index=el_nino.index)[::-1]]),
        fill="toself",
        fillcolor="rgba(255, 80, 80, 0.25)",
        line=dict(color="rgba(255,255,255,0)"),
        name="El Niño",
        hoverinfo="skip",
    ))

    # ── La Nina shading (smooth < -0.5) ──
    la_nina = df[df["enso_phase"] == "La Nina"]
    fig.add_trace(go.Scatter(
        x=pd.concat([la_nina.index.to_series(),
                     la_nina.index.to_series()[::-1]]),
        y=pd.concat([la_nina["nino34_smooth"],
                     pd.Series([-0.5] * len(la_nina),
                                index=la_nina.index)[::-1]]),
        fill="toself",
        fillcolor="rgba(80, 130, 255, 0.25)",
        line=dict(color="rgba(255,255,255,0)"),
        name="La Niña",
        hoverinfo="skip",
    ))

    # ── Threshold lines ──
    for y_val, label, color in [
        ( 0.5, "El Niño threshold", "rgba(255,100,100,0.6)"),
        (-0.5, "La Niña threshold", "rgba(100,150,255,0.6)"),
        ( 0.0, "Neutral",           "rgba(180,180,180,0.3)"),
    ]:
        fig.add_hline(
            y=y_val,
            line_dash="dash",
            line_color=color,
            line_width=1,
            annotation_text=label if y_val != 0 else "",
            annotation_font_color=color,
            annotation_font_size=9,
        )

    # ── Selected time marker ──
    if selected_time:
        fig.add_vline(
            x=selected_time,
            line_dash="dot",
            line_color="#FFD700",
            line_width=1.5,
            annotation_text="Selected",
            annotation_font_color="#FFD700",
            annotation_font_size=9,
        )

    # ── Notable event annotations ──
    events = {
        "1982-11": "1982–83",
        "1997-11": "1997–98",
        "2015-11": "2015–16",
        "2023-09": "2023–24",
    }
    for date, label in events.items():
        if date in df.index.strftime("%Y-%m").tolist():
            y_pos = float(df.loc[date, "nino34_smooth"].iloc[0]) \
                    if hasattr(df.loc[date, "nino34_smooth"], "iloc") \
                    else float(df.loc[date, "nino34_smooth"])
            fig.add_annotation(
                x=date,
                y=y_pos + 0.2,
                text=label,
                showarrow=False,
                font=dict(size=8, color="#FFD700"),
            )

    # ── Layout ──
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="Niño 3.4 Index (1975–2025)",
            font=dict(size=13, color="#eeeeee"),
        ),
        xaxis=dict(
            title="Year",
            showgrid=True,
            gridcolor="#333333",
            tickfont=dict(size=9),
        ),
        yaxis=dict(
            title="SST Anomaly (°C)",
            showgrid=True,
            gridcolor="#333333",
            zeroline=False,
            range=[-2.5, 3.5],
            tickfont=dict(size=9),
        ),
        legend=dict(
            orientation="h",
            y=-0.18,
            font=dict(size=9),
        ),
        margin=dict(l=50, r=30, t=50, b=60),
        hovermode="x unified",
        height=350,
    )

    return fig
