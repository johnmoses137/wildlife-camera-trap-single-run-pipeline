# ===============================================================
# INHERIT METADATA FOR CROPPED IMAGES
# ===============================================================
# Cropped images don't need EXIF re-extraction.
# They inherit site, camera, timestamp, and cluster info
# from their parent image in meta_data_clustered.csv
# ===============================================================

from pathlib import Path
import pandas as pd


def inherit_metadata(
    cropped_csv: Path,
    original_meta_csv: Path,
    out_root: Path,
    crop_manifest_csv: Path = None
) -> Path:
    """
    Join cropped predictions with parent image metadata.
    Cropped image names follow pattern: originalname-det1.jpg
    Parent is identified by stripping -detN suffix.
    Returns path to cropped_predictions_with_metadata.csv
    """

    cropped  = pd.read_csv(cropped_csv, dtype=str)
    original = pd.read_csv(original_meta_csv, dtype=str)

    if crop_manifest_csv and Path(crop_manifest_csv).exists():
        manifest = pd.read_csv(crop_manifest_csv, dtype=str)
        manifest = manifest.rename(columns={"crop_image": "image"})
        cropped = cropped.merge(
            manifest,
            on="image",
            how="left"
        )
    else:
        # Fallback for older crop folders that do not have a manifest.
        cropped["parent_image"] = cropped["image"].str.replace(
            r"-det\d+\.\w+$", "", regex=True
        ) + "." + cropped["image"].str.split(".").str[-1]

    # Normalize keys for joining
    cropped["parent_key"] = cropped["parent_image"].str.strip().str.lower()
    original["key"]       = original["image"].str.strip().str.lower()

    # Metadata columns to inherit from parent
    META_COLS = [
        "site_id",
        "camera_id",
        "subfolder_token",
        "capture_ts",
        "capture_date",
        "cluster_id"
    ]

    # Only keep meta cols that actually exist in original
    available_meta = [c for c in META_COLS if c in original.columns]

    joined = cropped.merge(
        original[["key"] + available_meta],
        left_on="parent_key",
        right_on="key",
        how="left"
    ).drop(columns=["key", "parent_key"], errors="ignore")

    out = out_root / "cropped_predictions_with_metadata.csv"
    joined.to_csv(out, index=False)

    print(f" Metadata inherited for {len(joined)} cropped rows → {out.name}")
    return out
