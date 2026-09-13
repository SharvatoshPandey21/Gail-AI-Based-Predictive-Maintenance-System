"""
train_model.py

WHY THIS FILE EXISTS:
This is where the actual "AI" in the project happens. We train two models
on engineered_features.csv:

1. Isolation Forest (unsupervised anomaly detector)
   - Learns what "normal" readings look like across all assets
   - Flags readings that deviate significantly, even for failure patterns
     we've never explicitly seen before
   - Doesn't need labeled failures to work

2. Random Forest classifier (supervised)
   - Uses our labeled `failure` column to directly learn "these trend
     patterns precede a failure"
   - More confident and explainable than anomaly detection alone, but
     only as good as the labeled examples it's trained on

We save both trained models as .pkl files so the prediction API (Phase 6)
can load them instantly without retraining every time a new reading comes in.

OUTPUT: models/anomaly_model.pkl, models/failure_classifier.pkl,
        models/feature_columns.pkl (so the API knows what columns to expect)
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

MODELS_DIR = Path(__file__).parent

def load_data():
    df = pd.read_csv(MODELS_DIR / "engineered_features.csv")
    return df

def get_feature_columns(df: pd.DataFrame) -> list:
    """
    We train on the engineered numeric features only -- not on identifiers
    like asset_id/timestamp, categorical fields, or the label itself.
    """
    exclude = {
        "id",
        "asset_id",
        "timestamp",
        "source",
        "failure",
        "severity_tier"
    }
    return [c for c in df.columns if c not in exclude]

def train_anomaly_model(df: pd.DataFrame, feature_cols: list):
    print("\n--- Training Isolation Forest (anomaly detector) ---")
    X = df[feature_cols].fillna(0)

    # contamination = expected proportion of abnormal readings in the data.
    # Our synthetic data has 48 failure-flagged rows out of 21,600 (~0.2%),
    # but we set this a bit higher to also catch "trending toward failure"
    # readings, not just the labeled failure hour itself.
    model = IsolationForest(
        n_estimators=200,
        contamination=0.02,
        random_state=42
    )
    model.fit(X)

    # -1 = anomaly, 1 = normal (sklearn convention) -- flip to 1/0 for clarity
    preds = model.predict(X)
    anomaly_count = (preds == -1).sum()
    print(f"Flagged {anomaly_count} readings as anomalies out of {len(X)}")

    return model

def train_failure_classifier(df: pd.DataFrame, feature_cols: list):
    print("\n--- Training Random Forest (failure classifier) ---")

    # To predict failure BEFORE it happens (not just at the exact failure
    # hour), we widen the label: mark the 72 hours leading up to a failure
    # as "at risk" too. This gives the model a meaningful early-warning
    # window to learn from instead of only the single failure hour.
    df = df.sort_values(["asset_id", "timestamp"]).reset_index(drop=True)
    df["at_risk"] = 0
    for asset_id, group in df.groupby("asset_id"):
        failure_indices = group.index[group["failure"] == 1]
        for idx in failure_indices:
            window_start = max(group.index.min(), idx - 72)
            df.loc[window_start:idx, "at_risk"] = 1

    X = df[feature_cols].fillna(0)
    y = df["at_risk"]

    print(f"Positive (at-risk) samples: {y.sum()} / {len(y)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        class_weight="balanced",  # important: failures are rare, this
                                   # stops the model from just predicting
                                   # "healthy" every time
        random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\nClassification report on held-out test data:")
    print(classification_report(y_test, y_pred, target_names=["healthy", "at_risk"]))
    print(f"ROC-AUC score: {roc_auc_score(y_test, y_proba):.3f}")

    # Feature importance -- useful for your project report to show WHICH
    # sensor trends matter most for prediction
    importances = pd.Series(model.feature_importances_, index=feature_cols)
    print("\nTop 8 most important features:")
    print(importances.sort_values(ascending=False).head(8))

    return model

def main():
    df = load_data()
    feature_cols = get_feature_columns(df)
    print(f"Training on {len(feature_cols)} engineered features, {len(df)} rows")

    anomaly_model = train_anomaly_model(df, feature_cols)
    failure_model = train_failure_classifier(df, feature_cols)

    joblib.dump(anomaly_model, MODELS_DIR / "anomaly_model.pkl")
    joblib.dump(failure_model, MODELS_DIR / "failure_classifier.pkl")
    joblib.dump(feature_cols, MODELS_DIR / "feature_columns.pkl")

    print(f"\nSaved models to {MODELS_DIR}:")
    print("  - anomaly_model.pkl")
    print("  - failure_classifier.pkl")
    print("  - feature_columns.pkl (column order the API must use)")

if __name__ == "__main__":
    main()
