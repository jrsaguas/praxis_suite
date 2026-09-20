import unittest
from agent_graph import AgentGraphPlanner
from agent_runtime import AgentRuntime


class AgentRuntimeTests(unittest.TestCase):
    def test_runtime_passes_artifacts_between_agents(self):
        plan = AgentGraphPlanner().plan(required_artifacts=["canvas"])
        seen = []

        def execute(task, context):
            seen.append((task.agent_id, sorted(context)))
            return {task.agent_id: True}

        trace = AgentRuntime(execute).run(plan)
        self.assertEqual(trace.status, "completed")
        self.assertIn("canvas_engineer", trace.completed)
        self.assertTrue(any(agent == "canvas_engineer" and "representation_designer" in keys for agent, keys in seen))

    def test_failed_gate_retries_only_that_task_and_blocks_descendants(self):
        plan = AgentGraphPlanner().plan(required_artifacts=["canvas"])
        attempts = {}
        def execute(task, context):
            attempts[task.task_id] = attempts.get(task.task_id, 0) + 1
            return {task.agent_id: True}
        def gate(task, output):
            if task.agent_id == "representation_designer" and attempts[task.task_id] == 1:
                return {"passed": False, "reason": "representation mismatch"}
            return {"passed": True}
        trace = AgentRuntime(execute, gate, max_retries=1).run(plan)
        self.assertEqual(trace.status, "completed")
        self.assertEqual(attempts["task:representation_designer"], 2)
        self.assertIn("task:canvas_engineer", trace.blocked)
        self.assertNotIn("task:canvas_engineer", trace.completed)


if __name__ == "__main__":
    unittest.main()
