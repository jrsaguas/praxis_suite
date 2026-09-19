#!/usr/bin/env python3
# -*- coding: utf-8 -*
"""
PRAXIS INTERACTIVE SIMULATION DISPATCHER (v13.0)
Conecta la solicitud del ejercicio con el sintetizador dinámico Canvas HTML5.
"""

import sys
import os

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIRECTORY)

import canvas_synthesizer

def build_interactive_visualizer(title, topic_domain="", governing_eqs=""):
    """
    Agente Consultor y Sintetizador:
    Genera un simulador interactivo autónomo adaptado a las ecuaciones y dominio del problema.
    """
    return canvas_synthesizer.synthesize_canvas_simulator(
        title=title,
        prompt_text=topic_domain,
        governing_eqs=governing_eqs
    )

if __name__ == "__main__":
    test = build_interactive_visualizer("Sistema Caótico", "Atractor de Lorenz")
    print(f"[Interactive Engine v13] Simulador generado con éxito ({len(test)} bytes).")
