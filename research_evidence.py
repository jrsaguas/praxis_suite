"""Validation of retrieved research evidence.

The verifier does not treat model-supplied URLs or citations as retrieval.
Evidence must carry provenance from a real retriever used by Praxis.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

RETRIEVER_IDS = {"rag_engine.search_arxiv"}

def verify_research_evidence(evidence: Any) -> dict[str, Any]:
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        return {"passed": False, "method": "retrieval_provenance_check",
                "reason": "research_evidence_missing"}
    valid, invalid = [], []
    for item in evidence:
        if not isinstance(item, Mapping):
            invalid.append("non_mapping")
            continue
        required = ("title", "year", "abstract", "pdf_url", "retrieved_by")
        missing = [key for key in required if not item.get(key)]
        if missing or item.get("retrieved_by") not in RETRIEVER_IDS:
            invalid.append({"missing": missing, "retrieved_by": item.get("retrieved_by")})
            continue
        valid.append({"title": str(item["title"]), "year": str(item["year"]),
                      "pdf_url": str(item["pdf_url"]), "retrieved_by": item["retrieved_by"]})
    return {
        "passed": bool(valid) and not invalid,
        "method": "retrieval_provenance_check",
        "verified_by": "praxis_retriever_contract",
        "authoritative": True,
        "valid_sources": valid,
        "invalid_sources": invalid,
        "count": len(valid),
    }
