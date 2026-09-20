import unittest
import tempfile
from pathlib import Path

from process_reporter import generate_process_report

class ProcessReportTests(unittest.TestCase):
    def test_report_is_reproducible_and_contains_trace_files(self):
        with tempfile.TemporaryDirectory() as td:
            result = generate_process_report(td, "2+2", "Regression", {"plan":{"prompt":"p","rawOutput":"r"}}, {})
            self.assertTrue(Path(result["json_path"]).exists())
            self.assertTrue(Path(result["md_path"]).exists())
            self.assertTrue(Path(result["html_path"]).exists())
            self.assertIn("2+2", Path(result["json_path"]).read_text(encoding="utf-8"))

    def test_report_includes_runtime_observable_events(self):
        with tempfile.TemporaryDirectory() as td:
            result = generate_process_report(
                td, "x", "Runtime", {},
                {"events": [{
                    "sequence": 1, "task_id": "task:a", "agent_id": "a",
                    "phase": "task", "status": "completed",
                    "input_keys": ["x"], "output_keys": ["md"],
                    "message": "completed"
                }]}
            )
            md = Path(result["md_path"]).read_text(encoding="utf-8")
            html = Path(result["html_path"]).read_text(encoding="utf-8")
            self.assertIn("Bitácora Operacional Observable", md)
            self.assertIn("task:a", md)
            self.assertIn("task:a", html)

if __name__ == "__main__":
    unittest.main()