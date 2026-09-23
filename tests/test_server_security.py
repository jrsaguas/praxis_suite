import unittest
from pathlib import Path
import tempfile
import json
import os
from unittest import mock

import server
from security_utils import safe_child_path, safe_filename


class RequestLimitTests(unittest.TestCase):
    def test_limit_rejects_oversized_content_length(self):
        class Headers(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        class R:
            headers = Headers({"Content-Length": str(server.MAX_REQUEST_BYTES + 1)})
            rfile = None
            def _read_body(self):
                return server.PraxisRequestHandler._read_body(self)
        with self.assertRaises(ValueError):
            R()._read_body()


class PathSafetyTests(unittest.TestCase):
    def test_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                safe_child_path(root, "..", "secret.txt")

    def test_filename_is_basename(self):
        self.assertEqual(safe_filename("../../secret.txt"), "secret.txt")


    def test_agent_graph_execute_handler_runs_runtime(self):
        payload = {
            "task": "verificar una identidad algebraica",
            "chat_id": "chat-1",
            "evaluation_profile": {"mathematics": 90, "depth": 85},
            "task_family": "algebra",
            "required_artifacts": [],
            "max_retries": 0,
        }

        class Handler:
            def _read_body(self):
                return json.dumps(payload).encode("utf-8")

            def send_response(self, code):
                self.response = code

            def send_header(self, *args):
                pass

            def end_headers(self):
                pass

        handler = Handler()
        handler.response = None
        handler.wfile = mock.Mock()

        fake_plan = mock.Mock(name="plan")
        fake_trace = mock.Mock(status="completed")
        fake_trace.to_dict.return_value = {"status": "completed"}

        with mock.patch.object(
            server.investigation_store, "get_evaluation_profile", return_value={}
        ), mock.patch.object(
            server.learning_bridge, "build_experience_context", return_value={"references": []}
        ), mock.patch.object(
            server.agent_graph.AgentGraphPlanner, "plan", return_value=fake_plan
        ) as planner, mock.patch.object(
            server.learning_bridge, "make_runtime_experience_sink", return_value=mock.Mock()
        ) as sink_factory, mock.patch.object(
            server.agent_runtime.AgentRuntime
        ) as runtime_cls:
            runtime_cls.return_value.run.return_value = fake_trace
            server.PraxisRequestHandler.handle_agent_graph_execute(handler)

        self.assertEqual(handler.response, 200)
        handler.wfile.write.assert_called_once()
        planner.assert_called_once()
        self.assertEqual(
            planner.call_args.kwargs["depth_requirements"]["evaluation_profile"],
            payload["evaluation_profile"],
        )
        sink_factory.assert_called_once()
        runtime_cls.return_value.run.assert_called_once_with(
            fake_plan,
            initial_context=mock.ANY,
        )

if __name__ == "__main__":
    unittest.main()
