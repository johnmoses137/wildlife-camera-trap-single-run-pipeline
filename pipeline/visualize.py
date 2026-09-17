# ===============================================================
# STEP 5: CREATE SPECIES DISTRIBUTION VISUALIZATIONS
# ===============================================================
# Generates bar charts showing species abundance
# ===============================================================

import re
import time
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def create_visualizations(grouped_dir: Path, out_root: Path):
    """
    Generate bar charts from grouped species folders.
    Creates two charts: with and without blank images.
    """
    start = time.time()

    viz_dir = out_root / "Visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)

    # Count images per species folder
    species_counts = {}
    for folder in grouped_dir.iterdir():
        if folder.is_dir():
            # Remove "(45)" from "Deer (45)" to get clean name
            name = re.sub(r"\(\d+\)", "", folder.name).strip()
            count = (
                len(list(folder.glob("*.jpg"))) +
                len(list(folder.glob("*.JPG"))) +
                len(list(folder.glob("*.png"))) +
                len(list(folder.glob("*.PNG")))
            )
            species_counts[name] = count

    if not species_counts:
        print(" No species folders found, skipping visualizations")
        return

    # Two datasets: all species, and non-blank only
    sorted_all = dict(sorted(species_counts.items(), key=lambda x: x[1], reverse=True))
    sorted_nb  = dict(sorted(
        {k: v for k, v in species_counts.items() if k.lower() != "blank"}.items(),
        key=lambda x: x[1], reverse=True
    ))

    def make_bar(data, title, fname):
        plt.figure(figsize=(14, 8))
        plt.barh(list(data.keys()), list(data.values()))
        plt.gca().invert_yaxis()
        plt.title(title)
        plt.xlabel("Count")
        plt.tight_layout()
        plt.savefig(viz_dir / fname, dpi=300)
        plt.close()

    make_bar(sorted_all, "Species Distribution (Including Blanks)", "bar_including_blanks.png")
    make_bar(sorted_nb,  "Species Distribution (Excluding Blanks)", "bar_excluding_blanks.png")

    print(f" Visualizations saved → {viz_dir.name}")
