"""Runtime for executing the specialist-agent graph.

The runtime is deliberately provider-agnostic. An adapter supplies the actual
agent execution; the runtime owns dependency scheduling, artifact passing,
quality gates, retries and traceability.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple
from agent_graph import ExecutionPlan, AgentTask
from agent_adapters import adapter_for


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    agent_id: str
    status: str
    model_id: Optional[str] = None
    outputs: Mapping[str, Any] = field(default_factory=dict)
    quality: Mapping[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    attempts: int = 1


@dataclass(frozen=True)
class ExecutionEvent:
    sequence: int
    task_id: str
    agent_id: str
    phase: str
    status: str
    model_id: Optional[str] = None
    input_keys: Tuple[str, ...] = ()
    output_keys: Tuple[str, ...] = ()
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "model_id": self.model_id,
            "phase": self.phase,
            "status": self.status,
            "input_keys": list(self.input_keys),
            "output_keys": list(self.output_keys),
            "message": self.message,
        }


@dataclass(frozen=True)
class ExecutionTrace:
    status: str
    results: Tuple[TaskResult, ...]
    artifacts: Mapping[str, Any]
    completed: Tuple[str, ...]
    blocked: Tuple[str, ...]
    events: Tuple[ExecutionEvent, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "completed": list(self.completed),
            "blocked": list(self.blocked),
            "events": [event.to_dict() for event in self.events],
            "results": [
                {
                    "task_id": result.task_id,
                    "agent_id": result.agent_id,
                    "model_id": result.model_id,
                    "status": result.status,
                    "outputs": dict(result.outputs),
                    "quality": dict(result.quality),
                    "error": result.error,
                    "attempts": result.attempts,
                }
                for result in self.results
            ],
        }


def default_executor(task: AgentTask, context: Mapping[str, Any]) -> Mapping[str, Any]:
    adapter = adapter_for(task.agent_id)
    if adapter is None:
        raise LookupError(f"No existe adaptador operativo para {task.agent_id}")
    return adapter(task, context)


class AgentRuntime:
    def __init__(
        self,
        executor: Callable[[AgentTask, Mapping[str, Any]], Mapping[str, Any]],
        quality_gate: Optional[Callable[[AgentTask, Mapping[str, Any]], Mapping[str, Any]]] = None,
        *,
        max_retries: int = 1,
        event_sink: Optional[Callable[[ExecutionEvent], None]] = None,
    ):
        self.executor = executor
        self.event_sink = event_sink
        self.quality_gate = quality_gate or (lambda task, result: {"passed": True})
        self.max_retries = max(0, int(max_retries))

    def run(self, plan: ExecutionPlan, initial_context: Optional[Mapping[str, Any]] = None) -> ExecutionTrace:
        artifacts: Dict[str, Any] = dict(initial_context or {})
        if "model_assignments" not in artifacts:
            artifacts["model_assignments"] = {t.agent_id: t.model_id for t in plan.tasks if t.model_id}
        completed = []
        results = []
        events = []
        blocked = []
        sequence = 0
        pending = {task.task_id: task for task in plan.tasks}

        while pending:
            ready = [task for task in pending.values() if all(dep in completed for dep in task.depends_on)]
            if not ready:
                blocked.extend(sorted(pending))
                break

            progress = False
            for task in ready:
                before_keys = tuple(sorted(artifacts.keys()))
                result = self._run_task(task, artifacts)
                sequence += 1
                event = ExecutionEvent(sequence, task.task_id, task.agent_id, "task", result.status, task.model_id, before_keys, tuple(sorted(result.outputs.keys())), result.error or "completed")
                events.append(event)
                if self.event_sink is not None:
                    self.event_sink(event)
                results.append(result)
                pending.pop(task.task_id, None)
                if result.status == "completed":
                    artifacts.update(result.outputs)
                    artifacts.setdefault("agent_results", {})[task.agent_id] = dict(result.outputs)
                    completed.append(task.task_id)
                    progress = True
                else:
                    blocked.append(task.task_id)
                    for descendant in pending.values():
                        if task.task_id in descendant.depends_on and descendant.task_id not in blocked:
                            blocked.append(descendant.task_id)

            if not progress:
                blocked.extend(sorted(pending))
                break

        status = "completed" if not pending and not blocked else "partial" if completed else "failed"
        return ExecutionTrace(status, tuple(results), dict(artifacts), tuple(completed), tuple(sorted(set(blocked))), tuple(events))

    def _run_task(self, task: AgentTask, artifacts: Mapping[str, Any]) -> TaskResult:
        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                output = dict(self.executor(task, artifacts))
                gate = dict(self.quality_gate(task, output))
                if not gate.get("passed", False):
                    last_error = str(gate.get("reason", "quality gate failed"))
                    continue
                return TaskResult(task.task_id, task.agent_id, "completed", task.model_id, output, gate, attempts=attempt)
            except Exception as exc:
                last_error = str(exc)
        return TaskResult(task.task_id, task.agent_id, "failed", model_id=task.model_id, error=last_error, attempts=self.max_retries + 1)
