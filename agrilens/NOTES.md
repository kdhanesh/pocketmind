# AgriLens classifier — conversion notes

## What's VERIFIED

- **Numpy port is numerically exact against the real torch model.** Compared
  logits from `mnv2_numpy.py` against `torchvision.models.mobilenet_v2()`
  loaded with the same checkpoint, on 6 test images. Max abs diff ≈ 2.7e-5,
  max rel diff ≈ 2e-6 — pure float32 rounding noise, not an implementation bug.
  Every image's numpy top-1 class exactly matched torch's top-1 class.

- **The 38-class alphabetical label order is correct**, not just assumed. The
  checkpoint's `class_names.json` is missing from the HuggingFace repo
  (`Daksh159/plant-disease-mobilenetv2`) despite the README mentioning it, so
  there was no author-confirmed order. I used the standard alphabetical
  PlantVillage/"New Plant Diseases Dataset" folder order and validated it on
  4 same-distribution test images pulled directly from the original
  `spMohanty/PlantVillage-Dataset` GitHub mirror:
  - `Tomato___Septoria_leaf_spot` sample → predicted class 32 (correct), conf 0.99997
  - `Corn_(maize)___Northern_Leaf_Blight` sample → predicted class 9 (correct), conf 0.99939
  - `Tomato___healthy` sample → predicted class 37 (correct)
  - `Pepper,_bell___healthy` sample → predicted class 19 (correct)

  All 4 matched exactly, with high confidence (>0.99 in the two checked
  above), so the label list in `classify.py` can be trusted.

- **classifier head quirk**: the checkpoint's `classifier.1` is itself a
  `Sequential(Dropout, Linear)` rather than a plain `Linear` (key path
  `classifier.1.1.weight/bias`, not `classifier.1.weight/bias`). Both
  Dropouts are no-ops at inference so this doesn't change behavior, but it
  will break a naive `torch_model.load_state_dict()` against the stock
  `torchvision.models.mobilenet_v2()` unless you rebuild `classifier[1]` to
  match first (see `validate.py`).

## What's a PROXY / limitation, not a bug

- **"Chilli" is not a real class in this model.** PlantVillage has no chilli
  data. `classify.py` maps the `Pepper,_bell` classes (bell pepper — same
  genus, *Capsicum*, but a different species from Indian chilli/hot pepper
  cultivars) onto `crop: "chilli (proxy: bell pepper model, not
  chilli-trained)"` so the product can still talk about chilli, but every
  chilli prediction from this checkpoint is a proxy guess, not a trained
  chilli classifier. Don't quote an accuracy number for chilli from this
  model — there isn't one to quote honestly.

- **Real-world (non-PlantVillage) photos did noticeably worse** than the
  same-distribution test above. Two full-scene, high-resolution phone/DSLR
  photos pulled from Wikimedia Commons (a tomato septoria leaf-spot photo and
  a corn northern-leaf-blight photo, both correctly labeled by their
  photographers) were misclassified by the model — the tomato photo's top-1
  was a corn-rust class, and the corn photo's top-1 was the wrong corn
  disease (right crop, wrong disease). This is not a code bug — the numpy and
  torch outputs matched exactly on these too — it's the model itself: it was
  trained only on PlantVillage's clean, single-leaf, uniform-background lab
  photos, and those don't generalize well to cluttered real-world framing.
  This is the exact PlantVillage generalization gap already flagged in
  `PROOF_AND_PILOT_PLAN.md` ("Public leaf-image datasets ... are lab photos
  and often perform poorly on real field photos"). **Don't publish any
  accuracy number for AgriLens without testing on the team's own field
  photos first** — this run is further evidence that PlantVillage-only
  accuracy won't transfer.

## Performance

- Single 224×224 image inference: **~0.07s** on this laptop's CPU (one core,
  im2col + matmul via numpy/BLAS, no GPU). An old Android phone's CPU is
  likely 3-10x slower depending on model/age, so budget roughly **0.3-1s per
  photo** on-device — still fine for an interactive demo, no "thinking"
  spinner needed for the classifier step specifically (the SLM explanation
  step afterward will be the slow part, per PROOF_AND_PILOT_PLAN.md's own
  "expect a few tokens per second" caution).

## Files produced

- `export_npz.py` — one-time conversion (torch state_dict → `mobilenetv2_plant.npz`); needs torch, run once on the laptop, never on the phone.
- `mnv2_numpy.py` — pure-numpy MobileNetV2 forward pass. No torch dependency.
- `preprocess.py` — standalone preprocessing module (same logic is inlined into `classify.py` too, so `classify.py` has zero sibling-file imports besides `mnv2_numpy.py` + the `.npz`).
- `validate.py` — the torch-vs-numpy + label-order validation harness (keep for regression-checking if the checkpoint ever changes).
- `classify.py` — **the actual phone-side deliverable.** Only imports `numpy`, `PIL.Image`, `json`, `sys`, `os`. Copy this + `mnv2_numpy.py` + `mobilenetv2_plant.npz` to Termux; nothing else is needed.
- `mobilenetv2_plant.npz` (9.1MB) — exported weights, float32.
- `testimgs/` — validation images (not needed on-device, dev-only).

## Phone-side dependencies

Termux: `pkg install python`, then `pip install numpy pillow`. That's it — no
torch, no TFLite, no ONNX runtime, no compiling anything. This was the whole
point of the numpy port: avoid dependencies that don't have usable prebuilt
wheels for Termux's bionic-libc ARM64 environment.
