"""Contextual strategy selection.

Selection is ranked evidence, not a promotion mechanism. Only promoted
strategies are eligible by default; validated pattern evidence can refine the
selection but can never bypass the promotion gate.
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


def _pattern_evidence(
    strategy_id: str,
    patterns: Iterable[Mapping[str, Any]],
    *,
    task_family: Optional[str],
) -> Dict[str, Any]:
    matching = []
    for pattern in patterns:
        if pattern.get("status") != "validated":
            continue
        if str(pattern.get("strategy_id") or "") != str(strategy_id):
            continue
        if task_family and pattern.get("task_family") != task_family:
            continue
        selection = pattern.get("selection") or {}
        if selection.get("score") is not None:
            score = max(0.0, min(1.0, float(selection["score"])))
        else:
            evidence = pattern.get("evidence") or {}
            evaluation = max(0.0, min(1.0, float(evidence.get("evaluation_score", 0.0))))
            rating = evidence.get("user_rating")
            rating_score = float(rating) / 100.0 if rating is not None else 0.0
            score = 0.70 * evaluation + 0.30 * rating_score
        matching.append((score, pattern))
    if not matching:
        return {
            "fit": 0.0,
            "pattern_ids": [],
            "source_record_ids": [],
            "support_count": 0,
        }
    fit = sum(score for score, _ in matching) / len(matching)
    pattern_ids = sorted({str(p.get("pattern_id")) for _, p in matching if p.get("pattern_id")})
    source_record_ids = sorted({
        str(record_id)
        for _, p in matching
        for record_id in p.get("source_record_ids", [])
        if record_id
    })
    return {
        "fit": round(fit, 4),
        "pattern_ids": pattern_ids,
        "source_record_ids": source_record_ids,
        "support_count": len(matching),
    }


def select_strategies(
    strategies: Iterable[Mapping[str, Any]],
    *,
    task_family: Optional[str] = None,
    preferences: Optional[PreferenceProfile] = None,
    trends: Iterable[Mapping[str, Any]] = (),
    validated_patterns: Iterable[Mapping[str, Any]] = (),
    include_candidates: bool = False,
    limit: int = 5,
) -> list[Dict[str, Any]]:
    ranked = []
    patterns = tuple(validated_patterns)
    for strategy in strategies:
        if not include_candidates and strategy.get("status") != "promoted":
            continue
        if strategy.get("status") in {"retired", "degraded"} and not include_candidates:
            continue
        family = _family_match(strategy, task_family)
        preference = _preference_fit(strategy, preferences)
        trend = _trend_fit(strategy, trends)
        evidence = _pattern_evidence(
            str(strategy.get("strategy_id") or ""),
            patterns,
            task_family=task_family,
        )
        base_score = 0.40 * family + 0.40 * preference + 0.20 * trend
        score = (
            0.85 * base_score + 0.15 * evidence["fit"]
            if patterns
            else base_score
        )
        ranked.append({
            "strategy": dict(strategy),
            "selection_score": round(score, 4),
            "signals": {
                "task_family_fit": round(family, 4),
                "preference_fit": round(preference, 4),
                "trend_fit": round(trend, 4),
                "validated_pattern_evidence_fit": evidence["fit"],
            },
            "validated_pattern_evidence": {
                "pattern_ids": evidence["pattern_ids"],
                "source_record_ids": evidence["source_record_ids"],
                "support_count": evidence["support_count"],
                "policy": "validated_pattern_evidence_v1",
            },
        })
    ranked.sort(
        key=lambda x: (
            -x["selection_score"],
            str(x["strategy"].get("strategy_id", "")),
        )
    )
    return ranked[:max(1, int(limit))]
