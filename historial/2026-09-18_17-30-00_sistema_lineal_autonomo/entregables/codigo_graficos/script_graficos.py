import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt

# Retrato de fase del sistema lineal x' = y, y' = -x
Y, X = np.mgrid[-3:3:25j, -3:3:25j]
U = Y
V = -X

plt.figure(figsize=(7, 7), dpi=150)
plt.streamplot(X, Y, U, V, color=np.sqrt(U**2 + V**2), cmap='viridis', linewidth=1.2, arrowsize=1.2)
plt.plot(0, 0, 'ro', label='Centro (0,0)')
plt.title("Retrato de Fase: Centro Neutro Estable (Sentido Horario)")
plt.xlabel("x(t)")
plt.ylabel("y(t)")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("retrato_de_fase.png")
plt.close()
