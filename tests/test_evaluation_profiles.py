import unittest

from evaluation_profiles import compare_profiles, profile_from_dict


class EvaluationProfilesTests(unittest.TestCase):
    def test_weighted_comparison_exposes_dimension_changes(self):
        baseline = profile_from_dict({
            "mathematics": 90, "depth": 80, "visualization": 70
        })
        candidate = profile_from_dict({
            "mathematics": 92, "depth": 88, "visualization": 65
        })
        result = compare_profiles(baseline, candidate)
        self.assertEqual(result.improved_dimensions, ("mathematics", "depth"))
        self.assertEqual(result.regressed_dimensions, ("visualization",))
        self.assertGreater(result.improvement, 0)

    def test_user_weights_change_global_score(self):
        baseline = profile_from_dict({"mathematics": 100, "visualization": 0})
        candidate = profile_from_dict({"mathematics": 90, "visualization": 80})
        math_heavy = compare_profiles(
            baseline, candidate, weights={"mathematics": 10, "visualization": 1}
        )
        visual_heavy = compare_profiles(
            baseline, candidate, weights={"mathematics": 1, "visualization": 10}
        )
        self.assertLess(math_heavy.improvement, visual_heavy.improvement)


if __name__ == "__main__":
    unittest.main()
