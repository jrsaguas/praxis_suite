import tempfile
import unittest

from evaluator_orchestrator import (
    AgentResult, Evaluation, LearningRecord
)
from learning_bridge import persist_learning_record, build_experience_context, normalize_planning_context


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


    def test_build_experience_context_uses_only_accepted_records(self):
        from experience_store import append_record, record_user_feedback
        with tempfile.TemporaryDirectory() as tmp:
            append_record(tmp, "chat-1", task_fingerprint="candidate",
                evaluation={"consistent": True, "score": .99}, strategy_id="candidate",
                metadata={"evaluation_profile": {"depth": 100}})
            accepted = append_record(tmp, "chat-1", task_fingerprint="accepted",
                evaluation={"consistent": True, "score": .80}, strategy_id="accepted",
                metadata={"evaluation_profile": {"depth": 90}})
            record_user_feedback(tmp, "chat-1", accepted["record_id"], decision="accept", rating=90)
            context = build_experience_context(tmp, "chat-1", evaluation_profile={"depth": 90})
            self.assertEqual([r["strategy_id"] for r in context["references"]], ["accepted"])

    def test_rejected_feedback_is_excluded_from_future_context(self):
        from experience_store import append_record, record_user_feedback

        with tempfile.TemporaryDirectory() as tmp:
            rejected = append_record(
                tmp, "chat-1",
                task_fingerprint="rejected",
                evaluation={"consistent": True, "score": 0.99},
                strategy_id="rejected",
                metadata={"evaluation_profile": {"depth": 90}},
            )
            record_user_feedback(
                tmp, "chat-1", rejected["record_id"],
                decision="reject", rating=0,
            )
            context = build_experience_context(
                tmp, "chat-1", evaluation_profile={"depth": 90}
            )
            self.assertEqual(context["references"], [])

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


    def test_planning_context_preserves_adaptive_selection_and_depth(self):
        planning = {
            "adaptive_selection": {
                "active": True,
                "reason": "missing_capability",
                "selected_reusable_agents": ["surface_specialist"],
                "generated_candidates": ["adaptive_surface_a1b2c3"],
            },
            "mathematical_depth": {
                "profile": {"proof": 92, "research": 88},
                "proof_expectation": 92,
            },
            "execution_agents": ["foundation_analyst", "surface_specialist", "final_auditor"],
        }
        normalized = normalize_planning_context(planning)
        self.assertEqual(normalized["selected_reusable_agents"], ["surface_specialist"])
        self.assertEqual(normalized["generated_candidates"], ["adaptive_surface_a1b2c3"])
        self.assertEqual(normalized["mathematical_depth"]["proof_expectation"], 92)
        self.assertEqual(normalized["execution_agents"][-1], "final_auditor")

    def test_runtime_sink_persists_planning_context_without_promoting_candidate(self):
        from learning_bridge import make_runtime_experience_sink
        with tempfile.TemporaryDirectory() as tmp:
            sink = make_runtime_experience_sink(tmp, "chat-1")
            class Task:
                task_id = "task:experience"
                agent_id = "experience_evaluator"
            saved = sink(
                Task(),
                {"planning_metadata": {
                    "adaptive_selection": {
                        "active": True,
                        "selected_reusable_agents": ["surface_specialist"],
                        "generated_candidates": ["candidate-x"],
                    },
                    "mathematical_depth": {"profile": {"proof": 95}},
                    "execution_agents": ["surface_specialist", "experience_evaluator"],
                }},
                {"evaluation": {"consistent": True, "score": 0.9},
                 "experience_record": {"candidate_type": "strategy_outcome"}},
            )
            self.assertEqual(saved["reuse_status"], "candidate")
            context = saved["metadata"]["planning_context"]
            self.assertTrue(context["adaptive_active"])
            self.assertEqual(context["selected_reusable_agents"], ["surface_specialist"])
            self.assertEqual(context["generated_candidates"], ["candidate-x"])
            self.assertEqual(context["mathematical_depth"]["profile"]["proof"], 95)

if __name__ == "__main__":
    unittest.main()
