import unittest

from agent_architect import AgentArchitect
from agent_factory import AgentFactory
from agent_catalog import AgentCatalog
from agent_validation import AgentValidationGate


class TestAgentValidation(unittest.TestCase):
    def _candidate(self):
        return AgentArchitect().synthesize(
            __import__("adaptive_agent").AdaptiveRequest(
                task="validate a reusable specialist",
                requirements=("verification",),
                tools=("sympy",),
                role="mathematical-proof specialist",
            )
        ).candidate

    def test_missing_evaluation_cannot_validate(self):
        candidate = self._candidate()
        gate = AgentValidationGate()
        with self.assertRaises(ValueError):
            gate.validate(candidate, {}, source_id="eval-000")

    def test_failing_evaluation_cannot_validate(self):
        candidate = self._candidate()
        evaluation = {
            "consistent": False,
            "score": 0.95,
            "errors": ["review failure"],
            "required_retries": ["review failure"],
            "recommendation": "RETRY",
        }
        with self.assertRaises(ValueError):
            gate = AgentValidationGate()
            gate.validate(candidate, evaluation, source_id="eval-001")

    def test_passing_evaluation_validates_with_provenance(self):
        candidate = self._candidate()
        evaluation = {
            "consistent": True,
            "score": 0.92,
            "errors": [],
            "required_retries": [],
            "recommendation": "ACCEPT",
            "reasons": ["all declared checks passed"],
        }
        validated = AgentValidationGate().validate(
            candidate, evaluation, source_id="eval-002", checks=("quality", "verification")
        )
        self.assertEqual(validated.status, "validated")
        evidence = validated.validation["evidence"]
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["source_id"], "eval-002")
        self.assertEqual(evidence["validator"], "agent_validation_gate")
        self.assertEqual(evidence["evaluation"]["score"], 0.92)
        self.assertEqual(evidence["gate"]["checks"]["minimum_score"], True)

    def test_validation_provenance_survives_catalog_registration(self):
        candidate = self._candidate()
        evaluation = {
            "consistent": True,
            "score": 0.90,
            "errors": [],
            "required_retries": [],
            "recommendation": "ACCEPT",
        }
        validated = AgentValidationGate().validate(candidate, evaluation, source_id="eval-003")
        catalog = AgentCatalog((validated,))
        stored = catalog.get(validated.id)
        self.assertEqual(stored.validation["evidence"]["source_id"], "eval-003")
        self.assertEqual(stored.state, "sleeping")

    def test_threshold_is_explicit(self):
        candidate = self._candidate()
        evaluation = {
            "consistent": True,
            "score": 0.79,
            "errors": [],
            "required_retries": [],
            "recommendation": "ACCEPT",
        }
        with self.assertRaises(ValueError):
            AgentValidationGate(minimum_score=0.80).validate(
                candidate, evaluation, source_id="eval-004"
            )


if __name__ == "__main__":
    unittest.main()
