import unittest

from experience_analyzer import detect_patterns, select_references, fuse_reference_patterns, build_strategy_candidate


class ExperienceAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "record_id": "e1", "task_fingerprint": "surface gradient",
                "investigation_id": "chat/r1", "version_id": "v1",
                "evaluation": {"score": 0.95, "consistent": True},
                "metadata": {"topic": "superficies", "features": ["canvas", "sliders"]},
            },
            {
                "record_id": "e2", "task_fingerprint": "surface curvature",
                "investigation_id": "chat/r2", "version_id": "v2",
                "evaluation": {"score": 0.90, "consistent": True},
                "metadata": {"topic": "superficies", "features": ["canvas", "sliders"]},
            },
            {
                "record_id": "e3", "task_fingerprint": "unrelated",
                "investigation_id": "chat/r3", "version_id": "v3",
                "evaluation": {"score": 0.40, "consistent": False},
                "metadata": {"topic": "álgebra", "features": ["text"]},
            },
        ]

    def test_detects_repeated_high_value_feature(self):
        patterns = detect_patterns(self.records)
        self.assertEqual(patterns[0].key, "canvas")
        self.assertEqual(patterns[0].frequency, 2)
        self.assertEqual(patterns[0].accept_rate, 1.0)

    def test_selects_relevant_references(self):
        refs = select_references(self.records, "superficies con Canvas y sliders", limit=2)
        self.assertEqual(refs[0].investigation_id, "chat/r1")
        self.assertLessEqual(len(refs), 2)

    def test_build_candidate_from_evidence_without_promoting(self):
        refs = select_references(self.records, "superficies Canvas")
        patterns = detect_patterns(self.records)
        candidate = build_strategy_candidate(refs, patterns)
        self.assertEqual(candidate.status, "candidate")
        self.assertEqual(candidate.source, "experience-analysis")
        self.assertIn("strategy-regression", candidate.required_tests)

    def test_fusion_is_not_promotion(self):
        refs = select_references(self.records, "superficies Canvas")
        patterns = detect_patterns(self.records)
        fused = fuse_reference_patterns(refs, patterns)
        self.assertEqual(fused["strategy"], "reference-fusion-v1")
        self.assertIn("explicit promotion gate", fused["guardrail"])


if __name__ == "__main__":
    unittest.main()
