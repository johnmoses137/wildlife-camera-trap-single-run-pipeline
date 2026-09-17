# ===============================================================
# PIPELINE RUNNER
# ===============================================================
# Orchestrates the full wildtrack pipeline end to end.
# This is the only file that knows the order of operations.
# ===============================================================

from pathlib import Path
import shutil
from dataclasses import replace
from config import Config

from pipeline.speciesnet_runner import run_speciesnet
from pipeline.json_to_csv import json_to_csv
from pipeline.annotate import annotate_images
from pipeline.group import group_by_species
from pipeline.visualize import create_visualizations
from pipeline.metadata import extract_metadata_and_cluster
from pipeline.crop import crop_detections
from pipeline.inherit_metadata import inherit_metadata
from pipeline.merge import merge_original_and_cropped


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def contains_images(folder: Path) -> bool:
    return any(
        p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        for p in folder.rglob("*")
    )


def has_direct_images(folder: Path) -> bool:
    return any(
        p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        for p in folder.iterdir()
    )


def discover_child_datasets(parent_dir: Path) -> list[Path]:
    """
    Find immediate child folders that should be processed as separate datasets.
    Example: animals/antelope, animals/badger, animals/bat.
    """
    datasets = []
    for child in sorted(parent_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name.endswith("-output"):
            continue
        if contains_images(child):
            datasets.append(child)
    return datasets


def discover_batch_datasets(parent_dir: Path) -> list[tuple[str, Path, bool]]:
    """
    Build the batch run list for a folder.
    - direct images in parent_dir become one dataset named after parent_dir
    - each immediate child folder with images becomes its own dataset
    """
    datasets = []
    if has_direct_images(parent_dir):
        datasets.append((parent_dir.name, parent_dir, False))

    datasets.extend(
        (child.name, child, True)
        for child in discover_child_datasets(parent_dir)
    )
    return datasets


def publish_final_output(result_csv: Path, config: Config) -> Path:
    if not config.final_output_path:
        return result_csv

    final_path = config.final_output_path
    if result_csv.resolve() != final_path.resolve():
        shutil.copy2(result_csv, final_path)
    return final_path


def run_batch_pipeline(config: Config):
    """
    Run one full pipeline per immediate child folder when the input folder is
    a parent collection such as animals/antelope, animals/badger, animals/bat.
    """
    images_dir = config.images_dir
    datasets = discover_batch_datasets(images_dir)

    if not datasets:
        return run_pipeline(config)

    if len(datasets) <= 1 and datasets[0][1] == images_dir:
        return run_pipeline(config)

    if config.final_output_path:
        raise ValueError(
            "Batch mode needs an output directory, not a single final CSV path."
        )

    config.output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" WILDTRACK BATCH PIPELINE STARTING")
    print("="*60)
    print(f" Parent folder : {images_dir}")
    print(f" Output folder : {config.output_dir}")
    print(f" Datasets found: {len(datasets)}")
    print("="*60)

    results = []
    failures = []

    for index, (dataset_name, dataset_dir, recursive_images) in enumerate(datasets, start=1):
        dataset_output = config.output_dir / f"{dataset_name}-output"
        dataset_config = replace(
            config,
            images_dir=dataset_dir,
            output_dir=dataset_output,
            final_output_path=None,
            recursive_images=recursive_images,
        )

        print("\n" + "#"*60)
        print(f" BATCH ITEM {index}/{len(datasets)}: {dataset_name}")
        print("#"*60)

        try:
            final_csv = run_pipeline(dataset_config)
            results.append({
                "dataset": dataset_name,
                "input": str(dataset_dir),
                "output_folder": str(dataset_output),
                "final_csv": str(final_csv),
                "status": "complete",
            })
        except Exception as exc:
            failures.append({
                "dataset": dataset_name,
                "input": str(dataset_dir),
                "output_folder": str(dataset_output),
                "error": str(exc),
                "status": "failed",
            })
            print(f"\n ERROR processing {dataset_name}: {exc}")

    summary_csv = config.output_dir / "batch_summary.csv"
    import pandas as pd
    pd.DataFrame(results + failures).to_csv(summary_csv, index=False)

    print("\n" + "="*60)
    print(" BATCH PIPELINE COMPLETE")
    print(f" Completed: {len(results)}")
    print(f" Failed   : {len(failures)}")
    print(f" Summary  : {summary_csv}")
    print("="*60)

    if failures:
        raise RuntimeError(
            f"Batch completed with {len(failures)} failed dataset(s). See {summary_csv}"
        )

    return summary_csv


def run_pipeline(config: Config):
    """
    Full pipeline from raw images to final merged CSV.
    """

    images_dir = config.images_dir
    out_root   = config.output_dir
    out_root.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" WILDTRACK PIPELINE STARTING")
    print("="*60)
    print(f" Input images : {images_dir}")
    print(f" Output folder: {out_root}")
    if config.final_output_path:
        print(f" Final CSV    : {config.final_output_path}")
    print(f" Country      : {config.country}")
    print(f" Cluster mins : {config.cluster_minutes}")
    print("="*60)

    # ----------------------------------------------------------
    # STAGE 1: ORIGINAL IMAGES
    # ----------------------------------------------------------

    # Step 1: Run SpeciesNet on original images
    print("\n[1/7] Running SpeciesNet on original images...")
    orig_json = run_speciesnet(
        images_dir,
        out_root,
        config.country,
        recursive=config.recursive_images
    )

    # Step 2: JSON → CSV
    print("\n[2/7] Converting predictions to CSV...")
    orig_csv = json_to_csv(orig_json, out_root, is_cropped=False)

    # Step 3: Annotate images
    print("\n[3/7] Annotating images with bounding boxes...")
    annotated_dir = annotate_images(
        images_dir,
        orig_json,
        out_root,
        recursive=config.recursive_images
    )

    # Step 4: Group by species
    print("\n[4/7] Grouping images by species...")
    grouped_dir = group_by_species(orig_csv, annotated_dir, out_root)

    # Step 5: Visualizations
    print("\n[5/7] Creating visualizations...")
    create_visualizations(grouped_dir, out_root)

    # Steps 6-7: Metadata + clustering
    print("\n[6/7] Extracting metadata and clustering by time...")
    meta_csv = extract_metadata_and_cluster(
        images_dir,
        orig_csv,
        out_root,
        config.cluster_minutes,
        recursive=config.recursive_images,
        site_id=config.site_id,
        camera_id=config.camera_id,
    )

    if not config.run_crops:
        final_path = publish_final_output(meta_csv, config)
        print("\n" + "="*60)
        print(" PIPELINE COMPLETE (crop processing skipped)")
        print(f" Final output: {final_path}")
        print("="*60)
        return final_path

    # ----------------------------------------------------------
    # STAGE 2: CROPPED IMAGES
    # ----------------------------------------------------------

    # Crop secondary detections
    print("\n[7/7] Processing secondary detections (crops)...")
    cropped_dir = crop_detections(
        orig_json,
        out_root,
        min_confidence=config.min_detection_confidence,
    )

    # Check if any crops were produced
    crops = list(cropped_dir.glob("*.jpg"))
    if not crops:
        final_path = publish_final_output(meta_csv, config)
        print(" No secondary detections found — skipping crop pipeline")
        print("\n" + "="*60)
        print(" PIPELINE COMPLETE (no crops)")
        print(f" Final output: {final_path}")
        print("="*60)
        return final_path

    # Run SpeciesNet on crops
    print("\n Running SpeciesNet on cropped images...")
    crop_json = run_speciesnet(cropped_dir, out_root / "crops", config.country)

    # JSON → CSV for crops
    crop_csv_dir = out_root / "crops"
    crop_csv = json_to_csv(crop_json, crop_csv_dir, is_cropped=True)

    # Inherit metadata from parent images
    crop_manifest = cropped_dir / "crop_manifest.csv"
    crop_meta_csv = inherit_metadata(crop_csv, meta_csv, crop_csv_dir, crop_manifest)

    # Final merge
    final_csv = merge_original_and_cropped(meta_csv, crop_meta_csv, out_root)
    final_path = publish_final_output(final_csv, config)

    print("\n" + "="*60)
    print(" PIPELINE COMPLETE")
    print(f" Final output: {final_path}")
    print("="*60)

    return final_path
