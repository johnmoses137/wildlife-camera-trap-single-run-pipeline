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
- Elapsed processing time and sampled peak RAM, saved to `run_metrics.json`

## Repository structure

```text
.
├── main.py                    # Command-line and interactive entry point
├── config.py                  # Pipeline configuration
├── requirements.txt           # Python dependencies
├── CHANGELOG.md               # Consolidation and reliability changes
└── pipeline/
    ├── runner.py              # End-to-end orchestration
    ├── run_metrics.py         # Elapsed time and process-tree memory reporting
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

### 1. Download the project

On this GitHub page, select **Code**, then **Download ZIP**, and extract the ZIP.
Keep `main.py`, `config.py`, `requirements.txt`, and `pipeline/` together.
Open a terminal in the extracted folder. Git users can instead run:

```bash
git clone https://github.com/johnmoses137/wildlife-camera-trap-single-run-pipeline.git
cd wildlife-camera-trap-single-run-pipeline
```

### 2. Create and activate a Python environment

Install Python first if needed. Python 3.11 or 3.12 is a suitable starting point.
Use the commands for your operating system, from the project folder.

macOS / Linux:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

Windows Command Prompt (with Python 3.11 installed):

```bat
py -3.11 --version
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
```

Windows PowerShell uses `.venv\Scripts\Activate.ps1` for activation. If local
PowerShell policy blocks activation, use Command Prompt instead.

### 3. Install dependencies and check the commands

Use `python` inside the activated environment so installation and execution use
the same interpreter:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python -m speciesnet.scripts.run_model --help
python main.py --help
```

The requirements pin **SpeciesNet 5.0.5** because this pipeline reads its
image-level `prediction` and `prediction_score` fields. SpeciesNet 5.0.6 changed
to a per-detection classification format. Do not upgrade SpeciesNet independently
until the pipeline supports that format. Pandas is constrained to the 2.x series
for the metadata timestamp handling. These constraints are not a full lock of
every transitive dependency.

References: [SpeciesNet 5.0.5 package documentation](https://pypi.org/project/speciesnet/5.0.5/)
and [SpeciesNet output documentation](https://pypi.org/project/speciesnet/).

A CPU can run inference. A compatible NVIDIA GPU is optional; follow
[SpeciesNet's GPU setup instructions](https://github.com/google/cameratrapai#using-gpus)
if you need acceleration. The first run needs internet to download model files.
Re-activate `.venv` when you open a new terminal.

## Usage

### Interactive mode

```bash
python main.py
```

### Command-line mode

```bash
python main.py \
  --images "/path/to/camera-trap/images" \
  --output "/path/to/output"
```

### Recommended research-data command

```bash
python main.py \
  --images "/path/to/images" \
  --output "/path/to/output" \
  --single-folder \
  --site-id "SITE_01" \
  --camera-id "CAMERA_01" \
  --cluster-minutes 5 \
  --min-detection-confidence 0.1
```

The multi-line commands above use macOS/Linux shell syntax. On Windows, enter
the command on one line with your own image/output paths.

For the first run, use a few JPG, JPEG, or PNG images with unique filenames and a
**new output folder outside the image directory**. Generated image folders are
not cleared between runs, so reusing an output folder can mix old and new files.
The completion message prints the final CSV path. Open that CSV and inspect the
annotated images before processing a larger dataset.

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
├── run_metrics.json
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

On October 23, 2026, the updated requirements were installed in a clean Python
3.12.14 environment on macOS (Apple Silicon). `pip check` passed. A two-image
test with cached model weights completed both original and crop inference,
metadata inheritance, and the final merge: two original rows plus one crop row.
That test used a deliberately low `--min-detection-confidence 0.01` to exercise
the crop path; the default remains `0.1`.

The metrics report recorded completion and correctly flagged incomplete memory
measurement because the test sandbox blocks child-process discovery. Five
regression tests passed; the live child-discovery test was skipped for that OS
restriction. Windows and Linux installation were not executed in this check.

## Notes and limitations

- Accuracy varies by geography, species, image quality, and camera placement.
- Prefer explicit site and camera identifiers for research datasets.
- Filesystem timestamps may reflect copying or downloading, not capture time.
- Review low-confidence predictions and validate ecological conclusions against
  expert-labeled data.
- Use unique image filenames within each dataset, including nested folders.
  Several output paths and metadata joins use the filename rather than a full path.

## Run time and memory usage

Each `python main.py` run prints elapsed processing time and sampled peak RAM,
and writes `run_metrics.json` in the output folder. Measurement starts after
input prompts, path validation, and output-folder setup. A batch gets one report
covering all its datasets and crop passes.

RAM is sampled every 0.2 seconds across the main Python process and its recursive
child processes, including SpeciesNet. This is the peak sampled sum of resident
memory (RSS), not GPU memory or total computer RAM usage. Shared pages can be
counted more than once, and peaks between samples can be missed.

The report records `complete`, `failed`, or `interrupted` and also appears after
a pipeline exception or Ctrl+C. It does not suppress the original error.
Force-killing the process or shutting down the computer prevents final reporting.
Runs replace an existing `run_metrics.json` in the same output folder. MiB and
GiB use powers of 1024.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `main.py` cannot be found | Open the terminal in the extracted project folder. |
| A Python module is missing | Activate `.venv`, then install requirements with `python -m pip`. |
| Prediction labels are empty after an upgrade | Check `python -m pip show speciesnet`; reinstall the pinned requirements. |
| A first run pauses on downloads | Keep internet available until the model files finish downloading. |
| Old images appear in results | Use a fresh output folder. |
| Capture times do not match camera times | Inspect `timestamp_source`; `FileModifyDate` is a filesystem fallback. |

## Development checks

With the requirements installed:

```bash
python -m unittest discover -s tests -v
```

## Related project

- [Original step-by-step workflow](https://github.com/johnmoses137/wildlife-camera-trap-classification)

## Author

Developed by John Moses Bollarapu as part of master's-level wildlife research
work in collaboration with a biology department.
