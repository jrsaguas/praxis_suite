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
    archetype_id: Optional[str] = None
    required_tools: Tuple[str, ...] = ()
    optional_tools: Tuple[str, ...] = ()
    model_capabilities: Tuple[str, ...] = ()
    depth_requirements: Tuple[Tuple[str, int], ...] = ()
    delivery_gates: Tuple[str, ...] = ()
    missing_tools: Tuple[str, ...] = ()
    depth_gaps: Tuple[Tuple[str, int, int], ...] = ()


@dataclass(frozen=True)
class ExecutionPlan:
    tasks: Tuple[AgentTask, ...]
    selected_agents: Tuple[str, ...]
    depth_requirements: Mapping[str, object] = field(default_factory=dict)
    planning_metadata: Mapping[str, object] = field(default_factory=dict)

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
        additional_agents: Iterable[AgentSpec] = (),
        available_tools: Iterable[str] = (),
    ) -> ExecutionPlan:
        additional = tuple(additional_agents)
        registry = dict(self._agents)
        for agent in additional:
            registry[agent.id] = agent
        requested = set(requested_agents or ())
        artifacts = set(required_artifacts)
        experience_context = {}
        target_profile = {}
        if isinstance(depth_requirements, Mapping):
            experience_context = dict(depth_requirements.get("experience_context") or {})
            target_profile = dict(depth_requirements.get("evaluation_profile") or {})
            if target_profile and "target_profile" not in experience_context:
                experience_context["target_profile"] = target_profile
        reference_bias = {
            str(ref.get("strategy_id")): float(ref.get("relevance", 0.0))
            for ref in (experience_context.get("references") or [])
            if ref.get("strategy_id")
        }
        selected = self._closure_with_registry(requested, artifacts, registry)
        selected.update(self._agents_required_by_depth(depth_requirements or {}))
        if "final_auditor" not in selected and (selected or requested or artifacts):
            selected.add("final_auditor")
        if "experience_evaluator" not in selected and (selected or requested or artifacts):
            selected.add("experience_evaluator")
        selected = self._closure_with_registry(selected, set(), registry)
        tasks = []
        overrides = dict(model_overrides or {})
        available_tool_set = {str(x) for x in available_tools}
        try:
            from model_registry import ModelRouter
            router = ModelRouter()
        except Exception:
            router = None
        for agent_id in self._topological(selected, registry):
            spec = registry[agent_id]
            deps = tuple(d for d in spec.depends_on if d in selected)
            missing_tools = tuple(sorted(set(spec.required_tools) - available_tool_set)) if available_tool_set else ()
            depth_gaps = self._depth_gaps(spec, depth_requirements)
            tasks.append(AgentTask(
                task_id=f"task:{agent_id}",
                agent_id=agent_id,
                model_id=(router.resolve_with_experience(agent_id, experience_context, overrides.get(agent_id)).model_id if router else None),
                inputs=spec.inputs,
                outputs=spec.outputs,
                depends_on=tuple(f"task:{d}" for d in deps),
                quality_gates=spec.quality_gates,
                status="blocked" if (missing_tools or depth_gaps) else "pending",
                archetype_id=spec.archetype_id,
                required_tools=spec.required_tools,
                optional_tools=spec.optional_tools,
                model_capabilities=spec.model_capabilities,
                depth_requirements=spec.depth_requirements,
                delivery_gates=spec.delivery_gates,
                missing_tools=missing_tools,
                depth_gaps=depth_gaps,
            ))
        if isinstance(depth_requirements, Mapping):
            depth_payload = dict(depth_requirements)
        elif isinstance(depth_requirements, (list, tuple, set)):
            depth_payload = {str(item): 100 for item in depth_requirements}
        else:
            depth_payload = {}
        if experience_context or target_profile:
            depth_payload["experience_context"] = {
                **experience_context,
                **({"target_profile": target_profile} if target_profile else {}),
            }
        if reference_bias:
            depth_payload["experience_context"] = {
                **dict(depth_payload.get("experience_context") or {}),
                "strategy_bias": reference_bias,
                "selection_policy": experience_context.get("selection_policy", "evidence_weighted_multi_reference"),
            }
        operational = {
            task.agent_id: {
                "archetype_id": task.archetype_id,
                "required_tools": list(task.required_tools),
                "optional_tools": list(task.optional_tools),
                "model_capabilities": list(task.model_capabilities),
                "depth_requirements": dict(task.depth_requirements),
                "delivery_gates": list(task.delivery_gates),
                "missing_tools": list(task.missing_tools),
                "depth_gaps": [list(gap) for gap in task.depth_gaps],
            }
            for task in tasks
            if task.archetype_id
        }
        return ExecutionPlan(
            tuple(tasks),
            tuple(a.agent_id for a in tasks),
            depth_payload,
            {"operational_profiles": operational},
        )


    @staticmethod
    def _depth_gaps(spec: AgentSpec, requirements: Optional[Mapping[str, object]]) -> Tuple[Tuple[str, int, int], ...]:
        """Return explicit depth deficits against an archetype minimum contract."""
        if not isinstance(requirements, Mapping) or not spec.depth_requirements:
            return ()
        profile = requirements.get("profile")
        values = dict(profile) if isinstance(profile, Mapping) else {}
        values.update({k: v for k, v in requirements.items() if k != "profile"})
        aliases = {
            "proof": ("proof", "proof_expectation"),
            "research": ("research", "research_expectation"),
            "visualization": ("visualization", "visualization_expectation"),
            "experimentation": ("experimentation", "experimentation_expectation"),
            "formalism": ("formalism", "formalism_expectation"),
            "generalization": ("generalization", "generalization_expectation"),
            "rigor": ("rigor", "rigor_expectation"),
            "prerequisites": ("prerequisites", "prerequisites_expectation"),
            "applications": ("applications", "application_expectation"),
        }
        gaps = []
        for dimension, minimum in spec.depth_requirements:
            supplied = next((values[key] for key in aliases.get(dimension, (dimension,)) if key in values), None)
            if supplied is None:
                continue
            try:
                actual = int(supplied)
            except (TypeError, ValueError):
                continue
            if actual < int(minimum):
                gaps.append((dimension, int(minimum), actual))
        return tuple(gaps)

    @staticmethod
    def _agents_required_by_depth(requirements: Mapping[str, object]) -> set[str]:
        """Translate either depth thresholds or raw profile dimensions into roles."""
        required = set()
        if isinstance(requirements, (list, tuple, set)):
            requirements = {str(x): 100 for x in requirements}
        requirements = dict(requirements or {})
        profile = requirements.get("profile")
        if isinstance(profile, Mapping):
            requirements = {**dict(profile), **requirements}
        aliases = {
            "proof_expectation": ("proof_expectation", "proof"),
            "research_expectation": ("research_expectation", "research"),
            "visualization_expectation": ("visualization_expectation", "visualization"),
            "experimentation_expectation": ("experimentation_expectation", "experimentation"),
            "formalism_expectation": ("formalism_expectation", "formalism"),
            "generalization_expectation": ("generalization_expectation", "generalization"),
        }
        def level(name: str) -> int:
            for key in aliases[name]:
                if key in requirements:
                    try:
                        return int(requirements[key])
                    except (TypeError, ValueError):
                        return 0
            return 0
        if level("proof_expectation") >= 60:
            required.add("proof_specialist")
        if level("research_expectation") >= 60:
            required.add("research_specialist")
        if level("visualization_expectation") >= 60:
            required.add("representation_designer")
        if level("experimentation_expectation") >= 70:
            required.update(("python_visualizer", "code_reviewer"))
        if level("formalism_expectation") >= 80:
            required.add("foundation_analyst")
        if level("generalization_expectation") >= 80:
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

    def _topological(self, selected: set[str], registry: Optional[Mapping[str, AgentSpec]] = None) -> List[str]:
        agents = registry or self._agents
        pending = {x: {d for d in agents[x].depends_on if d in selected} for x in selected}
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

    def _closure_with_registry(self, requested: set[str], artifacts: set[str], registry: Mapping[str, AgentSpec]) -> set[str]:
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
                if agent_id not in registry:
                    raise KeyError(agent_id)
                for dep in registry[agent_id].depends_on:
                    if dep not in selected:
                        selected.add(dep)
                        changed = True
        return selected
