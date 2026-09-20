import unittest
from evaluator_orchestrator import EvaluationOrchestrator

class FullPipelineTests(unittest.TestCase):
    def test_answer_review_cas_and_rag_flow(self):
        def answer(*args): return "x^2 + 2*x + 1 = (x+1)^2"
        def review(*args): return {"errors": [], "strengths": ["review-ok"], "reasons": []}
        def cas(*args): return {"estado_global": "VALIDADO_CAS", "registros": []}
        def rag(*args): return []
        record = EvaluationOrchestrator(answer, review, cas_verifier=cas, rag_provider=rag).run("identity")
        self.assertTrue(record.evaluation.consistent)
        self.assertEqual(record.strategy_id, "baseline-v1")
        self.assertEqual(len(record.agent_results), 4)

if __name__ == "__main__":
    unittest.main()