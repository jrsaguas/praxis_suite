"""Build a deterministic strategy context for investigation orchestration."""
from __future__ import annotations

from typing import Any, Dict, Optional

from preference_profiles import PreferenceProfile
from strategy_selector import select_strategies
from task_family import classify_task_family
from mathematical_depth import MathematicalDepthProfile, build_depth_context


def build_strategy_context(
    task: str,
    *,
    records=(),
    strategies=(),
    preferences: Optional[PreferenceProfile] = None,
    trends=(),
    validated_patterns=(),
    limit: int = 5,
    depth_profile: Optional[MathematicalDepthProfile] = None,
) -> Dict[str, Any]:
    record = {"metadata": {"topic": task}, "task_fingerprint": task}
    family = classify_task_family(record)
    ranked = select_strategies(
        strategies,
        task_family=family,
        preferences=preferences,
        trends=trends,
        validated_patterns=validated_patterns,
        limit=limit,
    )
    depth = depth_profile or MathematicalDepthProfile.preset("licenciatura")
    depth_context = build_depth_context(depth)
    return {
        "task_family": family,
        "depth_context": depth_context,
        "selection_policy": "promoted_only_with_validated_pattern_evidence",
        "strategy_ids": [x["strategy"].get("strategy_id") for x in ranked],
        "strategies": ranked,
        "operational_instructions": [
            rule
            for item in ranked[:3]
            for rule in item["strategy"].get("rules", [])
        ],
        "validated_pattern_ids": sorted({
            pattern_id
            for item in ranked
            for pattern_id in item.get("validated_pattern_evidence", {}).get("pattern_ids", [])
        }),
        "preference_version": preferences.version if preferences else None,
        "strategy_context_version": 3,
        "selected_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
