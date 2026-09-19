import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.figure(figsize=(6, 3), dpi=150)
plt.plot([0, 1], [0, 0], 'r--', label='Función nula f(x)=0')
plt.title("Espacio Nulo de Soluciones")
plt.legend()
plt.tight_layout()
plt.savefig("espacio_nulo.png")
plt.close()
