import tempfile
import unittest

from preference_store import save_explicit, save_inferred, effective_profile, load


class PreferenceStoreTests(unittest.TestCase):
    def test_explicit_preference_has_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_inferred(tmp, "chat-1", {"mathematics": 40}, evidence_ids=["e1"], confidence=0.99)
            save_explicit(tmp, "chat-1", {"mathematics": 100})
            profile = effective_profile(tmp, "chat-1")
            self.assertEqual(profile.weights["mathematics"], 100)

    def test_low_confidence_inference_is_not_effective(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_inferred(tmp, "chat-1", {"visualization": 100}, evidence_ids=["e1"], confidence=0.60)
            self.assertIsNone(effective_profile(tmp, "chat-1"))

    def test_history_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_explicit(tmp, "chat-1", {"code": 90})
            data = load(tmp, "chat-1")
            self.assertEqual(len(data["history"]), 1)


if __name__ == "__main__":
    unittest.main()
