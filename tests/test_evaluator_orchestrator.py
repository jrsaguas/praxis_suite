import unittest
from evaluator_orchestrator import (
    AgentResult, EvaluationOrchestrator, Evidence
)


class EvaluatorOrchestratorTests(unittest.TestCase):
    def test_retries_after_inconsistent_review(self):
        calls = {"answer": 0}
        def answer(task, context, strategy, history):
            calls["answer"] += 1
            return {"attempt": calls["answer"]}
        def review(task, output, context, strategy):
            if output["attempt"] == 1:
                return {"errors": ["error reproducible"], "strengths": [], "reasons": ["review"]}
            return {"errors": [], "strengths": ["fixed"], "reasons": []}
        record = EvaluationOrchestrator(answer, review, max_retries=1).run("integral")
        self.assertTrue(record.evaluation.consistent)
        self.assertEqual(calls["answer"], 2)

    def test_persistent_failure_creates_improvement_proposal(self):
        def answer(*args):
            return {"bad": True}
        def review(*args):
            return {"errors": ["bad output"], "strengths": [], "reasons": []}
        record = EvaluationOrchestrator(answer, review, max_retries=1).run("task")
        self.assertFalse(record.evaluation.consistent)
        self.assertIsNotNone(record.proposal)
        self.assertEqual(record.evaluation.recommendation, "RETRY")


if __name__ == "__main__":
    unittest.main()
