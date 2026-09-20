"""Controlled recovery selection for retired strategies."""
from __future__ import annotations
from typing import Any, Dict, Iterable, Mapping


def recovery_candidate(
    outcomes: Iterable[Mapping[str, Any]],
    *,
    family: str,
    excluded_strategy_ids: Iterable[str] = (),
    recent_limit: int = 10,
    min_score: float = .75,
) -> Dict[str, Any]:
    excluded = {str(x) for x in excluded_strategy_ids}
    rows = [
        x for x in outcomes
        if (x.get("metadata") or {}).get("task_family") == family
        and str(x.get("strategy_id")) not in excluded
    ]
    grouped: Dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("strategy_id")), []).append(
            float((row.get("evaluation") or {}).get("score", 0.0))
        )
    candidates = []
    for strategy_id, scores in grouped.items():
        recent = scores[-max(1, int(recent_limit)):]
        if len(recent) < 3:
            continue
        mean = sum(recent) / len(recent)
        if mean >= min_score:
            candidates.append({"strategy_id": strategy_id, "mean_score": round(mean, 4), "samples": len(recent)})
    candidates.sort(key=lambda x: x["mean_score"], reverse=True)
    return {
        "family": family,
        "eligible": bool(candidates),
        "candidate": candidates[0] if candidates else None,
        "candidates": candidates,
        "selection_policy": "stable_history_only",
    }
