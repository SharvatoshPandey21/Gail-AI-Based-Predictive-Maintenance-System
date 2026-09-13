"""
reset_project.py

WHY THIS FILE EXISTS:
Runs a full, clean reset of the project's data + models in one go:
  1. Deletes the old database (wipes ALL history -- synthetic + manual)
  2. Regenerates fresh synthetic data (tiered severity version)
  3. Rebuilds the database from that fresh data
  4. Re-runs feature engineering
  5. Retrains both ML models

Use this whenever you want a clean slate -- e.g. after test entries have
contaminated an asset's history, or after updating the data generator.

RUN FROM THE PROJECT ROOT (the folder containing data/, models/, api/):
    python reset_project.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable  # uses whichever python/venv is currently active

def run_step(description: str, cwd: Path, args: list):
    print(f"\n{'='*60}\n{description}\n{'='*60}")
    result = subprocess.run([PYTHON] + args, cwd=cwd)
    if result.returncode != 0:
        print(f"\nSTOPPED: '{description}' failed. Fix the error above and re-run.")
        sys.exit(1)

def main():
    data_dir = ROOT / "data"
    models_dir = ROOT / "models"

    db_path = data_dir / "gail_maintenance.db"
    if db_path.exists():
        db_path.unlink()
        print(f"Deleted old database: {db_path}")
    else:
        print("No existing database found -- starting fresh anyway.")

    run_step(
        "Step 1/4: Generating fresh synthetic sensor data",
        cwd=data_dir,
        args=["generate_synthetic_data.py"]
    )
    run_step(
        "Step 2/4: Rebuilding the database",
        cwd=data_dir,
        args=["db.py"]
    )
    run_step(
        "Step 3/4: Running feature engineering",
        cwd=models_dir,
        args=["feature_engineering.py"]
    )
    run_step(
        "Step 4/4: Retraining the ML models",
        cwd=models_dir,
        args=["train_model.py"]
    )

    print("\n" + "="*60)
    print("RESET COMPLETE. Database, features, and models are all fresh.")
    print("Restart your API (uvicorn) and dashboard (streamlit) to pick up the changes.")
    print("="*60)

if __name__ == "__main__":
    main()
