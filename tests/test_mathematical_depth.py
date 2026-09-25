import unittest
from mathematical_depth import MathematicalDepthProfile, build_depth_context


class MathematicalDepthTests(unittest.TestCase):
    def test_doctorado_is_multidimensional(self):
        p = MathematicalDepthProfile.preset("doctorado")
        self.assertEqual(p.rigor, 95)
        self.assertEqual(p.proof, 92)
        self.assertEqual(p.research, 92)
        self.assertEqual(p.generalization, 92)
        self.assertEqual(len(build_depth_context(p)["requirements"]), 9)

    def test_custom_profile_bounds(self):
        with self.assertRaises(ValueError):
            MathematicalDepthProfile.preset("doctorado")
            MathematicalDepthProfile("custom", 101, 0, 0, 0, 0, 0, 0, 0)

    def test_manual_values_override_preset_dimensions(self):
        p = MathematicalDepthProfile.from_request(
            "doctorado",
            values={"rigor": 100, "proof": 55, "applications": 73},
            custom_rules=["usar contraejemplos"],
        )
        self.assertEqual(p.rigor, 100)
        self.assertEqual(p.proof, 55)
        self.assertEqual(p.applications, 73)
        self.assertEqual(p.research, 92)
        self.assertIn("usar contraejemplos", p.custom_rules)

    def test_custom_rules_survive_serialization(self):
        p = MathematicalDepthProfile.preset("licenciatura", ["explicar cada salto algebraico"])
        self.assertIn("explicar cada salto algebraico", p.to_dict()["custom_rules"])


if __name__ == "__main__":
    unittest.main()
