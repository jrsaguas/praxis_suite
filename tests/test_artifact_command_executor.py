import tempfile
import unittest
from pathlib import Path

from artifact_command_executor import classify_artifact_command, execute_artifact_command


class ArtifactCommandExecutorTests(unittest.TestCase):
    def test_canvas_command_isolated_from_pipeline(self):
        plan = classify_artifact_command("genera otro Canvas con controles")
        self.assertEqual(plan.operation, "generate_canvas")
        self.assertTrue(plan.allowed)

    def test_unknown_command_is_rejected(self):
        plan = classify_artifact_command("haz algo impresionante")
        self.assertFalse(plan.allowed)
        self.assertEqual(plan.operation, "unknown")

    def test_figure_command_reuses_existing_script(self):
        plan = classify_artifact_command("genera más figuras")
        self.assertEqual(plan.operation, "regenerate_figures")

    def test_executor_rejects_missing_investigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                execute_artifact_command(
                    tmp, "chat", "respuesta_001", "genera otro Canvas"
                )


if __name__ == "__main__":
    unittest.main()
