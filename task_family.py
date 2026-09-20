"""Task-family grouping for controlled experience learning.

Experiences from unrelated task families are not mixed when deriving trends.
The classifier is intentionally conservative: explicit metadata wins, then
stable feature/topic signals, otherwise a generic family is used.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List


FAMILY_RULES = {
    "surface_visualization": {
        "surface", "superficie", "gradient", "curvature", "curvatura",
        "level_curve", "curvas_nivel", "canvas", "3d",
    },
    "calculus": {
        "integral", "derivative", "derivada", "integral", "green", "stokes",
        "gauss", "divergence", "divergencia", "triple",
    },
    "linear_algebra": {
        "matrix", "matriz", "vector", "eigen", "determinant",
        "determinante", "linear", "lineal", "system",
    },
    "research_document": {
        "research", "investigación", "investigation", "document",
        "documento", "report", "informe", "apa", "sources", "fuentes",
    },
}


def classify_task_family(record: Dict[str, Any]) -> str:
    metadata = record.get("metadata") or {}
    explicit = metadata.get("task_family") or record.get("task_family")
    if explicit:
        return str(explicit).strip().lower().replace(" ", "_")

    text = " ".join([
        str(record.get("task_fingerprint", "")),
        str(metadata.get("title", "")),
        str(metadata.get("topic", "")),
        " ".join(map(str, metadata.get("features", []))),
    ]).lower()

    scores = {
        family: sum(1 for signal in signals if signal in text)
        for family, signals in FAMILY_RULES.items()
    }
    family, score = max(scores.items(), key=lambda item: item[1])
    return family if score else "general"


def group_records_by_family(
    records: Iterable[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[classify_task_family(record)].append(record)
    return dict(groups)


def family_summary(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups = group_records_by_family(records)
    result = []
    for family, items in groups.items():
        scores = [float((r.get("evaluation") or {}).get("score", 0.0)) for r in items]
        accepted = sum(bool((r.get("evaluation") or {}).get("consistent")) for r in items)
        result.append({
            "task_family": family,
            "count": len(items),
            "mean_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "accept_rate": round(accepted / len(items), 4) if items else 0.0,
            "record_ids": [str(r.get("record_id", "")) for r in items[-10:]],
        })
    return sorted(result, key=lambda item: (item["mean_score"], item["count"]), reverse=True)
