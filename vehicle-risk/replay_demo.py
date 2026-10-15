"""Live terminal replay demo — feeds one real recorded trip through the
two-stage risk model exactly as an ESP32 streaming from its own IMU would,
printing a running risk readout. Fully offline: no network call anywhere
in this file.

Usage:
  python3 replay_demo.py                      # picks a random held-out-style trip
  python3 replay_demo.py <trip_csv_filename>   # replay a specific trip
  python3 replay_demo.py --speed 1             # 1x = real recorded timing
                                                # (default is 20x so the demo
                                                # doesn't take the full trip length)
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning)

import joblib
import numpy as np
import pandas as pd

from train import DATA_DIR, FEATURES, WINDOW, label_from_filename
import json

MODEL_DIR = Path(__file__).parent / "model"


def load_trip(name: str | None) -> tuple[pd.DataFrame, str]:
    files = sorted(DATA_DIR.glob("*.csv"))
    if name:
        path = next((p for p in files if p.name == name), None)
        if path is None:
            print(f"Trip file not found: {name}\nAvailable files:")
            for p in files:
                print(" ", p.name)
            sys.exit(1)
    else:
        # default: the same held-out trip IDs train.py's test split uses
        # (trip_id = sort order, seed 42, first 20%), so the demo replays a
        # trip the model never trained on — not an inflated in-sample result
        rng = np.random.RandomState(42)
        order = list(range(len(files)))
        rng.shuffle(order)
        held_out = set(order[:max(1, int(len(files) * 0.2))])
        candidates = [files[i] for i in held_out if "sudden-brake" in files[i].name]
        path = candidates[0] if candidates else files[sorted(held_out)[0]]
    df = pd.read_csv(path)
    trip_label = label_from_filename(path.name)
    df["accel_mag"] = np.sqrt(df.acc_x**2 + df.acc_y**2 + df.acc_z**2)
    df["gyro_mag"] = np.sqrt(df.gyro_x**2 + df.gyro_y**2 + df.gyro_z**2)
    df["accel_mag_roll_max"] = df.accel_mag.rolling(WINDOW, min_periods=1).max()
    df["accel_mag_roll_std"] = df.accel_mag.rolling(WINDOW, min_periods=1).std().fillna(0)
    df["gyro_mag_roll_max"] = df.gyro_mag.rolling(WINDOW, min_periods=1).max()
    df["gyro_mag_roll_std"] = df.gyro_mag.rolling(WINDOW, min_periods=1).std().fillna(0)
    return df, path.name


def main():
    args = sys.argv[1:]
    speed = 20.0
    if "--speed" in args:
        i = args.index("--speed")
        speed = float(args[i + 1])
        del args[i:i + 2]
    trip_name = args[0] if args else None

    detector = joblib.load(MODEL_DIR / "event_detector.joblib")
    subtype = joblib.load(MODEL_DIR / "event_subtype.joblib")
    risk_tiers = json.loads((MODEL_DIR / "risk_tiers.json").read_text())

    df, fname = load_trip(trip_name)
    print(f"=== PocketMind Vehicle Risk — replaying real trip: {fname} ===")
    print(f"{len(df)} samples · fully offline, no network call in this process")
    print(f"Model: 2-stage RandomForest (30 trees, depth 6) trained on held-out trips")
    print("-" * 72)

    last_alert_t = -999
    for idx, row in df.iterrows():
        feats = pd.DataFrame([row[FEATURES].values], columns=FEATURES)
        is_event = detector.predict(feats)[0]
        event_prob = detector.predict_proba(feats)[0][1]

        feat_vals = feats.values[0]
        t = idx * 0.02  # approx display clock, independent of real file timestamps
        if is_event:
            sub_proba = subtype.predict_proba(feats)[0]
            order = np.argsort(sub_proba)[::-1]
            top2 = ", ".join(f"{subtype.classes_[i]} {sub_proba[i]:.0%}" for i in order[:2])
            sub_pred = subtype.classes_[order[0]]
            tier = risk_tiers.get(sub_pred, "medium")
            top_feat_idx = int(np.argmax(np.abs(feat_vals)))
            reasoning = f"{FEATURES[top_feat_idx]}={feat_vals[top_feat_idx]:.2f}"
            tag = {"low": " ", "medium": "!", "high": "!!"}[tier]
            print(f"[{t:6.2f}s] {tag} RISK={tier.upper():6s} (p={event_prob:.0%})  "
                  f"likely: {top2}  reasoning: {reasoning} spiked")
        else:
            if idx % 25 == 0:
                print(f"[{t:6.2f}s]    normal   (p={event_prob:.0%})")
        time.sleep(0.02 / speed)

    print("-" * 72)
    print("Replay complete. Ground-truth label for this trip file: "
          f"{label_from_filename(fname)}")
    print("This is a behavior classifier trained on real accelerometer/gyroscope "
          "data (not a crash predictor) — see README.md for accuracy, limits, "
          "and the ESP32 porting plan.")


if __name__ == "__main__":
    main()
