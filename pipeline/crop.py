# ===============================================================
# CROP SECONDARY DETECTIONS
# ===============================================================
# Crops secondary detections (skips detection 0) from original
# images based on SpeciesNet bounding boxes
# ===============================================================

import json
import time
from pathlib import Path
import cv2
import pandas as pd


def crop_detections(
    pred_json_path: Path,
    out_root: Path,
    min_confidence: float = 0.1,
) -> Path:
    """
    Crop secondary detections from original images.
    Skips detection index 0 (primary detection).
    Returns path to cropped_images/ folder.
    """
    start = time.time()

    with open(pred_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    predictions = data.get("predictions", data)
    cropped_dir = out_root / "cropped_images"
    cropped_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = []

    total_crops = 0
    total_images = 0

    items = (
        predictions.values()
        if isinstance(predictions, dict)
        else predictions
    )

    for item in items:
        detections = item.get("detections", [])
        filepath   = item.get("filepath")

        if not detections or not filepath:
            continue

        img_path = Path(filepath)
        if not img_path.exists():
            continue

        image = cv2.imread(str(img_path))
        if image is None:
            continue

        total_images += 1
        h_img, w_img = image.shape[:2]
        image_stem   = img_path.stem

        # Skip detection 0, crop from index 1 onwards
        for i, det in enumerate(detections):
            if i == 0:
                continue

            confidence = float(det.get("conf", 0) or 0)
            if confidence < min_confidence:
                continue

            bbox = det.get("bbox")
            if not bbox or len(bbox) != 4:
                continue

            # bbox = [x_min, y_min, width, height] normalized
            x1 = int(bbox[0] * w_img)
            y1 = int(bbox[1] * h_img)
            x2 = int((bbox[0] + bbox[2]) * w_img)
            y2 = int((bbox[1] + bbox[3]) * h_img)

            # Clip to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_img, x2), min(h_img, y2)

            if x2 <= x1 or y2 <= y1:
                continue

            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            crop_filename = f"{image_stem}-det{i}.jpg"
            cv2.imwrite(str(cropped_dir / crop_filename), crop)
            manifest_rows.append({
                "crop_image": crop_filename,
                "crop_filepath": str(cropped_dir / crop_filename),
                "parent_image": img_path.name,
                "parent_filepath": str(img_path),
                "detection_index": i,
                "bbox_x": bbox[0],
                "bbox_y": bbox[1],
                "bbox_width": bbox[2],
                "bbox_height": bbox[3],
                "detection_confidence": confidence,
                "detection_label": det.get("label", ""),
            })
            total_crops += 1

    manifest_path = cropped_dir / "crop_manifest.csv"
    manifest_columns = [
        "crop_image", "crop_filepath", "parent_image", "parent_filepath",
        "detection_index", "bbox_x", "bbox_y", "bbox_width", "bbox_height",
        "detection_confidence", "detection_label",
    ]
    pd.DataFrame(manifest_rows, columns=manifest_columns).to_csv(
        manifest_path, index=False
    )

    print(
        f" Cropped {total_crops} detections from {total_images} images "
        f"(confidence >= {min_confidence:.3f}) → {cropped_dir.name}"
    )
    print(f" Crop manifest saved → {manifest_path.name}")
    return cropped_dir
