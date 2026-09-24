# PLAN DE EJECUCIÓN — CIERRE P0/P1
Fecha de actualización: 2026-09-23
Rama: audit/hardening-2026-09

## Objetivo
Cerrar la cadena real:
perfil → referencias aceptadas → planner → AgentRuntime → auditoría → evaluador → candidate → feedback → accepted → selección futura → versionado → snapshot → preview → branching.

## Estado del cierre

### IMPLEMENTADO
- Endpoint POST /api/agent-graph/execute.
- Planner → runtime → trace observable.
- Contexto de perfil/profundidad/experiencia.
- final_auditor → experience_evaluator.
- Candidate persistente y exclusión de candidates de referencias futuras.
- Feedback accept/reject/review en store.
- Versionado, parent_version_id y navegación.
- Snapshots físicos y restauración como nueva versión.
- Manifest/freshness.
- Preview histórico MD/HTML read-only con integridad SHA-256.
- Metadata de snapshot para descubrir artefactos.
- UI de preview/restauración/contexto.
- Snapshot de la versión raíz.
- Tests HTTP de preview y branching.
- Test de rechazo de traversal histórico añadido en HEAD actual.

### VERIFICADO
- CI 35951100534, commit baf33161d9ea66183d7e19b2e46cdd316622c0e7: success.
- El PR #1 sigue draft, abierto y apunta a main.
- main no fue modificado.

### PENDIENTE
1. CI verificable sobre el HEAD actual `282277899b31ba320fcefd2ab0c7fc6151fa1760`.
2. Una vez verde, revisar únicamente regresiones reales; no ampliar el alcance de este bloque.
3. Emitir cierre formal y comenzar P2.

## Cobertura física

`_ARTIFACT_ROOTS` define explícitamente las raíces versionadas:
- documentos
- visualizador interactivo
- imágenes
- código de gráficos
- proceso de agentes

No se deben describir como snapshot completo los metadatos globales, configuración, credenciales, modelos externos ni recursos remotos.

## Criterio de cierre final

Se requieren:
1. Runtime observable.
2. Ejecución exitosa → versión; ejecución fallida → no versión.
3. Auditoría/evaluación/experiencia con candidate/accepted/rejected.
4. Historial + snapshot + preview + restore + branching + manifest + stale detection.
5. Integración HTTP/flujo de runtime.
6. CI verde sobre el estado que se va a declarar cerrado.

P2 no comienza hasta cumplir el punto 6.
