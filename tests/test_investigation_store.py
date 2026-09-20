import json
import tempfile
import unittest
from pathlib import Path

from investigation_store import list_versions, register_version, record_execution


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

if __name__ == "__main__":
    unittest.main()
