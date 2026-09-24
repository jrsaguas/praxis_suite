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
from typing import Tuple

from adaptive_agent import AdaptiveRequest, AdaptationDecision
from agent_catalog import AgentCatalog
from agent_factory import AgentBlueprint, AgentFactory


@dataclass(frozen=True)
class ArchitectureDecision:
    reusable_agents: Tuple[str, ...] = ()
    candidate: AgentBlueprint | None = None
    reason: str = ""

    @property
    def generated(self) -> bool:
        return self.candidate is not None

    def to_dict(self):
        return {
            "reusable_agents": list(self.reusable_agents),
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "reason": self.reason,
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

    def synthesize(
        self,
        request: AdaptiveRequest,
        *,
        decision: AdaptationDecision | None = None,
        model_id: str = "adaptive-default",
    ) -> ArchitectureDecision:
        matches = self.catalog.search(
            requirements=request.requirements,
            tools=request.tools,
            role=request.role,
        )

        if matches:
            return ArchitectureDecision(
                reusable_agents=tuple(m.agent_id for m in matches),
                reason="reusable_validated_agent_available",
            )

        if decision is not None and not decision.generated_agent_required:
            return ArchitectureDecision(
                reason="generation_not_required",
            )

        role = request.role.strip() or "adaptive specialist"
        requirements = tuple(dict.fromkeys(request.requirements))
        tools = tuple(dict.fromkeys(request.tools))
        evaluation = tuple(dict.fromkeys(request.acceptance_criteria))
        actions = tuple(dict.fromkeys((*requirements, *request.acceptance_criteria)))

        candidate = self.factory.create(
            agent_id=self._stable_id(request),
            role=role,
            model_id=model_id,
            tools=tools,
            context=(request.task, *requirements),
            memory=tuple(sorted(str(k) for k in request.context)),
            evaluation=evaluation,
            actions=actions,
            source="agent_architect",
        )
        return ArchitectureDecision(
            candidate=candidate,
            reason="no_reusable_validated_agent_available",
        )

    def from_request(
        self,
        request: AdaptiveRequest,
        *,
        model_id: str = "adaptive-default",
    ) -> ArchitectureDecision:
        return self.synthesize(request, model_id=model_id)
