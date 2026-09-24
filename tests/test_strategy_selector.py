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

    def test_validated_pattern_evidence_is_attached_without_bypassing_promotion(self):
        items = [
            {
                "strategy_id": "surface",
                "status": "promoted",
                "task_families": ["geometry"],
            },
            {
                "strategy_id": "candidate",
                "status": "candidate",
                "task_families": ["geometry"],
            },
        ]
        patterns = [
            {
                "pattern_id": "pat-valid",
                "status": "validated",
                "strategy_id": "surface",
                "task_family": "geometry",
                "selection": {"score": 0.97},
                "source_record_ids": ["exp-1"],
            },
            {
                "pattern_id": "pat-rejected",
                "status": "rejected",
                "strategy_id": "surface",
                "task_family": "geometry",
                "selection": {"score": 1.0},
                "source_record_ids": ["exp-2"],
            },
            {
                "pattern_id": "pat-candidate",
                "status": "candidate",
                "strategy_id": "candidate",
                "task_family": "geometry",
                "selection": {"score": 1.0},
                "source_record_ids": ["exp-3"],
            },
        ]
        result = select_strategies(
            items,
            task_family="geometry",
            validated_patterns=patterns,
        )
        self.assertEqual([x["strategy"]["strategy_id"] for x in result], ["surface"])
        evidence = result[0]["validated_pattern_evidence"]
        self.assertEqual(evidence["pattern_ids"], ["pat-valid"])
        self.assertEqual(evidence["source_record_ids"], ["exp-1"])
        self.assertEqual(evidence["support_count"], 1)

    def test_pattern_evidence_selection_is_deterministic(self):
        items = [
            {"strategy_id": "b", "status": "promoted", "task_families": ["geometry"]},
            {"strategy_id": "a", "status": "promoted", "task_families": ["geometry"]},
        ]
        patterns = [
            {"pattern_id": "p-b", "status": "validated", "strategy_id": "b", "task_family": "geometry", "selection": {"score": .8}},
            {"pattern_id": "p-a", "status": "validated", "strategy_id": "a", "task_family": "geometry", "selection": {"score": .8}},
        ]
        first = select_strategies(items, task_family="geometry", validated_patterns=patterns)
        second = select_strategies(list(reversed(items)), task_family="geometry", validated_patterns=list(reversed(patterns)))
        self.assertEqual(
            [x["strategy"]["strategy_id"] for x in first],
            [x["strategy"]["strategy_id"] for x in second],
        )


if __name__ == "__main__":
    unittest.main()
