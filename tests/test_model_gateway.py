import unittest
from unittest.mock import patch
import model_gateway

class ModelGatewayTests(unittest.TestCase):
    def test_ollama_payload_and_response(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"message":{"content":"resultado"}}'
        with patch("model_gateway.urllib.request.urlopen", return_value=FakeResponse()) as call:
            spec = type("Spec", (), {"provider":"ollama","model":"demo","endpoint_env":"OLLAMA_BASE_URL","api_key_env":None})()
            result = model_gateway.invoke_model(spec, "hola")
            self.assertEqual(result["content"], "resultado")
            payload = call.call_args.args[0].data
            self.assertIn(b'"model": "demo"', payload)
