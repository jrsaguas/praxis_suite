"""Controlled executor for natural-language edits to an existing investigation.

The executor deliberately reuses Praxis' existing artifact engines and the
existing response folder. It never creates a parallel investigation hierarchy
and it never sends an artifact command back through the mathematical pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import glob
import os
import re
import subprocess
import sys
from typing import Any, Dict, List

import convert
import interactive_engine
import refinement_engine
from security_utils import validate_component, safe_child_path


@dataclass(frozen=True)
class ArtifactCommandPlan:
    operation: str
    instruction: str
    confidence: float
    reason: str
    allowed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactExecutionResult:
    status: str
    operation: str
    message: str
    changed_files: List[str]
    artifact_types: List[str]
    plan: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_artifact_command(instruction: str) -> ArtifactCommandPlan:
    text = str(instruction or "").strip()
    low = text.lower()

    if not text:
        return ArtifactCommandPlan("unknown", text, 0.0, "Instrucción vacía", False)

    if re.search(r"\b(canvas|simulador|visualizador)\b", low):
        if re.search(r"\b(fix|corrige|correg|arregla|repara|reconstruye|regenera|actualiza)\b", low):
            return ArtifactCommandPlan("repair_canvas", text, 0.95, "Orden explícita sobre el Canvas existente")
        if re.search(r"\b(otro|otra|nuevo|nueva|genera|crea|añade|agrega|más|adicional)\b", low):
            return ArtifactCommandPlan("generate_canvas", text, 0.95, "Orden explícita para generar Canvas")

    if re.search(r"\b(figura|figuras|imagen|imágenes|graficos|gráficos)\b", low):
        if re.search(r"\b(genera|crea|añade|agrega|más|otra|otro|regenera|actualiza)\b", low):
            return ArtifactCommandPlan("regenerate_figures", text, 0.90, "Orden para reutilizar el generador de figuras del informe")

    if re.search(r"\b(word|docx|documento|markdown|md|html)\b", low):
        if re.search(r"\b(regenera|actualiza|recompila|reconstruye|corrige|arregla|genera)\b", low):
            return ArtifactCommandPlan("rebuild_documents", text, 0.88, "Orden para recompilar salidas desde Markdown")

    if re.search(r"\b(sección|seccion|desarrollo|teoría|teoria|demostración|demostracion|modelación|modelacion)\b", low):
        if re.search(r"\b(modifica|actualiza|refina|afila|profundiza|amplía|amplia|corrige|cambia)\b", low):
            return ArtifactCommandPlan("refine_section", text, 0.84, "Orden de refinamiento de una sección")

    return ArtifactCommandPlan(
        "unknown",
        text,
        0.20,
        "No existe una operación segura suficientemente determinada",
        False,
    )


def _response_path(chats_dir: str, chat_id: str, folder: str) -> str:
    chat_id = validate_component(chat_id, "chat_id")
    folder = validate_component(folder, "folder")
    return safe_child_path(safe_child_path(chats_dir, chat_id), folder)


def _document_paths(response_path: str):
    doc_dir = os.path.join(response_path, "entregables", "documentos")
    md_files = glob.glob(os.path.join(doc_dir, "*.md"))
    if not md_files:
        raise FileNotFoundError("No se encontró Markdown canónico en la investigación.")
    md_file = md_files[0]
    base = os.path.splitext(os.path.basename(md_file))[0]
    return (
        doc_dir,
        md_file,
        os.path.join(doc_dir, base + ".docx"),
        os.path.join(doc_dir, base + ".doc"),
    )


def _rebuild_documents(response_path: str) -> List[str]:
    _, md_file, docx_file, doc_file = _document_paths(response_path)
    result = convert.convert_file_to_both_words(md_file, docx_file, doc_file, title=os.path.splitext(os.path.basename(md_file))[0])
    changed = [md_file]
    if result.get("docx") and os.path.exists(docx_file):
        changed.append(docx_file)
    if result.get("doc") and os.path.exists(doc_file):
        changed.append(doc_file)
    return changed


def _run_existing_figure_script(response_path: str) -> List[str]:
    code_dir = os.path.join(response_path, "entregables", "codigo_graficos")
    img_dir = os.path.join(response_path, "entregables", "imagenes")
    scripts = glob.glob(os.path.join(code_dir, "*.py"))
    if not scripts:
        raise FileNotFoundError("No existe un script Python de figuras reutilizable.")

    os.makedirs(img_dir, exist_ok=True)
    script = scripts[0]
    proc = subprocess.run(
        [sys.executable, script],
        cwd=img_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "error desconocido").strip()[-1200:]
        raise RuntimeError("El generador de figuras falló: " + detail)

    return sorted(
        os.path.join(img_dir, name)
        for name in os.listdir(img_dir)
        if os.path.isfile(os.path.join(img_dir, name))
    )


def _write_canvas(response_path: str, title: str, instruction: str) -> str:
    sim_dir = os.path.join(response_path, "entregables", "visualizador_interactivo")
    os.makedirs(sim_dir, exist_ok=True)
    # Reuse the existing synthesizer. The instruction becomes domain context;
    # no new agent or parallel artifact tree is introduced.
    html = interactive_engine.build_interactive_visualizer(title, instruction)
    path = os.path.join(sim_dir, "simulador.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


def execute_artifact_command(
    chats_dir: str,
    chat_id: str,
    folder: str,
    instruction: str,
    *,
    title: str = "",
) -> Dict[str, Any]:
    plan = classify_artifact_command(instruction)
    if not plan.allowed:
        return ArtifactExecutionResult(
            "rejected", plan.operation, plan.reason, [], [], plan.to_dict()
        ).to_dict()

    response_path = _response_path(chats_dir, chat_id, folder)
    if not os.path.isdir(response_path):
        raise FileNotFoundError("No se encontró la carpeta de la investigación.")

    changed: List[str] = []
    types: List[str] = []

    if plan.operation in ("generate_canvas", "repair_canvas"):
        changed.append(_write_canvas(response_path, title or folder, instruction))
        types.append("simulador")

    elif plan.operation == "regenerate_figures":
        changed.extend(_run_existing_figure_script(response_path))
        types.append("imagenes")

    elif plan.operation == "rebuild_documents":
        changed.extend(_rebuild_documents(response_path))
        types.extend(["md", "docx", "doc"])

    elif plan.operation == "refine_section":
        # This operation requires an explicit section target. We only execute
        # when the command names one, avoiding destructive guesses.
        match = re.search(
            r"\b(sección|seccion)\s+(?:de\s+)?([a-záéíóúñ][a-záéíóúñ0-9 _-]{2,60})",
            instruction,
            re.I,
        )
        if not match:
            return ArtifactExecutionResult(
                "rejected",
                plan.operation,
                "Indica la sección que deseas modificar.",
                [],
                [],
                plan.to_dict(),
            ).to_dict()
        target = match.group(2).strip(" .,:;")
        _, md_file, _, _ = _document_paths(response_path)
        with open(md_file, "r", encoding="utf-8") as fh:
            current = fh.read()
        # The existing directed-refinement endpoint remains the semantic writer;
        # this command executor intentionally does not invent new text itself.
        result = refinement_engine.apply_refinement_to_saved_response(
            chat_id, folder, target, instruction, "artifact-command"
        )
        if result.get("status") != "ok":
            raise RuntimeError(result.get("message", "No se pudo refinar la sección."))
        changed.append(md_file)
        types.extend(["md", "docx", "doc"])

    return ArtifactExecutionResult(
        "ok",
        plan.operation,
        "Artefacto actualizado correctamente.",
        changed,
        types,
        plan.to_dict(),
    ).to_dict()
