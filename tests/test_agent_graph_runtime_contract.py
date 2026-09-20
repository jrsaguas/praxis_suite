import unittest
import json
from agent_graph import AgentGraphPlanner
from mathematical_depth import MathematicalDepthProfile
from operational_context import build_operational_context


class AgentGraphRuntimeContractTests(unittest.TestCase):
    def test_doctoral_canvas_plan_contains_full_operational_context(self):
        profile = MathematicalDepthProfile.preset("doctorado")
        depth = {
            "requirements": profile.requirements(),
        }
        plan = AgentGraphPlanner().plan(
            required_artifacts=["canvas", "python"],
            depth_requirements=depth["requirements"],
        )
        ids = set(plan.selected_agents)
        self.assertTrue({"foundation_analyst","mathematical_resolver","proof_specialist",
                         "representation_designer","python_visualizer","canvas_engineer",
                         "code_reviewer","research_specialist"} <= ids)

    def test_context_is_serializable(self):
        context = build_operational_context(
            task="límite y derivada",
            investigation_id="chat/a",
            strategy_context={"strategy_ids":["s1"],"operational_instructions":["mostrar teoría"]},
        )
        json.dumps(context, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
