# ===============================================================
# WILDTRACK - WILDLIFE CAMERA TRAP ANALYSIS TOOL
# ===============================================================
# Single entry point for the full pipeline.
# Run this file to process your camera trap images.
#
# USAGE:
#   python3 main.py
# ===============================================================

import argparse

from pipeline.run_metrics import RunMetrics
from config import get_config
from pipeline.runner import run_batch_pipeline, run_pipeline


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the full WildTrack camera trap pipeline."
    )
    parser.add_argument(
        "--images",
        help="Path to the folder containing original camera trap images.",
    )
    parser.add_argument(
        "--output",
        help="Output folder or exact final CSV path, for example /tmp/results.csv.",
    )
    parser.add_argument(
        "--country",
        default=None,
        help="Optional country code passed to SpeciesNet, for example USA or KEN.",
    )
    parser.add_argument(
        "--cluster-minutes",
        type=int,
        default=5,
        help="Minutes between captures before starting a new event cluster. Default: 5.",
    )
    parser.add_argument(
        "--skip-crops",
        action="store_true",
        help="Only run the original-image pass and skip secondary crop processing.",
    )
    parser.add_argument(
        "--single-folder",
        action="store_true",
        help="Force one combined run for the input folder instead of batch-running child folders.",
    )
    parser.add_argument(
        "--min-detection-confidence",
        type=float,
        default=0.1,
        help="Minimum detector confidence for secondary crops. Default: 0.1.",
    )
    parser.add_argument(
        "--site-id",
        default=None,
        help="Optional site identifier. Overrides folder-based inference.",
    )
    parser.add_argument(
        "--camera-id",
        default=None,
        help="Optional camera identifier. Overrides folder-based inference.",
    )
    return parser


def main():
    print("\n" + "="*60)
    print("   WILDTRACK - Wildlife Camera Trap Analysis Tool")
    print("="*60)

    args = build_parser().parse_args()

    # --- Get inputs from user if not provided on command line ---
    images_dir = args.images or input("\n Enter path to input images folder: ").strip()
    output_dir = args.output or input(" Enter output folder or final CSV path: ").strip()

    # --- Build config with defaults ---
    config = get_config(
        images_dir=images_dir,
        output_dir=output_dir,
        country=args.country,
        cluster_minutes=args.cluster_minutes,
        run_crops=not args.skip_crops,
        min_detection_confidence=args.min_detection_confidence,
        site_id=args.site_id,
        camera_id=args.camera_id,
    )

    # --- Validate inputs ---
    if not config.images_dir.exists():
        print(f"\n Error: Images folder not found: {config.images_dir}")
        return
    if not config.images_dir.is_dir():
        print(f"\n Error: Images path must be a folder: {config.images_dir}")
        return

    config.output_dir.mkdir(parents=True, exist_ok=True)
    if config.final_output_path:
        config.final_output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Run pipeline ---
    with RunMetrics(config.output_dir):
        if args.single_folder:
            run_pipeline(config)
        else:
            run_batch_pipeline(config)


if __name__ == "__main__":
    main()
