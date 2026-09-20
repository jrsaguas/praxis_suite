#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilities for safe filesystem components used by the local Praxis server."""

import os
import re

_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,119}$")


def validate_component(value, field_name="component"):
    """Validate a single path component; reject traversal and separators."""
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise ValueError(f"{field_name} inválido")
    if not _COMPONENT_RE.fullmatch(value):
        raise ValueError(f"{field_name} contiene caracteres no permitidos")
    return value


def safe_filename(filename):
    """Return a basename-only filename safe for storage below the upload directory."""
    if not isinstance(filename, str) or not filename:
        raise ValueError("filename inválido")
    base = os.path.basename(filename.replace("\\", "/"))
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")
    if not base:
        raise ValueError("filename inválido")
    return base[:180]


def safe_child_path(root, *components):
    """Resolve a path and guarantee it remains below root."""
    root_abs = os.path.abspath(root)
    path = root_abs
    for component in components:
        component = validate_component(component, "path_component")
        path = os.path.join(path, component)
    path_abs = os.path.abspath(path)
    if os.path.commonpath([root_abs, path_abs]) != root_abs:
        raise ValueError("Ruta fuera del directorio permitido")
    return path_abs
