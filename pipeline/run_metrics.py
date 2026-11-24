"""Measure wall time and sampled RAM for the pipeline and its children."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread

import psutil


class RunMetrics:
    """Report even on exceptions; never suppress a pipeline failure."""

    def __init__(self, output_dir, interval=0.2):
        self.path = Path(output_dir) / "run_metrics.json"
        self.interval = interval
        self.process = psutil.Process()
        self.stop = Event()
        self.peak = 0
        self.samples = 0
        self.incomplete = False

    def _sample(self):
        processes = [self.process]
        try:
            processes.extend(self.process.children(recursive=True))
        except (psutil.Error, OSError):
            self.incomplete = True
        total = 0
        for process in processes:
            try:
                total += process.memory_info().rss
            except psutil.NoSuchProcess:
                pass  # A child can exit between discovery and measurement.
            except (psutil.Error, OSError):
                self.incomplete = True
        self.peak = max(self.peak, total)
        self.samples += 1

    def _watch(self):
        while not self.stop.wait(self.interval):
            self._sample()

    def __enter__(self):
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.start = time.perf_counter()
        self._sample()
        self.worker = Thread(target=self._watch, daemon=True)
        self.worker.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        elapsed = time.perf_counter() - self.start
        self.stop.set()
        self.worker.join()
        self._sample()
        status = "complete" if exc_type is None else (
            "interrupted" if issubclass(exc_type, KeyboardInterrupt) else "failed"
        )
        peak_mib = self.peak / (1024 ** 2)
        metrics = {
            "started_at_utc": self.started_at,
            "status": status,
            "elapsed_seconds": round(elapsed, 3),
            "peak_process_tree_rss_bytes": self.peak,
            "peak_process_tree_rss_mib": round(peak_mib, 2),
            "sample_interval_seconds": self.interval,
            "sample_count": self.samples,
            "memory_measurement_incomplete": self.incomplete,
            "memory_scope": "Main process plus recursive child processes, including SpeciesNet",
            "memory_note": "Sampled sum of RSS; shared pages may be counted more than once. "
                           "Brief peaks may be missed. Excludes GPU memory and unrelated apps.",
        }
        print("\n" + "=" * 60)
        print(f" RUN PERFORMANCE ({status})")
        print(f" Time taken       : {elapsed / 60:.2f} minutes ({elapsed:.2f} seconds)")
        print(f" Sampled peak RAM : {peak_mib:.1f} MiB ({peak_mib / 1024:.2f} GiB)")
        print(" RAM includes the pipeline and SpeciesNet child processes.")
        if self.incomplete:
            print(" Warning: some process memory readings were unavailable.")
        try:
            self.path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
            print(f" Metrics saved to : {self.path}")
        except OSError as error:
            print(f" Warning: could not save run metrics: {error}")
        print("=" * 60)
        return False
