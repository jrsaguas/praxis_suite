import unittest

from investigation_model import EvaluationProfile, InvestigationVersion, slug_investigation_id


class InvestigationModelTests(unittest.TestCase):
    def test_evaluation_profile_is_bounded_and_weighted(self):
        profile = EvaluationProfile(mathematics=100, depth=50)
        self.assertEqual(profile.weighted_score(), 18.75)

    def test_invalid_evaluation_is_rejected(self):
        with self.assertRaises(ValueError):
            EvaluationProfile(mathematics=101)

    def test_version_chain_has_parent_and_stable_shape(self):
        first = InvestigationVersion.create("chat/response", "prompt", "Title")
        second = InvestigationVersion.create(
            "chat/response",
            "correction",
            "Title v2",
            parent_version_id=first.version_id,
            source="artifact_command",
            commands=["genera otro Canvas"],
        )
        self.assertNotEqual(first.version_id, second.version_id)
        self.assertEqual(second.parent_version_id, first.version_id)
        self.assertEqual(second.source, "artifact_command")
        self.assertEqual(first.status, "succeeded")
        self.assertEqual(second.to_dict()["status"], "succeeded")

    def test_id_uses_existing_folder_identity(self):
        self.assertEqual(
            slug_investigation_id("chat-1", "respuesta_001_demo"),
            "chat-1/respuesta_001_demo",
        )


if __name__ == "__main__":
    unittest.main()
