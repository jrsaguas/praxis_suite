import unittest

from adaptive_agent import AdaptiveRequest
from agent_architect import AgentArchitect


class TestArchetypeArchitectIntegration(unittest.TestCase):
    def test_canvas_candidate_records_archetype_context(self):
        request = AdaptiveRequest(
            task="build interactive surface",
            requirements=("surface_geometry",),
            tools=("python", "canvas"),
            role="surface visualization specialist",
        )
        candidate = AgentArchitect().synthesize(request).candidate
        self.assertIn("archetype:canvas_html", candidate.context)
        self.assertEqual(candidate.role, "canvas-html specialist")

    def test_python_visualization_candidate_records_archetype_context(self):
        request = AdaptiveRequest(
            task="plot vector field",
            requirements=("vector_field",),
            tools=("python", "matplotlib"),
            role="visualization specialist",
        )
        candidate = AgentArchitect().synthesize(request).candidate
        self.assertIn("archetype:python_visualization", candidate.context)
        self.assertEqual(candidate.role, "python-visualization specialist")

    def test_proof_candidate_records_archetype_context(self):
        request = AdaptiveRequest(
            task="prove theorem",
            requirements=("formal_proof",),
            tools=("sympy",),
            role="mathematical-proof specialist",
        )
        candidate = AgentArchitect().synthesize(request).candidate
        self.assertIn("archetype:mathematical_proof", candidate.context)
        self.assertEqual(candidate.role, "mathematical-proof specialist")


if __name__ == "__main__":
    unittest.main()
