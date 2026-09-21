"""Provider/model registry and per-agent model routing.

An agent is a role; a model is an interchangeable reasoning/generation engine.
This layer makes the assignment explicit and runtime-overridable without
storing API secrets in investigation metadata.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import os
from typing import Any, Mapping, Optional

@dataclass(frozen=True)
class ModelSpec:
    id: str
    provider: str
    model: str
    capabilities: tuple[str, ...] = ()
    endpoint_env: Optional[str] = None
    api_key_env: Optional[str] = None

    def to_dict(self):
        data = asdict(self)
        data["capabilities"] = list(self.capabilities)
        return data

@dataclass(frozen=True)
class ModelAssignment:
    agent_id: str
    model_id: str
    reason: str = "default"

    def to_dict(self):
        return asdict(self)

DEFAULT_MODELS = (
    ModelSpec("ollama-qwen", "ollama", "qwen2-math:7b", ("math","reasoning","local"), "OLLAMA_BASE_URL"),
    ModelSpec("ollama-llama", "ollama", "llama3.2:3b", ("general","local"), "OLLAMA_BASE_URL"),
    ModelSpec("gemini-default", "gemini", "configured", ("general","reasoning","research"), "GEMINI_API_URL", "GEMINI_API_KEY"),
    ModelSpec("openrouter-default", "openrouter", "configured", ("general","reasoning","research"), "OPENROUTER_BASE_URL", "OPENROUTER_API_KEY"),
    ModelSpec("groq-default", "groq", "configured", ("general","fast"), "GROQ_BASE_URL", "GROQ_API_KEY"),
)

DEFAULT_ASSIGNMENTS = {
    "foundation_analyst": "ollama-qwen",
    "mathematical_resolver": "ollama-qwen",
    "proof_specialist": "ollama-qwen",
    "research_specialist": "gemini-default",
    "python_visualizer": "ollama-qwen",
    "canvas_engineer": "ollama-llama",
    "code_reviewer": "ollama-llama",
    "epistemic_reviewer": "gemini-default",
    "final_auditor": "gemini-default",
    "document_engineer": "ollama-llama",
}

class ModelRegistry:
    def __init__(self, models=DEFAULT_MODELS):
        self._models = {m.id: m for m in models}

    def get(self, model_id: str) -> ModelSpec:
        return self._models[str(model_id)]

    def list(self):
        return tuple(self._models.values())

    def public_config(self):
        return [m.to_dict() for m in self._models.values()]

class ModelRouter:
    def __init__(self, registry: Optional[ModelRegistry] = None, assignments: Optional[Mapping[str, str]] = None):
        self.registry = registry or ModelRegistry()
        self.assignments = dict(DEFAULT_ASSIGNMENTS)
        self.assignments.update(dict(assignments or {}))
        env_json = os.getenv("PRAXIS_MODEL_ASSIGNMENTS", "").strip()
        if env_json:
            try:
                self.assignments.update(json.loads(env_json))
            except json.JSONDecodeError:
                pass

    def resolve(self, agent_id: str, override: Optional[str] = None) -> ModelAssignment:
        model_id = override or self.assignments.get(agent_id)
        if not model_id:
            # Deterministic fallback; the role remains usable without a model.
            model_id = "ollama-llama"
        self.registry.get(model_id)
        return ModelAssignment(agent_id, model_id, "override" if override else "configured")

    def resolve_with_experience(self, agent_id: str, experience_context: Optional[Mapping[str, Any]] = None, override: Optional[str] = None) -> ModelAssignment:
        if override:
            return self.resolve(agent_id, override)
        refs = (experience_context or {}).get("references") or []
        # Experience may recommend a model explicitly, but only an allowed registered model is accepted.
        for ref in refs:
            candidate = ((ref.get("metadata") or {}).get("recommended_model") or
                         (ref.get("metadata") or {}).get("model_id"))
            if candidate and candidate in {m.id for m in self.registry.list()}:
                return ModelAssignment(agent_id, candidate, "experience_reference")
        return self.resolve(agent_id)

    def resolve_plan(self, agent_ids, overrides=None, experience_context=None):
        overrides = overrides or {}
        return {agent_id: self.resolve_with_experience(agent_id, experience_context, overrides.get(agent_id)) for agent_id in agent_ids}
