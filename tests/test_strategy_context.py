import unittest
from preference_profiles import PreferenceProfile
from strategy_context import build_strategy_context


class StrategyContextTests(unittest.TestCase):
    def test_context_resolves_family_and_promoted_strategies(self):
        prefs = PreferenceProfile.from_percentages({"mathematics": 100})
        strategies = [{
            "strategy_id": "s1", "status": "promoted",
            "task_families": ["linear_algebra"],
            "evaluation_profile": {"mathematics": 95},
        }]
        context = build_strategy_context(
            "resolver una matriz y determinar su determinante",
            strategies=strategies, preferences=prefs,
        )
        self.assertEqual(context["task_family"], "linear_algebra")
        self.assertEqual(context["strategy_ids"], ["s1"])
        self.assertEqual(context["preference_version"], 1)


if __name__ == "__main__":
    unittest.main()
