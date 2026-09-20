import unittest
from agent_adapters import adapter_for, execute_document


class AgentAdapterTests(unittest.TestCase):
    def test_existing_capabilities_are_bound_to_roles(self):
        self.assertIsNotNone(adapter_for("canvas_engineer"))
        self.assertIsNotNone(adapter_for("document_engineer"))

    def test_document_adapter_preserves_markdown(self):
        md = "$$\\frac{1}{2}$$"
        result = execute_document(None, {"markdown": md})
        self.assertEqual(result["markdown"], md)
        self.assertEqual(result["artifact_type"], "markdown")


if __name__ == "__main__":
    unittest.main()
