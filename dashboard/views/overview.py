"""
views/overview.py

WHY THIS PAGE EXISTS:
This is the "walk in and see everything at a glance" page -- the page
a maintenance supervisor would actually leave open on a monitor. It
shows every asset's current health as a card with a status light,
sorted so the riskiest assets surface first.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from style import inject_theme, section_header, asset_card_html, hero_ring_html, COLORS
from api_client import get_fleet_status, api_is_reachable


def render():
    inject_theme()
    section_header("Fleet status", "Asset overview")

    if not api_is_reachable():
        st.error(
            "Cannot reach the Prediction API at http://127.0.0.1:8000. "
            "Start it with: `uvicorn main:app --reload --port 8000` "
            "(run from the `api/` folder)."
        )
        return

    with st.spinner("Checking current health for every asset..."):
        fleet_df = get_fleet_status()

    if fleet_df.empty:
        st.info("No assets found yet. Submit a reading on the Manual Entry page first.")
        return

    # Riskiest assets first -- HIGH, then MEDIUM, then LOW
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    fleet_df["_sort"] = fleet_df["risk_level"].map(risk_order)
    fleet_df = fleet_df.sort_values("_sort")

    st.markdown(hero_ring_html(fleet_df["health_score"].mean()), unsafe_allow_html=True)

    high_count = (fleet_df["risk_level"] == "HIGH").sum()
    medium_count = (fleet_df["risk_level"] == "MEDIUM").sum()
    low_count = (fleet_df["risk_level"] == "LOW").sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total assets", len(fleet_df))
    col2.metric("Healthy", int(low_count))
    col3.metric("Needs attention", int(medium_count))
    col4.metric("Critical", int(high_count))

    st.divider()

    cols = st.columns(3)
    for i, row in enumerate(fleet_df.itertuples()):
        with cols[i % 3]:
            st.markdown(
                asset_card_html(
                    asset_id=row.asset_id,
                    risk_level=row.risk_level,
                    health_score=row.health_score,
                    subtitle="anomaly" if row.is_anomaly else "",
                    trend_values=row.trend_values,
                ),
                unsafe_allow_html=True,
            )

    st.caption(
        "Health is recalculated from each asset's most recent stored reading. "
        "Go to Manual Entry to submit a new one, or Trends to see history."
    )