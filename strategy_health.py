"""Detect sustained degradation of promoted strategies."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


def assess_degradation(
    outcomes: Iterable[Mapping[str, Any]],
    *,
    strategy_id: str,
    task_family: str | None = None,
    recent_limit: int = 5,
    min_score: float = 0.70,
    max_decline: float = 0.05,
) -> Dict[str, Any]:
    rows = [
        x for x in outcomes
        if str(x.get("strategy_id")) == strategy_id
        and (not task_family or (x.get("metadata") or {}).get("task_family") == task_family)
    ]
    rows.sort(key=lambda x: str(x.get("created_at", "")))
    recent = rows[-max(1, int(recent_limit)):]
    if len(recent) < 3:
        return {"strategy_id": strategy_id, "degraded": False, "status": "insufficient_evidence",
                "samples": len(recent)}
    scores = [float((x.get("evaluation") or {}).get("score", 0.0)) for x in recent]
    mean = sum(scores) / len(scores)
    first_half = scores[:len(scores)//2]
    second_half = scores[len(scores)//2:]
    first = sum(first_half) / len(first_half)
    second = sum(second_half) / len(second_half)
    decline = first - second
    degraded = mean < min_score or decline > max_decline
    return {
        "strategy_id": strategy_id,
        "degraded": degraded,
        "status": "degraded" if degraded else "healthy",
        "samples": len(recent),
        "mean_score": round(mean, 4),
        "early_mean": round(first, 4),
        "recent_mean": round(second, 4),
        "decline": round(decline, 4),
        "thresholds": {"min_score": min_score, "max_decline": max_decline},
    }
