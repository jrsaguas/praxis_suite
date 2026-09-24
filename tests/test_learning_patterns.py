import tempfile
import unittest

from experience_store import append_record, record_user_feedback, list_records
from learning_patterns import (
    propose_from_experience,
    persist_candidates,
    update_status,
    select_validated_patterns,
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
                __import__("learning_patterns")._load(
                    __import__("learning_patterns")._path(tmp, "chat-1")
                )["patterns"],
                task_family="geometry",
            )
            self.assertEqual(patterns[0]["pattern_id"], saved[0]["pattern_id"])

    def test_rejected_pattern_never_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._accepted(tmp)
            saved = persist_candidates(
                tmp, "chat-1", propose_from_experience(list_records(tmp, "chat-1"))
            )
            update_status(tmp, "chat-1", saved[0]["pattern_id"], status="rejected")
            self.assertEqual(
                select_validated_patterns(
                    __import__("learning_patterns")._load(
                        __import__("learning_patterns")._path(tmp, "chat-1")
                    )["patterns"]
                ),
                [],
            )


if __name__ == "__main__":
    unittest.main()
