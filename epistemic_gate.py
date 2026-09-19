"""Epistemic gating for Praxis knowledge consolidation."""

VALID_STATUSES = frozenset({"VALIDADO_CAS", "VALIDADO_FUENTES", "REVISADO_HUMANO"})
PENDING_STATUS = "CANDIDATO_PENDIENTE"


def make_provenance(investigation_id, status=PENDING_STATUS, checks=()):
    return {
        "investigacion_id": investigation_id,
        "estado_validacion": status,
        "checks": list(checks),
    }


def can_consolidate(provenance):
    return provenance.get("estado_validacion") in VALID_STATUSES
