"""Controlled bridge from adaptive selection to the existing agent graph."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping, Tuple

from adaptive_agent import AdaptiveAgent, AdaptiveRequest, AdaptationDecision
from agent_architecture import AgentSpec
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
    """Resolve reusable agents, strategies, then hand roles to the graph.

    This bridge is planning-only: it never activates agents, calls models, or
    mutates investigation state. Unvalidated factory candidates are reported
    separately and cannot enter the execution plan. Strategy definitions must
    already be promoted; validated patterns are evidence only.
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
        selected_patterns: Iterable[Mapping[str, object]] = (),
        strategy_context: Mapping[str, object] | None = None,
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

        patterns = tuple(selected_patterns)
        strategies = tuple(
            item for item in (strategy_context or {}).get("strategies", [])
            if str(item.get("strategy", {}).get("status", "")) == "promoted"
        )
        architecture = self.architect.synthesize(
            request,
            decision=decision,
            validated_patterns=patterns,
            validated_strategies=strategies,
        )
        generated_candidates = (architecture.candidate.id,) if architecture.candidate else ()

        selected_pattern_metadata = [
            {
                "pattern_id": str(pattern.get("pattern_id")),
                "task_family": str(pattern.get("task_family", "")),
                "strategy_id": str(pattern.get("strategy_id", "")),
                "selection": dict(pattern.get("selection") or {}),
                "source_record_ids": [str(x) for x in pattern.get("source_record_ids", [])],
            }
            for pattern in patterns
            if pattern.get("status") == "validated" and pattern.get("pattern_id")
        ]
        selected_strategy_metadata = [
            {
                "strategy_id": str(item.get("strategy", {}).get("strategy_id")),
                "selection_score": float(item.get("selection_score", 0.0)),
                "signals": dict(item.get("signals") or {}),
                "validated_pattern_evidence": dict(
                    item.get("validated_pattern_evidence") or {}
                ),
            }
            for item in strategies
            if item.get("strategy", {}).get("strategy_id")
        ]
        planning_metadata = {
            "operational_profiles": dict(plan.planning_metadata.get("operational_profiles") or {}),
            "adaptive_selection": {
                **decision.to_dict(),
                "selected_reusable_agents": [spec.id for spec in reusable_specs],
                "generated_candidates": list(generated_candidates),
                "architecture_reason": architecture.reason,
                "strategy_ids": list(architecture.strategy_ids),
            },
            "mathematical_depth": dict(depth_requirements or {}),
            "execution_agents": list(plan.selected_agents),
            "selected_patterns": selected_pattern_metadata,
            "selected_strategies": selected_strategy_metadata,
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

    @staticmethod
    def _archetype_id(blueprint) -> str | None:
        for item in blueprint.context:
            if str(item).startswith("archetype:"):
                value = str(item).split(":", 1)[1].strip()
                return value or None
        return None

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
            archetype_id=self._archetype_id(blueprint),
        )
