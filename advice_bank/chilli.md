# Chilli — advice bank

**Classifier status:** AgriLens's current classifier has no chilli-specific
training data. The closest class it can output is a bell-pepper proxy
(`Pepper,_bell___Bacterial_spot` / `Pepper,_bell___healthy`) — a related but
different species. Real chilli-specific disease detection (leaf curl virus,
thrips damage, anthracnose/die-back, powdery mildew) is **roadmap, not
shipped**. This file exists so the content is ready the moment real chilli
training photos exist; don't claim chilli-disease detection in a demo until
`classifier_label` lines below actually match something the model outputs.

---

### Pepper,_bell___Bacterial_spot (shown to users as "Chilli — Bacterial spot (pepper-family proxy)")
classifier_label: Pepper,_bell___Bacterial_spot

**What it looks like:** small, dark, water-soaked spots on leaves and
fruit, similar in appearance to tomato bacterial spot (same bacterial
genus affects both crops). Spreads in warm, wet weather and by handling
wet plants.

**General management:** same principles as tomato bacterial spot — avoid
overhead watering, remove infected material, avoid working in wet fields,
rotate out of the pepper/tomato family where severe. Confirm any
bactericide product/dose with your agriculture officer.

**Important honesty note for the app:** this result comes from a model
that was never shown an actual chilli photo during training — it is
answering "does this look like the bell-pepper disease pattern it knows,"
not "I recognize chilli." Always show this caveat alongside the result.

---

### Pepper,_bell___healthy (shown to users as "Chilli — looks healthy (pepper-family proxy)")
classifier_label: Pepper,_bell___healthy

**What it looks like:** uniform green leaf color, no spots or curling.

**General management:** No action needed, with the same proxy caveat as
above — a true chilli-trained model is needed before this is reliable
enough to publish an accuracy number.

---

## Reference only — not yet wired to the classifier

These are real, common chilli problems in Andhra Pradesh that a future,
properly trained classifier should cover. Listed here so the advice bank
is ready in advance, and so reviewers can see the roadmap is grounded in
the actual crop, not just the proxy.

### Chilli leaf curl virus (a major AP chilli problem)
Upward/downward curling of leaves, stunted plants, reduced yield. Spread by
whiteflies, not by touch. Management: control the whitefly vector (yellow
sticky traps, reflective mulch), remove infected plants early, use
resistant/tolerant varieties recommended by your local KVK. No chemical
cure exists once a plant is infected.

### Chilli thrips damage
Silvery/bronze streaking on leaves, upward leaf curling, distorted young
growth. Caused by thrips feeding, not a pathogen. Management: blue sticky
traps for monitoring, biological controls where available, confirm
insecticide choice locally (thrips are prone to resistance, so product
choice matters).

### Chilli die-back / fruit rot (anthracnose)
Sunken, dark, often ring-patterned lesions on fruit, and branch die-back
from the tip inward. Favors warm, humid weather. Management: remove and
destroy infected fruit/branches, avoid overhead irrigation, rotate crops,
confirm fungicide program with your agriculture officer.
