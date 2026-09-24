"""Agent Factory for Praxis.

The factory creates declarative agent blueprints. It does not execute models,
modify investigations, or silently promote generated agents.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
            "id": self.id,
            "role": self.role,
            "model_id": self.model_id,
            "tools": list(self.tools),
            "context": list(self.context),
            "state": self.state,
            "memory": list(self.memory),
            "evaluation": list(self.evaluation),
            "actions": list(self.actions),
            "source": self.source,
            "status": self.status,
        }


class AgentFactory:
    """Validate and construct agents while keeping generated agents dormant."""

    def create(
        self,
        *,
        agent_id: str,
        role: str,
        model_id: str,
        tools: Iterable[str] = (),
        context: Iterable[str] = (),
        memory: Iterable[str] = (),
        evaluation: Iterable[str] = (),
        actions: Iterable[str] = (),
        source: str = "agent_factory",
    ) -> AgentBlueprint:
        return AgentBlueprint(
            id=str(agent_id),
            role=str(role),
            model_id=str(model_id),
            tools=tuple(str(x) for x in tools),
            context=tuple(str(x) for x in context),
            state="sleeping",
            memory=tuple(str(x) for x in memory),
            evaluation=tuple(str(x) for x in evaluation),
            actions=tuple(str(x) for x in actions),
            source=str(source),
            status="candidate",
        )

    @staticmethod
    def activate(agent: AgentBlueprint) -> AgentBlueprint:
        if agent.status != "validated":
            raise ValueError("Solo un agente validado puede activarse")
        return AgentBlueprint(**{**agent.to_dict(), "state": "active",
                                 "tools": tuple(agent.tools),
                                 "context": tuple(agent.context),
                                 "memory": tuple(agent.memory),
                                 "evaluation": tuple(agent.evaluation),
                                 "actions": tuple(agent.actions)})

    @staticmethod
    def validate(agent: AgentBlueprint) -> AgentBlueprint:
        return AgentBlueprint(**{**agent.to_dict(), "status": "validated",
                                 "tools": tuple(agent.tools),
                                 "context": tuple(agent.context),
                                 "memory": tuple(agent.memory),
                                 "evaluation": tuple(agent.evaluation),
                                 "actions": tuple(agent.actions)})
