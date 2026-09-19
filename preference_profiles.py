"""Preference profiles and preference-aware experience scoring.

Preferences are data, not executable policy. They influence comparison and
reference selection only when explicitly supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Any

from investigation_model import DIMENSIONS, EvaluationProfile


@dataclass(frozen=True)
class PreferenceProfile:
    weights: Dict[str, float]
    version: int = 1

    def __post_init__(self):
        unknown = set(self.weights) - set(DIMENSIONS)
        if unknown:
            raise ValueError(f"Unknown preference dimensions: {sorted(unknown)}")
        for key, value in self.weights.items():
            if float(value) < 0:
                raise ValueError(f"Preference weight must be non-negative: {key}")

    @classmethod
    def from_percentages(cls, percentages: Mapping[str, int]) -> "PreferenceProfile":
        values = {}
        for dimension in DIMENSIONS:
            value = int(percentages.get(dimension, 0))
            if not 0 <= value <= 100:
                raise ValueError(f"{dimension} must be between 0 and 100")
            values[dimension] = float(value)
        return cls(values)

    def score(self, evaluation: EvaluationProfile) -> float:
        return evaluation.weighted_score(self.weights)

    def to_dict(self) -> Dict[str, Any]:
        return {"version": self.version, "weights": dict(self.weights)}


def preference_from_dict(data: Mapping[str, Any]) -> PreferenceProfile:
    return PreferenceProfile(
        weights={dimension: float(value) for dimension, value in (data.get("weights") or {}).items()},
        version=int(data.get("version", 1)),
    )


def compare_preference_fit(
    baseline: EvaluationProfile,
    candidate: EvaluationProfile,
    preferences: PreferenceProfile,
) -> Dict[str, Any]:
    base = preferences.score(baseline)
    cand = preferences.score(candidate)
    return {
        "baseline": base,
        "candidate": cand,
        "improvement": round(cand - base, 2),
        "preferred_dimensions": [
            d for d in DIMENSIONS
            if getattr(candidate, d) > getattr(baseline, d)
            and preferences.weights.get(d, 0) > 0
        ],
        "regressed_dimensions": [
            d for d in DIMENSIONS
            if getattr(candidate, d) < getattr(baseline, d)
            and preferences.weights.get(d, 0) > 0
        ],
    }
