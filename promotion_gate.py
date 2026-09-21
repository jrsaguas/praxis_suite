"""Evidence-based promotion gate for learned strategies.

A candidate can only be promoted when it has enough comparable outcomes in the
same task family, beats a baseline by the configured margin, has no critical
regression, and passes its declared regression tests. This module only decides;
it never changes application code.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


def _mean(items, key, default=0.0):
    vals = [float((x.get("evaluation") or {}).get(key, default)) for x in items]
    return sum(vals) / len(vals) if vals else default


def compare_strategy_to_baseline(
    outcomes: Iterable[Mapping[str, Any]],
    *,
    strategy_id: str,
    baseline_id: str = "baseline-v1",
    task_family: str | None = None,
    min_samples: int = 3,
    accepted_only: bool = True,
) -> Dict[str, Any]:
    rows = list(outcomes)
    if accepted_only:
        rows = [x for x in rows if str(x.get('reuse_status', 'candidate')) == 'accepted']

    def same_family(x):
        return not task_family or (x.get("metadata") or {}).get("task_family") == task_family

    comparable = [x for x in rows if same_family(x)]
    candidate = [x for x in comparable if str(x.get("strategy_id")) == strategy_id]
    baseline = [x for x in comparable if str(x.get("strategy_id")) == baseline_id]

    candidate_score = _mean(candidate, "score")
    baseline_score = _mean(baseline, "score")
    improvement = candidate_score - baseline_score

    return {
        "strategy_id": strategy_id,
        "baseline_id": baseline_id,
        "task_family": task_family,
        "candidate_samples": len(candidate),
        "baseline_samples": len(baseline),
        "candidate_score": round(candidate_score, 4),
        "baseline_score": round(baseline_score, 4),
        "improvement": round(improvement, 4),
        "enough_evidence": len(candidate) >= min_samples and len(baseline) >= min_samples,
        "accepted_only": accepted_only,
    }


def evaluate_gate(
    comparison: Mapping[str, Any],
    *,
    passed_tests: Iterable[str] = (),
    required_tests: Iterable[str] = (),
    min_improvement: float = 0.02,
    max_regressions: int = 0,
    regressions: Iterable[str] = (),
) -> Dict[str, Any]:
    passed = {str(x) for x in passed_tests}
    required = {str(x) for x in required_tests}
    regressions = tuple(dict.fromkeys(str(x) for x in regressions))
    missing = sorted(required - passed)
    improvement = float(comparison.get("improvement", 0.0))
    enough = bool(comparison.get("enough_evidence"))
    approved = enough and improvement >= min_improvement and not missing and len(regressions) <= max_regressions

    return {
        "approved": approved,
        "reason": (
            "evidencia suficiente, mejora mínima y pruebas sin regresiones"
            if approved else
            "evidencia insuficiente, mejora insuficiente, pruebas faltantes o regresiones"
        ),
        "evidence": dict(comparison),
        "required_tests": sorted(required),
        "passed_tests": sorted(passed),
        "missing_tests": missing,
        "regressions": list(regressions),
        "thresholds": {
            "min_samples": None,
            "min_improvement": min_improvement,
            "max_regressions": max_regressions,
        },
    }
