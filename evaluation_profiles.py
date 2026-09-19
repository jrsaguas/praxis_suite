"""Multi-dimensional evaluation and strategy comparison utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

from investigation_model import DIMENSIONS, EvaluationProfile


@dataclass(frozen=True)
class ProfileComparison:
    baseline: float
    candidate: float
    improvement: float
    improved_dimensions: tuple[str, ...]
    regressed_dimensions: tuple[str, ...]
    unchanged_dimensions: tuple[str, ...]

    def to_dict(self):
        return {
            "baseline": self.baseline,
            "candidate": self.candidate,
            "improvement": self.improvement,
            "improved_dimensions": list(self.improved_dimensions),
            "regressed_dimensions": list(self.regressed_dimensions),
            "unchanged_dimensions": list(self.unchanged_dimensions),
        }


def compare_profiles(
    baseline: EvaluationProfile,
    candidate: EvaluationProfile,
    *,
    weights: Mapping[str, float] | None = None,
) -> ProfileComparison:
    weights = weights or {d: 1.0 for d in DIMENSIONS}
    improved, regressed, unchanged = [], [], []
    for dimension in DIMENSIONS:
        left, right = getattr(baseline, dimension), getattr(candidate, dimension)
        if right > left:
            improved.append(dimension)
        elif right < left:
            regressed.append(dimension)
        else:
            unchanged.append(dimension)

    return ProfileComparison(
        baseline=baseline.weighted_score(dict(weights)),
        candidate=candidate.weighted_score(dict(weights)),
        improvement=round(
            candidate.weighted_score(dict(weights))
            - baseline.weighted_score(dict(weights)), 2
        ),
        improved_dimensions=tuple(improved),
        regressed_dimensions=tuple(regressed),
        unchanged_dimensions=tuple(unchanged),
    )


def profile_from_dict(data: Dict[str, int]) -> EvaluationProfile:
    return EvaluationProfile(**{d: int(data.get(d, 0)) for d in DIMENSIONS})
