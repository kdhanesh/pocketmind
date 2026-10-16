Paste everything below this line into Gemini to UPDATE the existing,
already-finalized deck — do not generate a new deck from scratch, and do
not restructure, reorder, or drop any slide. This follows the exact
12-slide structure of "VYOMAA LABS: DPIIT Pitch Deck (Organic Edition)"
(https://docs.google.com/presentation/d/13vPrO6XfPPWv616wJdMI6rtM0uK-SozCumnN1YnXtIk/edit),
slide by slide, filling in only what was left as a `[CONFIRM: ...]`
placeholder, with real, final values. Everything else in the deck —
wording, tone, layout, the stats already sourced on slide 10 — stays as
it is. One new slide (13, References) is added at the very end.

Where something still cannot be confirmed (team names, a specific pilot
location, the IndiaAI Innovation Challenge status, the AP airports/freight
agent system's own data), it is marked **STILL NEEDS YOUR INPUT** below —
do not invent a value for these, leave the placeholder as-is or ask the
deck owner.

---

## ⚠️ One real mismatch to resolve first — read before editing slide 3

Slide 3 ("HOW IT WORKS") describes a language layer — "Speak or type in
an Indian language → Detect language → Translate in → Small model
answers → Translate back" — and asks to confirm which languages are
supported ("e.g. Telugu, Hindi, English"). **This does not exist in the
actual shipped build.** The real PocketMind engine today is English-only
(LearnLoop's content pack is English, Class 8-10; there is no language
detection or translation step anywhere in `engine/`). This is not a
placeholder to fill in with a plausible-sounding list of languages — it
would be a false claim in a government filing.

Two honest ways to resolve it, your call:
- **(a)** Keep the language-layer diagram but relabel it as a roadmap
  item — move it under "Next" language, not "Today," and do not name any
  specific language as tested.
- **(b)** Remove the language-layer diagram from this slide for now and
  replace it with the actual architecture that IS shipped: retrieval
  first, then the model only rephrases the verified note (see the real
  flow below, under slide 3's fill).

Do not silently pick (a) and move on — flag this choice back to whoever
is finalizing the deck.

## Live links and files

Every file below is a real, local file at the path given, inside this
repo's `design/demo-media/` folder — **attach these directly as files**
when pasting into Gemini; don't rely on it fetching a URL. The same
filenames (hyphenated instead of underscored) are also live on the
website if a tool supports Insert Image/Video → By URL (Google Slides
does): `https://vyomaalabs.github.io/pocketmind/media/<hyphenated-name>`.

- **Product site:** https://vyomaalabs.github.io/pocketmind/

- **Combined narrated demo video** (~3 min, landscape, all three tools +
  architecture + business model + national mission + offline proof,
  voiced): `design/demo-media/demo_full_narrated.mp4`

- **Per-tool demo clips — trimmed, loading time cut, result held ~5s**
  (use these on slide 5 and slide 9; each is also available as an
  animated GIF for slides/tools that don't embed video):
  - AgriLens: `design/demo-media/demo_agrilens.mp4` (video, 8.5s) /
    `design/demo-media/demo-agrilens.gif` (GIF, same content)
  - LearnLoop: `design/demo-media/demo_learnloop.mp4` (video, 8.5s,
    shows "What is Newton's second law of motion" start to finish) /
    `design/demo-media/demo-learnloop.gif` (GIF, same content)
  - Fleet Risk: `design/demo-media/demo_fleet.mp4` (video, 7.2s) /
    `design/demo-media/demo-fleet.gif` (GIF, same content)
  - If the slide tool supports an embedded, auto-playing video, prefer
    the `.mp4`; use the `.gif` only where the tool can't embed video
    (e.g. a plain image placeholder, or a PDF export).

- **Screenshots — all in `design/demo-media/`:**
  - `home.png` — phone home screen (slide 1)
  - `agrilens-result.png` — full AgriLens result, Tomato Septoria leaf
    spot, 100% confidence (slide 5)
  - `learnloop-result.png` — top of the LearnLoop result: question,
    matched note, intro text, and the formula rendered as `F = ma`
    (slide 5, first of a pair)
  - `learnloop-result-2.png` — same answer scrolled further, showing
    the full step-by-step explanation (slide 5, second of the pair —
    LearnLoop's answer is long enough that one screenshot can't show
    it all; use both side by side, not just the first)
  - `fleet-dashboard.png` — full Fleet Risk dashboard: risk-tier tiles,
    timeline, flagged events (slide 5 or 9)
  - `airplane-proof.png` — airplane-mode proof, plane icon visible,
    WiFi confirmed off, correct grounded answer (slide 9)

- **QR code for "Watch the demo" (slide 9):** no QR generator is
  available in this environment — generate one from the narrated-video
  URL above using any QR tool (e.g. qr-code-generator.com) and paste the
  image in.

## Slide-by-slide fills

**Slide 1 — Cover.** No placeholder to fill. Unchanged.

**Slide 2 — THE PROBLEM.** No placeholder to fill. The stats here
(UDISE+ 63.5%, Agriculture Census 86%) are already sourced — carry their
citations forward to the new References slide (13), don't duplicate them
inline.

**Slide 3 — HOW IT WORKS.** Resolve the language-layer mismatch above
first. The actual shipped architecture, if you go with option (b):
"Every request is matched against verified, pre-written content first.
Only if there's a confident match does the model rephrase that note in
plain language — it is never allowed to invent a fact. If nothing
matches, the tool says so instead of guessing." No language has been
tested/confirmed beyond English — do not name Telugu or Hindi as
supported.

**Slide 4 — THE PLATFORM.** No placeholder to fill. Matches the real
build: AgriLens and LearnLoop are "Now," Edge fleet unit (Fleet Risk) is
also real and running today, not just "Next" — it replays real trip data
through a two-stage offline classifier live on-device (70% held-out
accuracy). Consider moving "Edge fleet unit / Vehicle safety" from "Next"
to "Now" alongside AgriLens and LearnLoop, since it's built and running,
even though vehicle hardware integration and the cloud layer are still
in progress. EcoTrace and MedNotes stay "Next" — nothing built yet.

**Slide 5 — FIRST PRODUCTS.**
- AgriLens stage: **prototype, in field pilot — 5 farmers.** Not yet
  "field-tested" to completion; honestly "prototype" with a pilot
  underway.
- LearnLoop stage: **prototype, in field pilot — 10 students** across
  Class 8-10 topics.
- Replace "Illustrative screens" with the real screenshots:
  `agrilens-result.png` (shows the real Tomato Septoria leaf spot
  result, 100% confidence) and `learnloop-result.png` (real grounded
  Newton's-second-law answer). Airplane-mode icon is visible in the real
  LearnLoop screenshot too, if you want one image to carry both the
  product and the offline claim.

**Slide 6 — FLEETS AND NEXT SECTORS.**
- Edge AI fleet unit stage: **prototype — not yet in pilot with a named
  fleet.** The model runs live on-device against recorded trip data
  (70% held-out accuracy, 54ms for a full ~1,000-row trip replay); the
  on-vehicle sensor/IMU hardware and the AWS cloud-aggregation layer are
  both still in progress. Do not claim a named fleet pilot — there isn't
  one yet.
- MedNotes and EcoTrace: no change, both still "Next," nothing to fill.

**Slide 7 — ENGINEERING METHOD.** No placeholder to fill. Unchanged.

**Slide 8 — WHY WE ARE DIFFERENT.** No placeholder to fill. Unchanged.
("Verified agents" / "refusal of unverified numbers" already matches the
real confidence-gating and retrieval-precision fixes documented in
`BATTLE_TEST_REPORT.md`.)

**Slide 9 — PROOF AND TRACTION.**
- Screenshots: use `fleet-dashboard.png` (the real risk-tier/timeline/
  event-card dashboard) for "dashboard," and `airplane-proof.png` (plane
  icon visible, WiFi confirmed off, correct grounded answer in 55.5s)
  for "phone in airplane mode." **STILL NEEDS YOUR INPUT:** "agent
  trace" screenshot — this refers to the separate AP airports/freight
  agent system, not PocketMind; pull that screenshot from that project,
  not from this repo.
- "PocketMind on a phone, offline": model = **a 0.5B-parameter model
  with task-tuned layers** (never name the specific base model/vendor —
  deliberate, keep consistent with the rest of this deck's wording);
  phone = **Redmi 24116RNC1I**; demo recorded in airplane mode =
  **confirmed, yes** (WiFi explicitly disabled at the radio, not just the
  airplane-mode toggle — see `BATTLE_TEST_REPORT.md` for the exact
  verification method).
- "Agriculture field work": **5 farmers**, piloting AgriLens. **STILL
  NEEDS YOUR INPUT:** where (district/state) — not something this repo
  has; fill in from whoever is running the pilot.
- "IndiaAI Innovation Challenge [CONFIRM status: RTGS x Govt. of Andhra
  Pradesh]": **STILL NEEDS YOUR INPUT** — this repo has no data on this
  challenge's status; do not guess or imply a status wasn't confirmed.
- "Watch the demo": link is the narrated video URL above; QR code to be
  generated separately (see "Live links and files").

**Slide 10 — MARKET SCOPE.** No placeholder to fill — already real,
already sourced (IAMAI 2025, UDISE+ 2024-25, Agriculture Census
2015-16, Brickwork 2024). Carry these four citations into slide 13.

**Slide 11 — BUSINESS MODEL.** No placeholder to fill — this is already
the real, correct model: free/low-cost direct to individuals, paid at
the institution level. Keep it exactly as written:
- Schools and universities: per-seat/per-institution LearnLoop licences.
- Agri co-ops and FPOs: farmer advisory subscriptions, local
  crop-knowledge packs. (Individual farmers themselves still get
  AgriLens access at no cost — the co-op/FPO layer is what's paid.)
- Commercial fleets: edge hardware unit + per-vehicle monthly
  subscription.
- Developers/OEMs: PocketMind SDK licence + domain model packs.
- Governments: deployment, localisation, citizen-service contracts.
- Clinics (next): MedNotes licence per practitioner.

**Slide 12 — ROADMAP AND ASK.**
- Team: **STILL NEEDS YOUR INPUT** — partner names/roles are personal
  information this repo has no record of; fill in directly, don't guess.
- DPIIT ask: no placeholder, already correct — Startup India benefits,
  government procurement/grant access, IP support.
- Roadmap milestones: no placeholder to fill, already real and
  consistent with where things actually stand (0-3 months: harden +
  launch site — the site is in fact already live at the link above, so
  that part of month 0-3 is done; 3-6 months: pilots — AgriLens and
  LearnLoop pilots are already underway at 5 farmers / 10 students, so
  note that as ahead of schedule if accurate).

## New slide 13 — References (add at the very end)

A citations/appendix slide, not a sales slide. Combine the four sources
already used on slide 10 with the sources behind this repo's own
numbers:

| Claim | Source |
|---|---|
| 958M active internet users in India, ~548M (57%) rural | IAMAI, 2025 |
| 14.7 lakh schools, 63.5% with internet | UDISE+ 2024-25 |
| 14.6 crore operational farm holdings, 86% small/marginal | Agriculture Census 2015-16 |
| 7.4M commercial vehicles, ~3.5M with telematics | Brickwork, 2024 |
| AgriLens classifier | Numerically validated against a real torch model trained on the PlantVillage / "New Plant Diseases Dataset" lineage (spMohanty/PlantVillage-Dataset mirror) |
| Fleet Risk classifier | Kaggle "Harsh driving dataset" — 54 trips, ~33,000 rows, 44 training / 10 held-out |
| LearnLoop content | Original, self-authored notes — a representative slice of Class 8-10 topics, not a full official syllabus transcription |
| Latency/thermal/memory/accuracy figures | Measured directly on the physical Redmi 24116RNC1I this build targets — no laptop numbers presented as device numbers |

## Things to get right (don't let the model drift on these)

- Never name the underlying base language model anywhere in the deck —
  "a 0.5B-parameter model with task-tuned layers" only.
- Never claim a named fleet pilot, a confirmed language beyond English,
  or an IndiaAI Challenge status — these are explicitly unconfirmed;
  leave them flagged, not filled with a guess.
- Keep the pilot numbers exact: 5 farmers, 10 students. Don't round.
- Don't touch the AP airports/freight agent system's own claims (slide
  9) — that's a different project; this repo has no data to update it.
- Don't restructure the 12 real slides or change their order; only add
  slide 13 after them.
