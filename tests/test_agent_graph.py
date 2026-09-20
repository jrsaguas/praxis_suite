import unittest
from agent_graph import AgentGraphPlanner


class AgentGraphTests(unittest.TestCase):
    def test_canvas_request_builds_required_upstream_chain(self):
        plan = AgentGraphPlanner().plan(required_artifacts=["canvas"])
        ids = [x.agent_id for x in plan.tasks]
        self.assertIn("canvas_engineer", ids)
        self.assertIn("representation_designer", ids)
        self.assertIn("mathematical_resolver", ids)
        self.assertIn("foundation_analyst", ids)
        self.assertLess(ids.index("representation_designer"), ids.index("canvas_engineer"))

    def test_ready_tasks_only_expose_satisfied_dependencies(self):
        plan = AgentGraphPlanner().plan(required_artifacts=["canvas"])
        ready = plan.ready([])
        self.assertEqual([x.agent_id for x in ready], ["intent_router"])

    def test_depth_context_is_carried_into_plan(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["mathematical_resolver"],
            depth_requirements={"proof_expectation": 92},
        )
        self.assertEqual(plan.depth_requirements["proof_expectation"], 92)


if __name__ == "__main__":
    unittest.main()

# CI graph regression coverage.
