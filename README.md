# Praxis V13.0 Suite · Manual de Operación y Arquitectura del Sistema
## Ecosistema Matemático Multi-Agente Híbrido con Verificación Simbólica CAS y Síntesis Dinámica

Suite avanzada de investigación matemática con:

1. **Síntesis Generativa Dinámica de Simuladores Canvas HTML5 (`canvas_synthesizer.py`):**
   * Se erradicaron las plantillas estáticas genéricas.
   * El sistema genera simuladores interactivos especializados para cada tipo de problema:
     - **Atractores Caóticos y 3D (Lorenz / Rössler)** con integración RK4 en tiempo real y rotación de cámara.
     - **Péndulos No Lineales y Sistemas Mecánicos** con vista física y retrato de fase $(\theta, \omega)$ simultáneos y cálculo de energía mecánica $E(t)$.
     - **Sistemas Presa-Depredador (Lotka-Volterra)** con órbitas cerradas en plano fase y puntos de equilibrio.
     - **Álgebra Lineal y Matrices:** Círculo unitario deformado en elipse de transformación, autovectores directos y cálculo analítico de autovalores.
     - **Series de Taylor y Aproximaciones:** Deslizador de orden $N$ y punto de expansión $x_0$.
     - **Espacio de Estados General:** Integrador Runge-Kutta 4, campo vectorial (quiver plot) y generación de partículas al hacer clic en el lienzo.
2. **Motor de Verificación Simbólica Formal con SymPy CAS (`cas_verifier.py`):**
   * Valida determinísticamente matrices, derivadas, autovalores, determinantes e identidades algebraicas utilizando SymPy 1.13.3 en el servidor.
   * Emite un **"Certificado de Validación Simbólica (SymPy CAS)"** adjunto al informe de auditoría y al documento Word `.docx`.
3. **Motor RAG Denso Vectorial Local (`rag_engine.py`):**
   * Segmentación semántica de PDFs y notas en ventanas deslizantes con solapamiento en `archivos_cargados/`.
   * Indexación vectorial con cálculo de similitud coseno $\cos(\theta)$ para recuperar los pasajes más relevantes y citarlos en el reporte.
4. **Tuneo Quirúrgico por Árbol Sintáctico (Markdown AST) (`refinement_engine.py`):**
   * Reemplazo robusto de secciones por árbol de nodos, inmune a variaciones de encabezados. Recompila Word al instante.
5. **Timeouts Optimizados:**
   * Timeout de Ollama ampliado a **120 segundos (2 min)** para máquinas con RAM moderada (configurable en `.env`).
   * Timeout de conexión rápida de claves API fijado en **3.0 segundos**.
6. **Compilación Continua de Documentos Word** (`.docx` con OMML 2D y `.doc` con MathML editable).

---

## Puesta en Marcha en Visual Studio Code

### 1. Iniciar el Servidor Local
En la terminal de PowerShell dentro de tu entorno virtual:
```powershell
python server.py
```
El servidor arrancará en `http://localhost:8000` y abrirá tu navegador web automáticamente.
