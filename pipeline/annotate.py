# ===============================================================
# STEP 3: ANNOTATE IMAGES WITH BOUNDING BOXES
# ===============================================================
# Draws bounding boxes and species labels on original images
# ===============================================================

import json
import time
from pathlib import Path
import cv2


def annotate_images(
    images_dir: Path,
    pred_json_path: Path,
    out_root: Path,
    recursive: bool = True
) -> Path:
    """
    Draw bounding boxes and species labels on images.
    Returns path to annotated_images/ folder.
    """
    start = time.time()

    with open(pred_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    preds = data.get("predictions", [])
    if not preds:
        raise ValueError("No predictions found in JSON")

    annotated_dir = out_root / "annotated_images"
    annotated_dir.mkdir(parents=True, exist_ok=True)
    image_iter = images_dir.rglob("*") if recursive else images_dir.iterdir()
    image_lookup = {
        p.name.lower(): p
        for p in image_iter
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    }

    count = 0
    skipped = 0

    for pred in preds:
        raw_path = Path(pred.get("filepath", "") or pred.get("image", ""))
        fn = raw_path.name
        img_path = raw_path if raw_path.exists() else image_lookup.get(fn.lower())

        if not img_path or not img_path.exists():
            skipped += 1
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            skipped += 1
            continue

        h, w, _ = img.shape

        # Draw bounding boxes for each detection
        for det in pred.get("detections", []):
            bbox = det.get("bbox", [])
            conf = float(det.get("conf", 0) or 0)
            if len(bbox) == 4:
                x1 = int(bbox[0] * w)
                y1 = int(bbox[1] * h)
                x2 = x1 + int(bbox[2] * w)
                y2 = y1 + int(bbox[3] * h)

                # Red bounding box
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                # Confidence score above box
                cv2.putText(img, f"{conf:.2f}", (x1, max(0, y1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Species label at top of image
        label = (pred.get("prediction", "") or "").split(";")[-1]
        cv2.putText(img, label, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imwrite(str(annotated_dir / fn), img)
        count += 1

    print(f" Annotated {count} images ({skipped} skipped) → {annotated_dir.name}")
    return annotated_dir
