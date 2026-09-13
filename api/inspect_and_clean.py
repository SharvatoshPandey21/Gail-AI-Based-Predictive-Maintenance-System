"""
inspect_and_clean.py

WHY THIS FILE EXISTS:
If you test the app with deliberately extreme values (like we did to test
the rules engine) and the form saves them to the database, those extreme
readings become part of that asset's real history. Since our rolling/trend
features are calculated FROM recent history, a contaminated history can
make even normal future readings look anomalous -- not because anything
is actually wrong, but because the "recent baseline" the model compares
against is skewed by test data.

This script lets you:
1. See an asset's most recent readings (to spot test/junk entries)
2. Delete specific rows by their database id
3. Delete ALL manual entries for an asset in one go (useful if you've
   been testing a lot and just want a clean slate)

RUN WITH: python inspect_and_clean.py
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "data"))
from db import get_connection, get_all_readings

def show_recent(asset_id: str, n: int = 15):
    df = get_all_readings(asset_id=asset_id)
    print(f"\nLast {n} readings for {asset_id}:")
    cols = ["id", "timestamp", "vibration_mm_s", "bearing_temp_c",
            "oil_temp_c", "discharge_pressure_bar", "source"]
    print(df[cols].tail(n).to_string(index=False))

def delete_by_id(row_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM readings WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
    print(f"Deleted row id={row_id}")

def delete_all_manual_for_asset(asset_id: str):
    """Removes every 'manual' source row for an asset -- keeps synthetic
    history intact, only clears out test entries you typed in yourself."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM readings WHERE asset_id = ? AND source = 'manual'",
        (asset_id,)
    )
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    print(f"Deleted {deleted} manual readings for {asset_id}")

if __name__ == "__main__":
    ASSET_TO_CHECK = "COMP-01"

    show_recent(ASSET_TO_CHECK, n=15)

    print("\nOptions:")
    print("  1. Delete a specific row by id -- edit this script, call delete_by_id(<id>)")
    print("  2. Delete ALL manual test entries for this asset -- uncomment the line below")
    print()

    # Uncomment the next line to actually clean out manual test entries:
    # delete_all_manual_for_asset(ASSET_TO_CHECK)

    print("Nothing deleted yet -- uncomment the line above and re-run to clean up.")
