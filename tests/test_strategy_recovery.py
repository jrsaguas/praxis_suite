import unittest
from strategy_recovery import recovery_candidate


class StrategyRecoveryTests(unittest.TestCase):
    def test_selects_stable_historical_strategy(self):
        rows = []
        for score in (.82, .84, .80):
            rows.append({"strategy_id":"old", "metadata":{"task_family":"calculus"}, "evaluation":{"score":score}})
        result = recovery_candidate(rows, family="calculus", min_score=.75)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["candidate"]["strategy_id"], "old")

    def test_insufficient_history_blocks_recovery(self):
        rows = [{"strategy_id":"old","metadata":{"task_family":"calculus"},"evaluation":{"score":.99}}]
        self.assertFalse(recovery_candidate(rows, family="calculus")["eligible"])


if __name__ == "__main__":
    unittest.main()
