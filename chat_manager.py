import cas_verifier
import re
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRAXIS MULTI-CHAT MANAGER & INTER-CHAT EPISTEMIC BRIDGE (v10.0)
Gestiona la jerarquía de conversaciones:
historial/chats/[id_chat]/[respuestas]/
Permite la navegación lateral sin regenerar, el autoguardado estructurado
y la recuperación automatizada de teoremas/datos entre conversaciones distintas.
"""

import os
import sys
import json
import glob
import datetime
import subprocess

from security_utils import validate_component, safe_filename, safe_child_path

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_DIR = os.path.join(DIRECTORY, "historial")
CHATS_DIR = os.path.join(HISTORIAL_DIR, "chats")

os.makedirs(CHATS_DIR, exist_ok=True)

# Importar motores auxiliares
sys.path.insert(0, DIRECTORY)
import convert
import knowledge_engine
import process_reporter
import interactive_engine

def list_chats():
    """Devuelve la lista de conversaciones ordenadas cronológicamente"""
    os.makedirs(CHATS_DIR, exist_ok=True)
    chats = []
    for entry in sorted(os.listdir(CHATS_DIR), reverse=True):
        chat_path = os.path.join(CHATS_DIR, entry)
        if not os.path.isdir(chat_path): continue
        meta_file = os.path.join(chat_path, "conversacion_metadata.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    chats.append(meta)
                    continue
            except Exception:
                pass
        # Fallback si no tiene metadata
        chats.append({
            "id": entry,
            "title": entry.replace("_", " "),
            "created_at": "N/A",
            "updated_at": "N/A",
            "total_responses": len([d for d in os.listdir(chat_path) if d.startswith("respuesta_")]),
            "responses": []
        })
    return chats

def create_chat(title="Nueva Conversación"):
    """Crea una nueva conversación independiente en historial/chats/"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_title = re.sub(r"[^a-zA-Z0-9_\-]", "_", title)[:45].strip("_")
    chat_id = f"{now_str}_{safe_title}"
    chat_dir = os.path.join(CHATS_DIR, chat_id)
    os.makedirs(chat_dir, exist_ok=True)

    meta = {
        "id": chat_id,
        "title": title,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_responses": 0,
        "responses": []
    }
    with open(os.path.join(chat_dir, "conversacion_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta

def get_chat(chat_id):
    """Carga los mensajes y entregables de una conversación específica"""
    chat_id = validate_component(chat_id, "chat_id")
    chat_dir = safe_child_path(CHATS_DIR, chat_id)
    meta_file = os.path.join(chat_dir, "conversacion_metadata.json")
    if not os.path.exists(meta_file):
        return None
    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Enriquecer respuestas con estado de archivos
    for resp in meta.get("responses", []):
        r_folder = os.path.join(chat_dir, resp["folder"])
        if os.path.exists(r_folder):
            doc_dir = os.path.join(r_folder, "entregables", "documentos")
            sim_dir = os.path.join(r_folder, "entregables", "visualizador_interactivo")
            resp["has_docx"] = len(glob.glob(os.path.join(doc_dir, "*.docx"))) > 0
            resp["has_doc"] = len(glob.glob(os.path.join(doc_dir, "*.doc"))) > 0
            resp["has_sim"] = os.path.exists(os.path.join(sim_dir, "simulador.html"))

    return meta

def save_response_to_chat(chat_id, data):
    """
    Guarda una respuesta dentro de una conversación específica con estructura:
    entregables/ (documentos, imagenes, codigo_graficos, visualizador_interactivo)
    proceso_agentes/ (informe_proceso.md, .html, trazas.json)
    """
    title = data.get('title', 'Investigacion_Matematica').strip()
    prompt = data.get('prompt', '').strip()
    markdown = data.get('markdown', '')
    html = data.get('html', '')
    python_code = data.get('python_code', '')
    svgs = data.get('svgs', [])
    traces = data.get('traces', {})
    strategy_context = data.get('strategy_context') or {}

    # Si no se envía chat_id válido, crear o usar el más reciente
    if not chat_id or not os.path.exists(os.path.join(CHATS_DIR, chat_id)):
        all_c = list_chats()
        if all_c:
            chat_id = all_c[0]["id"]
        else:
            new_c = create_chat(f"Investigación {title[:30]}")
            chat_id = new_c["id"]

    chat_id = validate_component(chat_id, "chat_id")
    chat_dir = safe_child_path(CHATS_DIR, chat_id)
    meta_file = os.path.join(chat_dir, "conversacion_metadata.json")
    meta = {}
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception: pass

    resp_num = meta.get("total_responses", 0) + 1
    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_title = re.sub(r"[^a-zA-Z0-9_\-]", "_", title)[:45].strip("_")
    resp_folder = f"respuesta_{resp_num:03d}_{now_str}_{safe_title}"
    resp_path = os.path.join(chat_dir, resp_folder)

    entregables_dir = os.path.join(resp_path, "entregables")
    doc_dir = os.path.join(entregables_dir, "documentos")
    img_dir = os.path.join(entregables_dir, "imagenes")
    code_dir = os.path.join(entregables_dir, "codigo_graficos")
    sim_dir = os.path.join(entregables_dir, "visualizador_interactivo")
    process_dir = os.path.join(resp_path, "proceso_agentes")

    for d in [doc_dir, img_dir, code_dir, sim_dir, process_dir]:
        os.makedirs(d, exist_ok=True)

    # 1. Generar simulador interactivo autónomo
    sim_html = interactive_engine.build_interactive_visualizer(title, prompt)
    sim_file = os.path.join(sim_dir, "simulador.html")
    with open(sim_file, "w", encoding="utf-8") as sf:
        sf.write(sim_html)

    # 2. Agregar Anexo de Código del Simulador en Markdown antes de compilar
    annex_code = f"\n\n---\n\n## Anexo: Código Fuente del Visualizador Matemático Interactivo (Canvas HTML5)\n\nEl siguiente código genera el simulador interactivo autónomo con deslizadores paramétricos:\n\n```html\n{sim_html}\n```\n"
    if "## Anexo: Código Fuente del Visualizador" not in markdown:
        full_md = markdown + annex_code
    else:
        full_md = markdown

    # Guardar Markdown e HTML
    md_path = os.path.join(doc_dir, f"{safe_title}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_md)

    html_path = os.path.join(doc_dir, f"{safe_title}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 3. Compilar Word (.docx y .doc) con soporte de OMML 2D y MathML
    docx_path = os.path.join(doc_dir, f"{safe_title}.docx")
    doc_path = os.path.join(doc_dir, f"{safe_title}.doc")
    convert_res = convert.convert_file_to_both_words(md_path, docx_path, doc_path, title=title)

    # 4. Código Python e imágenes de gráficos
    if python_code:
        py_path = os.path.join(code_dir, "script_graficos.py")
        clean_py = python_code
        if "matplotlib.use" not in clean_py:
            clean_py = "import matplotlib\nmatplotlib.use('Agg')\n" + clean_py
        with open(py_path, "w", encoding="utf-8") as pf:
            pf.write(clean_py)
        try:
            subprocess.run([sys.executable, py_path], cwd=img_dir, capture_output=True, timeout=12)
        except Exception as e:
            print("[Chat Manager Warning] Ejecución script gráficos:", e)

    # Guardar SVGs
    for idx, svg_item in enumerate(svgs):
        svg_code = svg_item if isinstance(svg_item, str) else svg_item.get('svg', '')
        if svg_code:
            with open(os.path.join(img_dir, f"figura_{idx+1}.svg"), "w", encoding="utf-8") as sf:
                sf.write(svg_code)

    # 4.5 Certificación Simbólica Formal con SymPy (CAS)
    resolver_data = data.get('resolver') or {}
    cas_cert = cas_verifier.verify_mathematical_derivation(
        steps=resolver_data.get('pasos', []),
        final_result=resolver_data.get('resultado', ''),
        user_prompt=prompt
    )
    data['cas_certificate'] = cas_cert

    # Añadir sección de Certificación CAS al final del Markdown si no está presente
    if "### Certificado de Validación Simbólica (SymPy CAS)" not in full_md:
        cas_md = f"\n\n---\n\n### Certificado de Validación Simbólica (SymPy CAS)\n\n" \
                 f"**Estado:** `{cas_cert.get('estado_global', 'CERTIFICADO')}`  \n" \
                 f"**Motor:** {cas_cert.get('modulo', 'SymPy 1.13.3')}  \n" \
                 f"**Validaciones ejecutadas:** {cas_cert.get('total_validaciones', 0)}  \n\n"
        for reg in cas_cert.get('registros', []):
            cas_md += f"* **{reg.get('tipo', 'Operación')}:** {reg.get('operacion', '')}  \n" \
                      f"  > *Resultado CAS:* `{reg.get('resultado_cas', '')}` ({reg.get('estado', '')})\n"
        cas_md += f"\n> *Nota de auditoría formal:* {cas_cert.get('nota_certificacion', '')}\n"
        full_md += cas_md
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(full_md)
        # Recompilar Word con el anexo CAS
        convert.convert_file_to_both_words(md_path, docx_path, doc_path, title=title)

    # 5. Generar informe de auditoría de agentes
    process_reporter.generate_process_report(
        folder_path=process_dir,
        user_prompt=prompt,
        title=title,
        traces=traces,
        run_data=data
    )

    # 6. Actualizar Base de Conocimiento Unificada
    knowledge_engine.process_investigation_run(
        run_data=data,
        investigation_id=f"{chat_id}/{resp_folder}",
        investigation_title=title
    )

    # 7. Actualizar metadata del chat
    # 7.1 Identidad de investigación/versionado lógico.
    # Se apoya en la carpeta existente: no crea una jerarquía paralela.
    from investigation_model import InvestigationVersion, slug_investigation_id
    investigation_id = slug_investigation_id(chat_id, resp_folder)
    version = InvestigationVersion.create(
        investigation_id=investigation_id,
        prompt=prompt,
        title=title,
        response_folder=resp_folder,
        source="pipeline",
        artifact_types=["md", "html", "docx", "doc", "simulador", "proceso_agentes"],
        strategy_context=strategy_context,
    )

    resp_entry = {
        "folder": resp_folder,
        "title": title,
        "prompt": prompt,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "docx_filename": f"{safe_title}.docx",
        "doc_filename": f"{safe_title}.doc",
        "sim_filename": "simulador.html",
        "markdown_snippet": markdown[:300] + "...",
        "investigation_id": investigation_id,
        "version_id": version.version_id,
        "parent_version_id": version.parent_version_id,
        "version_source": version.source,
        "artifact_types": version.artifact_types,
        "evaluation": None,
        "strategy_context": strategy_context,
    }
    meta["updated_at"] = resp_entry["timestamp"]
    meta["total_responses"] = resp_num
    meta.setdefault("responses", []).append(resp_entry)

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "chat_id": chat_id,
        "response_folder": resp_folder,
        "folder_name": resp_folder,
        "docx_path": docx_path,
        "doc_path": doc_path,
        "sim_path": sim_file,
        "has_docx": convert_res["docx"],
        "has_doc": convert_res["doc"]
    }

def query_inter_chats(query_text, exclude_chat_id=None):
    """
    Agente Puente Epistémico:
    Busca semánticamente en todas las demás conversaciones para recuperar
    definiciones, teoremas o conclusiones previas y enriquecer el análisis actual.
    """
    if not query_text: return []
    os.makedirs(CHATS_DIR, exist_ok=True)
    q_norm = query_text.lower().split()
    results = []

    for c in list_chats():
        cid = c.get("id")
        if exclude_chat_id and cid == exclude_chat_id: continue
        c_title = c.get("title", "")
        
        chat_dir = os.path.join(CHATS_DIR, cid)
        meta_file = os.path.join(chat_dir, "conversacion_metadata.json")
        if not os.path.exists(meta_file): continue
        
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception: continue

        for resp in meta.get("responses", []):
            score = 0
            text_corpus = (c_title + " " + resp.get("title", "") + " " + resp.get("prompt", "")).lower()
            for word in q_norm:
                if len(word) >= 4 and word in text_corpus:
                    score += 2
            
            if score > 0:
                results.append({
                    "chat_id": cid,
                    "chat_title": c_title,
                    "response_title": resp.get("title"),
                    "prompt": resp.get("prompt"),
                    "timestamp": resp.get("timestamp"),
                    "score": score
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]

if __name__ == "__main__":
    print("[Chat Manager] Módulo de chats inicializado. Chats activos:", len(list_chats()))

# ============================================================
# CHECKPOINTS, TOLERANCIA A FALLOS Y RECUPERACIÓN DE ESTADO
# ============================================================

def save_checkpoint(chat_id, checkpoint_data):
    """Guarda el estado de ejecución de un pipeline interrumpido o en progreso."""
    if not chat_id: return None
    chat_id = validate_component(chat_id, "chat_id")
    chat_dir = safe_child_path(CHATS_DIR, chat_id)
    os.makedirs(chat_dir, exist_ok=True)
    cp_file = os.path.join(chat_dir, "checkpoint.json")
    checkpoint_data["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(cp_file, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "chat_id": chat_id, "checkpoint": checkpoint_data}

def get_checkpoint(chat_id):
    """Obtiene el último checkpoint registrado para el chat."""
    if not chat_id: return None
    chat_id = validate_component(chat_id, "chat_id")
    cp_file = os.path.join(safe_child_path(CHATS_DIR, chat_id), "checkpoint.json")
    if not os.path.exists(cp_file): return None
    try:
        with open(cp_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def clear_checkpoint(chat_id):
    """Elimina el checkpoint tras completar el flujo exitosamente."""
    if not chat_id: return
    chat_id = validate_component(chat_id, "chat_id")
    cp_file = os.path.join(safe_child_path(CHATS_DIR, chat_id), "checkpoint.json")
    if os.path.exists(cp_file):
        try: os.remove(cp_file)
        except Exception: pass

def get_response_detail(chat_id, folder_name):
    """Obtiene el contenido completo (HTML, MD, rutas) de una investigación pasada."""
    chat_id = validate_component(chat_id, "chat_id")
    folder_name = validate_component(folder_name, "folder_name")
    chat_dir = safe_child_path(CHATS_DIR, chat_id)
    resp_path = safe_child_path(chat_dir, folder_name)
    if not os.path.exists(resp_path): return None

    doc_dir = os.path.join(resp_path, "entregables", "documentos")
    sim_dir = os.path.join(resp_path, "entregables", "visualizador_interactivo")
    proc_dir = os.path.join(resp_path, "proceso_agentes")

    html_content = ""
    md_content = ""
    docx_file = ""
    doc_file = ""
    sim_file = ""

    html_files = glob.glob(os.path.join(doc_dir, "*.html"))
    if html_files:
        with open(html_files[0], "r", encoding="utf-8") as f:
            html_content = f.read()

    md_files = glob.glob(os.path.join(doc_dir, "*.md"))
    if md_files:
        with open(md_files[0], "r", encoding="utf-8") as f:
            md_content = f.read()

    docx_files = glob.glob(os.path.join(doc_dir, "*.docx"))
    if docx_files: docx_file = os.path.basename(docx_files[0])

    doc_files = glob.glob(os.path.join(doc_dir, "*.doc"))
    if doc_files: doc_file = os.path.basename(doc_files[0])

    if os.path.exists(os.path.join(sim_dir, "simulador.html")):
        sim_file = "simulador.html"

    proc_html = ""
    proc_html_file = os.path.join(proc_dir, "informe_proceso.html")
    if os.path.exists(proc_html_file):
        with open(proc_html_file, "r", encoding="utf-8") as f:
            proc_html = f.read()

    # Cargar trazas
    traces = {}
    traces_file = os.path.join(proc_dir, "trazas_agentes.json")
    if os.path.exists(traces_file):
        try:
            with open(traces_file, "r", encoding="utf-8") as f:
                traces = json.load(f)
        except Exception: pass

    # Cargar metadatos
    meta_file = os.path.join(chat_dir, "conversacion_metadata.json")
    meta = {}
    prompt = ""
    title = folder_name
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                for r in meta.get("responses", []):
                    if r.get("folder") == folder_name:
                        prompt = r.get("prompt", "")
                        title = r.get("title", title)
                        break
        except Exception: pass

    # Rutas relativas para descargas directas
    rel_base = f"/historial/chats/{chat_id}/{folder_name}/entregables"
    return {
        "status": "ok",
        "chat_id": chat_id,
        "folder": folder_name,
        "title": title,
        "prompt": prompt,
        "html": html_content,
        "markdown": md_content,
        "process_report_html": proc_html,
        "traces": traces,
        "docx_url": f"{rel_base}/documentos/{docx_file}" if docx_file else None,
        "doc_url": f"{rel_base}/documentos/{doc_file}" if doc_file else None,
        "sim_url": f"{rel_base}/visualizador_interactivo/{sim_file}" if sim_file else None,
        "md_url": f"{rel_base}/documentos/{os.path.basename(md_files[0])}" if md_files else None
    }

def save_chat_attachment(chat_id, filename, file_bytes):
    """Guarda un archivo subido por el usuario en la carpeta específica del chat."""
    if not chat_id:
        chat_id = "general"
    chat_id = validate_component(chat_id, "chat_id")
    safe_fn = safe_filename(filename)
    upload_dir = safe_child_path(CHATS_DIR, chat_id, "archivos_cargados")
    os.makedirs(upload_dir, exist_ok=True)
    dest_path = safe_child_path(upload_dir, safe_fn)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return {
        "status": "ok",
        "chat_id": chat_id,
        "filename": safe_fn,
        "path": dest_path,
        "url": f"/historial/chats/{chat_id}/archivos_cargados/{safe_fn}"
    }

def list_chat_attachments(chat_id):
    """Lista todos los archivos adjuntados en una conversación."""
    if not chat_id: return []
    upload_dir = os.path.join(CHATS_DIR, chat_id, "archivos_cargados")
    if not os.path.exists(upload_dir): return []
    items = []
    for fn in os.listdir(upload_dir):
        fp = os.path.join(upload_dir, fn)
        if os.path.isfile(fp):
            items.append({
                "filename": fn,
                "size": os.path.getsize(fp),
                "url": f"/historial/chats/{chat_id}/archivos_cargados/{fn}"
            })
    return items

import shutil

def delete_chat(chat_id):
    """Elimina permanentemente una conversación y toda su carpeta en disco."""
    if not chat_id: return {"status": "error", "message": "Falta chat_id"}
    chat_dir = os.path.join(CHATS_DIR, chat_id)
    if os.path.exists(chat_dir):
        try:
            shutil.rmtree(chat_dir)
            return {"status": "ok", "deleted_chat_id": chat_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return {"status": "not_found", "message": "El chat no existe"}

def delete_response(chat_id, folder_name):
    """Elimina una investigación específica y su carpeta física, actualizando la metadata."""
    if not chat_id or not folder_name:
        return {"status": "error", "message": "Parámetros incompletos"}
    chat_dir = os.path.join(CHATS_DIR, chat_id)
    resp_path = os.path.join(chat_dir, folder_name)

    if os.path.exists(resp_path):
        try:
            shutil.rmtree(resp_path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # Actualizar metadata del chat
    meta_file = os.path.join(chat_dir, "conversacion_metadata.json")
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            responses = meta.get("responses", [])
            meta["responses"] = [r for r in responses if r.get("folder") != folder_name]
            meta["total_responses"] = len(meta["responses"])
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception: pass

    return {"status": "ok", "deleted_folder": folder_name}
