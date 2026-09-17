# ===============================================================
# STEP 2: JSON TO CSV CONVERSION
# ===============================================================
# Converts SpeciesNet JSON predictions to structured CSV format
# ===============================================================

import os
import json
import re
import time
from pathlib import Path
import pandas as pd


def extract_common_name(label_hierarchy: str) -> str:
    if not label_hierarchy:
        return ""
    parts = [p.strip().lower() for p in label_hierarchy.split(";") if p.strip()]
    if not parts:
        return ""
    last = parts[-1]
    if last == "blank":
        return "blank"
    if re.fullmatch(r"[a-f0-9\-]+", last):
        for item in reversed(parts):
            if item not in {"blank", "animal"} and re.search(r"[a-z]", item):
                return item.title()
        return ""
    return last.title()


def json_to_csv(pred_json_path: Path, out_root: Path, is_cropped: bool = False) -> Path:
    """
    Convert SpeciesNet predictions JSON to CSV.
    is_cropped=True uses simplified schema (no categories/confidence_scores).
    """
    start = time.time()

    if not pred_json_path.exists():
        raise FileNotFoundError(f"Predictions JSON not found: {pred_json_path}")

    csv_path = out_root / "predictions.csv"

    with open(pred_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    preds = data.get("predictions", []) if isinstance(data, dict) else data
    if not preds:
        raise ValueError(f"No predictions found in {pred_json_path}")

    rows = []
    skipped = 0

    for p in preds:
        img_name = os.path.basename(p.get("filepath") or p.get("image") or "")

        if "checkpoint" in img_name.lower():
            skipped += 1
            continue

        dets = p.get("detections", []) or []
        label_h = str(p.get("prediction", "")).strip()

        if is_cropped:
            # Simplified schema for cropped images
            rows.append({
                "filepath": p.get("filepath") or p.get("image"),
                "image": img_name,
                "no_of_detections": len(dets),
                "label_hierarchy": label_h,
                "common_name": extract_common_name(label_h),
                "prediction_score": p.get("prediction_score", "")
            })
        else:
            # Full schema for original images
            rows.append({
                "filepath": p.get("filepath") or p.get("image"),
                "image": img_name,
                "no_of_detections": len(dets),
                "categories": ", ".join(str(d.get("label", "")).strip() for d in dets),
                "confidence_scores": ", ".join(f"{float(d.get('conf', 0) or 0):.3f}" for d in dets),
                "label_hierarchy": label_h,
                "common_name": extract_common_name(label_h),
                "prediction_score": p.get("prediction_score", "")
            })

    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f" JSON→CSV: {len(rows)} rows, {skipped} skipped → {csv_path.name}")
    return csv_path