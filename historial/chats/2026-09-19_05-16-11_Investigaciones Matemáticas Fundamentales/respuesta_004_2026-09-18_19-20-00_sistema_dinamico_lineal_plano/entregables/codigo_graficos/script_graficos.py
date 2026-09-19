import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt

theta = np.linspace(0, 2*np.pi, 200)
plt.figure(figsize=(6, 6), dpi=150)
for r in [0.5, 1.0, 1.5, 2.0, 2.5]:
    plt.plot(r*np.cos(theta), r*np.sin(theta), label=f'R = {r}')
plt.plot(0, 0, 'ko', label='Origen (Centro)')
plt.title("Órbitas Concéntricas Periódicas en el Plano Fase")
plt.xlabel("x")
plt.ylabel("y")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("orbitas_concentricas.png")
plt.close()
