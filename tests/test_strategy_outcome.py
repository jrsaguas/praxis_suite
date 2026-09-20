import unittest

from learning_bridge import persist_strategy_outcome


class StrategyOutcomeTests(unittest.TestCase):
    def test_selected_strategy_outcome_is_auditable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            record = persist_strategy_outcome(
                tmp, "chat-1",
                strategy_context={
                    "strategy_context_version": 2,
                    "task_family": "calculus",
                    "strategy_ids": ["calc-v2"],
                    "strategies": [{"selection_score": 0.91}],
                    "temporal_trends": [{"feature": "canvas"}],
                },
                evaluation_profile={"mathematics": 95, "visualization": 90},
                score=0.94,
                consistent=True,
                investigation_id="chat-1/r1",
                version_id="v1",
            )
            self.assertEqual(record["strategy_id"], "calc-v2")
            self.assertEqual(record["evaluation"]["score"], 0.94)
            self.assertEqual(record["metadata"]["task_family"], "calculus")
            self.assertEqual(record["metadata"]["evaluation_profile"]["mathematics"], 95)


if __name__ == "__main__":
    unittest.main()
