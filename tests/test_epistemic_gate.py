import unittest
from epistemic_gate import can_consolidate, make_provenance


class EpistemicGateTests(unittest.TestCase):
    def test_pending_cannot_consolidate(self):
        self.assertFalse(can_consolidate(make_provenance("inv-1")))

    def test_cas_verified_can_consolidate(self):
        self.assertTrue(can_consolidate(make_provenance("inv-1", "VALIDADO_CAS", ["identity-check"])))

    def test_unknown_status_cannot_consolidate(self):
        self.assertFalse(can_consolidate(make_provenance("inv-1", "LLM_DICE_QUE_ES_CORRECTO")))


if __name__ == "__main__":
    unittest.main()
