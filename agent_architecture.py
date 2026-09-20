"""Declarative specialist-agent architecture for Praxis.

The registry defines responsibilities, inputs/outputs, dependencies and quality
gates. It is intentionally separate from LLM provider code: agents are roles,
not models. The runtime may assign Gemini, Ollama or another model to a role.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class AgentSpec:
    id: str
    mission: str
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    depends_on: Tuple[str, ...] = ()
    quality_gates: Tuple[str, ...] = ()
    tool_profile: Tuple[str, ...] = ()


AGENTS = (
    AgentSpec("intent_router", "clasificar intención y familia matemática", ("user_prompt",), ("intent","task_family")),
    AgentSpec("architect", "diseñar el plan maestro y descomponer el problema", ("user_prompt","intent","task_family","strategy_context"), ("plan",), ("intent_router",), ("plan_valid","dependency_check")),
    AgentSpec("foundation_analyst", "identificar definiciones, axiomas, prerequisitos y notación necesarios", ("plan","knowledge_context"), ("foundations",), ("architect",), ("foundation_coverage",)),
    AgentSpec("mathematical_resolver", "resolver con desarrollo algebraico/analítico completo", ("plan","foundations","user_prompt"), ("solution",), ("foundation_analyst",), ("symbolic_consistency","step_completeness"), ("sympy",)),
    AgentSpec("proof_specialist", "construir y revisar demostraciones formales", ("foundations","solution"), ("proofs",), ("mathematical_resolver",), ("proof_completeness","logical_consistency")),
    AgentSpec("representation_designer", "decidir qué representaciones hacen visible la idea matemática", ("plan","foundations","solution"), ("representation_plan",), ("mathematical_resolver",), ("representation_relevance",)),
    AgentSpec("python_visualizer", "producir especificaciones/código Python para figuras matemáticas reproducibles", ("representation_plan","solution"), ("python_artifacts",), ("representation_designer",), ("code_syntax","numerical_sanity"), ("python","numpy","sympy","matplotlib")),
    AgentSpec("canvas_engineer", "crear visores HTML/Canvas/JavaScript interactivos", ("representation_plan","solution"), ("canvas_artifacts",), ("representation_designer",), ("html_safety","interaction_integrity"), ("html","javascript","canvas")),
    AgentSpec("code_reviewer", "revisar código, reproducibilidad y correspondencia matemática", ("python_artifacts","canvas_artifacts","solution"), ("code_review",), ("python_visualizer","canvas_engineer"), ("code_regression","math_code_alignment")),
    AgentSpec("research_specialist", "extender el problema con generalizaciones, relaciones y aplicaciones pertinentes", ("plan","foundations","solution"), ("research",), ("proof_specialist",), ("source_traceability",)),
    AgentSpec("integrator", "integrar teoría, solución, pruebas y representaciones sin perder trazabilidad", ("plan","foundations","solution","proofs","python_artifacts","canvas_artifacts","research"), ("integrated_report",), ("code_reviewer","research_specialist"), ("completeness","traceability")),
    AgentSpec("epistemic_reviewer", "auditar afirmaciones, evidencia y certificación", ("integrated_report",), ("epistemic_review",), ("integrator",), ("evidence_gate","cas_gate")),
    AgentSpec("document_engineer", "emitir Markdown canónico y derivados HTML/DOCX/DOC", ("integrated_report","epistemic_review"), ("markdown","html","documents"), ("epistemic_reviewer",), ("markdown_canonical","math_rendering")),
    AgentSpec("experience_evaluator", "evaluar resultado y registrar experiencia para aprendizaje controlado", ("integrated_report","epistemic_review","strategy_context"), ("evaluation","experience_record"), ("document_engineer",), ("evaluation_profile","strategy_outcome")),
)


def get_agent(agent_id: str) -> AgentSpec:
    for agent in AGENTS:
        if agent.id == agent_id:
            return agent
    raise KeyError(agent_id)


def execution_order() -> Tuple[str, ...]:
    pending = {a.id: set(a.depends_on) for a in AGENTS}
    order = []
    while pending:
        ready = sorted(k for k, deps in pending.items() if not deps.intersection(pending))
        if not ready:
            raise ValueError("Dependencia circular en arquitectura de agentes")
        order.extend(ready)
        for k in ready:
            pending.pop(k)
    return tuple(order)


def validate_artifact_owner(agent_id: str, artifact_type: str) -> bool:
    owners = {
        "python": "python_visualizer",
        "figure": "python_visualizer",
        "canvas": "canvas_engineer",
        "html": "document_engineer",
        "markdown": "document_engineer",
        "docx": "document_engineer",
        "proof": "proof_specialist",
        "research": "research_specialist",
    }
    return owners.get(artifact_type) == agent_id
