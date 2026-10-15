"""Live terminal replay demo -- the version that actually runs ON THE
PHONE in Termux. Unlike replay_demo.py (which needs the sklearn/pandas
venv on a laptop), this uses only infer.py's pure-stdlib tree walker, so
it needs nothing beyond the Python that's already in Termux for app.py.

Feeds one real recorded trip through the two-stage risk model row by row,
exactly as an ESP32 streaming its own IMU over the OBD2-adjacent mount
would, printing a running risk readout. Zero network calls anywhere in
this file -- that's the actual point of running it with the phone in
airplane mode.

Usage (from the pocketmind/vehicle-risk/ directory on the phone):
  python3 replay_termux.py                                   # default trip
  python3 replay_termux.py <trip_csv_filename>                # pick one
  python3 replay_termux.py <trip_csv_filename> --speed 1      # real-time
                                                                # (default 20x)
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

from infer import RiskModel, replay_trip

SAMPLE_DIR = Path(__file__).parent / "data" / "sample_trips"
FULL_DIR = Path(__file__).parent / "data" / "harsh-driving"


def pick_trip(name: str | None) -> Path:
    search_dirs = [SAMPLE_DIR, FULL_DIR]
    if name:
        for d in search_dirs:
            p = d / name
            if p.is_file():
                return p
        print(f"Trip file not found: {name}\nAvailable in {SAMPLE_DIR}:")
        for p in sorted(SAMPLE_DIR.glob("*.csv")):
            print(" ", p.name)
        sys.exit(1)
    default = sorted(SAMPLE_DIR.glob("*.csv"))
    if not default:
        print(f"No sample trips found in {SAMPLE_DIR}")
        sys.exit(1)
    brake = [p for p in default if "sudden-brake" in p.name]
    return brake[0] if brake else default[0]


def main():
    args = sys.argv[1:]
    speed = 20.0
    if "--speed" in args:
        i = args.index("--speed")
        speed = float(args[i + 1])
        del args[i:i + 2]
    trip_path = pick_trip(args[0] if args else None)

    model = RiskModel()
    n_rows = sum(1 for _ in csv.DictReader(open(trip_path)))

    print(f"=== PocketMind Fleet Risk -- replaying real trip: {trip_path.name} ===")
    print(f"{n_rows} samples · fully offline, no network call in this process")
    print("Model: 2-stage RandomForest (30 trees each) walked in pure Python, no sklearn on-device")
    print("-" * 72)

    n_events = 0
    tier_counts = {"low": 0, "medium": 0, "high": 0}
    for idx, t, row, pred in replay_trip(model, trip_path):
        tier_counts[pred["tier"]] += 1
        if pred["is_event"]:
            n_events += 1
            top2 = ", ".join(f"{b} {p:.0%}" for b, p in pred["ranked"])
            tag = {"low": " ", "medium": "!", "high": "!!"}[pred["tier"]]
            print(f"[{t:6.2f}s] {tag} RISK={pred['tier'].upper():6s} "
                  f"(p={pred['event_proba']:.0%})  likely: {top2}")
        elif idx % 25 == 0:
            print(f"[{t:6.2f}s]    normal   (p={pred['event_proba']:.0%})")
        time.sleep(0.02 / speed)

    print("-" * 72)
    print(f"Replay complete. {n_events} elevated-risk moments flagged out of {n_rows} samples "
          f"({tier_counts['high']} high, {tier_counts['medium']} medium).")
    print("Behavior classifier, not a crash predictor -- see README.md for accuracy, limits, "
          "and the ESP32 porting plan.")


if __name__ == "__main__":
    main()
