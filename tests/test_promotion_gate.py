import unittest
from promotion_gate import compare_strategy_to_baseline, evaluate_gate


class PromotionGateTests(unittest.TestCase):
    def _row(self, strategy, score, family="calculus", status="accepted"):
        return {
            "strategy_id": strategy,
            "metadata": {"task_family": family},
            "evaluation": {"score": score, "consistent": True},
            "reuse_status": status,
        }

    def test_requires_comparable_evidence(self):
        rows = [self._row("candidate-v2", .9), self._row("baseline-v1", .8)]
        cmp = compare_strategy_to_baseline(rows, strategy_id="candidate-v2", min_samples=2)
        self.assertFalse(cmp["enough_evidence"])

    def test_candidate_experience_is_not_promotion_evidence(self):
        rows = (
            [self._row("candidate-v2", .95, status="candidate") for _ in range(3)] +
            [self._row("baseline-v1", .80, status="accepted") for _ in range(3)]
        )
        cmp = compare_strategy_to_baseline(rows, strategy_id="candidate-v2", min_samples=3)
        self.assertFalse(cmp["enough_evidence"])

    def test_approves_clear_improvement_without_regression(self):
        rows = (
            [self._row("candidate-v2", .90) for _ in range(3)] +
            [self._row("baseline-v1", .80) for _ in range(3)]
        )
        cmp = compare_strategy_to_baseline(rows, strategy_id="candidate-v2", min_samples=3)
        decision = evaluate_gate(cmp, min_improvement=.02)
        self.assertTrue(decision["approved"])

    def test_regression_blocks_promotion(self):
        rows = (
            [self._row("candidate-v2", .90) for _ in range(3)] +
            [self._row("baseline-v1", .80) for _ in range(3)]
        )
        cmp = compare_strategy_to_baseline(rows, strategy_id="candidate-v2", min_samples=3)
        decision = evaluate_gate(cmp, regressions=["canvas_render"])
        self.assertFalse(decision["approved"])


if __name__ == "__main__":
    unittest.main()
