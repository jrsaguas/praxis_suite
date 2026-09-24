"""Reusable-agent catalog for adaptive orchestration."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple
from agent_factory import AgentBlueprint

@dataclass(frozen=True)
class AgentMatch:
    agent_id: str
    compatibility: float
    missing_tools: Tuple[str, ...] = ()
    missing_capabilities: Tuple[str, ...] = ()
    reason: str = ""
    def to_dict(self):
        return {"agent_id": self.agent_id, "compatibility": round(self.compatibility,4),
                "missing_tools": list(self.missing_tools),
                "missing_capabilities": list(self.missing_capabilities), "reason": self.reason}

class AgentCatalog:
    def __init__(self, agents: Iterable[AgentBlueprint] = ()):
        self._agents = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: AgentBlueprint) -> None:
        if agent.status != "validated":
            raise ValueError("Solo un agente validado puede registrarse en el catálogo")
        if agent.state == "retired":
            raise ValueError("Un agente retirado no puede registrarse en el catálogo")
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> AgentBlueprint | None:
        return self._agents.get(str(agent_id))

    def search(self, *, requirements=(), tools=(), role="", minimum_compatibility=0.70):
        req, needed = {str(x) for x in requirements}, {str(x) for x in tools}
        role_tokens = set(str(role).lower().split())
        matches = []
        for agent in self._agents.values():
            if agent.state not in {"sleeping","active"} or agent.status != "validated": continue
            capabilities = set(agent.actions)|set(agent.context)|{agent.role}
            missing = tuple(sorted(req-capabilities))
            missing_tools = tuple(sorted(needed-set(agent.tools)))
            cap = 1.0 if not req else 1.0-len(missing)/len(req)
            tool = 1.0 if not needed else 1.0-len(missing_tools)/len(needed)
            role_score = 1.0 if not role_tokens else len(role_tokens & set(agent.role.lower().split()))/len(role_tokens)
            compatibility = .50*cap+.30*tool+.20*role_score
            if compatibility >= float(minimum_compatibility):
                matches.append(AgentMatch(agent.id,compatibility,missing_tools,missing,"validated reusable agent"))
        return tuple(sorted(matches,key=lambda x:(-x.compatibility,x.agent_id)))
