import unittest

from adaptive_agent import AdaptiveRequest
from agent_catalog import AgentCatalog
from agent_factory import AgentFactory
from adaptive_graph import AdaptiveGraphBridge
from agent_runtime import AgentRuntime


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
            {"mathematical_resolver": {"proof"}},
            self._catalog(),
        )
        result = bridge.plan(
            AdaptiveRequest(task="resolver", requirements=("proof",)),
            requested_agents=("mathematical_resolver",),
        )
        self.assertFalse(result.decision.active)
        self.assertIn("mathematical_resolver", result.execution_plan.selected_agents)
        self.assertIn("final_auditor", result.execution_plan.selected_agents)
        self.assertIn("experience_evaluator", result.execution_plan.selected_agents)

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
        self.assertEqual(len(result.generated_candidates), 1)
        self.assertNotIn(result.generated_candidates[0], result.execution_plan.selected_agents)
        self.assertEqual(result.execution_plan.planning_metadata["adaptive_selection"]["generated_candidates"], list(result.generated_candidates))

    def test_adaptive_selection_is_recorded_in_runtime_trace(self):
        bridge = AdaptiveGraphBridge({}, self._catalog())
        result = bridge.plan(AdaptiveRequest(task="surface", requirements=("symbolic_geometry",), tools=("sympy",), role="surface geometry"))
        runtime = AgentRuntime(lambda task, context: {})
        trace = runtime.run(result.execution_plan)
        self.assertEqual(trace.artifacts["planning_metadata"]["adaptive_selection"]["reusable_agents"], ["surface_specialist"])
        self.assertEqual(trace.events[0].phase, "planning")
        self.assertEqual(trace.events[0].agent_id, "orchestrator")

    def test_validated_patterns_are_only_planning_evidence(self):
        bridge = AdaptiveGraphBridge({}, self._catalog())
        result = bridge.plan(
            AdaptiveRequest(task="surface", requirements=("symbolic_geometry",)),
            selected_patterns=[
                {
                    "pattern_id": "pat-valid",
                    "status": "validated",
                    "task_family": "geometry",
                    "selection": {"score": 0.91},
                    "source_record_ids": ["exp-1"],
                },
                {
                    "pattern_id": "pat-candidate",
                    "status": "candidate",
                    "task_family": "geometry",
                },
            ],
        )
        selected = result.execution_plan.planning_metadata["selected_patterns"]
        self.assertEqual([p["pattern_id"] for p in selected], ["pat-valid"])
        self.assertEqual(selected[0]["source_record_ids"], ["exp-1"])
        self.assertNotIn("pat-valid", result.execution_plan.selected_agents)

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
