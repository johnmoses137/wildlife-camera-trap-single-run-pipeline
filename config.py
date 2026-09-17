# ===============================================================
# WILDTRACK CONFIGURATION
# ===============================================================
# All user-configurable settings in one place.
# Users can change these defaults here or override via main.py
# ===============================================================

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def clean_path(value: str) -> str:
    """Remove surrounding quotes that are often pasted with macOS paths."""
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


@dataclass
class Config:
    # --- Required inputs (set by user at runtime) ---
    images_dir: Path = None          # Path to original input images
    output_dir: Path = None          # Working/output folder for all pipeline files
    final_output_path: Optional[Path] = None  # Optional exact CSV path requested by user

    # --- SpeciesNet settings ---
    country: Optional[str] = None    # Optional country code for SpeciesNet model

    # --- Clustering settings ---
    cluster_minutes: int = 5         # Time gap (minutes) to split wildlife events
    site_id: Optional[str] = None    # Optional explicit site identifier
    camera_id: Optional[str] = None  # Optional explicit camera identifier

    # --- Processing flags ---
    run_crops: bool = True           # Whether to run secondary detection cropping
    recursive_images: bool = True    # Whether to include images inside nested folders
    min_detection_confidence: float = 0.1  # Minimum confidence for secondary crops


def get_config(images_dir: str, output_dir: str,
               country: Optional[str] = None, cluster_minutes: int = 5,
               run_crops: bool = True,
               recursive_images: bool = True,
               min_detection_confidence: float = 0.1,
               site_id: Optional[str] = None,
               camera_id: Optional[str] = None) -> Config:
    images_dir = clean_path(images_dir)
    output_dir = clean_path(output_dir)

    output_path = Path(output_dir).expanduser().resolve()
    final_output_path = output_path if output_path.suffix.lower() == ".csv" else None
    working_output_dir = output_path.parent if final_output_path else output_path

    return Config(
        images_dir=Path(images_dir).expanduser().resolve(),
        output_dir=working_output_dir,
        final_output_path=final_output_path,
        country=country.strip().upper() if country else None,
        cluster_minutes=cluster_minutes,
        run_crops=run_crops,
        recursive_images=recursive_images,
        min_detection_confidence=min_detection_confidence,
        site_id=site_id.strip() if site_id else None,
        camera_id=camera_id.strip() if camera_id else None,
    )
