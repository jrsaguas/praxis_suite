# Cierre del bloque P0/P1/P1.5 — 2026-09-24

## Estado

El bloque funcional de endurecimiento, ejecución observable, evaluación/experiencia y versionado de investigaciones queda **cerrado para pasar a P2**.

Rama: `audit/hardening-2026-09`  
PR: #1 contra `main`  
Último commit verificado: `baf33161d9ea66183d7e19b2e46cdd316622c0e7`  
CI: ejecución 35951100534 — **success**.

## Criterios de cierre

- **Runtime:** tareas, dependencias, contexto, selección de modelo y trazas observables.
- **Ejecución:** comandos de artefactos, registro de ejecución, promoción únicamente de ejecuciones exitosas y bloqueo de falsos positivos.
- **Evaluación/experiencia:** auditor final, evaluación estructurada, experiencias aceptadas como referencias y exclusión de candidatos/rechazados.
- **Versionado:** historial, navegación, ramificación mediante `parent_version_id`, snapshots físicos, restauración como nueva versión y manifest actualizado.
- **Vista histórica:** lectura verificada por SHA-256 de snapshots MD/HTML sin modificar el estado actual; la UI ya puede previsualizar snapshots en modo solo lectura.
- **Integridad:** pruebas unitarias y de integración cubren restauración, preview histórico, branching contextual y consistencia del manifest.
- **CI:** la última ejecución del flujo completo terminó correctamente.

## Qué queda deliberadamente fuera de este cierre

Esto no significa que Praxis Suite esté terminado como producto completo. Quedan para **P2** las capacidades superiores que fueron acordadas:

1. Adaptive Agent.
2. Agent Factory.
3. Tools Panel para adaptación manual de agentes.
4. Perfil matemático multidimensional completo en UI.
5. Composición dinámica de agentes y flujos.
6. Aprendizaje de patrones/preferencias con promoción controlada.
7. Evolución posterior de UI de historial y ramas.

No se modifica `main` en este cierre.

## Decisión de transición

A partir de este punto no se deben seguir agregando requisitos al bloque P0/P1/P1.5 salvo que aparezca un fallo real en regresión. El siguiente trabajo debe comenzar en **P2: Adaptive Agent + Agent Factory**, manteniendo esta base como contrato de estabilidad.
