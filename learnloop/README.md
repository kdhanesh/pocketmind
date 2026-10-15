# LearnLoop content pack

You asked for class 8-10, maths/science/social, "in all language." Per
PROOF_AND_PILOT_PLAN.md's own rule — "claim only languages that pass a
test sheet; add a language only after it passes" — this first pack ships
**English only**. That's not a scope cut, it's the honesty rule already
written into the project: Qwen2.5-1.5B is confirmed weak in Telugu, so any
non-English content here needs a native-speaker-checked test sheet before
the app is allowed to claim it. Building 30 untested Telugu chunks would
make the demo look broader than it's safe to claim.

**To add a language:** translate `content_en.md`'s chunks, run PROOF_AND_
PILOT_PLAN.md's test-sheet process (20 questions per language, answers
checked by a native speaker), and only then add `content_<lang>.md` and
list that language as supported in the app and in DPIIT_INNOVATION_NOTE.md
section A(d).

## How retrieval works

Same pattern as the advice bank: each `###` heading in `content_en.md` is
one retrieval chunk, tagged with `class`, `subject`, and `topic`. The
engine's retrieval step does keyword matching against the student's
question, pulls the best-matching chunk(s), and gives the SLM only that
content to explain/rephrase — never open-ended generation on a maths or
science fact, for the same hallucination-safety reason as the advice bank.

## Coverage in this first pack

A representative slice per class/subject, not a full syllabus — enough to
prove the retrieval → explain loop end to end for the demo. Expanding
topic coverage is pure content work from here, no engine changes needed.
