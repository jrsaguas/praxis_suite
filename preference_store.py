"""Persistent, auditable user preference profiles.

Explicit preferences are distinguished from inferred tendencies. Inference is
evidence only and never silently replaces an explicit user setting.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from investigation_model import DIMENSIONS
from preference_profiles import PreferenceProfile
from security_utils import validate_component, safe_child_path


def _path(chats_dir: str, chat_id: str) -> str:
    chat_id = validate_component(chat_id, "chat_id")
    return safe_child_path(safe_child_path(chats_dir, chat_id), "preferencias.json")


def _load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"schema_version": 1, "explicit": {}, "inferred": {}, "history": []}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("El almacén de preferencias debe ser un objeto JSON.")
    data.setdefault("schema_version", 1)
    data.setdefault("explicit", {})
    data.setdefault("inferred", {})
    data.setdefault("history", [])
    return data


def save_explicit(chats_dir: str, chat_id: str, percentages: Mapping[str, int], *, source: str = "user") -> Dict[str, Any]:
    profile = PreferenceProfile.from_percentages(percentages)
    path = _path(chats_dir, chat_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = _load(path)
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "profile": profile.to_dict(),
    }
    data["explicit"] = entry
    data["history"].append({"kind": "explicit", **entry})
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return entry


def save_inferred(chats_dir: str, chat_id: str, percentages: Mapping[str, int], *, evidence_ids: list[str], confidence: float) -> Dict[str, Any]:
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    profile = PreferenceProfile.from_percentages(percentages)
    path = _path(chats_dir, chat_id)
    data = _load(path)
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "profile": profile.to_dict(),
        "evidence_ids": list(dict.fromkeys(map(str, evidence_ids))),
        "confidence": float(confidence),
    }
    data["inferred"] = entry
    data["history"].append({"kind": "inferred", **entry})
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return entry


def load(chats_dir: str, chat_id: str) -> Dict[str, Any]:
    return _load(_path(chats_dir, chat_id))


def effective_profile(chats_dir: str, chat_id: str) -> Optional[PreferenceProfile]:
    data = load(chats_dir, chat_id)
    explicit = data.get("explicit") or {}
    if explicit.get("profile"):
        from preference_profiles import preference_from_dict
        return preference_from_dict(explicit["profile"])
    inferred = data.get("inferred") or {}
    if inferred.get("profile") and float(inferred.get("confidence", 0)) >= 0.75:
        from preference_profiles import preference_from_dict
        return preference_from_dict(inferred["profile"])
    return None
