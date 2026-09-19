#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRAXIS DRAFT STUDIO (TALLER DE BORRADORES v10.0)
Permite trabajar con borradores modulares en segundo plano:
- Seleccionar, podar y combinar secciones de diferentes investigaciones.
- Exportar borradores consolidados a Word (.docx y .doc).
- Guardar la estructura personalizada como una nueva plantilla evolutiva de entrega.
"""

import os
import sys
import json
import datetime
import re

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_DIR = os.path.join(DIRECTORY, "historial")
DRAFTS_DIR = os.path.join(HISTORIAL_DIR, "borradores")
TEMPLATE_DIR = os.path.join(HISTORIAL_DIR, "plantillas")

for d in [DRAFTS_DIR, TEMPLATE_DIR]:
    os.makedirs(d, exist_ok=True)

sys.path.insert(0, DIRECTORY)
import convert

def list_drafts():
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    drafts = []
    for f in sorted(os.listdir(DRAFTS_DIR), reverse=True):
        if f.endswith('.json'):
            try:
                with open(os.path.join(DRAFTS_DIR, f), 'r', encoding='utf-8') as df:
                    drafts.append(json.load(df))
            except Exception: pass
    return drafts

def get_draft(draft_id):
    fpath = os.path.join(DRAFTS_DIR, f"{draft_id}.json")
    if not os.path.exists(fpath):
        return None
    with open(fpath, 'r', encoding='utf-8') as df:
        return json.load(df)

def save_draft(data):
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    draft_id = data.get('id')
    if not draft_id:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_t = re.sub(r'[^a-zA-Z0-9_\-]', '_', data.get('title', 'borrador'))[:30]
        draft_id = f"draft_{now_str}_{safe_t}"
        data['id'] = draft_id
        data['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data['updated_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fpath = os.path.join(DRAFTS_DIR, f"{draft_id}.json")
    with open(fpath, 'w', encoding='utf-8') as df:
        json.dump(data, df, ensure_ascii=False, indent=2)
    return data

def compile_draft_to_words(draft_id):
    draft = get_draft(draft_id)
    if not draft:
        raise ValueError("Borrador no encontrado")

    title = draft.get('title', 'Borrador Consolidado')
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:45]

    # Ensamblar Markdown desde las secciones seleccionadas
    sections = draft.get('sections', [])
    md_lines = [f"# {title}", ""]

    for sec in sections:
        sec_title = sec.get('title', '')
        sec_content = sec.get('content', '')
        if sec_title:
            md_lines.append(f"## {sec_title}")
            md_lines.append("")
        if sec_content:
            md_lines.append(sec_content)
            md_lines.append("")

    full_md = "\n".join(md_lines)
    tmp_md = os.path.join(DRAFTS_DIR, f"{safe_title}.md")
    tmp_docx = os.path.join(DRAFTS_DIR, f"{safe_title}.docx")
    tmp_doc = os.path.join(DRAFTS_DIR, f"{safe_title}.doc")

    with open(tmp_md, 'w', encoding='utf-8') as f:
        f.write(full_md)

    res = convert.convert_file_to_both_words(tmp_md, tmp_docx, tmp_doc, title=title)
    return {
        "status": "ok",
        "title": title,
        "md_path": tmp_md,
        "docx_path": tmp_docx,
        "doc_path": tmp_doc,
        "has_docx": res['docx'],
        "has_doc": res['doc']
    }

def save_draft_as_template(draft_id, template_name=None):
    draft = get_draft(draft_id)
    if not draft:
        raise ValueError("Borrador no encontrado")

    t_name = template_name or f"Plantilla basada en {draft.get('title', 'Borrador')}"
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', t_name)[:40]

    template_data = {
        "id": f"plantilla_usuario_{safe_name}",
        "nombre": t_name,
        "tipo": "plantilla_usuario",
        "creada_desde_borrador": draft_id,
        "secciones": [s.get('title') for s in draft.get('sections', []) if s.get('title')],
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    tpath = os.path.join(TEMPLATE_DIR, f"{template_data['id']}.json")
    with open(tpath, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, ensure_ascii=False, indent=2)

    return template_data

if __name__ == "__main__":
    print("[Draft Studio] Módulo de borradores inicializado.")
