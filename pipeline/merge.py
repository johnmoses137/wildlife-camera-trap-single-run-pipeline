# ===============================================================
# FINAL MERGE
# ===============================================================
# Merges original predictions with cropped predictions.
# Cropped rows are inserted immediately after their parent row.
# Cropped rows inherit all metadata from parent.
# ===============================================================

from pathlib import Path
import pandas as pd


def merge_original_and_cropped(
    original_meta_csv: Path,
    cropped_meta_csv: Path,
    out_root: Path
) -> Path:
    """
    Merge original and cropped prediction CSVs.
    Returns path to final merged CSV.
    """

    df_orig = pd.read_csv(original_meta_csv, dtype=str)
    df_crop = pd.read_csv(cropped_meta_csv, dtype=str)

    # Safety checks
    if "image" not in df_orig.columns:
        raise ValueError("Original CSV must contain 'image' column")
    if "image" not in df_crop.columns:
        raise ValueError("Cropped CSV must contain 'image' column")

    # Normalize join keys
    df_orig["__key__"] = df_orig["image"].str.strip().str.lower()

    if "parent_image" in df_crop.columns:
        df_crop["__parent_key__"] = df_crop["parent_image"].str.strip().str.lower()
    else:
        # Fallback for older crop CSVs that do not include crop_manifest data.
        df_crop["__parent_key__"] = (
            df_crop["image"]
            .str.replace(r"-det\d+\.\w+$", "", regex=True)
            .str.strip()
            .str.lower()
        ) + "." + df_crop["image"].str.split(".").str[-1].str.lower()

    # Metadata columns inherited from original
    META_COLS = [
        "site_id",
        "camera_id",
        "subfolder_token",
        "capture_ts",
        "capture_date",
        "cluster_id"
    ]

    # Prediction columns overwritten by cropped data
    PRED_COLS = [
        "filepath",
        "image",
        "no_of_detections",
        "label_hierarchy",
        "common_name",
        "prediction_score"
    ]

    # Group cropped rows by parent key for fast lookup
    crop_groups = df_crop.groupby("__parent_key__")

    merged_rows = []
    used_crops  = 0

    for _, orig_row in df_orig.iterrows():
        parent_key = orig_row["__key__"]

        # Always keep original row
        original_record = orig_row.drop("__key__").to_dict()
        original_record["record_type"] = "ORIGINAL"
        original_record["parent_image"] = ""
        original_record["detection_index"] = 0
        merged_rows.append(original_record)

        # Append cropped rows after parent if any exist
        if parent_key in crop_groups.groups:
            crops = crop_groups.get_group(parent_key)
            for _, crop_row in crops.iterrows():
                # Start from original row (inherits all metadata)
                merged = orig_row.to_dict()

                # Overwrite prediction fields with cropped data
                for col in PRED_COLS:
                    if col in crop_row.index:
                        merged[col] = crop_row[col]

                # Explicitly enforce metadata inheritance from parent
                for mcol in META_COLS:
                    merged[mcol] = orig_row.get(mcol)

                # Preserve the parent-child relationship for warehouse analytics
                merged["record_type"] = "CROP"
                merged["parent_image"] = crop_row.get("parent_image", orig_row.get("image"))
                merged["detection_index"] = crop_row.get("detection_index", "")

                merged.pop("__key__", None)
                merged_rows.append(merged)
                used_crops += 1

    merged_df = pd.DataFrame(merged_rows)

    out_csv = out_root / "final_merged_predictions.csv"
    merged_df.to_csv(out_csv, index=False)

    print(f"\n MERGE COMPLETE")
    print(f"   Original rows : {len(df_orig)}")
    print(f"   Cropped rows  : {len(df_crop)}")
    print(f"   Inserted crops: {used_crops}")
    print(f"   Final rows    : {len(merged_df)}")
    print(f"   Output        : {out_csv.name}")

    return out_csv
