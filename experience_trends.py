"""Temporal trend analysis for experience patterns.

Recent evidence receives more weight, but old evidence is retained. Trends
are descriptive signals and never modify strategies automatically.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def _timestamp(record: Dict[str, Any]) -> datetime:
    raw = record.get("created_at") or record.get("at")
    if not raw:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def recency_weight(record: Dict[str, Any], *, now: datetime | None = None, half_life_days: float = 30.0) -> float:
    now = now or datetime.now(timezone.utc)
    age = max(0.0, (now - _timestamp(record)).total_seconds() / 86400)
    return math.pow(0.5, age / max(1.0, half_life_days))


def trend_for_feature(
    records: Iterable[Dict[str, Any]],
    feature: str,
    *,
    now: datetime | None = None,
    half_life_days: float = 30.0,
) -> Dict[str, Any]:
    items = [
        r for r in records
        if feature in [str(x) for x in ((r.get("metadata") or {}).get("features") or [])]
    ]
    if not items:
        return {
            "feature": feature, "count": 0, "weighted_score": 0.0,
            "weighted_accept_rate": 0.0, "trend": "insufficient_evidence",
        }

    weighted_total = weighted_score = weighted_accept = 0.0
    recent_scores: List[float] = []
    older_scores: List[float] = []
    cutoff = (now or datetime.now(timezone.utc)).timestamp() - 30 * 86400

    for record in items:
        w = recency_weight(record, now=now, half_life_days=half_life_days)
        score = float((record.get("evaluation") or {}).get("score", 0.0))
        accepted = 1.0 if bool((record.get("evaluation") or {}).get("consistent")) else 0.0
        weighted_total += w
        weighted_score += w * score
        weighted_accept += w * accepted
        if _timestamp(record).timestamp() >= cutoff:
            recent_scores.append(score)
        else:
            older_scores.append(score)

    recent = sum(recent_scores) / len(recent_scores) if recent_scores else None
    older = sum(older_scores) / len(older_scores) if older_scores else None
    delta = (recent - older) if recent is not None and older is not None else None

    if len(items) < 2:
        trend = "insufficient_evidence"
    elif delta is None:
        trend = "stable_window_pending"
    elif delta > 0.03:
        trend = "improving"
    elif delta < -0.03:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "feature": feature,
        "count": len(items),
        "weighted_score": round(weighted_score / weighted_total, 4),
        "weighted_accept_rate": round(weighted_accept / weighted_total, 4),
        "recent_mean": None if recent is None else round(recent, 4),
        "older_mean": None if older is None else round(older, 4),
        "delta": None if delta is None else round(delta, 4),
        "trend": trend,
    }


def temporal_feature_summary(
    records: Iterable[Dict[str, Any]],
    *,
    now: datetime | None = None,
    half_life_days: float = 30.0,
) -> List[Dict[str, Any]]:
    records = list(records)
    features = sorted({
        str(feature)
        for record in records
        for feature in ((record.get("metadata") or {}).get("features") or [])
    })
    return [
        trend_for_feature(records, feature, now=now, half_life_days=half_life_days)
        for feature in features
    ]
