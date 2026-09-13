"""
views/history.py

WHY THIS PAGE EXISTS:
A raw table of every reading ever taken, with any engineering threshold
breaches flagged inline. This is the page you'd use to answer "when did
this start" or to audit what's been recorded -- useful for your project
report as a way to demonstrate that data really is being captured over
time, not just used in one-off demos.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "data"))
sys.path.append(str(Path(__file__).parent.parent.parent / "api"))
from style import inject_theme, section_header
from db import get_all_readings, get_asset_list  # noqa: E402
from rules_engine import evaluate_thresholds  # noqa: E402


def render():
    inject_theme()
    section_header("Audit log", "Reading history")

    assets = get_asset_list()
    if not assets:
        st.info("No data yet. Submit readings on the Manual Entry page first.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        asset_filter = st.selectbox("Asset", options=["All assets"] + assets)
    with col2:
        show_only_flagged = st.checkbox("Show only flagged readings", value=False)

    df = get_all_readings(asset_id=None if asset_filter == "All assets" else asset_filter)
    df = df.sort_values("timestamp", ascending=False)

    if df.empty:
        st.info(f"No readings found for {asset_filter}.")
        return

    slider_max = min(2000, len(df))
    slider_min = min(20, slider_max - 1)
    slider_default = min(200, slider_max)

    if slider_min >= slider_max:
        n_rows = slider_max
        st.caption(f"Showing all {slider_max} available readings.")
    else:
        n_rows = st.slider("Rows to check", slider_min, slider_max, slider_default)

    view_df = df.head(n_rows).copy()

    # Rule checks are cheap (no ML), so we can run them per-row for the
    # table view without needing the API. This gives every historical
    # row a "flagged" status even if it was recorded before the rules
    # engine existed.
    severities = []
    for _, row in view_df.iterrows():
        result = evaluate_thresholds({
            "vibration_mm_s": row["vibration_mm_s"],
            "bearing_temp_c": row["bearing_temp_c"],
            "oil_temp_c": row["oil_temp_c"],
            "discharge_pressure_bar": row["discharge_pressure_bar"],
            "suction_pressure_bar": row["suction_pressure_bar"],
        })
        severities.append(result.max_severity)
    view_df["flag"] = severities

    if show_only_flagged:
        view_df = view_df[view_df["flag"] != "normal"]

    display_cols = [
        "asset_id", "timestamp", "vibration_mm_s", "bearing_temp_c",
        "oil_temp_c", "discharge_pressure_bar", "suction_pressure_bar",
        "rpm", "source", "flag"
    ]

    st.dataframe(
        view_df[display_cols],
        use_container_width=True,
        height=520,
        column_config={
            "flag": st.column_config.TextColumn("Threshold flag"),
            "source": st.column_config.TextColumn("Source"),
        },
    )

    st.caption(
        f"Showing {len(view_df)} of {len(df)} readings"
        f"{' for ' + asset_filter if asset_filter != 'All assets' else ''}. "
        "Flag is computed from fixed engineering thresholds, independent of the ML models."
    )