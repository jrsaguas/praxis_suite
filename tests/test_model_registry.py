import os
import unittest
from model_registry import ModelRegistry, ModelRouter

class ModelRegistryTests(unittest.TestCase):
    def test_roles_resolve_to_explicit_models(self):
        router = ModelRouter()
        plan = router.resolve_plan(["foundation_analyst", "final_auditor"])
        self.assertEqual(plan["foundation_analyst"].model_id, "ollama-qwen")
        self.assertEqual(plan["final_auditor"].model_id, "gemini-default")

    def test_override_changes_only_selected_role(self):
        router = ModelRouter()
        self.assertEqual(router.resolve("final_auditor", "ollama-llama").model_id, "ollama-llama")
        self.assertEqual(router.resolve("foundation_analyst").model_id, "ollama-qwen")

    def test_public_config_contains_no_api_keys(self):
        data = ModelRegistry().public_config()
        self.assertTrue(data)
        self.assertTrue(all("api_key" not in item for item in data))
