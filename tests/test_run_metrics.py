"""Performance reports must preserve failures and include inference children."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import psutil

from pipeline.run_metrics import RunMetrics


class RunMetricsTests(unittest.TestCase):
    def report(self, error=None):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            output = Path(tmp)
            if error is None:
                with RunMetrics(output, interval=0.01):
                    time.sleep(0.03)
            else:
                with self.assertRaises(type(error)) as raised:
                    with RunMetrics(output, interval=0.01):
                        raise error
                self.assertIs(raised.exception, error)
            return json.loads((output / "run_metrics.json").read_text())

    def test_completed_run_reports_time_and_memory(self):
        result = self.report()
        self.assertEqual(result["status"], "complete")
        self.assertGreaterEqual(result["elapsed_seconds"], 0.02)
        self.assertGreater(result["peak_process_tree_rss_bytes"], 0)
        self.assertGreaterEqual(result["sample_count"], 2)

    def test_failure_is_reported_and_propagated(self):
        self.assertEqual(self.report(RuntimeError("model failed"))["status"], "failed")

    def test_keyboard_interrupt_is_reported_and_propagated(self):
        self.assertEqual(self.report(KeyboardInterrupt())["status"], "interrupted")

    def test_child_memory_is_included(self):
        try:
            psutil.Process().children(recursive=True)
        except (psutil.Error, OSError) as exc:
            self.skipTest(f"OS blocks child-process discovery: {exc}")
        baseline = psutil.Process().memory_info().rss
        child_code = (
            "import time; data = b'x' * (64 * 1024 * 1024); "
            "print('ready', flush=True); time.sleep(30)"
        )
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            with RunMetrics(tmp, interval=0.01):
                child = subprocess.Popen(
                    [sys.executable, "-c", child_code], stdout=subprocess.PIPE, text=True
                )
                try:
                    self.assertEqual(child.stdout.readline().strip(), "ready")
                    time.sleep(0.1)
                finally:
                    child.terminate()
                    child.wait(timeout=5)
                    child.stdout.close()
            result = json.loads((Path(tmp) / "run_metrics.json").read_text())
        self.assertGreater(result["peak_process_tree_rss_bytes"], baseline + 48 * 1024 * 1024)

    def test_restricted_process_access_marks_measurement_incomplete(self):
        with patch.object(psutil.Process, "children", side_effect=PermissionError("restricted")):
            result = self.report()
        self.assertTrue(result["memory_measurement_incomplete"])
        self.assertEqual(result["status"], "complete")

    def test_unwritable_report_does_not_mask_pipeline_error(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as log:
            invalid_output = Path(tmp) / "missing" / "directory"
            with self.assertRaisesRegex(ValueError, "original failure"):
                with RunMetrics(invalid_output):
                    raise ValueError("original failure")
            self.assertIn("could not save run metrics", log.getvalue())


if __name__ == "__main__":
    unittest.main()
