import unittest
from agent_graph import AgentGraphPlanner

class ModelRoutingGraphTests(unittest.TestCase):
    def test_plan_contains_models_per_agent(self):
        plan = AgentGraphPlanner().plan(required_artifacts=["canvas"], model_overrides={"canvas_engineer":"ollama-llama"})
        task = next(t for t in plan.tasks if t.agent_id == "canvas_engineer")
        self.assertEqual(task.model_id, "ollama-llama")

    def test_final_auditor_is_terminal_quality_stage(self):

        plan = AgentGraphPlanner().plan(requested_agents=["final_auditor"])
        ids = {t.agent_id for t in plan.tasks}
        self.assertIn("final_auditor", ids)
        audit = next(t for t in plan.tasks if t.agent_id == "final_auditor")
        experience = next(t for t in plan.tasks if t.agent_id == "experience_evaluator")
        self.assertTrue(audit.depends_on)
        self.assertIn("task:final_auditor", experience.depends_on)


    def test_current_evaluation_profile_is_carried_into_experience_context(self):
        profile = {"depth": 100, "mathematics": 90, "visualization": 70}
        plan = AgentGraphPlanner().plan(
            required_artifacts=["canvas"],
            depth_requirements={"evaluation_profile": profile},
        )
        self.assertEqual(plan.depth_requirements["evaluation_profile"], profile)
        self.assertEqual(plan.depth_requirements["experience_context"]["target_profile"], profile)
