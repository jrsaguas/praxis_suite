import unittest
from operational_context import build_operational_context


class OperationalContextTests(unittest.TestCase):
    def test_strategy_and_depth_become_agent_context(self):
        context = build_operational_context(
            task="límite de una función",
            investigation_id="chat/x",
            strategy_context={
                "task_family": "calculus",
                "strategy_ids": ["s1"],
                "operational_instructions": ["explicar cada salto"],
                "depth_context": {"requirements": {"proof_expectation": 92}},
            },
        )
        self.assertEqual(context["strategy_ids"], ("s1",))
        self.assertEqual(context["requirements"]["proof_expectation"], 92)
        self.assertEqual(context["investigation_id"], "chat/x")


if __name__ == "__main__":
    unittest.main()
