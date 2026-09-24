"""Agent Architect for Praxis.

The architect converts an adaptive request into a declarative candidate blueprint.
It never executes a model, activates an agent, mutates the catalog, or changes an
investigation. Reusable validated agents are preferred; generation is only
proposed when the catalog has no compatible reusable agent.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Mapping, Tuple

from adaptive_agent import AdaptiveRequest, AdaptationDecision
from agent_catalog import AgentCatalog
from agent_factory import AgentBlueprint, AgentFactory


@dataclass(frozen=True)
class ArchitectureDecision:
    reusable_agents: Tuple[str, ...] = ()
    candidate: AgentBlueprint | None = None
    reason: str = ""
    pattern_ids: Tuple[str, ...] = ()
    strategy_ids: Tuple[str, ...] = ()

    @property
    def generated(self) -> bool:
        return self.candidate is not None

    def to_dict(self):
        return {
            "reusable_agents": list(self.reusable_agents),
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "reason": self.reason,
            "pattern_ids": list(self.pattern_ids),
            "strategy_ids": list(self.strategy_ids),
        }


class AgentArchitect:
    """Synthesize dormant agent blueprints without executing or registering them."""

    def __init__(self, factory: AgentFactory | None = None, catalog: AgentCatalog | None = None):
        self.factory = factory or AgentFactory()
        self.catalog = catalog or AgentCatalog()

    @staticmethod
    def _slug(value: str) -> str:
        value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return value[:28] or "specialist"

    @staticmethod
    def _stable_id(request: AdaptiveRequest) -> str:
        material = "|".join((
            request.task,
            request.role,
            *request.requirements,
            *request.tools,
            *request.acceptance_criteria,
        ))
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:10]
        return f"adaptive-{AgentArchitect._slug(request.role or request.task)}-{digest}"[:64]

    @staticmethod
    def _infer_specialist_role(
        request: AdaptiveRequest,
        tools: Tuple[str, ...],
        requirements: Tuple[str, ...],
    ) -> str:
        """Infer a stable specialist role from explicit task/tool signals."""
        if any(t in {"canvas", "javascript", "html", "js"} for t in tools):
            return "canvas-html specialist"
        if any(t in {"python", "matplotlib", "plotly"} for t in tools):
            return "python-visualization specialist"
        if any("proof" in x or "formal" in x for x in requirements):
            return "mathematical-proof specialist"
        if any("research" in x or "source" in x for x in requirements):
            return "research specialist"
        if any("code" in x or "implementation" in x for x in requirements):
            return "code specialist"
        return request.role.strip() or "adaptive specialist"

    def synthesize(
        self,
        request: AdaptiveRequest,
        *,
        decision: AdaptationDecision | None = None,
        model_id: str = "adaptive-default",
        validated_patterns: Tuple[Mapping[str, object], ...] = (),
        validated_strategies: Tuple[Mapping[str, object], ...] = (),
    ) -> ArchitectureDecision:
        matches = self.catalog.search(
            requirements=request.requirements,
            tools=request.tools,
            role=request.role,
        )

        pattern_ids = tuple(
            str(p.get("pattern_id"))
            for p in validated_patterns
            if p.get("status") == "validated" and p.get("pattern_id")
        )
        strategy_ids = tuple(
            str(item.get("strategy", {}).get("strategy_id"))
            for item in validated_strategies
            if item.get("strategy", {}).get("status") == "promoted"
            and item.get("strategy", {}).get("strategy_id")
        )

        if matches:
            return ArchitectureDecision(
                reusable_agents=tuple(m.agent_id for m in matches),
                reason="reusable_validated_agent_available",
                pattern_ids=pattern_ids,
                strategy_ids=strategy_ids,
            )

        if decision is not None and not decision.generated_agent_required:
            return ArchitectureDecision(
                reason="generation_not_required",
                pattern_ids=pattern_ids,
                strategy_ids=strategy_ids,
            )

        requirements = tuple(dict.fromkeys(request.requirements))
        tools = tuple(dict.fromkeys(request.tools))
        evaluation = tuple(dict.fromkeys(request.acceptance_criteria))
        actions = tuple(dict.fromkeys((*requirements, *request.acceptance_criteria)))

        strategy_context = tuple(
            f"validated_strategy:{sid}" for sid in strategy_ids
        )
        pattern_context = tuple(f"validated_pattern:{pid}" for pid in pattern_ids)
        role = self._infer_specialist_role(request, tools, requirements)
        candidate = self.factory.create(
            agent_id=self._stable_id(request),
            role=role,
            model_id=model_id,
            tools=tools,
            context=(
                request.task,
                *requirements,
                *strategy_context,
                *pattern_context,
            ),
            memory=tuple(sorted(str(k) for k in request.context)),
            evaluation=evaluation,
            actions=actions,
            source="agent_architect",
        )
        return ArchitectureDecision(
            candidate=candidate,
            reason="no_reusable_validated_agent_available",
            pattern_ids=pattern_ids,
            strategy_ids=strategy_ids,
        )

    def from_request(
        self,
        request: AdaptiveRequest,
        *,
        model_id: str = "adaptive-default",
    ) -> ArchitectureDecision:
        return self.synthesize(request, model_id=model_id)
