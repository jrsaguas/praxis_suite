"""Build a deterministic strategy context for investigation orchestration."""
from __future__ import annotations

from typing import Any, Dict, Optional

from preference_profiles import PreferenceProfile
from strategy_selector import select_strategies
from task_family import classify_task_family


def build_strategy_context(
    task: str,
    *,
    records=(),
    strategies=(),
    preferences: Optional[PreferenceProfile] = None,
    trends=(),
    limit: int = 5,
) -> Dict[str, Any]:
    record = {"metadata": {"topic": task}, "task_fingerprint": task}
    family = classify_task_family(record)
    ranked = select_strategies(
        strategies,
        task_family=family,
        preferences=preferences,
        trends=trends,
        limit=limit,
    )
    return {
        "task_family": family,
        "strategy_ids": [x["strategy"].get("strategy_id") for x in ranked],
        "strategies": ranked,
        "operational_instructions": [
            rule
            for item in ranked[:3]
            for rule in item["strategy"].get("rules", [])
        ],
        "preference_version": preferences.version if preferences else None,
        "strategy_context_version": 1,
    }
