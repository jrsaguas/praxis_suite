"""Structured quality/delivery gate evaluation for specialist-agent handoffs.

Gate evidence must be explicit in the agent output. The runtime never treats an
artifact as verified merely because execution returned successfully.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from agent_graph import AgentTask


@dataclass(frozen=True)
class GateEvaluation:
    phase: str
    agent_id: str
    passed: bool
    required_gates: Tuple[str, ...]
    failed_gates: Tuple[str, ...] = ()
    missing_gates: Tuple[str, ...] = ()
    evidence: Mapping[str, Any] = None

    def __post_init__(self):
        if self.evidence is None:
            object.__setattr__(self, "evidence", {})

    @property
    def blocked_handoff(self) -> bool:
        return not self.passed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "agent_id": self.agent_id,
            "passed": self.passed,
            "required_gates": list(self.required_gates),
            "failed_gates": list(self.failed_gates),
            "missing_gates": list(self.missing_gates),
            "blocked_handoff": self.blocked_handoff,
            "evidence": dict(self.evidence),
        }


def evaluate_gate_contract(task: AgentTask, output: Mapping[str, Any], phase: str) -> GateEvaluation:
    """Evaluate named gates from explicit gate_results output.

    Accepted shape:
        {"gate_results": {"gate_name": {"passed": True, ...}}}

    A bare passed flag is intentionally not sufficient when named gates exist:
    it cannot establish which contract requirements were checked.
    """
    required = tuple(task.quality_gates if phase == "quality" else task.delivery_gates)
    if not required:
        return GateEvaluation(phase, task.agent_id, True, ())

    raw = output.get("gate_results")
    if not isinstance(raw, Mapping):
        return GateEvaluation(
            phase, task.agent_id, False, required, missing_gates=required,
            evidence={"reason": "explicit gate_results mapping is required"},
        )

    failed = []
    missing = []
    evidence = {}
    for gate in required:
        item = raw.get(gate)
        if not isinstance(item, Mapping):
            missing.append(gate)
            continue
        evidence[gate] = dict(item)
        if item.get("passed") is not True:
            failed.append(gate)

    passed = not failed and not missing
    return GateEvaluation(
        phase, task.agent_id, passed, required,
        failed_gates=tuple(failed), missing_gates=tuple(missing), evidence=evidence,
    )
