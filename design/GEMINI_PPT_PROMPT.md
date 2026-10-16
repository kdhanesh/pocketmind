Paste everything below this line into Gemini (or another model good at slide
generation) to get the DPIIT submission deck for PocketMind, VYOMAA LABS'
on-device AI suite. Every number, status, and claim below is real and final
— nothing here is a placeholder. Do not invent, round up, or soften any
figure; if something is marked "in progress," keep it marked that way.

---

I need a presentation deck (10-12 slides, 16:9) for a government (DPIIT)
startup submission and an investor-facing hackathon demo. The company is
**VYOMAA LABS**, the product is **PocketMind** — three on-device AI tools
(AgriLens, LearnLoop, Fleet Risk) that run a small, task-tuned language
model entirely on a mid-range Android phone, with zero cloud calls. Tone:
confident but honest — this is a real, working, physically-demoed product,
not a mockup, and the deck should read that way. Where something is still
in progress, say so plainly; don't claim it's finished.

**Tagline:** "AI in every hand, for a future-ready India."

## How to actually attach these (read this before the links)

Every link below is a real, live, publicly-reachable file on GitHub
Pages — confirmed working (HTTP 200, correct `image/png` / `video/mp4`
content-type) as of this writing. How you get each one into the deck
depends on the tool:

- **Google Slides** (if Gemini is generating/editing an actual Slides
  file): use **Insert → Image → By URL** and paste the PNG link directly
  — Slides fetches and embeds it, no download needed. The same works for
  a video via **Insert → Video → By URL** for the two mp4 links, though
  Slides video embeds work best with a YouTube/Drive URL rather than a
  raw mp4 link — if the direct URL doesn't embed cleanly, download the
  mp4 and re-upload it to Drive first, then insert from Drive.
- **Gemini chat without direct Slides access**: it may not reliably fetch
  a remote image URL on its own. The safe path is to download each PNG
  from the links below first, then attach the actual files in the chat
  so Gemini can see and place the real pixels — don't rely on it
  resolving the URL text alone.
- **Either way**, these are the exact, final images/videos to use — do
  not regenerate or re-describe them from the text alone if the tool can
  take the real file.

## Live links (use these directly — embed the screenshots, link the videos)

- **Product site (architecture, live demo recordings, full benchmarks):**
  https://kdhanesh.github.io/pocketmind/
- **Combined narrated walkthrough video (~3min, landscape, all 3 tools +
  architecture + business model + national mission + offline proof, voiced):**
  https://kdhanesh.github.io/pocketmind/media/demo-full-narrated.mp4
- **Per-tool raw screen recordings** (use these on the individual tool
  slides if you'd rather show the specific tool's own clip instead of the
  combined video):
  - AgriLens: https://kdhanesh.github.io/pocketmind/media/demo-agrilens.mp4
  - LearnLoop: https://kdhanesh.github.io/pocketmind/media/demo-learnloop.mp4
  - Fleet Risk: https://kdhanesh.github.io/pocketmind/media/demo-fleet.mp4
- **Screenshots** (use as static images wherever a slide needs a result
  visual instead of/alongside video):
  - Phone home screen: https://kdhanesh.github.io/pocketmind/media/home.png
  - AgriLens result (Tomato Septoria leaf spot, 100% confidence): https://kdhanesh.github.io/pocketmind/media/agrilens-result.png
  - LearnLoop result (Newton's second law, grounded answer): https://kdhanesh.github.io/pocketmind/media/learnloop-result.png
  - Fleet Risk dashboard (risk tiers, timeline, flagged events): https://kdhanesh.github.io/pocketmind/media/fleet-dashboard.png
  - Offline/airplane-mode proof (plane icon visible, WiFi off, correct answer): https://kdhanesh.github.io/pocketmind/media/airplane-proof.png

## Slide-by-slide content

**1. Cover**
"PocketMind" — VYOMAA LABS · DPIIT Submission. Subhead: "Three tools. One
phone. No signal required." Badges: "Zero cloud calls" / "0.5B params,
task-tuned layers" / "Airplane-mode verified". Use home.png as the hero
image.

**2. The core rule**
Statement slide: "The model is never allowed to invent a fact." Every tool
retrieves a verified note first, then lets the model only rephrase it in
plain language. If nothing verified matches, the tool refuses instead of
guessing. This is the one design decision everything else serves — a small
model will hallucinate a pesticide dose or a wrong formula if allowed to
generate freely, and that's real-world harm, not a demo glitch.

**3. How it works (architecture)**
Flow: Sensor input (photo / question / IMU stream) → Classifier or
retrieval (tiny offline model / keyword match) → Matched a verified entry?
→ YES: model rephrases the verified note only, cannot add new facts, shown
with confidence + timing → NO: "not confident enough," no guess given. No
embedding model, no vector index, no multi-agent framework — there isn't
RAM to spare for a second heavy process on a 3.5GB phone, and the real task
(one retrieval hop, one rephrase call) doesn't need one.

**4. The three tools**
- **AgriLens** — crop photo → disease ID → verified agronomy advice.
  Classifier numerically validated against the real model; piloting with
  **5 farmers** in the field. Embed agrilens-result.png and/or the AgriLens
  clip.
- **LearnLoop** — Class 8-10 question → grounded, plain-language
  explanation from verified study notes. Piloting with **10 students**.
  Embed learnloop-result.png and/or the LearnLoop clip.
- **Fleet Risk** — accelerometer trip data → two-stage offline risk
  classifier, **70% held-out accuracy**. Embed fleet-dashboard.png and/or
  the Fleet Risk clip.

**5. Who we build for (business model — be precise here, this is the
commercial story)**
- AgriLens and LearnLoop are **free** for individual farmers and students.
- For **schools**: LearnLoop is customized to that school's own syllabus
  and curriculum, acting as a first-hand mentor — not a generic chatbot.
- For **agribusiness** (companies running large farms / crop supply
  chains): a **paid, customized AgriLens** — VYOMAA LABS builds a new
  dataset and trains a model specific to the exact crop that company
  grows, then hands their farmer network a smart device tuned to it. This
  is a separate, paid offering, distinct from the free farmer tool.
- **Fleet Risk is closed-source by design** — a licensed product built to
  be sold into fleet-management and transportation/logistics companies
  only. Not free, not open, unlike the other two tools.

**6. Measured performance**
Device: Redmi 24116RNC1I, Android 16, arm64-v8a, 3.5GB RAM (~1.6GB
available at idle). Table: 1.5B-parameter baseline (42-84s/answer) vs.
0.5B parameters with task-tuned layers, the shipped default (15.3s
single-shot, 15-55s under load) — same quality, no loss found. Metrics:
35.0°C→34.0°C battery temp across a ~25-call stress run (no throttling),
~30-50MB RAM truly free with the model loaded, 99.997% AgriLens confidence
on a clean lab photo, 54ms for a full 1,034-row Fleet Risk trip replay.

**7. Hardened before it went near a demo**
Four real bugs found and fixed during adversarial testing on the live
phone: (1) AgriLens had no confidence floor — any image forced a
diagnosis, fixed with a 70% confidence gate; (2) LearnLoop's retrieval
could match on stopwords alone and let the model answer from its own
knowledge instead of refusing, fixed with stopword filtering; (3) a
path-traversal bug in Fleet Risk's trip selector, fixed with a directory
whitelist check; (4) AgriLens's multipart upload parser silently
truncated large photos whose binary bytes happened to contain the
boundary string, fixed by requiring the delimiter be preceded by its own
CRLF. One open item, tracked not hidden: LearnLoop's answer time drifts
from ~15s to 30-55s across repeated back-to-back questions (thermal
throttling ruled out).

**8. Deployment status, honestly — do not mark anything "complete" that
isn't**
| Component | Status | Detail |
|---|---|---|
| AgriLens field pilot | In progress | Piloting with 5 farmers, collecting real field photos |
| LearnLoop field pilot | In progress | Piloting with 10 students across Class 8-10 topics |
| Fleet Risk — database layer | **Complete** | On-device trip/event schema built and verified |
| Fleet Risk — vehicle hardware | In progress | Building up the on-vehicle sensor/IMU layer |
| Fleet Risk — cloud compute | In progress | AWS layer for fleet-wide aggregation being built |

End-to-end on the actual phone is done and confirmed — over WiFi and with
WiFi explicitly disabled plus airplane mode on, for all three tools. Use
airplane-proof.png here or on slide 11.

**9. Where latency is headed**
Current 15-55s answer times reflect an unoptimized pipeline, not a
ceiling. The model's own layers and the routing between retrieval and
generation are actively being tuned — newer quantization, decoding, and
routing algorithms and patterns are being tested now. Target: a couple of
seconds per answer, end to end, by the end of this year. Flag this
explicitly as a forward-looking engineering target, not a measured result.

**10. A better India ahead (mission + national alignment)**
Once the architecture layers, training process, and performance
benchmarks are finalized across sectors, the target is **100+
fully-trained, customized models** — each tuned to its own sector the way
AgriLens and LearnLoop already are — all runnable on any smartphone of
even the lowest practical configuration, so access is never gated by
hardware. This sits alongside work already underway nationally:
**Startup India / DPIIT recognition** (the basis of this filing), the
**IndiaAI Mission**'s push to democratize AI access, the **Digital
Agriculture Mission**'s use of AI and data analytics for farmer
advisories, and **PM eVidya**'s mandate under **NEP 2020** to reach
learners without reliable internet — the same problem LearnLoop was built
to solve. Be precise: VYOMAA LABS claims no formal affiliation with any of
these programs beyond DPIIT recognition itself — the point is shared
goals, not partnership.

**11. See it live (closing)**
Link to the product site (https://kdhanesh.github.io/pocketmind/) and the
combined narrated demo video (link above). Tagline: "VYOMAA LABS · AI in
every hand, for a future-ready India."

**12. Data sources & references (last slide — keep this as the final
slide, it's a citations/appendix slide, not a sales slide)**
| Claim | Source |
|---|---|
| AgriLens classifier | Numerically validated against a real torch model trained on the PlantVillage / "New Plant Diseases Dataset" lineage (spMohanty/PlantVillage-Dataset mirror) |
| Fleet Risk classifier | Kaggle "Harsh driving dataset" — 54 trips, ~33,000 rows, 44 training / 10 held-out |
| LearnLoop content | Original, self-authored notes — a representative slice of Class 8-10 topics, not a full official syllabus transcription |
| Latency / thermal / memory / accuracy | Measured directly on the physical Redmi 24116RNC1I this build targets — no laptop numbers presented as device numbers |
| Government scheme references | Public program descriptions, cited for mission alignment only — no formal affiliation claimed beyond DPIIT recognition itself |

## Things to get right (don't let the model drift on these)

- Never name the underlying base language model. Describe it only as "a
  0.5B-parameter model with task-tuned layers" or similar. This is
  deliberate — do not substitute a specific model/vendor name anywhere in
  the deck.
- Never claim Fleet Risk's hardware or cloud layer is done — both are
  explicitly "in progress." Only the database/schema layer is "complete."
- Never round the pilot numbers up or down — exactly 5 farmers, exactly 10
  students.
- Never claim formal government/program affiliation — alignment only,
  explicitly caveated, except for DPIIT recognition itself (which is real
  and is the basis of this filing).
- Keep the "Where latency is headed" numbers as a target/roadmap, not a
  measured result.
