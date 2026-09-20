import unittest
from strategy_health import assess_degradation


class StrategyHealthTests(unittest.TestCase):
    def test_insufficient_history_does_not_trigger_retirement(self):
        rows = [{"strategy_id": "s", "evaluation": {"score": .2}} for _ in range(2)]
        self.assertFalse(assess_degradation(rows, strategy_id="s")["degraded"])

    def test_sustained_decline_is_detected(self):
        rows = [
            {"strategy_id": "s", "created_at": f"2026-09-{d:02d}", "evaluation": {"score": score}}
            for d, score in [(1,.92),(2,.90),(3,.88),(4,.60),(5,.58)]
        ]
        result = assess_degradation(rows, strategy_id="s", max_decline=.05)
        self.assertTrue(result["degraded"])
        self.assertEqual(result["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
