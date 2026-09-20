import unittest
from contracts import PipelineResult, VerificationStatus


class ContractTests(unittest.TestCase):
    def test_verified_status_is_explicit(self):
        verified = VerificationStatus("VALIDADO_CAS", checks=1)
        unverified = VerificationStatus("NO_VALIDADO_CAS")
        self.assertTrue(verified.is_verified)
        self.assertFalse(unverified.is_verified)

    def test_pipeline_result_is_immutable(self):
        result = PipelineResult(ok=True, stage="cas", payload={})
        with self.assertRaises(Exception):
            result.ok = False


if __name__ == "__main__":
    unittest.main()
