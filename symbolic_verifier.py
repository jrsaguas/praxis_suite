"""Independent symbolic verification adapter.

Praxis already has a CAS engine in cas_verifier.py. This module exposes a
small structured contract for specialist artifacts while delegating the actual
symbolic computation to that existing SymPy verifier. The model's passed field
is never trusted.
"""
from __future__ import annotations

from typing import Any, Mapping

from cas_verifier import verify_mathematical_derivation


def verify_symbolic_certificate(certificate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(certificate, Mapping):
        return {"passed": False, "method": "cas_verifier", "reason": "certificate_missing"}

    claim_type = str(certificate.get("claim_type") or "").lower()
    if claim_type not in {"identity", "equality"}:
        return {
            "passed": False,
            "method": "cas_verifier",
            "reason": "unsupported_claim_type",
            "supported_claim_types": ["identity", "equality"],
        }

    lhs = certificate.get("lhs")
    rhs = certificate.get("rhs")
    if not isinstance(lhs, str) or not isinstance(rhs, str) or not lhs.strip() or not rhs.strip():
        return {"passed": False, "method": "cas_verifier", "reason": "lhs_or_rhs_missing"}

    variables = certificate.get("variables")
    if variables is not None and not isinstance(variables, (list, tuple)):
        return {"passed": False, "method": "cas_verifier", "reason": "invalid_variables"}

    cas = verify_mathematical_derivation(final_result=f"{lhs} = {rhs}")
    passed = cas.get("estado_global") == "VALIDADO_CAS"
    return {
        "passed": passed,
        "method": "existing_cas_verifier",
        "verified_by": "independent_cas",
        "authoritative": True,
        "claim_type": claim_type,
        "cas_certificate": cas,
    }
