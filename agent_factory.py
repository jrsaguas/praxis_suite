"""Agent Factory for Praxis.

The factory creates declarative agent blueprints. It does not execute models,
modify investigations, or silently promote generated agents.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Tuple


_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


@dataclass(frozen=True)
class AgentBlueprint:
    id: str
    role: str
    model_id: str
    tools: Tuple[str, ...] = ()
    context: Tuple[str, ...] = ()
    state: str = "sleeping"
    memory: Tuple[str, ...] = ()
    evaluation: Tuple[str, ...] = ()
    actions: Tuple[str, ...] = ()
    source: str = "agent_factory"
    status: str = "candidate"
    validation: Mapping[str, object] | None = None

    def __post_init__(self):
        if not _ID_RE.match(self.id):
            raise ValueError("agent id inválido")
        if not self.role.strip():
            raise ValueError("role no puede estar vacío")
        if not self.model_id.strip():
            raise ValueError("model_id no puede estar vacío")
        if self.state not in {"sleeping", "active", "retired"}:
            raise ValueError("state inválido")
        if self.status not in {"candidate", "validated", "rejected"}:
            raise ValueError("status inválido")

    def to_dict(self):
        return {
            "id": self.id, "role": self.role, "model_id": self.model_id,
            "tools": list(self.tools), "context": list(self.context),
            "state": self.state, "memory": list(self.memory),
            "evaluation": list(self.evaluation), "actions": list(self.actions),
            "source": self.source, "status": self.status,
            "validation": dict(self.validation or {}),
        }


def _copy(agent: AgentBlueprint, **changes) -> AgentBlueprint:
    data = agent.to_dict()
    data.update(changes)
    for key in ("tools", "context", "memory", "evaluation", "actions"):
        data[key] = tuple(data[key])
    return AgentBlueprint(**data)


class AgentFactory:
    """Validate, reject, and construct agents while keeping them dormant."""

    def create(
        self, *, agent_id: str, role: str, model_id: str,
        tools: Iterable[str] = (), context: Iterable[str] = (),
        memory: Iterable[str] = (), evaluation: Iterable[str] = (),
        actions: Iterable[str] = (), source: str = "agent_factory",
    ) -> AgentBlueprint:
        return AgentBlueprint(
            id=str(agent_id), role=str(role), model_id=str(model_id),
            tools=tuple(str(x) for x in tools), context=tuple(str(x) for x in context),
            state="sleeping", memory=tuple(str(x) for x in memory),
            evaluation=tuple(str(x) for x in evaluation),
            actions=tuple(str(x) for x in actions),
            source=str(source), status="candidate",
        )

    @staticmethod
    def validate(
        agent: AgentBlueprint,
        *,
        evidence: Mapping[str, object] | None = None,
        require_evidence: bool = False,
    ) -> AgentBlueprint:
        if agent.status != "candidate":
            raise ValueError("Solo un candidato puede validarse")
        evidence = dict(evidence or {})
        if require_evidence and not evidence:
            raise ValueError("La validación requiere evidencia explícita")
        if evidence.get("passed") is False:
            raise ValueError("La evidencia indica que el candidato no superó la validación")
        return _copy(
            agent,
            status="validated",
            validation={"passed": True, "evidence": evidence},
        )

    @staticmethod
    def reject(agent: AgentBlueprint) -> AgentBlueprint:
        if agent.status != "candidate":
            raise ValueError("Solo un candidato puede rechazarse")
        return _copy(agent, status="rejected")

    @staticmethod
    def activate(agent: AgentBlueprint) -> AgentBlueprint:
        if agent.status != "validated":
            raise ValueError("Solo un agente validado puede activarse")
        if agent.state == "retired":
            raise ValueError("Un agente retirado no puede activarse")
        return _copy(agent, state="active")
