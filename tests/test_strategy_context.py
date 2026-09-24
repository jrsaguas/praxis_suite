import unittest
from strategy_context import build_strategy_context
from preference_profiles import PreferenceProfile


class StrategyContextTests(unittest.TestCase):
    def test_context_resolves_family_and_promoted_strategies(self):
        prefs = PreferenceProfile.from_percentages({"mathematics": 100})
        strategies = [{
            "strategy_id": "s1", "status": "promoted",
            "task_families": ["linear_algebra"],
            "evaluation_profile": {"mathematics": 95},
            "rules": ["demostrar cada transformación"],
        }]
        context = build_strategy_context(
            "resolver una matriz y determinar su determinante",
            strategies=strategies, preferences=prefs,
        )
        self.assertEqual(context["task_family"], "linear_algebra")
        self.assertEqual(context["strategy_ids"], ["s1"])
        self.assertEqual(context["operational_instructions"], ["demostrar cada transformación"])
        self.assertEqual(context["preference_version"], 1)

    def test_validated_pattern_evidence_flows_into_context(self):
        strategies = [{
            "strategy_id": "s1", "status": "promoted",
            "task_families": ["linear_algebra"],
            "evaluation_profile": {"mathematics": 95},
            "rules": ["demostrar cada transformación"],
        }]
        patterns = [{
            "pattern_id": "pat-s1",
            "status": "validated",
            "strategy_id": "s1",
            "task_family": "linear_algebra",
            "selection": {"score": .93},
            "source_record_ids": ["exp-1"],
        }]
        context = build_strategy_context(
            "resolver una matriz y determinar su determinante",
            strategies=strategies,
            validated_patterns=patterns,
        )
        self.assertEqual(context["strategy_context_version"], 3)
        self.assertEqual(context["validated_pattern_ids"], ["pat-s1"])
        self.assertEqual(
            context["strategies"][0]["validated_pattern_evidence"]["pattern_ids"],
            ["pat-s1"],
        )


if __name__ == "__main__":
    unittest.main()
