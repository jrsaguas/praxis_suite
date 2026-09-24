import unittest

from agent_graph import AgentGraphPlanner
from mathematical_depth import MathematicalDepthProfile, build_depth_context


class MathematicalDepthGraphTests(unittest.TestCase):
    def test_doctorado_profile_adds_formal_proof_research_visualization_roles(self):
        profile = MathematicalDepthProfile.preset("doctorado")
        plan = AgentGraphPlanner().plan(depth_requirements=build_depth_context(profile))
        selected = set(plan.selected_agents)
        self.assertIn("foundation_analyst", selected)
        self.assertIn("proof_specialist", selected)
        self.assertIn("research_specialist", selected)
        self.assertIn("representation_designer", selected)

    def test_raw_profile_dimensions_are_honored(self):
        profile = MathematicalDepthProfile(
            "custom",
            rigor=90, prerequisites=80, formalism=90, proof=85,
            research=85, visualization=80, experimentation=75,
            generalization=85, applications=70,
        )
        plan = AgentGraphPlanner().plan(depth_requirements=profile.to_dict())
        selected = set(plan.selected_agents)
        self.assertIn("foundation_analyst", selected)
        self.assertIn("proof_specialist", selected)
        self.assertIn("research_specialist", selected)
        self.assertIn("representation_designer", selected)
        self.assertIn("python_visualizer", selected)
        self.assertIn("code_reviewer", selected)

    def test_low_depth_profile_does_not_force_specialists(self):
        profile = MathematicalDepthProfile.preset("introductorio")
        plan = AgentGraphPlanner().plan(depth_requirements=build_depth_context(profile))
        selected = set(plan.selected_agents)
        self.assertNotIn("proof_specialist", selected)
        self.assertNotIn("research_specialist", selected)
        self.assertNotIn("python_visualizer", selected)


if __name__ == "__main__":
    unittest.main()
