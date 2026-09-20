import unittest
from agent_architecture import AGENTS, execution_order, validate_artifact_owner


class AgentArchitectureTests(unittest.TestCase):
    def test_dependencies_produce_valid_order(self):
        order = execution_order()
        self.assertEqual(set(order), {a.id for a in AGENTS})
        positions = {name: i for i, name in enumerate(order)}
        for agent in AGENTS:
            for dep in agent.depends_on:
                self.assertLess(positions[dep], positions[agent.id])

    def test_artifact_ownership_is_explicit(self):
        self.assertTrue(validate_artifact_owner("python_visualizer", "python"))
        self.assertTrue(validate_artifact_owner("canvas_engineer", "canvas"))
        self.assertFalse(validate_artifact_owner("mathematical_resolver", "canvas"))

    def test_specialists_are_distinct_roles(self):
        ids = {a.id for a in AGENTS}
        self.assertIn("foundation_analyst", ids)
        self.assertIn("proof_specialist", ids)
        self.assertIn("python_visualizer", ids)
        self.assertIn("canvas_engineer", ids)
        self.assertIn("code_reviewer", ids)
        self.assertIn("epistemic_reviewer", ids)


if __name__ == "__main__":
    unittest.main()
