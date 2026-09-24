import unittest

from adaptive_agent import AdaptiveAgent, AdaptiveRequest
from agent_architect import AgentArchitect
from agent_catalog import AgentCatalog
from agent_factory import AgentBlueprint, AgentFactory


class TestAgentArchitect(unittest.TestCase):
    def _request(self, **changes):
        data = {
            "task": "build an interactive surface visualization",
            "requirements": ("surface_geometry", "tangent_plane"),
            "tools": ("python", "canvas"),
            "acceptance_criteria": ("verify_gradient",),
            "role": "surface visualization specialist",
            "context": {"math_depth": "doctorado"},
        }
        data.update(changes)
        return AdaptiveRequest(**data)

    def test_synthesis_creates_dormant_candidate(self):
        request = self._request()
        result = AgentArchitect(catalog=AgentCatalog()).synthesize(request)
        self.assertTrue(result.generated)
        self.assertEqual(result.candidate.status, "candidate")
        self.assertEqual(result.candidate.state, "sleeping")
        self.assertEqual(result.candidate.source, "agent_architect")

    def test_candidate_is_not_catalog_searchable(self):
        request = self._request()
        factory = AgentFactory()
        candidate = factory.create(
            agent_id="candidate-specialist",
            role=request.role,
            model_id="adaptive-default",
            tools=request.tools,
            context=request.requirements,
            actions=request.requirements,
        )
        with self.assertRaises(ValueError):
            AgentCatalog((candidate,))

    def test_validation_requires_evidence_when_requested(self):
        request = self._request()
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        with self.assertRaises(ValueError):
            factory.validate(candidate, require_evidence=True)
        validated = factory.validate(
            candidate,
            evidence={"passed": True, "checks": ["role", "tools", "acceptance"]},
            require_evidence=True,
        )
        self.assertEqual(validated.status, "validated")
        self.assertTrue(validated.validation["passed"])
        self.assertEqual(validated.validation["evidence"]["checks"][0], "role")

    def test_catalog_rejects_validated_agent_without_validation_evidence(self):
        request = self._request()
        candidate = AgentArchitect().synthesize(request).candidate
        validated_without_evidence = AgentBlueprint(
            id=candidate.id,
            role=candidate.role,
            model_id=candidate.model_id,
            tools=candidate.tools,
            context=candidate.context,
            state=candidate.state,
            memory=candidate.memory,
            evaluation=candidate.evaluation,
            actions=candidate.actions,
            source=candidate.source,
            status="validated",
        )
        with self.assertRaises(ValueError):
            AgentCatalog((validated_without_evidence,))

    def test_validation_is_required_before_registration(self):
        request = self._request()
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        validated = factory.validate(
            candidate,
            evidence={"passed": True, "checks": ["role", "tools", "acceptance"]},
            require_evidence=True,
        )
        catalog = AgentCatalog((validated,))
        self.assertEqual(catalog.get(validated.id).status, "validated")

    def test_reusable_agent_prevents_duplicate_generation(self):
        request = self._request()
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        reusable = factory.validate(
            candidate,
            evidence={"passed": True, "checks": ["role", "tools", "acceptance"]},
            require_evidence=True,
        )
        catalog = AgentCatalog((reusable,))
        result = AgentArchitect(factory=factory, catalog=catalog).synthesize(request)
        self.assertFalse(result.generated)
        self.assertEqual(result.reusable_agents, (reusable.id,))

    def test_explicit_activation_does_not_force_duplicate_when_reusable_exists(self):
        request = self._request(explicit_activation=True)
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        reusable = factory.validate(
            candidate,
            evidence={"passed": True, "checks": ["role", "tools", "acceptance"]},
            require_evidence=True,
        )
        catalog = AgentCatalog((reusable,))
        adaptive = AdaptiveAgent(catalog=catalog)
        decision = adaptive.decide(request)
        result = AgentArchitect(factory=factory, catalog=catalog).synthesize(
            request, decision=decision
        )
        self.assertFalse(result.generated)
        self.assertEqual(result.reusable_agents, (reusable.id,))

    def test_validated_pattern_is_evidence_but_does_not_validate_candidate(self):
        request = self._request()
        result = AgentArchitect().synthesize(
            request,
            validated_patterns=(
                {
                    "pattern_id": "pat-surface-1",
                    "status": "validated",
                    "task_family": "geometry",
                },
                {
                    "pattern_id": "pat-ignored",
                    "status": "candidate",
                    "task_family": "geometry",
                },
            ),
        )
        self.assertEqual(result.pattern_ids, ("pat-surface-1",))
        self.assertIn("validated_pattern:pat-surface-1", result.candidate.context)
        self.assertEqual(result.candidate.status, "candidate")
        self.assertEqual(result.candidate.state, "sleeping")

    def test_validated_strategy_evidence_reaches_candidate_without_validation(self):
        request = self._request()
        result = AgentArchitect().synthesize(
            request,
            validated_patterns=(
                {"pattern_id": "pat-surface-1", "status": "validated", "task_family": "geometry"},
            ),
            validated_strategies=(
                {
                    "strategy": {"strategy_id": "surface-v2", "status": "promoted"},
                    "selection_score": .94,
                    "validated_pattern_evidence": {"pattern_ids": ["pat-surface-1"]},
                },
                {
                    "strategy": {"strategy_id": "ignored", "status": "candidate"},
                },
            ),
        )
        self.assertEqual(result.strategy_ids, ("surface-v2",))
        self.assertIn("validated_strategy:surface-v2", result.candidate.context)
        self.assertEqual(result.candidate.status, "candidate")

    def test_architect_candidate_is_not_execution_eligible_until_validated(self):
        request = self._request()
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        self.assertEqual(candidate.status, "candidate")
        with self.assertRaises(ValueError):
            factory.activate(candidate)
        validated = factory.validate(
            candidate,
            evidence={"passed": True, "checks": ["role", "tools", "acceptance"]},
            require_evidence=True,
        )
        activated = factory.activate(validated)
        self.assertEqual(activated.state, "active")

    def test_tool_signals_select_specialist_role(self):
        canvas = AgentArchitect().synthesize(
            self._request(tools=("canvas", "python")),
        )
        self.assertEqual(canvas.candidate.role, "canvas-html specialist")

        proof = AgentArchitect().synthesize(
            self._request(tools=("sympy",), requirements=("formal_proof",)),
        )
        self.assertEqual(proof.candidate.role, "mathematical-proof specialist")

    def test_generation_is_deterministic_for_same_request(self):
        request = self._request()
        first = AgentArchitect().synthesize(request).candidate
        second = AgentArchitect().synthesize(request).candidate
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.to_dict(), second.to_dict())


if __name__ == "__main__":
    unittest.main()
