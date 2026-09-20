"""Build execution context from strategy and mathematical depth selections."""
from __future__ import annotations
from typing import Any, Mapping


def build_operational_context(
    *,
    strategy_context: Mapping[str, Any],
    task: str,
    investigation_id: str | None = None,
) -> dict:
    depth = dict(strategy_context.get("depth_context", {}))
    return {
        "task": task,
        "investigation_id": investigation_id,
        "task_family": strategy_context.get("task_family"),
        "strategy_ids": tuple(strategy_context.get("strategy_ids", ())),
        "operational_instructions": tuple(strategy_context.get("operational_instructions", ())),
        "depth_context": depth,
        "requirements": dict(depth.get("requirements", {})),
        "context_version": 1,
    }
