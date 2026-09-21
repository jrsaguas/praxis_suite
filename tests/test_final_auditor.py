import unittest
from final_auditor import audit_product

class FinalAuditorTests(unittest.TestCase):
    def test_complete_product_has_structural_pass(self):
        report = audit_product({
            "prompt": "Demuestra y verifica la integral.",
            "markdown": "# Procedimiento

Se demuestra la ecuación \nabla f.

### Validación CAS
certificación",
            "artifact_manifest": {"artifacts": [{"type":"md","path":"x.md"}]},
            "runtime_trace": {"events":[{"sequence":1}]},
        })
        self.assertEqual(report.status, "pass")
        self.assertTrue(report.checks["procedures_present"])
        self.assertTrue(report.checks["mathematical_content_present"])

    def test_missing_product_is_flagged(self):
        report = audit_product({})
        self.assertEqual(report.status, "needs_review")
        categories = {f.category for f in report.findings}
        self.assertIn("completitud", categories)
        self.assertIn("verificación", categories)
