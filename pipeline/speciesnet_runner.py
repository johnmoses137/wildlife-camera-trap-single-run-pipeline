# ===============================================================
# SPECIESNET RUNNER
# ===============================================================
# Wraps the SpeciesNet model call as a subprocess.
# This is the adapter layer — only file that talks to SpeciesNet.
# ===============================================================

import subprocess
import sys
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def find_image_folders(images_dir: Path, recursive: bool = True) -> list[Path]:
    """
    Return every folder under images_dir that directly contains image files.
    This supports datasets shaped like:
        input/site/camera/images...
    instead of requiring all images to sit in the top-level input folder.
    """
    iterator = images_dir.rglob("*") if recursive else images_dir.iterdir()
    image_folders = {
        p.parent.resolve()
        for p in iterator
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    }
    return sorted(image_folders)


def run_speciesnet(
    images_dir: Path,
    output_dir: Path,
    country: str = None,
    recursive: bool = True
) -> Path:
    """
    Run SpeciesNet inference on a folder of images.
    Returns path to the predictions JSON file.
    """
    images_dir = Path(images_dir).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    image_folders = find_image_folders(images_dir, recursive=recursive)

    if not image_folders:
        raise ValueError(f"No image files found under: {images_dir}")

    # Output JSON named after the input folder
    json_filename = f"{images_dir.name}_predictions.json"
    pred_json = output_dir / json_filename

    # Use the same Python interpreter that's running this script
    python_exec = sys.executable

    cmd = [
        python_exec,
        "-m", "speciesnet.scripts.run_model",
        "--folders",
        *[str(folder) for folder in image_folders],
        "--predictions_json", str(pred_json),
        "--bypass_prompts",
        "--progress_bars"
    ]

    if country:
        cmd.extend(["--country", country])

    print(f"\n Running SpeciesNet on: {images_dir.name}")
    print(f" Image folders found: {len(image_folders)}")
    print(f" Country filter: {country or 'none'}")
    print(f" Output JSON: {pred_json}")

    proc = subprocess.run(cmd, capture_output=False, text=True)

    if proc.returncode != 0:
        raise RuntimeError(f"SpeciesNet failed with return code {proc.returncode}")

    if not pred_json.exists() or pred_json.stat().st_size == 0:
        raise RuntimeError(f"predictions JSON missing or empty: {pred_json}")

    print(f" SpeciesNet complete → {pred_json}")
    return pred_json
