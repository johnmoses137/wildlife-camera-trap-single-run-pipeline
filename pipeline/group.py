# ===============================================================
# STEP 4: GROUP ANNOTATED IMAGES BY SPECIES
# ===============================================================
# Organizes annotated images into species-specific folders
# ===============================================================

import shutil
import time
from pathlib import Path
import pandas as pd


def group_by_species(csv_path: Path, annotated_dir: Path, out_root: Path) -> Path:
    """
    Copy annotated images into species-named subfolders.
    Folders are renamed to include count: e.g. 'Deer (45)'
    Returns path to Grouped_Images/ folder.
    """
    start = time.time()

    df = pd.read_csv(csv_path)
    grouped = out_root / "Grouped_Images"
    grouped.mkdir(parents=True, exist_ok=True)

    counts = {}

    for _, row in df.iterrows():
        img = str(row.get("image", "")).strip()
        sp  = str(row.get("common_name", "")).strip()

        if not img or not sp:
            continue

        src = annotated_dir / img
        if not src.exists():
            continue

        dst_dir = grouped / sp
        dst_dir.mkdir(exist_ok=True)

        counts[sp] = counts.get(sp, 0) + 1
        dst_img = dst_dir / f"{sp}_{counts[sp]:03d}_{img}"
        shutil.copy2(src, dst_img)

    # Rename folders to include count
    for sp, c in counts.items():
        src_dir = grouped / sp
        dst_dir = grouped / f"{sp} ({c})"
        if src_dir.exists() and not dst_dir.exists():
            src_dir.rename(dst_dir)

    total = sum(counts.values())
    print(f" Grouped {total} images into {len(counts)} species folders → {grouped.name}")
    return grouped