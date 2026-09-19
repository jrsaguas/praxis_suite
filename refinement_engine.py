#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRAXIS AST DIRECTED REFINEMENT ENGINE (v13.0)
Analizador sintáctico de árbol (Markdown AST) para tuneo quirúrgico de secciones.
Elimina la fragilidad de las expresiones regulares: descompone el documento en
un árbol de nodos jerárquicos (H1, H2, H3), localiza semánticamente la sección deseada
y reemplaza su contenido preservando la integridad del documento.
"""

import os
import re
import json
import glob
import datetime

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CHATS_DIR = os.path.join(DIRECTORY, "historial", "chats")

import convert

class MarkdownNode:
    def __init__(self, level, header_line, title):
        self.level = level
        self.header_line = header_line
        self.title = title
        self.content_lines = []

def parse_markdown_ast(markdown_text):
    """Parsea el texto Markdown en una lista de nodos de encabezados jerárquicos"""
    lines = markdown_text.splitlines()
    nodes = []
    current_node = MarkdownNode(0, "", "Preámbulo")

    for line in lines:
        h_match = re.match(r'^(#{1,6})\s+(.*)$', line)
        if h_match:
            nodes.append(current_node)
            level = len(h_match.group(1))
            title = h_match.group(2).strip()
            current_node = MarkdownNode(level, line, title)
        else:
            current_node.content_lines.append(line)

    nodes.append(current_node)
    return nodes

def serialize_markdown_ast(nodes):
    """Reconstruye el documento Markdown a partir de los nodos AST"""
    out_lines = []
    for n in nodes:
        if n.header_line:
            out_lines.append(n.header_line)
        if n.content_lines:
            out_lines.extend(n.content_lines)
    return "\n".join(out_lines).strip() + "\n"

def match_target_section(node_title, target_intent):
    """Evalúa si un título de nodo corresponde a la sección que se desea tunear"""
    t_low = (node_title or "").lower()
    tgt = (target_intent or "").lower()

    synonyms = {
        'estrategia': ['estrategia', 'plan', 'planteamiento', 'hipotesis', 'supuestos'],
        'desarrollo': ['desarrollo', 'resolucion', 'paso a paso', 'deduccion', 'derivacion'],
        'teoria': ['teoria', 'marco teorico', 'teorema', 'definicion', 'lemas'],
        'modelacion': ['modelacion', 'modelo', 'sistemas complejos', 'ecuaciones de gobierno', 'estado'],
        'figuras': ['figuras', 'visualizacion', 'graficos', 'ilustracion'],
        'simulador': ['simulador', 'canvas', 'laboratorio interactivo'],
        'investigacion': ['investigacion', 'extension', 'generalizacion', 'literatura', 'bibliografia']
    }

    # Búsqueda de coincidencia directa o por sinónimos
    if tgt in t_low:
        return True
    for syn_key, words in synonyms.items():
        if syn_key in tgt:
            if any(w in t_low for w in words):
                return True
    return False


def refine_section_ast(markdown_text, section_target, new_content):
    """
    Sustitución quirúrgica basada en AST:
    Localiza el nodo semántico correspondiente y reemplaza su cuerpo con new_content.
    """
    if not markdown_text:
        return f"# Investigación Refinada\n\n## {section_target.capitalize()}\n\n{new_content}\n"

    nodes = parse_markdown_ast(markdown_text)
    matched = False

    for n in nodes:
        if n.level > 0 and match_target_section(n.title, section_target):
            # Preservar el encabezado original y reemplazar su contenido con el texto refinado
            n.content_lines = ["", new_content.strip(), ""]
            matched = True
            break

    if not matched:
        # Si no coincidió ningún nodo, insertar una nueva sección H2 con el contenido refinado
        new_node = MarkdownNode(2, f"## Sección Actualizada: {section_target.capitalize()}", section_target.capitalize())
        new_node.content_lines = ["", new_content.strip(), ""]
        nodes.append(new_node)

    return serialize_markdown_ast(nodes)


def apply_refinement_to_saved_response(chat_id, folder_name, section_target, new_content, prompt_note=""):
    """
    Aplica el refinamiento AST sobre los archivos físicos del chat y recompila el Word.
    """
    chat_dir = os.path.join(CHATS_DIR, chat_id)
    resp_path = os.path.join(chat_dir, folder_name)
    if not os.path.exists(resp_path):
        return {"status": "error", "message": "No se encontró la investigación en el chat."}

    doc_dir = os.path.join(resp_path, "entregables", "documentos")
    md_files = glob.glob(os.path.join(doc_dir, "*.md"))
    if not md_files:
        return {"status": "error", "message": "No se encontró el archivo Markdown base."}

    md_file = md_files[0]
    with open(md_file, "r", encoding="utf-8") as f:
        current_md = f.read()

    # Refinamiento quirúrgico mediante AST
    updated_md = refine_section_ast(current_md, section_target, new_content)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(updated_md)

    title = os.path.splitext(os.path.basename(md_file))[0]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:45].strip('_')
    docx_path = os.path.join(doc_dir, f"{safe_title}.docx")
    doc_path = os.path.join(doc_dir, f"{safe_title}.doc")

    # Recompilar Word (.docx con OMML 2D y .doc con MathML)
    conv_res = convert.convert_file_to_both_words(md_file, docx_path, doc_path, title=title)

    # Registrar en el informe de auditoría
    traces_file = os.path.join(resp_path, "proceso_agentes", "trazas_agentes.json")
    if os.path.exists(traces_file):
        try:
            with open(traces_file, "r", encoding="utf-8") as tf:
                traces = json.load(tf)
            traces.setdefault("refinamientos_ast", []).append({
                "seccion": section_target,
                "nota": prompt_note,
                "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            with open(traces_file, "w", encoding="utf-8") as tf:
                json.dump(traces, tf, ensure_ascii=False, indent=2)
        except Exception: pass

    rel_base = f"/historial/chats/{chat_id}/{folder_name}/entregables"
    return {
        "status": "ok",
        "chat_id": chat_id,
        "folder": folder_name,
        "section_refined": section_target,
        "markdown": updated_md,
        "docx_url": f"{rel_base}/documentos/{os.path.basename(docx_path)}",
        "doc_url": f"{rel_base}/documentos/{os.path.basename(doc_path)}",
        "has_docx": conv_res["docx"],
        "has_doc": conv_res["doc"]
    }

if __name__ == "__main__":
    sample_md = "# Titulo\n\n## 1. Estrategia\nVieja estrategia.\n\n## 2. Desarrollo Paso a Paso\nViejo desarrollo.\n"
    res_ast = refine_section_ast(sample_md, "desarrollo", "NUEVO DESARROLLO SIN ATAJOS.")
    print("[Refinement AST Engine v13] Prueba de tuneo AST exitosa:\n", res_ast)
