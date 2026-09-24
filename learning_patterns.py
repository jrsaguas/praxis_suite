"""Controlled extraction of reusable patterns from accepted Praxis experiences.

Patterns are evidence-backed candidates. They never become agents or strategies
automatically; explicit validation is required before they can be reused.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from security_utils import safe_child_path, validate_component


def _path(chats_dir: str, chat_id: str) -> str:
    return safe_child_path(
        safe_child_path(chats_dir, validate_component(chat_id, "chat_id")),
        "patrones.json",
    )


def _load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"schema_version": 1, "patterns": []}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("El almacén de patrones debe ser un objeto JSON.")
    data.setdefault("schema_version", 1)
    data.setdefault("patterns", [])
    return data


def _pattern_id(task_family: str, strategy_id: str, signature: Dict[str, Any]) -> str:
    raw = json.dumps(
        {"task_family": task_family, "strategy_id": strategy_id, "signature": signature},
        sort_keys=True,
        ensure_ascii=False,
    )
    return "pat-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def propose_from_experience(
    records: Iterable[Dict[str, Any]],
    *,
    minimum_score: float = 0.75,
    minimum_rating: Optional[int] = None,
) -> list[Dict[str, Any]]:
    """Derive pattern candidates only from explicitly accepted experiences."""
    proposals: list[Dict[str, Any]] = []
    for record in records:
        if record.get("reuse_status") != "accepted":
            continue
        evaluation = record.get("evaluation") or {}
        if float(evaluation.get("score", 0.0)) < float(minimum_score):
            continue
        feedback = record.get("user_feedback") or {}
        rating = feedback.get("rating")
        if minimum_rating is not None and (rating is None or int(rating) < int(minimum_rating)):
            continue
        metadata = record.get("metadata") or {}
        planning = metadata.get("planning_context") or {}
        signature = {
            "selected_reusable_agents": tuple(planning.get("selected_reusable_agents", [])),
            "execution_agents": tuple(planning.get("execution_agents", [])),
            "mathematical_depth": planning.get("mathematical_depth") or {},
        }
        task_family = str(metadata.get("task_family") or "unknown")
        strategy_id = str(record.get("strategy_id") or "unknown")
        proposals.append({
            "pattern_id": _pattern_id(task_family, strategy_id, signature),
            "status": "candidate",
            "source_record_ids": [str(record.get("record_id"))],
            "task_family": task_family,
            "strategy_id": strategy_id,
            "signature": signature,
            "evidence": {
                "evaluation_score": float(evaluation.get("score", 0.0)),
                "user_rating": rating,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return proposals


def persist_candidates(
    chats_dir: str,
    chat_id: str,
    candidates: Iterable[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """Append pattern candidates without validating or activating them."""
    path = _path(chats_dir, chat_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = _load(path)
    existing = {p.get("pattern_id") for p in data["patterns"]}
    saved = []
    for candidate in candidates:
        pattern = dict(candidate)
        pattern["status"] = "candidate"
        if pattern.get("pattern_id") in existing:
            continue
        data["patterns"].append(pattern)
        existing.add(pattern.get("pattern_id"))
        saved.append(pattern)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return saved


def update_status(
    chats_dir: str,
    chat_id: str,
    pattern_id: str,
    *,
    status: str,
    note: str = "",
) -> Dict[str, Any]:
    """Validate or reject a candidate explicitly."""
    status = str(status).strip().lower()
    if status not in {"candidate", "validated", "rejected"}:
        raise ValueError("status must be candidate, validated or rejected")
    path = _path(chats_dir, chat_id)
    data = _load(path)
    for pattern in data["patterns"]:
        if pattern.get("pattern_id") != str(pattern_id):
            continue
        pattern["status"] = status
        pattern["review"] = {
            "note": str(note),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return pattern
    raise KeyError(f"Pattern not found: {pattern_id}")


def list_patterns(chats_dir: str, chat_id: str, *, limit: int = 100) -> list[Dict[str, Any]]:
    path = _path(chats_dir, chat_id)
    return _load(path)["patterns"][-max(1, int(limit)):]


def select_validated_patterns(
    records: Iterable[Dict[str, Any]],
    *,
    task_family: Optional[str] = None,
    depth_requirements: Optional[Dict[str, Any]] = None,
    limit: int = 5,
) -> list[Dict[str, Any]]:
    """Select validated patterns using family, depth similarity and evidence.

    Selection is deterministic and traceable. A candidate or rejected pattern
    can never enter the result, regardless of its score.
    """
    target = dict(depth_requirements or {})
    target = dict(target.get("profile") or target)
    dimensions = (
        "rigor", "prerequisites", "formalism", "proof", "research",
        "visualization", "experimentation", "generalization", "applications",
    )

    def depth_similarity(pattern: Dict[str, Any]) -> float:
        observed = dict(pattern.get("signature", {}).get("mathematical_depth") or {})
        observed = dict(observed.get("profile") or observed)
        pairs = [(float(target[k]), float(observed[k])) for k in dimensions if k in target and k in observed]
        if not pairs:
            return 0.0
        return sum(max(0.0, 1.0 - abs(a - b) / 100.0) for a, b in pairs) / len(pairs)

    rows = []
    for pattern in records:
        if pattern.get("status") != "validated":
            continue
        if task_family and pattern.get("task_family") != task_family:
            continue
        evidence = pattern.get("evidence") or {}
        evaluation = max(0.0, min(1.0, float(evidence.get("evaluation_score", 0.0))))
        rating = evidence.get("user_rating")
        rating_score = float(rating) / 100.0 if rating is not None else 0.0
        similarity = depth_similarity(pattern)
        score = 0.50 * evaluation + 0.20 * rating_score + 0.30 * similarity
        rows.append((score, pattern))

    rows.sort(key=lambda item: (-item[0], str(item[1].get("pattern_id", ""))))
    selected = []
    for score, pattern in rows[:max(1, int(limit))]:
        item = dict(pattern)
        item["selection"] = {
            "score": round(score, 6),
            "depth_similarity": round(depth_similarity(pattern), 6),
            "policy": "validated_family_depth_evidence_v1",
        }
        selected.append(item)
    return selected
