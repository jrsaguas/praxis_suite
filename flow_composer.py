"""Compose static and adaptive agent flows without executing them."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from adaptive_agent import AdaptationDecision
from agent_factory import AgentBlueprint


@dataclass(frozen=True)
class ComposedFlow:
    agents: Tuple[str, ...]
    generated_agents: Tuple[str, ...] = ()
    adaptive_active: bool = False
    reason: str = ""

    def to_dict(self):
        return {
            "agents": list(self.agents),
            "generated_agents": list(self.generated_agents),
            "adaptive_active": self.adaptive_active,
            "reason": self.reason,
        }


class FlowComposer:
    """Insert validated adaptive agents into an existing role flow."""

    def compose(
        self,
        existing_agents: Iterable[str],
        decision: AdaptationDecision,
        generated_agents: Iterable[AgentBlueprint] = (),
    ) -> ComposedFlow:
        base = list(dict.fromkeys(str(x) for x in existing_agents))
        generated = [
            agent for agent in generated_agents
            if agent.status == "validated"
        ]
        if not decision.active:
            return ComposedFlow(tuple(base), (), False, decision.reason)

        ids = list(base)
        for agent in generated:
            if agent.state not in {"sleeping", "active"}:
                continue
            if agent.id not in ids:
                ids.append(agent.id)
        return ComposedFlow(
            tuple(ids),
            tuple(agent.id for agent in generated),
            True,
            decision.reason,
        )
