"""Multidimensional mathematical depth profiles for investigation orchestration."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping, Tuple

DIMENSIONS = (
    "rigor", "prerequisites", "formalism", "proof", "research",
    "visualization", "experimentation", "generalization",
)

LEVEL_PRESETS = {
    "fundamental":       (35, 55, 25, 15, 5, 55, 25, 20),
    "secondary":         (45, 60, 35, 25, 5, 60, 35, 25),
    "licenciatura":      (70, 80, 65, 60, 35, 70, 45, 55),
    "maestria":          (82, 88, 82, 78, 65, 78, 65, 75),
    "doctorado":         (95, 95, 95, 92, 92, 82, 78, 92),
    "postdoctorado":     (98, 98, 98, 97, 98, 88, 90, 98),
    "experimental":      (75, 82, 70, 60, 85, 95, 100, 80),
    "matematicas_aplicadas": (82, 85, 78, 70, 82, 88, 92, 90),
    "estadistica":       (78, 82, 72, 65, 78, 88, 95, 82),
    "sistemas_complejos":(85, 88, 82, 72, 88, 92, 95, 95),
    "fisica_matematica": (94, 95, 96, 92, 94, 86, 88, 96),
}


@dataclass(frozen=True)
class MathematicalDepthProfile:
    level: str
    rigor: int
    prerequisites: int
    formalism: int
    proof: int
    research: int
    visualization: int
    experimentation: int
    generalization: int
    custom_rules: Tuple[str, ...] = ()

    def __post_init__(self):
        for field in ("rigor","prerequisites","formalism","proof","research","visualization","experimentation","generalization"):
            value = getattr(self, field)
            if not 0 <= value <= 100:
                raise ValueError(f"{field} must be between 0 and 100")

    @classmethod
    def preset(cls, level: str, custom_rules=()):
        key = str(level).lower().strip()
        if key not in LEVEL_PRESETS:
            raise ValueError(f"Unknown mathematical depth level: {level}")
        values = LEVEL_PRESETS[key]
        return cls(key, *values, tuple(str(x) for x in custom_rules if str(x).strip()))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]):
        if data.get("level") and data["level"] in LEVEL_PRESETS and not any(
            k in data for k in ("rigor","prerequisites","formalism","proof","research","visualization","experimentation","generalization")
        ):
            return cls.preset(data["level"], data.get("custom_rules", ()))
        values = {k: int(data.get(k, 0)) for k in ("rigor","prerequisites","formalism","proof","research","visualization","experimentation","generalization")}
        return cls(str(data.get("level", "custom")), **values, custom_rules=tuple(data.get("custom_rules", ())))

    def requirements(self) -> Dict[str, Any]:
        return {
            "min_prerequisite_coverage": self.prerequisites,
            "proof_expectation": self.proof,
            "formalism_expectation": self.formalism,
            "research_expectation": self.research,
            "visualization_expectation": self.visualization,
            "experimentation_expectation": self.experimentation,
            "generalization_expectation": self.generalization,
            "rigor_expectation": self.rigor,
            "custom_rules": list(self.custom_rules),
        }

    def to_dict(self):
        return asdict(self)


def build_depth_context(profile: MathematicalDepthProfile) -> Dict[str, Any]:
    return {
        "depth_profile": profile.to_dict(),
        "requirements": profile.requirements(),
        "context_version": 1,
    }
