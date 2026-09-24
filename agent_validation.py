"""Explicit validation gate connecting evaluation evidence to agent lifecycle.

This module is the controlled boundary between an observable evaluation result
and AgentFactory.validate(). It never validates a candidate merely because an
evaluation object exists: the declared quality gates must pass first.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from agent_factory import AgentBlueprint, AgentFactory


class AgentValidationGate:
    """Convert passing evaluation evidence into auditable agent validation."""

    def __init__(self, *, minimum_score: float = 0.80):
        self.minimum_score = float(minimum_score)

    def build_evidence(
        self,
        evaluation: Any,
        *,
        source_id: str,
        checks: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if not source_id or not str(source_id).strip():
            raise ValueError("source_id es obligatorio para validar un agente")

        if isinstance(evaluation, Mapping):
            data = dict(evaluation)
        else:
            data = {
                "consistent": getattr(evaluation, "consistent", None),
                "score": getattr(evaluation, "score", None),
                "errors": list(getattr(evaluation, "errors", ()) or ()),
                "required_retries": list(getattr(evaluation, "required_retries", ()) or ()),
                "recommendation": getattr(evaluation, "recommendation", None),
                "reasons": list(getattr(evaluation, "reasons", ()) or ()),
            }

        score = data.get("score")
        consistent = data.get("consistent")
        recommendation = str(data.get("recommendation") or "").upper()
        errors = tuple(data.get("errors") or ())
        retries = tuple(data.get("required_retries") or ())

        gate_checks = {
            "evaluation_present": bool(data),
            "consistent": consistent is True,
            "minimum_score": score is not None and float(score) >= self.minimum_score,
            "recommendation_accept": recommendation == "ACCEPT",
            "no_errors": not errors,
            "no_required_retries": not retries,
        }
        passed = all(gate_checks.values())

        return {
            "passed": passed,
            "validator": "agent_validation_gate",
            "source_id": str(source_id),
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "evaluation": data,
            "gate": {
                "minimum_score": self.minimum_score,
                "checks": gate_checks,
                "requested_checks": list(checks),
            },
        }

    def validate(
        self,
        agent: AgentBlueprint,
        evaluation: Any,
        *,
        source_id: str,
        checks: tuple[str, ...] = (),
    ) -> AgentBlueprint:
        evidence = self.build_evidence(evaluation, source_id=source_id, checks=checks)
        if not evidence["passed"]:
            raise ValueError("La evaluación no supera los gates de validación del agente")
        return AgentFactory.validate(agent, evidence=evidence)
