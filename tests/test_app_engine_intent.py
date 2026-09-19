import re
import unittest

APP_PATH = "app_engine.js"

class IntentRoutingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Static contract test: app_engine.js is browser JS, so we verify
        # the routing guards without requiring a browser runtime.
        from pathlib import Path
        cls.source = Path(APP_PATH).read_text(encoding="utf-8")

    def test_specific_stage_resume_is_before_generic_resume(self):
        src = self.source
        specific = src.index("CMD_RESUME_STAGE")
        generic = src.index("CMD_RESUME")
        self.assertLess(specific, generic)

    def test_stage_command_cannot_fall_through_to_pipeline(self):
        src = self.source
        self.assertIn("contin[uú]a|reanuda|retoma|sigue|destraba", src)
        self.assertIn("type: 'CMD_RESUME_STAGE'", src)
        self.assertIn("type === 'CMD_RESUME_STAGE'", src)

    def test_artifact_edit_is_explicitly_isolated(self):
        src = self.source
        self.assertIn("CMD_ARTIFACT_EDIT", src)
        self.assertIn("no fue enviada al pipeline matemático", src)
        self.assertIn("pendingArtifactCommand", src)

if __name__ == "__main__":
    unittest.main()
