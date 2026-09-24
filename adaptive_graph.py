"""Controlled bridge from adaptive selection to the existing agent graph."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping, Tuple

from adaptive_agent import AdaptiveAgent, AdaptiveRequest, AdaptationDecision
from agent_architecture import AgentSpec
from agent_factory import AgentBlueprint
from agent_graph import AgentGraphPlanner, ExecutionPlan
from agent_catalog import AgentCatalog
from agent_architect import AgentArchitect


@dataclass(frozen=True)
class AdaptiveGraphPlan:
    decision: AdaptationDecision
    execution_plan: ExecutionPlan
    generated_candidates: Tuple[str, ...] = ()

    def to_dict(self):
        return {
            "decision": self.decision.to_dict(),
            "execution_plan": {
                "tasks": [task.task_id for task in self.execution_plan.tasks],
                "selected_agents": list(self.execution_plan.selected_agents),
            },
            "generated_candidates": list(self.generated_candidates),
        }


class AdaptiveGraphBridge:
    """Resolve reusable agents, then hand the resulting roles to AgentGraphPlanner.

    This bridge is planning-only: it never activates agents, calls models, or
    mutates investigation state. Unvalidated factory candidates are reported
    separately and cannot enter the execution plan.
    """

    def __init__(
        self,
        static_capabilities: Mapping[str, Iterable[str]] | None = None,
        catalog: AgentCatalog | None = None,
        planner: AgentGraphPlanner | None = None,
        architect: AgentArchitect | None = None,
    ):
        self.adaptive = AdaptiveAgent(static_capabilities, catalog)
        self.catalog = catalog
        self.planner = planner or AgentGraphPlanner()
        self.architect = architect or AgentArchitect(catalog=catalog)

    def plan(
        self,
        request: AdaptiveRequest,
        *,
        requested_agents: Iterable[str] = (),
        required_artifacts: Iterable[str] = (),
        depth_requirements: Mapping[str, object] | None = None,
        model_overrides: Mapping[str, str] | None = None,
    ) -> AdaptiveGraphPlan:
        decision = self.adaptive.decide(request)
        reusable_specs = tuple(
            self._blueprint_to_spec(match.agent_id)
            for match in self._matches(request)
        )
        selected = tuple(dict.fromkeys(
            tuple(str(agent) for agent in requested_agents)
            + tuple(spec.id for spec in reusable_specs)
        ))
        plan = self.planner.plan(
            requested_agents=selected,
            required_artifacts=required_artifacts,
            depth_requirements=depth_requirements,
            model_overrides=model_overrides,
            additional_agents=reusable_specs,
        )
        architecture = self.architect.synthesize(request, decision=decision)
        generated_candidates = (architecture.candidate.id,) if architecture.candidate else ()
        planning_metadata = {
            "adaptive_selection": {
                **decision.to_dict(),
                "selected_reusable_agents": [spec.id for spec in reusable_specs],
                "generated_candidates": list(generated_candidates),
                "architecture_reason": architecture.reason,
            },
            "mathematical_depth": dict(depth_requirements or {}),
            "execution_agents": list(plan.selected_agents),
        }
        plan = replace(plan, planning_metadata=planning_metadata)
        return AdaptiveGraphPlan(decision, plan, generated_candidates)

    def _matches(self, request: AdaptiveRequest):
        if not self.catalog or not request.requirements and not request.tools and not request.role:
            return ()
        return self.catalog.search(
            requirements=request.requirements,
            tools=request.tools,
            role=request.role,
        )

    def _blueprint_to_spec(self, agent_id: str) -> AgentSpec:
        assert self.catalog is not None
        blueprint = self.catalog.get(agent_id)
        if blueprint is None:
            raise KeyError(f"reusable agent not found: {agent_id}")
        return AgentSpec(
            id=blueprint.id,
            mission=blueprint.role,
            inputs=tuple(blueprint.context),
            outputs=tuple(blueprint.actions),
            quality_gates=tuple(blueprint.evaluation),
            tool_profile=tuple(blueprint.tools),
        )
