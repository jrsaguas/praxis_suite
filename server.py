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

from config import BASE_DIR as DIRECTORY, HISTORIAL_DIR, CHATS_DIR, TEMPLATE_DIR, KNOWLEDGE_DIR, PORT, HOST, MAX_REQUEST_BYTES, ALLOWED_ORIGINS, ensure_directories

ensure_directories()

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
import investigation_store
import artifact_command_executor
import experience_analyzer
import experience_store
import strategy_registry
import learning_bridge
import task_family
import experience_trends
import strategy_selector
import strategy_context
import promotion_gate
import strategy_health
import strategy_recovery
import preference_store
import rag_engine
import refinement_engine
import cas_verifier
import draft_manager
import agent_graph
import mathematical_depth
import operational_context
try:
    import pdf_mimicry_engine
except Exception as e:
    pdf_mimicry_engine = None
    print(f"[Server] Advertencia: motor de mimetismo PDF operando en modo básico: {e}")

class PraxisRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        origin = self.headers.get('Origin', '')
        allowed_origins = ALLOWED_ORIGINS
        if origin in allowed_origins:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        super().end_headers()

    def _read_body(self):
        try:
            content_len = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ValueError('Content-Length inválido')
        if content_len < 0 or content_len > MAX_REQUEST_BYTES:
            raise ValueError(f'Payload demasiado grande (máximo {MAX_REQUEST_BYTES} bytes)')
        return self.rfile.read(content_len)

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
        elif path == '/api/investigations/version':
            self.handle_register_investigation_version()
        elif path == '/api/agent-graph/plan':
            self.handle_agent_graph_plan()
        elif path == '/api/investigations/artifact-command':
            self.handle_artifact_command()
        elif path == '/api/experience/analyze':
            self.handle_experience_analysis()
        elif path == '/api/strategies/recovery-candidate':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id, family = data.get('chat_id'), data.get('task_family')
                if not chat_id or not family:
                    raise ValueError('chat_id y task_family son obligatorios')
                outcomes = experience_store.list_records(chat_manager.CHATS_DIR, chat_id, limit=1000)
                result = strategy_recovery.recovery_candidate(
                    outcomes, family=family,
                    excluded_strategy_ids=data.get('excluded_strategy_ids') or [],
                    min_score=float(data.get('min_score', .75)),
                )
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status':'ok','recovery':result}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/strategies/health':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id = data.get('chat_id')
                strategy_id = data.get('strategy_id')
                if not chat_id or not strategy_id:
                    raise ValueError('chat_id y strategy_id son obligatorios')
                registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
                strategy = next((x for x in registry.list(chat_id) if x.get('strategy_id') == strategy_id), None)
                if not strategy:
                    raise ValueError('Estrategia no encontrada')
                outcomes = experience_store.list_records(chat_manager.CHATS_DIR, chat_id, limit=1000)
                health = strategy_health.assess_degradation(
                    outcomes,
                    strategy_id=strategy_id,
                    task_family=data.get('task_family'),
                    recent_limit=int(data.get('recent_limit', 5)),
                    min_score=float(data.get('min_score', .70)),
                    max_decline=float(data.get('max_decline', .05)),
                )
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'strategy': strategy, 'health': health}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/strategies/promote':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id = data.get('chat_id')
                strategy_id = data.get('strategy_id')
                if not chat_id or not strategy_id:
                    raise ValueError('chat_id y strategy_id son obligatorios')
                registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
                item = next((x for x in registry.list(chat_id) if x.get('strategy_id') == strategy_id), None)
                if not item:
                    raise ValueError('Estrategia no encontrada')
                if item.get('status') == 'promoted':
                    raise ValueError('La estrategia ya está promovida')
                outcomes = experience_store.list_records(chat_manager.CHATS_DIR, chat_id, limit=1000)
                comparison = promotion_gate.compare_strategy_to_baseline(
                    outcomes, strategy_id=strategy_id,
                    baseline_id=str(data.get('baseline_id', 'baseline-v1')),
                    task_family=data.get('task_family'),
                    min_samples=int(data.get('min_samples', 3)),
                )
                decision_raw = promotion_gate.evaluate_gate(
                    comparison,
                    passed_tests=data.get('passed_tests') or [],
                    required_tests=item.get('required_tests') or [],
                    min_improvement=float(data.get('min_improvement', 0.02)),
                    regressions=data.get('regressions') or [],
                    max_regressions=int(data.get('max_regressions', 0)),
                )
                decision = strategy_registry.PromotionDecision(
                    strategy_id=strategy_id,
                    approved=bool(decision_raw['approved']),
                    reason=str(decision_raw['reason']),
                    baseline_score=float(comparison['baseline_score']),
                    candidate_score=float(comparison['candidate_score']),
                    required_tests=tuple(decision_raw['required_tests']),
                    passed_tests=tuple(decision_raw['passed_tests']),
                    regressions=tuple(decision_raw['regressions']),
                )
                if not decision.approved:
                    raise ValueError('Promotion Gate rechazó la estrategia: ' + decision.reason)
                promoted = registry.promote(chat_id, decision)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'promoted',
                    'strategy': promoted,
                    'decision': decision.to_dict()
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/strategies/promotion-check':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id = data.get('chat_id')
                strategy_id = data.get('strategy_id')
                if not chat_id or not strategy_id:
                    raise ValueError('chat_id y strategy_id son obligatorios')
                registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
                strategy_items = registry.list(chat_id)
                selected = next((x for x in strategy_items if x.get('strategy_id') == strategy_id), None)
                if not selected:
                    raise ValueError('Estrategia no encontrada')
                outcomes = experience_store.list_records(chat_manager.CHATS_DIR, chat_id, limit=1000)
                comparison = promotion_gate.compare_strategy_to_baseline(
                    outcomes,
                    strategy_id=strategy_id,
                    baseline_id=str(data.get('baseline_id', 'baseline-v1')),
                    task_family=data.get('task_family'),
                    min_samples=int(data.get('min_samples', 3)),
                )
                decision = promotion_gate.evaluate_gate(
                    comparison,
                    passed_tests=data.get('passed_tests') or [],
                    required_tests=selected.get('required_tests') or [],
                    min_improvement=float(data.get('min_improvement', 0.02)),
                    regressions=data.get('regressions') or [],
                    max_regressions=int(data.get('max_regressions', 0)),
                )
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'comparison': comparison, 'decision': decision}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/strategies/reactivate':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id, strategy_id = data.get('chat_id'), data.get('strategy_id')
                if not chat_id or not strategy_id:
                    raise ValueError('chat_id y strategy_id son obligatorios')
                registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
                strategy = next((x for x in registry.list(chat_id) if x.get('strategy_id') == strategy_id), None)
                if not strategy:
                    raise ValueError('Estrategia no encontrada')
                outcomes = experience_store.list_records(chat_manager.CHATS_DIR, chat_id, limit=1000)
                family = data.get('task_family')
                recovery = strategy_recovery.recovery_candidate(outcomes, family=family, min_score=float(data.get('min_score', .75)))
                target = next((x for x in recovery.get('candidates', []) if x.get('strategy_id') == strategy_id), None)
                if not target:
                    raise ValueError('La evidencia histórica actual no justifica reactivar esta estrategia.')
                recovery['selected_reactivation'] = target
                reactivated = registry.reactivate(chat_id, strategy_id, reason='recuperacion_basada_en_historial', evidence=recovery)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status':'reactivated','strategy':reactivated,'recovery':recovery}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/strategies/retire':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id = data.get('chat_id')
                strategy_id = data.get('strategy_id')
                if not chat_id or not strategy_id:
                    raise ValueError('chat_id y strategy_id son obligatorios')
                registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
                outcomes = experience_store.list_records(chat_manager.CHATS_DIR, chat_id, limit=1000)
                health = strategy_health.assess_degradation(outcomes, strategy_id=strategy_id, task_family=data.get('task_family'))
                if not health.get('degraded'):
                    raise ValueError('La evidencia disponible no justifica retirar la estrategia.')
                retired = registry.retire(chat_id, strategy_id, reason='degradacion_detectada', evidence=health)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'retired', 'strategy': retired, 'health': health}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/strategies/context':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id = data.get('chat_id')
                query = str(data.get('query', '')).strip()
                if not query:
                    raise ValueError('query es obligatorio')
                records = experience_store.list_records(chat_manager.CHATS_DIR, chat_id, limit=100) if chat_id else []
                preferences = preference_store.effective_profile(chat_manager.CHATS_DIR, chat_id) if chat_id else None
                family = task_family.classify_task_family({"metadata": {"topic": query}, "task_fingerprint": query})
                trends = experience_trends.temporal_feature_summary(records)
                registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
                context = strategy_context.build_strategy_context(
                    query,
                    records=records,
                    strategies=registry.list(chat_id) if chat_id else [],
                    preferences=preferences,
                    trends=trends,
                )
                context["evidence_count"] = len(records)
                context["trend_count"] = len(trends)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'strategy_context': context}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/strategies/select':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id = data.get('chat_id')
                if not chat_id:
                    raise ValueError('chat_id es obligatorio')
                registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
                strategies = registry.list(chat_id)
                preferences = None
                if data.get('preferences'):
                    from preference_profiles import preference_from_dict
                    preferences = preference_from_dict(data['preferences'])
                ranked = strategy_selector.select_strategies(
                    strategies,
                    task_family=data.get('task_family'),
                    preferences=preferences,
                    trends=data.get('trends') or [],
                    include_candidates=bool(data.get('include_candidates', False)),
                    limit=int(data.get('limit', 5)),
                )
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'strategies': ranked}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/experience/strategy-outcome':
            try:
                data = json.loads(self._read_body().decode('utf-8'))
                chat_id = data.get('chat_id')
                if not chat_id or not data.get('strategy_context'):
                    raise ValueError('chat_id y strategy_context son obligatorios')
                saved = learning_bridge.persist_strategy_outcome(
                    chat_manager.CHATS_DIR, chat_id,
                    strategy_context=data['strategy_context'],
                    evaluation_profile=data.get('evaluation_profile') or {},
                    score=float(data.get('score', 0)),
                    consistent=bool(data.get('consistent', False)),
                    investigation_id=data.get('investigation_id'),
                    version_id=data.get('version_id'),
                    metadata=data.get('metadata'),
                )
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'experience': saved}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_error(400, str(e))
        elif path == '/api/experience/record':
            self.handle_learning_record()
        elif path == '/api/strategies':
            self.handle_strategy_registry()
        elif path == '/api/refine_section':
            self.handle_refine_section()
        elif path == '/api/verify_cas':
            self.handle_verify_cas()
        else:
            self.send_error(404, "Endpoint no encontrado")

    def handle_agent_graph_plan(self):
        try:
            data = json.loads(self._read_body().decode('utf-8'))
            task = str(data.get('task', '')).strip()
            if not task:
                raise ValueError('task es obligatorio')
            profile_data = data.get('depth_profile') or {'level': data.get('level', 'licenciatura')}
            profile = mathematical_depth.MathematicalDepthProfile.from_dict(profile_data)
            depth_context = mathematical_depth.build_depth_context(profile)
            required_artifacts = data.get('required_artifacts') or []
            requested_agents = data.get('requested_agents') or []
            plan = agent_graph.AgentGraphPlanner().plan(
                requested_agents=requested_agents,
                required_artifacts=required_artifacts,
                depth_requirements=depth_context['requirements'],
            )
            strategy = data.get('strategy_context') or {}
            context = operational_context.build_operational_context(
                strategy_context=strategy,
                task=task,
                investigation_id=data.get('investigation_id'),
            )
            context['depth_context'] = depth_context
            context['agent_plan'] = {
                'selected_agents': plan.selected_agents,
                'tasks': [
                    {
                        'task_id': t.task_id,
                        'agent_id': t.agent_id,
                        'inputs': t.inputs,
                        'outputs': t.outputs,
                        'depends_on': t.depends_on,
                        'quality_gates': t.quality_gates,
                    }
                    for t in plan.tasks
                ],
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'plan': context['agent_plan'], 'context': context}, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(400, str(e))

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
        elif path.startswith('/api/investigations/') and path.endswith('/versions'):
            parts = path[len('/api/investigations/'):].rsplit('/versions', 1)[0].strip('/')
            bits = parts.split('/', 1)
            if len(bits) != 2:
                self.send_error(400, 'Ruta de investigación inválida')
                return
            chat_id, folder = unquote(bits[0]), unquote(bits[1])
            try:
                versions = investigation_store.list_versions(chat_manager.CHATS_DIR, chat_id, folder)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status':'ok','versions':versions}).encode('utf-8'))
            except Exception as e:
                self.send_error(500, str(e))
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
            post_body = self._read_body()
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
            post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
        post_body = self._read_body()
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
            post_body = self._read_body()
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
            post_body = self._read_body()
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


    def handle_artifact_command(self):
        try:
            data = json.loads(self._read_body().decode('utf-8'))
            chat_id = data.get('chat_id')
            folder = data.get('folder')
            instruction = data.get('instruction', '')
            if not chat_id or not folder or not instruction:
                raise ValueError('chat_id, folder e instruction son obligatorios')

            result = artifact_command_executor.execute_artifact_command(
                chat_manager.CHATS_DIR,
                chat_id,
                folder,
                instruction,
                title=data.get('title', folder),
            )
            investigation_store.record_execution(
                chat_manager.CHATS_DIR,
                chat_id,
                folder,
                operation=result.get('operation', 'unknown'),
                instruction=instruction,
                status=result.get('status', 'unknown'),
                changed_files=result.get('changed_files') or [],
                artifact_types=result.get('artifact_types') or [],
                message=result.get('message', ''),
                plan=result.get('plan') or {},
            )
            status = 200 if result.get('status') == 'ok' else 400
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_learning_record(self):
        try:
            data = json.loads(self._read_body().decode('utf-8'))
            chat_id = data.get('chat_id')
            record_data = data.get('record')
            if not chat_id or not isinstance(record_data, dict):
                raise ValueError('chat_id y record son obligatorios')
            from evaluator_orchestrator import LearningRecord, Evaluation, AgentResult
            evaluation_data = record_data.get('evaluation') or {}
            evaluation = Evaluation(
                consistent=bool(evaluation_data.get('consistent')),
                score=float(evaluation_data.get('score', 0)),
                errors=tuple(evaluation_data.get('errors', [])),
                strengths=tuple(evaluation_data.get('strengths', [])),
                required_retries=tuple(evaluation_data.get('required_retries', [])),
                recommendation=str(evaluation_data.get('recommendation', 'ACCEPT')),
                reasons=tuple(evaluation_data.get('reasons', [])),
            )
            agents = tuple(
                AgentResult(
                    str(a.get('agent', 'unknown')),
                    a.get('output'),
                    (),
                    str(a.get('status', 'COMPLETED')),
                ) for a in record_data.get('agent_results', [])
            )
            record = LearningRecord(
                record_id=str(record_data.get('record_id', '')),
                created_at=str(record_data.get('created_at', '')),
                task_fingerprint=str(record_data.get('task_fingerprint', '')),
                agent_results=agents,
                evaluation=evaluation,
                proposal=None,
                strategy_id=str(record_data.get('strategy_id', 'baseline-v1')),
            )
            saved = learning_bridge.persist_learning_record(
                chat_manager.CHATS_DIR, chat_id, record,
                investigation_id=data.get('investigation_id'),
                version_id=data.get('version_id'),
                evaluation_profile=data.get('evaluation_profile'),
                metadata=data.get('metadata'),
            )
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(saved, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(400, str(e))

    def handle_experience_analysis(self):
        try:
            data = json.loads(self._read_body().decode('utf-8'))
            chat_id = data.get('chat_id')
            query = data.get('query', '')
            records = experience_store.list_records(
                chat_manager.CHATS_DIR, chat_id, limit=data.get('limit', 100)
            )
            family = data.get('task_family')
            if family:
                records = [
                    r for r in records
                    if task_family.classify_task_family(r) == str(family).strip().lower().replace(' ', '_')
                ]
            refs = experience_analyzer.select_references(
                records, query, limit=data.get('reference_limit', 5)
            )
            patterns = experience_analyzer.detect_patterns(records)
            result = experience_analyzer.fuse_reference_patterns(refs, patterns)
            candidate = experience_analyzer.build_strategy_candidate(refs, patterns)
            result['task_families'] = task_family.family_summary(records)
            result['temporal_trends'] = experience_trends.temporal_feature_summary(records)
            result['strategy_summary'] = experience_store.summarize_strategies(records)
            result['candidate_strategy'] = candidate.to_dict()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_strategy_registry(self):
        try:
            data = json.loads(self._read_body().decode('utf-8'))
            registry = strategy_registry.StrategyRegistry(chat_manager.CHATS_DIR)
            chat_id = data.get('chat_id')
            action = data.get('action', 'list')

            if action == 'list':
                result = registry.list(chat_id, data.get('status'))
            elif action == 'register':
                strategy = strategy_registry.create_candidate(
                    data.get('name', ''),
                    data.get('objective', ''),
                    data.get('rules', []),
                    required_tests=data.get('required_tests', []),
                    evidence_ids=data.get('evidence_ids', []),
                    metrics=data.get('metrics', {}),
                )
                result = registry.register(chat_id, strategy).to_dict()
            elif action == 'promote':
                decision = strategy_registry.PromotionDecision(
                    strategy_id=data['strategy_id'],
                    approved=bool(data['approved']),
                    reason=data.get('reason', ''),
                    baseline_score=float(data.get('baseline_score', 0)),
                    candidate_score=float(data.get('candidate_score', 0)),
                    required_tests=tuple(data.get('required_tests', [])),
                    passed_tests=tuple(data.get('passed_tests', [])),
                )
                result = registry.promote(chat_id, decision)
            else:
                raise ValueError('Acción de estrategia no soportada')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(400, str(e))

    # --- VERSIONADO LÓGICO DE INVESTIGACIONES ---

    def handle_register_investigation_version(self):
        try:
            data = json.loads(self._read_body().decode('utf-8'))
            chat_id = data.get('chat_id')
            folder = data.get('folder')
            if not chat_id or not folder:
                raise ValueError('chat_id y folder son obligatorios')
            version = investigation_store.register_version(
                chat_manager.CHATS_DIR,
                chat_id,
                folder,
                prompt=data.get('prompt', ''),
                title=data.get('title', folder),
                source=data.get('source', 'artifact_command'),
                parent_version_id=data.get('parent_version_id'),
                commands=data.get('commands') or [],
                references=data.get('references') or [],
                artifact_types=data.get('artifact_types') or [],
            )
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'version': version}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    # --- RAG ACADÉMICO Y TUNEO DIRIGIDO DE SECCIONES (FASES 5 Y 6) ---

    def handle_rag_arxiv(self):
        try:
            post_body = self._read_body()
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
            post_body = self._read_body()
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
            post_body = self._read_body()
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
            post_body = self._read_body()
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
    with socketserver.ThreadingTCPServer((HOST, PORT), PraxisRequestHandler) as httpd:
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
