import unittest

from cas_verifier import verify_mathematical_derivation


class CASVerifierTests(unittest.TestCase):
    def test_exact_identity_is_validated(self):
        result = verify_mathematical_derivation(final_result="x^2 + 2*x + 1 = (x+1)^2")
        self.assertEqual(result["estado_global"], "VALIDADO_CAS")
        self.assertTrue(any(r["estado"] == "VALIDADO_SIMBOLICAMENTE" for r in result["registros"]))

    def test_false_identity_is_not_certified(self):
        result = verify_mathematical_derivation(final_result="x^2 = x")
        self.assertNotEqual(result["estado_global"], "VALIDADO_CAS")

    def test_unverifiable_text_is_not_certified(self):
        result = verify_mathematical_derivation(final_result="La respuesta parece correcta")
        self.assertEqual(result["estado_global"], "NO_VALIDADO_CAS")

    def test_matrix_is_verified(self):
        result = verify_mathematical_derivation(
            user_prompt=r"Sea A = \begin{pmatrix} 0 & 1 \\ -4 & 0 \end{pmatrix}"
        )
        self.assertEqual(result["estado_global"], "VALIDADO_CAS")


if __name__ == "__main__":
    unittest.main()
