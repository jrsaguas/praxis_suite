"""Bridge evaluator results into the persistent experience layer."""
from __future__ import annotations

from typing import Any, Dict, Optional

from evaluator_orchestrator import LearningRecord, record_to_dict
from experience_store import append_record


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
