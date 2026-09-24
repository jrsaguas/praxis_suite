import unittest

from agent_archetypes import ARCHETYPES, get_archetype, infer_archetype


class TestAgentArchetypes(unittest.TestCase):
    def test_registry_contains_required_specialists(self):
        ids = {item.id for item in ARCHETYPES}
        self.assertTrue(
            {
                "code",
                "python_visualization",
                "canvas_html",
                "mathematical_proof",
                "research",
                "math_resolver",
            }.issubset(ids)
        )

    def test_archetypes_have_non_empty_contracts(self):
        for archetype in ARCHETYPES:
            self.assertTrue(archetype.mission)
            self.assertTrue(archetype.capabilities)
            self.assertTrue(archetype.tool_profile)
            self.assertTrue(archetype.input_artifacts)
            self.assertTrue(archetype.output_artifacts)
            self.assertTrue(archetype.quality_gates)
            self.assertTrue(archetype.forbidden_actions)

    def test_canvas_signal_selects_canvas_archetype(self):
        self.assertEqual(
            infer_archetype(tools=("canvas", "javascript")).id,
            "canvas_html",
        )

    def test_python_visualization_signal_selects_python_archetype(self):
        self.assertEqual(
            infer_archetype(tools=("python", "matplotlib")).id,
            "python_visualization",
        )

    def test_proof_signal_selects_proof_archetype(self):
        self.assertEqual(
            infer_archetype(requirements=("formal_proof",)).id,
            "mathematical_proof",
        )

    def test_research_signal_selects_research_archetype(self):
        self.assertEqual(
            infer_archetype(requirements=("source_traceability",)).id,
            "research",
        )

    def test_code_signal_selects_code_archetype(self):
        self.assertEqual(
            infer_archetype(requirements=("implementation",)).id,
            "code",
        )

    def test_unknown_signal_falls_back_to_math_resolver(self):
        self.assertEqual(infer_archetype(requirements=("symbolic",)).id, "math_resolver")

    def test_lookup_is_deterministic(self):
        self.assertEqual(get_archetype("code"), get_archetype("code"))
        with self.assertRaises(KeyError):
            get_archetype("does-not-exist")


if __name__ == "__main__":
    unittest.main()
