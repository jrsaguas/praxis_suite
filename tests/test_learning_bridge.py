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


if __name__ == "__main__":
    unittest.main()
