"""Configuración central de Praxis.

Toda configuración operativa debe pasar por este módulo para evitar que
cada componente mantenga su propia copia de rutas, puertos y límites.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HISTORIAL_DIR = BASE_DIR / "historial"
CHATS_DIR = HISTORIAL_DIR / "chats"
TEMPLATE_DIR = HISTORIAL_DIR / "plantillas"
KNOWLEDGE_DIR = HISTORIAL_DIR / "base_conocimiento"

HOST = os.getenv("PRAXIS_HOST", "127.0.0.1")
PORT = int(os.getenv("PRAXIS_PORT", "8000"))
MAX_REQUEST_BYTES = int(os.getenv("PRAXIS_MAX_REQUEST_BYTES", str(25 * 1024 * 1024)))

ALLOWED_ORIGINS = frozenset({
    f"http://127.0.0.1:{PORT}",
    f"http://localhost:{PORT}",
})


def ensure_directories():
    for directory in (HISTORIAL_DIR, CHATS_DIR, TEMPLATE_DIR, KNOWLEDGE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
