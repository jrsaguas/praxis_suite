import unittest
from strategy_registry import StrategyRegistry, create_candidate, PromotionDecision


class PromotionRegistryTests(unittest.TestCase):
    def test_approved_decision_promotes_and_records_evidence(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            chat = os.path.join(tmp, "chat")
            os.makedirs(chat)
            registry = StrategyRegistry(tmp)
            candidate = create_candidate(
                "Canvas calculus", "improve visualization",
                ["use interactive surface controls"],
                required_tests=["render"],
            )
            registry.register("chat", candidate)
            decision = PromotionDecision(
                strategy_id=candidate.strategy_id, approved=True,
                reason="evidence", baseline_score=.80,
                candidate_score=.90, required_tests=("render",),
                passed_tests=("render",),
            )
            promoted = registry.promote("chat", decision)
            self.assertEqual(promoted["status"], "promoted")
            self.assertEqual(promoted["promotion"]["candidate_score"], .90)
            self.assertIsNotNone(promoted["promoted_at"])


if __name__ == "__main__":
    unittest.main()
