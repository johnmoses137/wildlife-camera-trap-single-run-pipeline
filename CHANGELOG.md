# Updates

## 2026-11-24

- Add elapsed-time and sampled process-tree RAM reporting from the latest local
  tool, including completion, failure, and interruption status in `run_metrics.json`.
- Pin SpeciesNet to 5.0.5, which preserves the image-level prediction format this
  pipeline reads, and constrain pandas to the 2.x series for metadata processing.
- Explain GitHub ZIP downloads, environment setup on macOS/Linux and Windows,
  dependency checks, first runs, and output-folder handling in the README.
- Add regression coverage for performance reporting.

## Consolidated Pipeline

This copy combines the latest useful changes found in the two project copies.

- Base: professor-edited Google Drive folder.
- `pipeline/metadata.py`: retains the Drive improvements for skipping embedded
  JPEG thumbnail data and parsing mixed timestamp formats safely.
- `pipeline/merge.py`: retains the local improvements that add `record_type`,
  `parent_image`, and `detection_index` to the final merged dataset.

The original local and Google Drive copies were not modified.

## Reliability fixes

- Parse standard camera EXIF timestamps (`YYYY:MM:DD HH:MM:SS`) correctly.
- Filter secondary crops by a configurable detector-confidence threshold.
- Support explicit `--site-id` and `--camera-id` values for datasets whose
  folder paths do not encode those identifiers.
- Keep an empty crop manifest structurally valid when no secondary detections
  pass the threshold.
- Use Matplotlib's non-interactive backend for reliable terminal execution.
