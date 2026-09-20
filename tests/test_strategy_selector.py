import unittest
from preference_profiles import PreferenceProfile
from strategy_selector import select_strategies


class StrategySelectorTests(unittest.TestCase):
    def test_candidate_is_not_selected_by_default(self):
        items = [
            {"strategy_id": "c", "status": "candidate", "task_families": ["calculus"]},
        ]
        self.assertEqual(select_strategies(items), [])

    def test_selection_combines_family_preference_and_trend(self):
        prefs = PreferenceProfile.from_percentages({"mathematics": 100, "visualization": 100})
        items = [
            {
                "strategy_id": "surface",
                "status": "promoted",
                "task_families": ["surface_visualization"],
                "features": ["canvas"],
                "evaluation_profile": {"mathematics": 90, "visualization": 95},
            },
            {
                "strategy_id": "generic",
                "status": "promoted",
                "task_families": ["calculus"],
                "features": ["canvas"],
                "evaluation_profile": {"mathematics": 70, "visualization": 70},
            },
        ]
        result = select_strategies(
            items,
            task_family="surface_visualization",
            preferences=prefs,
            trends=[{"feature": "canvas", "trend": "improving"}],
        )
        self.assertEqual(result[0]["strategy"]["strategy_id"], "surface")


if __name__ == "__main__":
    unittest.main()
