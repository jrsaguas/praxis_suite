import tempfile
import unittest

from evaluator_orchestrator import (
    AgentResult, Evaluation, LearningRecord
)
from learning_bridge import persist_learning_record


class LearningBridgeTests(unittest.TestCase):
    def test_evaluation_becomes_persistent_experience(self):
        record = LearningRecord(
            record_id="r1",
            created_at="2026-01-01T00:00:00+00:00",
            task_fingerprint="abc",
            agent_results=(AgentResult("answer", "ok"),),
            evaluation=Evaluation(
                consistent=True, score=0.95,
                strengths=("correcto",)
            ),
            proposal=None,
            strategy_id="baseline-v1",
        )
        with tempfile.TemporaryDirectory() as tmp:
            saved = persist_learning_record(
                tmp, "chat-1", record,
                investigation_id="chat-1/r1",
                version_id="v1",
                evaluation_profile={"mathematics": 96, "depth": 90},
            )
            self.assertEqual(saved["strategy_id"], "baseline-v1")
            self.assertEqual(
                saved["metadata"]["evaluation_profile"]["mathematics"], 96
            )


    def test_runtime_experience_is_persisted_as_candidate(self):
        from learning_bridge import persist_runtime_experience
        with tempfile.TemporaryDirectory() as tmp:
            saved = persist_runtime_experience(
                tmp, "chat-1",
                task_fingerprint="fp",
                evaluation={"consistent": True, "score": 0.8},
                experience_record={"candidate_type": "strategy_outcome"},
                investigation_id="chat-1/r1",
                version_id="v1",
                evaluation_profile={"depth": 90},
            )
            self.assertEqual(saved["reuse_status"], "candidate")
            self.assertEqual(saved["metadata"]["runtime_experience_source"], "experience_evaluator")
            self.assertEqual(saved["metadata"]["evaluation_profile"]["depth"], 90)


    def test_runtime_sink_builds_candidate_from_evaluator_output(self):
        from learning_bridge import make_runtime_experience_sink
        with tempfile.TemporaryDirectory() as tmp:
            sink = make_runtime_experience_sink(
                tmp, "chat-1", investigation_id="i1", version_id="v1",
                evaluation_profile={"depth": 80},
            )
            class Task:
                task_id = "task:experience"
                agent_id = "experience_evaluator"
            saved = sink(
                Task(),
                {"final_audit": {"status": "pass"}},
                {"evaluation": {"consistent": True, "score": 0.9},
                 "experience_record": {"candidate_type": "strategy_outcome"}},
            )
            self.assertEqual(saved["reuse_status"], "candidate")
            self.assertEqual(saved["metadata"]["runtime_agent_id"], "experience_evaluator")

    def test_runtime_sink_preserves_strategy_and_profile_metadata(self):
        from learning_bridge import make_runtime_experience_sink
        with tempfile.TemporaryDirectory() as tmp:
            sink = make_runtime_experience_sink(
                tmp, "chat-1",
                evaluation_profile={"depth": 95},
                strategy_context={"strategy_id": "surface-v3", "task_family": "geometry"},
            )
            class Task:
                task_id = "task:evaluate"
                agent_id = "experience_evaluator"
            saved = sink(Task(), {"final_audit": {"status": "pass"}}, {
                "evaluation": {"consistent": True, "score": .91},
                "experience_record": {"candidate_type": "strategy_outcome"},
            })
            self.assertEqual(saved["metadata"]["evaluation_profile"]["depth"], 95)
            self.assertEqual(saved["metadata"]["task_family"], "geometry")
            self.assertEqual(saved["strategy_id"], "surface-v3")



if __name__ == "__main__":
    unittest.main()
