"""Independent symbolic verification for mathematical resolver artifacts.

This module deliberately verifies a narrow, declarative contract with SymPy.
It never trusts a model-provided passed flag. Unsupported claims return
passed=False with a conservative reason instead of guessing.
"""
from __future__ import annotations
from typing import Any, Mapping
import sympy as sp

_ALLOWED = {
    name: getattr(sp, name)
    for name in (
        "Abs", "E", "I", "Integer", "Rational", "pi", "sqrt",
        "sin", "cos", "tan", "exp", "log", "sinh", "cosh", "tanh",
    )
}

def _symbols(names: Any) -> dict[str, sp.Symbol]:
    if not isinstance(names, (list, tuple)) or not names:
        return {}
    result = {}
    for name in names:
        if not isinstance(name, str) or not name.isidentifier():
            return {}
        result[name] = sp.Symbol(name)
    return result

def _parse(expression: Any, locals_map: Mapping[str, Any]):
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression_missing")
    if len(expression) > 2000:
        raise ValueError("expression_too_long")
    return sp.sympify(expression, locals=dict(_ALLOWED, **dict(locals_map)), evaluate=True)

def verify_symbolic_certificate(certificate: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute a narrow symbolic claim and return authoritative evidence.

    Supported claim types:
      * identity: simplify(lhs - rhs) == 0
      * equality: same check as identity, explicitly named as equality

    The model may supply expressions and variables, but the result is always
    recomputed by SymPy. Model passed fields are ignored.
    """
    if not isinstance(certificate, Mapping):
        return {"passed": False, "method": "sympy", "reason": "certificate_missing"}
    claim_type = str(certificate.get("claim_type") or "").lower()
    if claim_type not in {"identity", "equality"}:
        return {"passed": False, "method": "sympy", "reason": "unsupported_claim_type",
                "supported_claim_types": ["identity", "equality"]}
    variables = _symbols(certificate.get("variables"))
    if certificate.get("variables") and not variables:
        return {"passed": False, "method": "sympy", "reason": "invalid_variables"}
    try:
        lhs = _parse(certificate.get("lhs"), variables)
        rhs = _parse(certificate.get("rhs"), variables)
        residual = sp.simplify(lhs - rhs)
        passed = bool(residual == 0)
        return {
            "passed": passed,
            "method": "sympy_simplify",
            "claim_type": claim_type,
            "lhs": sp.srepr(lhs),
            "rhs": sp.srepr(rhs),
            "residual": sp.srepr(residual),
            "verified_by": "independent_cas",
            "authoritative": True,
        }
    except (TypeError, ValueError, SyntaxError, sp.SympifyError) as exc:
        return {"passed": False, "method": "sympy_simplify",
                "verified_by": "independent_cas", "authoritative": True,
                "reason": str(exc)}
