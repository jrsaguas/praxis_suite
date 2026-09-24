import unittest

from adaptive_agent import AdaptiveAgent, AdaptiveRequest
from agent_factory import AgentFactory
from flow_composer import FlowComposer
from agent_catalog import AgentCatalog


class AdaptiveAgentTests(unittest.TestCase):
    def test_reusable_validated_agent_is_preferred_before_generation(self):
        factory = AgentFactory()
        reusable = factory.validate(factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
            tools=("sympy",),
            actions=("symbolic_geometry",),
            context=("surface",),
        ))
        catalog = AgentCatalog((reusable,))
        decision = AdaptiveAgent({}, catalog).decide(AdaptiveRequest(
            task="surface",
            requirements=("symbolic_geometry",),
            tools=("sympy",),
            role="surface geometry",
        ))
        self.assertTrue(decision.active)
        self.assertEqual(decision.reusable_agents, ("surface_specialist",))
        self.assertFalse(decision.generated_agent_required)

    def test_adaptive_agent_is_inactive_when_static_capabilities_cover_request(self):
        agent = AdaptiveAgent({"resolver": {"proof", "python"}})
        decision = agent.decide(AdaptiveRequest(
            task="resolver",
            requirements=("proof",),
        ))
        self.assertFalse(decision.active)
        self.assertEqual(decision.reason, "static_graph_sufficient")

    def test_adaptive_agent_activates_for_missing_capability(self):
        agent = AdaptiveAgent({"resolver": {"proof"}})
        decision = agent.decide(AdaptiveRequest(
            task="resolver",
            requirements=("proof", "symbolic_geometry"),
        ))
        self.assertTrue(decision.active)
        self.assertEqual(decision.missing_requirements, ("symbolic_geometry",))

    def test_explicit_activation_does_not_require_missing_capability(self):
        decision = AdaptiveAgent({}).decide(AdaptiveRequest(
            task="specialized",
            explicit_activation=True,
        ))
        self.assertTrue(decision.active)
        self.assertEqual(decision.reason, "explicit_activation")


class AgentFactoryTests(unittest.TestCase):
    def test_factory_creates_sleeping_candidate(self):
        agent = AgentFactory().create(
            agent_id="surface_specialist",
            role="specialized surface geometry",
            model_id="ollama-qwen",
            tools=("sympy", "python"),
            context=("surface",),
            memory=("accepted_surface_patterns",),
            evaluation=("math_code_alignment",),
            actions=("solve", "verify"),
        )
        self.assertEqual(agent.state, "sleeping")
        self.assertEqual(agent.status, "candidate")
        self.assertEqual(agent.tools, ("sympy", "python"))

    def test_factory_requires_validation_before_activation(self):
        factory = AgentFactory()
        agent = factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
        )
        with self.assertRaises(ValueError):
            factory.activate(agent)
        validated = factory.validate(agent)
        active = factory.activate(validated)
        self.assertEqual(active.status, "validated")
        self.assertEqual(active.state, "active")


class FlowComposerTests(unittest.TestCase):
    def test_inactive_adaptation_keeps_static_flow(self):
        decision = AdaptiveAgent({"resolver": {"proof"}}).decide(
            AdaptiveRequest(task="x", requirements=("proof",))
        )
        flow = FlowComposer().compose(("intent_router", "resolver"), decision)
        self.assertEqual(flow.agents, ("intent_router", "resolver"))
        self.assertFalse(flow.adaptive_active)

    def test_validated_generated_agent_is_inserted_without_replacing_existing_roles(self):
        factory = AgentFactory()
        generated = factory.validate(factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
        ))
        decision = AdaptiveAgent({}).decide(
            AdaptiveRequest(task="x", explicit_activation=True)
        )
        flow = FlowComposer().compose(
            ("intent_router", "resolver"),
            decision,
            (generated,),
        )
        self.assertTrue(flow.adaptive_active)
        self.assertEqual(
            flow.agents,
            ("intent_router", "resolver", "surface_specialist"),
        )
        self.assertEqual(flow.generated_agents, ("surface_specialist",))


if __name__ == "__main__":
    unittest.main()
