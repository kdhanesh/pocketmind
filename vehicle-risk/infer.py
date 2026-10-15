"""Dependency-free inference for the vehicle risk model.

Walks the raw tree arrays exported by export_portable.py with plain Python
(stdlib `csv`/`json`/`math` only) -- no numpy, pandas, or scikit-learn.
This is what actually runs on the phone: Termux has no safe path to a
built scikit-learn wheel, and joblib's pickle format needs sklearn
installed just to load the class. The numbers this produces are the exact
same numbers sklearn would give (same tree thresholds, same leaf-proba
averaging sklearn's RandomForestClassifier.predict_proba does internally)
-- see replay_demo.py for the sklearn-backed version these were checked
against.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "model"


def _tree_proba(nodes: list[dict], feat: list[float]) -> list[float]:
    node = nodes[0]
    while not node["leaf"]:
        node = nodes[node["left"] if feat[node["feature"]] <= node["threshold"] else node["right"]]
    return node["proba"]


def _forest_proba(forest: dict, feat: list[float]) -> list[float]:
    n_classes = len(forest["classes"])
    acc = [0.0] * n_classes
    for tree in forest["trees"]:
        p = _tree_proba(tree, feat)
        for i in range(n_classes):
            acc[i] += p[i]
    n = len(forest["trees"])
    return [a / n for a in acc]


class RiskModel:
    def __init__(self, portable_path: Path = MODEL_DIR / "portable_model.json"):
        data = json.loads(Path(portable_path).read_text())
        self.features: list[str] = data["features"]
        self.window: int = data["window"]
        self.risk_tiers: dict[str, str] = data["risk_tiers"]
        self.stage1 = data["stage1_event_detector"]
        self.stage2 = data["stage2_event_subtype"]

    def predict(self, feat: list[float]) -> dict:
        p1 = _forest_proba(self.stage1, feat)
        event_idx = self.stage1["classes"].index(1)
        event_proba = p1[event_idx]
        is_event = event_proba == max(p1)

        p2 = _forest_proba(self.stage2, feat)
        ranked = sorted(zip(self.stage2["classes"], p2), key=lambda kv: -kv[1])
        top_behavior, top_p = ranked[0]
        tier = self.risk_tiers.get(top_behavior, "medium") if is_event else "low"
        return {
            "is_event": is_event,
            "event_proba": event_proba,
            "tier": tier,
            "top_behavior": top_behavior,
            "top_p": top_p,
            "ranked": ranked[:2],
        }


def _rolling_std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(var)


def replay_trip(model: RiskModel, csv_path: Path):
    """Yields (row_index, elapsed_seconds, raw_row, prediction) per row,
    computing the same trailing-window features train.py used, as a
    streaming ring buffer (no full-file dataframe needed)."""
    accel_buf: list[float] = []
    gyro_buf: list[float] = []
    with open(csv_path, newline="") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            ax, ay, az = float(row["acc_x"]), float(row["acc_y"]), float(row["acc_z"])
            gx, gy, gz = float(row["gyro_x"]), float(row["gyro_y"]), float(row["gyro_z"])
            accel_mag = math.sqrt(ax * ax + ay * ay + az * az)
            gyro_mag = math.sqrt(gx * gx + gy * gy + gz * gz)

            accel_buf.append(accel_mag)
            gyro_buf.append(gyro_mag)
            if len(accel_buf) > model.window:
                accel_buf.pop(0)
            if len(gyro_buf) > model.window:
                gyro_buf.pop(0)

            feat = [ax, ay, az, gx, gy, gz, accel_mag, gyro_mag,
                    max(accel_buf), _rolling_std(accel_buf),
                    max(gyro_buf), _rolling_std(gyro_buf)]
            pred = model.predict(feat)
            t = idx * 0.02  # approx display clock, matches replay_demo.py
            yield idx, t, row, pred


def summarize_trip(model: RiskModel, csv_path: Path, max_events_shown: int = 14) -> str:
    """Compact text log of a full trip replay -- same shape the terminal
    demo prints, formatted for the web result card."""
    lines = []
    n_rows = 0
    n_events = 0
    tier_counts = {"low": 0, "medium": 0, "high": 0}
    shown = 0
    for idx, t, row, pred in replay_trip(model, csv_path):
        n_rows += 1
        tier_counts[pred["tier"]] += 1
        if pred["is_event"]:
            n_events += 1
            if shown < max_events_shown:
                top2 = ", ".join(f"{b} {p:.0%}" for b, p in pred["ranked"])
                tag = {"low": " ", "medium": "!", "high": "!!"}[pred["tier"]]
                lines.append(f"[{t:6.2f}s] {tag} RISK={pred['tier'].upper():6s} "
                             f"(p={pred['event_proba']:.0%})  likely: {top2}")
                shown += 1
    if n_events > max_events_shown:
        lines.append(f"... {n_events - max_events_shown} more flagged moments ...")
    lines.append("")
    lines.append(f"{n_rows} samples replayed · {n_events} elevated-risk moments flagged "
                 f"({tier_counts['high']} high, {tier_counts['medium']} medium) · "
                 f"{tier_counts['low']} normal")
    return "\n".join(lines)
