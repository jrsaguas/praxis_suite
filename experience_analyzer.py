"""Reference selection and pattern detection for controlled learning.

This module only analyzes recorded experience. It never promotes a strategy
or changes runtime behavior by itself.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional
import math
import re


@dataclass(frozen=True)
class Pattern:
    key: str
    frequency: int
    mean_score: float
    accept_rate: float
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceCandidate:
    investigation_id: str
    version_id: str
    relevance: float
    reason: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-záéíóúñ0-9_]{3,}", str(text).lower())
        if token not in {"para", "como", "con", "una", "uno", "del", "las", "los"}
    }


def _similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


def detect_patterns(records: Iterable[Dict[str, Any]], *, min_frequency: int = 2) -> List[Pattern]:
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        evaluation = record.get("evaluation") or {}
        metadata = record.get("metadata") or {}
        for key in metadata.get("features", []):
            buckets[str(key)].append(record)

    patterns: List[Pattern] = []
    for key, items in buckets.items():
        if len(items) < min_frequency:
            continue
        scores = [float((r.get("evaluation") or {}).get("score", 0.0)) for r in items]
        accepted = sum(bool((r.get("evaluation") or {}).get("consistent")) for r in items)
        patterns.append(Pattern(
            key=key,
            frequency=len(items),
            mean_score=round(sum(scores) / len(scores), 4),
            accept_rate=round(accepted / len(items), 4),
            evidence=tuple(str(r.get("record_id", "")) for r in items[-5:]),
        ))
    return sorted(patterns, key=lambda p: (p.mean_score, p.frequency), reverse=True)


def select_references(
    records: Iterable[Dict[str, Any]],
    query: str,
    *,
    limit: int = 5,
    min_score: float = 0.0,
) -> List[ReferenceCandidate]:
    candidates: List[ReferenceCandidate] = []
    for record in records:
        evaluation = record.get("evaluation") or {}
        score = float(evaluation.get("score", 0.0))
        if score < min_score:
            continue
        investigation_id = record.get("investigation_id")
        version_id = record.get("version_id")
        if not investigation_id or not version_id:
            continue

        metadata = record.get("metadata") or {}
        context = " ".join(
            [
                str(record.get("task_fingerprint", "")),
                str(metadata.get("title", "")),
                str(metadata.get("topic", "")),
                " ".join(map(str, metadata.get("features", []))),
            ]
        )
        similarity = _similarity(query, context)
        relevance = round(0.65 * similarity + 0.35 * score, 4)
        if relevance <= 0:
            continue
        candidates.append(ReferenceCandidate(
            investigation_id=investigation_id,
            version_id=version_id,
            relevance=relevance,
            reason=f"similitud={similarity:.3f}; score={score:.3f}",
            score=score,
        ))

    candidates.sort(key=lambda c: c.relevance, reverse=True)
    return candidates[:max(1, int(limit))]


def fuse_reference_patterns(
    references: Iterable[ReferenceCandidate],
    patterns: Iterable[Pattern],
) -> Dict[str, Any]:
    refs = list(references)
    pats = list(patterns)
    return {
        "references": [r.to_dict() for r in refs],
        "patterns": [p.to_dict() for p in pats],
        "strategy": "reference-fusion-v1",
        "guardrail": "analysis-only; requires explicit promotion gate",
    }


def build_strategy_candidate(
    references: Iterable[ReferenceCandidate],
    patterns: Iterable[Pattern],
    *,
    name: str = "reference-fusion-v1",
    objective: str = "Reutilizar patrones de experiencias relevantes sin alterar automáticamente el comportamiento.",
):
    """Turn analyzed evidence into a registry candidate; never promotes it."""
    from strategy_registry import create_candidate

    refs = list(references)
    pats = list(patterns)
    rules = [f"considerar patrón: {p.key}" for p in pats if p.accept_rate > 0]
    rules.extend(f"consultar referencia: {r.investigation_id}/{r.version_id}" for r in refs)
    evidence = [*map(lambda r: r.version_id, refs), *[e for p in pats for e in p.evidence]]
    metrics = {
        "reference_count": float(len(refs)),
        "pattern_count": float(len(pats)),
        "mean_reference_score": round(sum(r.score for r in refs) / len(refs), 4) if refs else 0.0,
    }
    if not rules:
        raise ValueError("No hay evidencia suficiente para construir una estrategia candidata.")
    return create_candidate(
        name=name,
        objective=objective,
        rules=rules,
        required_tests=("strategy-regression", "artifact-regression"),
        evidence_ids=evidence,
        metrics=metrics,
        source="experience-analysis",
    )
