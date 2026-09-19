import tempfile
import unittest

from strategy_registry import (
    StrategyRegistry, create_candidate, evaluate_promotion
)


class StrategyRegistryTests(unittest.TestCase):
    def test_candidate_is_not_promoted_automatically(self):
        strategy = create_candidate(
            "Canvas enriquecido",
            "mejorar interactividad",
            ["usar controles", "mostrar curvas de nivel"],
            required_tests=["canvas-regression", "html-regression"],
        )
        self.assertEqual(strategy.status, "candidate")

    def test_promotion_requires_all_tests_and_improvement(self):
        strategy = create_candidate(
            "S1", "obj", ["rule"], required_tests=["t1", "t2"]
        )
        rejected = evaluate_promotion(
            strategy, baseline_score=0.9, candidate_score=0.91, passed_tests=["t1"]
        )
        self.assertFalse(rejected.approved)

        approved = evaluate_promotion(
            strategy, baseline_score=0.9, candidate_score=0.94, passed_tests=["t1", "t2"]
        )
        self.assertTrue(approved.approved)

    def test_registry_promotes_only_approved_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = StrategyRegistry(tmp)
            strategy = registry.register(
                "chat-1",
                create_candidate("S2", "obj", ["rule"], required_tests=["t"]),
            )
            decision = evaluate_promotion(
                strategy, baseline_score=0.8, candidate_score=0.85, passed_tests=["t"]
            )
            result = registry.promote("chat-1", decision)
            self.assertEqual(result["status"], "promoted")
            self.assertEqual(len(registry.list("chat-1", status="promoted")), 1)


if __name__ == "__main__":
    unittest.main()
