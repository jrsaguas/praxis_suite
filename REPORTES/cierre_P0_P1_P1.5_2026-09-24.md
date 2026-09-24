# CIERRE DEL BLOQUE P0/P1/P1.5 — VERIFICACIÓN FINAL

## Estado

**PARCIAL — NO CERRADO TODAVÍA.**

La implementación funcional del bloque está presente en `audit/hardening-2026-09`, pero después de añadir cobertura de seguridad del preview histórico y controles finales de UI, el HEAD cambió. Por trazabilidad no se conserva la declaración anterior de cierre hasta disponer de CI verificable sobre el estado actual.

Rama: `audit/hardening-2026-09`  
PR: #1 contra `main`  
HEAD actual: `282277899b31ba320fcefd2ab0c7fc6151fa1760`

## Evidencia previa

CI `35951100534` — **success**  
Commit verificado: `baf33161d9ea66183d7e19b2e46cdd316622c0e7`

Ese CI verificó la batería existente antes de los últimos cambios de hardening. No se utiliza como evidencia de que el HEAD actual esté certificado.

## Últimos cambios pendientes de certificación

- Test unitario de rechazo de traversal en `read_version_snapshot_artifact`.
- Test HTTP de rechazo de traversal en preview histórico.
- Controles explícitos en la vista histórica:
  - volver al estado actual;
  - restaurar como nueva versión;
  - usar la versión como contexto.

## Criterios funcionales ya implementados

- Runtime: tareas, dependencias, contexto, modelo, requisitos y trace observable.
- Execution: promoción de versión solo después de ejecución exitosa.
- Evaluation: auditoría final y evaluación estructurada.
- Experience: candidate/accepted/rejected y selección ponderada.
- Versioning: historial, navegación, parent_version_id.
- Snapshot: físico, hash SHA-256, restore como nueva versión.
- Historical Preview: MD/HTML read-only.
- Branching: edición contextual desde parent_version_id.
- Manifest: current/stale y relación con Markdown fuente.
- Integration: endpoint HTTP y pruebas de runtime/artefactos.

## Decisión

No se agrega P2 todavía. El único bloqueo del cierre formal es la certificación CI del estado actual.
