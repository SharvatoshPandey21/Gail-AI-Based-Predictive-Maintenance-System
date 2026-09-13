"""
feature_engineering.py

WHY THIS FILE EXISTS:
Raw sensor readings (vibration=4.2, temp=68) don't tell a model much on
their own -- a single value could be normal noise or the start of a failure
trend. What actually signals "this asset is degrading" is the SHAPE of
recent readings: is vibration climbing over the last day? Is temperature
rising faster than it used to?

This script reads every reading per asset (in time order), and for each
row computes rolling-window and rate-of-change features. The output is
what we'll actually train the model on in Phase 5 -- not the raw readings.

OUTPUT: models/engineered_features.csv
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).parent.parent / "data"))
from db import get_all_readings

# Sensor columns we'll build rolling/trend features from
SENSOR_COLS = [
    "vibration_mm_s", "bearing_temp_c", "discharge_pressure_bar",
    "suction_pressure_bar", "rpm", "oil_temp_c"
]

# Window sizes in NUMBER OF READINGS (our synthetic data is hourly,
# so 24 = 1 day, 72 = 3 days). If your real data has a different
# frequency, adjust these.
SHORT_WINDOW = 24
LONG_WINDOW = 72

def engineer_features_for_asset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes one asset's readings (already sorted by time) and adds
    rolling mean, rolling std, and rate-of-change columns.
    """
    df = df.sort_values("timestamp").reset_index(drop=True)

    for col in SENSOR_COLS:
        # Rolling mean: smooths out noise, shows the recent "typical" level
        df[f"{col}_roll_mean_{SHORT_WINDOW}h"] = (
            df[col].rolling(window=SHORT_WINDOW, min_periods=1).mean()
        )
        # Rolling std: how noisy/unstable readings have been recently
        df[f"{col}_roll_std_{SHORT_WINDOW}h"] = (
            df[col].rolling(window=SHORT_WINDOW, min_periods=1).std().fillna(0)
        )
        # Rate of change: difference between current short-term average
        # and long-term average -- positive means the value is climbing
        long_mean = df[col].rolling(window=LONG_WINDOW, min_periods=1).mean()
        df[f"{col}_trend"] = df[f"{col}_roll_mean_{SHORT_WINDOW}h"] - long_mean

        # Deviation from this asset's own overall baseline (its first
        # week of readings) -- a simple stand-in for "normal operating range"
        baseline = df[col].iloc[:SHORT_WINDOW].mean()
        df[f"{col}_dev_from_baseline"] = df[col] - baseline

    return df

def main():
    print("Loading readings from database...")
    raw = get_all_readings()
    print(f"Loaded {len(raw)} readings across {raw['asset_id'].nunique()} assets")

    engineered_parts = []
    for asset_id, group in raw.groupby("asset_id"):
        print(f"Engineering features for {asset_id} ({len(group)} rows)...")
        engineered_parts.append(engineer_features_for_asset(group))

    engineered = pd.concat(engineered_parts, ignore_index=True)

    output_path = Path(__file__).parent / "engineered_features.csv"
    engineered.to_csv(output_path, index=False)
    print(f"\nSaved engineered feature set: {output_path}")
    print(f"Shape: {engineered.shape[0]} rows x {engineered.shape[1]} columns")
    print(f"New feature columns added: {engineered.shape[1] - raw.shape[1]}")

if __name__ == "__main__":
    main()