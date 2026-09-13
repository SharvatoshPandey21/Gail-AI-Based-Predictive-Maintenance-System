"""
generate_synthetic_data.py (v2 -- tiered severity)

WHY THIS VERSION EXISTS:
Our first version had one fixed degradation shape: every "failing" asset
ramped up to roughly the same peak values (~9 mm/s vibration, ~90C temp).
That taught the classifier a narrow lesson: "values near 9/90 mean
danger" -- but it never saw anything WORSE than that. When we later fed
it a genuinely extreme reading (18 mm/s, 120C) during testing, the model
had no training examples anywhere near that range, so it couldn't judge
it correctly. This is a textbook extrapolation failure for tree-based
models, and it's exactly what we saw happen.

THE FIX: instead of one severity level, every degrading asset is now
randomly assigned one of four severity TIERS -- mild, moderate, severe,
extreme -- each with a different peak magnitude and a different ramp
speed (severe failures develop faster than mild ones, which matches
real mechanical behavior: a small imbalance creeps up slowly, a serious
fault escalates quickly). This means the model actually trains on
examples spanning the full range from "slightly off" to "catastrophic,"
so it learns that failure risk scales smoothly with severity, rather
than treating everything past one fixed threshold as equally unknown.

We also increase the number of assets (15 instead of 5) so there's
enough variety across severity tiers for the model to learn a real
pattern, not just memorize a couple of examples.

OUTPUT: data/sensor_readings.csv
Columns: asset_id, timestamp, vibration_mm_s, bearing_temp_c,
         discharge_pressure_bar, suction_pressure_bar, rpm, oil_temp_c,
         failure, severity_tier (kept for our own inspection/report --
         NOT used as a model input, since real SCADA data would never
         hand us a ready-made severity label)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

# ---- Configuration ----
NUM_ASSETS = 15
DAYS_OF_HISTORY = 180
START_TIME = datetime(2026, 1, 26)

# Roughly 40% of assets will show a degradation trend; the rest stay healthy
DEGRADE_PROBABILITY = 0.4

# ---- Severity tiers ----
# Each tier defines: how high vibration/temp climb, how much pressure
# drops, how many days the ramp takes (severe = faster escalation), and
# how many hours before "failure" get flagged as the failure window.
SEVERITY_TIERS = {
    "mild": {
        "vibration_peak_add": 3.0,   # vibration climbs to ~6 mm/s
        "temp_peak_add": 10,          # bearing temp climbs to ~75C
        "oil_temp_peak_add": 6,
        "pressure_drop": 4,
        "ramp_days": 21,
        "failure_window_hours": 12,
    },
    "moderate": {
        "vibration_peak_add": 6.0,   # ~9 mm/s
        "temp_peak_add": 25,          # ~90C
        "oil_temp_peak_add": 15,
        "pressure_drop": 8,
        "ramp_days": 14,
        "failure_window_hours": 24,
    },
    "severe": {
        "vibration_peak_add": 11.0,  # ~14 mm/s
        "temp_peak_add": 40,          # ~105C
        "oil_temp_peak_add": 28,
        "pressure_drop": 15,
        "ramp_days": 9,
        "failure_window_hours": 36,
    },
    "extreme": {
        "vibration_peak_add": 17.0,  # ~20 mm/s -- covers the range that
        "temp_peak_add": 65,          # ~130C     previously broke the model
        "oil_temp_peak_add": 45,
        "pressure_drop": 20,
        "ramp_days": 5,
        "failure_window_hours": 48,
    },
}


def generate_asset_data(asset_id: int, tier_name):
    """Generate one asset's full time series. tier_name is None for a
    healthy asset, or one of SEVERITY_TIERS' keys for a degrading one."""
    n_hours = DAYS_OF_HISTORY * 24
    timestamps = [START_TIME + timedelta(hours=i) for i in range(n_hours)]

    vibration = np.random.normal(loc=3.0, scale=0.3, size=n_hours)
    bearing_temp = np.random.normal(loc=65, scale=2, size=n_hours)
    discharge_pressure = np.random.normal(loc=55, scale=1.5, size=n_hours)
    suction_pressure = np.random.normal(loc=18, scale=0.8, size=n_hours)
    rpm = np.random.normal(loc=3000, scale=25, size=n_hours)
    oil_temp = np.random.normal(loc=60, scale=1.5, size=n_hours)

    failure_flag = np.zeros(n_hours, dtype=int)

    if tier_name is not None:
        tier = SEVERITY_TIERS[tier_name]
        ramp_len = 24 * tier["ramp_days"]
        ramp_start = n_hours - ramp_len
        # Accelerating degradation curve -- gets steeper near the end,
        # which is how real bearing wear / mechanical faults typically
        # behave (slow onset, rapid final decline).
        ramp = np.linspace(0, 1, ramp_len) ** 2

        vibration[ramp_start:] += ramp * tier["vibration_peak_add"]
        bearing_temp[ramp_start:] += ramp * tier["temp_peak_add"]
        oil_temp[ramp_start:] += ramp * tier["oil_temp_peak_add"]
        discharge_pressure[ramp_start:] -= ramp * tier["pressure_drop"]

        failure_flag[-tier["failure_window_hours"]:] = 1

    df = pd.DataFrame({
        "asset_id": f"COMP-{asset_id:02d}",
        "timestamp": timestamps,
        "vibration_mm_s": vibration.round(3),
        "bearing_temp_c": bearing_temp.round(2),
        "discharge_pressure_bar": discharge_pressure.round(2),
        "suction_pressure_bar": suction_pressure.round(2),
        "rpm": rpm.round(0),
        "oil_temp_c": oil_temp.round(2),
        "failure": failure_flag,
        "severity_tier": tier_name if tier_name else "none",
    })
    return df


def main():
    all_data = []
    tier_names = list(SEVERITY_TIERS.keys())

    # Guarantee at least ONE degrading asset per severity tier. With only
    # 15 assets and pure randomness, it's entirely possible for "severe"
    # and "extreme" to be skipped by chance -- which would defeat the
    # whole point of this rewrite, since those are exactly the examples
    # the model needs to see. We assign tiers to the first few assets
    # explicitly, then randomize the rest.
    assignments = list(tier_names)  # one of each tier, guaranteed
    remaining_slots = NUM_ASSETS - len(assignments)
    for _ in range(remaining_slots):
        if np.random.random() < DEGRADE_PROBABILITY:
            assignments.append(np.random.choice(tier_names))
        else:
            assignments.append(None)  # healthy
    np.random.shuffle(assignments)

    for asset_id, tier_name in zip(range(1, NUM_ASSETS + 1), assignments):
        df = generate_asset_data(asset_id, tier_name)
        all_data.append(df)

        status = f"DEGRADING ({tier_name})" if tier_name else "healthy"
        print(f"Generated COMP-{asset_id:02d}: {status}, {len(df)} readings")

    full_df = pd.concat(all_data, ignore_index=True)
    output_path = "sensor_readings.csv"
    full_df.to_csv(output_path, index=False)

    print(f"\nSaved {len(full_df)} total readings to {output_path}")
    print("\nFailure hours by asset:")
    print(full_df.groupby("asset_id")["failure"].sum())
    print("\nAssets by severity tier:")
    print(full_df.drop_duplicates("asset_id")["severity_tier"].value_counts())

    print("\nPeak values reached per severity tier (sanity check):")
    for tier in tier_names:
        tier_df = full_df[full_df["severity_tier"] == tier]
        if not tier_df.empty:
            print(f"  {tier:10s} -> max vibration: {tier_df['vibration_mm_s'].max():.1f} mm/s, "
                  f"max bearing temp: {tier_df['bearing_temp_c'].max():.1f} C")


if __name__ == "__main__":
    main()
