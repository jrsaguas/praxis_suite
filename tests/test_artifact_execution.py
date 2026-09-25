import unittest
from artifact_execution import verify_python_artifact, verify_numeric_claims

class ExecutionEvidenceTests(unittest.TestCase):
    def test_restricted_python_execution_produces_authoritative_evidence(self):
        result = verify_python_artifact("x = 2 + 2\nprint(x)")
        self.assertTrue(result["passed"])
        self.assertEqual(result["method"], "restricted_python_execution")

    def test_unsafe_python_is_rejected(self):
        result = verify_python_artifact("import os\nprint(1)")
        self.assertFalse(result["passed"])

    def test_numeric_claim_is_recomputed(self):
        result = verify_numeric_claims({"expected": 4.0, "actual": 4.0, "tolerance": 1e-9})
        self.assertTrue(result["passed"])

    def test_numeric_claim_mismatch_fails(self):
        result = verify_numeric_claims({"expected": 4.0, "actual": 4.1, "tolerance": 1e-9})
        self.assertFalse(result["passed"])

if __name__ == "__main__":
    unittest.main()
