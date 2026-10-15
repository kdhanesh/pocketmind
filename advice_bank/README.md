# Advice bank — rules

This is the verified content PocketMind is allowed to draw from when it gives
agriculture or study advice. It exists because of one hard rule from
STRATEGY_AND_SUSTAINABILITY.md and PROOF_AND_PILOT_PLAN.md: **a 1.5B model
must never invent a pesticide name, a dose, or a fact. It may only select and
rephrase text that already lives in these files.**

How the engine uses this:
1. A classifier or a user question identifies a topic (e.g. "Tomato Early
   blight", or "Class 8 Maths — linear equations").
2. The retrieval step pulls the matching chunk(s) from these files — plain
   keyword/section match for now, not a trained embedding model (this is an
   old phone; a tiny retrieval step is worth less latency than it's worth in
   accuracy here, there isn't enough content yet to need a heavier method).
3. The SLM is given ONLY that chunk as context and told to explain it in
   plain language, in the user's language. It is not allowed to add any
   crop-protection fact that isn't already in the retrieved chunk.
4. Every answer the app shows ends with: **"Advice only. Confirm with your
   agriculture officer / KVK before acting."**

## Status of this content — read before trusting it in the field

This first pass was written by Claude (an AI assistant) from general,
widely-published agronomy knowledge (standard descriptions of these diseases
that appear across ICAR, state agricultural university extension
literature, and international plant-pathology references). It is **not yet
checked against ANGRAU or a local KVK**, and it deliberately contains **no
specific pesticide brand names and no exact doses** — only the kind of
general, non-prescriptive management guidance that's safe to show before
that verification happens. Treat every file here as a first draft. Before
any real farmer sees this content, a real agriculture officer needs to read
it and sign off line by line, per the project's own proof rules.

## Crop coverage vs. classifier coverage

AgriLens's current image classifier (`agrilens/classify.py`) is built on a
public MobileNetV2 checkpoint trained on the standard 38-class PlantVillage
set. It can recognize real disease classes for **tomato** and
**maize/corn**, but has **no chilli-specific training data** — the closest
available proxy class is "Pepper, bell," a different (though related)
species. So:

- `tomato.md` and `maize.md` — every disease listed has a matching
  classifier class, so the full photo → diagnosis → advice loop works today.
- `chilli.md` — written for completeness and for the DPIIT pitch (chilli is
  one of the three named crops), but the classifier can only say "pepper-
  family, bacterial spot" or "pepper-family, healthy" right now. Say so
  plainly in any demo: chilli-specific detection is roadmap, not shipped.
