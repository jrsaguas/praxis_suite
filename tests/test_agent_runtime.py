import unittest

from agent_graph import AgentGraphPlanner
from agent_runtime import AgentRuntime


def passing_contract(task):
    return {
        "gate_results": {
            gate: {"passed": True, "evidence": f"{gate}:verified"}
            for gate in (*task.quality_gates, *task.delivery_gates)
        }
    }


class AgentRuntimeTests(unittest.TestCase):
    def test_runtime_passes_artifacts_between_agents(self):
        plan = AgentGraphPlanner().plan(required_artifacts=["canvas"])
        seen = []

        def execute(task, context):
            seen.append((task.agent_id, sorted(context)))
            return {task.agent_id: True, **passing_contract(task)}

        trace = AgentRuntime(execute).run(plan)
        self.assertEqual(trace.status, "completed")
        self.assertIn("canvas_engineer", trace.completed)
        self.assertTrue(any(agent == "canvas_engineer" and "representation_designer" in keys for agent, keys in seen))

    def test_failed_gate_retries_only_that_task_and_blocks_descendants(self):
        plan = AgentGraphPlanner().plan(required_artifacts=["canvas"])
        attempts = {}
        def execute(task, context):
            attempts[task.task_id] = attempts.get(task.task_id, 0) + 1
            return {task.agent_id: True, **passing_contract(task)}
        def gate(task, output):
            if task.agent_id == "representation_designer" and attempts[task.task_id] == 1:
                return {"passed": False, "reason": "representation mismatch"}
            return {"passed": True, "gate_results": {
                gate: {"passed": True} for gate in task.quality_gates
            }}
        trace = AgentRuntime(execute, gate, max_retries=1).run(plan)
        self.assertEqual(trace.status, "completed")
        self.assertEqual(attempts["task:representation_designer"], 2)
        self.assertNotIn("task:canvas_engineer", trace.blocked)

    def test_delivery_failure_blocks_descendants_without_publishing_outputs(self):
        plan = AgentGraphPlanner().plan(requested_agents=["canvas_engineer"])
        def execute(task, context):
            return {task.agent_id: True, **passing_contract(task)}
        def delivery(task, output):
            if task.agent_id == "canvas_engineer":
                return {"passed": False, "reason": "interaction test failed"}
            return {"passed": True, "gate_results": {g: {"passed": True} for g in task.delivery_gates}}
        trace = AgentRuntime(execute, delivery_gate=delivery, max_retries=0).run(plan)
        result = next(r for r in trace.results if r.agent_id == "canvas_engineer")
        self.assertEqual(result.status, "failed")
        self.assertNotIn("canvas_engineer", trace.completed)
        self.assertIn("task:canvas_engineer", trace.blocked)
        self.assertNotIn("canvas_engineer", trace.artifacts)

    def test_missing_explicit_gate_evidence_cannot_pass(self):
        plan = AgentGraphPlanner().plan(requested_agents=["mathematical_resolver"])

        def execute(task, context):
            if task.agent_id == "mathematical_resolver":
                return {task.agent_id: True}
            return {task.agent_id: True, **passing_contract(task)}

        trace = AgentRuntime(execute, max_retries=0).run(plan)
        self.assertEqual(trace.status, "failed")
        result = next(r for r in trace.results if r.agent_id == "mathematical_resolver")
        self.assertEqual(result.status, "failed")
        self.assertTrue(result.quality["missing_gates"])
        self.assertEqual(result.delivery, {})

    def test_blocked_planning_task_never_executes(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["canvas_engineer"],
            available_tools=("html", "javascript"),
        )
        called = []
        trace = AgentRuntime(lambda task, context: called.append(task.agent_id) or {}, max_retries=0).run(plan)
        self.assertNotIn("canvas_engineer", called)
        self.assertIn("task:canvas_engineer", trace.blocked)

    def test_trace_contains_gate_evidence(self):
        plan = AgentGraphPlanner().plan(requested_agents=["mathematical_resolver"])
        trace = AgentRuntime(lambda task, context: {task.agent_id: True, **passing_contract(task)}).run(plan)
        data = trace.to_dict()
        phases = {event["phase"] for event in data["events"]}
        self.assertIn("quality_gate", phases)
        self.assertIn("delivery_gate", phases)
        gate_events = [e for e in data["events"] if e["phase"] == "delivery_gate"]
        self.assertTrue(gate_events[0]["gate"]["evidence"])


if __name__ == "__main__":
    unittest.main()
