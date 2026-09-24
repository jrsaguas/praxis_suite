"""Adaptive-agent decision layer for Praxis.

The adaptive agent is a planner component, not an LLM. It stays inactive unless
the task requires capabilities that the current static graph cannot satisfy,
or the caller explicitly requests adaptation.
"""
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
    explicit_activation: bool = False

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "AdaptiveRequest":
        def seq(name: str) -> Tuple[str, ...]:
            value = data.get(name) or ()
            if isinstance(value, str):
                return (value,)
            return tuple(str(x) for x in value)

        return cls(
            task=str(data.get("task") or data.get("user_prompt") or "").strip(),
            context=dict(data.get("context") or {}),
            requirements=seq("requirements"),
            restrictions=seq("restrictions"),
            tools=seq("tools"),
            acceptance_criteria=seq("acceptance_criteria"),
            explicit_activation=bool(data.get("explicit_activation", False)),
        )


@dataclass(frozen=True)
class AdaptationDecision:
    active: bool
    reason: str
    missing_requirements: Tuple[str, ...] = ()
    reusable_agents: Tuple[str, ...] = ()
    requested_tools: Tuple[str, ...] = ()

    def to_dict(self):
        return {
            "active": self.active,
            "reason": self.reason,
            "missing_requirements": list(self.missing_requirements),
            "reusable_agents": list(self.reusable_agents),
            "requested_tools": list(self.requested_tools),
        }


class AdaptiveAgent:
    """Decide whether adaptation is necessary without executing an agent."""

    def __init__(self, known_capabilities: Mapping[str, Iterable[str]] | None = None):
        self.known_capabilities = {
            str(agent): {str(cap) for cap in capabilities}
            for agent, capabilities in (known_capabilities or {}).items()
        }

    def decide(self, request: AdaptiveRequest) -> AdaptationDecision:
        if request.explicit_activation:
            return AdaptationDecision(
                True, "explicit_activation", requested_tools=request.tools
            )

        available = set().union(*self.known_capabilities.values()) if self.known_capabilities else set()
        missing = tuple(sorted(set(request.requirements) - available))
        if missing:
            return AdaptationDecision(
                True,
                "required_capabilities_missing",
                missing_requirements=missing,
                requested_tools=request.tools,
            )

        if request.tools and not set(request.tools) <= available:
            missing_tools = tuple(sorted(set(request.tools) - available))
            return AdaptationDecision(
                True,
                "required_tools_missing",
                missing_requirements=missing_tools,
                requested_tools=request.tools,
            )

        return AdaptationDecision(False, "static_graph_sufficient", requested_tools=request.tools)
