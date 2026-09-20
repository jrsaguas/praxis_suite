import json
import tempfile
import unittest
from pathlib import Path

from investigation_store import list_versions, register_version, record_execution, promote_execution_to_version


class InvestigationStoreTests(unittest.TestCase):
    def test_register_version_reuses_existing_response_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            chats = Path(tmp) / "chats"
            chat = chats / "chat-1"
            chat.mkdir(parents=True)
            meta = {
                "id": "chat-1",
                "responses": [{
                    "folder": "respuesta_001",
                    "title": "Original",
                    "prompt": "investiga superficies",
                    "timestamp": "2026-09-19 00:00:00",
                    "investigation_id": "chat-1/respuesta_001",
                    "version_id": "v-root",
                    "parent_version_id": None,
                    "version_source": "pipeline",
                    "artifact_types": ["md", "html", "simulador"],
                    "evaluation": None,
                }],
            }
            (chat / "conversacion_metadata.json").write_text(
                json.dumps(meta), encoding="utf-8"
            )
            version = register_version(
                str(chats),
                "chat-1",
                "respuesta_001",
                prompt="genera otro Canvas",
                title="Original",
                source="artifact_command",
                commands=["genera otro Canvas"],
            )
            self.assertEqual(version["parent_version_id"], "v-root")
            versions = list_versions(str(chats), "chat-1", "respuesta_001")
            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0]["source"], "artifact_command")
            self.assertEqual(versions[0]["commands"], ["genera otro Canvas"])
            saved = json.loads((chat / "conversacion_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["responses"][0]["version_id"], version["version_id"])

    def test_execution_history_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            chats = Path(tmp) / "chats"
            chat = chats / "chat-1"
            chat.mkdir(parents=True)
            meta = {"id": "chat-1", "responses": [{"folder": "respuesta_001"}]}
            (chat / "conversacion_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
            event = record_execution(
                str(chats), "chat-1", "respuesta_001",
                operation="generate_canvas",
                instruction="genera un Canvas",
                status="ok",
                changed_files=["simulador.html"],
                artifact_types=["simulador"],
            )
            saved = json.loads((chat / "conversacion_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(event["status"], "ok")
            self.assertEqual(saved["responses"][0]["execution_history"][0]["operation"], "generate_canvas")
    def test_failed_execution_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            chats = Path(tmp) / "chats"
            chat = chats / "chat-1"
            chat.mkdir(parents=True)
            meta = {"id": "chat-1", "responses": [{"folder": "respuesta_001", "version_id": "v-root"}]}
            (chat / "conversacion_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
            with self.assertRaises(ValueError):
                promote_execution_to_version(
                    str(chats), "chat-1", "respuesta_001",
                    event={"status": "failed", "instruction": "corrige Canvas"},
                    prompt="corrige Canvas", title="Canvas",
                )

    def test_successful_execution_promotes_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            chats = Path(tmp) / "chats"
            chat = chats / "chat-1"
            chat.mkdir(parents=True)
            meta = {"id": "chat-1", "responses": [{"folder": "respuesta_001", "version_id": "v-root"}]}
            (chat / "conversacion_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
            version = promote_execution_to_version(
                str(chats), "chat-1", "respuesta_001",
                event={"status": "ok", "instruction": "genera Canvas", "artifact_types": ["simulador"]},
                prompt="genera Canvas", title="Canvas",
            )
            self.assertEqual(version["status"], "succeeded")
            self.assertEqual(version["source"], "artifact_execution")

    def test_version_navigation_does_not_mutate_history(self):
        with tempfile.TemporaryDirectory() as td:
            chat_id = "chat_nav"
            folder = "respuesta_nav"
            self._write_response(td, chat_id, folder)
            first = investigation_store.register_version(
                td, chat_id, folder, prompt="p1", title="T1", source="pipeline"
            )
            second = investigation_store.register_version(
                td, chat_id, folder, prompt="p2", title="T2", source="artifact_execution"
            )
            nav = investigation_store.navigate_versions(td, chat_id, folder, first["version_id"])
            self.assertEqual(nav["current"]["version_id"], first["version_id"])
            self.assertIsNone(nav["previous"])
            self.assertEqual(nav["next"]["version_id"], second["version_id"])
            self.assertEqual(len(investigation_store.list_versions(td, chat_id, folder)), 2)


if __name__ == "__main__":
    unittest.main()
