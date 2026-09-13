"""
db.py

WHY THIS FILE EXISTS:
Every part of this system (manual entry form, synthetic data, model training,
dashboard) needs to read/write the SAME set of readings. Instead of each part
touching sensor_readings.csv directly (which gets messy with concurrent
writes), we put one small SQLite database in the middle. SQLite needs no
server setup -- perfect for a prototype -- but the functions here are written
so that swapping in a real database (Postgres) later only means changing
this one file, not the whole app.

TABLE: readings
  asset_id, timestamp, vibration_mm_s, bearing_temp_c,
  discharge_pressure_bar, suction_pressure_bar, rpm, oil_temp_c,
  source ('synthetic' or 'manual'), failure
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "gail_maintenance.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Create the readings table if it doesn't already exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            vibration_mm_s REAL,
            bearing_temp_c REAL,
            discharge_pressure_bar REAL,
            suction_pressure_bar REAL,
            rpm REAL,
            oil_temp_c REAL,
            source TEXT DEFAULT 'manual',
            failure INTEGER DEFAULT 0,
            severity_tier TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"Database ready at {DB_PATH}")

def load_csv_into_db(csv_path: str):
    """One-time import of our synthetic data into the database."""
    df = pd.read_csv(csv_path)
    df["source"] = "synthetic"
    conn = get_connection()
    df.to_sql("readings", conn, if_exists="append", index=False)
    conn.close()
    print(f"Loaded {len(df)} synthetic rows into the database")

def insert_reading(reading: dict):
    """
    Used by the manual entry form to add a single new reading.
    """
    conn = get_connection()

    reading.setdefault("severity_tier", None)

    conn.execute("""
        INSERT INTO readings
        (asset_id, timestamp, vibration_mm_s, bearing_temp_c,
         discharge_pressure_bar, suction_pressure_bar, rpm, oil_temp_c,
         source, failure, severity_tier)
        VALUES (:asset_id, :timestamp, :vibration_mm_s, :bearing_temp_c,
                :discharge_pressure_bar, :suction_pressure_bar, :rpm,
                :oil_temp_c, :source, :failure, :severity_tier)
    """, reading)

    conn.commit()
    conn.close()

def get_all_readings(asset_id: str = None) -> pd.DataFrame:
    """Used by the dashboard and model to pull readings back out."""
    conn = get_connection()
    if asset_id:
        df = pd.read_sql("SELECT * FROM readings WHERE asset_id = ? ORDER BY timestamp", conn, params=(asset_id,))
    else:
        df = pd.read_sql("SELECT * FROM readings ORDER BY timestamp", conn)
    conn.close()
    return df

def get_asset_list() -> list:
    conn = get_connection()
    ids = pd.read_sql("SELECT DISTINCT asset_id FROM readings ORDER BY asset_id", conn)
    conn.close()
    return ids["asset_id"].tolist()

if __name__ == "__main__":
    # Running this file directly sets up the DB and imports our synthetic data.
    init_db()
    load_csv_into_db("../data/sensor_readings.csv")
    print("Assets in DB:", get_asset_list())