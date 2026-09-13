"""
api_client.py

WHY THIS FILE EXISTS:
Every dashboard page needs to talk to the FastAPI backend or read from
the database. Rather than repeating requests.post(...) and connection
handling in every page, we centralize it here.
"""

import sys
from pathlib import Path
import requests
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent / "data"))
from db import get_all_readings, get_asset_list  # noqa: E402

API_URL = "http://127.0.0.1:8000"


def api_is_reachable() -> bool:
    try:
        requests.get(f"{API_URL}/", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False


def predict(payload: dict) -> dict | None:
    """Calls POST /predict. Returns None (and lets the caller handle it)
    if the API is unreachable or returns an error."""
    try:
        resp = requests.post(f"{API_URL}/predict", json=payload, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": resp.json().get("detail", resp.text)}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_latest_reading(asset_id: str) -> dict | None:
    """Pulls the most recent stored reading for an asset directly from
    the database -- used by the Overview page to re-check current health
    without requiring the user to type anything in."""
    df = get_all_readings(asset_id=asset_id)
    if df.empty:
        return None
    return df.sort_values("timestamp").iloc[-1].to_dict()


def get_fleet_status() -> pd.DataFrame:
    """For every known asset, predicts on its latest stored reading
    (without saving anything new) so the Overview page can show a
    live-ish snapshot of the whole fleet in one table/grid. Also pulls
    each asset's last 24 vibration readings for the sparkline shown on
    its card -- gives a sense of direction, not just a single number."""
    rows = []
    for asset_id in get_asset_list():
        history = get_all_readings(asset_id=asset_id)
        if history.empty:
            continue
        history = history.sort_values("timestamp")
        latest = history.iloc[-1].to_dict()

        result = predict({
            "asset_id": asset_id,
            "vibration_mm_s": latest["vibration_mm_s"],
            "bearing_temp_c": latest["bearing_temp_c"],
            "discharge_pressure_bar": latest["discharge_pressure_bar"],
            "suction_pressure_bar": latest["suction_pressure_bar"],
            "rpm": latest["rpm"],
            "oil_temp_c": latest["oil_temp_c"],
            "save_to_db": False,  # this is a status check, not a new reading
        })
        if result and "error" not in result:
            trend_values = history["vibration_mm_s"].tail(24).tolist()
            rows.append({
                "asset_id": asset_id,
                "health_score": result["health_score"],
                "risk_level": result["risk_level"],
                "is_anomaly": result["is_anomaly"],
                "last_reading_time": latest["timestamp"],
                "trend_values": trend_values,
            })
    return pd.DataFrame(rows)