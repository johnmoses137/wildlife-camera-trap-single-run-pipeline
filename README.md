# Wildlife Camera Trap Single-Run Pipeline

An end-to-end wildlife camera-trap analysis workflow built around Google's
[SpeciesNet](https://github.com/google/cameratrapai). One command runs image
classification, annotation, species grouping, visualization, EXIF metadata
extraction, temporal clustering, secondary-detection cropping, reclassification,
and final dataset merging.

This repository is the automated companion to the original
[step-by-step wildlife camera-trap classification project](https://github.com/johnmoses137/wildlife-camera-trap-classification).

## Why this version exists

The original project exposes each processing stage as a separate script. This
version provides one entry point, `main.py`, that coordinates the complete
two-pass workflow. It supports individual datasets, nested image folders, and
batch processing of multiple dataset folders.

## Workflow

```text
Camera-trap images
        |
        v
SpeciesNet inference on original images
        |
        +--> Prediction CSV
        +--> Annotated images
        +--> Species folders and distribution charts
        +--> EXIF metadata and temporal event clusters
        |
        v
Secondary detections above the confidence threshold
        |
        v
Crop -> SpeciesNet reclassification -> Parent metadata inheritance
        |
        v
Final merged prediction dataset
```

SpeciesNet classifies the highest-confidence detection in an image. This
pipeline can also crop additional animal detections and submit those crops to a
second SpeciesNet pass, allowing multiple animals in the same frame to be
represented in the final dataset.

## Features

- Single-command execution of the complete pipeline
- Original-image and secondary-crop SpeciesNet passes
- Configurable confidence threshold for secondary detections
- Bounding-box annotations and species-organized image folders
- Species-distribution charts, including a non-blank view
- Camera EXIF timestamp extraction with filesystem-time fallback
- Explicit timestamp provenance in the `timestamp_source` column
- Configurable temporal event clustering
- Optional site and camera identifiers
- Parent-child tracking for cropped detections
- Batch processing with per-dataset failure isolation and summaries

## Repository structure

```text
.
├── main.py                    # Command-line and interactive entry point
├── config.py                  # Pipeline configuration
├── requirements.txt           # Python dependencies
├── CHANGELOG.md               # Consolidation and reliability changes
└── pipeline/
    ├── runner.py              # End-to-end orchestration
    ├── speciesnet_runner.py   # SpeciesNet subprocess adapter
    ├── json_to_csv.py         # Prediction JSON to CSV conversion
    ├── annotate.py            # Bounding-box image annotation
    ├── group.py               # Species-based image organization
    ├── visualize.py           # Species-distribution charts
    ├── metadata.py            # EXIF extraction and event clustering
    ├── crop.py                # Secondary-detection cropping
    ├── inherit_metadata.py    # Parent metadata inheritance
    └── merge.py               # Original and crop result merge
```

## Requirements

- Python 3.9 or later
- SpeciesNet and its model dependencies
- Packages listed in `requirements.txt`

SpeciesNet downloads model files on first use, so the initial run may take
longer and requires internet access.

## Installation

```bash
git clone https://github.com/johnmoses137/wildlife-camera-trap-single-run-pipeline.git
cd wildlife-camera-trap-single-run-pipeline
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

Confirm that SpeciesNet is available:

```bash
python3 -m speciesnet.scripts.run_model --help
```

## Usage

### Interactive mode

```bash
python3 main.py
```

### Command-line mode

```bash
python3 main.py \
  --images "/path/to/camera-trap/images" \
  --output "/path/to/output"
```

### Recommended research-data command

```bash
python3 main.py \
  --images "/path/to/images" \
  --output "/path/to/output" \
  --single-folder \
  --site-id "SITE_01" \
  --camera-id "CAMERA_01" \
  --cluster-minutes 5 \
  --min-detection-confidence 0.1
```

## Options

| Option | Purpose | Default |
| --- | --- | --- |
| `--images` | Input image directory | Interactive prompt |
| `--output` | Output directory or final CSV path | Interactive prompt |
| `--country` | Country code passed to SpeciesNet | None |
| `--cluster-minutes` | Time gap that starts a new event | `5` |
| `--min-detection-confidence` | Minimum confidence for secondary crops | `0.1` |
| `--site-id` | Explicit site identifier | Inferred from folders |
| `--camera-id` | Explicit camera identifier | Inferred from folders |
| `--skip-crops` | Skip secondary-detection processing | Off |
| `--single-folder` | Treat the entire input as one dataset | Off |

The confidence threshold only affects additional detections. It does not remove
original images or primary classifications. Set it to `0` to reproduce the
original crop behavior.

## Input organization

One dataset:

```text
images/
├── image001.jpg
├── image002.jpg
└── image003.jpg
```

Multiple datasets:

```text
animals/
├── antelope/
├── badger/
└── bat/
```

Without `--single-folder`, each immediate child containing images receives its
own output directory and a `batch_summary.csv` is produced.

## Output

```text
output/
├── predictions.csv
├── meta_data_clustered.csv
├── final_merged_predictions.csv       # When crops are reclassified
├── annotated_images/
├── Grouped_Images/
├── Visualizations/
│   ├── bar_including_blanks.png
│   └── bar_excluding_blanks.png
├── cropped_images/
│   └── crop_manifest.csv
└── crops/
    ├── predictions.csv
    └── cropped_predictions_with_metadata.csv
```

If no secondary detections pass the threshold, crop inference is skipped and
`meta_data_clustered.csv` is the final tabular result.

### Timestamp behavior

Capture time is selected in this order:

1. `DateTimeOriginal`
2. `DateTimeDigitized`
3. `DateTime`
4. Filesystem modification time

Standard camera timestamps such as `2021:04:11 20:43:09` are explicitly
parsed. The `timestamp_source` column records the source selected for each row.

### Merged-record fields

When secondary crops exist, the final merged file includes:

- `record_type`: `ORIGINAL` or `CROP`
- `parent_image`: source image for a crop
- `detection_index`: detection position within the source image

## Validation

The workflow was tested end to end on a 10-image camera-trap sample. It used all
10 EXIF `DateTimeOriginal` values, generated one temporal cluster, classified
all original images, and rejected a 1.7%-confidence secondary detection at the
default 10% crop threshold.

This integration test is not a biological accuracy benchmark. Confidence
thresholds should be validated against manually reviewed images before use in a
scientific study.

## Notes and limitations

- Accuracy varies by geography, species, image quality, and camera placement.
- Prefer explicit site and camera identifiers for research datasets.
- Filesystem timestamps may reflect copying or downloading, not capture time.
- Review low-confidence predictions and validate ecological conclusions against
  expert-labeled data.

## Related project

- [Original step-by-step workflow](https://github.com/johnmoses137/wildlife-camera-trap-classification)

## Author

Developed by John Moses Bollarapu as part of master's-level wildlife research
work in collaboration with a biology department.
