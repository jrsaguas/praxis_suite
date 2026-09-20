import unittest
from datetime import datetime, timezone, timedelta

from experience_trends import recency_weight, trend_for_feature


class ExperienceTrendsTests(unittest.TestCase):
    def test_recent_evidence_has_more_weight(self):
        now = datetime(2026, 9, 20, tzinfo=timezone.utc)
        recent = {"created_at": "2026-09-19T00:00:00+00:00"}
        old = {"created_at": "2026-07-01T00:00:00+00:00"}
        self.assertGreater(recency_weight(recent, now=now), recency_weight(old, now=now))

    def test_feature_can_be_detected_as_improving(self):
        now = datetime(2026, 9, 20, tzinfo=timezone.utc)
        records = [
            {"record_id": "old", "created_at": "2026-07-01T00:00:00+00:00",
             "metadata": {"features": ["canvas"]},
             "evaluation": {"score": 0.70, "consistent": True}},
            {"record_id": "recent", "created_at": "2026-09-19T00:00:00+00:00",
             "metadata": {"features": ["canvas"]},
             "evaluation": {"score": 0.95, "consistent": True}},
        ]
        result = trend_for_feature(records, "canvas", now=now)
        self.assertEqual(result["trend"], "improving")
        self.assertGreater(result["weighted_score"], 0.80)

    def test_missing_history_is_not_called_stable(self):
        result = trend_for_feature([], "canvas")
        self.assertEqual(result["trend"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
