import unittest

from agent_architecture import get_agent


class TestAgentSpecArchetypes(unittest.TestCase):
    def test_specialist_specs_reference_archetypes(self):
        expected = {
            "mathematical_resolver": "math_resolver",
            "proof_specialist": "mathematical_proof",
            "python_visualizer": "python_visualization",
            "canvas_engineer": "canvas_html",
            "code_reviewer": "code",
            "research_specialist": "research",
            "integrator": "integrator",
        }
        for agent_id, archetype_id in expected.items():
            self.assertEqual(get_agent(agent_id).archetype_id, archetype_id)


if __name__ == "__main__":
    unittest.main()
