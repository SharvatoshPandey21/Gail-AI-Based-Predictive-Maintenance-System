"""
views/trends.py

WHY THIS PAGE EXISTS:
Health scores and risk levels answer "is something wrong right now,"
but trends answer "how did we get here." This page charts an asset's
sensor history over time -- the same kind of view we used earlier to
visually confirm our synthetic degradation pattern looked realistic.
"""

import streamlit as st
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "data"))
from style import inject_theme, section_header, COLORS
from db import get_all_readings, get_asset_list  # noqa: E402

SENSORS = {
    "vibration_mm_s": "Vibration (mm/s)",
    "bearing_temp_c": "Bearing temperature (°C)",
    "oil_temp_c": "Oil temperature (°C)",
    "discharge_pressure_bar": "Discharge pressure (bar)",
    "suction_pressure_bar": "Suction pressure (bar)",
    "rpm": "RPM",
}


def render():
    inject_theme()
    section_header("Historical data", "Sensor trends")

    assets = get_asset_list()
    if not assets:
        st.info("No data yet. Submit readings on the Manual Entry page first.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        asset_id = st.selectbox("Asset", options=assets)
    with col2:
        sensor_key = st.selectbox("Sensor", options=list(SENSORS.keys()), format_func=lambda k: SENSORS[k])

    df = get_all_readings(asset_id=asset_id)
    if df.empty:
        st.info(f"No readings found for {asset_id}.")
        return

    df = df.sort_values("timestamp")

    # Guard against assets with very little history (e.g. a newly added
    # asset with only a couple of manual entries) -- without this, the
    # slider's min_value can end up equal to or higher than its
    # max_value, which Streamlit refuses to render.
    if len(df) < 10:
        st.info(
            f"{asset_id} only has {len(df)} reading(s) so far -- not enough "
            "for a meaningful trend chart yet. Submit more readings first."
        )
        return

    slider_max = min(5000, len(df))
    slider_min = min(50, slider_max - 1)  # always strictly less than slider_max
    slider_default = min(500, slider_max)

    if slider_min >= slider_max:
        # Too little data for a meaningful range slider -- just plot everything
        max_points = slider_max
        st.caption(f"Showing all {slider_max} available readings.")
    else:
        max_points = st.slider("Show last N readings", slider_min, slider_max, slider_default)

    plot_df = df.tail(max_points)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df["timestamp"],
        y=plot_df[sensor_key],
        mode="lines",
        line=dict(color=COLORS["accent"], width=2),
        name=SENSORS[sensor_key],
    ))

    # Highlight manually-entered points distinctly from synthetic history
    manual_points = plot_df[plot_df["source"] == "manual"]
    if not manual_points.empty:
        fig.add_trace(go.Scatter(
            x=manual_points["timestamp"],
            y=manual_points[sensor_key],
            mode="markers",
            marker=dict(color=COLORS["danger"], size=8, symbol="diamond"),
            name="Manual entry",
        ))

    fig.update_layout(
        template="plotly_dark",
        height=440,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="IBM Plex Sans", color=COLORS["ink"]),
        xaxis_title="Time",
        yaxis_title=SENSORS[sensor_key],
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Showing {len(plot_df)} of {len(df)} total readings for {asset_id}. "
        "Red diamonds mark manually entered readings; the line covers all sources."
    )