# PLAN DE EJECUCIÓN — CIERRE P0/P1
Fecha: 2026-09-22
Rama: audit/hardening-2026-09

## Objetivo
Cerrar la cadena real de ejecución y aprendizaje sin tocar main:

perfil objetivo → referencias aceptadas → planner → AgentRuntime → auditoría → evaluador → candidate → feedback humano → accepted → selección futura.

## Fase P0 — Runtime ejecutable
- [x] Endpoint POST /api/agent-graph/execute cableado.
- [x] Carga de perfil persistido cuando se proporciona chat/folder.
- [x] Construcción de contexto de profundidad.
- [x] Selección de experiencia aceptada.
- [x] Planificación con overrides de modelo.
- [x] Fingerprint estable de tarea.
- [x] Experience sink conectado al runtime.
- [x] Fallo de persistencia no invalida ejecución.
- [ ] Prueba HTTP real del endpoint.
- [ ] CI verde sobre el conjunto completo.

## Fase P1 — Aprendizaje controlado
- [x] Resultados del evaluador se almacenan como candidate.
- [x] candidate no entra en referencias futuras.
- [x] Feedback accept/reject cambia reutilización.
- [x] Solo accepted puede alimentar Promotion Gate.
- [x] Perfil 0–100 participa en selección.
- [x] Test del contexto confirma candidate excluido y accepted seleccionado.
- [ ] Integrar feedback con UI.
- [ ] Verificar flujo completo con datos de una investigación real.

## Fase P1.5 — Artefactos/versionado
- [ ] Estado freshness: current/stale/invalid.
- [ ] Relación fuente MD → derivados HTML/DOCX/DOC.
- [ ] Manifest actualizado tras cada ejecución.
- [ ] Descargas apuntan a versión actual.
- [ ] Prueba de edición → regeneración → manifest.

## Fase P2 — UI y expansión
- [ ] Navegación visual de versiones.
- [ ] Edición contextual por bloque/canvas/imagen.
- [ ] Adaptive Agent.
- [ ] Agent Factory.
- [ ] Panel avanzado de herramientas.
- [ ] Perfiles multidimensionales completos conectados a UI.

## Criterio de cierre P0/P1
No se considera terminado hasta que:
1. CI pase.
2. Un request real cree plan y ejecute runtime.
3. final_auditor y experience_evaluator aparezcan en el trace.
4. Se genere candidate persistente.
5. candidate no se reutilice.
6. accept lo convierta en accepted.
7. Una ejecución posterior pueda seleccionarlo según task_family/perfil.
8. Un fallo del almacén de experiencia no marque la investigación como fallida.

## Riesgos actuales
- El PR #1 es grande; evitar más cambios estructurales innecesarios.
- Algunas pruebas existentes son de inspección de fuente; deben sustituirse gradualmente por integración HTTP.
- La ejecución real depende de adaptadores/modelos disponibles; el test debe aislar proveedor cuando corresponda.
