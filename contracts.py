"""Contratos mínimos entre etapas del pipeline de Praxis.

Estos contratos no deciden si un resultado es correcto; garantizan que las
etapas intercambien estructuras predecibles y trazables.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VerificationStatus:
    status: str
    checks: int = 0
    details: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def is_verified(self) -> bool:
        return self.status == "VALIDADO_CAS"


@dataclass(frozen=True)
class PipelineResult:
    ok: bool
    stage: str
    payload: Any
    verification: VerificationStatus | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
