"""Bridge evaluator results into the persistent experience layer."""
from __future__ import annotations

from typing import Any, Dict, Optional

from evaluator_orchestrator import LearningRecord, record_to_dict
from experience_store import append_record, select_references


def persist_learning_record(
    chats_dir: str,
    chat_id: str,
    record: LearningRecord,
    *,
    investigation_id: Optional[str] = None,
    version_id: Optional[str] = None,
    evaluation_profile: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = record_to_dict(record)
    merged_metadata = dict(metadata or {})
    if evaluation_profile is not None:
        merged_metadata["evaluation_profile"] = {
            str(k): int(v) for k, v in evaluation_profile.items()
        }
    merged_metadata["attempt_count"] = len(record.agent_results)
    merged_metadata["recommendation"] = record.evaluation.recommendation
    return append_record(
        chats_dir,
        chat_id,
        task_fingerprint=record.task_fingerprint,
        evaluation={
            "consistent": record.evaluation.consistent,
            "score": record.evaluation.score,
            "errors": list(record.evaluation.errors),
            "strengths": list(record.evaluation.strengths),
            "required_retries": list(record.evaluation.required_retries),
            "recommendation": record.evaluation.recommendation,
            "reasons": list(record.evaluation.reasons),
        },
        strategy_id=record.strategy_id,
        investigation_id=investigation_id,
        version_id=version_id,
        proposal=(
            {
                "target": record.proposal.target,
                "reason": record.proposal.reason,
                "strategy": record.proposal.strategy,
                "expected_effect": record.proposal.expected_effect,
                "tests": list(record.proposal.tests),
            }
            if record.proposal else None
        ),
        metadata=merged_metadata,
    )



def persist_strategy_outcome(
    chats_dir: str,
    chat_id: str,
    *,
    strategy_context: Dict[str, Any],
    evaluation_profile: Dict[str, int],
    score: float,
    consistent: bool,
    investigation_id: Optional[str] = None,
    version_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record the concrete outcome of a context-selected strategy."""
    strategy_ids = strategy_context.get("strategy_ids") or ["baseline-v1"]
    selected = str(strategy_ids[0])
    merged = dict(metadata or {})
    merged.update({
        "strategy_context_version": strategy_context.get("strategy_context_version"),
        "selection_score": (
            strategy_context.get("strategies", [{}])[0].get("selection_score")
            if strategy_context.get("strategies") else None
        ),
        "task_family": strategy_context.get("task_family"),
        "features": [
            str(x.get("feature"))
            for x in strategy_context.get("temporal_trends", [])
            if x.get("feature")
        ],
        "evaluation_profile": {str(k): int(v) for k, v in evaluation_profile.items()},
    })
    return append_record(
        chats_dir,
        chat_id,
        task_fingerprint=str(strategy_context.get("task_fingerprint", "")),
        evaluation={
            "consistent": bool(consistent),
            "score": max(0.0, min(1.0, float(score))),
            "errors": [],
            "strengths": [],
            "required_retries": [],
            "recommendation": "ACCEPT" if consistent else "REVIEW",
            "reasons": ["post_run_strategy_outcome"],
        },
        strategy_id=selected,
        investigation_id=investigation_id,
        version_id=version_id,
        metadata=merged,
    )


def build_experience_context(
    chats_dir: str,
    chat_id: str,
    *,
    task_family: Optional[str] = None,
    limit: int = 5,
    evaluation_profile: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Build a weighted reference context without mutating the experience store."""
    from experience_store import list_records
    records = list_records(chats_dir, chat_id, limit=500)
    return {
        "task_family": task_family,
        "references": select_references(records, task_family=task_family, target_profile=evaluation_profile, limit=limit),
        "selection_policy": "evidence_weighted_multi_reference",
    }

def normalize_planning_context(planning_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize planner metadata into a stable, auditable learning contract."""
    raw = dict(planning_metadata or {})
    adaptive = dict(raw.get("adaptive_selection") or {})
    depth = dict(raw.get("mathematical_depth") or {})
    return {
        "schema_version": 1,
        "adaptive_active": bool(adaptive.get("active", False)),
        "adaptive_reason": str(adaptive.get("reason", "")),
        "selected_reusable_agents": [str(x) for x in adaptive.get("selected_reusable_agents", []) if x],
        "generated_candidates": [str(x) for x in adaptive.get("generated_candidates", []) if x],
        "execution_agents": [str(x) for x in raw.get("execution_agents", []) if x],
        "mathematical_depth": depth,
        "selected_patterns": [
            {
                "pattern_id": str(x.get("pattern_id")),
                "task_family": str(x.get("task_family", "")),
                "selection": dict(x.get("selection") or {}),
                "source_record_ids": [str(r) for r in x.get("source_record_ids", [])],
            }
            for x in raw.get("selected_patterns", [])
            if x.get("pattern_id")
        ],
    }


def persist_runtime_experience(
    chats_dir: str,
    chat_id: str,
    *,
    task_fingerprint: str,
    evaluation: Dict[str, Any],
    experience_record: Dict[str, Any],
    investigation_id: Optional[str] = None,
    version_id: Optional[str] = None,
    evaluation_profile: Optional[Dict[str, int]] = None,
    strategy_context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    planning_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persist an evaluator outcome as a candidate; never auto-promotes it."""
    merged = dict(metadata or {})
    merged["evaluation_profile"] = {
        str(k): int(v) for k, v in (evaluation_profile or {}).items()
    }
    merged["runtime_experience_source"] = "experience_evaluator"
    merged["candidate_type"] = experience_record.get("candidate_type", "strategy_outcome")
    merged["promotion_eligible"] = bool(experience_record.get("promotion_eligible", False))
    merged["requires_human_or_gate_review"] = bool(
        experience_record.get("requires_human_or_gate_review", True)
    )
    if planning_metadata:
        merged["planning_context"] = normalize_planning_context(planning_metadata)
    if strategy_context:
        merged["strategy_context_version"] = strategy_context.get("strategy_context_version")
        merged["task_family"] = strategy_context.get("task_family")
        merged["strategy_id"] = strategy_context.get("strategy_id")
    return append_record(
        chats_dir,
        chat_id,
        task_fingerprint=task_fingerprint,
        evaluation=dict(evaluation or {}),
        strategy_id=str((strategy_context or {}).get("strategy_id") or "runtime-outcome"),
        investigation_id=investigation_id,
        version_id=version_id,
        metadata=merged,
    )



def make_runtime_experience_sink(
    chats_dir: str,
    chat_id: str,
    *,
    investigation_id: Optional[str] = None,
    version_id: Optional[str] = None,
    task_fingerprint: str = "",
    evaluation_profile: Optional[Dict[str, int]] = None,
    strategy_context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Build the runtime callback that records evaluator outcomes as candidates."""
    def sink(task, artifacts, output):
        evaluation = dict(output.get("evaluation") or {})
        experience_record = dict(output.get("experience_record") or {})
        return persist_runtime_experience(
            chats_dir,
            chat_id,
            task_fingerprint=task_fingerprint or str(getattr(task, "task_id", "")),
            evaluation=evaluation,
            experience_record=experience_record,
            investigation_id=investigation_id,
            version_id=version_id,
            evaluation_profile=evaluation_profile,
            strategy_context=strategy_context,
            planning_metadata=dict(artifacts.get("planning_metadata") or {}),
            metadata={
                **dict(metadata or {}),
                "runtime_task_id": getattr(task, "task_id", ""),
                "runtime_agent_id": getattr(task, "agent_id", ""),
                "final_audit_present": bool(artifacts.get("final_audit")),
            },
        )
    return sink
