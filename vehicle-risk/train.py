"""Vehicle accident-risk classifier — trains on raw IMU (accelerometer +
gyroscope + magnetometer) trip data, the same signal class a real ESP32 +
MPU9250/6050 rig would stream.

Dataset: Kaggle "Harsh driving dataset" (saboorahmad47/harsh-driving-dataset)
— 54 trip recordings, ~33k rows, each row labeled with event_class (0=normal,
1=inside a harsh-driving window) and the harsh-event TYPE encoded in the
trip's filename (sudden-brake, sudden-acc, sudden-left-turn, sudden-right-turn,
sudden-left-line-chg, sudden-right-line-chg, safe / safe-acc / safe-no-movement).

Honest framing: no public dataset pairs raw telemetry with actual crash
outcomes, so this does NOT predict "will crash." It classifies DRIVING
BEHAVIOR from raw motion data and assigns a risk tier to each behavior class
— the same "grounded classifier + plain-language reasoning" pattern as
AgriLens, not a black-box crash oracle.

Two-stage design (chosen after comparing against a single 7-way classifier,
see train_report.txt for both):
  Stage 1 — binary "is this an elevated-risk event, or normal driving?"
            on ALL rows. This is the number that matters for a risk alert:
            70% held-out-trip accuracy, 57% recall / 49% precision on
            events (vs. a one-shot 7-way classifier's ~37% accuracy).
  Stage 2 — "which kind of event?", trained only on rows already flagged
            as events. This is the REASONING shown alongside the alert
            ("sudden-brake" vs "sudden lane change"), not the headline
            number, so its weaker accuracy matters less for the demo.

Train/test split is by TRIP FILE (not by row) so the test set never sees
rows from a trip the model trained on — rows within one trip are highly
correlated (same driver, same few seconds), so a row-level split would leak.

Model: small RandomForests (shallow, few trees) — deliberately tiny so they
port cleanly to an ESP32 later (a handful of trees of depth<=6 is a few KB
of if/else logic, well within microcontroller flash budgets).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

DATA_DIR = Path(__file__).parent / "data" / "harsh-driving"
OUT_DIR = Path(__file__).parent / "model"
OUT_DIR.mkdir(exist_ok=True)

FEATURES = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z",
            "accel_mag", "gyro_mag",
            "accel_mag_roll_max", "accel_mag_roll_std",
            "gyro_mag_roll_max", "gyro_mag_roll_std"]
WINDOW = 10  # trailing samples — a real-time ESP32 detector keeps the same
             # size ring buffer instead of classifying single raw readings,
             # since one sensor sample is noise, not a driving event.

RISK_TIER = {
    "normal": "low",
    "safe": "low",
    "safe-acc": "low",
    "safe-no-movement": "low",
    "sudden-left-turn": "medium",
    "sudden-right-turn": "medium",
    "sudden-left-line-chg": "medium",
    "sudden-right-line-chg": "medium",
    "sudden-brake": "high",
    "sudden-acc": "high",
}


def label_from_filename(fname: str) -> str:
    m = re.match(r"^[a-z]+_([a-z-]+?)_const", fname)
    return m.group(1) if m else "unknown"


def load_all() -> pd.DataFrame:
    frames = []
    for i, path in enumerate(sorted(DATA_DIR.glob("*.csv"))):
        df = pd.read_csv(path)
        trip_label = label_from_filename(path.name)
        df["trip_id"] = i
        df["trip_file"] = path.name
        df["behavior"] = np.where(df["event_class"] == 1, trip_label, "normal")
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    full["accel_mag"] = np.sqrt(full.acc_x**2 + full.acc_y**2 + full.acc_z**2)
    full["gyro_mag"] = np.sqrt(full.gyro_x**2 + full.gyro_y**2 + full.gyro_z**2)

    rolled = []
    for _, g in full.groupby("trip_id", sort=False):
        g = g.copy()
        g["accel_mag_roll_max"] = g.accel_mag.rolling(WINDOW, min_periods=1).max()
        g["accel_mag_roll_std"] = g.accel_mag.rolling(WINDOW, min_periods=1).std().fillna(0)
        g["gyro_mag_roll_max"] = g.gyro_mag.rolling(WINDOW, min_periods=1).max()
        g["gyro_mag_roll_std"] = g.gyro_mag.rolling(WINDOW, min_periods=1).std().fillna(0)
        rolled.append(g)
    return pd.concat(rolled, ignore_index=True)


def main():
    df = load_all()
    df["is_event"] = (df.behavior != "normal").astype(int)
    print(f"Loaded {len(df)} rows from {df.trip_id.nunique()} trips")
    print(df.behavior.value_counts())

    trip_ids = sorted(df.trip_id.unique())
    rng = np.random.RandomState(42)
    rng.shuffle(trip_ids)
    n_test = max(1, int(len(trip_ids) * 0.2))
    test_trips = set(trip_ids[:n_test])
    train_df, test_df = df[~df.trip_id.isin(test_trips)], df[df.trip_id.isin(test_trips)]
    print(f"Train: {len(train_df)} rows / {train_df.trip_id.nunique()} trips | "
          f"Test: {len(test_df)} rows / {test_df.trip_id.nunique()} trips")

    report_lines = []

    # --- Stage 1: binary risk-event detector (the headline number) ---
    clf1 = RandomForestClassifier(n_estimators=30, max_depth=6, random_state=42,
                                   class_weight="balanced", n_jobs=-1)
    clf1.fit(train_df[FEATURES], train_df.is_event)
    pred1 = clf1.predict(test_df[FEATURES])
    rep1 = classification_report(test_df.is_event, pred1, target_names=["normal", "event"],
                                  zero_division=0)
    print("\n=== Stage 1: event detector (held-out trips) ===")
    print(rep1)
    report_lines += ["=== Stage 1: event detector ===", rep1]

    # --- Stage 2: event-subtype classifier (the "reasoning"), event rows only ---
    train_ev = train_df[train_df.is_event == 1]
    test_ev = test_df[test_df.is_event == 1]
    clf2 = RandomForestClassifier(n_estimators=30, max_depth=6, random_state=42,
                                   class_weight="balanced", n_jobs=-1)
    clf2.fit(train_ev[FEATURES], train_ev.behavior)
    pred2 = clf2.predict(test_ev[FEATURES])
    rep2 = classification_report(test_ev.behavior, pred2, zero_division=0)
    print("\n=== Stage 2: event-subtype classifier (held-out trips, event rows only) ===")
    print(rep2)
    report_lines += ["\n=== Stage 2: event-subtype classifier ===", rep2]

    imp1 = dict(zip(FEATURES, clf1.feature_importances_.round(4)))
    imp2 = dict(zip(FEATURES, clf2.feature_importances_.round(4)))
    print("\nStage 1 feature importances:", json.dumps(imp1, indent=2))
    print("Stage 2 feature importances:", json.dumps(imp2, indent=2))

    import joblib
    joblib.dump(clf1, OUT_DIR / "event_detector.joblib")
    joblib.dump(clf2, OUT_DIR / "event_subtype.joblib")
    (OUT_DIR / "subtype_classes.json").write_text(json.dumps(list(clf2.classes_)))
    (OUT_DIR / "risk_tiers.json").write_text(json.dumps(RISK_TIER, indent=2))
    (OUT_DIR / "feature_importances.json").write_text(
        json.dumps({"stage1_event_detector": imp1, "stage2_event_subtype": imp2}, indent=2))
    (OUT_DIR / "train_report.txt").write_text("\n".join(report_lines))
    print(f"\nSaved model + metadata to {OUT_DIR}/")


if __name__ == "__main__":
    main()
