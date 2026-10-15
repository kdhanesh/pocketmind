"""AgriLens crop-disease classifier -- pure numpy + Pillow, no torch/TFLite/ONNX.

Runs a MobileNetV2 (38-class PlantVillage head) entirely in numpy, so it works
inside Termux on an old Android phone with nothing but `pip install numpy pillow`.

Usage:
    python3 classify.py <image.jpg>

As a library:
    from classify import classify
    result = classify("leaf.jpg")
"""
import json
import sys
import os
import numpy as np
from PIL import Image

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Full 38-class PlantVillage head (verified against the real torch model --
# see NOTES.md). We keep all 38 because the model's softmax needs the full
# head; the product only acts on the 3 target crops below.
CLASS_NAMES = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
    "Blueberry___healthy", "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot_Gray_leaf_spot", "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight", "Corn_(maize)___healthy",
    "Grape___Black_rot", "Grape___Esca_(Black_Measles)", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy", "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot", "Tomato___Spider_mites_Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus", "Tomato___healthy",
]
assert len(CLASS_NAMES) == 38

# Target crops for the AgriLens product. "chilli" is NOT a real class in this
# model -- there is no chilli-specific training data here. We map it onto
# "Pepper,_bell" (bell pepper), the closest taxonomic relative (both Capsicum),
# as an explicit PROXY. Treat any chilli prediction as low-confidence until the
# team's own chilli field photos are collected and the model is fine-tuned or
# re-validated on them -- see PROOF_AND_PILOT_PLAN.md's caution about
# PlantVillage lab photos vs real field photos.
CROP_OF_CLASS = {}
for i, name in enumerate(CLASS_NAMES):
    if name.startswith("Tomato___"):
        CROP_OF_CLASS[i] = "tomato"
    elif name.startswith("Corn_(maize)___"):
        CROP_OF_CLASS[i] = "maize"
    elif name.startswith("Pepper,_bell___"):
        CROP_OF_CLASS[i] = "chilli (proxy: bell pepper model, not chilli-trained)"

_MODEL = None  # lazy-loaded singleton


def _get_model():
    global _MODEL
    if _MODEL is None:
        from mnv2_numpy import MobileNetV2Numpy
        here = os.path.dirname(os.path.abspath(__file__))
        _MODEL = MobileNetV2Numpy(os.path.join(here, "mobilenetv2_plant.npz"))
    return _MODEL


def _load_image(path, resize_size=256, crop_size=224):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if w < h:
        new_w, new_h = resize_size, round(h * resize_size / w)
    else:
        new_h, new_w = resize_size, round(w * resize_size / h)
    img = img.resize((new_w, new_h), Image.BILINEAR)

    left = (new_w - crop_size) // 2
    top = (new_h - crop_size) // 2
    img = img.crop((left, top, left + crop_size, top + crop_size))

    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = (arr - MEAN) / STD
    return arr.transpose(2, 0, 1).astype(np.float32)


def _softmax(logits):
    e = np.exp(logits - logits.max())
    return e / e.sum()


def classify(image_path):
    model = _get_model()
    x = _load_image(image_path)
    logits = model(x)
    probs = _softmax(logits)

    order = np.argsort(probs)[::-1]
    top1 = int(order[0])
    top3 = [
        {"class_name": CLASS_NAMES[i], "confidence": float(probs[i])}
        for i in order[:3]
    ]

    return {
        "class_name": CLASS_NAMES[top1],
        "crop": CROP_OF_CLASS.get(top1, "other (not a target crop for this product)"),
        "confidence": float(probs[top1]),
        "top3": top3,
        "is_target_crop": top1 in CROP_OF_CLASS,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 classify.py <image.jpg>", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(classify(sys.argv[1]), indent=2))
