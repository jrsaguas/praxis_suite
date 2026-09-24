"""Declarative specialist-agent archetypes for Praxis.

Archetypes describe reusable role contracts. They do not select a model, execute
work, validate candidates, or activate agents. A concrete AgentBlueprint may
reference an archetype through its context/provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AgentArchetype:
    id: str
    role: str
    mission: str
    capabilities: Tuple[str, ...]
    tool_profile: Tuple[str, ...]
    input_artifacts: Tuple[str, ...]
    output_artifacts: Tuple[str, ...]
    quality_gates: Tuple[str, ...]
    forbidden_actions: Tuple[str, ...]
    depth_dimensions: Tuple[str, ...] = ()


ARCHETYPES = (
    AgentArchetype(
        "code",
        "code specialist",
        "implementar y mantener código reproducible alineado con requisitos técnicos",
        ("implementation", "refactoring", "testing", "debugging"),
        ("python", "javascript", "git"),
        ("requirements", "source_code", "tests"),
        ("code_artifacts", "test_results"),
        ("syntax", "regression", "reproducibility", "requirement_alignment"),
        ("activate_agents", "mutate_investigation", "silently_change_requirements"),
        ("rigor", "formalism", "experimentation"),
    ),
    AgentArchetype(
        "python_visualization",
        "python-visualization specialist",
        "producir visualizaciones matemáticas y físicas reproducibles con Python",
        ("numerical_visualization", "mathematical_plotting", "physics_visualization"),
        ("python", "numpy", "sympy", "matplotlib", "plotly"),
        ("solution", "representation_plan", "parameters"),
        ("python_artifacts", "figures", "numeric_checks"),
        ("code_syntax", "numerical_sanity", "math_code_alignment", "reproducibility"),
        ("change_mathematical_claims", "activate_agents", "silently_change_requirements"),
        ("rigor", "visualization", "experimentation", "generalization"),
    ),
    AgentArchetype(
        "canvas_html",
        "canvas-html specialist",
        "construir visualizaciones web interactivas con HTML, JavaScript y Canvas",
        ("interactive_visualization", "canvas", "browser_interaction"),
        ("html", "javascript", "canvas", "mathjax"),
        ("solution", "representation_plan", "interaction_requirements"),
        ("canvas_artifacts", "html_artifacts", "interaction_tests"),
        ("html_safety", "interaction_integrity", "math_rendering", "accessibility"),
        ("execute_untrusted_external_code", "change_mathematical_claims", "activate_agents"),
        ("visualization", "experimentation", "generalization"),
    ),
    AgentArchetype(
        "mathematical_proof",
        "mathematical-proof specialist",
        "construir, revisar y formalizar demostraciones con trazabilidad lógica",
        ("proof_construction", "proof_review", "formal_reasoning"),
        ("sympy", "lean", "theorem_prover"),
        ("foundations", "definitions", "solution", "claims"),
        ("proofs", "proof_obligations", "verification_notes"),
        ("proof_completeness", "logical_consistency", "assumption_traceability"),
        ("invent_definitions", "skip_required_prerequisites", "activate_agents"),
        ("rigor", "prerequisites", "formalism", "proof", "generalization"),
    ),
    AgentArchetype(
        "research",
        "research specialist",
        "localizar, contrastar y sintetizar evidencia externa trazable",
        ("source_retrieval", "source_comparison", "literature_synthesis"),
        ("web", "rag", "citation_tools"),
        ("research_question", "claims", "knowledge_context"),
        ("research_evidence", "source_map", "citations"),
        ("source_traceability", "claim_support", "date_relevance"),
        ("present_uncited_claims_as_verified", "alter_primary_artifacts", "activate_agents"),
        ("research", "generalization", "applications"),
    ),
    AgentArchetype(
        "math_resolver",
        "mathematical-resolver specialist",
        "resolver problemas matemáticos con desarrollo verificable y completo",
        ("symbolic_reasoning", "algebraic_derivation", "numerical_checking"),
        ("sympy", "python", "cas"),
        ("user_prompt", "foundations", "constraints"),
        ("solution", "derivation", "verification_certificate"),
        ("symbolic_consistency", "step_completeness", "assumption_traceability"),
        ("hide_unverified_steps", "change_requirements", "activate_agents"),
        ("rigor", "prerequisites", "formalism", "proof", "experimentation"),
    ),
    AgentArchetype(
        "integrator",
        "integrator specialist",
        "integrar resultados heterogéneos conservando trazabilidad y contratos",
        ("artifact_integration", "traceability", "consistency_review"),
        ("python", "html", "rag"),
        ("plan", "solution", "proofs", "research_evidence", "artifacts"),
        ("integrated_report", "artifact_manifest", "traceability_map"),
        ("completeness", "traceability", "cross_artifact_consistency"),
        ("invent_missing_evidence", "silently_change_specialist_results", "activate_agents"),
        ("rigor", "formalism", "research", "generalization"),
    ),
)


def get_archetype(archetype_id: str) -> AgentArchetype:
    for archetype in ARCHETYPES:
        if archetype.id == archetype_id:
            return archetype
    raise KeyError(archetype_id)


def infer_archetype(*, tools=(), requirements=(), role="") -> AgentArchetype:
    signals = {str(x).lower() for x in (*tools, *requirements)}
    role_text = str(role).lower()

    if any(x in signals or x in role_text for x in ("canvas", "javascript", "html", "js")):
        return get_archetype("canvas_html")
    if any(x in signals or x in role_text for x in ("matplotlib", "plotly", "visualization", "visualization")):
        return get_archetype("python_visualization")
    if any("proof" in x or "formal" in x for x in signals) or "proof" in role_text:
        return get_archetype("mathematical_proof")
    if any("research" in x or "source" in x for x in signals) or "research" in role_text:
        return get_archetype("research")
    if any("code" in x or "implementation" in x for x in signals) or "code" in role_text:
        return get_archetype("code")
    if any(x in signals for x in ("sympy", "cas", "symbolic")):
        return get_archetype("math_resolver")
    if "integrator" in role_text:
        return get_archetype("integrator")
    return get_archetype("math_resolver")
