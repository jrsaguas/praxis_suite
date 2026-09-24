import unittest
from pathlib import Path
import tempfile
import json
import os
import http.client
import socketserver
import threading
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
            server.agent_runtime, "AgentRuntime"
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

    def test_agent_graph_execute_real_http_request(self):
        payload = {
            "task": "verificar una identidad algebraica",
            "chat_id": "chat-http",
            "evaluation_profile": {"mathematics": 90, "depth": 85},
            "task_family": "algebra",
            "required_artifacts": [],
            "max_retries": 0,
        }

        fake_plan = mock.Mock(name="plan")
        fake_trace = mock.Mock(status="completed")
        fake_trace.to_dict.return_value = {"status": "completed", "events": []}

        with mock.patch.object(
            server.investigation_store, "get_evaluation_profile", return_value={}
        ), mock.patch.object(
            server.learning_bridge, "build_experience_context", return_value={"references": []}
        ), mock.patch.object(
            server.agent_graph.AgentGraphPlanner, "plan", return_value=fake_plan
        ) as planner, mock.patch.object(
            server.learning_bridge, "make_runtime_experience_sink", return_value=mock.Mock()
        ) as sink_factory, mock.patch.object(
            server.agent_runtime, "AgentRuntime"
        ) as runtime_cls:
            runtime_cls.return_value.run.return_value = fake_trace
            with socketserver.ThreadingTCPServer(("127.0.0.1", 0), server.PraxisRequestHandler) as httpd:
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                try:
                    host, port = httpd.server_address
                    conn = http.client.HTTPConnection(host, port, timeout=5)
                    body = json.dumps(payload).encode("utf-8")
                    conn.request(
                        "POST",
                        "/api/agent-graph/execute",
                        body=body,
                        headers={
                            "Content-Type": "application/json",
                            "Content-Length": str(len(body)),
                        },
                    )
                    response = conn.getresponse()
                    response_body = json.loads(response.read().decode("utf-8"))
                    conn.close()
                finally:
                    httpd.shutdown()
                    thread.join(timeout=5)

        self.assertEqual(response.status, 200)
        self.assertEqual(response_body["status"], "completed")
        planner.assert_called_once()
        sink_factory.assert_called_once()
        runtime_cls.return_value.run.assert_called_once_with(
            fake_plan,
            initial_context=mock.ANY,
        )


    def test_restore_snapshot_route_creates_new_version_and_current_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            chat_id = "chat-restore"
            folder = "respuesta_001"
            response = Path(tmp) / chat_id / folder
            doc_dir = response / "entregables" / "documentos"
            doc_dir.mkdir(parents=True)
            (Path(tmp) / chat_id / "conversacion_metadata.json").write_text(
                json.dumps({
                    "id": chat_id,
                    "responses": [{
                        "folder": folder,
                        "version_id": "v-root",
                        "investigation_id": f"{chat_id}/{folder}",
                    }],
                }),
                encoding="utf-8",
            )
            md = doc_dir / "investigacion.md"
            html = doc_dir / "investigacion.html"
            md.write_text("# Versión 1", encoding="utf-8")
            html.write_text("<h1>Versión 1</h1>", encoding="utf-8")
            v1 = server.investigation_store.register_version(
                tmp, chat_id, folder, prompt="v1", title="Investigación",
                source="test", parent_version_id=None,
                artifact_types=["md", "html"],
            )
            md.write_text("# Versión 2", encoding="utf-8")
            html.write_text("<h1>Versión 2</h1>", encoding="utf-8")
            v2 = server.investigation_store.register_version(
                tmp, chat_id, folder, prompt="v2", title="Investigación",
                source="test", parent_version_id=v1["version_id"],
                artifact_types=["md", "html"],
            )
            self.assertNotEqual(v1["version_id"], v2["version_id"])

            payload = json.dumps({
                "chat_id": chat_id,
                "folder": folder,
                "version_id": v1["version_id"],
                "title": "Restauración",
            }).encode("utf-8")

            class Handler:
                def _read_body(self):
                    return payload
                def send_response(self, code):
                    self.response = code
                def send_header(self, *args):
                    pass
                def end_headers(self):
                    pass

            handler = Handler()
            handler.response = None
            handler.wfile = mock.Mock()

            with mock.patch.object(server.chat_manager, "CHATS_DIR", tmp):
                server.PraxisRequestHandler.handle_restore_investigation_snapshot(handler)

            self.assertEqual(handler.response, 200)
            result = json.loads(handler.wfile.write.call_args.args[0])
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["restored_from"], v1["version_id"])
            self.assertNotEqual(result["version"]["version_id"], v1["version_id"])
            self.assertEqual(result["version"]["parent_version_id"], v1["version_id"])
            self.assertEqual(md.read_text(encoding="utf-8"), "# Versión 1")
            self.assertEqual(html.read_text(encoding="utf-8"), "<h1>Versión 1</h1>")
            manifest = result["artifact_manifest"]
            self.assertEqual(manifest["version_id"], result["version"]["version_id"])
            self.assertEqual(
                next(a for a in manifest["artifacts"]
                     if a["path"] == "entregables/documentos/investigacion.md")["status"],
                "current",
            )

    def test_snapshot_preview_route_returns_historical_text_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            chat_id = "chat-preview-route"
            folder = "respuesta_001"
            response = Path(tmp) / chat_id / folder
            doc_dir = response / "entregables" / "documentos"
            doc_dir.mkdir(parents=True)
            (Path(tmp) / chat_id / "conversacion_metadata.json").write_text(
                json.dumps({
                    "id": chat_id,
                    "responses": [{
                        "folder": folder,
                        "version_id": "v-root",
                        "investigation_id": f"{chat_id}/{folder}",
                    }],
                }),
                encoding="utf-8",
            )
            md = doc_dir / "investigacion.md"
            md.write_text("# Histórico", encoding="utf-8")
            version = server.investigation_store.register_version(
                tmp, chat_id, folder, prompt="p", title="V1", source="test",
                artifact_types=["md"],
            )
            md.write_text("# Actual", encoding="utf-8")

            from urllib.parse import quote
            path = (
                f"/api/investigations/{quote(chat_id)}/{quote(folder)}"
                f"/snapshot/entregables/documentos/investigacion.md"
                f"?version_id={quote(version['version_id'])}"
            )

            class Handler:
                def __init__(self):
                    self.path = path
                    self.response = None
                    self.wfile = mock.Mock()
                def send_response(self, code):
                    self.response = code
                def send_header(self, *args):
                    pass
                def end_headers(self):
                    pass

            handler = Handler()
            with mock.patch.object(server.chat_manager, "CHATS_DIR", tmp):
                server.PraxisRequestHandler.do_GET(handler)

            self.assertEqual(handler.response, 200)
            payload = json.loads(handler.wfile.write.call_args.args[0])
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["artifact"]["content"], "# Histórico")
            self.assertEqual(md.read_text(encoding="utf-8"), "# Actual")

    def test_artifact_command_promotes_version_and_refreshes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            chat_id = "chat-chain"
            folder = "respuesta_001"
            response = Path(tmp) / chat_id / folder
            doc_dir = response / "entregables" / "documentos"
            doc_dir.mkdir(parents=True)
            (Path(tmp) / chat_id / "conversacion_metadata.json").write_text(
                json.dumps({
                    "id": chat_id,
                    "responses": [{
                        "folder": folder,
                        "version_id": "v-root",
                        "investigation_id": f"{chat_id}/{folder}",
                    }],
                }),
                encoding="utf-8",
            )

            payload = {
                "chat_id": chat_id,
                "folder": folder,
                "instruction": "actualiza el documento",
                "title": "Investigación",
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

            calls = [0]

            def fake_executor(*args, **kwargs):
                calls[0] += 1
                md = doc_dir / "investigacion.md"
                html = doc_dir / "investigacion.html"
                md.write_text(
                    f"# Versión actualizada {calls[0]}",
                    encoding="utf-8",
                )
                if calls[0] == 1:
                    html.write_text("<h1>Versión 1</h1>", encoding="utf-8")
                return {
                    "status": "ok",
                    "operation": "rebuild_documents",
                    "message": "ok",
                    "changed_files": [str(md)],
                    "artifact_types": ["md", "docx", "doc"],
                    "plan": {},
                }

            with mock.patch.object(server.chat_manager, "CHATS_DIR", tmp), \
                 mock.patch.object(
                     server.artifact_command_executor,
                     "execute_artifact_command",
                     side_effect=fake_executor,
                 ):
                server.PraxisRequestHandler.handle_artifact_command(handler)

                self.assertEqual(handler.response, 200)
                result = json.loads(handler.wfile.write.call_args.args[0])
                self.assertEqual(result["version"]["source"], "artifact_execution")
                manifest = result["artifact_manifest"]
                self.assertEqual(manifest["version_id"], result["version"]["version_id"])
                md_item = next(
                    a for a in manifest["artifacts"]
                    if a["path"] == "entregables/documentos/investigacion.md"
                )
                html_item = next(
                    a for a in manifest["artifacts"]
                    if a["path"] == "entregables/documentos/investigacion.html"
                )
                self.assertEqual(md_item["status"], "current")
                self.assertEqual(html_item["status"], "current")
                self.assertEqual(
                    md_item["source_md_sha256"],
                    manifest["source_md_sha256"],
                )

                saved = json.loads(
                    (Path(tmp) / chat_id / "conversacion_metadata.json").read_text(
                        encoding="utf-8"
                    )
                )
                response_meta = saved["responses"][0]
                self.assertEqual(response_meta["version_id"], result["version"]["version_id"])
                self.assertEqual(len(response_meta["execution_history"]), 1)

                handler.wfile.reset_mock()
                server.PraxisRequestHandler.handle_artifact_command(handler)
                self.assertEqual(handler.response, 200)
                second_result = json.loads(handler.wfile.write.call_args.args[0])
                self.assertNotEqual(
                    second_result["version"]["version_id"],
                    result["version"]["version_id"],
                )
                second_html = next(
                    a for a in second_result["artifact_manifest"]["artifacts"]
                    if a["path"] == "entregables/documentos/investigacion.html"
                )
                self.assertEqual(second_html["status"], "stale")

if __name__ == "__main__":
    unittest.main()
