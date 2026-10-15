# Vehicle Risk — accident-risk behavior classifier

Third PocketMind-style module for VYOMAA LABS: fully offline, on-device
classification of driving behavior from raw motion-sensor data — the same
class of signal (accelerometer + gyroscope + magnetometer) a real ESP32 +
MPU9250/6050 rig streams from a vehicle, with or without an OBD2 feed.

## Honest framing

**This is not a crash predictor.** No public dataset pairs raw vehicle
telemetry with actual crash outcomes, so nothing here claims to predict
"will this vehicle crash." It classifies **driving behavior** from motion
data (normal / sudden-brake / sudden-acceleration / sudden turn / sudden
lane change) and assigns each behavior a **risk tier** (low/medium/high) —
the same "grounded classifier + explainable reasoning" pattern AgriLens
uses for crop disease, not a black-box oracle. The risk-tier mapping
(`train.py: RISK_TIER`) is the one place human judgment enters; everything
upstream of it is learned from real recorded driving data.

## Data

[Kaggle: Harsh driving dataset](https://www.kaggle.com/datasets/saboorahmad47/harsh-driving-dataset)
— 54 real trip recordings (Mehran car, Arduino + MPU9250 IMU), ~33k rows.
Each row has raw `acc_x/y/z`, `gyro_x/y/z`, `mag_x/y/z`, a binary
`event_class` (0=normal, 1=inside a labeled harsh-driving window), and the
trip's event type encoded in its filename (`sudden-brake`, `sudden-acc`,
`sudden-left-turn`, `sudden-right-turn`, `sudden-left-line-chg`,
`sudden-right-line-chg`, or `safe*`).

## Model: two stages, deliberately tiny

1. **Event detector** (binary, all rows): is this an elevated-risk moment
   or normal driving? RandomForest, 30 trees, depth 6.
2. **Event-subtype classifier** (event rows only): *which kind* of event —
   this is the "reasoning" shown next to the risk alert. Same size model.

Both are small enough (a few KB of tree logic each) to port to an ESP32
later — a stretch goal, not done yet; `train.py`'s docstring explains why
the model was kept this small on purpose.

Features: raw 3-axis accel/gyro + magnitude + a 10-sample trailing rolling
window (max, std) of accel/gyro magnitude — a single raw sensor reading is
noise, not a driving event, so the window mirrors what a real-time
ring-buffer detector on a microcontroller would actually see.

**Train/test split is by trip file**, not by row — rows inside one trip
are highly correlated (same driver, same few seconds), so a row-level
split would leak and inflate the numbers.

## Results (held-out trips, 44 train / 10 test, seed 42)

Stage 1 — event detector:

| | precision | recall | f1 |
|---|---|---|---|
| normal | 0.82 | 0.76 | 0.78 |
| event | 0.49 | 0.57 | 0.53 |

**70% held-out-trip accuracy.** This is the headline number for a live
alert ("is something happening right now") — reasonable for a first
prototype on 44 training trips from a single vehicle/driver setup, not
production-grade. More trips, more vehicles, more drivers is the direct
path to improving it.

Stage 2 — event subtype (event rows only): 53% accuracy, 6-way. Adjacent
classes (left vs. right turn/lane-change) are the main confusion — expected
given how similar their accelerometer signatures are without a magnetometer
heading reference, which this dataset under-samples. Full report:
`model/train_report.txt` after running `train.py`.

## Running it

```bash
# from pocketmind/vehicle-risk/, with a venv that has
# scikit-learn, pandas, numpy, joblib, kaggle installed
python3 train.py          # trains both stages, writes model/, prints the report
python3 replay_demo.py    # replays a real held-out trip, live terminal risk readout
python3 replay_demo.py <trip.csv> --speed 1   # specific trip, real-time speed
```

`replay_demo.py` makes zero network calls — it's the same "run it, then show
the terminal, then show it still works in airplane mode" proof pattern as
the phone demo.

## What's next

- Pull a second dataset (UAH-DriveSet or similar) for a different
  vehicle/driver to test whether accuracy holds out-of-distribution.
- If/when real ESP32 + accelerometer + OBD2 hardware is available: port the
  trained trees to plain C (or TFLite Micro) and replace the CSV replay
  with a live serial/BLE stream from the board.
- Consider adding OBD2 features (speed, RPM, throttle, brake) once a
  dataset that pairs them with accelerometer data is found — this dataset
  is accelerometer-only.
