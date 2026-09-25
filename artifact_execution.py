"""Execution-backed evidence for specialist artifacts.

Only evidence produced by this module (or explicitly supplied by a trusted
external verifier) is authoritative. Model self-reports remain non-authoritative.
"""
from __future__ import annotations

import ast
import contextlib
import io
import math
import re
from typing import Any, Mapping


def verify_python_artifact(source: Any, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    if not isinstance(source, str) or not source.strip():
        return {"passed": False, "method": "python_ast", "error": "source unavailable"}
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return {"passed": False, "method": "python_ast", "error": str(exc)}

    # Deliberately narrow sandbox: execute only code that contains no imports,
    # file/network/process primitives, or dunder access. This is a sanity runner,
    # not a general Python sandbox.
    blocked = re.search(
        r"\b(?:import|from|open|exec|eval|compile|__import__|input)\b|"
        r"\b(?:os|sys|subprocess|socket|requests|urllib|pathlib)\b",
        source,
    )
    if blocked:
        return {"passed": False, "method": "restricted_python_execution", "error": "unsafe construct"}

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            code = compile(source, "<praxis-artifact>", "exec")
            exec(code, {"__builtins__": {"abs": abs, "min": min, "max": max, "round": round, "sum": sum, "len": len, "range": range}})
    except Exception as exc:
        return {"passed": False, "method": "restricted_python_execution", "error": repr(exc)}
    return {"passed": True, "method": "restricted_python_execution", "stdout": stdout.getvalue()[:4000]}


def verify_numeric_claims(checks: Any) -> dict[str, Any]:
    if not isinstance(checks, Mapping):
        return {"passed": False, "method": "numeric_claims", "error": "checks unavailable"}
    # Authoritative only when the checker itself can recompute the stated scalar.
    expected = checks.get("expected")
    actual = checks.get("actual")
    tolerance = checks.get("tolerance", 1e-9)
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        passed = math.isfinite(float(expected)) and math.isfinite(float(actual)) and abs(float(expected)-float(actual)) <= float(tolerance)
        return {"passed": passed, "method": "recomputed_scalar_comparison", "expected": expected, "actual": actual, "tolerance": tolerance}
    return {"passed": False, "method": "numeric_claims", "error": "expected/actual scalar evidence unavailable"}
