import unittest

from agent_archetypes import ARCHETYPES, DEPTH_DIMENSIONS, MODEL_CAPABILITY_TAGS
from agent_architecture import get_agent
from agent_graph import AgentGraphPlanner


class TestArchetypeOperationalProfiles(unittest.TestCase):
    def test_every_archetype_has_a_complete_operational_profile(self):
        for archetype in ARCHETYPES:
            profile = archetype.operational_profile()
            self.assertEqual(profile["archetype_id"], archetype.id)
            self.assertTrue(profile["required_tools"])
            self.assertTrue(profile["delivery_gates"])
            self.assertTrue(set(archetype.depth_requirements) <= set(archetype.depth_requirements))
            for dimension, threshold in archetype.depth_requirements:
                self.assertIn(dimension, DEPTH_DIMENSIONS)
                self.assertTrue(0 <= threshold <= 100)
            self.assertTrue(set(archetype.model_capabilities) <= set(MODEL_CAPABILITY_TAGS))

    def test_agent_spec_materializes_archetype_contract(self):
        spec = get_agent("canvas_engineer")
        self.assertEqual(spec.archetype_id, "canvas_html")
        self.assertEqual(spec.required_tools, ("html", "javascript", "canvas"))
        self.assertIn("math_rendering", spec.delivery_gates)
        self.assertEqual(dict(spec.depth_requirements)["visualization"], 60)

    def test_planner_exposes_operational_profile(self):
        plan = AgentGraphPlanner().plan(requested_agents=["canvas_engineer"])
        task = next(item for item in plan.tasks if item.agent_id == "canvas_engineer")
        profile = plan.planning_metadata["operational_profiles"]["canvas_engineer"]
        self.assertEqual(task.archetype_id, "canvas_html")
        self.assertEqual(profile["required_tools"], ["html", "javascript", "canvas"])
        self.assertIn("interaction_integrity", profile["delivery_gates"])

    def test_missing_required_tools_block_task_when_inventory_is_supplied(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["canvas_engineer"],
            available_tools=("html", "javascript"),
        )
        task = next(item for item in plan.tasks if item.agent_id == "canvas_engineer")
        self.assertEqual(task.status, "blocked")
        self.assertEqual(task.missing_tools, ("canvas",))


if __name__ == "__main__":
    unittest.main()
