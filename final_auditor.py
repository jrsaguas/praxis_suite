"""Final product auditor.

The auditor consumes the complete observable product context. It does not
rewrite or silently modify the product. Its output is an auditable report with
verified observations separated from recommendations.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Iterable
import re

@dataclass(frozen=True)
class AuditFinding:
    category: str
    severity: str
    message: str
    evidence: str = ""
    recommendation: str = ""

    def to_dict(self):
        return asdict(self)

@dataclass(frozen=True)
class AuditReport:
    status: str
    summary: str
    findings: tuple[AuditFinding, ...]
    checks: Mapping[str, Any]
    model_assignment: Mapping[str, Any] | None = None

    def to_dict(self):
        return {
            "status": self.status,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "checks": dict(self.checks),
            "model_assignment": dict(self.model_assignment or {}),
        }

def audit_product(product: Mapping[str, Any]) -> AuditReport:
    md = str(product.get("markdown") or product.get("integrated_report") or "")
    prompt = str(product.get("user_prompt") or product.get("prompt") or "")
    findings = []
    checks = {}

    checks["markdown_present"] = bool(md.strip())
    checks["requirements_present"] = bool(prompt.strip())
    checks["procedures_present"] = bool(re.search(r"(^|\n)#{1,6}.*(proced|método|metod|desarrollo|paso)", md, re.I))
    checks["mathematical_content_present"] = bool(re.search(r"(\\frac|\\int|\\sum|\\nabla|teorema|demostr|ecuaci)", md, re.I))
    checks["evidence_or_validation_present"] = bool(
        product.get("cas_certificate") or product.get("epistemic_review") or
        re.search(r"(fuente|referencia|validaci|certific)", md, re.I)
    )
    manifest = product.get("artifact_manifest") or {}
    artifacts = manifest.get("artifacts") or []
    checks["artifact_manifest_present"] = bool(manifest)
    checks["derived_artifacts_listed"] = bool(artifacts)
    checks["runtime_trace_present"] = bool(product.get("runtime_trace") or product.get("events") or product.get("traces"))

    if not checks["markdown_present"]:
        findings.append(AuditFinding("completitud", "critical", "No se recibió Markdown canónico completo.", recommendation="Generar o recuperar el Markdown antes de cerrar la investigación."))
    if not checks["requirements_present"]:
        findings.append(AuditFinding("especificaciones", "high", "No se recibió la especificación/prompt original.", recommendation="Conservar el requerimiento original en el contexto de auditoría."))
    if not checks["procedures_present"]:
        findings.append(AuditFinding("procedimiento", "high", "No se detectó una sección explícita de procedimiento/desarrollo.", recommendation="Comprobar que el procedimiento completo esté explicado y sea reproducible."))
    if not checks["evidence_or_validation_present"]:
        findings.append(AuditFinding("verificación", "high", "No se detectó evidencia de validación o revisión.", recommendation="Ejecutar CAS, revisión epistemológica o verificación externa pertinente."))
    if not checks["artifact_manifest_present"]:
        findings.append(AuditFinding("artefactos", "medium", "Falta el manifiesto de artefactos derivados.", recommendation="Actualizar el manifiesto antes de presentar el resultado."))
    if not checks["runtime_trace_present"]:
        findings.append(AuditFinding("trazabilidad", "medium", "No se recibió una traza operacional observable.", recommendation="Registrar eventos del runtime sin exponer razonamiento interno del modelo."))

    status = "pass" if not findings else "needs_review"
    summary = "Auditoría estructural completada; no se detectaron faltantes estructurales." if not findings else f"Auditoría estructural detectó {len(findings)} punto(s) para revisión."
    return AuditReport(status, summary, tuple(findings), checks)

def audit_with_model(product: Mapping[str, Any], model_callable=None) -> AuditReport:
    """Allow a provider-backed model to enrich the audit without making it mandatory."""
    base = audit_product(product)
    if model_callable is None:
        return base
    model_result = model_callable(product)
    findings = list(base.findings)
    if isinstance(model_result, Mapping):
        for item in model_result.get("findings", []):
            if isinstance(item, Mapping):
                findings.append(AuditFinding(
                    str(item.get("category", "model")),
                    str(item.get("severity", "info")),
                    str(item.get("message", "")),
                    str(item.get("evidence", "")),
                    str(item.get("recommendation", "")),
                ))
    summary = str(model_result.get("summary") or base.summary) if isinstance(model_result, Mapping) else base.summary
    return AuditReport("needs_review" if findings else "pass", summary, tuple(findings), base.checks, base.model_assignment)
