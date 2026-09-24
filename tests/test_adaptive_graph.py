import unittest

from adaptive_agent import AdaptiveRequest
from agent_catalog import AgentCatalog
from agent_factory import AgentFactory
from adaptive_graph import AdaptiveGraphBridge


class AdaptiveGraphBridgeTests(unittest.TestCase):
    def _catalog(self):
        factory = AgentFactory()
        agent = factory.validate(factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
            tools=("sympy",),
            context=("surface",),
            evaluation=("math_code_alignment",),
            actions=("symbolic_geometry",),
        ))
        return AgentCatalog((agent,))

    def test_static_graph_does_not_activate_adaptive_stage(self):
        bridge = AdaptiveGraphBridge(
            {"resolver": {"proof"}},
            self._catalog(),
        )
        result = bridge.plan(
            AdaptiveRequest(task="resolver", requirements=("proof",)),
            requested_agents=("resolver",),
        )
        self.assertFalse(result.decision.active)
        self.assertEqual(result.execution_plan.selected_agents, (
            "resolver",
            "final_auditor",
            "experience_evaluator",
        ))

    def test_reusable_agent_enters_existing_graph_as_planned_role(self):
        bridge = AdaptiveGraphBridge({}, self._catalog())
        result = bridge.plan(AdaptiveRequest(
            task="surface",
            requirements=("symbolic_geometry",),
            tools=("sympy",),
            role="surface geometry",
        ))
        self.assertTrue(result.decision.active)
        self.assertEqual(result.decision.reusable_agents, ("surface_specialist",))
        self.assertIn("surface_specialist", result.execution_plan.selected_agents)

    def test_unavailable_capability_does_not_create_or_activate_candidate(self):
        bridge = AdaptiveGraphBridge({})
        result = bridge.plan(AdaptiveRequest(
            task="new",
            requirements=("unavailable_capability",),
        ))
        self.assertTrue(result.decision.active)
        self.assertTrue(result.decision.generated_agent_required)
        self.assertNotIn("unavailable_capability", result.execution_plan.selected_agents)
        self.assertFalse(result.generated_candidates)

    def test_dynamic_reusable_agent_is_deterministically_planned(self):
        bridge = AdaptiveGraphBridge({}, self._catalog())
        first = bridge.plan(AdaptiveRequest(
            task="surface",
            requirements=("symbolic_geometry",),
            tools=("sympy",),
            role="surface geometry",
        ))
        second = bridge.plan(AdaptiveRequest(
            task="surface",
            requirements=("symbolic_geometry",),
            tools=("sympy",),
            role="surface geometry",
        ))
        self.assertEqual(first.execution_plan.selected_agents, second.execution_plan.selected_agents)
        self.assertEqual(first.execution_plan.selected_agents.count("surface_specialist"), 1)


if __name__ == "__main__":
    unittest.main()
