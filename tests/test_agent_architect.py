import unittest

from adaptive_agent import AdaptiveAgent, AdaptiveRequest
from agent_architect import AgentArchitect
from agent_catalog import AgentCatalog
from agent_factory import AgentFactory


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

    def test_validation_is_required_before_registration(self):
        request = self._request()
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        validated = factory.validate(candidate)
        catalog = AgentCatalog((validated,))
        self.assertEqual(catalog.get(validated.id).status, "validated")

    def test_reusable_agent_prevents_duplicate_generation(self):
        request = self._request()
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        reusable = factory.validate(candidate)
        catalog = AgentCatalog((reusable,))
        result = AgentArchitect(factory=factory, catalog=catalog).synthesize(request)
        self.assertFalse(result.generated)
        self.assertEqual(result.reusable_agents, (reusable.id,))

    def test_explicit_activation_does_not_force_duplicate_when_reusable_exists(self):
        request = self._request(explicit_activation=True)
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        reusable = factory.validate(candidate)
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

    def test_architect_candidate_is_not_execution_eligible_until_validated(self):
        request = self._request()
        factory = AgentFactory()
        candidate = AgentArchitect(factory=factory).synthesize(request).candidate
        self.assertEqual(candidate.status, "candidate")
        with self.assertRaises(ValueError):
            factory.activate(candidate)
        validated = factory.validate(candidate)
        activated = factory.activate(validated)
        self.assertEqual(activated.state, "active")

    def test_generation_is_deterministic_for_same_request(self):
        request = self._request()
        first = AgentArchitect().synthesize(request).candidate
        second = AgentArchitect().synthesize(request).candidate
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.to_dict(), second.to_dict())


if __name__ == "__main__":
    unittest.main()
