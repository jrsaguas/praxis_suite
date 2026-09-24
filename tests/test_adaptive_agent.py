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
        ), evidence={"passed": True, "checks": ["legacy-test"]})
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
        validated = factory.validate(agent, evidence={"passed": True, "checks": ["legacy-test"]})
        active = factory.activate(validated)
        self.assertEqual(active.status, "validated")
        self.assertEqual(active.state, "active")

    def test_rejected_candidate_cannot_be_activated(self):
        factory = AgentFactory()
        candidate = factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
        )
        rejected = factory.reject(candidate)
        self.assertEqual(rejected.status, "rejected")
        with self.assertRaises(ValueError):
            factory.activate(rejected)

    def test_validated_agent_can_be_reused_without_activation(self):
        factory = AgentFactory()
        validated = factory.validate(factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
            actions=("surface",),
        ), evidence={"passed": True, "checks": ["legacy-test"]})
        catalog = AgentCatalog()
        catalog.register(validated)
        self.assertEqual(
            catalog.search(requirements=("surface",), role="surface geometry")[0].agent_id,
            "surface_specialist",
        )
        self.assertEqual(catalog.get("surface_specialist").state, "sleeping")


class AgentCatalogTests(unittest.TestCase):
    def test_catalog_rejects_unvalidated_candidate(self):
        candidate = AgentFactory().create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
        )
        with self.assertRaises(ValueError):
            AgentCatalog((candidate,))

    def test_catalog_rejects_retired_agent(self):
        validated = AgentFactory().validate(AgentFactory().create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
        ), evidence={"passed": True, "checks": ["legacy-test"]})
        retired = type(validated)(**{
            **validated.to_dict(),
            "state": "retired",
            "tools": tuple(validated.tools),
            "context": tuple(validated.context),
            "memory": tuple(validated.memory),
            "evaluation": tuple(validated.evaluation),
            "actions": tuple(validated.actions),
        })
        with self.assertRaises(ValueError):
            AgentCatalog((retired,))


class FlowComposerTests(unittest.TestCase):
    def test_inactive_adaptation_keeps_static_flow(self):
        decision = AdaptiveAgent({"resolver": {"proof"}}).decide(
            AdaptiveRequest(task="x", requirements=("proof",))
        )
        flow = FlowComposer().compose(("intent_router", "resolver"), decision)
        self.assertEqual(flow.agents, ("intent_router", "resolver"))
        self.assertFalse(flow.adaptive_active)

    def test_candidate_never_enters_composed_flow(self):
        factory = AgentFactory()
        candidate = factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
        )
        decision = AdaptiveAgent({}).decide(
            AdaptiveRequest(task="x", explicit_activation=True)
        )
        flow = FlowComposer().compose(
            ("intent_router", "resolver"), decision, (candidate,)
        )
        self.assertEqual(flow.agents, ("intent_router", "resolver"))
        self.assertEqual(flow.generated_agents, ())

    def test_validated_generated_agent_is_inserted_without_replacing_existing_roles(self):
        factory = AgentFactory()
        generated = factory.validate(factory.create(
            agent_id="surface_specialist",
            role="surface geometry",
            model_id="ollama-qwen",
        ), evidence={"passed": True, "checks": ["legacy-test"]})
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
