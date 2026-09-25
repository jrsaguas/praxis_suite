import unittest

from agent_artifacts import parse_structured_response, merge_model_artifacts

class StructuredArtifactTests(unittest.TestCase):
    def test_valid_json_becomes_explicit_artifacts(self):
        content = '{"derivation":"x=1","assumptions":["x real"],"solution":"1","verification_certificate":{"passed":true}}'
        artifacts, meta = parse_structured_response("mathematical_resolver", content)
        self.assertTrue(meta["structured"])
        self.assertEqual(artifacts["solution"], "1")
        self.assertEqual(meta["evidence_origin"], "model_self_report")

    def test_fenced_json_is_accepted_but_marked_self_reported(self):
        content = "```json\n{\"python_code\":\"print(1)\",\"numeric_checks\":{\"passed\":true}}\n```"
        output = merge_model_artifacts({"content": content, "provider": "ollama", "model": "x"}, "python_visualizer")
        self.assertEqual(output["python_code"], "print(1)")
        self.assertFalse(output["evidence_provenance"]["authoritative"])

    def test_malformed_json_does_not_create_artifacts(self):
        artifacts, meta = parse_structured_response("mathematical_resolver", '{"solution":')
        self.assertEqual(artifacts, {})
        self.assertFalse(meta["structured"])
        self.assertIn("invalid_json", meta["parse_error"])

    def test_prose_does_not_create_artifacts(self):
        artifacts, meta = parse_structured_response("research_specialist", "Aquí están mis fuentes: https://example.test")
        self.assertEqual(artifacts, {})
        self.assertFalse(meta["structured"])

    def test_unknown_agent_keeps_raw_response_only(self):
        output = merge_model_artifacts({"content": "plain response"}, "intent_router")
        self.assertEqual(output["agent_response"], "plain response")
        self.assertNotIn("evidence_provenance", output)

if __name__ == "__main__":
    unittest.main()
