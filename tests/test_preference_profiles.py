import unittest
from investigation_model import EvaluationProfile
from preference_profiles import PreferenceProfile, compare_preference_fit


class PreferenceProfilesTests(unittest.TestCase):
    def test_percentages_are_bounded_and_score_is_weighted(self):
        p = PreferenceProfile.from_percentages({
            "mathematics": 100, "visualization": 20
        })
        e = EvaluationProfile(mathematics=90, visualization=80)
        self.assertAlmostEqual(p.score(e), 88.33, places=2)

    def test_preference_fit_exposes_relevant_regressions(self):
        p = PreferenceProfile.from_percentages({
            "mathematics": 100, "visualization": 100
        })
        result = compare_preference_fit(
            EvaluationProfile(mathematics=90, visualization=80),
            EvaluationProfile(mathematics=95, visualization=70),
            p,
        )
        self.assertEqual(result["preferred_dimensions"], ["mathematics"])
        self.assertEqual(result["regressed_dimensions"], ["visualization"])


if __name__ == "__main__":
    unittest.main()
