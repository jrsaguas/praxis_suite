"""Runtime for executing the specialist-agent graph.

The runtime is deliberately provider-agnostic. An adapter supplies the actual
agent execution; the runtime owns dependency scheduling, artifact passing,
quality gates, retries and traceability.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple
from agent_graph import ExecutionPlan, AgentTask


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    agent_id: str
    status: str
    outputs: Mapping[str, Any] = field(default_factory=dict)
    quality: Mapping[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    attempts: int = 1


@dataclass(frozen=True)
class ExecutionTrace:
    status: str
    results: Tuple[TaskResult, ...]
    artifacts: Mapping[str, Any]
    completed: Tuple[str, ...]
    blocked: Tuple[str, ...]


class AgentRuntime:
    def __init__(
        self,
        executor: Callable[[AgentTask, Mapping[str, Any]], Mapping[str, Any]],
        quality_gate: Optional[Callable[[AgentTask, Mapping[str, Any]], Mapping[str, Any]]] = None,
        *,
        max_retries: int = 1,
    ):
        self.executor = executor
        self.quality_gate = quality_gate or (lambda task, result: {"passed": True})
        self.max_retries = max(0, int(max_retries))

    def run(self, plan: ExecutionPlan, initial_context: Optional[Mapping[str, Any]] = None) -> ExecutionTrace:
        artifacts: Dict[str, Any] = dict(initial_context or {})
        completed = []
        results = []
        blocked = []
        pending = {task.task_id: task for task in plan.tasks}

        while pending:
            ready = [task for task in pending.values() if all(dep in completed for dep in task.depends_on)]
            if not ready:
                blocked.extend(sorted(pending))
                break

            progress = False
            for task in ready:
                result = self._run_task(task, artifacts)
                results.append(result)
                pending.pop(task.task_id, None)
                if result.status == "completed":
                    artifacts.update(result.outputs)
                    completed.append(task.task_id)
                    progress = True
                else:
                    blocked.append(task.task_id)

            if not progress:
                blocked.extend(sorted(pending))
                break

        status = "completed" if not pending and not blocked else "partial" if completed else "failed"
        return ExecutionTrace(status, tuple(results), dict(artifacts), tuple(completed), tuple(sorted(set(blocked))))

    def _run_task(self, task: AgentTask, artifacts: Mapping[str, Any]) -> TaskResult:
        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                output = dict(self.executor(task, artifacts))
                gate = dict(self.quality_gate(task, output))
                if not gate.get("passed", False):
                    last_error = str(gate.get("reason", "quality gate failed"))
                    continue
                return TaskResult(task.task_id, task.agent_id, "completed", output, gate, attempts=attempt)
            except Exception as exc:
                last_error = str(exc)
        return TaskResult(task.task_id, task.agent_id, "failed", error=last_error, attempts=self.max_retries + 1)
