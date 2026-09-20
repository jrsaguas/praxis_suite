"""Domain model for investigations and their evolution.

This layer deliberately sits above the existing chat/response folders. It does
not move files or create a second storage hierarchy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import re


DIMENSIONS = (
    "mathematics",
    "depth",
    "explanation",
    "visualization",
    "interactivity",
    "images",
    "code",
    "structure",
)


@dataclass(frozen=True)
class EvaluationProfile:
    """User-evaluable quality dimensions, normalized to 0..100."""

    mathematics: int = 0
    depth: int = 0
    explanation: int = 0
    visualization: int = 0
    interactivity: int = 0
    images: int = 0
    code: int = 0
    structure: int = 0

    def __post_init__(self) -> None:
        for name in DIMENSIONS:
            value = getattr(self, name)
            if not isinstance(value, int) or not 0 <= value <= 100:
                raise ValueError(f"{name} must be an integer between 0 and 100")

    def weighted_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        weights = weights or {name: 1.0 for name in DIMENSIONS}
        total = 0.0
        weight_sum = 0.0
        for name in DIMENSIONS:
            weight = max(0.0, float(weights.get(name, 0.0)))
            total += getattr(self, name) * weight
            weight_sum += weight
        return round(total / weight_sum, 2) if weight_sum else 0.0


@dataclass(frozen=True)
class InvestigationVersion:
    investigation_id: str
    version_id: str
    parent_version_id: Optional[str]
    created_at: str
    source: str
    prompt: str
    title: str
    response_folder: Optional[str] = None
    commands: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    evaluation: Optional[EvaluationProfile] = None
    artifact_types: List[str] = field(default_factory=list)
    status: str = "succeeded"
    strategy_context: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        investigation_id: str,
        prompt: str,
        title: str,
        *,
        parent_version_id: Optional[str] = None,
        response_folder: Optional[str] = None,
        source: str = "pipeline",
        commands: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
        evaluation: Optional[EvaluationProfile] = None,
        artifact_types: Optional[List[str]] = None,
        status: str = "succeeded",
        strategy_context: Optional[Dict[str, Any]] = None,
    ) -> "InvestigationVersion":
        now = datetime.now(timezone.utc).isoformat()
        seed = "|".join(
            (
                investigation_id,
                parent_version_id or "",
                prompt,
                title,
                now,
            )
        )
        version_id = "v-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        return InvestigationVersion(
            investigation_id=investigation_id,
            version_id=version_id,
            parent_version_id=parent_version_id,
            created_at=now,
            source=source,
            prompt=prompt,
            title=title,
            response_folder=response_folder,
            commands=list(commands or []),
            references=list(references or []),
            evaluation=evaluation,
            artifact_types=list(artifact_types or []),
            status=status,
            strategy_context=dict(strategy_context or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.evaluation is not None:
            data["evaluation"] = asdict(self.evaluation)
        return data


def slug_investigation_id(chat_id: str, response_folder: str) -> str:
    """Stable identifier without changing the physical folder layout."""
    safe_chat = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(chat_id)).strip("_")
    safe_folder = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(response_folder)).strip("_")
    return f"{safe_chat}/{safe_folder}"



@dataclass(frozen=True)
class ExperienceReference:
    """A reusable reference selected from prior evaluated investigations."""

    investigation_id: str
    version_id: str
    relevance: float
    reason: str
    evaluation: EvaluationProfile | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.relevance) <= 1.0:
            raise ValueError("relevance must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.evaluation is not None:
            data["evaluation"] = asdict(self.evaluation)
        return data
