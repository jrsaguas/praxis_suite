"""Deterministic evidence verifiers for specialist delivery contracts.

These checks inspect produced artifacts instead of trusting an agent's prose
claim that a gate passed. They are intentionally conservative: unsupported
verification is reported as missing evidence and therefore cannot authorize a
handoff.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Mapping

from agent_delivery import GateEvaluation
from agent_graph import AgentTask
from artifact_execution import verify_numeric_claims
from symbolic_verifier import verify_symbolic_certificate
from research_evidence import verify_research_evidence


def verify_output(task: AgentTask, output: Mapping[str, Any], phase: str) -> GateEvaluation:
    required = tuple(task.quality_gates if phase == "quality" else task.delivery_gates)
    if not required:
        return GateEvaluation(phase, task.agent_id, True, ())

    evidence = {}
    failed = []
    missing = []

    for gate in required:
        ok, detail = _verify_gate(task.agent_id, gate, output)
        evidence[gate] = detail
        if ok is None:
            missing.append(gate)
        elif not ok:
            failed.append(gate)

    return GateEvaluation(
        phase, task.agent_id, not failed and not missing, required,
        tuple(failed), tuple(missing), evidence,
    )


def _verify_gate(agent_id: str, gate: str, output: Mapping[str, Any]):
    # An explicit external gate callback may provide authoritative evidence.
    supplied = output.get("verified_gates")
    if isinstance(supplied, Mapping) and gate in supplied:
        value = supplied[gate]
        if isinstance(value, Mapping) and value.get("passed") is True:
            return True, dict(value)
        if isinstance(value, Mapping):
            return False, dict(value)

    if agent_id == "code_reviewer":
        return _code_gate(gate, output)
    if agent_id == "python_visualizer":
        return _python_visualization_gate(gate, output)
    if agent_id == "canvas_engineer":
        return _canvas_gate(gate, output)
    if agent_id == "mathematical_resolver":
        return _math_gate(gate, output)
    if agent_id == "research_specialist":
        return _research_gate(gate, output)
    return None, {"reason": f"no deterministic verifier registered for {agent_id}:{gate}"}


def _code_gate(gate, output):
    source = _first(output, "code", "source_code", "python_code")
    if gate in ("syntax", "code_syntax"):
        if not isinstance(source, str) or not source.strip():
            return None, {"reason": "source code artifact unavailable"}
        try:
            ast.parse(source)
            return True, {"method": "ast.parse", "verified": True}
        except SyntaxError as exc:
            return False, {"method": "ast.parse", "verified": False, "error": str(exc)}
    if gate in ("tests", "regression"):
        tests = output.get("test_results")
        if isinstance(tests, Mapping):
            return bool(tests.get("passed") is True), dict(tests)
        return None, {"reason": "test_results artifact unavailable"}
    if gate == "requirement_alignment":
        return _explicit_bool(output, "requirement_alignment")
    if gate == "reproducibility":
        return _explicit_bool(output, "reproducibility")
    return None, {"reason": "unsupported code gate"}


def _python_visualization_gate(gate, output):
    if gate == "code_syntax":
        return _code_gate("syntax", output)
    if gate == "numerical_sanity":
        authoritative = output.get("execution_numeric_checks")
        if isinstance(authoritative, Mapping):
            return bool(authoritative.get("passed") is True), dict(authoritative)
        checks = output.get("numeric_checks")
        if isinstance(checks, Mapping) and "expected" in checks and "actual" in checks:
            recomputed = verify_numeric_claims(checks)
            return bool(recomputed.get("passed") is True), recomputed
        return None, {"reason": "authoritative numeric evidence unavailable"}
    if gate == "reproducibility":
        return _explicit_bool(output, "reproducibility")
    if gate == "math_code_alignment":
        return _explicit_bool(output, "math_code_alignment")
    return None, {"reason": "unsupported visualization gate"}


def _canvas_gate(gate, output):
    html = _first(output, "canvas_html", "html")
    if gate == "html_safety":
        if not isinstance(html, str) or not html.strip():
            return None, {"reason": "HTML artifact unavailable"}
        dangerous = re.findall(r"<\s*(?:script[^>]*src|iframe|object|embed)\b", html, re.I)
        return (not dangerous), {"method": "static_html_scan", "external_or_embedded_tags": len(dangerous)}
    if gate == "interaction_integrity":
        if not isinstance(html, str) or not html.strip():
            return None, {"reason": "HTML artifact unavailable"}
        has_canvas = bool(re.search(r"<\s*canvas\b", html, re.I))
        has_js = bool(re.search(r"<\s*script\b", html, re.I))
        return has_canvas and has_js, {"method": "static_html_scan", "canvas": has_canvas, "script": has_js}
    if gate == "math_rendering":
        if not isinstance(html, str) or not html.strip():
            return None, {"reason": "HTML artifact unavailable"}
        mathjax = "MathJax" in html or "mathjax" in html
        latex = bool(re.search(r"\\\(|\\\[|\$\$", html))
        return mathjax or latex, {"method": "static_math_markup_scan", "math_markup": latex, "mathjax": mathjax}
    if gate == "accessibility":
        if not isinstance(html, str) or not html.strip():
            return None, {"reason": "HTML artifact unavailable"}
        return bool(re.search(r"<\s*(?:main|section|h1|label|title)\b", html, re.I)), {"method": "static_semantic_html_scan"}
    return None, {"reason": "unsupported canvas gate"}


def _math_gate(gate, output):
    if gate == "symbolic_consistency":
        certificate = output.get("verification_certificate")
        if isinstance(certificate, Mapping):
            result = verify_symbolic_certificate(certificate)
            return bool(result.get("passed") is True), result
        return None, {"reason": "verification_certificate unavailable"}
    if gate == "step_completeness":
        derivation = output.get("derivation")
        if isinstance(derivation, str):
            return bool(derivation.strip()), {"method": "derivation_presence", "characters": len(derivation)}
        return None, {"reason": "derivation artifact unavailable"}
    if gate == "assumption_traceability":
        assumptions = output.get("assumptions")
        if isinstance(assumptions, (list, tuple, str)):
            return bool(assumptions), {"method": "assumption_artifact_presence"}
        return None, {"reason": "assumptions artifact unavailable"}
    return None, {"reason": "unsupported mathematical gate"}


def _research_gate(gate, output):
    retrieved = output.get("retrieved_sources")
    if gate == "source_traceability":
        result = verify_research_evidence(retrieved)
        return bool(result.get("passed") is True), result

    if not isinstance(retrieved, list) or not retrieved:
        return None, {"reason": "retrieved_sources unavailable"}

    source_keys = set()
    for item in retrieved:
        if isinstance(item, Mapping):
            for key in ("title", "pdf_url"):
                if item.get(key):
                    source_keys.add(str(item[key]).strip())

    if gate == "claim_support":
        source_map = output.get("source_map")
        citations = output.get("citations")
        if not isinstance(source_map, (list, tuple)) or not isinstance(citations, (list, tuple)):
            return None, {"reason": "source_map_or_citations unavailable"}
        references = []
        for item in list(source_map) + list(citations):
            if isinstance(item, Mapping):
                references.extend(str(item.get(k)).strip() for k in ("title", "source", "source_title", "url", "pdf_url") if item.get(k))
            elif isinstance(item, str):
                references.append(item.strip())
        grounded = [ref for ref in references if ref in source_keys]
        return bool(grounded), {
            "method": "retrieved_source_reference_match",
            "grounded_references": len(grounded),
            "reference_count": len(references),
        }

    if gate == "date_relevance":
        import datetime as _dt
        years = []
        for item in retrieved:
            if not isinstance(item, Mapping):
                continue
            try:
                years.append(int(str(item.get("year", ""))[:4]))
            except (TypeError, ValueError):
                return False, {"method": "retrieved_source_date_check", "reason": "invalid_year"}
        current_year = _dt.datetime.now(_dt.timezone.utc).year
        passed = bool(years) and all(1900 <= year <= current_year for year in years)
        return passed, {
            "method": "retrieved_source_date_check",
            "years": years,
            "current_year": current_year,
        }

    return None, {"reason": "unsupported research gate"}


def _is_model_self_report(output: Mapping[str, Any]) -> bool:
    provenance = output.get("evidence_provenance")
    return isinstance(provenance, Mapping) and provenance.get("origin") == "model_self_report"

def _explicit_bool(output, key):
    value = output.get(key)
    if isinstance(value, Mapping):
        return (value.get("passed") is True), dict(value)
    if isinstance(value, bool):
        return value, {"passed": value, "source": key}
    return None, {"reason": f"{key} evidence unavailable"}


def _first(output, *keys):
    for key in keys:
        value = output.get(key)
        if value is not None:
            return value
    return None
