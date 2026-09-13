"""
views/manual_entry.py

WHY THIS PAGE EXISTS:
This is the restyled version of our original manual entry form -- same
underlying logic (submit a reading, call the API, show the result), now
using the shared theme and showing the rule-engine's specific detected
issues/recommendations instead of generic text.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "data"))
from style import inject_theme, section_header, risk_pill_html, RISK_COLOR, COLORS
from api_client import predict, api_is_reachable
from db import init_db, get_asset_list  # noqa: E402
from style import inject_theme, section_header, risk_pill_html, RISK_COLOR, COLORS


def render():
    inject_theme()
    init_db()
    section_header("Data entry", "Manual sensor reading")

    st.caption(
        "Stand-in for a live SCADA feed. Readings are sent to the prediction "
        "API, checked against both ML models and fixed engineering thresholds, "
        "then stored in history (unless Test mode is on)."
    )

    if not api_is_reachable():
        st.error(
            "Cannot reach the Prediction API. Start it with "
            "`uvicorn main:app --reload --port 8000` from the `api/` folder."
        )
        return

    existing_assets = get_asset_list()

    with st.form("reading_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            asset_id = st.selectbox("Asset ID", options=existing_assets + ["+ New asset"])
            if asset_id == "+ New asset":
                asset_id = st.text_input("New asset ID", placeholder="COMP-06")

            vibration = st.number_input("Vibration (mm/s)", 0.0, 30.0, 3.0, 0.1)
            bearing_temp = st.number_input("Bearing temperature (°C)", 0.0, 150.0, 65.0, 0.5)
            rpm = st.number_input("RPM", 0.0, 10000.0, 3000.0, 10.0)

        with col2:
            discharge_pressure = st.number_input("Discharge pressure (bar)", 0.0, 200.0, 55.0, 0.5)
            suction_pressure = st.number_input("Suction pressure (bar)", 0.0, 100.0, 18.0, 0.5)
            oil_temp = st.number_input("Oil temperature (°C)", 0.0, 150.0, 60.0, 0.5)

        test_mode = st.checkbox(
            "Test mode (don't save this reading to history)",
            help="Use this for trying extreme values -- keeps your asset's real history clean."
        )

        submitted = st.form_submit_button("Submit reading", use_container_width=True)

    if submitted:
        if not asset_id:
            st.error("Please enter an asset ID.")
            return

        payload = {
            "asset_id": asset_id,
            "vibration_mm_s": vibration,
            "bearing_temp_c": bearing_temp,
            "discharge_pressure_bar": discharge_pressure,
            "suction_pressure_bar": suction_pressure,
            "rpm": rpm,
            "oil_temp_c": oil_temp,
            "save_to_db": not test_mode,
        }

        with st.spinner("Running prediction..."):
            result = predict(payload)

        if result is None or "error" in result:
            st.error(f"Prediction failed: {result.get('error') if result else 'unknown error'}")
            return

        if test_mode:
            st.info("Test mode was on — this reading was not saved to history.")

        risk = result["risk_level"]
        color = RISK_COLOR.get(risk, COLORS["muted"])

        st.markdown(
            f"""
            <div class="panel-card" style="border-left: 3px solid {color};">
                <div class="eyebrow">Result for {asset_id}</div>
                <div style="margin-bottom:14px;">
                    {risk_pill_html(risk)}
                </div>
                <div style="display:flex; gap:36px; flex-wrap:wrap;">
                    <div>
                        <div class="eyebrow">Health score</div>
                        <div class="mono-value" style="font-size:1.6rem;">{result['health_score']}%</div>
                    </div>
                    <div>
                        <div class="eyebrow">Failure probability</div>
                        <div class="mono-value" style="font-size:1.6rem;">{result['failure_probability']*100:.2f}%</div>
                    </div>
                    <div>
                        <div class="eyebrow">Anomaly detected</div>
                        <div class="mono-value" style="font-size:1.6rem;">{'Yes' if result['is_anomaly'] else 'No'}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        issues = result.get("detected_issues", [])
        recs = result.get("recommendations", [])

        if issues:
            with st.container():
                st.markdown("**Detected issues** (engineering threshold checks)")
                for issue in issues:
                    st.markdown(f"- {issue}")
        else:
            st.success("No sensor readings breached engineering thresholds.")

        if recs:
            st.markdown("**Recommended actions**")
            for rec in recs:
                st.markdown(f"- {rec}")