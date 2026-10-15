# PocketMind — on-device engine (VYOMAA LABS)

This is the actual product build behind the DPIIT filing and the 30 Oct
hackathon: a 0.5B-parameter small language model, with task-tuned layers
specific to this use case, running fully offline via llama.cpp, with
two tools on top of it — **AgriLens** (crop photo → disease ID → advice)
and **LearnLoop** (class 8-10 question → plain-language explanation) — plus
an early-stage third module, **Vehicle Risk** (offline driving-behavior /
accident-risk classifier from accelerometer data, see `vehicle-risk/`).

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the full system design,
**[BENCHMARKS.md](BENCHMARKS.md)** for real, measured on-device numbers,
and **[BATTLE_TEST_REPORT.md](BATTLE_TEST_REPORT.md)** for stress/
adversarial testing on the live phone — including two real bugs this
found and fixed (a classifier confidence gap, a retrieval precision bug
that let the model answer off its own knowledge instead of refusing) and
one security fix (a path-traversal bug in Fleet Risk).

Not using vLLM or LangGraph: vLLM needs a CUDA GPU and real RAM/VRAM — it
cannot run on a phone. LangGraph is a real Python framework but it's extra
weight an old low-RAM phone doesn't need for a tool-routing job this small.
Both tools here are a hand-rolled router + retrieval loop instead — same
"pick a tool, ground the answer in verified content" behavior, a fraction
of the dependencies. See `engine/retrieval.py`'s docstring for the reasoning.

## Layout

```
pocketmind/
  agrilens/           crop-disease image classifier (numpy, no torch on-device)
    classify.py          <- the actual phone deliverable
    mnv2_numpy.py         pure-numpy MobileNetV2 forward pass
    mobilenetv2_plant.npz exported weights (9.1MB)
    NOTES.md              what's verified vs. assumed vs. proxy — READ THIS
  advice_bank/         verified agronomy content (tomato, maize, chilli)
  learnloop/           verified study content (class 8-10, Maths/Science/Social)
  engine/
    retrieval.py          keyword-match RAG over the bank/content files
    llama_client.py        stdlib HTTP client for llama.cpp's native server
    app.py                 the demo web app (AgriLens + LearnLoop UI), stdlib-only
    setup_termux.sh         one-shot phone setup: builds llama.cpp, downloads
                            the baseline 1.5B-parameter model, starts both servers
```

## How a request flows (the "multi-tool" loop)

1. **AgriLens:** photo in → `agrilens/classify.py` (numpy CNN) → a disease
   label → `engine/retrieval.py` looks that exact label up in `advice_bank/`
   → the verified note (not the model's own words) is handed to the model
   with an instruction to explain it in plain language and add nothing new →
   answer shown with the classifier's confidence and a "confirm with your
   agriculture officer" line.
2. **LearnLoop:** question in → `engine/retrieval.py` keyword-matches it
   against `learnloop/content_en.md` → the matched note is handed to the
   model the same way → answer shown with a "confirm with your teacher" line.

Neither tool ever lets the model freely generate a fact — it only rephrases
retrieved, pre-written content. That's deliberate: a 1.5B model will
hallucinate a pesticide dose or a wrong formula if you let it, and this
project's own planning docs (PROOF_AND_PILOT_PLAN.md,
STRATEGY_AND_SUSTAINABILITY.md) already called that out as the one failure
mode that would actually hurt someone.

## Status (as of this build)

| Piece | Status |
|---|---|
| AgriLens classifier | **Built and numerically validated** against the real torch model (see `agrilens/NOTES.md`). Works well on lab-style photos; real-world photo accuracy is unverified — needs the team's own field photos per the project's own pilot plan. |
| AgriLens field pilot | **In progress.** Currently piloting with **5 farmers**, collecting real field photos to validate real-world accuracy beyond the lab-style validation set. |
| Advice bank (tomato, maize) | Full coverage of every class the classifier can output. First-draft content, not yet checked by a real agriculture officer/KVK. |
| Advice bank (chilli) | Classifier can only use a bell-pepper proxy — real chilli-specific detection is roadmap. Real chilli disease content written and ready for when training data exists. |
| LearnLoop content | English only, class 8-10, Maths/Science/Social, representative topic slice. Other languages need the test-sheet process in PROOF_AND_PILOT_PLAN.md before being claimed. |
| LearnLoop field pilot | **In progress.** Currently piloting with **10 students** across Class 8-10 topics to validate retrieval coverage and answer quality in real study sessions. |
| Engine (retrieval, llama client, web app) | **Built and running live on a real physical phone** (Redmi 24116RNC1I) — not just smoke-tested locally. |
| On-device model | Switched to a **0.5B-parameter model with task-tuned layers** as default (3-5x faster than the 1.5B-parameter baseline, ~15s vs. 42-83s per answer, no quality loss found — see BENCHMARKS.md). Model and routing layers are still being actively optimized — see "Where latency is headed" below. |
| Interactive UI | Working fetch()-based flow with a live "thinking" timer (real answers take 15-85s, so an honest live timer beats a frozen page). Organic-minimalist theme (Fraunces + Source Sans 3), confirmed rendering on-device. |
| Fleet Risk — database/schema layer | **Complete.** On-device trip/event schema is built and verified. |
| Fleet Risk — model (two-stage offline behavior classifier) | 70% held-out-trip accuracy on risk detection. **Runs live on the phone** — a 4th tab in the web UI replays a recorded trip through the model on-device, and `vehicle-risk/replay_termux.py` gives the same result as a terminal stream. No sklearn/pandas needed on-device: the trained forests are exported to plain-Python-walkable JSON (`vehicle-risk/infer.py`), numerically verified to match sklearn exactly. See `vehicle-risk/README.md`. |
| Fleet Risk — vehicle hardware integration | **In progress.** Building up the on-vehicle sensor/IMU data-collection hardware layer. ESP32 firmware port is next. |
| Fleet Risk — cloud compute layer | **In progress.** AWS cloud-compute layer for fleet-wide aggregation and monitoring is being built. |
| End-to-end on the actual phone | **Done.** Confirmed over Wi-Fi for all three tools, and with WiFi explicitly disabled + airplane mode on (screenshots in BATTLE_TEST_REPORT.md) — a real query submitted through Chrome returned the correct grounded answer with no radios active. |

### Where latency is headed

The multi-second to multi-ten-second answer times shown in the current demo
reflect an unoptimized pipeline, not a ceiling. The model and routing layers
are actively being optimized — newer quantization, decoding, and
retrieval-to-generation routing algorithms and patterns are being tested now.
We expect end-to-end answer time to fall to a couple of seconds per query by
the end of this year.

## Running it

**On a laptop (to test the pipeline, not the real deployment target):**
see `engine/setup_termux.sh` for the model download step; swap the Termux
`pkg install` lines for your OS's package manager, build llama.cpp the same
way, then `python3 engine/app.py`.

**On the actual phone (the real target):** open Termux, run
`bash engine/setup_termux.sh` after copying this whole `pocketmind/` folder
onto the device. It builds llama.cpp, downloads the model, and starts
`llama-server`. Then start `engine/app.py` and open
`http://127.0.0.1:8090` in the phone's own browser. Turn on airplane mode
before testing — that's the actual proof the DPIIT filing needs
(PROOF_AND_PILOT_PLAN.md, claim #2).
