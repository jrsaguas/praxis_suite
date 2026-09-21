"""Executable dependency graph for specialist-agent orchestration.

The graph plans work from agent contracts without coupling execution to a
specific LLM. A runtime adapter can execute each task and return artifacts;
failed quality gates can block only the affected branch.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple
from agent_architecture import AGENTS, AgentSpec


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    agent_id: str
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    depends_on: Tuple[str, ...]
    quality_gates: Tuple[str, ...]
    status: str = "pending"
    model_id: Optional[str] = None


@dataclass(frozen=True)
class ExecutionPlan:
    tasks: Tuple[AgentTask, ...]
    selected_agents: Tuple[str, ...]
    depth_requirements: Mapping[str, object] = field(default_factory=dict)

    def ready(self, completed: Iterable[str]) -> Tuple[AgentTask, ...]:
        done = set(completed)
        return tuple(t for t in self.tasks if t.status == "pending" and set(t.depends_on) <= done)


class AgentGraphPlanner:
    def __init__(self, agents: Iterable[AgentSpec] = AGENTS):
        self._agents = {a.id: a for a in agents}

    def plan(
        self,
        *,
        requested_agents: Optional[Iterable[str]] = None,
        required_artifacts: Iterable[str] = (),
        depth_requirements: Optional[Mapping[str, object]] = None,
        model_overrides: Optional[Mapping[str, str]] = None,
    ) -> ExecutionPlan:
        requested = set(requested_agents or ())
        artifacts = set(required_artifacts)
        selected = self._closure(requested, artifacts)
        selected.update(self._agents_required_by_depth(depth_requirements or {}))
        selected = self._closure(selected, set())
        tasks = []
        overrides = dict(model_overrides or {})
        try:
            from model_registry import ModelRouter
            router = ModelRouter()
        except Exception:
            router = None
        for agent_id in self._topological(selected):
            spec = self._agents[agent_id]
            deps = tuple(d for d in spec.depends_on if d in selected)
            tasks.append(AgentTask(
                task_id=f"task:{agent_id}",
                agent_id=agent_id,
                model_id=(router.resolve(agent_id, overrides.get(agent_id)).model_id if router else None),
                inputs=spec.inputs,
                outputs=spec.outputs,
                depends_on=tuple(f"task:{d}" for d in deps),
                quality_gates=spec.quality_gates,
            ))
        return ExecutionPlan(tuple(tasks), tuple(a.agent_id for a in tasks), depth_requirements or {})


    @staticmethod
    def _agents_required_by_depth(requirements: Mapping[str, object]) -> set[str]:
        required = set()
        if int(requirements.get("proof_expectation", 0)) >= 60:
            required.add("proof_specialist")
        if int(requirements.get("research_expectation", 0)) >= 60:
            required.add("research_specialist")
        if int(requirements.get("visualization_expectation", 0)) >= 60:
            required.add("representation_designer")
        if int(requirements.get("experimentation_expectation", 0)) >= 70:
            required.update(("python_visualizer", "code_reviewer"))
        if int(requirements.get("formalism_expectation", 0)) >= 80:
            required.add("foundation_analyst")
        if int(requirements.get("generalization_expectation", 0)) >= 80:
            required.add("research_specialist")
        return required

    def _closure(self, requested: set[str], artifacts: set[str]) -> set[str]:
        owners = {
            "python": "python_visualizer", "figure": "python_visualizer",
            "canvas": "canvas_engineer", "proof": "proof_specialist",
            "research": "research_specialist", "markdown": "document_engineer",
            "html": "document_engineer", "docx": "document_engineer",
        }
        selected = set(requested)
        selected.update(owners[a] for a in artifacts if a in owners)
        changed = True
        while changed:
            changed = False
            for agent_id in tuple(selected):
                for dep in self._agents[agent_id].depends_on:
                    if dep not in selected:
                        selected.add(dep)
                        changed = True
        return selected

    def _topological(self, selected: set[str]) -> List[str]:
        pending = {x: {d for d in self._agents[x].depends_on if d in selected} for x in selected}
        result = []
        while pending:
            ready = sorted(x for x, deps in pending.items() if not deps)
            if not ready:
                raise ValueError("El grafo de agentes contiene una dependencia circular")
            result.extend(ready)
            for x in ready:
                pending.pop(x)
            for deps in pending.values():
                deps.difference_update(ready)
        return result
