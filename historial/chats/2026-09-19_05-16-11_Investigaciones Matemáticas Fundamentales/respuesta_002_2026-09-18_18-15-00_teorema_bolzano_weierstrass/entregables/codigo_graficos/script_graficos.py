import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt

k = np.arange(1, 100)
x_k = np.cos(k)  # Sucesión acotada en [-1, 1]

plt.figure(figsize=(8, 4.5), dpi=150)
plt.plot(k, x_k, 'o-', color='#1a73e8', markersize=3, alpha=0.7, label='x_k = cos(k)')
plt.axhline(0, color='gray', linestyle='--', alpha=0.5)
plt.title("Sucesión Acotada en R y Acumulación Secuencial")
plt.xlabel("Índice k")
plt.ylabel("Valor x_k")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("sucesion_bolzano.png")
plt.close()
