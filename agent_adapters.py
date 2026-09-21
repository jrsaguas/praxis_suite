"""Adapters that connect graph roles to existing Praxis capabilities.

Adapters are intentionally small: orchestration decides *which* role runs;
this module decides *how* an existing capability is invoked.
"""
from __future__ import annotations
import os
from typing import Any, Mapping
import canvas_synthesizer
import convert
from model_gateway import build_agent_prompt, invoke_model


def execute_canvas(task, context: Mapping[str, Any]) -> Mapping[str, Any]:
    prompt = str(context.get("task") or "")
    title = str(context.get("title") or "Simulador matemático")
    html = canvas_synthesizer.synthesize_canvas_simulator(
        title=title,
        prompt_text=prompt,
        governing_eqs=str(context.get("governing_equations") or ""),
        state_vars=context.get("state_vars"),
        params=context.get("params"),
    )
    return {"canvas_html": html, "artifact_type": "canvas"}


def execute_document(task, context: Mapping[str, Any]) -> Mapping[str, Any]:
    markdown = str(context.get("markdown") or context.get("integrated_report") or "")
    if not markdown.strip():
        raise ValueError("document_engineer requiere Markdown canónico o informe integrado")
    return {"markdown": markdown, "artifact_type": "markdown"}


def export_docx(markdown_path: str, output_path: str) -> Mapping[str, Any]:
    ok, message = convert.convert_with_pandoc(markdown_path, output_path)
    if not ok:
        ok, message = convert.convert_with_python_docx(markdown_path, output_path)
    if not ok or not os.path.exists(output_path):
        raise RuntimeError(message or "No fue posible generar DOCX")
    return {"docx_path": output_path, "conversion": "pandoc_or_fallback"}


def execute_model_agent(task, context: Mapping[str, Any]) -> Mapping[str, Any]:
    from model_registry import ModelRegistry
    registry = ModelRegistry()
    if not task.model_id:
        raise ValueError(f"No hay modelo asignado para {task.agent_id}")
    spec = registry.get(task.model_id)
    prompt = build_agent_prompt(task, context)
    result = invoke_model(spec, prompt, context)
    return {
        "agent_response": result["content"],
        "model_provider": result["provider"],
        "model_used": result["model"],
        "agent_id": task.agent_id,
    }

def execute_experience_evaluator(task, context):
    from final_auditor import audit_product
    from evaluator_orchestrator import Evaluation, LearningRecord
    audit = context.get("final_audit") or audit_product(context).to_dict()
    status = str(audit.get("status", "needs_review"))
    score = 1.0 if status == "pass" else 0.0
    return {
        "evaluation": {
            "consistent": status == "pass",
            "score": score,
            "recommendation": "ACCEPT" if status == "pass" else "REVIEW",
            "audit_status": status,
            "findings": audit.get("findings", []),
        },
        "experience_record": {
            "source": "final_auditor",
            "promotion_eligible": status == "pass",
            "requires_human_or_gate_review": status != "pass",
        },
    }

MODEL_AGENTS = {
    "intent_router", "architect", "foundation_analyst", "mathematical_resolver",
    "proof_specialist", "representation_designer", "python_visualizer",
    "code_reviewer", "research_specialist", "integrator", "epistemic_reviewer",
    "final_auditor", "experience_evaluator",
}

ADAPTERS = {
    "canvas_engineer": execute_canvas,
    "document_engineer": execute_document,
    **{agent_id: execute_model_agent for agent_id in MODEL_AGENTS},
    "experience_evaluator": execute_experience_evaluator,
}


def adapter_for(agent_id: str):
    return ADAPTERS.get(agent_id)
