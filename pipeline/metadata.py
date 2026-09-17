# ===============================================================
# STEPS 6-7: EXTRACT METADATA AND CLUSTER BY TIME
# ===============================================================
# Extracts EXIF metadata from images and groups detections
# into temporal clusters (wildlife events)
# ===============================================================

import time
from pathlib import Path
import pandas as pd
import exifread
from tqdm import tqdm


def normalize(s):
    """Normalize filename for joining: remove path, lowercase."""
    return Path(str(s)).name.lower()


def extract_exif(p: Path) -> dict:
    """Extract EXIF metadata from a single image file."""
    d = {"FileName": p.name}
    try:
        with open(p, "rb") as f:
            tags = exifread.process_file(f, details=False)
        for k, v in tags.items():
            key = k.split()[-1]
            if key == "JPEGThumbnail":
                continue  # skip large binary thumbnail data
            d[key] = str(v)
    except Exception:
        pass

    # Filesystem timestamp fallback
    try:
        d["FileModifyDate"] = pd.to_datetime(p.stat().st_mtime, unit="s")
    except Exception:
        d["FileModifyDate"] = pd.NaT

    return d


def extract_metadata_and_cluster(
    images_dir: Path,
    pred_csv: Path,
    out_root: Path,
    cluster_minutes: int = 5,
    recursive: bool = True,
    site_id: str = None,
    camera_id: str = None,
) -> Path:
    """
    Join predictions with EXIF metadata and apply time-based clustering.
    Returns path to meta_data_clustered.csv
    """
    start = time.time()

    # --- Extract site/camera IDs from folder structure ---
    parents = images_dir.parents
    SITE_ID = site_id or (parents[1].name if len(parents) >= 2 else parents[0].name)
    CAMERA_ID = camera_id or parents[0].name
    SUBFOLDER = images_dir.name

    # --- Extract EXIF from all images ---
    image_iter = images_dir.rglob("*") if recursive else images_dir.iterdir()
    image_files = [
        p for p in image_iter
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    print(f" Extracting EXIF from {len(image_files)} images...")
    meta = pd.DataFrame([extract_exif(p) for p in tqdm(image_files)])

    if meta.empty:
        raise ValueError(f"No images found in {images_dir}")

    meta["__key__"]        = meta["FileName"].map(normalize)
    meta["site_id"]        = SITE_ID
    meta["camera_id"]      = CAMERA_ID
    meta["subfolder_token"] = SUBFOLDER

    # --- Load predictions CSV ---
    pred = pd.read_csv(pred_csv, dtype=str)
    pred["__key__"]        = pred["image"].map(normalize)
    pred["site_id"]        = SITE_ID
    pred["camera_id"]      = CAMERA_ID
    pred["subfolder_token"] = SUBFOLDER

    # --- Merge predictions with metadata ---
    joined = pred.merge(
        meta,
        on=["__key__", "site_id", "camera_id", "subfolder_token"],
        how="left"
    )

    # --- Resolve timestamps (priority order) ---
    joined["capture_ts"]       = pd.NaT
    joined["timestamp_source"] = None

    for col in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
        if col in joined.columns:
            # Camera EXIF timestamps normally use YYYY:MM:DD HH:MM:SS, which
            # pandas does not reliably recognize as a general mixed format.
            ts = pd.to_datetime(
                joined[col], errors="coerce", format="%Y:%m:%d %H:%M:%S"
            )
            unresolved = ts.isna() & joined[col].notna()
            if unresolved.any():
                ts.loc[unresolved] = pd.to_datetime(
                    joined.loc[unresolved, col], errors="coerce", format="mixed"
                )
            # Reject anything outside pandas' valid datetime64[ns] range
            min_ts = pd.Timestamp.min
            max_ts = pd.Timestamp.max
            ts = ts.where((ts >= min_ts) & (ts <= max_ts))
            mask = joined["capture_ts"].isna() & ts.notna()
            joined.loc[mask, "capture_ts"]       = ts[mask]
            joined.loc[mask, "timestamp_source"] = col

    if "FileModifyDate" in joined.columns:
        ts   = pd.to_datetime(joined["FileModifyDate"], errors="coerce")
        mask = joined["capture_ts"].isna() & ts.notna()
        joined.loc[mask, "capture_ts"]       = ts[mask]
        joined.loc[mask, "timestamp_source"] = "FileModifyDate"

    if joined["capture_ts"].isna().all():
        raise ValueError("No valid timestamps found in EXIF or filesystem metadata")

    joined["capture_ts"]   = pd.to_datetime(joined["capture_ts"], errors="coerce")
    joined["capture_date"] = joined["capture_ts"].dt.date

    # --- Time-based clustering ---
    joined = joined.sort_values(["site_id", "camera_id", "capture_ts"])

    gap = (
        joined
        .groupby(["site_id", "camera_id"])["capture_ts"]
        .diff()
        .dt.total_seconds()
        .div(60)
    )

    joined["cluster_id"] = (gap.isna() | (gap > cluster_minutes)).cumsum()

    # --- Save output ---
    out_csv = out_root / "meta_data_clustered.csv"
    joined.drop(columns=["__key__"], errors="ignore").to_csv(out_csv, index=False)

    print(f" Metadata + clustering complete → {out_csv.name}")
    return out_csv
