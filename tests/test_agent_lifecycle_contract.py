import json
import unittest

from agent_factory import AgentBlueprint, AgentFactory
from agent_catalog import AgentCatalog


class TestAgentLifecycleContract(unittest.TestCase):
    def _validated(self, agent_id="contract-specialist"):
        factory = AgentFactory()
        candidate = factory.create(
            agent_id=agent_id,
            role="contract specialist",
            model_id="test-model",
            tools=("python",),
            context=("verification",),
            actions=("verification",),
        )
        return factory.validate(
            candidate,
            evidence={
                "passed": True,
                "validator": "contract-test",
                "source_id": "eval-contract-001",
                "checks": ["verification"],
            },
        )

    def test_validation_provenance_survives_json_serialization(self):
        validated = self._validated()
        restored = AgentBlueprint(
            **{
                **json.loads(json.dumps(validated.to_dict())),
                "tools": tuple(validated.to_dict()["tools"]),
                "context": tuple(validated.to_dict()["context"]),
                "memory": tuple(validated.to_dict()["memory"]),
                "evaluation": tuple(validated.to_dict()["evaluation"]),
                "actions": tuple(validated.to_dict()["actions"]),
            }
        )
        self.assertEqual(
            restored.validation["evidence"]["source_id"],
            "eval-contract-001",
        )
        self.assertTrue(restored.validation["evidence"]["passed"])

    def test_catalog_registration_does_not_activate_agent(self):
        validated = self._validated()
        catalog = AgentCatalog()
        catalog.register(validated)
        stored = catalog.get(validated.id)
        self.assertEqual(stored.status, "validated")
        self.assertEqual(stored.state, "sleeping")

    def test_rejected_agent_cannot_register(self):
        factory = AgentFactory()
        candidate = factory.create(
            agent_id="rejected-specialist",
            role="contract specialist",
            model_id="test-model",
        )
        rejected = factory.reject(candidate)
        with self.assertRaises(ValueError):
            AgentCatalog((rejected,))

    def test_retired_agent_cannot_register(self):
        validated = self._validated()
        retired = AgentBlueprint(
            **{
                **validated.to_dict(),
                "tools": tuple(validated.tools),
                "context": tuple(validated.context),
                "memory": tuple(validated.memory),
                "evaluation": tuple(validated.evaluation),
                "actions": tuple(validated.actions),
                "state": "retired",
            }
        )
        with self.assertRaises(ValueError):
            AgentCatalog((retired,))

    def test_identical_duplicate_registration_is_idempotent(self):
        validated = self._validated()
        catalog = AgentCatalog()
        catalog.register(validated)
        catalog.register(validated)
        self.assertEqual(catalog.get(validated.id).to_dict(), validated.to_dict())

    def test_conflicting_duplicate_definition_is_rejected(self):
        validated = self._validated()
        catalog = AgentCatalog((validated,))
        conflicting = AgentBlueprint(
            **{
                **validated.to_dict(),
                "tools": ("python", "sympy"),
                "context": tuple(validated.context),
                "memory": tuple(validated.memory),
                "evaluation": tuple(validated.evaluation),
                "actions": tuple(validated.actions),
            }
        )
        with self.assertRaises(ValueError):
            catalog.register(conflicting)

    def test_catalog_registration_preserves_validation_evidence(self):
        validated = self._validated()
        catalog = AgentCatalog((validated,))
        stored = catalog.get(validated.id)
        self.assertEqual(
            stored.validation["evidence"]["source_id"],
            "eval-contract-001",
        )
        self.assertTrue(stored.validation["passed"])


if __name__ == "__main__":
    unittest.main()
