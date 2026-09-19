"""Persistence adapter for investigation/version metadata.

It reuses the existing chat metadata JSON. No parallel folder hierarchy is
created and no artifact is duplicated.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from security_utils import validate_component, safe_child_path
from investigation_model import InvestigationVersion


def _meta_path(chats_dir: str, chat_id: str) -> str:
    chat_id = validate_component(chat_id, "chat_id")
    return safe_child_path(
        safe_child_path(chats_dir, chat_id),
        "conversacion_metadata.json",
    )


def _load(chats_dir: str, chat_id: str) -> Dict[str, Any]:
    path = _meta_path(chats_dir, chat_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Chat metadata not found: {chat_id}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(chats_dir: str, chat_id: str, meta: Dict[str, Any]) -> None:
    path = _meta_path(chats_dir, chat_id)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)


def get_response(meta: Dict[str, Any], folder: str) -> Optional[Dict[str, Any]]:
    for response in meta.get("responses", []):
        if response.get("folder") == folder:
            return response
    return None


def register_version(
    chats_dir: str,
    chat_id: str,
    folder: str,
    *,
    prompt: str,
    title: str,
    source: str = "pipeline",
    parent_version_id: Optional[str] = None,
    commands: Optional[list[str]] = None,
    references: Optional[list[str]] = None,
    artifact_types: Optional[list[str]] = None,
) -> Dict[str, Any]:
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")

    investigation_id = response.get(
        "investigation_id",
        f"{chat_id}/{folder}",
    )
    version = InvestigationVersion.create(
        investigation_id=investigation_id,
        prompt=prompt,
        title=title,
        parent_version_id=parent_version_id or response.get("version_id"),
        response_folder=folder,
        source=source,
        commands=commands,
        references=references,
        artifact_types=artifact_types or response.get("artifact_types", []),
    )
    response["version_id"] = version.version_id
    response["parent_version_id"] = version.parent_version_id
    response["version_source"] = version.source
    response.setdefault("version_history", []).append(version.to_dict())
    response.setdefault("commands", []).extend(commands or [])
    response.setdefault("references", []).extend(references or [])
    _save(chats_dir, chat_id, meta)
    return version.to_dict()


def list_versions(chats_dir: str, chat_id: str, folder: str) -> list[Dict[str, Any]]:
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    history = response.get("version_history", [])
    if history:
        return history
    # Legacy response: expose the current metadata as a root version without
    # modifying the file until a real edit is registered.
    return [{
        "investigation_id": response.get("investigation_id", f"{chat_id}/{folder}"),
        "version_id": response.get("version_id"),
        "parent_version_id": response.get("parent_version_id"),
        "created_at": response.get("timestamp"),
        "source": response.get("version_source", "pipeline"),
        "prompt": response.get("prompt", ""),
        "title": response.get("title", folder),
        "response_folder": folder,
        "commands": response.get("commands", []),
        "references": response.get("references", []),
        "evaluation": response.get("evaluation"),
        "artifact_types": response.get("artifact_types", []),
    }]
