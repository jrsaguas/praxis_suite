import unittest

from agent_graph import AgentGraphPlanner
from agent_gate_verifiers import verify_output


class ArtifactGateVerifierTests(unittest.TestCase):
    def test_canvas_verifier_uses_real_html_artifact(self):
        plan = AgentGraphPlanner().plan(requested_agents=["canvas_engineer"])
        task = next(t for t in plan.tasks if t.agent_id == "canvas_engineer")
        result = verify_output(task, {
            "canvas_html": "<html><head><title>x</title></head><body><canvas></canvas><script>draw()</script></body></html>"
        }, "delivery")
        self.assertTrue(result.passed)
        self.assertFalse(result.missing_gates)
        self.assertTrue(result.evidence["interaction_integrity"]["canvas"])

    def test_canvas_external_script_fails_safety_gate(self):
        plan = AgentGraphPlanner().plan(requested_agents=["canvas_engineer"])
        task = next(t for t in plan.tasks if t.agent_id == "canvas_engineer")
        result = verify_output(task, {
            "canvas_html": '<canvas></canvas><script src="https://example.test/x.js"></script>'
        }, "delivery")
        self.assertIn("html_safety", result.failed_gates)

    def test_python_visualizer_requires_numeric_evidence(self):
        plan = AgentGraphPlanner().plan(requested_agents=["python_visualizer"])
        task = next(t for t in plan.tasks if t.agent_id == "python_visualizer")
        result = verify_output(task, {
            "python_code": "import math\nprint(math.pi)",
            "numeric_checks": {"passed": True, "method": "known_value_check"},
            "reproducibility": True,
        }, "delivery")
        self.assertTrue(result.passed)

    def test_math_resolver_does_not_accept_plain_prose_as_symbolic_verification(self):
        plan = AgentGraphPlanner().plan(requested_agents=["mathematical_resolver"])
        task = next(t for t in plan.tasks if t.agent_id == "mathematical_resolver")
        result = verify_output(task, {
            "derivation": "x + 1 = 2",
            "assumptions": ["x is real"],
        }, "delivery")
        self.assertFalse(result.passed)
        self.assertIn("symbolic_consistency", result.missing_gates)

    def test_unsupported_specialist_gate_is_conservatively_blocked(self):
        plan = AgentGraphPlanner().plan(requested_agents=["research_specialist"])
        task = next(t for t in plan.tasks if t.agent_id == "research_specialist")
        result = verify_output(task, {"agent_response": "research"}, "delivery")
        self.assertFalse(result.passed)
        self.assertTrue(result.missing_gates)


if __name__ == "__main__":
    unittest.main()
