#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRAXIS LOCAL WORKSPACE & AGENT SERVER (v10.0)
Servidor local para http://localhost:8000.
Gestiona:
1. Jerarquía Multi-Chat en disco: historial/chats/[id_chat]/[respuestas]/
2. Motor de Visualización y Simulación Interactiva Canvas HTML5 con sliders paramétricos
3. Compilación continua de Microsoft Word (.docx y .doc con OMML 2D y MathML)
4. Base de Conocimiento Matemático Unificada e Incremental
5. Puente Epistémico Inter-Chat (búsqueda y recuperación cruzada)
6. Proxy local para Ollama y LLMs externos
"""

import http.server
import socketserver
import os
import sys
import json
import glob
import shutil
import subprocess
import datetime
import urllib.request
import urllib.error
import webbrowser
from urllib.parse import urlparse, unquote

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_DIR = os.path.join(DIRECTORY, "historial")
CHATS_DIR = os.path.join(HISTORIAL_DIR, "chats")
TEMPLATE_DIR = os.path.join(HISTORIAL_DIR, "plantillas")
KNOWLEDGE_DIR = os.path.join(HISTORIAL_DIR, "base_conocimiento")
PORT = 8000

for d in [HISTORIAL_DIR, CHATS_DIR, TEMPLATE_DIR, KNOWLEDGE_DIR]:
    os.makedirs(d, exist_ok=True)

# Importar módulos auxiliares locales
sys.path.insert(0, DIRECTORY)

ENV_FILE = os.path.join(DIRECTORY, ".env")
def read_env():
    env_vars = {}
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        env_vars[k] = v
                        os.environ[k] = v
        except Exception as e:
            print(f"[Server] Error leyendo .env: {e}")
    return env_vars

GLOBAL_ENV = read_env()

import convert
import knowledge_engine
import process_reporter
import interactive_engine
import chat_manager
import rag_engine
import refinement_engine
import cas_verifier
import draft_manager
try:
    import pdf_mimicry_engine
except Exception as e:
    pdf_mimicry_engine = None
    print(f"[Server] Advertencia: motor de mimetismo PDF operando en modo básico: {e}")

class PraxisRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/system_config' or path == '/api/config':
            self.handle_get_system_config()
        elif path == '/api/chats/checkpoint':
            self.handle_save_checkpoint()
        elif path == '/api/chats/upload':
            self.handle_upload_attachment()
        elif path == '/api/save_investigation':
            self.handle_save_investigation()
        elif path == '/api/export_docx':
            self.handle_export_docx()
        elif path == '/api/export_doc':
            self.handle_export_doc()
        elif path == '/api/get_knowledge_context':
            self.handle_get_knowledge_context()
        elif path == '/api/chats/new':
            self.handle_create_chat()
        elif path == '/api/chats/delete':
            self.handle_delete_chat()
        elif path == '/api/chats/delete_response':
            self.handle_delete_response()
        elif path == '/api/chats/query_other':
            self.handle_query_other_chats()
        elif path == '/api/drafts/save':
            self.handle_save_draft()
        elif path == '/api/drafts/compile':
            self.handle_compile_draft()
        elif path == '/api/drafts/save_as_template':
            self.handle_save_draft_as_template()
        elif path == '/api/mimic_pdf':
            self.handle_mimic_pdf()
        elif path == '/api/ollama_chat':
            self.handle_ollama_chat()
        elif path == '/api/ollama_tags':
            self.handle_ollama_tags()
        elif path == '/api/rag/arxiv':
            self.handle_rag_arxiv()
        elif path == '/api/rag/chat_docs':
            self.handle_rag_chat_docs()
        elif path == '/api/refine_section':
            self.handle_refine_section()
        elif path == '/api/verify_cas':
            self.handle_verify_cas()
        else:
            self.send_error(404, "Endpoint no encontrado")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/system_config' or path == '/api/config':
            self.handle_get_system_config()
        elif path == '/api/chats':
            self.handle_list_chats()
        elif path.startswith('/api/chats/') and '/responses/' in path:
            parts = path.split('/responses/')
            chat_id = unquote(parts[0][len('/api/chats/'):]).strip('/')
            folder = unquote(parts[1]).strip('/')
            self.handle_get_response_detail(chat_id, folder)
        elif path.startswith('/api/chats/') and path.endswith('/checkpoint'):
            chat_id = unquote(path[len('/api/chats/'):-len('/checkpoint')]).strip('/')
            self.handle_get_checkpoint(chat_id)
        elif path.startswith('/api/chats/') and path.endswith('/attachments'):
            chat_id = unquote(path[len('/api/chats/'):-len('/attachments')]).strip('/')
            self.handle_list_attachments(chat_id)
        elif path.startswith('/api/chats/'):
            chat_id = unquote(path[len('/api/chats/'):]).strip('/')
            self.handle_get_chat(chat_id)
        elif path == '/api/list_history':
            self.handle_list_history()
        elif path == '/api/knowledge_base':
            self.handle_get_knowledge_base()
        elif path == '/api/templates':
            self.handle_list_templates()
        elif path == '/api/drafts':
            self.handle_list_drafts()
        elif path.startswith('/api/drafts/'):
            draft_id = unquote(path[len('/api/drafts/'):]).strip('/')
            self.handle_get_draft(draft_id)
        elif path == '/api/ollama_tags':
            self.handle_ollama_tags()
        else:
            super().do_GET()

    
    # --- CONTROLADORES DE DRAFT STUDIO Y MIMETISMO PDF ---

    def handle_list_drafts(self):
        try:
            drafts = draft_manager.list_drafts()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"drafts": drafts}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_draft(self, draft_id):
        try:
            draft = draft_manager.get_draft(draft_id)
            if not draft:
                self.send_error(404, "Borrador no encontrado")
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(draft).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_save_draft(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8'))
            saved = draft_manager.save_draft(data)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(saved).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_compile_draft(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8'))
            draft_id = data.get('draft_id')
            res = draft_manager.compile_draft_to_words(draft_id)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_save_draft_as_template(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8'))
            draft_id = data.get('draft_id')
            name = data.get('name')
            res = draft_manager.save_draft_as_template(draft_id, name)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_mimic_pdf(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            import base64
            data = json.loads(post_body.decode('utf-8'))
            b64_pdf = data.get('base64_pdf', '')
            filename = data.get('filename', 'trabajo_escolar.pdf')
            template_name = data.get('template_name', 'Mi Tarea Universitaria')

            tmp_pdf = os.path.join(DIRECTORY, "temp_upload.pdf")
            with open(tmp_pdf, "wb") as pf:
                pf.write(base64.b64decode(b64_pdf))

            tpl = pdf_mimicry_engine.analyze_pdf_structure(tmp_pdf, template_name)
            try: os.remove(tmp_pdf)
            except Exception: pass

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(tpl).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    # --- CONTROLADORES DE CHAT ---

    def handle_list_chats(self):
        """Lista todas las conversaciones activas"""
        try:
            chats = chat_manager.list_chats()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"chats": chats}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_delete_chat(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            chat_id = data.get('chat_id')
            res = chat_manager.delete_chat(chat_id)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_delete_response(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            chat_id = data.get('chat_id')
            folder = data.get('folder')
            res = chat_manager.delete_response(chat_id, folder)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_create_chat(self):
        """Crea una nueva conversación independiente"""
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8')) if post_body else {}
            title = data.get('title', 'Nueva Conversación')
            chat = chat_manager.create_chat(title)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(chat).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_chat(self, chat_id):
        """Devuelve los datos de una conversación con sus respuestas y simuladores"""
        try:
            chat = chat_manager.get_chat(chat_id)
            if not chat:
                self.send_error(404, "Conversación no encontrada")
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(chat).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_query_other_chats(self):
        """Puente Epistémico: Recupera datos semánticos de otras conversaciones"""
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8')) if post_body else {}
            query = data.get('query', '')
            exclude_id = data.get('exclude_chat_id')
            results = chat_manager.query_inter_chats(query, exclude_id)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"matches": results}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    # --- CONTROLADOR PRINCIPAL DE GUARDADO ---

    def handle_save_investigation(self):
        """
        Guarda la investigación dentro del chat activo en:
        historial/chats/[id_chat]/respuesta_[n]_[titulo]/
        generando docx, doc, md, html, imágenes, py, simulador.html y auditoría.
        """
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8'))
            chat_id = data.get('chat_id')
            res = chat_manager.save_response_to_chat(chat_id, data)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            print("[Praxis Server Error] Error al guardar investigación:", e)
            self.send_error(500, f"Error al guardar respuesta en chat: {str(e)}")

    # --- EXPORTACIONES WORD ---

    def handle_export_docx(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8'))
            title = data.get('title', 'informe').strip()
            markdown = data.get('markdown', '')
            safe_title = "".join([c if c.isalnum() or c in "._- " else "_" for c in title])[:50].strip()

            tmp_md = os.path.join(DIRECTORY, f"temp_{safe_title}.md")
            tmp_docx = os.path.join(DIRECTORY, f"temp_{safe_title}.docx")

            with open(tmp_md, 'w', encoding='utf-8') as f:
                f.write(markdown)

            ok, msg = convert.convert_with_pandoc(tmp_md, tmp_docx)
            if not ok:
                ok, msg = convert.convert_with_python_docx(tmp_md, tmp_docx)

            if os.path.exists(tmp_docx):
                with open(tmp_docx, 'rb') as f:
                    docx_bytes = f.read()

                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                self.send_header('Content-Disposition', f'attachment; filename="{safe_title}.docx"')
                self.send_header('Content-Length', str(len(docx_bytes)))
                self.end_headers()
                self.wfile.write(docx_bytes)

                try:
                    os.remove(tmp_md)
                    os.remove(tmp_docx)
                except Exception: pass
            else:
                self.send_error(500, "Fallo al compilar archivo .docx")
        except Exception as e:
            self.send_error(500, str(e))

    def handle_export_doc(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8'))
            title = data.get('title', 'informe').strip()
            markdown = data.get('markdown', '')
            safe_title = "".join([c if c.isalnum() or c in "._- " else "_" for c in title])[:50].strip()

            tmp_md = os.path.join(DIRECTORY, f"temp_{safe_title}.md")
            tmp_doc = os.path.join(DIRECTORY, f"temp_{safe_title}.doc")

            with open(tmp_md, 'w', encoding='utf-8') as f:
                f.write(markdown)

            convert.convert_markdown_to_doc(tmp_md, tmp_doc, title=title)

            if os.path.exists(tmp_doc):
                with open(tmp_doc, 'rb') as f:
                    doc_bytes = f.read()

                self.send_response(200)
                self.send_header('Content-Type', 'application/msword')
                self.send_header('Content-Disposition', f'attachment; filename="{safe_title}.doc"')
                self.send_header('Content-Length', str(len(doc_bytes)))
                self.end_headers()
                self.wfile.write(doc_bytes)

                try:
                    os.remove(tmp_md)
                    os.remove(tmp_doc)
                except Exception: pass
            else:
                self.send_error(500, "Fallo al generar archivo .doc")
        except Exception as e:
            self.send_error(500, str(e))

    # --- BASE DE CONOCIMIENTO Y PLANTILLAS ---

    def handle_get_knowledge_context(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            data = json.loads(post_body.decode('utf-8'))
            query = data.get('query', '')
            ctx = knowledge_engine.query_relevant_knowledge(query)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"context": ctx}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_knowledge_base(self):
        try:
            db = knowledge_engine.load_knowledge_db()
            md_content = ""
            if os.path.exists(knowledge_engine.MD_PATH):
                with open(knowledge_engine.MD_PATH, "r", encoding="utf-8") as f:
                    md_content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"db": db, "markdown": md_content}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_list_templates(self):
        try:
            templates = []
            if os.path.exists(TEMPLATE_DIR):
                for f in sorted(os.listdir(TEMPLATE_DIR)):
                    if f.endswith('.html'):
                        templates.append({"filename": f, "path": f"/historial/plantillas/{f}"})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"templates": templates}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_list_history(self):
        # Mantiene compatibilidad con clientes v9
        try:
            chats = chat_manager.list_chats()
            items = []
            for c in chats:
                cid = c.get("id")
                meta = chat_manager.get_chat(cid)
                for r in (meta.get("responses", []) if meta else []):
                    items.append({
                        "folder": f"{cid}/{r['folder']}",
                        "title": r.get("title", cid),
                        "has_docx": r.get("has_docx", True),
                        "has_doc": r.get("has_doc", True),
                        "has_sim": r.get("has_sim", True),
                        "has_md": True,
                        "has_html": True,
                        "has_process_report": True
                    })
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"investigations": items}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    # --- OLLAMA PROXY ---

    def handle_ollama_tags(self):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"models": [], "status": "offline", "error": str(e)}).encode('utf-8'))

    def handle_ollama_chat(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/chat",
                data=post_body,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


    # --- CONFIGURACIÓN DEL SISTEMA Y AUTO-DETECCIÓN (.ENV) ---

    def handle_get_system_config(self):
        env = read_env()
        ollama_avail = False
        ollama_models = []
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"User-Agent": "Praxis"})
            with urllib.request.urlopen(req, timeout=1.2) as r:
                data = json.loads(r.read().decode("utf-8"))
                ollama_avail = True
                ollama_models = [m.get("name") for m in data.get("models", [])]
        except Exception:
            pass

        cfg = {
            "gemini_api_key": env.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "")),
            "default_model": env.get("DEFAULT_MODEL", "gemini-2.5-flash"),
            "ollama_timeout": int(env.get("OLLAMA_TIMEOUT", 120)),
            "api_test_timeout": 3.0,
            "default_provider": env.get("DEFAULT_PROVIDER", "auto"),
            "ollama_base_url": env.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            "ollama_available": ollama_avail,
            "ollama_models": ollama_models,
            "gemini_models": [
                "gemini-2.5-flash",
                "gemini-1.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-pro"
            ]
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(cfg).encode('utf-8'))

    # --- CONTROLADORES DE CHECKPOINTS Y DETALLE DE RESPUESTAS ---

    def handle_save_checkpoint(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            chat_id = data.get('chat_id')
            checkpoint = data.get('checkpoint', {})
            res = chat_manager.save_checkpoint(chat_id, checkpoint)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res or {"status": "error"}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_checkpoint(self, chat_id):
        cp = chat_manager.get_checkpoint(chat_id)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "checkpoint": cp}).encode('utf-8'))

    def handle_get_response_detail(self, chat_id, folder):
        det = chat_manager.get_response_detail(chat_id, folder)
        if not det:
            self.send_error(404, "Respuesta no encontrada en el chat")
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(det).encode('utf-8'))

    def handle_upload_attachment(self):
        try:
            import base64
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            chat_id = data.get('chat_id', 'general')
            filename = data.get('filename', 'archivo_adjunto')
            b64 = data.get('base64_content', '')
            file_bytes = base64.b64decode(b64)
            res = chat_manager.save_chat_attachment(chat_id, filename, file_bytes)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_list_attachments(self, chat_id):
        items = chat_manager.list_chat_attachments(chat_id)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({"attachments": items}).encode('utf-8'))


    # --- RAG ACADÉMICO Y TUNEO DIRIGIDO DE SECCIONES (FASES 5 Y 6) ---

    def handle_rag_arxiv(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            query = data.get('query', '')
            max_results = data.get('max_results', 4)
            papers = rag_engine.search_arxiv(query, max_results=max_results)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"papers": papers}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_rag_chat_docs(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            chat_id = data.get('chat_id')
            query = data.get('query', '')
            snippets = rag_engine.search_chat_documents(chat_id, query)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"snippets": snippets}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_refine_section(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            chat_id = data.get('chat_id')
            folder = data.get('folder')
            section = data.get('section', 'desarrollo')
            new_content = data.get('content', '')
            note = data.get('note', '')
            res = refinement_engine.apply_refinement_to_saved_response(chat_id, folder, section, new_content, note)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))


    def handle_verify_cas(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            steps = data.get('steps', [])
            res = data.get('final_result', '')
            prompt = data.get('prompt', '')
            cert = cas_verifier.verify_mathematical_derivation(steps=steps, final_result=res, user_prompt=prompt)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(cert).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

def run_server():
    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PraxisRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 70)
        print("  PRAXIS V10.0 · SERVIDOR MULTI-CHAT & SIMULACIÓN INTERACTIVA")
        print("=" * 70)
        print(f"  URL Local:            {url}")
        print(f"  Jerarquía de Chats:   {CHATS_DIR}")
        print(f"  Plantillas Evolutivas:{TEMPLATE_DIR}")
        print(f"  Base Conocimiento:    {KNOWLEDGE_DIR}")
        print("  Formatos Soportados:  .docx (OMML 2D), .doc (MathML), Canvas HTML5")
        print("=" * 70)
        try:
            webbrowser.open(url)
        except Exception: pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor Praxis detenido correctamente.")

if __name__ == '__main__':
    run_server()
