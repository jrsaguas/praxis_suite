import tempfile
import unittest

from experience_store import append_record, list_records, summarize_strategies


class ExperienceStoreTests(unittest.TestCase):
    def test_append_and_summarize_without_mutating_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_record(
                tmp, "chat-1",
                task_fingerprint="abc",
                evaluation={"consistent": True, "score": 0.9},
                strategy_id="baseline-v1",
            )
            append_record(
                tmp, "chat-1",
                task_fingerprint="def",
                evaluation={"consistent": False, "score": 0.4},
                strategy_id="baseline-v1",
            )
            records = list_records(tmp, "chat-1")
            summary = summarize_strategies(records)
            self.assertEqual(len(records), 2)
            self.assertEqual(summary["baseline-v1"]["count"], 2.0)
            self.assertEqual(summary["baseline-v1"]["mean_score"], 0.65)
            self.assertEqual(summary["baseline-v1"]["accept_rate"], 0.5)

    def test_limit_returns_latest_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                append_record(
                    tmp, "chat-1",
                    task_fingerprint=str(i),
                    evaluation={"consistent": True, "score": 1.0},
                    strategy_id="s",
                )
            self.assertEqual(len(list_records(tmp, "chat-1", limit=2)), 2)


    def test_select_references_respects_target_profile(self):
        from experience_store import select_references
        records = [
            {"strategy_id": "depth", "evaluation": {"score": 0.9, "consistent": True},
             "metadata": {"evaluation_profile": {"depth": 100, "mathematics": 90}}},
            {"strategy_id": "visual", "evaluation": {"score": 0.88, "consistent": True},
             "metadata": {"evaluation_profile": {"visualization": 100, "interactivity": 90}}},
        ]
        refs = select_references(records, target_profile={"depth": 100, "mathematics": 90}, limit=2)
        self.assertEqual(refs[0]["strategy_id"], "depth")


if __name__ == "__main__":
    unittest.main()
