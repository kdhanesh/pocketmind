"""Exports the trained RandomForests to a dependency-free JSON format.

Why: the phone (Termux) has no safe story for building scikit-learn from
source, and joblib.load() of a RandomForestClassifier needs sklearn
installed anyway to unpickle the class. Since both forests are tiny
(30 trees, depth<=6 each -- chosen specifically so they'd port to ESP32
firmware later, see train.py), dumping the raw tree arrays to JSON and
walking them with plain Python on-device is the simplest path: zero
numpy/pandas/sklearn needed at inference time, same numbers.

Run with the venv that has scikit-learn installed (not on the phone):
  kgvenv/bin/python3 export_portable.py
"""
import json
from pathlib import Path

import joblib

OUT_DIR = Path(__file__).parent / "model"


def dump_tree(tree, classes):
    t = tree.tree_
    nodes = []
    for i in range(t.node_count):
        feature = int(t.feature[i])
        if feature == -2:  # leaf
            counts = t.value[i][0].tolist()
            total = sum(counts) or 1.0
            proba = [c / total for c in counts]
            nodes.append({"leaf": True, "proba": proba})
        else:
            nodes.append({
                "leaf": False,
                "feature": feature,
                "threshold": float(t.threshold[i]),
                "left": int(t.children_left[i]),
                "right": int(t.children_right[i]),
            })
    return nodes


def dump_forest(clf):
    return {
        "classes": [c.item() if hasattr(c, "item") else c for c in clf.classes_],
        "trees": [dump_tree(est, clf.classes_) for est in clf.estimators_],
    }


def main():
    clf1 = joblib.load(OUT_DIR / "event_detector.joblib")
    clf2 = joblib.load(OUT_DIR / "event_subtype.joblib")

    portable = {
        "features": ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z",
                     "accel_mag", "gyro_mag",
                     "accel_mag_roll_max", "accel_mag_roll_std",
                     "gyro_mag_roll_max", "gyro_mag_roll_std"],
        "window": 10,
        "risk_tiers": json.loads((OUT_DIR / "risk_tiers.json").read_text()),
        "stage1_event_detector": dump_forest(clf1),
        "stage2_event_subtype": dump_forest(clf2),
    }
    out_path = OUT_DIR / "portable_model.json"
    out_path.write_text(json.dumps(portable))
    n_nodes = (sum(len(t) for t in portable["stage1_event_detector"]["trees"]) +
               sum(len(t) for t in portable["stage2_event_subtype"]["trees"]))
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB, {n_nodes} tree nodes total)")


if __name__ == "__main__":
    main()
