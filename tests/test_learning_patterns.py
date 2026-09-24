import tempfile
import unittest

from experience_store import append_record, record_user_feedback, list_records
from learning_patterns import (
    propose_from_experience,
    persist_candidates,
    update_status,
    select_validated_patterns,
    list_patterns,
)


class LearningPatternTests(unittest.TestCase):
    def _accepted(self, tmp):
        saved = append_record(
            tmp, "chat-1",
            task_fingerprint="surface",
            evaluation={"consistent": True, "score": 0.92},
            strategy_id="surface-v3",
            metadata={
                "task_family": "geometry",
                "planning_context": {
                    "selected_reusable_agents": ["representation_designer"],
                    "execution_agents": ["foundation_analyst", "representation_designer"],
                    "mathematical_depth": {"profile": {"proof": 90, "visualization": 88}},
                },
            },
        )
        record_user_feedback(tmp, "chat-1", saved["record_id"], decision="accept", rating=95)
        return saved

    def test_only_accepted_experience_can_propose_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            accepted = self._accepted(tmp)
            rejected = append_record(
                tmp, "chat-1",
                task_fingerprint="bad",
                evaluation={"consistent": True, "score": 0.99},
                strategy_id="bad",
                metadata={"task_family": "geometry"},
            )
            record_user_feedback(tmp, "chat-1", rejected["record_id"], decision="reject", rating=0)
            proposals = propose_from_experience(list_records(tmp, "chat-1"), minimum_rating=90)
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0]["source_record_ids"], [accepted["record_id"]])
            self.assertEqual(proposals[0]["status"], "candidate")

    def test_candidate_is_not_reusable_until_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            accepted = self._accepted(tmp)
            proposals = propose_from_experience(list_records(tmp, "chat-1"))
            saved = persist_candidates(tmp, "chat-1", proposals)
            self.assertEqual(saved[0]["status"], "candidate")
            self.assertEqual(select_validated_patterns(saved), [])
            update_status(tmp, "chat-1", saved[0]["pattern_id"], status="validated")
            patterns = select_validated_patterns(
                list_patterns(tmp, "chat-1"), task_family="geometry"
            )
            self.assertEqual(patterns[0]["pattern_id"], saved[0]["pattern_id"])

    def test_selection_requires_validation_and_matches_family_and_depth(self):
        patterns = [
            {
                "pattern_id": "pat-geometry",
                "status": "validated",
                "task_family": "geometry",
                "signature": {"mathematical_depth": {"profile": {"proof": 90, "visualization": 90}}},
                "evidence": {"evaluation_score": 0.90, "user_rating": 95},
                "source_record_ids": ["exp-1"],
            },
            {
                "pattern_id": "pat-other",
                "status": "validated",
                "task_family": "algebra",
                "signature": {"mathematical_depth": {"profile": {"proof": 99, "visualization": 99}}},
                "evidence": {"evaluation_score": 1.0, "user_rating": 100},
                "source_record_ids": ["exp-2"],
            },
            {
                "pattern_id": "pat-candidate",
                "status": "candidate",
                "task_family": "geometry",
                "signature": {"mathematical_depth": {"profile": {"proof": 100, "visualization": 100}}},
                "evidence": {"evaluation_score": 1.0, "user_rating": 100},
                "source_record_ids": ["exp-3"],
            },
        ]
        selected = select_validated_patterns(
            patterns,
            task_family="geometry",
            depth_requirements={"profile": {"proof": 92, "visualization": 88}},
            limit=5,
        )
        self.assertEqual([p["pattern_id"] for p in selected], ["pat-geometry"])
        self.assertEqual(selected[0]["selection"]["policy"], "validated_family_depth_evidence_v1")

    def test_pattern_selection_is_deterministic(self):
        patterns = [
            {
                "pattern_id": "pat-b",
                "status": "validated",
                "task_family": "geometry",
                "signature": {"mathematical_depth": {"profile": {"proof": 90}}},
                "evidence": {"evaluation_score": 0.90, "user_rating": 90},
            },
            {
                "pattern_id": "pat-a",
                "status": "validated",
                "task_family": "geometry",
                "signature": {"mathematical_depth": {"profile": {"proof": 90}}},
                "evidence": {"evaluation_score": 0.90, "user_rating": 90},
            },
        ]
        first = select_validated_patterns(patterns, task_family="geometry", depth_requirements={"proof": 90})
        second = select_validated_patterns(list(reversed(patterns)), task_family="geometry", depth_requirements={"proof": 90})
        self.assertEqual([p["pattern_id"] for p in first], [p["pattern_id"] for p in second])

    def test_rejected_pattern_never_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._accepted(tmp)
            saved = persist_candidates(
                tmp, "chat-1", propose_from_experience(list_records(tmp, "chat-1"))
            )
            update_status(tmp, "chat-1", saved[0]["pattern_id"], status="rejected")
            self.assertEqual(
                select_validated_patterns(list_patterns(tmp, "chat-1")),
                [],
            )


if __name__ == "__main__":
    unittest.main()
