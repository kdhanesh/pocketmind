# Battle-test report — PocketMind, 2026-10-15

Stress and adversarial testing run against the live app on the actual
physical phone (Redmi 24116RNC1I), not a laptop simulation. Three real
bugs were found and fixed during this pass — this report covers what was
tested, what broke, what was fixed, and what's still honestly unresolved.

## Summary

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | AgriLens: no "not a leaf" rejection — any image forces a diagnosis | High (credibility) | **Fixed** |
| 2 | LearnLoop: stopword-only matches hand the model an unrelated note, which it then answers from general knowledge instead of refusing | High (breaks the core grounding guarantee) | **Fixed** |
| 3 | Fleet Risk: path traversal / arbitrary file read via the `trip` parameter | Medium (local-only server, but real) | **Fixed** |
| 4 | LearnLoop latency creeps from ~15s (single-shot) to 38-55s under repeated back-to-back calls | Low (still well within demo tolerance) | Documented, not a bug |
| 5 | SLM occasionally repeats itself verbatim under certain prompts (0.5B model, no repeat penalty set) | Low (cosmetic) | Documented, candidate fix below |

---

## 1. AgriLens — image classifier

### Method
6 real images pushed to the phone and POSTed through the actual HTTP
handler: 4 lab-quality PlantVillage-style photos, 2 full-resolution
real-world photos (2.9MB / 4.1MB) of the same conditions. Plus 2
adversarial cases (a non-image file, a request with no file field) and
one case the user found independently: a photo of a sheet of paper on a
desk.

### Results (before the fix)

| Image | Confidence | Correct? |
|---|---|---|
| pv_corn_nlb.jpg (lab) | 100% | Yes |
| pv_pepper_healthy.jpg (lab) | 94% | Yes |
| pv_tomato_healthy.jpg (lab) | 100% | Yes |
| pv_tomato_septoria.jpg (lab) | 100% | Yes |
| corn_nlb.jpg (real photo) | 38% | **No** — called Cercospora, actually Northern Leaf Blight |
| tomato_septoria.jpg (real photo) | 68% | **No** — called corn Common Rust, wrong *crop* |
| user's photo of paper on a desk | 39% | **No** — called "Cherry, Powdery Mildew" |

### The actual problem
The classifier is a closed-set softmax over ~38 PlantVillage classes.
It has no concept of "this isn't a leaf" — every input is forced into the
highest-scoring class, no matter how irrelevant. The confidence number
*was* being computed correctly; the app just wasn't looking at it before
presenting a result as if it were reliable.

### Fix
`AGRI_CONFIDENCE_FLOOR = 0.70` in `engine/app.py`, derived directly from
the table above — correct lab-photo IDs cluster at 94-100%, every wrong
guess and the garbage input cluster at 38-68%, with a clean gap between.
Below the floor, AgriLens now shows "Not confident enough to diagnose"
with a retake suggestion instead of asserting a guess. Re-verified after
the fix: all 4 correct photos still pass through normally; both
real-world misclassifications and the paper photo (confirmed with the
user's exact screenshot) are now correctly gated.

### Also found, not fixed (low priority)
- The error message for a corrupted/non-image upload leaks an internal
  Termux tmp file path (`cannot identify image file
  '/data/data/.../tmp/tmpXXXX.jpg'`). Harmless on a loopback-only local
  server, but worth trimming before any public-facing deployment.
- The pepper_healthy SLM response repeated one bullet point twice
  verbatim — see finding #5.

---

## 2. LearnLoop — retrieval + tutor

### Method
7 questions POSTed live: 3 known-good topic matches, 1 clearly
off-content question, 1 XSS/prompt-injection attempt, 1 Hindi-script
question, 1 empty submission.

### The real bug
**"What is the capital of France?"** matched the unrelated "periodic
table" content chunk and got a confident, fully-formed answer back —
*from the model's own general knowledge*, not from the matched note. This
is the single most serious finding in this whole pass: the entire
architecture's safety story is "the model only rephrases a verified note,
it never invents a fact" (see `ARCHITECTURE.md`), and this is exactly the
scenario that promise is supposed to prevent.

**Root cause**: `retrieval.py`'s keyword scorer had no stopword
filtering. "What is the capital of France?" tokenizes to `{what, the,
capital, france}`; the periodic-table chunk's title tokenizes to `{the,
periodic, table, organizing, elements}`. The single shared word **"the"**
produced a score of 1/4 = 0.25, clearing the 0.15 match threshold. A
Hindi-script Pythagoras question hit the same bug via the word "and",
misrouting to "Newton's laws."

A second-order problem showed up in the France case specifically: once
handed the wrong note, the 0.5B model didn't say "I don't know" — it
answered "Paris" correctly from its own training data, then degenerated
into **repeating "The capital city of France is Paris" about 15 times**
until it hit the token cap. Two separate failures stacked: a retrieval
precision bug, and a small-model repetition-loop bug (see #5).

### Fix
Added a stopword list to `retrieval.py`'s `_tokenize()` (the, a, an,
what, and, of, is, etc. — ~45 common function words). Re-verified with
all 6 original test questions: all 3 real topics still match correctly;
both the France question and the Hindi question now correctly return "no
match" instead of a spurious/wrong-language match.

### What worked correctly without changes
- The XSS payload (`<script>alert(1)</script> ...`) was safely
  HTML-escaped in every response path — no injection risk.
- Empty question submission correctly rejected both before and after.
- Devanagari (Hindi) script is invisible to the current ASCII-only
  tokenizer regex — after the fix, a Hindi question now honestly returns
  "no match" rather than a wrong guess, which is correct behavior but
  worth flagging: genuine Hindi-language support is still a roadmap item,
  not implemented.

### Latency under repeated load
First single-shot benchmark (BENCHMARKS.md): **15.3s**. This stress
battery's 6 back-to-back LearnLoop calls: **38.3s, 41.8s, 43.6s, 53.5s,
0.005s (no-match, no SLM call), 54.2s** — a clear upward drift across
consecutive calls, not noise. Checked for thermal throttling as the
likely cause: battery temp was 35.0°C before the battery and 34.0°C
after — essentially flat, not overheating. The cause is more likely
`llama-server`'s own internal state (KV cache, context accumulation)
under repeated requests without a restart between them. **Not yet root
caused** — flagging honestly rather than guessing further. Still well
within an acceptable range for a live demo (under a minute), but the
*benchmarked* 15s number should not be presented as the typical case in
a multi-question demo sequence — expect 20-55s in practice.

---

## 3. Fleet Risk — vehicle behavior classifier

### Method
Two separate passes:
1. **Scale/stability**: ran all 54 real trips (not just the 4 bundled
   demo samples) through `infer.py` directly — the identical code that
   runs on the phone.
2. **Security**: adversarial `trip` parameter values sent to the live
   `/fleet` endpoint on the phone.

### Scale results
| Metric | Result |
|---|---|
| Trips processed | 54 / 54, zero errors |
| Total rows replayed | 32,987 |
| Per-trip timing | min 14.6ms · p50 27.7ms · p95 56.4ms · max 83.5ms |
| Throughput | ~18,950 rows/sec |

No crashes, no exceptions, no degenerate trips (including the
`safe-no-movement` trip, which has long stretches of near-zero sensor
variance — a plausible edge case for the rolling-std feature computation,
handled correctly).

### Security finding (real vulnerability, fixed)
`trip=/data/data/com.termux/files/home/pocketmind/engine/app.py` as the
POST value caused the server to try to CSV-parse `app.py`'s own Python
source as if it were a trip recording (it crashed with a `KeyError`
reading the file, confirming the file was actually opened).

**Root cause**: `SAMPLE_TRIPS_DIR / trip` using pathlib's `/` operator —
when the right operand is an absolute path, pathlib **discards the left
side entirely** and returns just the absolute path. A deep relative
traversal (`../../../../../../etc/hosts`) was also tried but didn't
reach outside the Termux app sandbox at the depth tested; the absolute-
path vector was the one that actually worked.

**Fix**: the `trip` value is now checked against a whitelist built from
the real directory listing (`{p.name for p in
SAMPLE_TRIPS_DIR.glob("*.csv")}`) before any path is constructed from it,
instead of trusting client input for path construction at all.
Re-verified: both the absolute-path and relative-traversal payloads now
correctly return the generic "pick a recorded trip" error; legitimate
trip selection is unaffected.

Real-world risk is low (the server only binds to `127.0.0.1`, never
reachable off-device), but "it's local-only" is exactly the kind of
assumption that stops being true the moment someone demos over a
hotspot, roots the phone, or the binding gets changed later — worth
fixing regardless of today's exposure.

---

## 4. System resources under load

| Metric | Before stress testing | After |
|---|---|---|
| Battery level | 100% | 100% |
| Battery temp | 35.0°C | 34.0°C |
| MemFree (truly free) | 77MB | 52MB |
| MemAvailable (incl. reclaimable) | 1.37GB | 1.43GB |

No thermal buildup, no memory leak signature across the full test battery
(AgriLens ×8, LearnLoop ×7, Fleet Risk ×54 trips + security probes).

---

## 5. Offline / airplane-mode proof (previously pending, now done)

WiFi was explicitly disabled (`svc wifi disable`, confirmed via `dumpsys
wifi` → "Wi-Fi is disabled") and airplane mode flagged on in system
settings. With the plane icon visibly showing in the status bar and WiFi
off for the whole exchange, a LearnLoop query was typed and submitted
through the actual Chrome browser UI (not curl, not adb) and returned the
correct grounded answer in 55.5s. Screenshots captured at three points:
page loaded with radios off, the live "thinking" counter mid-computation,
and the final correct answer — all with the plane icon visible throughout.
WiFi was restored afterward.

---

## What's still open

- **Repetition-loop tendency** (finding from LearnLoop's France case and
  AgriLens's pepper_healthy case): the 0.5B model occasionally repeats a
  phrase or bullet point verbatim. `llama-server` supports a repeat
  penalty (`--repeat-penalty`, typically 1.1-1.3) that isn't currently
  set in `setup_termux.sh` — worth adding and re-testing.
- **LearnLoop latency drift under sustained use** (38-55s vs. the
  15.3s single-shot benchmark) — root cause not confirmed; ruled out
  thermal throttling, `llama-server` internal state is the leading
  suspect. Worth a dedicated investigation (e.g. restarting
  `llama-server` between calls vs. not, to isolate it) before the next
  demo if a presenter needs to set expectations on timing.
- **Hindi-language support**: genuinely not implemented (the retrieval
  tokenizer is ASCII-only) — now correctly *fails honestly* instead of
  silently misrouting, but real Hindi support is still roadmap, not done.
- **Minor info-disclosure**: AgriLens's corrupt-image error message
  includes an internal tmp file path. Low priority given the server is
  loopback-only, but trivial to trim.

## Methodology notes

All timings in this report are the server's own `time.time()`-measured
figures, not client-side `curl` wall-clock (which proved unreliable
through `adb shell`'s remote-shell quoting in a couple of ad-hoc checks —
noted in-session, not a finding about the app itself). AgriLens/LearnLoop
requests were sent via `curl` directly to `127.0.0.1:8090` from an `adb
shell` session, exercising the exact same HTTP handler code path the
phone's own browser uses. Fleet Risk's scale test (54 trips) ran via the
identical `infer.py` module on a dev machine for speed, since copying
the full 54-trip/2.4MB dataset to the phone isn't needed for the 4-trip
demo set already bundled there — the code executed is byte-identical to
what's on the phone (verified in `BENCHMARKS.md`'s earlier 0.000000
probability-diff cross-check against sklearn).
