"""Contextual strategy selection.

Selection is ranked evidence, not a promotion mechanism. Only promoted
strategies are eligible by default; the caller may explicitly include
candidates for inspection/testing.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from preference_profiles import PreferenceProfile


def _family_match(strategy: Mapping[str, Any], task_family: Optional[str]) -> float:
    if not task_family:
        return 0.5
    families = strategy.get("task_families") or strategy.get("metadata", {}).get("task_families") or []
    if not families:
        return 0.25
    normalized = str(task_family).strip().lower().replace(" ", "_")
    return 1.0 if normalized in {str(x).lower().replace(" ", "_") for x in families} else 0.0


def _preference_fit(strategy: Mapping[str, Any], preferences: Optional[PreferenceProfile]) -> float:
    if not preferences:
        return 0.5
    dimensions = strategy.get("evaluation_profile") or strategy.get("metrics", {}).get("evaluation_profile")
    if not isinstance(dimensions, Mapping):
        return 0.5
    from investigation_model import EvaluationProfile
    profile = EvaluationProfile(**{d: int(dimensions.get(d, 0)) for d in EvaluationProfile.__dataclass_fields__})
    return preferences.score(profile) / 100.0


def _trend_fit(strategy: Mapping[str, Any], trends: Iterable[Mapping[str, Any]]) -> float:
    trend_map = {str(x.get("feature")): x for x in trends}
    features = strategy.get("features") or []
    if not features:
        return 0.5
    values = []
    for feature in features:
        trend = trend_map.get(str(feature))
        if not trend:
            continue
        values.append({
            "improving": 1.0,
            "stable": 0.75,
            "stable_window_pending": 0.5,
            "declining": 0.2,
            "insufficient_evidence": 0.35,
        }.get(str(trend.get("trend")), 0.35))
    return sum(values) / len(values) if values else 0.5


def select_strategies(
    strategies: Iterable[Mapping[str, Any]],
    *,
    task_family: Optional[str] = None,
    preferences: Optional[PreferenceProfile] = None,
    trends: Iterable[Mapping[str, Any]] = (),
    include_candidates: bool = False,
    limit: int = 5,
) -> list[Dict[str, Any]]:
    ranked = []
    for strategy in strategies:
        if not include_candidates and strategy.get("status") != "promoted":
            continue
        family = _family_match(strategy, task_family)
        preference = _preference_fit(strategy, preferences)
        trend = _trend_fit(strategy, trends)
        score = 0.40 * family + 0.40 * preference + 0.20 * trend
        ranked.append({
            "strategy": dict(strategy),
            "selection_score": round(score, 4),
            "signals": {
                "task_family_fit": round(family, 4),
                "preference_fit": round(preference, 4),
                "trend_fit": round(trend, 4),
            },
        })
    ranked.sort(key=lambda x: x["selection_score"], reverse=True)
    return ranked[:max(1, int(limit))]
