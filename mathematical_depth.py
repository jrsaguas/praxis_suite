"""Multidimensional mathematical-depth profiles used by orchestration.

Depth is not a single academic label. Each profile expands into independent
requirements that the planner can use to add specialists and quality gates.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Tuple

DIMENSIONS = (
    "rigor", "prerequisites", "formalism", "proof", "research",
    "visualization", "experimentation", "generalization", "applications",
)

@dataclass(frozen=True)
class MathematicalDepthProfile:
    name: str
    rigor: int
    prerequisites: int
    formalism: int
    proof: int
    research: int
    visualization: int
    experimentation: int
    generalization: int
    applications: int = 0
    custom_rules: Tuple[str, ...] = ()

    def __post_init__(self):
        for field in DIMENSIONS:
            value = int(getattr(self, field))
            if not 0 <= value <= 100:
                raise ValueError(f"{field} must be between 0 and 100")

    @classmethod
    def preset(cls, name: str, custom_rules=()):
        presets = {
            "introductorio": (35, 25, 20, 15, 10, 45, 35, 20, 40),
            "licenciatura": (70, 65, 60, 65, 40, 70, 55, 55, 65),
            "maestria": (82, 78, 78, 80, 68, 78, 70, 75, 75),
            "doctorado": (95, 92, 94, 92, 92, 88, 82, 92, 84),
            "postdoctorado": (98, 96, 98, 96, 97, 92, 92, 97, 88),
            "experimental": (78, 70, 68, 60, 86, 96, 98, 88, 90),
        }
        if name not in presets:
            raise ValueError(f"Perfil de profundidad desconocido: {name}")
        return cls(name, *presets[name], tuple(custom_rules or ()))

    def to_dict(self):
        data = asdict(self)
        data["custom_rules"] = list(self.custom_rules)
        return data

def build_depth_context(profile: MathematicalDepthProfile) -> dict[str, Any]:
    thresholds = {
        "prerequisites": profile.prerequisites,
        "formalism": profile.formalism,
        "proof_expectation": profile.proof,
        "research_expectation": profile.research,
        "visualization_expectation": profile.visualization,
        "experimentation_expectation": profile.experimentation,
        "generalization_expectation": profile.generalization,
        "application_expectation": profile.applications,
        "rigor_expectation": profile.rigor,
    }
    requirements = [
        f"prerequisitos >= {profile.prerequisites}",
        f"formalismo >= {profile.formalism}",
        f"demostración/proof >= {profile.proof}",
        f"investigación >= {profile.research}",
        f"visualización >= {profile.visualization}",
        f"experimentación >= {profile.experimentation}",
        f"generalización >= {profile.generalization}",
        f"aplicaciones >= {profile.applications}",
        f"rigor >= {profile.rigor}",
    ]
    return {
        "profile": profile.to_dict(),
        "requirements": requirements,
        "thresholds": thresholds,
        "custom_rules": list(profile.custom_rules),
    }
