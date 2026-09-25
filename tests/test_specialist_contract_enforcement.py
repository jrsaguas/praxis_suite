import unittest

from agent_graph import AgentGraphPlanner


class TestSpecialistContractEnforcement(unittest.TestCase):
    def test_depth_below_archetype_minimum_blocks_specialist(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["mathematical_resolver"],
            depth_requirements={"rigor": 50},
        )
        task = next(t for t in plan.tasks if t.agent_id == "mathematical_resolver")
        self.assertEqual(task.status, "blocked")
        self.assertEqual(task.depth_gaps, (("rigor", 70, 50),))

    def test_depth_above_archetype_minimum_does_not_block(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["mathematical_resolver"],
            depth_requirements={"rigor": 90, "formalism": 80},
        )
        task = next(t for t in plan.tasks if t.agent_id == "mathematical_resolver")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.depth_gaps, ())

    def test_unspecified_depth_is_not_a_false_block(self):
        plan = AgentGraphPlanner().plan(requested_agents=["canvas_engineer"])
        task = next(t for t in plan.tasks if t.agent_id == "canvas_engineer")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.depth_gaps, ())

    def test_tool_and_depth_failures_are_reported_together(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["canvas_engineer"],
            depth_requirements={"visualization": 40},
            available_tools=("html", "javascript"),
        )
        task = next(t for t in plan.tasks if t.agent_id == "canvas_engineer")
        self.assertEqual(task.status, "blocked")
        self.assertEqual(task.missing_tools, ("canvas",))
        self.assertEqual(task.depth_gaps, (("visualization", 60, 40),))
        profile = plan.planning_metadata["operational_profiles"]["canvas_engineer"]
        self.assertEqual(profile["depth_gaps"], [["visualization", 60, 40]])


if __name__ == "__main__":
    unittest.main()
