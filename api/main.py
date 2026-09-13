"""
main.py (Prediction API)

WHY THIS FILE EXISTS:
This is the bridge between "a new sensor reading exists" and "here's whether
this asset is at risk." It's a separate service (not baked into the
dashboard) so that in production, GAIL's SCADA system, the dashboard, or
any other tool could all call the same prediction endpoint independently.

WHAT IT DOES, STEP BY STEP:
1. On startup, loads the two trained models + the feature column list
   (so we know exactly what columns/order the models expect)
2. Exposes POST /predict -- given an asset_id and a new reading, it:
   a. Pulls that asset's recent history from the database (needed to
      compute rolling/trend features -- a single reading alone can't
      produce a 24-hour rolling average)
   b. Appends the new reading, recomputes engineered features for it
   c. Runs both ML models AND the rule-based threshold engine
   d. Combines both into a single, explainable risk assessment

WHY BOTH ML AND RULES:
Our ML models can only reason within the range of values they were
trained on. A reading far outside that range (e.g. vibration = 18 mm/s
when training data topped out near 9) won't be handled reliably by the
models alone -- this is a well-known limitation of tree-based models,
not a bug. The rules_engine.py module acts as a safety net: fixed
engineering thresholds that catch dangerous readings and explain WHY
they're dangerous, regardless of what the ML models predict.

RUN WITH: uvicorn main:app --reload --port 8000
Then test at: http://localhost:8000/docs (FastAPI's built-in test UI)
"""

import sys
from pathlib import Path
import pandas as pd
import joblib
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import our existing modules from sibling folders
sys.path.append(str(Path(__file__).parent.parent / "data"))
sys.path.append(str(Path(__file__).parent.parent / "models"))
from db import get_all_readings, insert_reading, get_connection
from feature_engineering import engineer_features_for_asset, SENSOR_COLS
from rules_engine import evaluate_thresholds

MODELS_DIR = Path(__file__).parent.parent / "models"

app = FastAPI(title="GAIL Predictive Maintenance API")

# ---- Load trained models once at startup, not per-request ----
# Loading a .pkl file takes time; doing it on every prediction request
# would make the API slow. We load once into memory and reuse.
anomaly_model = joblib.load(MODELS_DIR / "anomaly_model.pkl")
failure_model = joblib.load(MODELS_DIR / "failure_classifier.pkl")
feature_columns = joblib.load(MODELS_DIR / "feature_columns.pkl")

# Minimum history needed before our rolling features are meaningful.
# Matches the SHORT_WINDOW used in feature_engineering.py.
MIN_HISTORY_ROWS = 24


class SensorReading(BaseModel):
    """Defines exactly what a prediction request must contain.
    FastAPI uses this to auto-validate incoming requests -- if a field
    is missing or the wrong type, the API rejects it before our code
    even runs."""
    asset_id: str
    vibration_mm_s: float
    bearing_temp_c: float
    discharge_pressure_bar: float
    suction_pressure_bar: float
    rpm: float
    oil_temp_c: float
    save_to_db: bool = True  # whether to also store this reading permanently


@app.get("/")
def root():
    return {"status": "GAIL Predictive Maintenance API is running"}


@app.get("/assets")
def list_assets():
    """Lets the dashboard show a dropdown of known assets."""
    df = get_all_readings()
    return {"assets": sorted(df["asset_id"].unique().tolist())}


@app.post("/predict")
def predict(reading: SensorReading):
    asset_id = reading.asset_id

    # Step 1: pull this asset's recent history -- we need it to compute
    # rolling/trend features for the new reading
    history = get_all_readings(asset_id=asset_id)

    if len(history) < MIN_HISTORY_ROWS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Not enough history for {asset_id} ({len(history)} rows). "
                f"Need at least {MIN_HISTORY_ROWS} readings before predictions "
                "are meaningful. Submit more readings first."
            )
        )

    # Step 2: append the new reading as the latest row
    new_row = {
        "asset_id": asset_id,
        "timestamp": datetime.now().isoformat(),
        "vibration_mm_s": reading.vibration_mm_s,
        "bearing_temp_c": reading.bearing_temp_c,
        "discharge_pressure_bar": reading.discharge_pressure_bar,
        "suction_pressure_bar": reading.suction_pressure_bar,
        "rpm": reading.rpm,
        "oil_temp_c": reading.oil_temp_c,
        "source": "manual",
        "failure": 0
    }
    combined = pd.concat([history, pd.DataFrame([new_row])], ignore_index=True)

    # Step 3: recompute engineered features -- reuses the exact same
    # function from Phase 4, so features are computed identically to
    # how the model was trained
    engineered = engineer_features_for_asset(combined)
    latest = engineered.iloc[[-1]]  # just the new reading's engineered row

    X = latest[feature_columns].fillna(0)

    # Step 4: run both ML models
    anomaly_raw = anomaly_model.predict(X)[0]       # -1 = anomaly, 1 = normal
    is_anomaly = bool(anomaly_raw == -1)
    anomaly_score = float(anomaly_model.decision_function(X)[0])  # lower = more abnormal

    failure_proba = float(failure_model.predict_proba(X)[0][1])  # probability of "at_risk"

    # Step 5: run the rule-based threshold engine on the RAW reading values
    # (not the engineered features) -- this checks fixed engineering limits
    # independent of anything the ML models learned. See rules_engine.py.
    rule_result = evaluate_thresholds({
        "vibration_mm_s": reading.vibration_mm_s,
        "bearing_temp_c": reading.bearing_temp_c,
        "oil_temp_c": reading.oil_temp_c,
        "discharge_pressure_bar": reading.discharge_pressure_bar,
        "suction_pressure_bar": reading.suction_pressure_bar,
    })

    # Step 6: combine ML + rules into one health score.
    # ML failure probability drives the baseline score; rule-breaches
    # subtract further on top. This means a reading can be flagged as
    # unhealthy either because the MODEL learned a bad pattern, OR
    # because it breaks a hard physical limit the model never saw --
    # whichever is worse wins.
    ml_health = (1 - failure_proba) * 100
    health_score = round(max(0, ml_health - rule_result.sensor_health_penalty), 1)

    # Step 7: risk level -- rules can only ever push risk UP, never down.
    # This is the safety-net principle: ML alone might under-react to an
    # extreme reading, but hard thresholds should never be silently ignored.
    if failure_proba >= 0.7 or rule_result.max_severity == "critical":
        risk_level = "HIGH"
    elif failure_proba >= 0.3 or is_anomaly or rule_result.max_severity == "warning":
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Step 8: optionally persist this reading so it becomes part of
    # future history/training data
    if reading.save_to_db:
        insert_reading(new_row)

    return {
        "asset_id": asset_id,
        "timestamp": new_row["timestamp"],
        "health_score": health_score,
        "risk_level": risk_level,
        "failure_probability": round(failure_proba, 4),
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 4),
        "detected_issues": rule_result.detected_issues,
        "recommendations": rule_result.recommendations,
        "rule_severity": rule_result.max_severity,
        "saved_to_db": reading.save_to_db
    }