"""Structured artifact contracts for model-based specialist agents."""
from __future__ import annotations
import json
import re
from typing import Any, Mapping

SPECIALIST_SCHEMAS = {
    "mathematical_resolver": {"solution": "string", "derivation": "string", "assumptions": "array|string", "verification_certificate": "object"},
    "proof_specialist": {"proofs": "array|string", "proof_obligations": "array|string", "assumptions": "array|string"},
    "python_visualizer": {"python_code": "string", "numeric_checks": "object", "reproducibility": "object|boolean", "math_code_alignment": "object|boolean"},
    "code_reviewer": {"code": "string", "test_results": "object", "requirement_alignment": "object|boolean", "reproducibility": "object|boolean"},
    "research_specialist": {"research_evidence": "array", "source_map": "array|object", "citations": "array"},
    "integrator": {"integrated_report": "string", "artifact_manifest": "array|object", "traceability_map": "array|object"},
}

def structured_output_contract(agent_id: str) -> dict[str, Any] | None:
    schema = SPECIALIST_SCHEMAS.get(agent_id)
    return dict(schema) if schema else None

def build_structured_instruction(agent_id: str) -> str:
    schema = structured_output_contract(agent_id)
    if not schema:
        return "Devuelve una respuesta normal. No inventes certificados ni evidencia externa que no puedas observar."
    instruction = ("RESPUESTA ESTRUCTURADA OBLIGATORIA. Devuelve UN ÚNICO objeto JSON válido, sin markdown ni texto antes/después. Usa estas claves: "
                   + json.dumps(schema, ensure_ascii=False, sort_keys=True)
                   + ". Si un campo no puede producirse de forma real, usa null o []. No inventes evidencia externa. La respuesta original se conservará por separado.")
    if agent_id == "mathematical_resolver":
        instruction += (" Para verification_certificate proporciona solo datos declarativos que CAS pueda recomputar: "
                         "claim_type (identity o equality), variables, lhs y rhs. No marques passed como evidencia.")
    if agent_id == "research_specialist":
        instruction += (" retrieved_sources es evidencia del recuperador y no debe sustituirse por URLs inventadas. "
                         "Usa esas fuentes para source_map/citations.")
    return instruction

def parse_structured_response(agent_id: str, content: str) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = structured_output_contract(agent_id)
    meta = {"structured": False, "parse_error": None, "evidence_origin": "none"}
    if not schema or not isinstance(content, str) or not content.strip():
        return {}, meta
    candidate = content.strip()
    if candidate.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.S | re.I)
        if not match:
            meta["parse_error"] = "invalid_json_fence"
            return {}, meta
        candidate = match.group(1).strip()
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        meta["parse_error"] = f"invalid_json:{exc.msg}"
        return {}, meta
    if not isinstance(data, dict):
        meta["parse_error"] = "root_must_be_object"
        return {}, meta
    normalized = {key: data[key] for key in schema if key in data}
    meta.update({"structured": True, "keys_present": sorted(normalized), "evidence_origin": "model_self_report"})
    return normalized, meta

def merge_model_artifacts(result: Mapping[str, Any], agent_id: str) -> dict[str, Any]:
    content = str(result.get("content") or "")
    artifacts, parse_meta = parse_structured_response(agent_id, content)
    output = dict(artifacts)
    output.update({"agent_response": content, "structured_output": parse_meta, "model_provider": result.get("provider"), "model_used": result.get("model"), "agent_id": agent_id})
    if artifacts:
        output["evidence_provenance"] = {"origin": "model_self_report", "authoritative": False, "fields": sorted(artifacts)}
    return output
