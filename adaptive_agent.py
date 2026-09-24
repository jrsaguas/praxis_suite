"""Adaptive-agent decision layer for Praxis."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Tuple

@dataclass(frozen=True)
class AdaptiveRequest:
    task: str
    context: Mapping[str, object] = field(default_factory=dict)
    requirements: Tuple[str, ...] = ()
    restrictions: Tuple[str, ...] = ()
    tools: Tuple[str, ...] = ()
    acceptance_criteria: Tuple[str, ...] = ()
    role: str = ""
    explicit_activation: bool = False
    @classmethod
    def from_mapping(cls, data):
        def seq(name):
            value=data.get(name) or ()
            return (value,) if isinstance(value,str) else tuple(str(x) for x in value)
        return cls(str(data.get("task") or data.get("user_prompt") or "").strip(),
                   dict(data.get("context") or {}), seq("requirements"), seq("restrictions"),
                   seq("tools"), seq("acceptance_criteria"), str(data.get("role") or ""),
                   bool(data.get("explicit_activation",False)))

@dataclass(frozen=True)
class AdaptationDecision:
    active: bool
    reason: str
    missing_requirements: Tuple[str,...]=()
    reusable_agents: Tuple[str,...]=()
    requested_tools: Tuple[str,...]=()
    generated_agent_required: bool=False
    def to_dict(self):
        return {"active":self.active,"reason":self.reason,
                "missing_requirements":list(self.missing_requirements),
                "reusable_agents":list(self.reusable_agents),
                "requested_tools":list(self.requested_tools),
                "generated_agent_required":self.generated_agent_required}

class AdaptiveAgent:
    def __init__(self, known_capabilities: Mapping[str,Iterable[str]]|None=None, catalog=None):
        self.known_capabilities={str(a):{str(c) for c in caps} for a,caps in (known_capabilities or {}).items()}
        self.catalog=catalog
    def _matches(self, request):
        if not self.catalog: return ()
        return self.catalog.search(requirements=request.requirements, tools=request.tools, role=request.role)
    def decide(self, request):
        if request.explicit_activation:
            matches=self._matches(request)
            return AdaptationDecision(True,"explicit_activation",
                reusable_agents=tuple(m.agent_id for m in matches),requested_tools=request.tools,
                generated_agent_required=not bool(matches))
        available=set().union(*self.known_capabilities.values()) if self.known_capabilities else set()
        missing=tuple(sorted(set(request.requirements)-available))
        if missing:
            matches=self._matches(request)
            return AdaptationDecision(True,"required_capabilities_missing",missing,
                tuple(m.agent_id for m in matches),request.tools,not bool(matches))
        if request.tools and not set(request.tools)<=available:
            missing_tools=tuple(sorted(set(request.tools)-available))
            matches=self._matches(request)
            return AdaptationDecision(True,"required_tools_missing",missing_tools,
                tuple(m.agent_id for m in matches),request.tools,not bool(matches))
        return AdaptationDecision(False,"static_graph_sufficient",requested_tools=request.tools)
