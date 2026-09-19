# Investigación rigurosa del sistema lineal autónomo plano y clasificación espectral del origen

## 1. Estrategia y Planteamiento

La investigación rigurosa procede mediante la formulación matricial del sistema lineal autónomo de primer orden en el espacio euclidiano bidimensional $\mathbb{R}^2$, verificando el cumplimiento de las hipótesis del Teorema de Picard-Lindelöf para garantizar la existencia y unicidad global de las soluciones. Posteriormente, se realiza el análisis espectral de la matriz de coeficientes $A$, calculando su traza, determinante y su espectro en el campo complejo $\mathbb{C}$. Al obtener eigenvalores puramente imaginarios conjugados, se desarrolla la solución general utilizando la exponencial de matriz $e^{At}$ mediante expansión en serie de potencias y el teorema de Cayley-Hamilton. Finalmente, se eliminan los términos temporales para obtener la ecuación implícita de las órbitas en el plano fase, clasificando el punto crítico como un centro topológico.

### Supuestos Formales
* El campo vectorial asociado es globalmente Lipschitz continuo en $\mathbb{R}^2$, lo que satisface las hipótesis de existencia y unicidad de Picard-Lindelöf.
* El origen $(0,0)$ es el único punto de equilibrio del sistema debido a la nonsingularidad de la matriz de coeficientes $\det(A) \neq 0$.

### Nomenclatura y Notación
* $X(t)$: vector de estado en el espacio fase $\mathbb{R}^2$, definido como $\begin{pmatrix} x(t) \\ y(t) \end{pmatrix}$.
* $A$: matriz de coeficientes del sistema lineal autónomo, dada por $\begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}$.
* $\sigma(A)$: espectro de la matriz $A$, definido como el conjunto de sus eigenvalores en $\mathbb{C}$.
* $e^{At}$: exponencial de la matriz $A$, operador de evolución temporal que mapea el estado inicial $X_0$ al estado $X(t)$.

---

## 2. Desarrollo Paso a Paso

### Paso 1: Formulación Matricial del Sistema Lineal Autónomo
Dado el sistema de ecuaciones diferenciales ordinarias escalares acopladas $x' = y$ e $y' = -x$, el operador diferencial lineal puede expresarse en forma matricial compacta. Definimos el vector de estado $X(t) = \begin{pmatrix} x(t) \\ y(t) \end{pmatrix} \in \mathbb{R}^2$ y la matriz de coeficientes constantes $A = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix} \in \mathcal{M}_2(\mathbb{R})$. Por consiguiente, el sistema se reescribe como el problema de Cauchy homogéneo $X'(t) = AX(t)$. La linealidad del operador y la continuidad de las componentes garantizan el cumplimiento de las hipótesis del Teorema de Existencia y Unicidad de Picard-Lindelöf para cualquier condición inicial $X(0) = X_0 \in \mathbb{R}^2$ en todo el dominio temporal $t \in \mathbb{R}$.

$$\begin{pmatrix} x'(t) \\ y'(t) \end{pmatrix} = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix} \begin{pmatrix} x(t) \\ y(t) \end{pmatrix}$$

*Herramienta:* Teorema de Existencia y Unicidad de Picard-Lindelöf.

### Paso 2: Análisis Espectral y Polinómico de la Matriz de Coeficientes
Para determinar las soluciones fundamentales del sistema homogéneo, calculamos el espectro $\sigma(A)$ resolviendo la ecuación característica $\det(A - \lambda I) = 0$. Desarrollamos el determinante de la matriz paramétrica: $\det \begin{pmatrix} -\lambda & 1 \\ -1 & -\lambda \end{pmatrix} = (-\lambda)(-\lambda) - (1)(-1) = \lambda^2 + 1$. Igualando a cero, obtenemos el polinomio característico $p(\lambda) = \lambda^2 + 1 = 0$. Las raíces de este polinomio son los eigenvalores complejos conjugados $\lambda_1 = i$ y $\lambda_2 = -i$. La traza de la matriz es $\text{tr}(A) = 0$ y su determinante es $\det(A) = 1$, lo cual confirma la ausencia de disipación volumétrica en el espacio fase y anticipa una órbita conservativa.

$$\det(A - \lambda I) = \det \begin{pmatrix} -\lambda & 1 \\ -1 & -\lambda \end{pmatrix} = \lambda^2 + 1 = 0 \implies \lambda_{1,2} = \pm i$$

*Herramienta:* Polinomio Característico y Espectro Matricial.

### Paso 3: Construcción de la Exponencial de Matriz $e^{At}$
La solución general de un sistema lineal autónomo de primer orden se expresa formalmente mediante la exponencial de matriz $X(t) = e^{At}X_0$. Para calcular analíticamente $e^{At}$, utilizamos la serie de potencias definida por $e^{At} = \sum_{k=0}^{\infty} \frac{t^k A^k}{k!}$. Evaluamos las potencias sucesivas de la matriz $A$: $A^0 = I$, $A^1 = A$, $A^2 = -I$, $A^3 = -A$, $A^4 = I$, exhibiendo un comportamiento periódico de período $4$ en las potencias de $A$. Separamos la serie en términos pares e impares: los términos pares contienen potencias de $(-1)^n I$ y los impares contienen potencias de $(-1)^n A$. Reconocemos formalmente los desarrollos en serie de Taylor de las funciones trigonométricas reales $\cos(t)$ y $\sin(t)$.

$$e^{At} = \sum_{k=0}^{\infty} \frac{t^k A^k}{k!} = I \sum_{n=0}^{\infty} \frac{(-1)^n t^{2n}}{(2n)!} + A \sum_{n=0}^{\infty} \frac{(-1)^n t^{2n+1}}{(2n+1)!}$$

*Herramienta:* Teorema de Expansión en Serie y Fórmula de Euler para Matrices.

### Paso 4: Deducción de la Solución General Explícita
Sustituyendo los desarrollos en serie de las funciones trigonométricas y las matrices $I$ y $A$ obtenidas en el paso anterior, la matriz de evolución temporal $e^{At}$ se simplifica analíticamente a una combinación lineal de matrices trigonométricas. Multiplicando esta matriz por el vector de condiciones iniciales $X_0 = \begin{pmatrix} x_0 \\ y_0 \end{pmatrix}$, obtenemos las expresiones paramétricas explícitas para las coordenadas temporales $x(t)$ e $y(t)$. Cada componente del vector de estado queda expresada como una combinación lineal ortogonal de senos y cosenos del tiempo $t$, gobernada estrictamente por las condiciones iniciales impuestas en el origen temporal $t = 0$.

$$X(t) = \begin{pmatrix} \cos(t) & \sin(t) \\ -\sin(t) & \cos(t) \end{pmatrix} \begin{pmatrix} x_0 \\ y_0 \end{pmatrix} = \begin{pmatrix} x_0 \cos(t) + y_0 \sin(t) \\ -x_0 \sin(t) + y_0 \cos(t) \end{pmatrix}$$

*Herramienta:* Operador de Evolución Temporal $\Phi(t) = e^{At}$.

### Paso 5: Obtención de las Trayectorias en el Plano Fase
Para eliminar explícitamente el parámetro temporal $t$ y encontrar la ecuación cartesiana que describe las trayectorias integrales en el plano fase $\mathbb{R}^2$, elevamos al cuadrado y sumamos las expresiones componentes de la solución general $x(t)$ e $y(t)$. Desarrollamos algebraicamente los binomios trigonométricos resultantes y aplicamos la identidad trigonométrica fundamental $\cos^2(t) + \sin^2(t) = 1$. Obtenemos así la ecuación implícita $x^2(t) + y^2(t) = x_0^2 + y_0^2$. Esta ecuación representa una familia uniparamétrica de circunferencias concéntricas centradas en el origen con radio constante $R = \sqrt{x_0^2 + y_0^2}$, demostrando que las órbitas son cerradas, periódicas y estables en sentido orbital.

$$x(t)^2 + y(t)^2 = (x_0 \cos t + y_0 \sin t)^2 + (-x_0 \sin t + y_0 \cos t)^2 = x_0^2 + y_0^2 = R^2$$

*Herramienta:* Identidades Trigonométricas Fundamentales e Invariantes Cuadráticos.

### Paso 6: Clasificación Topológica del Punto Crítico en el Origen
Analizamos el comportamiento dinámico local del campo vectorial alrededor del único punto de equilibrio $X^* = (0,0)$. Dado que el espectro de la matriz $A$ consta de eigenvalores puros imaginarios conjugados $\sigma(A) = \pm i$, con parte real nula $\text{Re}(\lambda_i) = 0$, el equilibrio no es hiperbólico. Por lo tanto, el Teorema de Hartman-Grobman no garantiza directamente la estabilidad topológica mediante la linealización pura sin considerar términos no lineales de orden superior si existieran; sin embargo, para el sistema estrictamente lineal, las órbitas son curvas cerradas (circunferencias) recorridas en sentido horario debido a que $x' = y > 0$ cuando $x = 0$ e $y > 0$. Esto clasifica analíticamente al origen como un centro (o vórtice estable marginal).

$$\text{Re}(\lambda_{1,2}) = 0, \quad \text{tr}(A) = 0, \quad \det(A) > 0 \implies \text{Punto Crítico: Centro}$$

*Herramienta:* Clasificación Espectral de Lyapunov y Teoría de Estabilidad de Poincaré.

---

## 3. Marco Teórico Formal

### 3.1. Álgebra Lineal y Teoría de Matrices

> **Definición (Espacio Vectorial y Matriz Asociada):** Un espacio vectorial $(V, +, \cdot)$ sobre un cuerpo $K$ es un conjunto dotado de dos operaciones que satisfacen los axiomas de linealidad. Una transformación lineal $T: V \to V$ en dimensión finita se representa unívocamente mediante una matriz $A = (a_{ij}) \in M_{n \times n}(K)$ tal que $T(\mathbf{v}) = A\mathbf{v}$.
> **Demostración:** Sean $\mathbf{v} = \begin{pmatrix} v_1 \\ v_2 \end{pmatrix} \in \mathbb{R}^2$ y la transformación lineal $T(\mathbf{v}) = \begin{pmatrix} v_2 \\ -v_1 \end{pmatrix}$. Por definición de representación matricial, la columna $j$-ésima de la matriz $A$ es la imagen del $j$-ésimo vector de la base canónica $\{\mathbf{e}_1, \mathbf{e}_2\}$. Tenemos que $T(\mathbf{e}_1) = T\left(\begin{pmatrix} 1 \\ 0 \end{pmatrix}\right) = \begin{pmatrix} 0 \\ -1 \end{pmatrix}$ y $T(\mathbf{e}_2) = T\left(\begin{pmatrix} 0 \\ 1 \end{pmatrix}\right) = \begin{pmatrix} 1 \\ 0 \end{pmatrix}$. Por lo tanto, $A = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}$, demostrando la correspondencia unívoca. Q.E.D. ■

> **Teorema (Polinomio Característico y Espectro Matricial):** Sea $A \in M_{n \times n}(\mathbb{R})$. Los eigenvalores $\lambda \in \mathbb{C}$ de la matriz $A$ son las raíces del polinomio característico $p(\lambda) = \det(\lambda I - A) = 0$.
> **Demostración:** Partimos de la ecuación de eigenvalores $A\mathbf{v} = \lambda\mathbf{v}$ para un vector no nulo $\mathbf{v} \neq \mathbf{0}$, la cual se reescribe como $(\lambda I - A)\mathbf{v} = \mathbf{0}$. Para que esta ecuación homogénea admita soluciones no triviales $\mathbf{v}$, el operador lineal $\lambda I - A$ debe ser no invertible, lo cual es equivalente a que su determinante sea nulo: $\det(\lambda I - A) = 0$. Para $A = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}$, calculamos $\lambda I - A = \begin{pmatrix} \lambda & -1 \\ 1 & \lambda \end{pmatrix}$. Su determinante es $\det(\lambda I - A) = \lambda(\lambda) - (-1)(1) = \lambda^2 + 1$. Al igualar a cero obtenemos el polinomio característico $\lambda^2 + 1 = 0$, cuyas raíces son $\lambda = \pm i$. Q.E.D. ■

### 3.2. Teoría Cualitativa de Ecuaciones Diferenciales Ordinarias

> **Teorema (Teorema de Existencia y Unicidad de Picard-Lindelöf):** Sea $\mathbf{f}: \Omega \subset \mathbb{R} \times \mathbb{R}^n \to \mathbb{R}^n$ una función continua y Lipschitz continua respecto a su segundo argumento en un entorno del punto inicial $(t_0, \mathbf{X}_0)$. Entonces, existe un único intervalo $]t_0 - h, t_0 + h[$ y una única solución $\mathbf{X}(t)$ al problema de valor inicial $\mathbf{X}' = \mathbf{f}(t, \mathbf{X})$, $\mathbf{X}(t_0) = \mathbf{X}_0$.
> **Demostración:** Consideremos el campo vectorial lineal $\mathbf{f}(\mathbf{X}) = A\mathbf{X}$ donde $A = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}$. La norma de la función es $\|\mathbf{f}(\mathbf{X}_1) - \mathbf{f}(\mathbf{X}_2)\| = \|A(\mathbf{X}_1 - \mathbf{X}_2)\| \leq \|A\|_{\text{op}} \|\mathbf{X}_1 - \mathbf{X}_2\|$. Dado que la norma de operador $\|A\|_{\text{op}}$ es finita para cualquier matriz real, la función satisface la condición de Lipschitz global con constante $L = \|A\|_{\text{op}}$. Por el Teorema de Picard-Lindelöf mediante el operador de contracción de Banach en el espacio de Banach de funciones continuas, existe una única solución definida para todo $t \in \mathbb{R}$. Q.E.D. ■

> **Proposición (Clasificación Topológica del Centro Espectral):** Si la matriz $A$ de un sistema autónomo plano $\mathbf{X}' = A\mathbf{X}$ posee eigenvalores puros imaginarios conjugados $\lambda = \pm i\beta$ con $\beta \neq 0$, el origen es un centro topológico donde las trayectorias son elipses (o circunferencias) cerradas concéntricas.
> **Demostración:** Sean $\lambda = \pm i$ los eigenvalores de $A$. La solución general se expresa como combinación lineal de funciones seno y coseno: $x(t) = x_0 \cos(t) + y_0 \sin(t)$ e $y(t) = -x_0 \sin(t) + y_0 \cos(t)$. Elevando ambas ecuaciones al cuadrado y sumándolas, obtenemos $x(t)^2 + y(t)^2 = (x_0 \cos(t) + y_0 \sin(t))^2 + (-x_0 \sin(t) + y_0 \cos(t))^2 = x_0^2(\cos^2(t) + \sin^2(t)) + y_0^2(\sin^2(t) + \cos^2(t)) = x_0^2 + y_0^2 = R^2$. Esta ecuación representa una familia uniparamétrica de circunferencias concéntricas de radio constante $R$, probando que las órbitas son cerradas y periódicas. Q.E.D. ■

---

## 4. Investigaciones y Conclusiones

### Generalizaciones en Dimensión Arbitraria
Cualquier sistema lineal autónomo homogéneo en $\mathbb{R}^n$ se expresa como $X'(t) = AX(t)$, donde $A \in M_n(\mathbb{R})$. Si la matriz $A$ es antisimétrica, es decir, $A^T = -A$, el operador induce un flujo que preserva el producto interno euclidiano y, por consecuencia, el volumen en el espacio fase según el teorema de Liouville. Las soluciones se obtienen mediante la exponencial de matriz $X(t) = e^{At}X_0$. Cuando $A$ posee eigenvalores puramente imaginarios conjugados, el espacio fase se descompone en suma directa de planos bidimensionales invariantes donde el movimiento es periódico.

### Sistemas Hamiltonianos y Variedades Simplécticas
El sistema analizado es un caso particular de sistema hamiltoniano con la función de energía total (hamiltoniano) $H(x,y) = \frac{1}{2}(x^2 + y^2)$. Las ecuaciones del movimiento se rigen por las relaciones $\frac{dx}{dt} = \frac{\partial H}{\partial y}$ y $\frac{dy}{dt} = -\frac{\partial H}{\partial x}$. Esta estructura se generaliza a variedades simplécticas de dimensión $2n$, donde las coordenadas canónicas $(q, p)$ satisfacen las ecuaciones de Hamilton y preservan la forma simpléctica fundamental.

### Problemas Abiertos
¿Bajo qué condiciones precisas sobre el término perturbador $f(t, X)$, con $\|f(t, X)\| = o(\|X\|)$ cuando $\|X\| \to 0$, el centro estricto del sistema lineal se convierte en un foco asintóticamente estable, un foco inestable o un ciclo límite en sistemas bidimensionales no autónomos? El problema general de la estabilidad para centros no lineales (el décimo problema de Hilbert en su vertiente dinámica) sigue abierto para clases amplias de polinomios de grado superior.

---

## 5. Bibliografía

* Hirsch, M. W., Smale, S., & Devaney, R. L. *Differential Equations, Dynamical Systems, and an Introduction to Chaos*. Elsevier/Academic Press, 2012.
* Perko, L. *Differential Equations and Dynamical Systems*. Springer-Verlag, 2001.