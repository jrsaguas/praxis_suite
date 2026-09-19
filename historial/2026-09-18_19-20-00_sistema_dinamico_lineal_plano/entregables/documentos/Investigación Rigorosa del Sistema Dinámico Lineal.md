# Investigación Rigorosa del Sistema Dinámico Lineal Plano: $X' = A X$

## 1. Estrategia
La estrategia analítica consiste en reformular el problema clásico como un sistema dinámico lineal en espacios de Banach y aplicar la teoría espectral. Primero, calcularemos el polinomio característico de la matriz $A$ para obtener su espectro $\sigma(A)$. A continuación, dado que $A$ carece de valores propios reales, utilizaremos la exponencial matricial $e^{At}$ mediante la fórmula de Euler para matrices, aprovechando que $A^2 = -I$. Derivaremos la solución general explícita, analizaremos las integrales primas del movimiento para demostrar que las trayectorias son circunferencias concéntricas, y finalmente aplicaremos la teoría de Lyapunov para clasificar el origen como un centro neutro estables en el sentido de Lyapunov pero no asintóticamente estable.

### Resultado analítico obtenido:
$$X(t) = \begin{pmatrix} \cos(t) & \sin(t) \\ -\sin(t) & \cos(t) \end{pmatrix} X_0, \quad x^2 + y^2 = R^2$$

### Verificación analítica:
Sustituyendo en las EDOs originales: $\frac{d}{dt}[x(t)] = y(t)$ y $\frac{d}{dt}[y(t)] = -x(t)$, verificando idénticamente el sistema. La derivada de la función de Lyapunov da cero, confirmando órbitas cerradas.

---

## 2. Marco Teórico
- **Definición: Exponencial de una Matriz:** $e^{A} = \sum_{k=0}^{\infty} \frac{A^k}{k!}$.
- **Teorema: Cayley-Hamilton:** $A^2 - \text{tr}(A)A + \det(A)I = 0 \implies A^2 = -I$.
- **Definición: Centro Lineal:** $\sigma(A) = \{\pm i\beta\}$. Órbitas periódicas cerradas.
- **Teorema: Estabilidad de Lyapunov:** $V(x,y) = \frac{1}{2}(x^2+y^2), \dot{V} \equiv 0$.
- **Teorema: Liouville:** Flujo conservativo con $\nabla \cdot F = 0$.

---

## 3. Generalizaciones
Sistemas lineales en $\mathbb{R}^n$, forma canónica de Jordan y mecánica hamiltoniana en variedades simplécticas con $\iota_{X_H} \omega = dH$.