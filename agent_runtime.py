"""Runtime for executing the specialist-agent graph.

The runtime is deliberately provider-agnostic. An adapter supplies the actual
agent execution; the runtime owns dependency scheduling, explicit quality and
delivery gates, retries and traceability.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional, Tuple
from agent_graph import ExecutionPlan, AgentTask
from agent_adapters import adapter_for
from agent_delivery import GateEvaluation, evaluate_gate_contract
from agent_gate_verifiers import verify_output


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    agent_id: str
    status: str
    model_id: Optional[str] = None
    outputs: Mapping[str, Any] = field(default_factory=dict)
    quality: Mapping[str, Any] = field(default_factory=dict)
    delivery: Mapping[str, Any] = field(default_factory=dict)
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
    gate: Mapping[str, Any] = field(default_factory=dict)

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
            "gate": dict(self.gate),
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
                    "delivery": dict(result.delivery),
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
        delivery_gate: Optional[Callable[[AgentTask, Mapping[str, Any]], Mapping[str, Any]]] = None,
        *,
        max_retries: int = 1,
        event_sink: Optional[Callable[[ExecutionEvent], None]] = None,
        experience_sink: Optional[Callable[[AgentTask, Mapping[str, Any], Mapping[str, Any]], None]] = None,
    ):
        self.executor = executor
        self.event_sink = event_sink
        self.experience_sink = experience_sink
        self.quality_gate = quality_gate
        self.delivery_gate = delivery_gate
        self.max_retries = max(0, int(max_retries))

    def run(self, plan: ExecutionPlan, initial_context: Optional[Mapping[str, Any]] = None) -> ExecutionTrace:
        artifacts: Dict[str, Any] = dict(initial_context or {})
        if "model_assignments" not in artifacts:
            artifacts["model_assignments"] = {t.agent_id: t.model_id for t in plan.tasks if t.model_id}
        completed = []
        completed_task_ids = set()
        results = []
        events = []
        blocked = []
        sequence = 0
        planning_metadata = dict(getattr(plan, "planning_metadata", {}) or {})
        if planning_metadata:
            event = ExecutionEvent(0, "plan:selection", "orchestrator", "planning", "recorded", message="structured planning metadata recorded")
            events.append(event)
            if self.event_sink is not None:
                self.event_sink(event)
            artifacts["planning_metadata"] = planning_metadata

        pending = {task.task_id: task for task in plan.tasks}
        for task in plan.tasks:
            if task.status == "blocked":
                blocked.append(task.task_id)

        while pending:
            for task_id, task in tuple(pending.items()):
                if task.status == "blocked":
                    pending.pop(task_id)
                    for descendant in pending.values():
                        if task_id in descendant.depends_on:
                            blocked.append(descendant.task_id)

            ready = [
                task for task in pending.values()
                if task.task_id not in blocked
                and all(dep in completed_task_ids for dep in task.depends_on)
            ]
            if not ready:
                blocked.extend(sorted(pending))
                break

            progress = False
            for task in ready:
                before_keys = tuple(sorted(artifacts.keys()))
                result, gate_events = self._run_task(task, artifacts, sequence + 1)
                sequence += len(gate_events) + 1
                events.extend(gate_events)
                if self.event_sink is not None:
                    for event in gate_events:
                        self.event_sink(event)
                event = ExecutionEvent(
                    sequence, task.task_id, task.agent_id, "task", result.status,
                    task.model_id, before_keys, tuple(sorted(result.outputs.keys())),
                    result.error or "completed",
                )
                events.append(event)
                if self.event_sink is not None:
                    self.event_sink(event)
                results.append(result)
                pending.pop(task.task_id, None)

                if result.status == "completed":
                    artifacts.update(result.outputs)
                    artifacts.setdefault("agent_results", {})[task.agent_id] = dict(result.outputs)
                    if task.agent_id == "final_auditor":
                        artifacts["final_audit"] = dict(result.outputs.get("final_audit") or result.outputs.get("audit") or {})
                    if task.agent_id == "experience_evaluator" and self.experience_sink is not None:
                        try:
                            self.experience_sink(task, artifacts, result.outputs)
                        except Exception as exc:
                            artifacts.setdefault("experience_persistence_errors", []).append({
                                "task_id": task.task_id, "agent_id": task.agent_id, "error": str(exc),
                            })
                    completed.append(task.agent_id)
                    completed_task_ids.add(task.task_id)
                else:
                    blocked.append(task.task_id)
                    for descendant in pending.values():
                        if task.task_id in descendant.depends_on:
                            blocked.append(descendant.task_id)
                progress = True

            if not progress:
                blocked.extend(sorted(pending))
                break

        status = "completed" if not pending and not blocked else "partial" if completed else "failed"
        return ExecutionTrace(status, tuple(results), dict(artifacts), tuple(completed), tuple(sorted(set(blocked))), tuple(events))

    def _run_task(self, task: AgentTask, artifacts: Mapping[str, Any], sequence_start: int) -> Tuple[TaskResult, Tuple[ExecutionEvent, ...]]:
        last_error = None
        gate_events = []
        for attempt in range(1, self.max_retries + 2):
            try:
                output = dict(self.executor(task, artifacts))

                quality = (
                    dict(self.quality_gate(task, output))
                    if self.quality_gate is not None
                    else (
                        evaluate_gate_contract(task, output, "quality").to_dict()
                        if "gate_results" in output
                        else verify_output(task, output, "quality").to_dict()
                    )
                )
                quality_eval = self._as_gate_evaluation(task, quality, "quality")
                gate_events.append(ExecutionEvent(
                    sequence_start + len(gate_events), task.task_id, task.agent_id,
                    "quality_gate", "passed" if quality_eval.passed else "failed",
                    task.model_id, output_keys=tuple(sorted(output.keys())),
                    message="quality gates evaluated", gate=quality_eval.to_dict(),
                ))
                if not quality_eval.passed:
                    last_error = self._gate_reason(quality_eval)
                    continue

                delivery = (
                    dict(self.delivery_gate(task, output))
                    if self.delivery_gate is not None
                    else (
                        evaluate_gate_contract(task, output, "delivery").to_dict()
                        if "gate_results" in output
                        else verify_output(task, output, "delivery").to_dict()
                    )
                )
                delivery_eval = self._as_gate_evaluation(task, delivery, "delivery")
                gate_events.append(ExecutionEvent(
                    sequence_start + len(gate_events), task.task_id, task.agent_id,
                    "delivery_gate", "passed" if delivery_eval.passed else "failed",
                    task.model_id, output_keys=tuple(sorted(output.keys())),
                    message="delivery gates evaluated", gate=delivery_eval.to_dict(),
                ))
                if not delivery_eval.passed:
                    last_error = self._gate_reason(delivery_eval)
                    continue

                return TaskResult(
                    task.task_id, task.agent_id, "completed", task.model_id,
                    output, quality, delivery, attempts=attempt,
                ), tuple(gate_events)
            except Exception as exc:
                last_error = str(exc)
        return TaskResult(
            task.task_id, task.agent_id, "failed", model_id=task.model_id,
            quality={}, delivery={}, error=last_error, attempts=self.max_retries + 1,
        ), tuple(gate_events)

    @staticmethod
    def _as_gate_evaluation(task: AgentTask, data: Mapping[str, Any], phase: str) -> GateEvaluation:
        if {"required_gates", "failed_gates", "missing_gates", "blocked_handoff"} <= set(data):
            return GateEvaluation(
                phase, task.agent_id, bool(data.get("passed")),
                tuple(data.get("required_gates") or ()),
                tuple(data.get("failed_gates") or ()),
                tuple(data.get("missing_gates") or ()),
                dict(data.get("evidence") or {}),
            )
        required = tuple(task.quality_gates if phase == "quality" else task.delivery_gates)
        if required and data.get("passed") is True and "gate_results" not in data:
            return GateEvaluation(phase, task.agent_id, False, required, missing_gates=required, evidence=data)
        return GateEvaluation(phase, task.agent_id, bool(data.get("passed", False)), required, evidence=data)

    @staticmethod
    def _gate_reason(gate: GateEvaluation) -> str:
        parts = []
        if gate.failed_gates:
            parts.append("failed: " + ", ".join(gate.failed_gates))
        if gate.missing_gates:
            parts.append("missing: " + ", ".join(gate.missing_gates))
        return f"{gate.phase} gate contract blocked handoff" + (f" ({'; '.join(parts)})" if parts else "")
