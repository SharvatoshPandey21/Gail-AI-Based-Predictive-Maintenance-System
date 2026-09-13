"""
manual_entry_app.py

WHY THIS FILE EXISTS:
We can't poll GAIL's live SCADA feed in this prototype, so this Streamlit app
acts as the manual data entry interface. An operator selects an asset, enters
the latest sensor readings, and submits them.

Instead of writing directly to the database, this app now sends the readings
to the FastAPI Prediction API (/predict). The API:
1. Performs feature engineering
2. Runs the ML models
3. Saves the reading into the database
4. Returns the prediction results

RUN WITH:
streamlit run manual_entry_app.py

Make sure the FastAPI backend is already running:

uvicorn main:app --reload --port 8000
"""

import requests
import streamlit as st
import sys
from pathlib import Path

# Allow importing db.py
sys.path.append(str(Path(__file__).parent))
from db import init_db, get_asset_list

API_URL = "http://127.0.0.1:8000/predict"

st.set_page_config(
    page_title="GAIL Predictive Maintenance",
    page_icon="🏭",
    layout="centered"
)

init_db()

st.title("🏭 GAIL Predictive Maintenance System")
st.subheader("Manual Sensor Reading Entry")

st.caption(
    "Stand-in for a live SCADA feed. Every submitted reading is sent "
    "to the Prediction API, analyzed by the ML models, and stored in "
    "the historical database."
)

existing_assets = get_asset_list()

with st.form("reading_form", clear_on_submit=True):

    col1, col2 = st.columns(2)

    with col1:

        asset_id = st.selectbox(
            "Asset ID",
            options=existing_assets + ["+ New Asset"]
        )

        if asset_id == "+ New Asset":
            asset_id = st.text_input(
                "Enter New Asset ID",
                placeholder="COMP-06"
            )

        vibration = st.number_input(
            "Vibration (mm/s)",
            min_value=0.0,
            max_value=30.0,
            value=3.0,
            step=0.1
        )

        bearing_temp = st.number_input(
            "Bearing Temperature (°C)",
            min_value=0.0,
            max_value=150.0,
            value=65.0,
            step=0.5
        )

        rpm = st.number_input(
            "RPM",
            min_value=0.0,
            max_value=10000.0,
            value=3000.0,
            step=10.0
        )

    with col2:

        discharge_pressure = st.number_input(
            "Discharge Pressure (bar)",
            min_value=0.0,
            max_value=200.0,
            value=55.0,
            step=0.5
        )

        suction_pressure = st.number_input(
            "Suction Pressure (bar)",
            min_value=0.0,
            max_value=100.0,
            value=18.0,
            step=0.5
        )

        oil_temp = st.number_input(
            "Oil Temperature (°C)",
            min_value=0.0,
            max_value=150.0,
            value=60.0,
            step=0.5
        )

    submitted = st.form_submit_button(
        "Submit Reading",
        use_container_width=True
    )

if submitted:

    if not asset_id:
        st.error("Please enter an Asset ID.")

    else:

        payload = {
            "asset_id": asset_id,
            "vibration_mm_s": vibration,
            "bearing_temp_c": bearing_temp,
            "discharge_pressure_bar": discharge_pressure,
            "suction_pressure_bar": suction_pressure,
            "rpm": rpm,
            "oil_temp_c": oil_temp,
            "save_to_db": True
        }

        try:

            with st.spinner("Running prediction..."):

                response = requests.post(
                    API_URL,
                    json=payload,
                    timeout=15
                )

            if response.status_code == 200:

                result = response.json()

                if result is None or not isinstance(result, dict):
                    st.error("Prediction API returned an empty or invalid response.")
                    st.stop()

                st.success("Prediction completed successfully!")

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Health Score",
                        f"{result['health_score']}%"
                    )

                    st.metric(
                        "Risk Level",
                        result["risk_level"]
                    )

                with col2:
                    st.metric(
                        "Failure Probability",
                        f"{result['failure_probability']*100:.2f}%"
                    )

                    anomaly = "Yes" if result["is_anomaly"] else "No"

                    st.metric(
                        "Anomaly",
                        anomaly
                    )

                st.divider()

                if result["risk_level"] == "LOW":

                    st.success(
                        """
### ✅ Asset Status: HEALTHY

**Recommendation**

- Continue normal operation
- No immediate maintenance required
- Monitor during routine inspection
                        """
                    )

                elif result["risk_level"] == "MEDIUM":

                    st.warning(
                        """
### ⚠ Asset Status: WARNING

**Recommendation**

- Schedule maintenance soon
- Inspect bearings
- Check lubrication system
- Monitor vibration trend
                        """
                    )

                else:

                    st.error(
                        """
### 🚨 Asset Status: HIGH RISK

**Recommendation**

- Immediate maintenance required
- Inspect compressor bearings
- Check lubrication system
- Verify discharge pressure
- Reduce operating load if possible
                        """
                    )

            else:

                try:
                    error = response.json()["detail"]
                except Exception:
                    error = response.text

                st.error(f"Prediction failed:\n\n{error}")

        except requests.exceptions.ConnectionError:

            st.error(
                """
Cannot connect to the Prediction API.

Make sure FastAPI is running.

Command:

uvicorn main:app --reload --port 8000
                """
            )

        except requests.exceptions.Timeout:

            st.error(
                "Prediction request timed out."
            )

        except Exception as e:

            st.exception(e)

st.divider()

st.caption(
    "Production deployment replaces this form with an OPC-UA/Modbus "
    "connection to GAIL's SCADA system. The prediction pipeline and "
    "database remain unchanged."
)