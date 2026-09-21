"""Persistent experience records for controlled Praxis learning.

The store is deliberately append-only and lives in the existing chat metadata
area. It records outcomes; it does not modify strategies automatically.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from security_utils import validate_component, safe_child_path


def _path(chats_dir: str, chat_id: str) -> str:
    chat_id = validate_component(chat_id, "chat_id")
    return safe_child_path(safe_child_path(chats_dir, chat_id), "experiencias.json")


def _load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"schema_version": 1, "records": []}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("El almacén de experiencias debe ser un objeto JSON.")
    data.setdefault("schema_version", 1)
    data.setdefault("records", [])
    return data


def append_record(
    chats_dir: str,
    chat_id: str,
    *,
    task_fingerprint: str,
    evaluation: Dict[str, Any],
    strategy_id: str,
    investigation_id: Optional[str] = None,
    version_id: Optional[str] = None,
    proposal: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    path = _path(chats_dir, chat_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = _load(path)
    record = {
        "record_id": f"exp-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_fingerprint": task_fingerprint,
        "investigation_id": investigation_id,
        "version_id": version_id,
        "strategy_id": strategy_id,
        "evaluation": evaluation,
        "proposal": proposal,
        "metadata": metadata or {},
    }
    data["records"].append(record)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return record


def list_records(chats_dir: str, chat_id: str, *, limit: int = 100) -> list[Dict[str, Any]]:
    path = _path(chats_dir, chat_id)
    records = _load(path)["records"]
    return records[-max(1, int(limit)):]


def summarize_strategies(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for record in records:
        strategy = record.get("strategy_id", "unknown")
        evaluation = record.get("evaluation") or {}
        bucket = summary.setdefault(strategy, {"count": 0.0, "score_sum": 0.0, "accepted": 0.0})
        bucket["count"] += 1
        bucket["score_sum"] += float(evaluation.get("score", 0.0))
        if evaluation.get("consistent"):
            bucket["accepted"] += 1
    for bucket in summary.values():
        count = bucket["count"]
        bucket["mean_score"] = round(bucket["score_sum"] / count, 4) if count else 0.0
        bucket["accept_rate"] = round(bucket["accepted"] / count, 4) if count else 0.0
    return summary
