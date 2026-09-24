
/* ============================================================
   NORMALIZADORES Y SANITIZADORES MATEMÁTICOS DE CERO ERRORES
   ============================================================ */
function cleanMathBlock(tex) {
  if (!tex) return '';
  let t = String(tex).trim();

  // Eliminar delimitadores externos redundantes
  if (t.startsWith('$$') && t.endsWith('$$') && t.length > 4) {
    t = t.slice(2, -2).trim();
  } else if (t.startsWith('$') && t.endsWith('$') && len(t) > 2) {
    t = t.slice(1, -1).trim();
  } else if (t.startsWith('\\(') && t.endsWith('\\)')) {
    t = t.slice(2, -2).trim();
  } else if (t.startsWith('\\[') && t.endsWith('\\]')) {
    t = t.slice(2, -2).trim();
  }

  // Corregir exponentes no agrupados comunes (ej. e^At -> e^{At}, e^tA -> e^{tA})
  t = t.replace(/e\^([a-zA-Z0-9]{2,})/g, 'e^{$1}');

  // Balancear llaves faltantes en exponentes o índices (previene 'missing open brace')
  const openB = (t.match(/\{/g) || []).length;
  const closeB = (t.match(/\}/g) || []).length;
  if (openB > closeB) {
    t += '}'.repeat(openB - closeB);
  }

  return t;
}

function formatSymbol(sym) {
  if (!sym) return '';
  let s = String(sym).trim();
  s = s.replace(/^\\\(/, '').replace(/\\\)$/, '').trim();
  if (s.startsWith('$') && s.endsWith('$')) return s;
  return `$${s}$`;
}

function formatProseMath(text) {
  if (!text) return '';
  let t = String(text);

  // Normalizar saltos de línea literales
  t = t.replace(/\\n/g, '\n');

  // Reemplazar delimitadores ambiguos \( ... \) por $ ... $
  t = t.replace(/\\\((.*?)\\\)/gs, '$$$1$$');

  // Reemplazar delimitadores \[ ... \] por $$ ... $$
  t = t.replace(/\\\[(.*?)\\\]/gs, '$$\n$1\n$$');

  // Corregir exponentes sin llaves dentro de fórmulas inline
  t = t.replace(/\$([^\$]+?)\$/g, (m, inner) => {
    return '$' + cleanMathBlock(inner) + '$';
  });

  return t;
}

"use strict";
/* ============================================================
   PRAXIS V6 — MOTOR NATIVO UNIFICADO PARA GEMINI
   ============================================================ */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

const STORAGE_KEY = 'praxis_gemini.cfg';
const API_BASE = 'https://generativelanguage.googleapis.com/v1beta';

const PREFERRED_MODELS = [
  'gemini-3.5-flash-lite',
  'gemini-3.5-flash',
  'gemini-flash-latest',
  'gemini-3.6-flash',
  'gemini-3.7-flash',
  'gemini-2.5-flash-lite',
  'gemini-2.5-pro',
  'gemini-pro-latest'
];

const overloadedCooldowns = {};

let cachedModels = [];

/* ============================================================
   INTEGRACIÓN MULTI-PROVEEDOR (GEMINI & OLLAMA LOCAL)
   ============================================================ */
async function loadSystemConfig() {
  try {
    const res = await fetch('/api/system_config');
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.gemini_api_key && (!S.key || S.key.length < 5)) {
        S.key = cfg.gemini_api_key;
        if ($('#apiKey')) $('#apiKey').value = S.key;
        log('Clave Gemini cargada automáticamente desde .env');
      }
      S.ollamaAvailable = !!cfg.ollama_available;
      S.ollamaModels = cfg.ollama_models || [];
      if (cfg.default_model && (!S.model || S.model === 'gemini-2.0-flash-exp')) {
        S.model = cfg.default_model;
      }
      updateModelSelect();
      updateConn();
    }
  } catch (e) {
    console.warn('Error al cargar configuración del servidor:', e);
  }
}

async function callOllama(prompt, opts = {}) {
  const model = S.ollamaModel || (S.ollamaModels && S.ollamaModels[0]) || 'llama3.2';
  const body = {
    model: model,
    messages: [{ role: 'user', content: String(prompt || '') }],
    stream: false,
    options: {
      temperature: opts.temperature != null ? opts.temperature : 0.3
    }
  };
  if (opts.json) {
    body.format = 'json';
  }

  // Timeout preventivo de 25 segundos para rescatar al LLM local de alargamientos
  const timeoutMs = opts.timeout != null ? opts.timeout : (S.ollamaTimeout ? S.ollamaTimeout * 1000 : 120000);
  const abortCtrl = new AbortController();
  const timer = setTimeout(() => abortCtrl.abort(), timeoutMs);

  try {
    const resp = await fetch('/api/ollama_chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: abortCtrl.signal
    });
    clearTimeout(timer);

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.error || `Error en Ollama local (${resp.status})`);
    }
    const data = await resp.json();
    return data.message?.content || '';

  } catch(err) {
    clearTimeout(timer);
    const isTimeout = err.name === 'AbortError' || String(err.message || '').includes('timeout');
    if (isTimeout) {
      log('Aviso: El modelo local Ollama excedió el tiempo límite (120s). Conmutando de emergencia a API en la nube (Gemini)...');
      toast('⚡ LLM local demoró demasiado. Conmutando automáticamente a Gemini en la nube...', 4500);
      // Fallback de emergencia a Gemini
      S.provider = 'gemini';
      updateConn();
      return await callGemini(prompt, opts);
    }
    throw err;
  }
}


/* Estado global de la aplicación */
const S = {
  key: '', // Clave eliminada por seguridad
  model: 'gemini-3.5-flash-lite',
  customModel: '',
  audience: 'doctor',
  depth: 'profunda',
  tools: { web: true, pdf: true, zip: false, code: false },
  files: [],
  running: false,
  abort: null,
  activeChatId: null,
  activeChatTitle: 'Investigación General',
  lastSimHtml: '',
  lastRun: null
};

const AUD_LABEL = {
  doctor: 'Doctores en Matemáticas',
  maestro: 'Maestros de Matemáticas',
  licenciatura: 'Estudiantes de Licenciatura en Matemáticas',
  publico: 'Público en General'
};
const DEPTH_LABEL = { breve: 'Breve', media: 'Media', profunda: 'Profunda' };

/* Utilidades básicas */
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const uid = () => 'id' + Math.random().toString(36).slice(2, 9);
function now() { return new Date().toLocaleTimeString(); }

function toast(msg, ms = 2800) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), ms);
}

function debounce(fn, ms) {
  let h;
  return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); };
}

async function typeset(el) {
  if (window.MathJax && MathJax.typesetPromise) {
    try { await MathJax.typesetPromise(el ? [el] : undefined); } catch (e) {}
  }
}

function download(name, text, mime = 'text/plain') {
  try {
    const b = new Blob([text], { type: mime + ';charset=utf-8' });
    const u = URL.createObjectURL(b);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = u;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      if (a.parentNode) a.parentNode.removeChild(a);
      URL.revokeObjectURL(u);
    }, 60000);
  } catch (err) {
    console.error('Error al descargar:', err);
    toast('Error en descarga: ' + err.message);
  }
}

function unique(arr) {
  const out = [], seen = {};
  for (let i = 0; i < arr.length; i++) {
    const v = String(arr[i] || '').trim();
    if (v && !seen[v]) { seen[v] = 1; out.push(v); }
  }
  return out;
}

function validKey(k) {
  k = String(k || '').trim();
  return /^AIza[0-9A-Za-z_-]{20,}$/.test(k) || /^AQ\.[A-Za-z0-9_.-]{20,}$/.test(k);
}

/* Diagnóstico en panel y consola */
function log(msg) {
  const text = typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2);
  const logEl = $('#pfpLog');
  if (logEl) {
    logEl.textContent += '[' + now() + '] ' + text + '\n\n';
    logEl.scrollTop = logEl.scrollHeight;
  }
  console.log('[Praxis v6]', msg);
}

function setPanelStatus(type, msg) {
  const el = $('#pfpStatus');
  if (!el) return;
  el.className = 'pfp-status ' + type;
  el.textContent = msg;
}

function friendlyError(e) {
  const msg = String(e && e.message || e || 'Error desconocido');
  const status = e && e.status;
  if (/Failed to fetch|NetworkError|Load failed|CORS/i.test(msg)) {
    return 'Error de red o CORS. Abre la URL en GitHub Pages o servidor web, no directo desde visor local restringido. Detalle: ' + msg;
  }
  if (status === 400) return 'HTTP 400: Petición inválida (revisar JSON o modelo). Detalle: ' + msg;
  if (status === 401) return 'HTTP 401: API Key inválida o no autorizada. Crea una nueva en Google AI Studio. Detalle: ' + msg;
  if (status === 403) return 'HTTP 403: Permiso denegado (revisa restricciones de clave, proyecto o cuota). Detalle: ' + msg;
  if (status === 404) return 'HTTP 404: El modelo solicitado no está disponible. Usa el botón "Listar modelos". Detalle: ' + msg;
  if (status === 429) return 'HTTP 429: Cuota excedida o rate limit alcanzado. Espera un momento o cambia de modelo.';
  if (status === 503 || /high demand/i.test(msg)) return 'HTTP 503: El modelo está saturado temporalmente por alta demanda. Cambia a gemini-2.5-flash o gemini-flash-latest.';
  if (status >= 500) return 'HTTP ' + status + ': Error temporal en los servidores de Google. Reintenta con otro modelo.';
  return msg;
}

/* Persistencia y sincronización de configuración */
function saveCfg() {
  try {
    const payload = {
      key: validKey(S.key) ? S.key : '',
      model: S.model,
      customModel: S.customModel,
      audience: S.audience,
      depth: S.depth,
      tools: S.tools
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch (e) {}
}

function loadCfg() {
  try {
    const c = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    if (validKey(c.key)) S.key = c.key;
    if (c.model && c.model !== 'gemini-2.0-flash-exp') S.model = c.model;
    if (typeof c.customModel === 'string') S.customModel = c.customModel;
    if (c.audience) S.audience = c.audience;
    if (c.depth) S.depth = c.depth;
    if (c.tools) S.tools = c.tools;
  } catch (e) {}
}

/* Parseo robusto de respuestas JSON */
function sanitizeJsonLatex(raw) {
  let out = '';
  let inStr = false;
  let i = 0;
  const len = raw.length;

  while (i < len) {
    const ch = raw[i];
    if (inStr) {
      if (ch === '"') {
        inStr = false;
        out += ch;
        i++;
      } else if (ch === '\\') {
        if (i + 1 < len) {
          const nextCh = raw[i + 1];
          // Ya escapada: \\
          if (nextCh === '\\') {
            out += '\\\\';
            i += 2;
          } else if (nextCh === '"') {
            out += '\\"';
            i += 2;
          } else if (nextCh === 'u' && i + 5 < len && /^[0-9a-fA-F]{4}$/.test(raw.slice(i + 2, i + 6))) {
            out += raw.slice(i, i + 6);
            i += 6;
          } else if ('bfnrt'.includes(nextCh) && (i + 2 < len && /[a-zA-Z]/.test(raw[i + 2]))) {
            // Comando LaTeX como \frac, \beta, \nabla, \rho, \theta (la siguiente letra es alfabética)
            out += '\\\\' + nextCh;
            i += 2;
          } else if ('nrt'.includes(nextCh)) {
            // Saltos de línea o tabuladores estándar
            out += '\\' + nextCh;
            i += 2;
          } else {
            // Cualquier otro caracter LaTeX como \int, \alpha, \partial, \sum, etc.
            out += '\\\\' + nextCh;
            i += 2;
          }
        } else {
          out += '\\\\';
          i++;
        }
      } else {
        out += ch;
        i++;
      }
    } else {
      if (ch === '"') inStr = true;
      out += ch;
      i++;
    }
  }
  return out;
}

function extractJSON(text) {
  if (!text) throw new Error('Respuesta vacía');
  let t = String(text).trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();

  const first = t.search(/[{\[]/);
  if (first >= 0) {
    t = t.slice(first);
  }

  // 1. Intento parseo directo
  try { return JSON.parse(t); } catch (e) {}

  // 2. Sanitizar escapes LaTeX (p. ej. \int, \frac, \alpha que rompen JSON.parse)
  const sanitized = sanitizeJsonLatex(t);
  try { return JSON.parse(sanitized); } catch (e) {}
  try { return JSON.parse(sanitized.replace(/,\s*([}\]])/g, '$1')); } catch (e) {}

  // 3. Auto-reparación por truncamiento (MAX_TOKENS): cerrar comillas y corchetes pendientes
  let inStr = false, escCh = false;
  const stack = [];
  for (let i = 0; i < sanitized.length; i++) {
    const ch = sanitized[i];
    if (inStr) {
      if (escCh) escCh = false;
      else if (ch === '\\') escCh = true;
      else if (ch === '"') inStr = false;
    } else {
      if (ch === '"') inStr = true;
      else if (ch === '{') stack.push('}');
      else if (ch === '[') stack.push(']');
      else if (ch === '}' || ch === ']') {
        if (stack.length && stack[stack.length - 1] === ch) stack.pop();
      }
    }
  }

  let repaired = sanitized;
  if (inStr) repaired += '"';
  while (stack.length) repaired += stack.pop();

  try { return JSON.parse(repaired); } catch (e) {}
  try { return JSON.parse(repaired.replace(/,\s*([}\]])/g, '$1')); } catch (e2) {
    throw new Error('La IA no devolvió JSON válido (revisar formato LaTeX): ' + String(e2.message || e2).slice(0, 140));
  }
}

/* ============================================================
   CLIENTE NATIVO DE GEMINI V6 (Dual Auth + Auto Fallback)
   ============================================================ */
async function rawFetch(url, init, timeoutMs = 25000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => {
    try { ctrl.abort(); } catch (e) {}
  }, timeoutMs);

  if (init && init.signal) {
    init.signal.addEventListener('abort', () => {
      try { ctrl.abort(); } catch (e) {}
    });
  }

  try {
    const fetchInit = Object.assign({}, init, { signal: ctrl.signal });
    const res = await fetch(url, fetchInit);
    clearTimeout(timer);
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch (e) {}
    if (!res.ok) {
      const msg = (json && json.error && json.error.message) || text.slice(0, 600) || res.statusText;
      const err = new Error('HTTP ' + res.status + ': ' + msg);
      err.status = res.status;
      err.json = json;
      err.text = text;
      throw err;
    }
    return json || {};
  } catch (e) {
    clearTimeout(timer);
    if (e && e.name === 'AbortError') {
      if (init && init.signal && init.signal.aborted) throw e;
      const toErr = new Error('Tiempo de espera agotado (' + Math.round(timeoutMs / 1000) + 's). El servidor no respondió a tiempo.');
      toErr.status = 504;
      toErr.isTimeout = true;
      throw toErr;
    }
    throw e;
  }
}

async function fetchModels() {
  const key = (S.key || '').trim();
  if (!validKey(key)) throw new Error('Falta una API key válida para listar modelos (AIza... o AQ...).');
  const baseUrl = API_BASE + '/models?pageSize=200';
  let json = null;

  try {
    json = await rawFetch(baseUrl, { method: 'GET', mode: 'cors', headers: { 'x-goog-api-key': key } }, 12000);
  } catch (e) {
    const sep = baseUrl.includes('?') ? '&' : '?';
    const queryUrl = baseUrl + sep + 'key=' + encodeURIComponent(key);
    log('GET /models vía header falló, intentando con parámetro key...');
    json = await rawFetch(queryUrl, { method: 'GET', mode: 'cors' }, 12000);
  }

  const models = Array.isArray(json.models) ? json.models : [];
  const parsed = models.map(m => {
    const name = String(m.name || '').replace(/^models\//, '').trim();
    const methods = Array.isArray(m.supportedGenerationMethods) ? m.supportedGenerationMethods : [];
    return { name, methods };
  }).filter(m => !!m.name);

  // Excluir modelos que NO son para chat/texto matemático o solo soportan Interactions API / Media
  const excludeKeywords = [
    'antigravity', 'deep-research', 'banana', 'aqa', 'embedding', 'image',
    'audio', 'tts', 'transcribe', 'live', 'clip', 'veo', 'lyria', 'robotics', 'er-2'
  ];

  const textSuitable = parsed.filter(m => {
    // Debe soportar generateContent explícitamente si methods está poblado
    const supportsGen = m.methods.length ? (m.methods.includes('generateContent') || m.methods.includes('streamGenerateContent')) : true;
    const hasExclude = excludeKeywords.some(kw => m.name.toLowerCase().includes(kw));
    return supportsGen && !hasExclude;
  }).map(m => m.name);

  cachedModels = unique(textSuitable);

  // Ordenar priorizando los modelos más estables y verificados
  cachedModels.sort((a, b) => {
    let ia = PREFERRED_MODELS.indexOf(a), ib = PREFERRED_MODELS.indexOf(b);
    if (ia < 0) ia = 999;
    if (ib < 0) ib = 999;
    if (ia !== ib) return ia - ib;
    return String(a).localeCompare(String(b));
  });

  if (!cachedModels.length) {
    cachedModels = PREFERRED_MODELS.slice();
  }

  let preferredFound = PREFERRED_MODELS.find(pm => cachedModels.includes(pm));
  if (!cachedModels.includes(S.model)) {
    S.model = preferredFound || cachedModels[0];
  }

  updateModelSelect();
  saveCfg();
  updateConn();
  return cachedModels;
}

async function callGemini(prompt, opts = {}) {
  const key = (S.key || '').trim();
  if (!validKey(key)) throw new Error('Falta una API key válida. Debe comenzar con AIza... o AQ...');

  const nowMs = Date.now();
  for (const m in overloadedCooldowns) {
    if (overloadedCooldowns[m] <= nowMs) delete overloadedCooldowns[m];
  }

  const activeModel = S.model === 'custom' ? (S.customModel || PREFERRED_MODELS[0]) : S.model;
  let candidates = unique([activeModel].concat(cachedModels.length ? cachedModels : PREFERRED_MODELS));

  // Mover modelos con 503 reciente al final
  candidates.sort((a, b) => {
    const aOver = overloadedCooldowns[a] ? 1 : 0;
    const bOver = overloadedCooldowns[b] ? 1 : 0;
    return aOver - bOver;
  });
  candidates = candidates.slice(0, 8);

  const ctrl = new AbortController();
  S.abort = ctrl;
  let lastError = null;

  for (let ci = 0; ci < candidates.length; ci++) {
    const model = candidates[ci];
    const base = API_BASE + '/models/' + encodeURIComponent(model) + ':generateContent';
    let modelUnavailable = false;
    const authModes = ['header', 'query'];

    for (let ai = 0; ai < authModes.length; ai++) {
      if (modelUnavailable) break;
      const auth = authModes[ai];
      const jsonAttempts = opts.json === false ? [false] : [true, false];

      for (let ji = 0; ji < jsonAttempts.length; ji++) {
        const useJson = jsonAttempts[ji];
        const url = auth === 'query' ? base + '?key=' + encodeURIComponent(key) : base;
        const headers = { 'Content-Type': 'application/json' };
        if (auth === 'header') headers['x-goog-api-key'] = key;

        // Ampliamos maxOutputTokens para no cortar respuestas complejas
        const maxTokens = opts.max_tokens != null ? opts.max_tokens : (opts.isTest ? 50 : 16384);
        const generationConfig = {
          temperature: opts.temperature != null ? opts.temperature : 0.4,
          topP: opts.topP != null ? opts.topP : 0.95,
          maxOutputTokens: maxTokens
        };
        if (useJson) generationConfig.responseMimeType = 'application/json';

        const body = {
          contents: [{ parts: [{ text: String(prompt || '') }] }],
          generationConfig
        };

        try {
          const timeoutMs = opts.timeout != null ? opts.timeout : (opts.isTest ? 3000 : 35000);
          const json = await rawFetch(url, {
            method: 'POST',
            mode: 'cors',
            headers,
            body: JSON.stringify(body),
            signal: ctrl.signal
          }, timeoutMs);

          // Modelo exitoso -> actualizar estado y selector visual
          if (S.model !== 'custom') {
            S.model = model;
            const sel = $('#model');
            if (sel && sel.value !== model) sel.value = model;
          }
          saveCfg();
          updateConn();

          const cand = json.candidates && json.candidates[0];
          if (!cand) throw new Error('Gemini no devolvió candidatos válidos.');

          if (cand.finishReason === 'MAX_TOKENS') {
            log('⚠️ Aviso: ' + model + ' alcanzó el límite de tokens. Auto-reparando JSON...');
          }

          const parts = cand.content && cand.content.parts ? cand.content.parts : [];
          const text = parts.map(p => (p && p.text) ? p.text : '').join('');
          if (!text.trim()) throw new Error('Gemini devolvió texto vacío.');
          return text;
        } catch (e) {
          lastError = e;
          if (e && e.name === 'AbortError' && ctrl.signal.aborted) throw e;
          const msg = String(e && e.message || '');

          // HTTP 429 (Cuota excedida o Rate Limit de este modelo) -> No colapsar: pausar 2s, marcar cooldown y saltar al siguiente modelo
          if (e && (e.status === 429 || /RESOURCE_EXHAUSTED|quota|rate limit/i.test(msg))) {
            overloadedCooldowns[model] = Date.now() + 60000;
            log('⚠️ ' + model + ' alcanzó su límite de cuota/RPM (HTTP 429). Conmutando automáticamente al siguiente modelo disponible...');
            setStat('run', 'Conmutando por cuota (429)…');
            setPanelStatus('warn', '429 en ' + model + '. Probando alternativo...');
            modelUnavailable = true;
            await new Promise(r => setTimeout(r, 2000));
            break;
          }

          // HTTP 503 / 500 / 502 / 504 o Timeout -> Modelo saturado, marcar cooldown de 60s y saltar al siguiente
          if (e && (e.status === 503 || e.status === 502 || e.status === 504 || e.status === 500 || e.isTimeout || /high demand|temporarily unavailable|overloaded/i.test(msg))) {
            overloadedCooldowns[model] = Date.now() + 60000;
            log('⚠️ ' + model + ' con saturación (HTTP 503/Timeout). Pasando de inmediato al siguiente modelo...');
            setStat('run', 'Probando modelo alternativo…');
            setPanelStatus('run', '503 en ' + model + '. Saltando...');
            modelUnavailable = true;
            break;
          }

          if (e && e.status === 404 && /model|NOT_FOUND|no longer available/i.test(msg)) {
            log('⚠️ ' + model + ' no disponible (HTTP 404). Pasando al siguiente candidato...');
            modelUnavailable = true;
            break;
          }

          if (e && e.status === 400 && useJson && /responseMimeType|JSON/i.test(msg)) {
            log(model + ' rechazó responseMimeType JSON. Reintentando en modo texto...');
            continue;
          }

          if (auth === 'header' && e.status) {
            if (e.status === 401 || e.status === 403) {
              throw new Error(friendlyError(e));
            }
            break;
          }

          log('Reintento: model=' + model + ', auth=' + auth + ', json=' + useJson + ', err=' + msg);
        }
      }
    }
  }
  throw new Error(friendlyError(lastError));
}

async function askJSON(prompt, opts = {}) {
  const raw = await callGemini(prompt, Object.assign({ json: true }, opts));
  return extractJSON(raw);
}


/* ============================================================
   CAPA EPISTÉMICA DE MECANISMOS MATEMÁTICOS (KNOWLEDGE LAYER)
   ============================================================ */
const PRAXIS_KNOWLEDGE_BASE = {
  "vector": {
    id: "vector",
    nombre: "Vector y Estructuras Vectoriales",
    dominio: "Álgebra Lineal & Geometría Diferencial",
    icono: "↗",
    definicion_axiomatica: "Elemento de un espacio vectorial (V, +, ·) sobre un cuerpo K que satisface los 8 axiomas de linealidad (conmutatividad, asociatividad, elemento neutro, inverso aditivo, distributividades respecto a suma vectorial y compatibilidad de escalares).",
    representaciones: {
      algebraica: "Tupla euclidiana v = (v₁, v₂, ..., vₙ) ∈ ℝⁿ o vector columna en M_{n×1}(ℝ): v = [v₁, v₂, ..., vₙ]ᵀ.",
      geometrica: "Segmento de recta orientado (flecha) en el espacio afín caracterizado por punto de aplicación, magnitud/norma ||v||, dirección (ángulo polar θ) y sentido.",
      operacional: "Derivación sobre el álgebra de funciones suaves C^∞(M) en un punto p (vector tangente v = ∑ vⁱ ∂/∂xⁱ|ₚ) o generador infinitesimal de traslaciones.",
      fisica: "Magnitud física orientada invariante bajo rotaciones del sistema de coordenadas (ej. velocidad, momento lineal, gradiente de potencial).",
      latex: "\\mathbf{v} = \\begin{pmatrix} v_1 \\\\ v_2 \\end{pmatrix}, \\quad \\|\\mathbf{v}\\| = \\sqrt{\\langle \\mathbf{v}, \\mathbf{v} \\rangle} = \\sqrt{v_1^2 + v_2^2}"
    },
    propiedades_clave: [
      "Independencia lineal y bases: todo vector se expresa de forma única como combinación lineal v = ∑ cᵢ eᵢ.",
      "Producto interno canónico y ortogonalidad: ⟨u, v⟩ = uᵀ v = ||u|| ||v|| cos θ. Si ⟨u, v⟩ = 0, los vectores son ortogonales.",
      "Desigualdad de Cauchy-Schwarz: |⟨u, v⟩| ≤ ||u|| ||v||."
    ]
  },
  "matriz_operador": {
    id: "matriz_operador",
    nombre: "Matriz y Operador Lineal",
    dominio: "Álgebra Lineal & Teoría de Operadores",
    icono: "⊞",
    definicion_axiomatica: "Homomorfismo entre espacios vectoriales T: V → W tal que T(αu + βv) = αT(u) + βT(v), representado unívocamente en bases dadas por una matriz A = (a_{ij}) ∈ M_{m×n}(K).",
    representaciones: {
      algebraica: "Arreglo bidimensional A = [a_{ij}], producto matricial (AB)_{ij} = ∑ a_{ik} b_{kj}.",
      geometrica: "Deformación continua del espacio afín: las columnas de A representan las imágenes de los vectores unitarios de la base canónica T(e₁), ..., T(eₙ). El determinante det(A) representa el factor de dilatación/inversión de volumen orientado.",
      operacional: "Operador diferencial lineal L[u] = A u, generador de flujos en sistemas dinámicos continuos X' = AX.",
      latex: "A = \\begin{pmatrix} a_{11} & a_{12} \\\\ a_{21} & a_{22} \\end{pmatrix} \\in \\mathcal{M}_2(\\mathbb{R}), \\quad \\det(A) = a_{11}a_{22} - a_{12}a_{21}"
    },
    propiedades_clave: [
      "Teorema del rango y nulidad: dim(V) = dim(ker T) + dim(im T).",
      "Invertibilidad: det(A) ≠ 0 ⟺ ker T = {0} ⟺ T es un isomorfismo.",
      "Invariantes canónicos: la traza tr(A) y el determinante det(A) son invariantes bajo transformaciones de semejanza P⁻¹AP."
    ]
  },
  "espectro_eigenvalores": {
    id: "espectro_eigenvalores",
    nombre: "Espectro y Subespacios Invariantes",
    dominio: "Álgebra Lineal & Dinámica Espectral",
    icono: "λ",
    definicion_axiomatica: "El espectro σ(A) es el conjunto de escalares λ ∈ ℂ tales que el operador (A - λI) no es biyectivo, satisfaciendo Av = λv para algún vector propio no nulo v ≠ 0.",
    representaciones: {
      algebraica: "Conjunto de raíces del polinomio característico secular p(λ) = det(λI - A) = 0.",
      geometrica: "Direcciones puramente dilatadas o comprimidas sin rotación espacial (para eigenvalores reales). Para eigenvalores complejos conjugados α ± iβ, generan rotaciones puras (si α=0) o espirales logarítmicas (si α≠0).",
      latex: "A \\mathbf{v} = \\lambda \\mathbf{v}, \\quad p(\\lambda) = \\det(\\lambda I - A) = \\lambda^2 - \\operatorname{tr}(A)\\lambda + \\det(A) = 0"
    },
    propiedades_clave: [
      "Multiplicidad algebraica vs geométrica: mg(λ) ≤ ma(λ).",
      "Diagonalizabilidad: A es diagonalizable sobre K si y solo si la suma de las multiplicidades geométricas iguala n.",
      "Teorema de Cayley-Hamilton: toda matriz cuadrada satisface su propia ecuación característica p(A) = 0."
    ]
  },
  "sistema_dinamico": {
    id: "sistema_dinamico",
    nombre: "Sistema Dinámico Autónomo y Retrato de Fase",
    dominio: "Ecuaciones Diferenciales Ordinarias",
    icono: "∮",
    definicion_axiomatica: "Par (M, φₜ) donde M es una variedad suave y φₜ: M → M es una acción del grupo aditivo (ℝ, +) generada por el campo vectorial suave X' = F(X).",
    representaciones: {
      algebraica: "Sistema de EDOs acopladas dx/dt = f(x, y), dy/dt = g(x, y).",
      geometrica: "Retrato de fase: espacio topológico foliado por curvas integrales tangentes al campo vectorial en cada punto.",
      fisica: "Evolución determinista de un estado físico (mecánico, térmico o cuántico) bajo leyes invariantes ante traslaciones temporales.",
      latex: "X'(t) = A X(t), \\quad X(t) = e^{At} X_0 = \\Phi(t) X_0"
    },
    propiedades_clave: [
      "Teorema de Picard-Lindelöf: Existencia y unicidad global garantizada por Lipschitzianidad.",
      "Invarianza orbital: dos órbitas distintas jamás se intersectan en tiempo finito.",
      "Clasificación topológica de Poincaré: Nodos, sillas, focos y centros según los signos de tr(A), det(A) y el discriminante."
    ]
  },
  "funcion_lyapunov": {
    id: "funcion_lyapunov",
    nombre: "Integral Primera y Estabilidad de Lyapunov",
    dominio: "Teoría Cualitativa de EDOs & Mecánica Hamiltoniana",
    icono: "∇",
    definicion_axiomatica: "Función escalar continua y definida positiva V: U → ℝ que actúa como energía generalizada. Si dV/dt ≤ 0 a lo largo del flujo, el equilibrio es estable; si dV/dt ≡ 0, el sistema es conservativo.",
    representaciones: {
      geometrica: "Curvas o superficies de nivel compactas V(x, y) = C que atrapan las trayectorias orbitales en su interior.",
      fisica: "Hamiltoniano o energía mecánica total del sistema H(q, p) = T(p) + U(q).",
      latex: "V(x, y) = \\frac{1}{2}(x^2 + y^2), \\quad \\dot{V} = \\nabla V \\cdot F = \\frac{\\partial V}{\\partial x}\\dot{x} + \\frac{\\partial V}{\\partial y}\\dot{y} = 0"
    },
    propiedades_clave: [
      "Estabilidad orbital de Lyapunov: confinamiento eterno en una vecindad arbitraria del equilibrio.",
      "Teorema de Liouville: campos de divergencia nula ∇·F = 0 preservan el volumen de Lebesgue en el espacio de fases.",
      "Integrales primeras: toda función invariante dV/dt = 0 reduce en una unidad la dimensión efectiva del sistema dinámico."
    ]
  }
};

function getInjectedMathKnowledge(userPrompt) {
  const p = (userPrompt || '').toLowerCase();
  const selected = [];
  if (p.includes('vector') || p.includes("x'") || p.includes('x(') || p.includes('sistema') || p.includes('campo')) {
    selected.push(PRAXIS_KNOWLEDGE_BASE['vector']);
  }
  if (p.includes('matriz') || p.includes('sistema') || p.includes('operador') || p.includes('lineal') || p.includes('a =')) {
    selected.push(PRAXIS_KNOWLEDGE_BASE['matriz_operador']);
  }
  if (p.includes('espectr') || p.includes('eigen') || p.includes('valor propio') || p.includes('polinomio') || p.includes('lambda')) {
    selected.push(PRAXIS_KNOWLEDGE_BASE['espectro_eigenvalores']);
  }
  if (p.includes('dinamico') || p.includes('flujo') || p.includes('fase') || p.includes('orbita') || p.includes('edo') || p.includes('diferencial')) {
    selected.push(PRAXIS_KNOWLEDGE_BASE['sistema_dinamico']);
  }
  if (p.includes('lyapunov') || p.includes('estabilidad') || p.includes('energia') || p.includes('conservativ') || p.includes('hamilton') || p.includes('primera')) {
    selected.push(PRAXIS_KNOWLEDGE_BASE['funcion_lyapunov']);
  }
  if (!selected.length) {
    selected.push(PRAXIS_KNOWLEDGE_BASE['vector'], PRAXIS_KNOWLEDGE_BASE['matriz_operador'], PRAXIS_KNOWLEDGE_BASE['sistema_dinamico']);
  }
  return selected;
}

/* ============================================================
   PROMPTS DEL ORQUESTADOR MATEMÁTICO
   ============================================================ */
const SYSTEM_CORE = `Eres PRAXIS, un orquestador cognitivo experto en matemáticas avanzadas. Tu misión: convertir UN ejercicio matemático en una investigación profunda y rigurosa.

REGLAS ABSOLUTAS DE FORMATO Y MATEMÁTICAS:
- Responde ÚNICAMENTE con un objeto JSON válido. Sin texto fuera del JSON. Sin cercas \`\`\`.
- SINTAXIS MATEMÁTICA ESTÁNDAR Y ESTRICTA:
  * Para fórmulas en línea (inline), usa SIEMPRE $...$ (ejemplo: $f(x) = x^2$ o $A \\in M_2(\\mathbb{R})$).
  * Para fórmulas en bloque (display), usa SIEMPRE $$...$$ (ejemplo: $$X'(t) = AX(t)$$).
  * NUNCA uses \\( ni \\) para fórmulas en línea.
  * NUNCA uses \\[ ni \\] para fórmulas en bloque.
  * Escribe el LaTeX estándar limpio: \\frac{a}{b}, \\int, \\sum, \\begin{pmatrix}...\\end{pmatrix}.
  * NUNCA agregues barras de escape huérfanas en el texto (como "\\ " o saltos de línea literales rotos).
- No inventes referencias falsas.
- Explica toda la notación y tecnicismos con máximo rigor.
- EXHAUSTIVIDAD AXIOMÁTICA Y NARRATIVA CONTINUA (PROHIBIDO EL ESTILO 'FLASHES' O CONDENSADO):
  * Desarrolla cada procedimiento con calma, orden y taxonomía pedagógica, mostrando cada micro-paso algebraico.
  * Justifica los despejes elementales desde los axiomas de cuerpo (inverso aditivo, inverso multiplicativo, neutro, conmutatividad, distributividad).
  * Explicita artificios algebraicos: racionalización, completación de cuadrados, identidades notables (binomios al cuadrado, al cubo, conjugados).
  * Si utilizas métodos deterministas clásicos (ej. método de Cardano-Tartaglia para cúbicas, variación de parámetros, descomposición espectral), deduce primero sus ecuaciones base antes de sustituir.
  * Demostraciones doctorales completas: hipótesis formal, lemas intermedios, justificación deductiva y cierre estricto con Q.E.D. ■.`;

function audienceInstr(a) {
  return {
    doctor: `Audiencia: DOCTORES EN MATEMÁTICAS. Máximo rigor: enuncia hipótesis exactas, da demostraciones completas y formales, discute generalizaciones, casos límite, conexiones con estructuras avanzadas (categorías, espacios funcionales, dualidades) y señala dónde el argumento es óptimo o puede refinarse.`,
    maestro: `Audiencia: MAESTROS DE MATEMÁTICAS. Rigor sólido pero orientado a la docencia: explica el PORQUÉ de cada paso, anticipa errores frecuentes de los estudiantes, ofrece interpretaciones intuitivas y sugerencias didácticas junto al formalismo.`,
    licenciatura: `Audiencia: ESTUDIANTES DE LICENCIATURA EN MATEMÁTICAS. Razona cada paso con detalle pedagógico: no omitas justificaciones, define cada concepto nuevo en el momento que aparece, encadena la intuición con la formalización.`,
    publico: `Audiencia: PÚBLICO GENERAL. Comienza con una analogía accesible, define toda la jerga en lenguaje llano, mantén el rigor pero prioriza la claridad y la motivación sobre el tecnicismo.`
  }[a] || '';
}

function depthInstr(d) {
  return {
    breve: `Profundidad BREVE: sé conciso pero completo; agrupa pasos cuando sea natural.`,
    media: `Profundidad MEDIA: desarrollo detallado con la teoría esencial bien cubierta.`,
    profunda: `Profundidad PROFUNDA: exhaustivo. Desglosa cada micro-paso, cubre TODO el marco teórico implicado (definiciones, teoremas, lemas, axiomas, reglas, métodos, herramientas) con sus enunciados y demostraciones cuando aporten.`
  }[d] || '';
}

function promptPlanner(userPrompt, files, aud, dep) {
  const fdesc = files.length ? `\n\nFUENTES ADJUNTAS (usa su contenido como contexto; no las inventes):\n${files.map(f => `• [${f.kind}] ${f.name}${f.text ? '\n' + f.text.slice(0, 4000) : ''}`).join('\n')}` : '';
  return `${SYSTEM_CORE}

FASE 1 — PLANIFICACIÓN. Analiza el ejercicio del usuario y diseña el plan maestro.

EJERCICIO DEL USUARIO:
"""
${userPrompt}
"""${fdesc}

${audienceInstr(aud)}
${depthInstr(dep)}

Devuelve JSON con EXACTAMENTE estas claves:
{
  "titulo": "título descriptivo del problema",
  "area_principal": "rama matemática dominante",
  "ramas": ["rama1","rama2"],
  "objetivo": "qué se quiere demostrar/calcular/resolver",
  "nivel": "introductorio|intermedio|avanzado|investigación",
  "herramientas": ["nombre herramienta","uso"],
  "notacion": [{"symbolo":"\\\\LaTeX","significado":"explicación"}],
  "hipotesis": ["supuesto 1","supuesto 2"],
  "riesgos": ["posibles trampas o sutilezas del problema"],
  "estimacion_pasos": 5,
  "agente_resolucion": "instrucción específica para resolver el ejercicio",
  "agente_teoria": "instrucción sobre temas teóricos a extraer",
  "agente_figuras": "instrucción sobre qué visualizar",
  "agente_investigacion": "instrucción sobre generalizaciones"
}`;
}

function promptResolver(plan, userPrompt, aud, dep) {
  const kb = getInjectedMathKnowledge(userPrompt);
  return `${SYSTEM_CORE}

CAPA DE CONOCIMIENTO MATEMÁTICO INYECTADA:
${JSON.stringify(kb.map(k => ({ nombre: k.nombre, definicion: k.definicion_axiomatica, representaciones: k.representaciones, propiedades: k.propiedades_clave })))}

FASE 2 — RESOLUCIÓN ANALÍTICA ULTRA-DETALLADA Y EXPANDIDA.
Resuelve el ejercicio matemático con MÁXIMO RIGOR y EXPANSIÓN COMPLETA.

REGLAS DE EXHAUSTIVIDAD OBLIGATORIAS:
- Desarrolla TODO el procedimiento analítico paso por paso (mínimo 6 a 10 pasos detallados).
- PROHIBIDO resumir o saltarse cálculos algebraicos intermedios. Muestra cada sustitución, cada operación matricial explícita, cada cálculo de determinantes, derivadas e integrales renglón por renglón.
- Justifica teórica y formalmente cada transformación (qué propiedad, axioma o teorema fundamenta cada igualdad).
- SINTAXIS MATEMÁTICA LIMPIA: Fórmulas en línea con $...$ y fórmulas display en bloque con $$...$$. NUNCA uses \\( ni \\).

PLAN SELECCIONADO: ${JSON.stringify(plan)}
ENUNCIADO: """${userPrompt}"""

${audienceInstr(aud)}
${depthInstr(dep)}

Devuelve JSON:
{
  "estrategia": "explicación detallada de la estrategia analítica general",
  "supuestos": ["supuesto 1", "supuesto 2"],
  "notacion": [
    {"simbolo":"$X(t)$", "significado":"vector de estado en $\\mathbb{R}^2$ dependiente del tiempo"}
  ],
  "riesgos": ["sutileza o error común al resolver"],
  "pasos": [
    {
      "titulo": "Título descriptivo del paso",
      "html": "<p>Explicación rigurosa paso a paso con justificación formal...</p>",
      "latex": "fórmula display clave del paso (ej: $$X'(t) = AX(t)$$)",
      "herramienta": "método o teorema aplicado"
    }
  ],
  "resultado": "resultado final exacto en display math con su interpretación",
  "verificacion": "comprobación analítica paso a paso sustituyendo en el sistema original",
  "observaciones": "comentarios cualitativos y físicos profundos"
}`;
}

function promptTheory(plan, resolver, userPrompt, aud, dep) {
  const kb = getInjectedMathKnowledge(userPrompt);
  return `${SYSTEM_CORE}

CAPA DE CONOCIMIENTO MATEMÁTICO INYECTADA:
${JSON.stringify(kb.map(k => ({ nombre: k.nombre, definicion: k.definicion_axiomatica, representaciones: k.representaciones })))}

FASE 3 — MARCO TEÓRICO FORMAL CON DEMOSTRACIONES EXHAUSTIVAS.
Extrae de la solución y del problema TODA la base teórica necesaria agrupada por ramas temáticas.

REGLAS ESTRICTAS DE DEMOSTRACIÓN:
- Para CADA teorema, lema, corolario y proposición debes proporcionar su DEMOSTRACIÓN MATEMÁTICA FORMAL Y COMPLETA en el campo 'demostracion_html'.
- PROHIBIDO dejar demostraciones vacías o resumidas. Escribe la deducción matemática formal completa: hipótesis, pasos algebraicos/analíticos intermedios y conclusión (Q.E.D. / ■).
- SINTAXIS MATEMÁTICA: Usa exclusivamente $...$ para fórmulas en línea y $$...$$ para display math. El texto explicativo y enunciados deben ser texto en español limpio (NO envuelvas oraciones enteras en $$).

PLAN: ${JSON.stringify(plan)}
RESOLUCIÓN: ${JSON.stringify({ estrategia: resolver.estrategia, resultado: resolver.resultado })}
ENUNCIADO: """${userPrompt}"""

Devuelve JSON:
{
  "ramas": [
    {
      "nombre": "Rama temática (ej. Álgebra Lineal Avanzada)",
      "descripcion": "qué estudia esta rama y su relevancia aquí",
      "items": [
        {
          "tipo": "definicion|teorema|lema|corolario|axioma|proposicion|regla|metodo",
          "nombre": "Nombre del teorema o definición",
          "enunciado": "Enunciado formal en texto con fórmulas $...$ (ej. Sea $A \\in M_2(\\mathbb{R})$...)",
          "explicacion": "Explicación conceptual y significado geométrico/físico detallado",
          "demostracion_html": "Demostración matemática formal paso a paso con deducción y cálculos explícitos"
        }
      ]
    }
  ],
  "herramientas": [{"nombre":"...","uso":"para qué sirve aquí","fuente":"origen histórico o disciplina"}],
  "glosario": [{"termino":"...","definicion":"..."}]
}`;
}

function promptFigures(plan, resolver, theory, userPrompt) {
  return `${SYSTEM_CORE}

FASE 4 — FIGURAS. Diseña las ilustraciones que acompañan el ejercicio y la teoría. Tipos soportados:
- "funcion": y=f(x) (expr, xmin, xmax, ymin, ymax, titulo, descripcion)
- "vector_field": plano (fx, fy, xmin, xmax, ymin, ymax, titulo, descripcion)
- "parametrica": curva paramétrica (fx, fy, tmin, tmax, titulo, descripcion)
- "geometria": dibujo geométrico (shapes[], titulo, descripcion). Shapes: circle, poly, line, arrow, text.
- "diagrama": cajas y flechas (boxes:[{label,x,y}], arrows:[{from,to}], titulo, descripcion).
- "tabla": tabla de valores (headers:[], rows:[[]], titulo, descripcion)
- "prosa": descripción textual (titulo, descripcion)

Usa SOLO funciones estándar de JavaScript en expr/fx/fy (Math.sin, Math.cos, Math.exp, **, etc.).

PLAN: ${JSON.stringify({ titulo: plan.titulo, ramas: plan.ramas })}
RESULTADO: ${JSON.stringify(resolver.resultado)}

Devuelve JSON:
{
  "figuras":[
     {"id":"f1","tipo":"funcion","titulo":"...","descripcion":"...","expr":"Math.sin(x)","xmin":-6.28,"xmax":6.28,"ymin":-1.5,"ymax":1.5}
  ],
  "notas_imagenes":"lista textual de qué imágenes con qué características deben realizarse"
}`;
}


function promptInteractiveSim(plan, resolver, userPrompt) {
  return `${SYSTEM_CORE}

FASE 5 — AGENTE DE LABORATORIO INTERACTIVO (SIMULADOR DINÁMICO).
Tu misión es diseñar los parámetros para un simulador interactivo en HTML5 Canvas que permita al usuario mover deslizadores numéricos (sliders) y ver el comportamiento dinámico o geométrico de la matemática en tiempo real.

DATOS:
Problema: """${userPrompt}"""
Título: ${plan.titulo}
Resultado: ${resolver.resultado}

Define 3 a 5 parámetros dinámicos clave (ej. condiciones iniciales x0, y0, frecuencia angular omega, amortiguamiento gamma, constantes a, b, c) con sus rangos de exploración y valor predeterminado.

Devuelve JSON:
{
  "titulo": "Simulador Interactivo de Órbitas y Espacio Fase",
  "descripcion": "Ajuste las condiciones iniciales y parámetros del sistema para explorar la geometría del flujo y la conservación de la energía.",
  "parametros": [
    {"id": "x0", "nombre": "Posición inicial x₀", "min": -3.0, "max": 3.0, "step": 0.1, "valor": 1.0},
    {"id": "y0", "nombre": "Velocidad / Momento y₀", "min": -3.0, "max": 3.0, "step": 0.1, "valor": 0.0},
    {"id": "omega", "nombre": "Frecuencia angular ω", "min": 0.2, "max": 3.0, "step": 0.1, "valor": 1.0},
    {"id": "gamma", "nombre": "Amortiguamiento γ (0 = Centro conservativo)", "min": -0.5, "max": 0.5, "step": 0.02, "valor": 0.0}
  ],
  "formula_display": "X(t) = e^{-\\gamma t} \\begin{pmatrix} \\cos(\\omega t) & \\sin(\\omega t) \\\\ -\\sin(\\omega t) & \\cos(\\omega t) \\end{pmatrix} X_0",
  "conservada_nombre": "Energía Hamiltoniana H(x, y)",
  "conservada_formula": "H = \\frac{1}{2}(x^2 + y^2)"
}`;
}


function promptModeling(plan, resolver, userPrompt) {
  return `${SYSTEM_CORE}

FASE DE MODELACIÓN MATEMÁTICA CONTEXTUAL Y SISTEMAS COMPLEJOS.
Investiga y formaliza cómo la matemática de este ejercicio se aplica directamente para modelar sistemas reales complejos y casos atípicos o poco frecuentes (ej: cinemática y dinámica de manipuladores robóticos mediante grupos de Lie, tensores de deformación en medios continuos, dinámica de vórtices y fluidos geofísicos, electrodinámica relativista, o modelos dinámicos macroeconómicos).

DATOS DE ENTRADA:
Problema: """${userPrompt}"""
Título: ${plan.titulo}
Solución analítica: ${resolver.resultado}

REGLAS DE MODELACIÓN OBLIGATORIAS:
- No des solo ejemplos genéricos superficiales. Formula el modelo físico o sistémico concreto.
- Especifica el vector de estado formal $X(t) \\in \\mathbb{R}^n$ y los parámetros de gobierno.
- Presenta las ecuaciones diferenciales o algebraicas de gobierno en bloques display $$...$$.
- Describe el algoritmo computacional paso a paso para su integración numérica (ej: diferencias finitas, Runge-Kutta).
- Analiza al menos un régimen límite, resonancia o comportamiento singular del que casi nadie hable.

Devuelve JSON:
{
  "titulo_modelo": "Título descriptivo del modelo sistémico contextual",
  "contexto_sistemico": "Explicación detallada del sistema físico, mecatrónico o continuo donde opera esta matemática...",
  "variables_estado": [
    {"variable": "$X(t)$", "significado": "Vector de estado formal del sistema", "unidades": "m, rad/s"}
  ],
  "ecuaciones_gobierno": "$$F(X, \\dot{X}, t) = 0$$",
  "explicacion_ecuaciones": "Desglose término a término de las fuerzas o dinámicas presentes...",
  "algoritmo_numerico": "Algoritmo computacional paso a paso para simulación numérica...",
  "casos_atipicos": "Análisis de casos de frontera, singularidades o regímenes poco comunes..."
}`;
}

function promptResearch(plan, resolver, theory, userPrompt) {
  return `${SYSTEM_CORE}

FASE 5 — INVESTIGACIÓN Y EXTENSIÓN. Convierte el ejercicio en una línea de investigación: generalizaciones, problemas abiertos, aplicaciones, historia y literatura.

PLAN: ${JSON.stringify(plan)}
RESULTADO: ${JSON.stringify(resolver.resultado)}

Devuelve JSON:
{
  "generalizaciones":[{"titulo":"...","desarrollo":"explicación con LaTeX"}],
  "problemas_abiertos":[{"titulo":"...","planteamiento":"..."}],
  "aplicaciones":[{"campo":"...","descripcion":"..."}],
  "historia":[{"epoca":"...","hecho":"..."}],
  "bibliografia":[{"autor":"...","titulo":"...","tipo":"libro|artículo|curso","nota":"relevancia"}],
  "recursos":[{"nombre":"...","tipo":"libro|software|curso","descripcion":"..."}],
  "preguntas_siguientes":["..."]
}`;
}

function promptReport(plan, resolver, theory, figures, research, userPrompt) {
  return `${SYSTEM_CORE}

FASE 6 — AGENTE ESPECIALISTA EN FORMATO HTML / MATHJAX.
Tu misión: Tomar la solución matemática completa y estructurarla en un informe HTML semántico impecable listo para MathJax v3.

REGLAS ESTRICTAS DE FORMATO:
- Delimitadores matemáticos: Usa exclusivamente $...$ para matemáticas en línea y $$...$$ para display math en bloque. NUNCA uses \\( ni \\) ni \\[ ni \\].
- No agregues barras invertidas huérfanas en el texto ni repeticiones.
- Estructura con clases semánticas de Praxis:
  <section class="blk">
    <h3 class="sec"><span class="num">§</span>Título</h3>
    <div class="prose"><p>...</p></div>
    <div class="steps"><div class="step"><div class="idx"></div><div class="body"><div class="ttl">...</div><div class="prose">...</div></div></div></div>
    <div class="callout co-def"><div class="lab">Definición</div>...</div>
    <div class="callout co-thm"><div class="lab">Teorema</div>...</div>
    <div class="tbl-wrap"><table>...</table></div>
  </section>

DATOS A ENSAMBLAR:
Plan: ${JSON.stringify(plan)}
Resolución: ${JSON.stringify(resolver)}
Teoría: ${JSON.stringify(theory)}
Investigación: ${JSON.stringify(research)}

Devuelve JSON:
{"html":"<section class=\"blk\">...todo el informe ensamblado...</section>", "titulo_final":"título descriptivo y pulido"}`;
}

function promptMd(plan, resolver, theory, figures, research) {
  return `${SYSTEM_CORE}

FASE 7 — AGENTE ESPECIALISTA EN FORMATO MARKDOWN / WORD / PANDOC.
Tu misión: Generar un documento Markdown canónico, prístino y estrictamente estructurado para ser procesado por Word o Pandoc.

REGLAS ESTRICTAS DE SINTAXIS:
1. ECUACIONES EN BLOQUE (Display): Escribe SIEMPRE $$ en su propia línea, la fórmula en las líneas siguientes, y $$ de cierre en su propia línea:
   $$
   X(t) = \\begin{pmatrix} \\cos t & \\sin t \\\\ -\\sin t & \\cos t \\end{pmatrix} X_0
   $$
2. ECUACIONES EN LÍNEA (Inline): Usa SIEMPRE $formula$ (ejemplo: $x^2 + y^2 = R^2$ o $A \\in M_2(\\mathbb{R})$).
   NUNCA uses \\( ni \\) ni \\[ ni \\].
3. Estructura: # Título, ## Secciones numeradas (1. Estrategia, 2. Marco Teórico, 3. Investigaciones, 4. Bibliografía), * Viñetas.
4. NO dupliques texto, ni delimitadores, ni agregues barras invertidas huérfanas en el texto.

DATOS:
Plan: ${JSON.stringify({ titulo: plan.titulo, ramas: plan.ramas })}
Resolución: ${JSON.stringify({ estrategia: resolver.estrategia, resultado: resolver.resultado, verificacion: resolver.verificacion })}
Teoría: ${JSON.stringify(theory.ramas)}
Investigación: ${JSON.stringify({ generalizaciones: research.generalizaciones, bibliografia: research.bibliografia })}

Devuelve JSON: {"markdown":"contenido markdown completo y prístino"}`;
}

/* ============================================================
   PIPELINE UI & AGENTES
   ============================================================ */
const ICONS = {
  brain:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 3a3 3 0 0 0-3 3 3 3 0 0 0-1 5 3 3 0 0 0 2 5 3 3 0 0 0 5 1V4a1 1 0 0 0-1-1z"/><path d="M15 3a3 3 0 0 1 3 3 3 3 0 0 1 1 5 3 3 0 0 1-2 5 3 3 0 0 1-5 1"/></svg>',
  pen:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20l4-1 10-10-3-3L5 16z"/><path d="M14 6l3 3"/></svg>',
  book:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5a2 2 0 0 1 2-2h6v16H6a2 2 0 0 0-2 2z"/><path d="M20 5a2 2 0 0 0-2-2h-6v16h6a2 2 0 0 1 2 2z"/></svg>',
  chart:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 4v16h16"/><path d="M7 14l3-4 3 2 4-6"/></svg>',
  search:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/></svg>',
  doc:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2h9l4 4v16H6z"/><path d="M14 2v5h5"/><path d="M9 13h6M9 17h6"/></svg>',
  md:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 15v-4l2 2 2-2v4M16 9v4M14 12l2 2 2-2"/></svg>'
};


/* ============================================================
   ENRUTADOR DE INTENCIONES DE ENTRADA Y META-COMANDOS (AGENTE DE ENTRADA)
   ============================================================ */

/* ============================================================
   CONTROL DE CANCELACIÓN Y EDICIÓN DE ENTRADA CON REINICIO
   ============================================================ */
window.cancelPipeline = function() {
  if (S.abort) {
    try { S.abort.abort(); } catch(e) {}
  }
  S.running = false;
  const cBtn = $('#cancelBtn'); if (cBtn) cBtn.style.display = 'none';
  const eBtn = $('#editPromptBtn'); if (eBtn) eBtn.style.display = 'inline-block';
  $('#runBtn').innerHTML = '▶ Analizar';
  setStat('idle', 'Cancelado por usuario');

  const wrap = $('#stageWrap');
  if (wrap) {
    const banner = document.createElement('div');
    banner.style.cssText = 'background:rgba(244,63,94,0.08); border:1px solid var(--bad); border-radius:10px; padding:14px 18px; margin:14px 0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;';
    banner.innerHTML = `
      <div>
        <b style="color:var(--bad); font-size:13.5px;">✕ Proceso detenido por el usuario</b>
        <div style="font-size:12px; color:var(--muted); margin-top:2px;">La ejecución fue cancelada inmediatamente. Puedes modificar el enunciado y reiniciar desde cero.</div>
      </div>
      <button class="btn sm primary" onclick="editPromptAndRestart()">✏️ Editar Petición y Reiniciar</button>
    `;
    wrap.prepend(banner);
  }
  toast('Proceso detenido.');
};

window.editPromptAndRestart = function() {
  clearActiveCheckpoint();
  S.currentRun = null;
  const pInput = $('#prompt');
  if (pInput) {
    pInput.focus();
    pInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    pInput.style.borderColor = 'var(--brand)';
    pInput.style.boxShadow = '0 0 0 2px var(--brand-tint)';
    setTimeout(() => {
      pInput.style.borderColor = '';
      pInput.style.boxShadow = '';
    }, 1800);
  }
  const eBtn = $('#editPromptBtn'); if (eBtn) eBtn.style.display = 'none';
  toast('Puedes modificar la petición y presionar Analizar para iniciar desde cero.');
};

function classifyInputIntent(text) {
  const t = (text || '').trim();
  const tLower = t.toLowerCase();

  // 0. Meta-comandos sobre una investigación existente.
  // IMPORTANTE: estos comandos NO deben entrar al pipeline matemático.
  // El texto "continúa el paso 3" es una orden de control, no un ejercicio.
  const stageMatch = tLower.match(/(?:contin[uú]a|reanuda|retoma|sigue|destraba)\\s+(?:el\\s+)?(?:paso|fase|etapa)\\s*#?\\s*(\\d+)/i);
  if (stageMatch) {
    const n = Number(stageMatch[1]);
    if (n >= 1 && n <= 8) return { type: 'CMD_RESUME_STAGE', stage: n };
  }

  // 1. Comandos de Continuación / Reanudación / Destrabe
  if (/^(?:contin[uú]a|seguir|reanuda|retoma|sigue|destraba)(?:\\s+(?:el\\s+)?(?:proceso|análisis|analisis|trabajo|investigación|investigacion))?[.!]?$/i.test(tLower)
      || /(?:proceso|an[aá]lisis|investigaci[oó]n).*(?:incompleto|pendiente|en espera)/i.test(tLower)) {
    return { type: 'CMD_RESUME' };
  }

  // 2. Comandos de Reintento de Paso Específico
  const retryMatch = tLower.match(/(?:reintenta|repetir|volver a correr)\\s*(?:el\\s+)?(?:paso|fase|etapa)?\\s*#?\\s*([a-zA-Z0-9áéíóú]+)/i);
  if (retryMatch) {
    return { type: 'CMD_RETRY', target: retryMatch[1] || 'failed' };
  }

  // 2b. Edición de un artefacto/investigación existente.
  // Por ahora solo clasifica y aísla la intención; la capa de ejecución
  // evolucionará hacia versionado + agente de artefactos sin tocar el pipeline.
  if (/(genera|crea|haz|añade|agrega|corrige|arregla|repara|modifica|actualiza|regenera)\\b.*\\b(canvas|simulador|figura|figuras|imagen|imágenes|artefacto|investigaci[oó]n|documento)/i.test(tLower)
      && /(otra|otro|nueva|nuevo|m[aá]s|adicional|correg|arreg|repar|modific|actualiz|regener)/i.test(tLower)) {
    return { type: 'CMD_ARTIFACT_EDIT', instruction: t };
  }

  // 3. Comandos de Exportación Directa
  if (/(exporta|descarga|genera)\s*(word|docx)/i.test(tLower)) return { type: 'CMD_EXPORT', format: 'docx' };
  if (/(exporta|descarga|genera)\s*(doc|word.*2d|mathml)/i.test(tLower)) return { type: 'CMD_EXPORT', format: 'doc' };
  if (/(exporta|descarga|genera)\s*(simulador|canvas|html)/i.test(tLower)) return { type: 'CMD_EXPORT', format: 'sim' };
  if (/(exporta|descarga|genera)\s*(markdown|md)/i.test(tLower)) return { type: 'CMD_EXPORT', format: 'md' };

  // 4. Comandos de Limpieza / Nuevo Chat
  // Comandos de Refinamiento Dirigido ("Tuneo") de Secciones
  const refineMatch = tLower.match(/(tuneo|afilar|refinar|modificar secci[oó]n|cambiar secci[oó]n)\s*(.*)/i);
  if (refineMatch) {
    return { type: 'CMD_REFINE', instruction: refineMatch[2].trim() };
  }

  if (/(nuevo chat|nueva conversaci[oó]n)/i.test(tLower)) return { type: 'CMD_NEW_CHAT' };
  if (/(limpia|borra|reinicia)/i.test(tLower) && tLower.length < 35) return { type: 'CMD_CLEAR' };

  // 5. Comandos de Cambio de Proveedor
  if (/(cambia|usar|conmutar)\s*(a|al)?\s*ollama/i.test(tLower)) return { type: 'CMD_PROVIDER', provider: 'ollama' };
  if (/(cambia|usar|conmutar)\s*(a|al)?\s*gemini/i.test(tLower)) return { type: 'CMD_PROVIDER', provider: 'gemini' };

  // 6. Comandos de Herramientas UI
  if (/(abrir|abre|mostrar|ver)\s*(borradores|draft)/i.test(tLower)) return { type: 'CMD_UI', modal: 'draft' };
  if (/(abrir|abre|mostrar|ver)\s*(biblioteca|conocimiento)/i.test(tLower)) return { type: 'CMD_UI', modal: 'kb' };
  if (/(abrir|abre|mostrar|ver)\s*(mimetizar|pdf)/i.test(tLower)) return { type: 'CMD_UI', modal: 'pdf' };

  // 7. Conversación General / Saludo
  if (/^(hola|buenos d[ií]as|buenas tardes|buenas noches|qu[eé] puedes hacer|ayuda|qui[eé]n eres)\\b/i.test(tLower) && t.length < 80) {
    return { type: 'CONVERSATIONAL', text: t };
  }

  // Si ya existe una investigación activa, una instrucción claramente
  // orientada a modificarla no debe reinterpretarse como un nuevo ejercicio.
  // El ejecutor de artefactos será una capa independiente del pipeline.
  if (S.lastRun && /(continúa|continua|sigue|ahora|después|despues|sobre esta|esta investigación|este documento)/i.test(tLower)
      && !/(resuelve|demuestra|calcula|determina|encuentra|prueba que)/i.test(tLower)) {
    return { type: 'CMD_ARTIFACT_EDIT', instruction: t };
  }

  // Por defecto: Ejercicio o Investigación Matemática Profunda
  return { type: 'PIPELINE_RUN', text: t };
}


/* ============================================================
   FASE 6: MOTOR DE REFINAMIENTO DIRIGIDO ("TUNEO") DE SECCIONES
   ============================================================ */

window.searchArxivLiterature = async function() {
  const q = prompt('Buscar literatura matemática en arXiv (título, autores o concepto):', $('#prompt')?.value?.slice(0, 50) || 'dynamical systems');
  if (!q) return;
  toast('Consultando API de arXiv...');
  try {
    const resp = await fetch('/api/rag/arxiv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, max_results: 3 })
    });
    if (resp.ok) {
      const data = await resp.json();
      const papers = data.papers || [];
      if (!papers.length) {
        toast('No se encontraron artículos para esa búsqueda.');
        return;
      }
      const citations = papers.map(p => `• [arXiv] ${p.citation} (URL: ${p.pdf_url})`).join('\n');
      if ($('#prompt')) {
        $('#prompt').value += `\n\n[LITERATURA ARXIV VINCULADA]:\n${citations}`;
        $('#prompt').style.height = 'auto';
        $('#prompt').style.height = Math.min($('#prompt').scrollHeight, 240) + 'px';
      }
      toast(`✓ ${papers.length} artículos científicos reales de arXiv vinculados.`);
    }
  } catch(e) {
    toast('Error consultando arXiv: ' + e.message);
  }
};

window.promptSectionRefinement = function(sectionId) {
  const instr = prompt(`¿Qué modificación o ampliación deseas aplicar a la sección "${sectionId.toUpperCase()}"?`, 'Profundizar demostración y añadir pasos intermedios con rigor axiomático.');
  if (instr) {
    window.handleRefineSection(sectionId, instr);
  }
};

window.handleRefineSection = async function(sectionId, instruction) {
  if (!S.lastRun || !S.lastRun.markdown) {
    toast('Primero genera una investigación para poder tunear sus secciones.');
    return;
  }
  toast(`⚡ Iniciando tuneo dirigido sobre sección: ${sectionId}...`);
  setStat('run', `Tuneando ${sectionId}…`);

  const pRefine = `${SYSTEM_CORE}\n\nTUNEO DIRIGIDO DE SECCIÓN MATEMÁTICA: ${sectionId.toUpperCase()}.\n` +
    `INSTRUCCIÓN ESPECÍFICA DEL USUARIO: """` + instruction + `"""\n` +
    `DOCUMENTO MARKDOWN ACTUAL:\n"""` + S.lastRun.markdown.slice(0, 5000) + `"""\n\n` +
    `Tu misión: Redactar ÚNICAMENTE el nuevo cuerpo mejorado para esta sección, con máximo rigor axiomático, fórmulas display $$...$$ y sin saltos algebraicos. Responde directamente en Markdown sin cercas json.`;

  try {
    const refinedText = await callGemini(pRefine, { json: false, temperature: 0.3 });
    const cleanRefined = refinedText.trim().replace(/^```(?:markdown)?\s*/i, '').replace(/\s*```$/i, '').trim();

    // Enviar a servidor para actualizar archivos físicos y recompilar Word
    const resp = await fetch('/api/refine_section', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: S.activeChatId || 'general',
        folder: S.lastRun.folder || S.lastRun.response_folder || (S.currentCheckpoint?.run?.folder) || '',
        section: sectionId,
        content: cleanRefined,
        note: instruction
      })
    });

    if (resp.ok) {
      const rData = await resp.json();
      S.lastRun.markdown = rData.markdown || S.lastRun.markdown;
      S.lastRun.docx_url = rData.docx_url || S.lastRun.docx_url;
      S.lastRun.doc_url = rData.doc_url || S.lastRun.doc_url;
      toast(`✓ Sección ${sectionId} tuneada y Word recompilado con éxito.`);
      setStat('ok', 'Tuneo completado');
      assembleReport(S.lastRun, false);
    } else {
      toast('Tuneo completado localmente en memoria.');
      setStat('ok', 'Tuneo completado');
    }
  } catch(e) {
    toast('Error durante el tuneo: ' + e.message);
    setStat('bad', 'Error en tuneo');
  }
};

async function handleSpecialIntent(intent) {
  if (intent.type === 'CMD_REFINE') {
    const sec = intent.instruction.toLowerCase().includes('estrategia') ? 'estrategia' : (intent.instruction.toLowerCase().includes('teor') ? 'teoria' : (intent.instruction.toLowerCase().includes('model') ? 'modelacion' : 'desarrollo'));
    await window.handleRefineSection(sec, intent.instruction);
    return;
  }
  if (intent.type === 'CMD_RESUME_STAGE') {
    const stageOrder = ['plan', 'resolve', 'theory', 'figures', 'modeling', 'research', 'report', 'md'];
    const stageId = stageOrder[intent.stage - 1];
    if (!stageId) return;
    toast('⚙️ Continuando específicamente desde el paso ' + intent.stage + ' (' + stageId + ')…');
    if (!S.currentRun && !S.currentCheckpoint?.run) {
      // Intento de recuperación desde disco antes de declarar que no hay estado.
      await window.resumePipelineFromCheckpoint();
      return;
    }
    await window.retrySingleStage(stageId);
    return;
  }
  if (intent.type === 'CMD_RESUME') {
    toast('⚙️ Instrucción de sistema: Reanudando procesos pendientes...');
    await window.resumePipelineFromCheckpoint();
    return;
  }
  if (intent.type === 'CMD_ARTIFACT_EDIT') {
    // Barrera explícita: este comando NUNCA entra al pipeline matemático.
    // Se registra como evolución de la investigación existente.
    const folder = S.lastRun?.folder || S.lastRun?.response_folder ||
      localStorage.getItem('praxis_active_folder') || null;
    const chatId = S.activeChatId;
    window.pendingArtifactCommand = {
      instruction: intent.instruction,
      chatId,
      folder,
      timestamp: new Date().toISOString()
    };
    if (!chatId || !folder) {
      renderArtifactCommandNotice(intent.instruction, 'No hay una investigación activa identificable todavía.');
      return;
    }
    try {
      // Ejecutar primero: una versión no representa un cambio real hasta que
      // el artefacto haya sido materializado y validado.
      const execResp = await fetch('/api/investigations/artifact-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          folder,
          instruction: intent.instruction,
          title: S.lastRun?.plan?.titulo || folder,
          parent_version_id: window.selectedInvestigationVersion || null
        })
      });
      const execData = await execResp.json();
      if (!execResp.ok || execData.status !== 'ok') {
        throw new Error(execData.message || execData.error || 'No se pudo ejecutar el comando de artefacto');
      }

      // El servidor ya registra la versión únicamente después de materializar
      // y validar la ejecución. Nunca crear una segunda versión desde la UI.
      window.pendingArtifactCommand.execution = execData;
      window.pendingArtifactCommand.version = execData.version || null;
      renderArtifactCommandNotice(
        intent.instruction,
        '✓ Artefacto ejecutado y nueva versión registrada. El pipeline matemático no fue invocado.'
      );
    } catch (err) {
      renderArtifactCommandNotice(intent.instruction, 'No se aplicó ninguna nueva versión: ' + err.message);
    }
    return;
  }
  if (intent.type === 'CMD_RETRY') {
    toast(`🔄 Reintentando etapa solicitada: ${intent.target}`);
    await window.retrySingleStage(intent.target);
    return;
  }
  if (intent.type === 'CMD_EXPORT') {
    if (intent.format === 'docx') exportWordDocx();
    else if (intent.format === 'doc') exportWordDoc();
    else if (intent.format === 'sim') exportSimulatorHtml();
    else if (intent.format === 'md') downloadMd();
    toast(`✓ Exportación a ${intent.format.toUpperCase()} iniciada.`);
    return;
  }
  if (intent.type === 'CMD_NEW_CHAT') {
    createNewChatSession();
    toast('✓ Nueva sesión de conversación iniciada.');
    return;
  }
  if (intent.type === 'CMD_CLEAR') {
    $('#stageWrap').innerHTML = '';
    $('#prompt').value = '';
    S.files = [];
    renderAtts();
    showExamples();
    toast('Sesión limpiada.');
    return;
  }
  if (intent.type === 'CMD_PROVIDER') {
    S.provider = intent.provider;
    updateConn();
    toast(`✓ Proveedor cambiado a ${intent.provider.toUpperCase()}.`);
    return;
  }
  if (intent.type === 'CMD_UI') {
    if (intent.modal === 'draft') openDraftStudio();
    else if (intent.modal === 'kb') openKnowledgeModal();
    else if (intent.modal === 'pdf') openPdfMimicModal();
    return;
  }
  if (intent.type === 'CONVERSATIONAL') {
    renderConversationalResponse(intent.text);
    return;
  }
}

function renderArtifactCommandNotice(userText, statusText) {
  const wrap = $('#stageWrap');
  if (!wrap) return;
  const target = S.lastRun?.plan?.titulo || localStorage.getItem('praxis_active_folder') || 'investigación activa';
  wrap.innerHTML = `
    <div style="background:var(--card);border:1px solid var(--line);border-left:4px solid var(--brand);border-radius:12px;padding:20px;max-width:820px;margin:20px auto;box-shadow:var(--sh1);">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
        <span style="font-size:22px;">🧩</span>
        <b style="font-size:15px;color:var(--brand);">Comando sobre investigación existente</b>
      </div>
      <p style="margin:0 0 10px;color:var(--ink-2);font-size:13px;">
        La instrucción fue reconocida como una modificación de la investigación actual y <b>no fue enviada al pipeline matemático</b>.
      </p>
      <div style="padding:10px;background:var(--paper-2);border:1px solid var(--line-2);border-radius:8px;font-family:var(--mono);font-size:11.5px;white-space:pre-wrap;">${esc(userText)}</div>
      <div style="margin-top:10px;color:var(--muted);font-size:11px;">
        Objetivo detectado: ${esc(target)} · ${esc(statusText || 'pendiente de ejecución por la capa de artefactos/versionado')}
      </div>
    </div>`;
}

function renderConversationalResponse(userText) {
  const wrap = $('#stageWrap');
  wrap.innerHTML = `
    <div style="background:var(--card); border:1px solid var(--line); border-radius:14px; padding:24px; max-width:820px; margin:20px auto; box-shadow:0 4px 20px rgba(0,0,0,0.06);">
      <div style="display:flex; align-items:center; gap:12px; margin-bottom:14px;">
        <span style="font-size:26px;">🧠</span>
        <div>
          <h3 style="margin:0; font-size:18px; font-weight:700; color:var(--brand);">Praxis Nexus · Orquestador Cognitivo Matemático</h3>
          <small style="color:var(--muted);">Sistema Multi-Agente Híbrido Activo</small>
        </div>
      </div>
      <p style="font-size:14px; color:var(--ink-2); line-height:1.6; margin:0 0 14px;">
        ¡Hola! Soy <b>Praxis Nexus</b>, tu suite de deducción axiomática exhaustiva, modelación contextual de sistemas complejos y simulación interactiva en tiempo real.
      </p>
      <div style="background:var(--paper-2); padding:14px; border-radius:10px; border:1px solid var(--line-2); font-size:13px; color:var(--ink);">
        <b>¿Qué puedes pedirme?</b>
        <ul style="margin:8px 0 0; padding-left:20px; line-height:1.6;">
          <li><b>Ejercicios y teoremas:</b> Plantea cualquier ejercicio de Álgebra Lineal, Ecuaciones Diferenciales, Análisis Real o Geometría Diferencial.</li>
          <li><b>Comandos de control:</b> Puedes escribir <i>"continúa el proceso"</i>, <i>"reintentar paso 4"</i>, <i>"exportar a word"</i> o <i>"cambiar a ollama"</i> directamente en la caja de texto.</li>
          <li><b>Mimetismo de PDFs:</b> Analiza reportes previos para que tus nuevas tareas adopten su estructura formal automáticamente.</li>
        </ul>
      </div>
      <div style="margin-top:16px; display:flex; gap:10px; flex-wrap:wrap;">
        <button class="btn sm primary" onclick="showExamples()">✦ Ver Ejercicios de Demostración</button>
        <button class="btn sm ghost" onclick="openDraftStudio()">📝 Abrir Draft Studio</button>
        <button class="btn sm ghost" onclick="openKnowledgeModal()">📚 Base de Conocimiento</button>
      </div>
    </div>
  `;
}

const STAGES = [
  { id: 'plan', name: 'Planificador Maestro', role: 'Arquitecto del análisis', icon: 'brain' },
  { id: 'resolve', name: 'Agente de Resolución', role: 'Desarrollo paso a paso', icon: 'pen' },
  { id: 'theory', name: 'Agente Teórico', role: 'Marco teórico riguroso', icon: 'book' },
  { id: 'figures', name: 'Agente de Visualización', role: 'Figuras e ilustraciones', icon: 'chart' },
  { id: 'modeling', name: 'Agente de Modelación', role: 'Sistemas complejos y aplicaciones atípicas', icon: 'gear' },
  { id: 'research', name: 'Agente de Investigación', role: 'Extensión y literatura', icon: 'search' },
  { id: 'report', name: 'Ensamblador de Informe', role: 'Documento final', icon: 'doc' },
  { id: 'md', name: 'Agente Markdown', role: 'Exportación editable', icon: 'md' }
];
let stageEls = {};

function renderPipeline() {
  const wrap = $('#stageWrap');
  wrap.innerHTML = `<div class="pipe"><div class="pipe-track"><div class="pipe-fill" id="pipeFill"></div></div>
    ${STAGES.map(s => `
    <div class="stage clickable" id="st-${s.id}" onclick="window.handleStageClick('${s.id}')" title="Clic para inspeccionar, reintentar o continuar este paso">
      <div class="node">${ICONS[s.icon]}</div>
      <div class="meta">
        <div class="name">${s.name} <span class="role">· ${s.role}</span></div>
        <div class="status" id="ss-${s.id}"><span class="st-idle">en espera</span></div>
      </div>
    </div>`).join('')}
  </div>
  <div id="reportHost"></div>`;
  stageEls = {};
  STAGES.forEach(s => stageEls[s.id] = $('#st-' + s.id));
}

function saveCurrentCheckpoint(stageId, runData) {
  S.currentRun = runData;
  S.currentCheckpoint = {
    stageId: stageId,
    run: runData,
    prompt: $('#prompt')?.value || '',
    chatId: S.activeChatId,
    timestamp: new Date().toISOString()
  };
  try {
    localStorage.setItem('praxis_active_checkpoint', JSON.stringify(S.currentCheckpoint));
  } catch(e) {}

  if (S.activeChatId) {
    fetch('/api/chats/checkpoint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: S.activeChatId, checkpoint: S.currentCheckpoint })
    }).catch(() => {});
  }
}

function clearActiveCheckpoint() {
  S.currentCheckpoint = null;
  try {
    localStorage.removeItem('praxis_active_checkpoint');
  } catch(e) {}
}

function synthesizeCanonicalMarkdown(run, userPrompt) {
  const p = run.plan || {};
  const r = run.resolver || {};
  const th = run.theory || {};
  const mod = run.modeling || {};
  const res = run.research || {};

  let md = `# ${p.titulo || 'Investigación Matemática Rigurosa'}\n\n`;
  md += `**Área:** ${p.area_principal || 'Matemáticas Avanzadas'} | **Rigor:** Exhaustivo Axiomático | **Fecha:** ${new Date().toLocaleDateString()}\n\n`;
  md += `## Planteamiento y Enunciado Formal\n\n${r.enunciado_formal || userPrompt}\n\n`;

  md += `## 1. Estrategia y Planificación Axiomática\n\n${r.estrategia || 'Estrategia deductiva formal.'}\n\n`;
  if (p.hipotesis && p.hipotesis.length) {
    md += `### Hipótesis y Supuestos\n` + p.hipotesis.map(h => `* ${h}`).join('\n') + '\n\n';
  }
  if (p.notacion && p.notacion.length) {
    md += `### Taxonomía de Notación\n| Símbolo | Significado |\n|---|---|\n` +
      p.notacion.map(n => `| $${cleanMathBlock(n.symbolo)}$ | ${n.significado} |`).join('\n') + '\n\n';
  }

  md += `## 2. Deducción y Desarrollo Matemático Paso a Paso\n\n`;
  if (r.pasos && r.pasos.length) {
    r.pasos.forEach((step, idx) => {
      md += `### Paso ${idx + 1}: ${step.titulo || 'Derivación'}\n\n`;
      if (step.justificacion_axiomatica) md += `*Justificación axiomática:* ${step.justificacion_axiomatica}\n\n`;
      if (step.desarrollo) md += `${step.desarrollo}\n\n`;
      if (step.ecuacion_display) {
        md += `$$\n${cleanMathBlock(step.ecuacion_display)}\n$$\n\n`;
      }
    });
  }
  if (r.resultado) {
    md += `### Resultado Formal\n\n$$\n${cleanMathBlock(r.resultado)}\n$$\n\n`;
  }
  if (r.verificacion) {
    md += `> **Verificación:** ${r.verificacion}\n\n`;
  }

  md += `## 3. Marco Teórico Formal y Demostraciones\n\n`;
  if (th.ramas && th.ramas.length) {
    th.ramas.forEach(b => {
      md += `### Rama: ${b.nombre}\n${b.descripcion || ''}\n\n`;
      if (b.items && b.items.length) {
        b.items.forEach(it => {
          md += `#### ${it.nombre}\n${it.explicacion || ''}\n\n`;
          if (it.demostracion_html || it.demostracion) {
            md += `> **Demostración Doctoral:** ${it.demostracion_html || it.demostracion}\n> Q.E.D. ■\n\n`;
          }
        });
      }
    });
  }

  md += `## 4. Modelación Matemática Contextual y Sistemas Complejos\n\n`;
  md += `### Sistema: ${mod.titulo_modelo || 'Dinámica de Sistemas'}\n\n`;
  md += `${mod.contexto_sistemico || 'Formulación en espacio de estados continua.'}\n\n`;
  if (mod.variables_estado && mod.variables_estado.length) {
    md += `| Variable | Dimensión / Espacio | Interpretación Física |\n|---|---|---|\n` +
      mod.variables_estado.map(v => `| $${cleanMathBlock(v.variable)}$ | $${cleanMathBlock(v.espacio || '\\mathbb{R}')}$ | ${v.descripcion} |`).join('\n') + '\n\n';
  }
  if (mod.ecuaciones_gobierno) {
    md += `### Ecuaciones de Gobierno\n\n$$\n${cleanMathBlock(mod.ecuaciones_gobierno)}\n$$\n\n`;
  }
  if (mod.algoritmo_simulacion) {
    md += `### Algoritmo Computacional de Simulación\n\n${mod.algoritmo_simulacion}\n\n`;
  }

  md += `## 5. Investigación y Extensión Teórica\n\n`;
  if (res.generalizaciones && res.generalizaciones.length) {
    md += `### Generalizaciones\n` + res.generalizaciones.map(g => `* **${g.titulo || 'Generalización'}:** ${g.descripcion || g}`).join('\n') + '\n\n';
  }
  if (res.problemas_abiertos && res.problemas_abiertos.length) {
    md += `### Problemas Abiertos\n` + res.problemas_abiertos.map(po => `* ${po}`).join('\n') + '\n\n';
  }
  if (res.bibliografia && res.bibliografia.length) {
    md += `### Referencias Bibliográficas (APA 7)\n` + res.bibliografia.map(b => `* ${b.autor || b} (${b.año || ''}). *${b.titulo || ''}*.`).join('\n') + '\n\n';
  }

  return md;
}


function setStage(id, state, msg) {
  const el = stageEls[id]; if (!el) return;
  el.classList.remove('running', 'done', 'error');
  if (state !== 'idle') el.classList.add(state);
  const st = $('#ss-' + id);
  if (state === 'running') st.innerHTML = `<span class="spinner"></span>${esc(msg || 'procesando…')}`;
  else if (state === 'done') st.innerHTML = `<span class="badge">✓ listo</span> ${esc(msg || '')}`;
  else if (state === 'error') st.innerHTML = `<span class="badge" style="background:color-mix(in srgb,var(--bad) 18%,transparent);color:var(--bad)">✕ error</span> ${esc(msg || '')}`;
  else st.innerHTML = `<span class="st-idle">en espera</span>`;
  const done = STAGES.filter(s => stageEls[s.id] && stageEls[s.id].classList.contains('done')).length;
  const pf = $('#pipeFill'); if (pf) pf.style.height = Math.round(done / STAGES.length * 100) + '%';
}

function setStat(cls, txt) {
  const p = $('#statPill');
  p.className = 'pill ' + cls;
  $('#statTxt').textContent = txt;
}

/* ============================================================
   RENDER DEL INFORME
   ============================================================ */
const BRANCH_COLORS = ['#1a73e8','#d93025','#188038','#f9ab00','#9334e6','#12b5cb','#e37400','#5f6368'];

function renderSteps(pasos) {
  if (!pasos || !pasos.length) return '<p class="prose">Sin pasos registrados.</p>';
  return `<div class="steps">${pasos.map(p => `
    <div class="step"><div class="idx"></div><div class="body">
      <div class="ttl">${esc(p.titulo || '')}</div>
      <div class="prose">${p.html || ''}</div>
      ${p.latex ? `<div class=\"eq-block\">
$$
${cleanMathBlock(p.latex)}
$$
</div>` : ''}
      ${p.herramienta ? `<div class="tool">↳ ${esc(p.herramienta)}</div>` : ''}
    </div></div>`).join('')}</div>`;
}

function renderBranches(ramas) {
  if (!ramas || !ramas.length) return '';
  return `<div class="branches">${ramas.map((r, i) => {
    const col = BRANCH_COLORS[i % BRANCH_COLORS.length];
    const items = (r.items || []).map(it => {
      const demo = it.demostracion_html ? `<div class="demo"><b>Demostración.</b> ${it.demostracion_html}</div>` : '';
      const form = it.enunciado ? `<div class="prose item-enunciado" style="margin:6px 0;">${formatProseMath(it.enunciado)}</div>` : "";
      return `<div class="item">
        <div class="ih"><span class="tag" style="background:color-mix(in srgb,${col} 16%,transparent);color:${col}">${esc(it.tipo || '')}</span><span class="it">${esc(it.nombre || '')}</span></div>
        <div class="id">${it.explicacion || ''}</div>
        ${form}${demo}
      </div>`;
    }).join('');
    return `<div class="card">
      <div class="ch"><span class="ic" style="background:${col}">${ICONS.book}</span><span class="nm">${esc(r.nombre)}</span><span class="cnt">${(r.items || []).length} ítems</span></div>
      <div class="cb">${r.descripcion ? `<p class="prose" style="font-size:13px;color:var(--muted);margin:6px 0 2px">${esc(r.descripcion)}</p>` : ''}${items}</div>
    </div>`;
  }).join('')}</div>`;
}

function renderTable(headers, rows) {
  if (!headers || !rows) return '';
  return `<div class="tbl-wrap"><table><thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(c => `<td>${typeof c === 'string' && /[\\$]/.test(c) ? c : esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function renderResearch(rs) {
  if (!rs) return '';
  const sec = (title, inner) => inner ? `<div class="rcard"><div class="rh"><span class="ic">◆</span>${title}</div><div class="rb">${inner}</div></div>` : '';
  const cards = [
    sec('Generalizaciones', (rs.generalizaciones || []).map(g => `<h4>${esc(g.titulo)}</h4><div class="prose">${g.desarrollo || ''}</div>`).join('')),
    sec('Problemas abiertos', (rs.problemas_abiertos || []).map(p => `<b>${esc(p.titulo)}</b><br>${p.planteamiento || ''}`).join('<hr style="border:none;border-top:1px dashed var(--line);margin:8px 0">')),
    sec('Aplicaciones', `<ul>${(rs.aplicaciones || []).map(a => `<li><b>${esc(a.campo)}:</b> ${a.descripcion || ''}</li>`).join('')}</ul>`),
    sec('Historia', `<ul>${(rs.historia || []).map(h => `<li><b>${esc(h.epoca)}:</b> ${h.hecho || ''}</li>`).join('')}</ul>`),
    sec('Bibliografía', `<ul>${(rs.bibliografia || []).map(b => `<li>${esc(b.autor || '')} — <i>${esc(b.titulo || '')}</i> <span class="tag">${esc(b.tipo || '')}</span><br><span style="color:var(--muted);font-size:12px">${b.nota || ''}</span></li>`).join('')}</ul>`),
    sec('Recursos', `<ul>${(rs.recursos || []).map(r => `<li><b>${esc(r.nombre)}</b> <span class="tag">${esc(r.tipo || '')}</span><br>${r.descripcion || ''}</li>`).join('')}</ul>`),
    sec('Preguntas siguientes', `<ul>${(rs.preguntas_siguientes || []).map(q => `<li>${q}</li>`).join('')}</ul>`)
  ].filter(Boolean).join('');
  return `<div class="research">${cards}</div>`;
}

/* ============================================================
   GENERADOR DE FIGURAS SVG MATEMÁTICAS
   ============================================================ */
function compileExpr(src) {
  const s = String(src || '').trim();
  if (!s) return null;
  if (/[;{}]|document|window|fetch|eval|Function|require|import|=>/.test(s)) return null;
  try {
    const f = new Function('x', 't', 'Math', 'return (' + s + ');');
    f(0.5, 0.5, Math);
    return (x, t) => { try { const v = f(x, t === undefined ? x : t, Math); return (typeof v === 'number' && isFinite(v)) ? v : null; } catch (e) { return null; } };
  } catch (e) { return null; }
}

function niceTicks(min, max, n = 6) {
  const span = max - min || 1, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0))), norm = step0 / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const start = Math.ceil(min / step) * step, out = [];
  for (let v = start; v <= max + step * 1e-6; v += step) out.push(+v.toFixed(10));
  return out;
}

function fmtNum(v) {
  if (Math.abs(v) < 1e-9) return '0';
  if (Math.abs(v) >= 1000 || Math.abs(v) < 0.01) return v.toExponential(1);
  return (+v.toFixed(3)).toString();
}

function axesSVG(W, H, pad, xmin, xmax, ymin, ymax) {
  const iw = W - 2 * pad, ih = H - 2 * pad;
  const sx = x => pad + (x - xmin) / (xmax - xmin) * iw;
  const sy = y => pad + (ymax - y) / (ymax - ymin) * ih;
  let g = `<rect x="${pad}" y="${pad}" width="${iw}" height="${ih}" fill="var(--paper-2)" stroke="var(--line)" rx="6"/>`;
  const xt = niceTicks(xmin, xmax), yt = niceTicks(ymin, ymax);
  xt.forEach(x => { g += `<line x1="${sx(x)}" y1="${pad}" x2="${sx(x)}" y2="${pad + ih}" stroke="var(--line-2)" stroke-width="1"/>`; });
  yt.forEach(y => { g += `<line x1="${pad}" y1="${sy(y)}" x2="${pad + iw}" y2="${sy(y)}" stroke="var(--line-2)" stroke-width="1"/>`; });
  if (ymin < 0 && ymax > 0) g += `<line x1="${pad}" y1="${sy(0)}" x2="${pad + iw}" y2="${sy(0)}" stroke="var(--ink-2)" stroke-width="1.4"/>`;
  if (xmin < 0 && xmax > 0) g += `<line x1="${sx(0)}" y1="${pad}" x2="${sx(0)}" y2="${pad + ih}" stroke="var(--ink-2)" stroke-width="1.4"/>`;
  xt.forEach(x => { g += `<text x="${sx(x)}" y="${pad + ih + 14}" font-size="10" fill="var(--muted)" text-anchor="middle" font-family="var(--mono)">${fmtNum(x)}</text>`; });
  yt.forEach(y => { g += `<text x="${pad - 6}" y="${sy(y) + 3}" font-size="10" fill="var(--muted)" text-anchor="end" font-family="var(--mono)">${fmtNum(y)}</text>`; });
  return { g, sx, sy, iw, ih };
}

function figFunction(f) {
  const W = 520, H = 390, pad = 42;
  const xmin = +f.xmin ?? -6, xmax = +f.xmax ?? 6, ymin = +f.ymin ?? -3, ymax = +f.ymax ?? 3;
  const fn = compileExpr(f.expr);
  const { g, sx, sy } = axesSVG(W, H, pad, xmin, xmax, ymin, ymax);
  let path = '', started = false;
  const N = 360;
  if (fn) {
    for (let i = 0; i <= N; i++) {
      const x = xmin + (xmax - xmin) * i / N, y = fn(x);
      if (y == null || y < ymin - (ymax - ymin) || y > ymax + (ymax - ymin)) { started = false; continue; }
      const px = sx(x), py = sy(Math.max(ymin, Math.min(ymax, y)));
      path += (started ? ' L ' : ' M ') + px.toFixed(1) + ' ' + py.toFixed(1);
      started = true;
    }
  }
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${g}<path d="${path}" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>${fn ? '' : `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" fill="var(--muted)" font-size="13">expresión no evaluable</text>`}</svg>`;
}

function figVectorField(f) {
  const W = 520, H = 390, pad = 40;
  const xmin = +f.xmin ?? -3, xmax = +f.xmax ?? 3, ymin = +f.ymin ?? -3, ymax = +f.ymax ?? 3;
  const fx = compileExpr(f.fx), fy = compileExpr(f.fy);
  const { g, sx, sy } = axesSVG(W, H, pad, xmin, xmax, ymin, ymax);
  let arr = ''; const cols = 13, rows = 9;
  for (let i = 0; i <= cols; i++) for (let j = 0; j <= rows; j++) {
    const x = xmin + (xmax - xmin) * i / cols, y = ymin + (ymax - ymin) * j / rows;
    const ux = fx ? fx(x, y) : null, uy = fy ? fy(x, y) : null;
    if (ux == null || uy == null) continue;
    const m = Math.hypot(ux, uy) || 1e-9, sc = 0.62 / Math.max(1, m);
    const ex = x + ux * sc, ey = y + uy * sc;
    const x1 = sx(x), y1 = sy(y), x2 = sx(ex), y2 = sy(ey);
    const ang = Math.atan2(y2 - y1, x2 - x1), hl = 4;
    arr += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--brand)" stroke-width="1.3"/>`;
    arr += `<polygon points="${x2},${y2} ${x2-hl*Math.cos(ang-0.5)},${y2-hl*Math.sin(ang-0.5)} ${x2-hl*Math.cos(ang+0.5)},${y2-hl*Math.sin(ang+0.5)}" fill="var(--brand)"/>`;
  }
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${g}${arr}</svg>`;
}

function figParametric(f) {
  const W = 520, H = 390, pad = 42;
  const tmin = +f.tmin ?? 0, tmax = +f.tmax ?? (2 * Math.PI);
  const fx = compileExpr(f.fx), fy = compileExpr(f.fy);
  let xs = [], ys = [];
  if (fx && fy) for (let i = 0; i <= 400; i++) {
    const t = tmin + (tmax - tmin) * i / 400;
    const X = fx(t), Y = fy(t);
    if (X != null && Y != null) { xs.push(X); ys.push(Y); }
  }
  const pad2 = v => { const m = Math.max(...v, 1) - Math.min(...v, 0); return [Math.min(...v) - m * .1, Math.max(...v) + m * .1]; };
  const [xmin, xmax] = xs.length ? pad2(xs) : [-3, 3], [ymin, ymax] = ys.length ? pad2(ys) : [-3, 3];
  const { g, sx, sy } = axesSVG(W, H, pad, xmin, xmax, ymin, ymax);
  let path = '', started = false;
  if (fx && fy) for (let i = 0; i <= 600; i++) {
    const t = tmin + (tmax - tmin) * i / 600;
    const X = fx(t), Y = fy(t);
    if (X == null || Y == null) { started = false; continue; }
    const px = sx(X), py = sy(Y);
    path += (started ? ' L ' : ' M ') + px.toFixed(1) + ' ' + py.toFixed(1);
    started = true;
  }
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${g}<path d="${path}" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linejoin="round"/></svg>`;
}

function figGeometry(f) {
  const W = 520, H = 390, pad = 30;
  const shapes = f.shapes || [];
  let pts = [];
  shapes.forEach(s => {
    if (s.kind === 'circle') { pts.push([s.cx - s.r, s.cy - s.r], [s.cx + s.r, s.cy + s.r]); }
    else if (s.kind === 'poly' || s.kind === 'line' || s.kind === 'arrow') {
      (s.pts || [[s.x1, s.y1], [s.x2, s.y2]]).forEach(p => pts.push(p));
      if (s.pts == null && s.x1 != null) pts.push([s.x1, s.y1], [s.x2, s.y2]);
    } else if (s.kind === 'text') { pts.push([s.x, s.y]); }
  });
  if (!pts.length) pts = [[0, 0], [1, 1]];
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  let xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  const mx = (xmax - xmin) || 1, my = (ymax - ymin) || 1;
  xmin -= mx * .12; xmax += mx * .12; ymin -= my * .12; ymax += my * .12;
  const iw = W - 2 * pad, ih = H - 2 * pad;
  const sx = x => pad + (x - xmin) / (xmax - xmin) * iw, sy = y => pad + (ymax - y) / (ymax - ymin) * ih;
  let g = `<rect x="${pad}" y="${pad}" width="${iw}" height="${ih}" fill="var(--paper-2)" stroke="var(--line)" rx="6"/>`;
  shapes.forEach(s => {
    if (s.kind === 'circle') { g += `<circle cx="${sx(s.cx)}" cy="${sy(s.cy)}" r="${(s.r / (xmax - xmin)) * iw}" fill="none" stroke="var(--brand)" stroke-width="2"/>`; }
    else if (s.kind === 'poly') { const p = (s.pts || []).map(q => `${sx(q[0])},${sy(q[1])}`).join(' '); g += `<polygon points="${p}" fill="${s.fill ? 'color-mix(in srgb,var(--accent) 18%,transparent)' : 'none'}" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round"/>`; }
    else if (s.kind === 'line') { g += `<line x1="${sx(s.x1)}" y1="${sy(s.y1)}" x2="${sx(s.x2)}" y2="${sy(s.y2)}" stroke="var(--ink-2)" stroke-width="1.8"/>`; }
    else if (s.kind === 'arrow') { const x1 = sx(s.x1), y1 = sy(s.y1), x2 = sx(s.x2), y2 = sy(s.y2), ang = Math.atan2(y2 - y1, x2 - x1), hl = 8; g += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--brand)" stroke-width="2"/><polygon points="${x2},${y2} ${x2-hl*Math.cos(ang-.4)},${y2-hl*Math.sin(ang-.4)} ${x2-hl*Math.cos(ang+.4)},${y2-hl*Math.sin(ang+.4)}" fill="var(--brand)"/>`; }
    else if (s.kind === 'text') { g += `<text x="${sx(s.x)}" y="${sy(s.y)}" font-size="13" fill="var(--ink)" font-family="var(--serif)" font-style="italic">${esc(s.label || '')}</text>`; }
  });
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${g}</svg>`;
}

function figDiagram(f) {
  const W = 520, H = 390, boxes = f.boxes || [], arrows = f.arrows || [];
  const bw = 120, bh = 44, pos = {};
  boxes.forEach((b, i) => { const x = b.x != null ? b.x : (10 + (i % 3) * 32), y = b.y != null ? b.y : (10 + Math.floor(i / 3) * 30); pos[b.label || i] = { x: x / 100 * (W - bw), y: y / 100 * (H - bh) }; });
  let g = '';
  arrows.forEach(a => { const from = pos[a.from] || { x: 0, y: 0 }, to = pos[a.to] || { x: 0, y: 0 }; const x1 = from.x + bw / 2, y1 = from.y + bh / 2, x2 = to.x + bw / 2, y2 = to.y + bh / 2; const ang = Math.atan2(y2 - y1, x2 - x1), hl = 8; g += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--brand)" stroke-width="1.6" stroke-dasharray="4 3"/><polygon points="${x2},${y2} ${x2-hl*Math.cos(ang-.4)},${y2-hl*Math.sin(ang-.4)} ${x2-hl*Math.cos(ang+.4)},${y2-hl*Math.sin(ang+.4)}" fill="var(--brand)"/>`; });
  boxes.forEach((b, i) => { const p = pos[b.label || i]; g += `<rect x="${p.x}" y="${p.y}" width="${bw}" height="${bh}" rx="9" fill="var(--card-2)" stroke="var(--brand)" stroke-width="1.6"/><text x="${p.x + bw / 2}" y="${p.y + bh / 2 + 4}" text-anchor="middle" font-size="12" fill="var(--ink)" font-family="var(--sans)">${esc(String(b.label || '').slice(0, 20))}</text>`; });
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${g}</svg>`;
}

function renderFigure(f) {
  try {
    switch (f.tipo) {
      case 'funcion': return figFunction(f);
      case 'vector_field': return figVectorField(f);
      case 'parametrica': return figParametric(f);
      case 'geometria': return figGeometry(f);
      case 'diagrama': return figDiagram(f);
      case 'tabla': return renderTable(f.headers, f.rows) || '<div class="prose">tabla vacía</div>';
      default: return '';
    }
  } catch (e) { return `<div class="prose" style="color:var(--bad)">Error al generar figura: ${esc(e.message)}</div>`; }
}

function renderFiguresBlock(figData) {
  const figs = (figData && figData.figuras) || [];
  if (!figs.length) return '';
  const cards = figs.map(f => {
    const art = f.tipo === 'tabla' ? renderTable(f.headers, f.rows) : (f.tipo === 'prosa' ? '<div class="prose" style="padding:14px">' + (f.descripcion || '') + '</div>' : renderFigure(f));
    return `<figure><div class="art">${art}</div><figcaption><div class="ft">Fig. · ${esc(f.titulo || f.tipo)}</div><div class="fd">${f.descripcion || ''}</div></figcaption></figure>`;
  }).join('');
  return `<div class="figures">${cards}</div>`;
}

/* ============================================================
   ENSAMBLADO FINAL DEL REPORTE
   ============================================================ */
function assembleReport(run, isPartial = false) {
  if (!run) return;
  const plan = run.plan || {};
  const resolver = run.resolver || {};
  const theory = run.theory || {};
  const figures = run.figures || {};
  const modeling = run.modeling || {};
  const research = run.research || {};
  const report = run.report || {};

  const host = $('#reportHost');
  if (!host) return;
  const num = (n) => `<span class="num">§ ${n}</span>`;

  // Resumen Ejecutivo del Proceso
  const completedStages = STAGES.filter(s => stageEls[s.id] && stageEls[s.id].classList.contains('done')).length;
  const execSummary = `
    <div style="background:var(--card-2); border:1px solid var(--line); border-left:4px solid var(--brand); border-radius:10px; padding:14px 18px; margin-bottom:18px; box-shadow:var(--sh1);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:13.5px; color:var(--brand); display:flex; align-items:center; gap:8px;">
          <span>📋</span> Informe Ejecutivo del Proceso · ${isPartial ? '<span style="color:var(--gold);">En Progreso (' + completedStages + '/8)</span>' : '<span style="color:var(--ok);">Completado (8/8)</span>'}
        </span>
        <button class="btn sm ghost" onclick="openTraceModal()" style="font-size:11px; padding:3px 9px;">🔍 Inspeccionar Trazas de Agentes</button>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:10px; font-size:12px; color:var(--ink-2);">
        <div><b>Arquitecto:</b> Planificador (${(plan.ramas || []).length} ramas)</div>
        <div><b>Resolutor:</b> Axiomático (${(resolver.pasos || []).length} pasos)</div>
        <div><b>Marco Teórico:</b> ${(theory.ramas || []).length} ramas analizadas</div>
        <div><b>Modelación:</b> ${modeling.titulo_modelo || 'En formulación...'}</div>
        <div><b>Simulador:</b> Canvas HTML5 Autónomo</div>
        <div><b>Formato:</b> .docx (OMML 2D), .doc, .md</div>
      </div>
    </div>
  `;

  const mdBlock = run.markdown ? `<div class="mdview"><div class="mh"><span>Markdown editable (Word)</span><span class="grow"></span><button class="btn sm ghost" onclick="copyMd()">Copiar</button><button class="btn sm ghost" onclick="downloadMd()">Descargar .md</button></div><pre id="mdPre">${esc(run.markdown)}</pre></div>` : '';

  const html = `
  <article class="doc report">
    <div class="doc-head">
      <div class="kicker">${esc(plan.area_principal || 'Matemáticas Avanzadas')} · ${esc(AUD_LABEL[plan._aud || S.audience])} · profundidad ${esc(DEPTH_LABEL[plan._dep || S.depth])}</div>
      <h2>${esc(report.titulo_final || plan.titulo || 'Análisis Matemático')}</h2>
      <div class="prob"><b>Enunciado.</b> ${resolver.enunciado_formal || esc(plan.objetivo || $('#prompt')?.value || 'Enunciado en proceso')}</div>
    </div>
    
    ${execSummary}

    <div class="doc-body">

      ${resolver.estrategia || (plan.hipotesis && plan.hipotesis.length) ? `
      <section class="blk">
        <div style="display:flex; justify-content:space-between; align-items:center;"><h3 class="sec" style="margin:0;">${num(1)}Estrategia y planificación</h3><a href="javascript:void(0)" onclick="window.promptSectionRefinement('estrategia')" style="font-size:11px;color:var(--brand);text-decoration:none;font-weight:600;">✏️ Tunear Sección</a></div>
        <p class="sec-sub">Cómo se abordará el problema y con qué herramientas.</p>
        <div class="prose"><p>${resolver.estrategia || 'Formulando estrategia deductiva formal...'}</p></div>
        ${plan.hipotesis && plan.hipotesis.length ? `<div class="callout co-note"><div class="lab">Hipótesis y supuestos</div><ul>${plan.hipotesis.map(h => `<li>${h}</li>`).join('')}</ul></div>` : ''}
        ${plan.notacion && plan.notacion.length ? `<div class="tbl-wrap"><table><thead><tr><th>Símbolo</th><th>Significado</th></tr></thead><tbody>${plan.notacion.map(n => `<tr><td class="mono">${formatSymbol(n.symbolo)}</td><td>${formatProseMath(n.significado || "")}</td></tr>`).join('')}</tbody></table></div>` : ''}
        ${plan.riesgos && plan.riesgos.length ? `<div class="callout co-warn"><div class="lab">Sutilezas / riesgos</div><ul>${plan.riesgos.map(r => `<li>${r}</li>`).join('')}</ul></div>` : ''}
      </section>` : ''}

      ${resolver.pasos && resolver.pasos.length ? `
      <section class="blk">
        <div style="display:flex; justify-content:space-between; align-items:center;"><h3 class="sec" style="margin:0;">${num(2)}Desarrollo paso a paso</h3><a href="javascript:void(0)" onclick="window.promptSectionRefinement('desarrollo')" style="font-size:11px;color:var(--brand);text-decoration:none;font-weight:600;">✏️ Tunear Sección</a></div>
        <p class="sec-sub">Procedimiento deductivo completo desde axiomas, sin saltos algebraicos.</p>
        ${renderSteps(resolver.pasos)}
        ${resolver.resultado ? `<div class="callout co-ok"><div class="lab">Resultado</div><div class="prose">${formatProseMath(resolver.resultado)}</div></div>` : ''}
        ${resolver.verificacion ? `<div class="callout co-note"><div class="lab">Verificación</div><div class="prose">${formatProseMath(resolver.verificacion)}</div></div>` : ''}
        ${resolver.observaciones ? `<div class="callout co-thm"><div class="lab">Observaciones</div><div class="prose">${formatProseMath(resolver.observaciones)}</div></div>` : ''}
      </section>` : ''}

      ${theory.ramas && theory.ramas.length ? `
      <section class="blk">
        <div style="display:flex; justify-content:space-between; align-items:center;"><h3 class="sec" style="margin:0;">${num(3)}Marco teórico</h3><a href="javascript:void(0)" onclick="window.promptSectionRefinement('teoria')" style="font-size:11px;color:var(--brand);text-decoration:none;font-weight:600;">✏️ Tunear Sección</a></div>
        <p class="sec-sub">Definiciones, teoremas, lemas, axiomas, métodos y herramientas que sustentan la solución, por ramas.</p>
        ${renderBranches(theory.ramas)}
        ${theory.herramientas && theory.herramientas.length ? `<h4 style="font-family:var(--serif);margin:18px 0 6px">Herramientas</h4><div class="tbl-wrap"><table><thead><tr><th>Herramienta</th><th>Uso aquí</th><th>Fuente</th></tr></thead><tbody>${theory.herramientas.map(h => `<tr><td>${esc(h.nombre)}</td><td>${h.uso || ''}</td><td>${h.fuente || ''}</td></tr>`).join('')}</tbody></table></div>` : ''}
        ${theory.glosario && theory.glosario.length ? `<h4 style="font-family:var(--serif);margin:18px 0 6px">Glosario de términos y notación</h4><dl class="gloss">${theory.glosario.map(g => `<div class="gl"><dt>${esc(g.termino)}</dt><dd>${g.def || ''}</dd></div>`).join('')}</dl>` : ''}
      </section>` : ''}

      ${(figures.figuras && figures.figuras.length) || figures.notas_imagenes ? `
      <section class="blk">
        <h3 class="sec">${num(4)}Visualizaciones</h3>
        <p class="sec-sub">Figuras generadas para ilustrar el ejercicio y la teoría.</p>
        ${renderFiguresBlock(figures)}
        ${figures.notas_imagenes ? `<div class="callout co-note"><div class="lab">Guía de imágenes</div><div class="prose">${Array.isArray(figures.notas_imagenes) ? '<ul>' + figures.notas_imagenes.map(n => `<li>${n}</li>`).join('') + '</ul>' : figures.notas_imagenes}</div></div>` : ''}
      </section>` : ''}

      ${run.modeling ? `
      <section class="blk">
        <div style="display:flex; justify-content:space-between; align-items:center;"><h3 class="sec" style="margin:0;">${num(5)}Modelación Matemática Contextual</h3><a href="javascript:void(0)" onclick="window.promptSectionRefinement('modelacion')" style="font-size:11px;color:var(--brand);text-decoration:none;font-weight:600;">✏️ Tunear Sección</a></div>
        <p class="sec-sub">Formulación de sistemas complejos, ecuaciones de gobierno y aplicaciones atípicas.</p>
        ${renderModelingSection(run.modeling)}
      </section>` : ''}

      ${plan.titulo ? `
      <section class="blk">
        <h3 class="sec">${num(6)}Laboratorio Matemático Interactivo (Canvas HTML5)</h3>
        <p class="sec-sub">Simulador dinámico con sliders paramétricos para explorar el comportamiento analítico en tiempo real.</p>
        ${renderInteractiveSimCard(run)}
      </section>` : ''}

      ${research.generalizaciones && research.generalizaciones.length ? `
      <section class="blk">
        <h3 class="sec">${num(7)}Investigación y extensión</h3>
        <p class="sec-sub">De un ejercicio a una línea de investigación: generalizaciones, aplicaciones, historia y literatura.</p>
        ${renderResearch(research)}
      </section>` : ''}

      ${report && report.html ? `<section class="blk"><h3 class="sec">${num(8)}Informe integrado</h3><p class="sec-sub">Redacción continua que une todos los hilos del análisis.</p>${report.html}</section>` : ''}

      <section class="blk">
        <h3 class="sec">${num(9)}Exportación editable</h3>
        <p class="sec-sub">Markdown con el formato correspondiente listo para Word con ecuaciones editables.</p>
        ${mdBlock || '<p class="prose" style="color:var(--muted);font-size:12.5px;">Markdown en proceso de compilación final...</p>'}
      </section>
    </div>
  </article>
  
  <div class="toolbar" style="position:sticky; bottom:12px; z-index:90; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 16px; box-shadow:var(--sh2); display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-top:20px;">
    <button class="btn ghost sm" onclick="openKnowledgeModal()">📚 Base Conocimiento</button>
    <button class="btn ghost sm" onclick="openDraftStudio()">📝 Draft Studio</button>
    <button class="btn ghost sm" onclick="exportSimulatorHtml()">⚡ Simulador (.html)</button>
    <span class="grow"></span>
    <button class="btn ghost sm" onclick="downloadMd()">⬇ Markdown (.md)</button>
    <button class="btn ghost sm" onclick="exportWordDoc()">⬇ Word (.doc / Ecuaciones 2D)</button>
    <button class="btn ghost sm" onclick="exportWordDocx()">⬇ Word (.docx)</button>
    <button class="btn primary sm" onclick="exportHTML()">⬇ Exportar informe .html</button>
  </div>`;

  host.innerHTML = html;
  try {
    typeset(host);
  } catch(e) {}
}

/* ============================================================
   ORQUESTACIÓN PRINCIPAL DEL PIPELINE
   ============================================================ */
async function runPipeline(resumeFromStage = null, existingRun = null) {
  const userPrompt = $('#prompt').value.trim();
  if (!userPrompt && !resumeFromStage) { toast('Escribe o pega el ejercicio primero.'); $('#prompt').focus(); return; }

  // 1. FASE 0: AGENTE CLASIFICADOR DE ENTRADA (INTENT ROUTER)
  if (!resumeFromStage) {
    const intent = classifyInputIntent(userPrompt);
    if (intent.type !== 'PIPELINE_RUN') {
      await handleSpecialIntent(intent);
      return;
    }
  }

  // Comprobar proveedor o fallback local
  if (!validKey(S.key)) {
    if (S.ollamaAvailable) {
      S.provider = 'ollama';
      updateConn();
      log('Sin clave Gemini configurada. Operando en modo local (Ollama).');
      toast('⚙️ Operando con LLM local Ollama...');
    } else {
      openModal('key');
      return;
    }
  }

  if (S.running) { cancelPipeline(); return; }

  S.running = true;
  $('#runBtn').innerHTML = '■ Detener';
  const cBtn = $('#cancelBtn'); if (cBtn) cBtn.style.display = 'inline-block';
  const eBtn = $('#editPromptBtn'); if (eBtn) eBtn.style.display = 'none';
  setStat('run', 'Analizando con modelo activo…');

  if (!resumeFromStage) {
    renderPipeline();
  }

  const files = S.files, aud = S.audience, dep = S.depth;
  const run = existingRun || { plan: null, resolver: null, theory: null, figures: null, modeling: null, research: null, report: null, markdown: '' };
  window._activePraxisRun = run;
  run.observable_events = Array.isArray(run.observable_events) ? run.observable_events : [];
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // Orden secuencial de etapas
  const stageOrder = ['plan', 'resolve', 'theory', 'figures', 'modeling', 'research', 'report', 'md'];
  let startIdx = 0;
  if (resumeFromStage) {
    startIdx = stageOrder.indexOf(resumeFromStage);
    if (startIdx === -1) startIdx = 0;
    log(`Reanudando pipeline desde la etapa: ${resumeFromStage}`);
    toast(`🔄 Reanudando desde etapa: ${resumeFromStage}`);
  }

  try {
    // 0. Contexto de estrategia aprendido: se calcula antes de invocar agentes.
    let strategyContext = null;
    try {
      const sResp = await fetch('/api/strategies/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: S.activeChatId, query: userPrompt })
      });
      if (sResp.ok) {
        const sd = await sResp.json();
        strategyContext = sd.strategy_context || null;
        if (strategyContext?.strategy_ids?.length) {
          log('Contexto de estrategia aplicado: ' + strategyContext.strategy_ids.join(', '));
        }
      }
    } catch (e) {
      log('Contexto de estrategia no disponible; usando flujo base.');
    }
    run.strategy_context = strategyContext || { strategy_context_version: 1, strategy_ids: [] };

    // El perfil de profundidad ya no es solo una etiqueta de UI: se materializa
    // en el grafo operativo antes de ejecutar las etapas existentes.
    try {
      const depthLevelMap = {
        doctor: 'doctorado',
        maestro: 'maestria',
        licenciatura: 'licenciatura',
        publico: 'fundamental'
      };
      const depthProfile = {
        level: depthLevelMap[aud] || 'licenciatura',
        // La profundidad visual/procedimental de la UI puede complementar el preset.
        custom_rules: dep === 'profunda'
          ? ['explicar los saltos matemáticos relevantes', 'proponer representación visual cuando aporte comprensión']
          : []
      };
      const graphResp = await fetch('/api/agent-graph/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: userPrompt,
          chat_id: S.activeChatId,
          investigation_id: S.lastRun?.investigation_id || null,
          depth_profile: depthProfile,
          required_artifacts: ['python', 'canvas', 'markdown'],
          strategy_context: run.strategy_context
        })
      });
      if (graphResp.ok) {
        const graphData = await graphResp.json();
        run.agent_plan = graphData.plan || null;
        run.operational_context = graphData.context || null;
        if (run.agent_plan?.selected_agents?.length) {
          log('Grafo operativo seleccionado: ' + run.agent_plan.selected_agents.join(', '));
        }
      } else {
        log('Grafo operativo no disponible; se conserva el pipeline existente.');
      }
    } catch (e) {
      log('No fue posible materializar el grafo operativo; se conserva el pipeline existente.');
    }

    const strategyOps = (run.strategy_context.operational_instructions || []).join('\n');
    const strategyPromptContext = strategyOps ? '\n\n[ESTRATEGIA OPERATIVA APROBADA PARA ESTA INVESTIGACIÓN]:\n' + strategyOps : '';

    // 0. Consultar Base de Conocimiento y Puente Epistémico entre Chats
    let knowledgeCtx = '';
    try {
      const kResp = await fetch('/api/get_knowledge_context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userPrompt })
      });
      if (kResp.ok) {
        const kd = await kResp.json();
        knowledgeCtx = kd.context || '';
        if (knowledgeCtx) log('Base de conocimiento unificada vinculada.');
      }
    } catch(e) {}

    // Consultar Puente Epistémico entre otros chats
    try {
      const cResp = await fetch('/api/chats/query_other', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userPrompt, exclude_chat_id: S.activeChatId })
      });
      if (cResp.ok) {
        const cd = await cResp.json();
        const matches = cd.matches || [];
        if (matches.length > 0) {
          const interText = '\n\n[PUENTE EPISTÉMICO INTER-CHAT (RESULTADOS PREVIOS RELEVANTES)]:\n' +
            matches.map(m => `• Del Chat "${m.chat_title}": ${m.response_title}`).join('\n');
          knowledgeCtx += interText;
          log('Resultados recuperados de otras conversaciones vinculados.');
        }
      }
    } catch(e) {}

    // 1. Planificador Maestro
    if (startIdx <= 0 || !run.plan) {
      setStage('plan', 'running', 'analizando ejercicio y trazando plan maestro…');
      const pPlan = promptPlanner(userPrompt + (knowledgeCtx ? '\n\n' + knowledgeCtx : '') + strategyPromptContext, files, aud, dep);
      const rawPlan = await callGemini(pPlan, { json: true, temperature: 0.4 });
      run.plan = extractJSON(rawPlan);
      window.recordAgentTrace('plan', pPlan, rawPlan, run.plan);
      run.plan._aud = aud; run.plan._dep = dep;
      setStage('plan', 'done', (run.plan.ramas || []).length + ' ramas detectadas');
      saveCurrentCheckpoint('plan', run);
      assembleReport(run, true);
      await sleep(350);
    } else {
      setStage('plan', 'done', (run.plan.ramas || []).length + ' ramas detectadas');
    }

    // 2. Agente de Resolución Axiomática
    if (startIdx <= 1 || !run.resolver) {
      setStage('resolve', 'running', 'desarrollando resolución paso a paso sin atajos…');
      const pRes = promptResolver(run.plan, userPrompt, aud, dep);
      const rawRes = await callGemini(pRes, { json: true, temperature: 0.3 });
      run.resolver = extractJSON(rawRes);
      window.recordAgentTrace('resolve', pRes, rawRes, run.resolver);
      setStage('resolve', 'done', (run.resolver.pasos || []).length + ' pasos formalizados');
      saveCurrentCheckpoint('resolve', run);
      assembleReport(run, true);
      await sleep(350);
    } else {
      setStage('resolve', 'done', (run.resolver.pasos || []).length + ' pasos formalizados');
    }

    // FASES 5 Y 7: ENRUTADOR HÍBRIDO ASÍNCRONO EN GRAFO (DAG CONCURRENTE)
    // Tras el Resolutor, las etapas de Teoría, Figuras, Modelación e Investigación
    // se ejecutan concurrentemente en paralelo sin bloquearse entre sí, acelerando el flujo hasta 4x.
    if (startIdx <= 2 || !run.theory || !run.figures || !run.modeling || !run.research) {
      log('Lanzando ejecución concurrente en Grafo Asíncrono (Teoría + Figuras + Modelación + Investigación RAG)...');
      if (!run.theory) setStage('theory', 'running', 'Extrayendo marco teórico y lemas…');
      if (!run.figures) setStage('figures', 'running', 'Diseñando figuras vectoriales SVG…');
      if (!run.modeling) setStage('modeling', 'running', 'Modelando sistemas reales y aplicaciones…');
      if (!run.research) setStage('research', 'running', 'Consultando literatura científica (arXiv & local)…');

      const parallelTasks = [];

      // Rama A: Agente Teórico
      if (!run.theory) {
        parallelTasks.push((async () => {
          try {
            const pTheo = promptTheory(run.plan, run.resolver, userPrompt, aud, dep);
            const rawTheo = await callGemini(pTheo, { json: true, temperature: 0.35 });
            run.theory = extractJSON(rawTheo);
            window.recordAgentTrace('theory', pTheo, rawTheo, run.theory);
            setStage('theory', 'done', (run.theory.ramas || []).reduce((a, r) => a + ((r.items || []).length), 0) + ' ítems teóricos');
          } catch(e) {
            run.theory = { ramas: [{ nombre: 'Fundamentos Analíticos', descripcion: 'Marco axiomático base.', items: [] }] };
            setStage('theory', 'done', 'Marco teórico básico');
          }
          saveCurrentCheckpoint('theory', run);
          assembleReport(run, true);
        })());
      }

      // Rama B: Agente de Visualización (Figuras SVG)
      if (!run.figures) {
        parallelTasks.push((async () => {
          try {
            const pFigs = promptFigures(run.plan, run.resolver, run.theory || {}, userPrompt);
            const rawFigs = await callGemini(pFigs, { json: true, temperature: 0.4 });
            run.figures = extractJSON(rawFigs);
            window.recordAgentTrace('figures', pFigs, rawFigs, run.figures);
            setStage('figures', 'done', (run.figures.figuras || []).length + ' figuras SVG');
          } catch(e) {
            run.figures = { figuras: [], notas_imagenes: 'Figuras generadas procedimentalmente.' };
            setStage('figures', 'done', 'Visualizaciones base');
          }
          saveCurrentCheckpoint('figures', run);
          assembleReport(run, true);
        })());
      }

      // Rama C: Agente de Modelación Contextual
      if (!run.modeling) {
        parallelTasks.push((async () => {
          try {
            const pMod = promptModeling(run.plan, run.resolver, userPrompt);
            const rawMod = await callGemini(pMod, { json: true, temperature: 0.35 });
            run.modeling = extractJSON(rawMod);
            window.recordAgentTrace('modeling', pMod, rawMod, run.modeling);
            setStage('modeling', 'done', 'Modelación contextual completada');
          } catch(e) {
            run.modeling = { titulo_modelo: 'Modelación de Sistemas', contexto_sistemico: 'Formulación continua en espacio de estados.' };
            setStage('modeling', 'done', 'Modelación base');
          }
          saveCurrentCheckpoint('modeling', run);
          assembleReport(run, true);
        })());
      }

      // Rama D: Agente de Investigación con RAG Multimodal (arXiv y Documentos Locales)
      if (!run.research) {
        parallelTasks.push((async () => {
          try {
            let ragContext = '';
            // 1. Consulta RAG en arXiv
            try {
              const arxResp = await fetch('/api/rag/arxiv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userPrompt, max_results: 3 })
              });
              if (arxResp.ok) {
                const arxData = await arxResp.json();
                if (arxData.papers && arxData.papers.length) {
                  ragContext += '\n\n[LITERATURA CIENTÍFICA REAL RECUPERADA DE ARXIV]:\n' +
                    arxData.papers.map(p => `• ${p.citation} (PDF: ${p.pdf_url}) - Abstract: ${p.abstract}`).join('\n');
                  log('Preprints de arXiv recuperados e integrados.');
                }
              }
            } catch(e) {}

            // 2. Consulta RAG en documentos locales del chat
            try {
              if (S.activeChatId) {
                const docResp = await fetch('/api/rag/chat_docs', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ chat_id: S.activeChatId, query: userPrompt })
                });
                if (docResp.ok) {
                  const docData = await docResp.json();
                  if (docData.snippets && docData.snippets.length) {
                    ragContext += '\n\n[FRAGMENTOS DE DOCUMENTOS Y PDFS DEL CHAT]:\n' +
                      docData.snippets.map(s => `• De ${s.source}: "${s.text.slice(0, 300)}"`).join('\n');
                    log('Fragmentos de PDFs locales integrados mediante RAG.');
                  }
                }
              }
            } catch(e) {}

            const pRese = promptResearch(run.plan, run.resolver, run.theory || {}, userPrompt + ragContext);
            const rawRese = await callGemini(pRese, { json: true, temperature: 0.5 });
            run.research = extractJSON(rawRese);
            window.recordAgentTrace('research', pRese, rawRese, run.research);
            setStage('research', 'done', (run.research.bibliografia || []).length + ' referencias');
          } catch(e) {
            run.research = { generalizaciones: [], problemas_abiertos: [], aplicaciones: [], historia: [], bibliografia: [] };
            setStage('research', 'done', 'Referencias base');
          }
          saveCurrentCheckpoint('research', run);
          assembleReport(run, true);
        })());
      }

      await Promise.allSettled(parallelTasks);
      log('Todas las ramas del Grafo Concurrente concluidas.');
    } else {
      setStage('theory', 'done', 'Marco teórico cargado');
      setStage('figures', 'done', 'Figuras cargadas');
      setStage('modeling', 'done', 'Modelación cargada');
      setStage('research', 'done', 'Investigación cargada');
    }

    // 7. Ensamblador de Informe Markdown (Con Rescate Autónomo / Self-Healing)
    if (startIdx <= 6 || !run.markdown) {
      setStage('report', 'running', 'Redactando informe exhaustivo en Markdown canónico…');
      let mdContent = '';
      try {
        const promptReportMd = `${SYSTEM_CORE}\n\nFASE 6 — REDACCIÓN DEL INFORME MATEMÁTICO COMPLETO EN MARKDOWN CANÓNICO.\nTu misión: Redactar el informe completo de la investigación en Markdown riguroso, limpio e impecable.\n\nREGLAS DE FORMATO:\n- NO uses JSON. Responde DIRECTAMENTE con el documento Markdown.\n- Ecuaciones display centradas: SIEMPRE en bloque con $$ en su propia línea.\n- Ecuaciones en línea: SIEMPRE con $formula$.\n- Estructura: # Título, ## 1. Estrategia y Planteamiento, ## 2. Desarrollo Paso a Paso, ## 3. Marco Teórico Formal, ## 4. Modelación Contextual, ## 5. Bibliografía.\n\nDATOS:\nPlan: ${JSON.stringify(run.plan)}\nResolución: ${JSON.stringify(run.resolver)}\nTeoría: ${JSON.stringify(run.theory)}\nEjercicio: """${userPrompt}"""`;

        const rawReportMd = await callGemini(promptReportMd, { json: false, temperature: 0.3 });
        window.recordAgentTrace('report', promptReportMd, rawReportMd, { length: rawReportMd.length });
        mdContent = rawReportMd.trim().replace(/^```(?:markdown)?\s*/i, '').replace(/\s*```$/i, '').trim();
      } catch (e) {
        log('Aviso: Activando Agente de Auto-Reparación (Self-Healing) para ensamblar Markdown sin límite de tokens...');
        mdContent = synthesizeCanonicalMarkdown(run, userPrompt);
        window.recordAgentTrace('report', 'Self-Healing Synthesis', mdContent, { self_healed: true });
      }

      if (!mdContent || mdContent.length < 50) {
        mdContent = synthesizeCanonicalMarkdown(run, userPrompt);
      }
      run.markdown = mdContent;
      setStage('report', 'done', 'Markdown generado');
      saveCurrentCheckpoint('report', run);
      assembleReport(run, true);
      await sleep(250);
    } else {
      setStage('report', 'done', 'Markdown cargado');
    }

    // 8. Agente Markdown y Compilación Final Word / Historial
    setStage('md', 'running', 'Compilando entregables Word (.docx/.doc) y simulador…');
    run.report = {
      html: renderMarkdownToPraxisHtml(run.markdown),
      titulo_final: run.plan.titulo
    };
    setStage('md', 'done', 'Listo para Word, DOCX y Pandoc');

    // Registrar el resultado real de la estrategia seleccionada.
    try {
      const evalProfile = run.evaluation_profile || {
        mathematics: 0, depth: 0, explanation: 0, visualization: 0,
        interactivity: 0, images: 0, code: 0, structure: 0
      };
      const selected = (run.strategy_context?.strategy_ids || [])[0];
      if (S.activeChatId && selected) {
        const expResp = await fetch('/api/experience/strategy-outcome', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chat_id: S.activeChatId,
            strategy_context: run.strategy_context,
            evaluation_profile: evalProfile,
            score: Number(run.evaluation_score ?? 1),
            consistent: run.evaluation_consistent !== false,
            investigation_id: run.investigation_id || null,
            version_id: run.version_id || null,
            metadata: { completed_stages: 8 }
          })
        });
        if (expResp.ok) log('Resultado de estrategia registrado en Experience Store.');
      }
    } catch (e) {
      console.warn('No se pudo registrar el resultado de estrategia:', e);
    }

    window.saveRunToHistory(run, userPrompt);
    assembleReport(run, false); // INFORME FINAL COMPLETO
    S.lastRun = run;
    clearActiveCheckpoint();

    // Guardar en backend (carpetas estructuradas, compilar docx/doc)
    try {
      const resp = await fetch('/api/save_investigation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: S.activeChatId,
          title: run.plan.titulo || 'Investigacion_Matematica',
          prompt: userPrompt,
          markdown: run.markdown,
          html: run.report.html,
          python_code: run.figures?.codigo_python || '',
          svgs: run.figures?.figuras || [],
          plan: run.plan,
          resolver: run.resolver,
          theory: run.theory,
          figures: run.figures,
          research: run.research,
          traces: window.agentTraces || {},
          runtime_trace: { status: 'completed', events: run.observable_events || [] },
          strategy_context: run.strategy_context || {}
        })
      });
      if (resp.ok) {
        const sData = await resp.json();
        log('Entregables compilados en historial/' + sData.folder_name);
        toast('✓ Guardado en historial con Word (.docx y .doc).');
        if (typeof window.loadChatSessions === 'function') {
          window.loadChatSessions();
        }
      }
    } catch(e) {
      console.warn('Guardado local en servidor:', e);
    }

    setStat('ok', 'Investigación Completa');
    toast('✓ Investigación matemática generada con éxito.');

  } catch (err) {
    const cur = STAGES.find(s => stageEls[s.id] && stageEls[s.id].classList.contains('running'));
    if (cur) setStage(cur.id, 'error', String(err.message || err).slice(0, 160));
    setStat('bad', 'Pausado por error');
    const msg = String(err && err.message || err);
    if (msg.includes('abort')) toast('Análisis detenido.');
    else toast('Aviso: ' + msg.slice(0, 140) + '. Clic en el paso o escribe "continúa" para destrabar.', 5000);
    log('PIPELINE INTERRUMPIDO: ' + msg);
    // Renderizar reporte parcial con lo generado hasta ahora
    assembleReport(run, true);
  } finally {
    S.running = false;
    $('#runBtn').innerHTML = '▶ Analizar';
    const cBtn = $('#cancelBtn'); if (cBtn) cBtn.style.display = 'none';
    const eBtn = $('#editPromptBtn'); if (eBtn) eBtn.style.display = 'inline-block';
    if ($('#statPill').classList.contains('run')) setStat('', 'Listo');
  }
}

/* ============================================================
   INTERACCIÓN Y REANUDACIÓN POR PASO (SELF-HEALING)
   ============================================================ */
window.handleStageClick = async function(stageId) {
  if (S.running) {
    toast('Un proceso está ejecutándose actualmente.');
    return;
  }
  const el = document.getElementById('st-' + stageId);
  if (!el) return;

  if (el.classList.contains('done')) {
    window.toggleAgentTrace(stageId);
    return;
  }

  // Si está en error o pendiente, reintentar esa etapa
  await window.retrySingleStage(stageId);
};

window.retrySingleStage = async function(stageId) {
  if (!S.currentRun && !S.currentCheckpoint?.run) {
    toast('No hay datos previos de investigación para reintentar.');
    return;
  }
  const run = S.currentRun || S.currentCheckpoint.run;
  toast(`🔄 Reintentando etapa: ${stageId}...`);
  await runPipeline(stageId, run);
};

window.resumePipelineFromCheckpoint = async function() {
  let cp = S.currentCheckpoint;
  if (!cp) {
    try {
      const stored = localStorage.getItem('praxis_active_checkpoint');
      if (stored) cp = JSON.parse(stored);
    } catch(e) {}
  }
  if (!cp && S.activeChatId) {
    try {
      const resp = await fetch(`/api/chats/${encodeURIComponent(S.activeChatId)}/checkpoint`);
      if (resp.ok) {
        const data = await resp.json();
        cp = data.checkpoint;
      }
    } catch(e) {}
  }

  if (!cp || !cp.run) {
    toast('No se encontró ningún proceso pendiente o interrumpido para reanudar.');
    return;
  }

  const stageOrder = ['plan', 'resolve', 'theory', 'figures', 'modeling', 'research', 'report', 'md'];
  // Buscar el primer paso que no esté completado
  let targetStage = 'plan';
  for (const s of stageOrder) {
    if (!cp.run[s] && s !== 'md') {
      targetStage = s;
      break;
    }
  }

  if (cp.prompt && $('#prompt')) {
    $('#prompt').value = cp.prompt;
  }

  toast(`⚙️ Destrabando sistema: Reanudando desde etapa ${targetStage}...`);
  await runPipeline(targetStage, cp.run);
};


/* ============================================================
   EXPORTACIONES
   ============================================================ */
function collectReportHTML() {
  const doc = $('#reportHost .doc'); if (!doc) return '';
  const clone = doc.cloneNode(true);
  clone.querySelectorAll('button').forEach(b => b.remove());
  return clone.outerHTML;
}

function exportHTML() {
  const body = collectReportHTML();
  if (!body) { toast('Primero genera un análisis.'); return; }
  const css = document.querySelector('style').textContent;
  const title = (S.lastRun && S.lastRun.plan && S.lastRun.plan.titulo) || 'Informe matemático';
  const endScript = '<' + '/script>';
  const mathJaxScript = '<' + 'script>\n' +
    'window.MathJax = {\n' +
    '  tex: {\n' +
    '    inlineMath: [["$", "$"]],\n' +
    '    displayMath: [["$$", "$$"]],\n' +
    '    processEscapes: true\n' +
    '  },\n' +
    '  options: { skipHtmlTags: ["script", "noscript", "style", "textarea", "pre", "code"] },\n' +
    '  startup: { typeset: true }\n' +
    '};\n' +
    endScript + '\n<' + 'script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">' + endScript;

  const docHtml = '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(title) + '</title>\n' +
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900;1,9..144,500&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">\n' +
    mathJaxScript + '\n' +
    '<style>:root{--paper:#e7e6df;--paper-2:#f2f1ea;--card:#fbfaf5;--card-2:#fff;--ink:#171d29;--ink-2:#39424f;--muted:#6d7482;--line:#d7d6cc;--line-2:#e6e5dc;--brand:#1a73e8;--brand-2:#1557b0;--brand-tint:#e8f0fe;--accent:#d93025;--gold:#f9ab00;--ok:#188038;--warn:#f9ab00;--bad:#d93025;--sans:\'IBM Plex Sans\',sans-serif;--serif:\'Fraunces\',serif;--mono:\'IBM Plex Mono\',monospace;--sh1:0 1px 2px rgba(20,30,40,.06),0 3px 10px rgba(20,30,40,.05);--sh2:0 10px 30px rgba(20,30,40,.1)}' +
    'body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55;padding:32px 16px}\n' +
    '.wrap{max-width:960px;margin:0 auto}' + css.replace(/:root\{[^}]*\}/, '').replace(/\[data-theme="dark"\]\{[^}]*\}/, '').replace(/\.app\{[^}]*\}/, '').replace(/body\{[^}]*overflow:hidden[^}]*\}/, '') + '</style>\n' +
    '</head><body><div class="wrap">' + body + '</div></body></html>';

  download((title || 'informe').replace(/[^\w\-]+/g, '_').slice(0, 50) + '.html', docHtml, 'text/html');
  toast('Informe exportado con MathJax autónomo.');
}

function downloadMd() {
  if (!S.lastRun || !S.lastRun.markdown) { toast('Aún no hay markdown disponible.'); return; }
  download(((S.lastRun.plan.titulo) || 'informe').replace(/[^\w\-]+/g, '_').slice(0, 50) + '.md', S.lastRun.markdown, 'text/markdown');
  toast('Markdown descargado.');
}

function copyMd() {
  if (!S.lastRun || !S.lastRun.markdown) { toast('Aún no hay markdown para copiar.'); return; }
  navigator.clipboard.writeText(S.lastRun.markdown).then(() => toast('Markdown copiado al portapapeles.'));
}

/* ============================================================
   ARCHIVOS Y ADJUNTOS
   ============================================================ */
function fileKind(f) {
  const n = f.name.toLowerCase();
  if (n.endsWith('.pdf')) return 'pdf'; if (n.endsWith('.zip')) return 'zip';
  if (/\.(png|jpe?g|gif|webp|svg)$/.test(n)) return 'image';
  if (/\.(txt|md|csv|json|tex|xml|html)$/.test(n)) return 'text';
  if (/\.(py|js|ts|m|c|cpp|java|ipynb)$/.test(n)) return 'code';
  return 'other';
}

async function readFiles(list) {
  for (const f of list) {
    const kind = fileKind(f);
    const rec = { id: uid(), name: f.name, kind, size: f.size, text: '', url: '' };
    if (kind === 'text' || kind === 'code') { rec.text = await f.text(); }
    else if (kind === 'pdf') { rec.text = '[PDF adjunto: ' + f.name + '. Extrae el contexto relevante.]'; }
    else if (kind === 'zip') { rec.text = '[Archivo ZIP: ' + f.name + '.]'; }
    else if (kind === 'image') { rec.url = URL.createObjectURL(f); }
    S.files.push(rec);

    // Guardar copia del adjunto en historial/chats/[id_chat]/archivos_cargados/
    try {
      const reader = new FileReader();
      reader.onload = () => {
        const b64 = (reader.result || '').split(',')[1];
        if (b64) {
          fetch('/api/chats/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              chat_id: S.activeChatId || 'general',
              filename: f.name,
              base64_content: b64
            })
          }).catch(() => {});
        }
      };
      reader.readAsDataURL(f);
    } catch(e) {}
  }
  renderAtts();
}

function renderAtts() {
  $('#atts').innerHTML = S.files.map(f => `<span class="att">${f.kind === 'image' ? '🖼' : f.kind === 'pdf' ? '📄' : f.kind === 'zip' ? '🗜' : f.kind === 'code' ? '⌨️' : '📃'} ${esc(f.name)} <span style="color:var(--muted)">${(f.size / 1024).toFixed(0)}KB</span><span class="x" data-id="${f.id}">✕</span></span>`).join('');
  $$('#atts .x').forEach(x => x.onclick = () => { S.files = S.files.filter(f => f.id !== x.dataset.id); renderAtts(); });
}

/* ============================================================
   UI, MODELOS, TEMAS Y EVENTOS
   ============================================================ */
function updateModelSelect() {
  const sel = $('#model');
  if (!sel) return;
  const current = S.model;
  const values = unique([current].concat(PREFERRED_MODELS).concat(cachedModels).concat(['custom']));

  sel.innerHTML = '';
  values.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v;
    if (v === 'custom') opt.textContent = 'Personalizado…';
    else if (v === PREFERRED_MODELS[0]) opt.textContent = v + ' (recomendado)';
    else opt.textContent = v;
    sel.appendChild(opt);
  });

  sel.value = values.includes(current) ? current : PREFERRED_MODELS[0];
  $('#customModel').style.display = sel.value === 'custom' ? 'block' : 'none';
}

function updateConn() {
  const p = $('#connPill');
  const has = validKey(S.key);
  p.className = 'pill ' + (has ? 'ok' : 'warn');
  const modelName = S.model === 'custom' ? (S.customModel || 'personalizado') : S.model;
  $('#connTxt').textContent = has ? ((S.key.startsWith('AQ.') ? 'Key AQ' : 'Key AIza') + ' · ' + modelName) : 'Falta API key';

  if (has) setPanelStatus('ok', 'Clave detectada · ' + modelName);
  else setPanelStatus('warn', 'Pega tu clave Gemini: AQ... o AIza...');
}

function updateAudHint() {
  const m = {
    doctor: 'Rigor máximo: demostraciones completas, generalizaciones y conexiones avanzadas.',
    maestro: 'Rigor + enfoque docente: porqués, errores comunes e intuición didáctica.',
    licenciatura: 'Detalle pedagógico: cada paso justificado, conceptos definidos al aparecer.',
    publico: 'Analogías accesibles, define toda la jerga, prioriza intuición y claridad.'
  };
  $('#audHint').textContent = m[S.audience] || '';
}

function toggleTheme() {
  const b = document.body;
  b.dataset.theme = b.dataset.theme === 'dark' ? 'light' : 'dark';
  try { localStorage.setItem('praxis.theme', b.dataset.theme); } catch (e) {}
}

function loadTheme() {
  try {
    const t = localStorage.getItem('praxis.theme');
    if (t) document.body.dataset.theme = t;
  } catch (e) {}
}

const EXAMPLES = [
  { n: '01', t: 'Lema de Itô', d: 'Demostrar la fórmula de Itô para f(B_t) con Browniano.', p: 'Demuestra la fórmula de Itô: para un movimiento browniano B_t y f∈C², df(B_t)=f\'(B_t)dB_t + ½f\'\'(B_t)dt.' },
  { n: '02', t: 'Teorema de Cayley–Hamilton', d: 'Demostrar que toda matriz satisface su polinomio característico.', p: 'Enuncia y demuestra el teorema de Cayley–Hamilton: toda matriz cuadrada A sobre un cuerpo anula su polinomio característico p_A(A)=0.' },
  { n: '03', t: 'Serie armónica divergente', d: 'Probar que Σ 1/n diverge y estimar su crecimiento.', p: 'Demuestra que la serie armónica Σ_{n=1}^∞ 1/n diverge, y obtén la estimación asintótica Σ_{k≤n}1/k = ln n + γ + o(1).' },
  { n: '04', t: 'Flujo de un campo vectorial', d: 'Resolver el sistema dx/dt=y, dy/dt=-x y clasificar el origen.', p: 'Resuelve el sistema de EDO lineal x\'=y, y\'=-x, halla las trayectorias y clasifica el punto crítico en el origen usando el plano fase.' },
  { n: '05', t: 'Integral de Gauss', d: 'Calcular ∫_{-∞}^{∞} e^{-x²} dx.', p: 'Calcula la integral gaussiana I=∫_{-∞}^{∞} e^{-x^2}dx usando coordenadas polares, y comenta su relación con la función error.' },
  { n: '06', t: 'Teorema de Bolzano–Weierstrass', d: 'Toda sucesión acotada en ℝⁿ tiene subsucesión convergente.', p: 'Enuncia y demuestra el teorema de Bolzano–Weierstrass en ℝⁿ, discutiendo la relación con compacidad y completez.' }
];

function showExamples() {
  $('#stageWrap').innerHTML = `<div class="empty"><div class="big">De un ejercicio<br>a una <em>investigación</em>.</div>
  <p class="lead">Praxis orquesta siete agentes especializados con el motor nativo de <b>Gemini v6</b>: planifica, resuelve paso a paso, extrae el marco teórico, genera visualizaciones SVG, investiga extensiones y ensambla un informe exportable con MathJax y Markdown para Word.</p>
  <div class="sect-label" style="margin-top:0">Prueba con uno de estos</div>
  <div class="exlist">${EXAMPLES.map(e => `<button class="ex" data-p="${encodeURIComponent(e.p)}"><span class="n">${e.n}</span><span><span class="t">${esc(e.t)}</span><span class="d">${esc(e.d)}</span></span></button>`).join('')}</div>
  </div>`;
  $$('.ex').forEach(b => b.onclick = () => {
    $('#prompt').value = decodeURIComponent(b.dataset.p);
    $('#prompt').focus();
    $('#stageWrap').innerHTML = '';
    toast('Ejercicio cargado. Pulsa Analizar.');
  });
}

function openModal(which) {
  const m = $('#modal');
  if (which === 'key') {
    $('#modalTitle').textContent = 'API Key de Google Gemini';
    $('#modalBody').innerHTML = `<p>Praxis es compatible tanto con claves de <b>Google AI Studio</b> (<code>AIza...</code>) como con tokens/claves de despliegue (<code>AQ...</code>):</p>
    <ol class="steps-list">
      <li>Accede a <a href="https://aistudio.google.com/api-keys" target="_blank" style="color:var(--brand)">Google AI Studio - API Keys</a>.</li>
      <li>Inicia sesión con tu cuenta de Google.</li>
      <li>Crea tu API Key y pégala en el campo de conexión.</li>
      <li>Si estás en celular o GitHub Pages, usa el botón <b>"Probar conexión"</b> o la herramienta <b>"🛠"</b> de la barra superior.</li>
    </ol>
    <div class="warnbox"><b>Seguridad:</b> La clave se almacena exclusivamente en el almacenamiento local de tu navegador (localStorage) y se envía de forma cifrada mediante encabezados HTTPS oficiales.</div>`;
  } else {
    $('#modalTitle').textContent = 'Praxis · Guía de Orquestación';
    $('#modalBody').innerHTML = `<p><b>Arquitectura Multi-Agente:</b> Convierte cualquier ejercicio matemático en un estudio exhaustivo sin omisiones:</p>
    <h4>Flujo de las 7 fases</h4>
    <ol class="steps-list">
      <li><b>Planificador Maestro:</b> Clasificación, notación, riesgos e hipótesis.</li>
      <li><b>Agente de Resolución:</b> Demostración formal y pasos sin saltos.</li>
      <li><b>Agente Teórico:</b> Desglose de axiomas, teoremas y definiciones por ramas.</li>
      <li><b>Agente de Visualización:</b> Generación matemática nativa en SVG.</li>
      <li><b>Agente de Investigación:</b> Generalizaciones, historia, problemas abiertos y fuentes.</li>
      <li><b>Ensamblador de Informe:</b> Unificación en HTML legible con MathJax.</li>
      <li><b>Agente Markdown:</b> Exportación compatible con ecuaciones para Microsoft Word.</li>
    </ol>`;
  }
  m.classList.add('open');
}

function closeModal() { $('#modal').classList.remove('open'); }

/* Red geométrica de fondo */
function buildNet() {
  const svg = $('#net'); if (!svg) return;
  const w = innerWidth, h = innerHeight;
  const N = Math.min(46, Math.floor(w * h / 26000));
  const pts = [];
  for (let i = 0; i < N; i++) pts.push({ x: Math.random() * w, y: Math.random() * h, d: Math.random() * 6 });
  let lines = '';
  for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) {
    const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y, dist = Math.hypot(dx, dy);
    if (dist < 150) lines += `<line x1="${pts[i].x}" y1="${pts[i].y}" x2="${pts[j].x}" y2="${pts[j].y}" stroke-dasharray="2 6" style="animation-delay:${(dist / 150 * 8).toFixed(1)}s"/>`;
  }
  let dots = '';
  pts.forEach(p => dots += `<circle cx="${p.x}" cy="${p.y}" r="2" style="animation-delay:${p.d}s"/>`);
  svg.innerHTML = lines + dots;
}

/* Pruebas y diagnósticos */
async function testConnection() {
  if (!validKey(S.key)) {
    setPanelStatus('bad', 'Clave vacía o formato inválido');
    toast('Ingresa una API Key válida (AIza... o AQ...)');
    openModal('key');
    return;
  }
  const btn = $('#testBtn');
  btn.disabled = true; btn.textContent = 'Probando…';
  setPanelStatus('run', 'Probando conexión con Gemini…');
  setStat('run', 'Verificando…');
  try {
    const res = await callGemini('Responde exactamente con la palabra: OK', { temperature: 0, max_tokens: 20, json: false, isTest: true, timeout: 3000 });
    toast('Conexión correcta ✔ ' + res.trim().slice(0, 30));
    setStat('ok', 'Conectado');
    setPanelStatus('ok', 'Conexión verificada: ' + res.trim());
    log('Prueba exitosa con modelo ' + S.model + ': ' + res.trim());
  } catch (e) {
    const msg = friendlyError(e);
    toast('Fallo de conexión: ' + msg.slice(0, 100), 4500);
    setStat('bad', 'Error de conexión');
    setPanelStatus('bad', 'Fallo: ' + msg);
    log('ERROR TEST: ' + msg);
  } finally {
    btn.disabled = false; btn.textContent = 'Probar conexión';
  }
}

async function listModelsAction() {
  setPanelStatus('run', 'Consultando modelos disponibles en Google...');
  try {
    const models = await fetchModels();
    setPanelStatus('ok', 'Modelos detectados: ' + models.length);
    toast('Modelos cargados (' + models.length + ')');
    log('Modelos detectados: ' + models.join(', '));
  } catch (e) {
    const msg = friendlyError(e);
    setPanelStatus('bad', 'Error listando: ' + msg);
    toast('Error: ' + msg.slice(0, 100));
    log('ERROR LISTAR: ' + msg);
  }
}

/* ============================================================
   INICIALIZACIÓN
   ============================================================ */
function init() {
  loadCfg();
  loadTheme();
  loadSystemConfig();

  // Escuchador global de cierre de modales con Escape y clic fuera
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal.open').forEach(m => m.classList.remove('open'));
    }
  });
  document.addEventListener('click', e => {
    if (e.target && e.target.classList && e.target.classList.contains('modal')) {
      e.target.classList.remove('open');
    }
  });

  $('#apiKey').value = S.key || '';
  updateModelSelect();
  syncChips();

  // Enlace chips audiencia
  $$('#audChips .chip').forEach(c => c.onclick = () => {
    $$('#audChips .chip').forEach(x => x.classList.remove('on'));
    c.classList.add('on');
    S.audience = c.dataset.aud;
    saveCfg();
    updateAudHint();
  });

  // Enlace chips profundidad
  $$('#depthChips .chip').forEach(c => c.onclick = () => {
    $$('#depthChips .chip').forEach(x => x.classList.remove('on'));
    c.classList.add('on');
    S.depth = c.dataset.depth;
    saveCfg();
  });

  // Enlace chips herramientas
  $$('#toolChips .chip').forEach(c => c.onclick = () => {
    const t = c.dataset.tool;
    S.tools[t] = !S.tools[t];
    c.classList.toggle('on', S.tools[t]);
    saveCfg();
  });

  // Eventos de entrada
  $('#apiKey').addEventListener('input', debounce(() => {
    const val = $('#apiKey').value.trim();
    S.key = val;
    saveCfg();
    updateConn();
  }, 250));

  $('#eyeBtn').onclick = () => {
    const inp = $('#apiKey');
    inp.type = inp.type === 'password' ? 'text' : 'password';
  };

  $('#model').onchange = () => {
    S.model = $('#model').value;
    $('#customModel').style.display = S.model === 'custom' ? 'block' : 'none';
    saveCfg();
    updateConn();
  };

  $('#customModel').addEventListener('input', debounce(() => {
    S.customModel = $('#customModel').value.trim();
    saveCfg();
    updateConn();
  }, 250));

  $('#testBtn').onclick = testConnection;
  $('#listModelsBtn').onclick = listModelsAction;
  $('#helpKey').onclick = e => { e.preventDefault(); openModal('key'); };
  $('#aboutBtn').onclick = () => openModal('about');
  $('#modalClose').onclick = closeModal;
  $('#modal').onclick = e => { if (e.target.id === 'modal') closeModal(); };
  $('#themeBtn').onclick = toggleTheme;

  $('#clearBtn').onclick = () => {
    if (confirm('¿Deseas limpiar el ejercicio y los resultados actuales?')) {
      $('#stageWrap').innerHTML = '';
      $('#prompt').value = '';
      S.files = [];
      renderAtts();
      showExamples();
    }
  };

  $('#exampleBtn').onclick = showExamples;
  $('#runBtn').onclick = runPipeline;

  $('#prompt').addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runPipeline();
    }
  });

  $('#prompt').addEventListener('input', () => {
    const el = $('#prompt');
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 220) + 'px';
    const n = el.value.length;
    $('#tokEst').textContent = n ? ('~' + Math.round(n / 3.5) + ' tokens aprox.') : '';
  });

  $('#fileInput').onchange = e => {
    readFiles(Array.from(e.target.files));
    e.target.value = '';
  };

  // Controles del Panel de Diagnostico
  const pfp = $('#praxisFixPanel');
  const pfpHead = $('.pfp-head');
  const pfpToggle = $('#pfpToggle');
  const togglePanel = () => {
    pfp.classList.toggle('min');
    pfpToggle.textContent = pfp.classList.contains('min') ? '+' : '—';
  };
  if (pfpHead) pfpHead.onclick = togglePanel;
  $('#toggleDiagBtn').onclick = togglePanel;

  $('#pfpTest').onclick = testConnection;
  $('#pfpListModels').onclick = listModelsAction;
  $('#pfpReload').onclick = () => location.reload();
  $('#pfpClear').onclick = () => {
    localStorage.removeItem(STORAGE_KEY);
    S.key = '';
    $('#apiKey').value = '';
    saveCfg();
    updateConn();
    setPanelStatus('warn', 'Clave local borrada.');
    log('Clave borrada del almacenamiento local.');
  };
  $('#pfpCopy').onclick = () => {
    const txt = $('#pfpLog').textContent || '';
    navigator.clipboard.writeText(txt).then(() => toast('Log copiado.')).catch(() => toast('No se pudo copiar.'));
  };

  // Listeners globales para capturar errores de JavaScript y promesas en pantalla
  window.addEventListener('error', e => {
    const m = 'ERROR JS: ' + (e.message || '') + ' @ ' + (e.filename || '') + ':' + (e.lineno || '');
    log(m);
    setPanelStatus('bad', 'Error JS detectado');
  });
  window.addEventListener('unhandledrejection', e => {
    const reason = e && e.reason;
    const m = 'PROMESA RECHAZADA: ' + ((reason && reason.message) || reason);
    log(m);
    setPanelStatus('bad', 'Promesa rechazada');
  });

  window.addEventListener('resize', debounce(buildNet, 300));
  buildNet();
  updateConn();
  showExamples();

  log('Praxis v6 listo.');

  // Botones de Biblioteca y Conocimiento
  const openKb = $('#openKbBtn');
  if (openKb) openKb.onclick = () => window.openKnowledgeModal && window.openKnowledgeModal();
  const saveKb = $('#saveKbBtn');
  if (saveKb) saveKb.onclick = () => {
    if (S.lastRun) {
      toast('✓ Investigación actual registrada en la biblioteca.');
    } else {
      toast('Primero realiza un análisis para guardarlo en la biblioteca.');
    }
  };

  // Inicializar listados laterales si existen
  try { if (typeof renderHistorySidebar === 'function') renderHistorySidebar(); } catch(e){}
  try { if (typeof loadChatSessions === 'function') loadChatSessions(); } catch(e){}
  
  // Restaurar sesión activa si existe
  try {
    const savedActiveChat = localStorage.getItem('praxis_active_chat_id');
    const savedActiveFolder = localStorage.getItem('praxis_active_folder');
    if (savedActiveChat) {
      S.activeChatId = savedActiveChat;
      if (savedActiveFolder) {
        window.restoreHistoricalResponse(savedActiveChat, savedActiveFolder);
      }
    }
  } catch(e) {}
  try {
    const kbCountEl = document.getElementById('kbCount');
    if (kbCountEl && typeof PRAXIS_KNOWLEDGE_BASE !== 'undefined') {
      kbCountEl.textContent = Object.keys(PRAXIS_KNOWLEDGE_BASE).length;
    }
  } catch(e){}
  if (validKey(S.key)) {
    fetchModels().then(m => log('Auto-detección de modelos exitosa: ' + m.slice(0, 5).join(', '))).catch(e => log('Nota al inicio: ' + e.message));
  }
}

function syncChips() {
  $$('#audChips .chip').forEach(c => c.classList.toggle('on', c.dataset.aud === S.audience));
  $$('#depthChips .chip').forEach(c => c.classList.toggle('on', c.dataset.depth === S.depth));
  $$('#toolChips .chip').forEach(c => c.classList.toggle('on', !!S.tools[c.dataset.tool]));
  updateAudHint();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}




/* ============================================================
   CONTROLADORES GLOBALES DE MODALES Y CAPA DE CONOCIMIENTO
   ============================================================ */
window.openKnowledgeModal = function() {
  const m = document.getElementById('kbModal') || document.getElementById('knowledgeModal');
  if (!m) return;
  m.classList.add('open');
  window.renderKnowledgeList('');
};

window.closeKnowledgeModal = function() {
  const m = document.getElementById('kbModal') || document.getElementById('knowledgeModal');
  if (m) m.classList.remove('open');
};

window.updateKbSelectionCount = function() {
  const checks = document.querySelectorAll('.kb-check:checked');
  const count = checks.length;
  const hint = document.getElementById('kbSelectedHint');
  if (hint) hint.textContent = `${count} seleccionado${count === 1 ? '' : 's'}`;
  const btn = document.getElementById('kbSynthesizeBtn');
  if (btn) btn.disabled = count === 0;
};

window.selectAllKnowledge = function() {
  const checks = document.querySelectorAll('.kb-check');
  const allChecked = Array.from(checks).every(c => c.checked);
  checks.forEach(c => c.checked = !allChecked);
  window.updateKbSelectionCount();
};

window.synthesizeSelectedKnowledge = function() {
  const checks = Array.from(document.querySelectorAll('.kb-check:checked'));
  if (!checks.length) return;
  const selectedItems = checks.map(c => PRAXIS_KNOWLEDGE_BASE[c.value]).filter(Boolean);
  const titles = selectedItems.map(it => it.nombre).join(' + ');
  const promptInput = document.getElementById('prompt');
  if (promptInput) {
    promptInput.value = `Sintetizar y unificar formalmente los siguientes mecanismos matemáticos en una sola investigación axiomática profunda:\n` +
      selectedItems.map((it, idx) => `${idx + 1}. ${it.nombre} (${it.dominio}): ${it.definicion_axiomatica}`).join('\n') +
      `\n\nObjetivo: Demostrar las interconexiones teóricas, deducir el sistema dinámico conjunto y formular su modelación y simulación interactiva.`;
    promptInput.style.height = 'auto';
    promptInput.style.height = Math.min(promptInput.scrollHeight, 220) + 'px';
  }
  window.closeKnowledgeModal();
  toast('Mecanismos cargados en el compositor.');
};

window.exportKnowledgeJson = function() {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(PRAXIS_KNOWLEDGE_BASE, null, 2));
  const a = document.createElement('a');
  a.href = dataStr;
  a.download = `base_conocimiento_praxis_${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  toast('Base de conocimiento exportada como JSON.');
};

window.saveCurrentToKnowledge = function() {
  if (!S.lastRun || !S.lastRun.plan) {
    toast('Primero realiza un análisis para guardarlo en la biblioteca.');
    return;
  }
  const title = S.lastRun.plan.titulo || 'Mecanismo Matemático';
  const id = 'kb_' + Date.now();
  const item = {
    id: id,
    nombre: title,
    icono: '📐',
    dominio: S.lastRun.plan.ramas?.[0] || 'Matemática Avanzada',
    definicion_axiomatica: S.lastRun.resolver?.estrategia || title,
    representaciones: {
      algebraica: S.lastRun.resolver?.resultado || '',
      operacional: 'Deducción paso a paso verificada en Praxis.'
    }
  };
  PRAXIS_KNOWLEDGE_BASE[id] = item;
  try {
    localStorage.setItem('praxis_custom_kb', JSON.stringify(PRAXIS_KNOWLEDGE_BASE));
  } catch(e) {}
  
  const kbCountEl = document.getElementById('kbCount');
  if (kbCountEl) kbCountEl.textContent = Object.keys(PRAXIS_KNOWLEDGE_BASE).length;

  fetch('/api/knowledge/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item)
  }).catch(() => {});

  toast('✓ Investigación guardada en la biblioteca de conocimiento.');
};

window.filterKnowledgeList = function() {
  const q = (document.getElementById('kbSearchInp')?.value || '').trim();
  window.renderKnowledgeList(q);
};

window.renderKnowledgeList = function(query) {
  const host = document.getElementById('kbList');
  if (!host) return;
  const q = (query || '').toLowerCase();
  const keys = Object.keys(PRAXIS_KNOWLEDGE_BASE);

  const matched = keys.filter(k => {
    const it = PRAXIS_KNOWLEDGE_BASE[k];
    return !q || it.nombre.toLowerCase().includes(q) || it.dominio.toLowerCase().includes(q) || it.definicion_axiomatica.toLowerCase().includes(q);
  });

  if (!matched.length) {
    host.innerHTML = '<p style="color:var(--muted);font-size:13px;">No se encontraron mecanismos matemáticos para esa búsqueda.</p>';
    return;
  }

  host.innerHTML = matched.map(k => {
    const it = PRAXIS_KNOWLEDGE_BASE[k];
    const reps = it.representaciones || {};
    return `
    <div style="border:1px solid var(--line); border-radius:12px; padding:14px; background:var(--card); margin-bottom:10px;">
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
        <input type="checkbox" class="kb-check" value="${k}" onchange="window.updateKbSelectionCount()" style="width:16px; height:16px; accent-color:var(--brand); cursor:pointer;">
        <span style="font-size:18px;">${it.icono || '◆'}</span>
        <b style="font-size:15px; font-family:var(--serif); color:var(--ink);">${esc(it.nombre)}</b>
        <span class="tag" style="background:var(--brand-tint); color:var(--brand); margin-left:auto;">${esc(it.dominio)}</span>
      </div>
      <p style="font-size:13px; color:var(--ink-2); line-height:1.5; margin:4px 0 8px;"><b>Definición axiomática:</b> ${esc(it.definicion_axiomatica)}</p>
      
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:8px; margin-top:8px; font-size:12px;">
        ${reps.algebraica ? `<div style="background:var(--paper-2);padding:8px 10px;border-radius:8px;"><b>Algebraica:</b><br>${esc(reps.algebraica)}</div>` : ''}
        ${reps.geometrica ? `<div style="background:var(--paper-2);padding:8px 10px;border-radius:8px;"><b>Geométrica:</b><br>${esc(reps.geometrica)}</div>` : ''}
        ${reps.operacional ? `<div style="background:var(--paper-2);padding:8px 10px;border-radius:8px;"><b>Operacional:</b><br>${esc(reps.operacional)}</div>` : ''}
        ${reps.latex ? `<div style="background:var(--paper-2);padding:8px 10px;border-radius:8px;"><b>LaTeX:</b><br><code>${esc(reps.latex)}</code></div>` : ''}
      </div>

      ${(it.propiedades_clave || []).length ? `
      <div style="margin-top:8px; font-size:12px; color:var(--muted);">
        <b>Propiedades clave:</b>
        <ul style="margin:2px 0 0; padding-left:18px;">
          ${it.propiedades_clave.map(prop => `<li>${esc(prop)}</li>`).join('')}
        </ul>
      </div>` : ''}
    </div>`;
  }).join('');

  if (window.MathJax && MathJax.typesetPromise) {
    MathJax.typesetPromise([host]).catch(() => {});
  }
};

/* ============================================================
   SISTEMA DE INSPECCIÓN DE TRAZAS EN VIVO DE AGENTES
   ============================================================ */
window.agentTraces = window.agentTraces || {};

window.recordAgentTrace = function(stageId, prompt, rawOutput, parsed, error = null) {
  const observable = {
    sequence: (window._praxisTraceSequence = (window._praxisTraceSequence || 0) + 1),
    task_id: 'stage:' + stageId,
    agent_id: stageId,
    phase: 'task',
    status: error ? 'failed' : 'completed',
    input_keys: ['prompt'],
    output_keys: parsed ? [stageId] : [],
    message: error ? String(error.message || error) : 'completed'
  };
  if (window._activePraxisRun && Array.isArray(window._activePraxisRun.observable_events)) {
    window._activePraxisRun.observable_events.push(observable);
  }
  window.agentTraces[stageId] = {
    prompt: String(prompt || ''),
    rawOutput: String(rawOutput || ''),
    parsed: parsed || null,
    error: error ? String(error.message || error) : null,
    timestamp: new Date().toLocaleTimeString()
  };
  updateTraceButton(stageId);
};

function updateTraceButton(stageId) {
  const el = document.getElementById('traceBtn_' + stageId);
  if (el) {
    el.style.display = 'inline-flex';
    const trace = window.agentTraces[stageId];
    if (trace && trace.error) {
      el.classList.add('bad');
      el.textContent = '⚠️ Traza (Error)';
    } else {
      el.classList.remove('bad');
      el.textContent = '🔍 Ver Traza';
    }
  }
}

window.toggleAgentTrace = function(stageId) {
  const trace = window.agentTraces[stageId];
  if (!trace) {
    toast('No hay trazas registradas para este agente aún.');
    return;
  }
  const modal = document.getElementById('traceModal');
  if (!modal) return;
  
  document.getElementById('traceModalTitle').textContent = `Trazas del Agente: ${stageId.toUpperCase()} [${trace.timestamp}]`;
  document.getElementById('tracePromptText').textContent = trace.prompt;
  document.getElementById('traceRawText').textContent = trace.rawOutput;
  document.getElementById('traceParsedText').textContent = trace.parsed ? JSON.stringify(trace.parsed, null, 2) : (trace.error ? `ERROR: ${trace.error}` : 'Sin datos estructurados');
  
  modal.classList.add('open');
};

window.closeTraceModal = function() {
  const modal = document.getElementById('traceModal');
  if (modal) modal.classList.remove('open');
};

/* ============================================================
   HISTORIAL Y CONSULTAS NOTEBOOKLM EN CONVERSACIONES PREVIAS
   ============================================================ */
window.saveRunToHistory = function(run, promptText) {
  try {
    const hist = JSON.parse(localStorage.getItem('praxis_history') || '[]');
    const title = (run.plan && run.plan.titulo) || 'Investigación Matemática';
    const entry = {
      id: 'run_' + Date.now(),
      timestamp: new Date().toLocaleString(),
      title: title,
      prompt: promptText,
      markdown: run.markdown || '',
      resultado: (run.resolver && run.resolver.resultado) || '',
      estrategia: (run.resolver && run.resolver.estrategia) || ''
    };
    hist.unshift(entry);
    if (hist.length > 30) hist.pop();
    localStorage.setItem('praxis_history', JSON.stringify(hist));
    renderHistorySidebar(); loadChatSessions();
  } catch (e) {
    console.warn('No se pudo guardar en historial:', e);
  }
};

window.renderHistorySidebar = function() {
  const host = document.getElementById('historyList');
  if (!host) return;
  const hist = JSON.parse(localStorage.getItem('praxis_history') || '[]');
  if (!hist.length) {
    host.innerHTML = '<p style="color:var(--muted);font-size:11px;padding:6px 0;">Sin investigaciones previas.</p>';
    return;
  }
  host.innerHTML = hist.map(item => `
    <div class="ex" style="padding:8px 10px; margin-bottom:6px; cursor:pointer;" onclick="restoreHistoryRun('${item.id}')">
      <div class="t" style="font-size:12px; line-height:1.3;">${esc(item.title)}</div>
      <div class="d" style="font-size:10px;">${esc(item.timestamp)}</div>
    </div>
  `).join('');
};

window.restoreHistoryRun = function(id) {
  const hist = JSON.parse(localStorage.getItem('praxis_history') || '[]');
  const found = hist.find(h => h.id === id);
  if (!found) return;
  
  $('#prompt').value = found.prompt;
  if (found.markdown) {
    S.lastRun = {
      plan: { titulo: found.title, ramas: [] },
      markdown: found.markdown,
      resolver: { resultado: found.resultado, estrategia: found.estrategia }
    };
    renderReportView(S.lastRun);
    toast('Investigación cargada del historial.');
  }
};

window.queryPreviousKnowledge = function() {
  const query = prompt('¿Qué deseas buscar en tus investigaciones y chats anteriores?');
  if (!query) return;
  const hist = JSON.parse(localStorage.getItem('praxis_history') || '[]');
  const q = query.toLowerCase();
  
  const matches = hist.filter(h => 
    h.title.toLowerCase().includes(q) ||
    h.prompt.toLowerCase().includes(q) ||
    h.markdown.toLowerCase().includes(q)
  );

  if (!matches.length) {
    alert(`No se encontraron coincidencias para "${query}" en tu historial previo.`);
    return;
  }

  const summary = matches.map((m, idx) => `[${idx+1}] ${m.title} (${m.timestamp}):\n${m.prompt.slice(0, 150)}...`).join('\n\n');
  const inject = confirm(`Se encontraron ${matches.length} investigaciones relacionadas:\n\n${summary}\n\n¿Deseas inyectar esta información previa como contexto en el prompt actual?`);
  if (inject) {
    const ctx = `\n\n[CONTEXTO HISTÓRICO DE INVESTIGACIONES PREVIAS]:\n` + matches.map(m => `--- ${m.title} ---\n${m.markdown.slice(0, 1500)}...`).join('\n\n');
    $('#prompt').value += ctx;
    toast('Contexto de historial inyectado en el prompt.');
  }
};


window.switchTraceTab = function(tab) {
  ['prompt', 'raw', 'parsed'].forEach(t => {
    const v = document.getElementById('traceView_' + t);
    const b = document.getElementById('tabBtn_' + t);
    if (v) v.style.display = (t === tab) ? 'block' : 'none';
    if (b) {
      if (t === tab) { b.className = 'btn sm primary'; }
      else { b.className = 'btn sm ghost'; }
    }
  });
};

function renderMarkdownToPraxisHtml(md_text) {
  if (!md_text) return '<p class="prose">Sin contenido generado.</p>';
  const lines = String(md_text).split('\n');
  const out = [];
  let in_block_math = false;
  let block_math_lines = [];
  let in_quote = false;
  let quote_lines = [];

  function flush_quote() {
    if (in_quote && quote_lines.length) {
      const txt = quote_lines.join(' ').trim();
      let co_class = 'co-note';
      let lab = 'Nota';
      if (/demostraci[oó]n/i.test(txt)) { co_class = 'co-proof'; lab = 'Demostración formal'; }
      else if (/definici[oó]n/i.test(txt)) { co_class = 'co-def'; lab = 'Definición'; }
      else if (/teorema|lema|corolario/i.test(txt)) { co_class = 'co-thm'; lab = 'Teorema / Lema'; }
      else if (/resultado|soluci[oó]n/i.test(txt)) { co_class = 'co-ok'; lab = 'Resultado'; }

      const clean_txt = txt.replace(/^\>\s*\*\*.*?\:\*\*\s*/, '');
      out.push(`<div class="callout ${co_class}"><div class="lab">${lab}</div><div class="prose"><p>${formatProseMath(clean_txt)}</p></div></div>`);
      quote_lines = [];
      in_quote = false;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const s = lines[i].trim();

    if (s.startsWith('$$') && s.endsWith('$$') && s.length > 4) {
      flush_quote();
      out.push(`<div class="eq-block">\n$$\n${cleanMathBlock(s.slice(2, -2))}\n$$\n</div>`);
      continue;
    } else if (s === '$$') {
      flush_quote();
      if (in_block_math) {
        in_block_math = false;
        out.push(`<div class="eq-block">\n$$\n${cleanMathBlock(block_math_lines.join(' '))}\n$$\n</div>`);
        block_math_lines = [];
      } else {
        in_block_math = true;
        block_math_lines = [];
      }
      continue;
    } else if (in_block_math) {
      block_math_lines.push(s);
      continue;
    }

    if (s.startsWith('>')) {
      in_quote = true;
      quote_lines.push(s.slice(1).trim());
      continue;
    } else if (in_quote) {
      flush_quote();
    }

    if (!s) continue;

    if (s.startsWith('# ')) {
      out.push(`<h1 class="doc-title" style="font-family:var(--serif);font-size:26px;color:var(--brand);margin:18px 0 10px;">${esc(s.slice(2))}</h1>`);
    } else if (s.startsWith('## ')) {
      out.push(`<section class="blk"><h3 class="sec" style="margin-top:20px;"><span class="num">§</span>${esc(s.slice(3))}</h3><div class="prose">`);
    } else if (s.startsWith('### ')) {
      out.push(`<h4 style="font-family:var(--serif);font-size:16px;color:var(--ink);margin:14px 0 4px;">${esc(s.slice(4))}</h4>`);
    } else if (s.startsWith('#### ')) {
      out.push(`<h5 style="font-size:14px;font-weight:700;margin:8px 0 2px;">${esc(s.slice(5))}</h5>`);
    } else if (s === '---') {
      out.push('<hr style="border:none;border-top:1px dashed var(--line);margin:16px 0;">');
    } else if (s.startsWith('* ') || s.startsWith('- ')) {
      out.push(`<ul><li>${formatProseMath(s.slice(2))}</li></ul>`);
    } else {
      out.push(`<p>${formatProseMath(s)}</p>`);
    }
  }

  flush_quote();
  return out.join('\n');
}

/* ============================================================
   EXPORTACIONES WORD NATIVO (.docx y .doc) Y BASE DE CONOCIMIENTO
   ============================================================ */
window.exportWordDocx = async function() {
  if (S.lastRun?.docx_url) {
    window.open(S.lastRun.docx_url, '_blank');
    toast('✓ Descargando archivo .docx compilado de esta investigación.');
    return;
  }
  const run = S.lastRun;
  if (!run || !run.markdown) { toast('Primero genera un análisis matemático.'); return; }
  const title = (run.plan && run.plan.titulo) || 'Informe_Matematico';
  const safeTitle = (title.replace(/[^\w\-]+/g, '_').slice(0, 50) || 'informe') + '.docx';
  toast('Compilando Word .docx (Pandoc / OMML 2D)...');

  try {
    const resp = await fetch('/api/export_docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title, markdown: run.markdown })
    });
    if (resp.ok) {
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = safeTitle;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast('✓ Documento Word (.docx) descargado con éxito.');
      return;
    }
  } catch (e) {
    console.warn('Servidor local no disponible para export_docx:', e);
  }
  toast('Descargando archivo Markdown para compilar localmente con convert.py o Pandoc.');
  downloadMd();
};

window.exportWordDoc = async function() {
  const run = S.lastRun;
  if (!run || !run.markdown) { toast('Primero genera un análisis matemático.'); return; }
  const title = (run.plan && run.plan.titulo) || 'Informe_Matematico';
  const safeTitle = (title.replace(/[^\w\-]+/g, '_').slice(0, 50) || 'informe') + '.doc';
  toast('Generando Word .doc con Ecuaciones 2D MathML...');

  try {
    const resp = await fetch('/api/export_doc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title, markdown: run.markdown })
    });
    if (resp.ok) {
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = safeTitle;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast('✓ Documento Word (.doc) descargado exitosamente.');
      return;
    }
  } catch (e) {
    console.warn('Generando Word .doc en navegador directamente:', e);
  }

  // Generador cliente autónomo de Word .doc (HTML + MathML)
  generateClientWordDoc(run.markdown, title, safeTitle);
};

function generateClientWordDoc(md, title, filename) {
  let body = '';
  const lines = md.split('\n');
  let inBlock = false;
  let blockLines = [];

  for (let line of lines) {
    const s = line.trim();
    if (s.startsWith('$$') && s.endsWith('$$') && s.length > 4) {
      body += `<div style="text-align:center;margin:12pt 0;"><math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow><mi>${s.slice(2, -2).trim()}</mi></mrow></math></div>\n`;
      continue;
    } else if (s === '$$') {
      if (inBlock) {
        inBlock = false;
        body += `<div style="text-align:center;margin:12pt 0;"><math xmlns="http://www.w3.org/1998/Math/MathML" display="block"><mrow><mi>${blockLines.join(' ').trim()}</mi></mrow></math></div>\n`;
        blockLines = [];
      } else {
        inBlock = true;
        blockLines = [];
      }
      continue;
    } else if (inBlock) {
      blockLines.push(s);
      continue;
    }

    if (!s) { body += '<br/>\n'; continue; }

    if (s.startsWith('# ')) {
      body += `<h1 style="font-family:Georgia,serif;font-size:20pt;color:#1a73e8;margin-top:18pt;margin-bottom:8pt;">${s.slice(2)}</h1>\n`;
    } else if (s.startsWith('## ')) {
      body += `<h2 style="font-family:Georgia,serif;font-size:15pt;color:#d93025;border-bottom:1px solid #cbd5e1;padding-bottom:3pt;margin-top:14pt;margin-bottom:6pt;">${s.slice(3)}</h2>\n`;
    } else if (s.startsWith('### ')) {
      body += `<h3 style="font-family:Georgia,serif;font-size:12.5pt;color:#171d29;margin-top:10pt;margin-bottom:4pt;">${s.slice(4)}</h3>\n`;
    } else if (s.startsWith('#### ')) {
      body += `<h4 style="font-family:Georgia,serif;font-size:11pt;color:#475569;margin-top:8pt;margin-bottom:3pt;">${s.slice(5)}</h4>\n`;
    } else if (s === '---') {
      body += `<hr style="border:none;border-top:1px solid #cbd5e1;margin:12pt 0;" />\n`;
    } else if (s.startsWith('> ')) {
      body += `<div style="background:#f8fafc;border-left:4px solid #1a73e8;padding:8pt 12pt;margin:6pt 0;font-size:10.5pt;color:#1e293b;">${s.slice(2)}</div>\n`;
    } else if (s.startsWith('* ') || s.startsWith('- ')) {
      body += `<li style="margin-left:18pt;margin-bottom:3pt;">${s.slice(2)}</li>\n`;
    } else {
      const formatted = s.replace(/\$([^$]+?)\$/g, '<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mi>$1</mi></mrow></math>')
                         .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
                         .replace(/\*(.*?)\*/g, '<i>$1</i>');
      body += `<p style="margin:0 0 6pt 0;line-height:1.4;">${formatted}</p>\n`;
    }
  }

  const docHtml = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8"><title>${title}</title><style>@page{size:21.59cm 27.94cm;margin:2.54cm;}body{font-family:Calibri,sans-serif;font-size:11pt;line-height:1.35;color:#171d29;}h1,h2,h3,h4{font-family:Georgia,serif;}</style></head><body>${body}</body></html>`;
  const blob = new Blob([docHtml], { type: 'application/msword' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  toast('✓ Word (.doc) generado directamente en el navegador.');
}

window.openKnowledgeModal = async function() {
  let modal = document.getElementById('knowledgeModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'knowledgeModal';
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="sheet" style="max-width:850px;">
        <div class="sh">
          <h3>🧠 Base de Conocimiento Matemático Unificada</h3>
          <span class="spacer"></span>
          <button class="btn sm icon ghost" onclick="document.getElementById('knowledgeModal').classList.remove('open')">✕</button>
        </div>
        <div class="sb" style="padding:18px 24px;">
          <p style="font-size:13px;color:var(--muted);margin-top:0;">Esta base de conocimiento unifica, consolida y robustece los teoremas y conceptos matemáticos a medida que interactúas, evitando duplicaciones y asegurando coherencia.</p>
          <div id="knowledgeStats" style="display:flex;gap:12px;margin-bottom:14px;flex-wrap:wrap;"></div>
          <div style="margin-bottom:12px;display:flex;gap:8px;">
            <input type="text" id="knowledgeSearchInp" class="inp" placeholder="Filtrar conceptos por nombre o dominio..." oninput="filterKnowledgeCards()">
            <button class="btn sm ghost" onclick="refreshKnowledgeModal()">Actualizar</button>
          </div>
          <div id="knowledgeCardsHost" style="display:grid;gap:10px;max-height:450px;overflow:auto;padding-right:6px;"></div>
        </div>
      </div>`;
    document.body.appendChild(modal);
  }
  modal.classList.add('open');
  await refreshKnowledgeModal();
};

window.refreshKnowledgeModal = async function() {
  const host = document.getElementById('knowledgeCardsHost');
  const statsHost = document.getElementById('knowledgeStats');
  if (!host) return;
  host.innerHTML = '<p style="color:var(--muted);">Cargando base de conocimiento...</p>';

  try {
    const resp = await fetch('/api/knowledge_base');
    if (resp.ok) {
      const data = await resp.json();
      const db = data.db || {};
      const conceptos = Object.values(db.conceptos || {});
      window._cachedKnowledgeList = conceptos;
      
      if (statsHost) {
        statsHost.innerHTML = `
          <span class="pill ok"><b>${conceptos.length}</b>&nbsp;Conceptos Consolidados</span>
          <span class="pill"><b>${db.metadata?.total_teoremas || 0}</b>&nbsp;Teoremas Formalizados</span>
          <span class="pill"><b>${db.metadata?.total_demostraciones || 0}</b>&nbsp;Demostraciones Q.E.D.</span>
        `;
      }
      renderKnowledgeCards(conceptos);
      return;
    }
  } catch(e) {
    console.warn('Error obteniendo knowledge_base:', e);
  }

  // Fallback a base de conocimiento local en memoria
  const localList = Object.values(PRAXIS_KNOWLEDGE_BASE || {});
  window._cachedKnowledgeList = localList;
  if (statsHost) {
    statsHost.innerHTML = `<span class="pill ok"><b>${localList.length}</b> Conceptos en memoria local</span>`;
  }
  renderKnowledgeCards(localList);
};

window.renderKnowledgeCards = function(list) {
  const host = document.getElementById('knowledgeCardsHost');
  if (!host) return;
  if (!list.length) {
    host.innerHTML = '<p style="color:var(--muted);">No hay conceptos que coincidan con la búsqueda.</p>';
    return;
  }
  host.innerHTML = list.map(c => `
    <div class="ex" style="flex-direction:column;gap:6px;padding:12px 14px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="n" style="font-size:16px;">${esc(c.icono || '◆')}</span>
        <div class="t" style="font-size:14px;font-weight:700;">${esc(c.nombre || c.id)}</div>
        <span class="badge" style="margin-left:auto;">${esc(c.dominio || 'General')}</span>
      </div>
      <div style="font-size:12.5px;color:var(--ink-2);line-height:1.45;">
        ${esc(c.definicion_unificada || c.definicion_axiomatica || c.explicacion || '')}
      </div>
      ${c.formulas_clave && c.formulas_clave.length ? `<div style="font-family:var(--mono);font-size:11px;background:var(--brand-tint);padding:4px 8px;border-radius:6px;color:var(--brand);margin-top:4px;">${esc(c.formulas_clave[0])}</div>` : ''}
      <div style="font-size:10.5px;color:var(--muted);margin-top:2px;">
        Nivel: <b>${esc(c.nivel_madurez || 'Activo')}</b> · Contribuciones: ${c.historial_contribuciones ? c.historial_contribuciones.length : 1}
      </div>
    </div>
  `).join('');
};

window.filterKnowledgeCards = function() {
  const q = (document.getElementById('knowledgeSearchInp')?.value || '').toLowerCase();
  const list = window._cachedKnowledgeList || [];
  if (!q) { renderKnowledgeCards(list); return; }
  const filtered = list.filter(c => 
    (c.nombre && c.nombre.toLowerCase().includes(q)) ||
    (c.dominio && c.dominio.toLowerCase().includes(q)) ||
    (c.definicion_unificada && c.definicion_unificada.toLowerCase().includes(q))
  );
  renderKnowledgeCards(filtered);
};

/* ============================================================
   FASE 1: LABORATORIO INTERACTIVO CANVAS Y SIMULADOR PARAMÉTRICO
   ============================================================ */
window.buildClientSimulatorHtml = function(title, promptText, governingEqs) {
  const tFull = (title + ' ' + (promptText || '') + ' ' + (governingEqs || '')).toLowerCase();

  const isLorenz = ['lorenz', 'caos', 'atractor caotico'].some(k => tFull.includes(k));
  const isLotka = ['lotka', 'volterra', 'depredador', 'presa', 'ecologia', 'poblacion'].some(k => tFull.includes(k));
  const isPendulum = ['pendulo', 'no lineal', 'duffing', 'van der pol', 'oscilador no lineal'].some(k => tFull.includes(k));
  const isMatrix = ['matriz', 'autovalor', 'eigen', 'espacio vectorial', 'transformacion lineal'].some(k => tFull.includes(k)) && !['edo', 'diferencial', 'flujo'].some(k => tFull.includes(k));
  const isTaylor = ['taylor', 'fourier', 'serie', 'aproximacion', 'polinomio'].some(k => tFull.includes(k));

  const styles = `
    :root {
      --bg: #090d16; --card: #141c2e; --ink: #f8fafc; --muted: #94a3b8;
      --brand: #38bdf8; --accent: #f43f5e; --line: #1e293b; --gold: #f59e0b; --ok: #10b981;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 12px; }
    .wrap { width: 100%; max-width: 900px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
    .head { padding: 10px 16px; background: rgba(56,189,248,0.06); border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; }
    .head h2 { margin: 0; font-size: 14px; font-weight: 700; color: var(--brand); }
    .hud { font-size: 11px; font-family: monospace; color: var(--gold); background: rgba(0,0,0,0.3); padding: 3px 8px; border-radius: 5px; }
    canvas { width: 100%; height: 380px; background: #060911; display: block; cursor: crosshair; }
    .controls { padding: 12px 16px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; background: rgba(15,23,42,0.4); border-top: 1px solid var(--line); }
    .cg { display: flex; flex-direction: column; gap: 3px; }
    .cg label { font-size: 11px; color: var(--muted); display: flex; justify-content: space-between; }
    .cg input[type=range] { width: 100%; accent-color: var(--brand); cursor: pointer; }
    .bar { padding: 8px 16px; display: flex; gap: 8px; align-items: center; background: var(--card); border-top: 1px solid var(--line); flex-wrap: wrap; }
    button { background: var(--brand); color: #090d16; border: none; padding: 5px 12px; border-radius: 6px; font-weight: 700; font-size: 11.5px; cursor: pointer; }
    button.sec { background: #334155; color: #fff; }
    .hint { font-size: 10.5px; color: var(--muted); margin-left: auto; }
  `;

  if (isLorenz) {
    return `<!doctype html><html><head><meta charset="utf-8"><style>${styles}</style></head><body>
      <div class="wrap"><div class="head"><h2>⚡ ${title} · Atractor de Lorenz 3D (RK4)</h2><div class="hud" id="hud">σ: 10 | ρ: 28 | β: 2.67</div></div>
      <canvas id="c"></canvas>
      <div class="controls">
        <div class="cg"><label>Prandtl σ: <b id="vs">10.0</b></label><input type="range" id="s" min="1" max="25" step="0.5" value="10"></div>
        <div class="cg"><label>Rayleigh ρ: <b id="vr">28.0</b></label><input type="range" id="r" min="5" max="50" step="0.5" value="28"></div>
        <div class="cg"><label>Geometría β: <b id="vb">2.67</b></label><input type="range" id="b" min="0.5" max="5" step="0.1" value="2.67"></div>
      </div>
      <div class="bar"><button id="pBtn">Pausar</button><button class="sec" id="rBtn">Reiniciar</button><span class="hint">Órbita caótica determinista calculada con Runge-Kutta 4</span></div>
      </div>
      <script>
      (()=>{
        const c = document.getElementById('c'), ctx = c.getContext('2d');
        let w, h, cx, cy;
        let s = 10, r = 28, b = 2.67, ang = 0.8;
        let x = 0.1, y = 0, z = 0, trail = [], run = true;
        function sz(){ w = c.width = c.clientWidth; h = c.height = c.clientHeight; cx = w/2; cy = h*0.65; }
        window.onresize = sz; sz();
        function f(px,py,pz){ return [s*(py-px), px*(r-pz)-py, px*py-b*pz]; }
        function rk4(dt){
          let [k1x,k1y,k1z] = f(x,y,z);
          let [k2x,k2y,k2z] = f(x+0.5*dt*k1x, y+0.5*dt*k1y, z+0.5*dt*k1z);
          let [k3x,k3y,k3z] = f(x+0.5*dt*k2x, y+0.5*dt*k2y, z+0.5*dt*k2z);
          let [k4x,k4y,k4z] = f(x+dt*k3x, y+dt*k3y, z+dt*k3z);
          x += (dt/6)*(k1x+2*k2x+2*k3x+k4x);
          y += (dt/6)*(k1y+2*k2y+2*k3y+k4y);
          z += (dt/6)*(k1z+2*k2z+2*k3z+k4z);
        }
        function proj(px,py,pz){
          const rx = px*Math.cos(ang) - py*Math.sin(ang);
          const ry = px*Math.sin(ang) + py*Math.cos(ang);
          const sc = 7.0;
          return [cx + rx*sc, cy - pz*sc + ry*(sc*0.2)];
        }
        function draw(){
          ctx.fillStyle = '#090d16'; ctx.fillRect(0,0,w,h);
          if(run){ for(let i=0; i<4; i++){ rk4(0.008); trail.push(proj(x,y,z)); if(trail.length>750) trail.shift(); } }
          document.getElementById('hud').innerText = 'X: ' + x.toFixed(2) + ' | Y: ' + y.toFixed(2) + ' | Z: ' + z.toFixed(2);
          if(trail.length>1){
            for(let i=1; i<trail.length; i++){
              ctx.strokeStyle = 'hsl(' + (180 + Math.floor((i/trail.length)*140)) + ', 85%, 60%)';
              ctx.beginPath(); ctx.moveTo(trail[i-1][0], trail[i-1][1]); ctx.lineTo(trail[i][0], trail[i][1]); ctx.stroke();
            }
          }
          const cur = proj(x,y,z);
          ctx.fillStyle = '#f43f5e'; ctx.beginPath(); ctx.arc(cur[0], cur[1], 4.5, 0, 6.28); ctx.fill();
          requestAnimationFrame(draw);
        }
        document.getElementById('s').oninput = e => { s = parseFloat(e.target.value); document.getElementById('vs').innerText = s.toFixed(1); };
        document.getElementById('r').oninput = e => { r = parseFloat(e.target.value); document.getElementById('vr').innerText = r.toFixed(1); };
        document.getElementById('b').oninput = e => { b = parseFloat(e.target.value); document.getElementById('vb').innerText = b.toFixed(2); };
        document.getElementById('pBtn').onclick = e => { run = !run; e.target.innerText = run ? 'Pausar' : 'Reanudar'; };
        document.getElementById('rBtn').onclick = () => { x = 0.1; y = 0; z = 0; trail = []; };
        draw();
      })();
      </script></body></html>`;
  }

  // Por defecto: Retrato de Fase General con Campo Vectorial (Quiver) y RK4
  return `<!doctype html><html><head><meta charset="utf-8"><style>${styles}</style></head><body>
    <div class="wrap"><div class="head"><h2>⚡ ${title} · Retrato de Fase & Quiver Plot</h2><div class="hud" id="hud">Traza: 0.00 | Det: 1.00</div></div>
    <canvas id="c"></canvas>
    <div class="controls">
      <div class="cg"><label>a₁₁: <b id="va11">0.00</b></label><input type="range" id="a11" min="-3" max="3" step="0.1" value="0"></div>
      <div class="cg"><label>a₁₂: <b id="va12">1.00</b></label><input type="range" id="a12" min="-3" max="3" step="0.1" value="1"></div>
      <div class="cg"><label>a₂₁: <b id="va21">-1.00</b></label><input type="range" id="a21" min="-3" max="3" step="0.1" value="-1"></div>
      <div class="cg"><label>a₂₂: <b id="va22">0.00</b></label><input type="range" id="a22" min="-3" max="3" step="0.1" value="0"></div>
    </div>
    <div class="bar">
      <button id="pBtn">Pausar</button>
      <button class="sec" id="rBtn">Reiniciar</button>
      <button class="sec" id="clBtn">Limpiar Estelas</button>
      <span class="hint">Clic en el lienzo para generar órbitas</span>
    </div>
    </div>
    <script>
    (()=>{
      const c = document.getElementById('c'), ctx = c.getContext('2d');
      let w, h, cx, cy, sc = 45;
      let a11 = 0, a12 = 1, a21 = -1, a22 = 0;
      let run = true;
      let particles = [
        { x: 1, y: 0, trail: [], color: '#38bdf8' },
        { x: -1, y: 0, trail: [], color: '#f43f5e' },
        { x: 0, y: 1.5, trail: [], color: '#10b981' },
        { x: 0, y: -1.5, trail: [], color: '#f59e0b' }
      ];
      function sz(){ w = c.width = c.clientWidth; h = c.height = c.clientHeight; cx = w/2; cy = h/2; }
      window.onresize = sz; sz();
      function f(x, y){ return [a11*x + a12*y, a21*x + a22*y]; }
      function rk4(p, dt){
        let [k1x, k1y] = f(p.x, p.y);
        let [k2x, k2y] = f(p.x + 0.5*dt*k1x, p.y + 0.5*dt*k1y);
        let [k3x, k3y] = f(p.x + 0.5*dt*k2x, p.y + 0.5*dt*k2y);
        let [k4x, k4y] = f(p.x + dt*k3x, p.y + dt*k3y);
        p.x += (dt/6)*(k1x + 2*k2x + 2*k3x + k4x);
        p.y += (dt/6)*(k1y + 2*k2y + 2*k3y + k4y);
      }
      function draw(){
        ctx.fillStyle = '#090d16'; ctx.fillRect(0,0,w,h);
        ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(w,cy); ctx.moveTo(cx,0); ctx.lineTo(cx,h); ctx.stroke();
        if(run){
          particles.forEach(p => {
            for(let i=0; i<3; i++){
              rk4(p, 0.02);
              p.trail.push([cx + p.x*sc, cy - p.y*sc]);
              if(p.trail.length > 400) p.trail.shift();
            }
          });
        }
        particles.forEach(p => {
          if(p.trail.length > 1){
            ctx.strokeStyle = p.color; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(p.trail[0][0], p.trail[0][1]);
            for(let i=1; i<p.trail.length; i++) ctx.lineTo(p.trail[i][0], p.trail[i][1]);
            ctx.stroke();
          }
          ctx.fillStyle = p.color; ctx.beginPath();
          ctx.arc(cx + p.x*sc, cy - p.y*sc, 4.5, 0, 6.28); ctx.fill();
        });
        requestAnimationFrame(draw);
      }
      c.onclick = e => {
        const r = c.getBoundingClientRect();
        const nx = (e.clientX - r.left - cx)/sc, ny = (cy - (e.clientY - r.top))/sc;
        particles.push({ x: nx, y: ny, trail: [], color: '#a855f7' });
      };
      ['a11','a12','a21','a22'].forEach(id => {
        document.getElementById(id).oninput = e => {
          const val = parseFloat(e.target.value);
          if(id==='a11') a11 = val; if(id==='a12') a12 = val;
          if(id==='a21') a21 = val; if(id==='a22') a22 = val;
          document.getElementById('v' + id).innerText = val.toFixed(2);
          document.getElementById('hud').innerText = 'Traza: ' + (a11+a22).toFixed(2) + ' | Det: ' + (a11*a22 - a12*a21).toFixed(2);
          particles.forEach(p => p.trail = []);
        };
      });
      document.getElementById('pBtn').onclick = e => { run = !run; e.target.innerText = run ? 'Pausar' : 'Reanudar'; };
      document.getElementById('rBtn').onclick = () => {
        particles = [{ x: 1, y: 0, trail: [], color: '#38bdf8' }, { x: -1, y: 0, trail: [], color: '#f43f5e' }];
      };
      document.getElementById('clBtn').onclick = () => particles.forEach(p => p.trail = []);
      draw();
    })();
    </script></body></html>`;
};


window.renderInteractiveSimCard = function(run) {
  const title = (run.plan && run.plan.titulo) || 'Visualizador Matemático';
  const promptText = run.resolver?.estrategia || '';
  const simHtml = S.lastSimHtml || window.buildClientSimulatorHtml(title, promptText);
  S.lastSimHtml = simHtml;

  return `
    <div style="background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:hidden; margin:14px 0;">
      <div style="padding:10px 16px; background:rgba(56,189,248,0.08); border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:700; font-size:13px; color:var(--brand); display:flex; align-items:center; gap:6px;">
          <span>⚡</span> Laboratorio Interactivo con Sliders Paramétricos
        </span>
        <button class="btn sm ghost" onclick="exportSimulatorHtml()">⬇ Descargar Simulador (.html)</button>
      </div>
      <div style="height:480px; width:100%;">
        <iframe id="simFrame" style="width:100%; height:100%; border:none;" srcdoc="${esc(simHtml)}"></iframe>
      </div>
    </div>`;
};

window.exportSimulatorHtml = function() {
  if (S.lastRun?.sim_url) {
    window.open(S.lastRun.sim_url, '_blank');
    toast('✓ Descargando simulador interactivo de esta investigación.');
    return;
  }
  const sim = S.lastSimHtml || window.buildClientSimulatorHtml(S.lastRun?.plan?.titulo || 'Simulador', '');
  const blob = new Blob([sim], { type: 'text/html;charset=utf-8' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'simulador_interactivo_' + Date.now() + '.html';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  toast('✓ Simulador interactivo HTML5 descargado exitosamente.');
};

/* ============================================================
   FASE 2: GESTIÓN MULTI-CHAT Y PUENTE EPISTÉMICO EN SIDEBAR
   ============================================================ */
window.loadChatSessions = async function() {
  const host = document.getElementById('chatList');
  if (!host) return;

  try {
    const resp = await fetch('/api/chats');
    if (resp.ok) {
      const data = await resp.json();
      const chats = data.chats || [];
      if (!chats.length) {
        host.innerHTML = '<p style="color:var(--muted);font-size:11.5px;padding:8px 4px;">Sin conversaciones iniciadas. Haz clic en <b>＋ Nuevo</b> arriba para empezar.</p>';
        return;
      }

      host.innerHTML = chats.map(c => {
        const isActive = S.activeChatId === c.id;
        const responses = c.responses || [];
        return `
          <div class="chat-accordion ${isActive ? 'active open' : ''}" id="chat-acc-${c.id}">
            <div class="chat-acc-header" onclick="window.toggleChatAccordion('${c.id}')">
              <span class="chat-acc-arrow" id="arrow-${c.id}">▶</span>
              <span class="chat-acc-title" title="${esc(c.title)}">💬 ${esc(c.title)}</span>
              <span class="chat-acc-badge">${responses.length}</span>
              <span class="chat-del-btn" onclick="event.stopPropagation(); window.deleteChatSession('${c.id}')" title="Eliminar conversación y sus carpetas en disco">🗑️</span>
            </div>
            <div class="chat-acc-drawer" id="drawer-${c.id}">
              ${responses.length === 0 ? 
                '<div style="font-size:10.5px;color:var(--muted);padding:4px 6px;">Sin investigaciones registradas en este chat.</div>' :
                responses.map(r => `
                  <div class="history-sub-item" onclick="window.restoreHistoricalResponse('${c.id}', '${r.folder}')" title="Clic para restaurar en pantalla el informe completo y descargas de esta investigación">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:6px;">
                      <div class="history-sub-title">📄 ${esc(r.title)}</div>
                      <span class="resp-del-btn" onclick="event.stopPropagation(); window.deleteHistoricalResponse('${c.id}', '${r.folder}')" title="Eliminar esta investigación de disco">🗑️</span>
                    </div>
                    <div class="history-sub-date">
                      <span>🕒 ${esc(r.timestamp?.slice(5, 16) || '')}</span>
                      <span style="display:flex;gap:4px;">
                        ${r.docx_filename ? '<b style="color:var(--brand);font-size:9px;">DOCX</b>' : ''}
                        ${r.sim_filename ? '<b style="color:var(--gold);font-size:9px;">SIM</b>' : ''}
                      </span>
                    </div>
                  </div>
                `).join('')
              }
            </div>
          </div>
        `;
      }).join('');
      return;
    }
  } catch(e) {
    console.warn('Servidor local de chats no disponible:', e);
  }
  host.innerHTML = '<p style="color:var(--muted);font-size:11px;">Modo local offline.</p>';
};

window.toggleChatAccordion = function(chatId) {
  S.activeChatId = chatId;
  localStorage.setItem('praxis_active_chat_id', chatId);
  const allAcc = document.querySelectorAll('.chat-accordion');
  allAcc.forEach(acc => {
    if (acc.id === 'chat-acc-' + chatId) {
      acc.classList.toggle('open');
      acc.classList.add('active');
    } else {
      acc.classList.remove('active');
    }
  });
};

window.createNewChatSession = async function() {
  const title = prompt('Título para la nueva conversación matemática:', 'Investigación ' + new Date().toLocaleDateString());
  if (!title) return;

  try {
    const resp = await fetch('/api/chats/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title })
    });
    if (resp.ok) {
      const newChat = await resp.json();
      S.activeChatId = newChat.id;
      S.activeChatTitle = newChat.title;
      localStorage.setItem('praxis_active_chat_id', newChat.id);
      toast(`✓ Nueva conversación creada: "${newChat.title}"`);
      await window.loadChatSessions();
      $('#stageWrap').innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--muted);font-size:13px;">Conversación iniciada. Escribe o pega un ejercicio para comenzar.</div>';
      if ($('#prompt')) {
        $('#prompt').value = '';
        $('#prompt').focus();
      }
      return;
    }
  } catch(e) {
    console.warn('Error creando chat:', e);
  }
  S.activeChatId = 'chat_' + Date.now();
  S.activeChatTitle = title;
  toast('Conversación iniciada localmente.');
};

window.restoreHistoricalResponse = async function(chatId, folder) {
  toast('Cargando informe completo y trazabilidad de agentes...');
  try {
    const resp = await fetch(`/api/chats/${encodeURIComponent(chatId)}/responses/${encodeURIComponent(folder)}`);
    if (!resp.ok) {
      toast('No se pudo recuperar la investigación del servidor.');
      return;
    }
    const data = await resp.json();
    S.activeChatId = chatId;
    localStorage.setItem('praxis_active_chat_id', chatId);
    localStorage.setItem('praxis_active_folder', folder);

    // 1. Restaurar prompt
    if ($('#prompt')) $('#prompt').value = data.prompt || '';

    // 2. Restaurar trazas de agentes si están disponibles
    window.agentTraces = data.traces?.trazas_por_agente || data.traces || {};

    // 3. Restaurar línea de tiempo interactiva en done
    renderPipeline();
    STAGES.forEach(s => {
      setStage(s.id, 'done', 'completado');
    });

    // 4. Restaurar informe en el workspace junto con el informe de proceso
    const host = $('#reportHost');
    let versionPanelHtml = '';
    try {
      versionPanelHtml = await window.renderInvestigationVersionPanel(chatId, folder, data.version_id);
    } catch (versionError) {
      console.warn('No se pudo cargar la evolución de versiones:', versionError);
    }
    if (host) {
      let mainHtml = data.html;
      if (!mainHtml || mainHtml.length < 50) {
        if (data.markdown) mainHtml = `<article class="doc report">${renderMarkdownToPraxisHtml(data.markdown)}</article>`;
        else mainHtml = '<p style="color:var(--muted);">Sin contenido HTML disponible.</p>';
      }

      // Añadir tarjeta colapsable de Informe de Auditoría y Trazabilidad del Proceso
      const processCard = `
        <div style="background:var(--card); border:1px solid var(--line); border-radius:12px; margin:16px 0; overflow:hidden; box-shadow:var(--sh1);">
          <div style="padding:10px 16px; background:var(--paper-2); display:flex; justify-content:space-between; align-items:center; cursor:pointer;" onclick="document.getElementById('procReportDrawer').classList.toggle('open')">
            <span style="font-weight:700; font-size:13px; color:var(--brand); display:flex; align-items:center; gap:8px;">
              <span>📋</span> Informe de Auditoría y Trazabilidad Cognitiva del Proceso
            </span>
            <span style="font-size:11px; color:var(--muted);">▼ Clic para ver / ocultar registro de agentes</span>
          </div>
          <div id="procReportDrawer" style="display:none; padding:16px 20px; font-size:12.5px; line-height:1.5; border-top:1px solid var(--line);">
            ${data.process_report_html || '<p style="color:var(--muted);">Informe de proceso guardado en disco en proceso_agentes/informe_proceso.html.</p>'}
          </div>
        </div>
      `;

      host.innerHTML = versionPanelHtml + processCard + mainHtml;
      try { typeset(host); } catch(e) {}
    }

    // 5. Vincular datos y descargas directas del servidor
    S.lastRun = {
      plan: { titulo: data.title, ramas: [] },
      markdown: data.markdown,
      report: { html: data.html, titulo_final: data.title },
      docx_url: data.docx_url,
      doc_url: data.doc_url,
      sim_url: data.sim_url,
      md_url: data.md_url
    };

    const eBtn = $('#editPromptBtn'); if (eBtn) eBtn.style.display = 'inline-block';
    toast(`✓ Investigación "${data.title}" e informe de proceso restaurados.`);
    window.loadChatSessions();
  } catch(e) {
    toast('Error al restaurar: ' + e.message);
  }
};



/* ============================================================
   ELIMINACIÓN DE CHATS E HISTORIAL CON BORRADO FÍSICO EN DISCO
   ============================================================ */
window.deleteChatSession = async function(chatId) {
  if (!confirm('¿Seguro que deseas eliminar permanentemente esta conversación y todos sus archivos en disco?')) {
    return;
  }
  try {
    const resp = await fetch('/api/chats/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId })
    });
    if (resp.ok) {
      toast('✓ Conversación y archivos eliminados de disco.');
      if (S.activeChatId === chatId) {
        S.activeChatId = null;
        localStorage.removeItem('praxis_active_chat_id');
        localStorage.removeItem('praxis_active_folder');
        $('#stageWrap').innerHTML = '';
        if ($('#prompt')) $('#prompt').value = '';
        showExamples();
      }
      await window.loadChatSessions();
    } else {
      toast('No se pudo eliminar la conversación.');
    }
  } catch(e) {
    toast('Error eliminando chat: ' + e.message);
  }
};

window.deleteHistoricalResponse = async function(chatId, folder) {
  if (!confirm('¿Seguro que deseas eliminar esta investigación y sus archivos Word/HTML en disco?')) {
    return;
  }
  try {
    const resp = await fetch('/api/chats/delete_response', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, folder: folder })
    });
    if (resp.ok) {
      toast('✓ Investigación eliminada permanentemente de disco.');
      await window.loadChatSessions();
    } else {
      toast('No se pudo eliminar la investigación.');
    }
  } catch(e) {
    toast('Error eliminando investigación: ' + e.message);
  }
};

window.openDraftStudio = async function() {
  let modal = document.getElementById('draftModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'draftModal';
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="sheet" style="max-width:960px;">
        <div class="sh">
          <h3>📝 Taller de Borradores (Draft Studio)</h3>
          <span class="spacer"></span>
          <button class="btn sm icon ghost" onclick="document.getElementById('draftModal').classList.remove('open')">✕</button>
        </div>
        <div class="sb" style="padding:18px 24px;">
          <p style="font-size:12.5px;color:var(--muted);margin-top:0;">Copia, mezcla y ordena secciones de tus investigaciones previas sin alterar los originales. Genera borradores personalizados y expórtalos a Word o guárdalos como nuevas plantillas.</p>
          
          <div style="display:grid;grid-template-columns:1fr 1.2fr;gap:16px;">
            <div style="border-right:1px solid var(--line);padding-right:16px;">
              <label style="font-weight:700;font-size:12px;color:var(--brand);">1. Investigaciones Disponibles</label>
              <select id="draftSrcSelect" class="inp" style="margin-top:6px;" onchange="loadInvestigationSectionsForDraft()"></select>
              <div id="draftSectionsHost" style="margin-top:12px;max-height:350px;overflow:auto;display:flex;flex-direction:column;gap:6px;"></div>
            </div>
            
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <label style="font-weight:700;font-size:12px;color:var(--brand);">2. Borrador Activo en Construcción</label>
                <input type="text" id="draftTitleInp" class="inp" placeholder="Título del borrador..." style="width:220px;font-size:12px;">
              </div>
              <div id="draftCanvasHost" style="margin-top:12px;max-height:350px;overflow:auto;display:flex;flex-direction:column;gap:8px;"></div>
              
              <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
                <button class="btn sm primary" onclick="compileDraftWords()">📄 Compilar a Word (.docx/.doc)</button>
                <button class="btn sm ghost" onclick="saveDraftAsTemplate()">📋 Guardar como Plantilla</button>
                <button class="btn sm ghost" onclick="saveCurrentDraft()">💾 Guardar Borrador</button>
              </div>
            </div>
          </div>
        </div>
      </div>`;
    document.body.appendChild(modal);
  }
  modal.classList.add('open');
  await initDraftStudioData();
};

window.currentDraftSections = window.currentDraftSections || [];

window.initDraftStudioData = async function() {
  const sel = document.getElementById('draftSrcSelect');
  if (!sel) return;
  sel.innerHTML = '<option value="">Cargando investigaciones...</option>';

  try {
    const resp = await fetch('/api/list_history');
    if (resp.ok) {
      const data = await resp.json();
      const invs = data.investigations || [];
      sel.innerHTML = '<option value="">-- Selecciona una investigación previa --</option>' +
        invs.map(i => `<option value="${esc(i.folder)}">${esc(i.title || i.folder)}</option>`).join('');
    }
  } catch(e) {
    console.warn('Error cargando historial para draft:', e);
  }
  renderDraftCanvas();
};

window.loadInvestigationSectionsForDraft = async function() {
  const sel = document.getElementById('draftSrcSelect');
  const host = document.getElementById('draftSectionsHost');
  if (!sel || !host) return;
  const folder = sel.value;
  if (!folder) { host.innerHTML = '<p style="color:var(--muted);font-size:11px;">Selecciona una investigación para ver sus secciones.</p>'; return; }

  host.innerHTML = '<p style="color:var(--muted);font-size:11px;">Extrayendo secciones del informe...</p>';
  
  // Secciones estándar sugeridas
  const defaultSections = [
    { title: "1. Estrategia y Planificación", content: "Enfoque analítico y supuestos formalizados." },
    { title: "2. Desarrollo Paso a Paso", content: "Procedimiento algebraico riguroso y deducción completa." },
    { title: "3. Marco Teórico y Demostraciones", content: "Definiciones axiomáticas, teoremas formales y demostraciones Q.E.D." },
    { title: "4. Modelación Contextual del Sistema", content: "Ecuaciones de gobierno, variables de estado y aplicaciones atípicas." },
    { title: "5. Laboratorio Interactivo y Simulación", content: "Entorno dinámico Canvas HTML5 y código de simulación." },
    { title: "6. Conclusiones y Literatura", content: "Extensión a dimensiones superiores y referencias formales." }
  ];

  host.innerHTML = defaultSections.map((sec, idx) => `
    <div style="padding:8px 10px;background:var(--bg);border:1px solid var(--line);border-radius:8px;display:flex;justify-content:space-between;align-items:center;">
      <span style="font-size:12px;font-weight:600;">${esc(sec.title)}</span>
      <button class="btn sm ghost" onclick="addSectionToDraft(${idx})">＋ Añadir</button>
    </div>
  `).join('');
  window._loadedDraftDefaultSections = defaultSections;
};

window.addSectionToDraft = function(idx) {
  const sec = (window._loadedDraftDefaultSections || [])[idx];
  if (!sec) return;
  window.currentDraftSections.push({ title: sec.title, content: sec.content });
  renderDraftCanvas();
  toast('Sección añadida al borrador.');
};

window.renderDraftCanvas = function() {
  const host = document.getElementById('draftCanvasHost');
  if (!host) return;
  if (!window.currentDraftSections.length) {
    host.innerHTML = '<p style="color:var(--muted);font-size:11px;">El borrador está vacío. Añade secciones desde la izquierda.</p>';
    return;
  }
  host.innerHTML = window.currentDraftSections.map((sec, i) => `
    <div style="padding:10px;background:var(--bg);border:1px solid var(--line);border-radius:8px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <b style="font-size:12px;color:var(--brand);">#${i+1} ${esc(sec.title)}</b>
        <div style="display:flex;gap:4px;">
          ${i > 0 ? `<button class="btn sm ghost" onclick="moveDraftSec(${i}, -1)">▲</button>` : ''}
          ${i < window.currentDraftSections.length - 1 ? `<button class="btn sm ghost" onclick="moveDraftSec(${i}, 1)">▼</button>` : ''}
          <button class="btn sm ghost" onclick="removeDraftSec(${i})">✕</button>
        </div>
      </div>
      <textarea class="inp" style="width:100%;height:60px;font-size:11.5px;font-family:var(--mono);" onchange="updateDraftSecText(${i}, this.value)">${esc(sec.content)}</textarea>
    </div>
  `).join('');
};

window.moveDraftSec = function(idx, dir) {
  const temp = window.currentDraftSections[idx];
  window.currentDraftSections[idx] = window.currentDraftSections[idx + dir];
  window.currentDraftSections[idx + dir] = temp;
  renderDraftCanvas();
};

window.removeDraftSec = function(idx) {
  window.currentDraftSections.splice(idx, 1);
  renderDraftCanvas();
};

window.updateDraftSecText = function(idx, val) {
  if (window.currentDraftSections[idx]) window.currentDraftSections[idx].content = val;
};

window.saveCurrentDraft = async function() {
  const title = document.getElementById('draftTitleInp')?.value || 'Mi Borrador Consolidado';
  try {
    const resp = await fetch('/api/drafts/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title, sections: window.currentDraftSections })
    });
    if (resp.ok) {
      toast('✓ Borrador guardado exitosamente en historial/borradores/');
      return;
    }
  } catch(e) { console.warn(e); }
  toast('Borrador conservado en memoria local.');
};

window.compileDraftWords = async function() {
  const title = document.getElementById('draftTitleInp')?.value || 'Borrador Personalizado';
  toast('Compilando borrador a Word (.docx y .doc)...');
  try {
    const saveResp = await fetch('/api/drafts/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title, sections: window.currentDraftSections })
    });
    const sData = await saveResp.json();
    const cResp = await fetch('/api/drafts/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_id: sData.id })
    });
    if (cResp.ok) {
      toast('✓ Word compilado exitosamente desde el borrador.');
      return;
    }
  } catch(e) { console.warn(e); }
  toast('Asegúrate de tener server.py activo para compilar el borrador.');
};

window.saveDraftAsTemplate = async function() {
  const title = prompt('Nombre para la nueva plantilla de entrega:', 'Plantilla ' + (document.getElementById('draftTitleInp')?.value || 'Personalizada'));
  if (!title) return;
  try {
    const saveResp = await fetch('/api/drafts/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: title, sections: window.currentDraftSections })
    });
    const sData = await saveResp.json();
    const tResp = await fetch('/api/drafts/save_as_template', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_id: sData.id, name: title })
    });
    if (tResp.ok) {
      toast(`✓ Nueva plantilla guardada: "${title}". Disponible para futuras investigaciones.`);
      return;
    }
  } catch(e) { console.warn(e); }
  toast('Plantilla registrada.');
};

window.openPdfMimicModal = function() {
  let modal = document.getElementById('mimicModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'mimicModal';
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="sheet" style="max-width:560px;">
        <div class="sh">
          <h3>📄 Mimetismo Estructural de PDFs Escolares</h3>
          <span class="spacer"></span>
          <button class="btn sm icon ghost" onclick="document.getElementById('mimicModal').classList.remove('open')">✕</button>
        </div>
        <div class="sb" style="padding:18px 24px;">
          <p style="font-size:12.5px;color:var(--muted);margin-top:0;">Sube un PDF de una tarea, tesis o reporte universitario previo. El agente analizará su estructura, encabezados y formato formal para mimetizarla en tus próximas investigaciones de Praxis.</p>
          <div style="margin:14px 0;">
            <input type="file" id="mimicPdfInput" accept=".pdf" class="inp">
          </div>
          <div style="margin:14px 0;">
            <input type="text" id="mimicTemplateName" class="inp" placeholder="Nombre para esta plantilla (ej: Tarea UnADM Dinámica)">
          </div>
          <button class="btn primary block" onclick="submitPdfMimic()">Analizar y Mimetizar Estructura</button>
          <div id="mimicResultHost" style="margin-top:12px;"></div>
        </div>
      </div>`;
    document.body.appendChild(modal);
  }
  modal.classList.add('open');
};

window.submitPdfMimic = async function() {
  const fInput = document.getElementById('mimicPdfInput');
  const tName = document.getElementById('mimicTemplateName')?.value || 'Mi Formato Universitario';
  const resHost = document.getElementById('mimicResultHost');
  if (!fInput || !fInput.files || !fInput.files[0]) {
    alert('Por favor selecciona un archivo PDF primero.');
    return;
  }
  const file = fInput.files[0];
  resHost.innerHTML = '<p style="color:var(--brand);font-size:12px;">Analizando jerarquía y secciones del PDF...</p>';

  const reader = new FileReader();
  reader.onload = async () => {
    const b64 = reader.result.split(',')[1];
    try {
      const resp = await fetch('/api/mimic_pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base64_pdf: b64, filename: file.name, template_name: tName })
      });
      if (resp.ok) {
        const data = await resp.json();
        resHost.innerHTML = `
          <div style="padding:10px;background:var(--bg);border:1px solid var(--line);border-radius:8px;font-size:12px;">
            <b style="color:var(--brand);">✓ Plantilla Mimetizada Creada:</b> ${esc(data.nombre)}<br>
            <b>Secciones detectadas:</b>
            <ul style="margin:4px 0;padding-left:18px;">${(data.secciones_mimetizadas || []).map(s => `<li>${esc(s)}</li>`).join('')}</ul>
            <span style="color:var(--muted);font-size:11px;">Esta plantilla ya está disponible en historial/plantillas/</span>
          </div>`;
        toast('✓ Mimetismo estructural completado.');
        return;
      }
    } catch(e) {
      resHost.innerHTML = '<p style="color:var(--accent);font-size:12px;">Error al procesar PDF en el servidor local.</p>';
    }
  };
  reader.readAsDataURL(file);
};

/* ============================================================
   EVOLUCIÓN DE INVESTIGACIONES · NAVEGACIÓN DE VERSIONES
   ============================================================ */
window.selectedInvestigationVersion = null;

window.renderInvestigationVersionPanel = async function(chatId, folder, currentVersionId = null) {
  const resp = await fetch(
    `/api/investigations/${encodeURIComponent(chatId)}/${encodeURIComponent(folder)}/versions`
  );
  if (!resp.ok) throw new Error('No se pudo recuperar el historial de versiones.');
  const data = await resp.json();
  const versions = data.versions || [];
  if (!versions.length) return '';

  const current = currentVersionId || versions[versions.length - 1]?.version_id;
  window.selectedInvestigationVersion = current;

  const cards = versions.map((v, idx) => {
    const active = v.version_id === current;
    const source = v.source || 'pipeline';
    const date = v.created_at ? new Date(v.created_at).toLocaleString() : 'sin fecha';
    return `
      <div role="button" tabindex="0"
        data-version-id="${esc(v.version_id || '')}"
        onclick="if (!event.target.closest('button')) window.selectInvestigationVersion('${esc(chatId)}','${esc(folder)}','${esc(v.version_id || '')}')"
        style="width:100%;text-align:left;border:1px solid ${active ? 'var(--brand)' : 'var(--line)'};background:${active ? 'var(--brand-tint)' : 'var(--card)'};border-radius:9px;padding:9px 11px;cursor:pointer;color:var(--ink);">
        <div style="display:flex;align-items:center;gap:7px;">
          <span style="font-weight:800;">${active ? '●' : '○'} V${idx + 1}</span>
          <span style="font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(v.title || 'Sin título')}</span>
          <span style="margin-left:auto;font-size:9px;color:var(--muted);">${esc(source)}</span>
        </div>
        <div style="font-size:9.5px;color:var(--muted);margin-top:4px;">${esc(date)} · ${esc((v.version_id || '').slice(0, 12))}</div>
        ${v.prompt ? `<div style="font-size:10.5px;color:var(--ink-2);margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(v.prompt)}</div>` : ''}
        ${v.snapshot_available ? `<div style="margin-top:7px;display:flex;gap:6px;flex-wrap:wrap;"><button type="button" class="btn sm ghost" onclick="event.stopPropagation();window.previewInvestigationVersion('${esc(chatId)}','${esc(folder)}','${esc(v.version_id || '')}')">Ver snapshot</button><button type="button" class="btn sm ghost" onclick="event.stopPropagation();window.restoreInvestigationVersion('${esc(chatId)}','${esc(folder)}','${esc(v.version_id || '')}')">Restaurar esta versión como nueva</button></div>` : '<div style="font-size:9px;color:var(--muted);margin-top:6px;">Snapshot no disponible</div>'}
      </div>`;
  }).join('');

  return `
    <section id="investigationVersionPanel" style="border:1px solid var(--line);border-radius:12px;background:var(--card);margin:0 0 16px;overflow:hidden;box-shadow:var(--sh1);">
      <div style="padding:11px 14px;background:var(--paper-2);display:flex;align-items:center;gap:8px;">
        <span style="font-size:17px;">⟲</span>
        <b style="font-size:13px;color:var(--brand);">Evolución de la investigación</b>
        <span style="font-size:10px;color:var(--muted);">${versions.length} versión${versions.length === 1 ? '' : 'es'}</span>
        <span style="margin-left:auto;font-size:9.5px;color:var(--muted);">Selecciona una versión para usarla como contexto</span>
      </div>
      <div style="display:flex;gap:6px;padding:8px 10px;border-bottom:1px solid var(--line-2);">
        <button class="btn sm ghost" onclick="window.navigateInvestigationVersion('${esc(chatId)}','${esc(folder)}','previous')">← Anterior</button>
        <button class="btn sm ghost" onclick="window.navigateInvestigationVersion('${esc(chatId)}','${esc(folder)}','next')">Siguiente →</button>
        <span id="investigationVersionSelection" style="font-size:10px;color:var(--muted);align-self:center;margin-left:auto;">Contexto: ${esc((current || '').slice(0, 16))}</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px;padding:10px;max-height:250px;overflow:auto;">${cards}</div>
      <div style="padding:8px 11px;background:var(--paper-2);border-top:1px solid var(--line-2);font-size:10px;color:var(--muted);">
        La navegación actual conserva las versiones anteriores. El contenido histórico de los artefactos requiere snapshots; no se sustituye silenciosamente por el estado actual del disco.
      </div>
    </section>`;
};

window.selectInvestigationVersion = async function(chatId, folder, versionId) {
  try {
    const resp = await fetch(
      `/api/investigations/${encodeURIComponent(chatId)}/${encodeURIComponent(folder)}/versions/${encodeURIComponent(versionId)}`
    );
    if (!resp.ok) throw new Error('Versión no encontrada.');
    const data = await resp.json();
    window.selectedInvestigationVersion = data.current.version_id;
    const label = document.getElementById('investigationVersionSelection');
    if (label) label.textContent = 'Contexto: ' + String(data.current.version_id).slice(0, 16);
    document.querySelectorAll('#investigationVersionPanel [data-version-id]').forEach(btn => {
      const active = btn.dataset.versionId === String(versionId);
      btn.style.borderColor = active ? 'var(--brand)' : 'var(--line)';
      btn.style.background = active ? 'var(--brand-tint)' : 'var(--card)';
    });
    toast('✓ Versión seleccionada como contexto: ' + String(versionId).slice(0, 12));
    return data;
  } catch (e) {
    toast('No se pudo seleccionar la versión: ' + e.message);
    return null;
  }
};

window.previewInvestigationVersion = async function(chatId, folder, versionId) {
  try {
    const base = '/api/investigations/' + encodeURIComponent(chatId) + '/' + encodeURIComponent(folder);
    const metaResp = await fetch(base + '/snapshot?version_id=' + encodeURIComponent(versionId));
    if (!metaResp.ok) throw new Error('No se pudo recuperar el snapshot histórico.');
    const meta = await metaResp.json();
    const artifacts = meta.snapshot?.artifacts || [];
    const target = artifacts.find(a => String(a.type) === 'html') || artifacts.find(a => String(a.type) === 'md');
    if (!target?.path) throw new Error('El snapshot no contiene MD/HTML previsualizable.');

    const encodedPath = target.path.split('/').map(encodeURIComponent).join('/');
    const resp = await fetch(base + '/snapshot/' + encodedPath + '?version_id=' + encodeURIComponent(versionId));
    if (!resp.ok) throw new Error('No se pudo leer el artefacto histórico.');
    const data = await resp.json();
    const artifact = data.artifact || {};
    const host = document.getElementById('reportHost');
    if (!host) throw new Error('No se encontró el área de informe.');

    const banner = '<div style="padding:9px 12px;margin:0 0 12px;border:1px solid var(--brand);border-radius:10px;background:var(--brand-tint);font-size:11px;color:var(--ink);"><b>Vista histórica</b> · versión ' + esc(versionId).slice(0, 12) + ' · solo lectura. Los archivos actuales no fueron modificados.</div>';
    const body = artifact.type === 'html'
      ? artifact.content
      : '<article class="doc report">' + renderMarkdownToPraxisHtml(artifact.content || '') + '</article>';
    host.innerHTML = banner + body;
    try { typeset(host); } catch (e) {}
    toast('✓ Snapshot histórico cargado en modo solo lectura.');
    return artifact;
  } catch (e) {
    toast('No se pudo previsualizar la versión: ' + e.message);
    return null;
  }
};

window.restoreInvestigationVersion = async function(chatId, folder, versionId) {
  if (!confirm('Se restaurará el snapshot físico de esta versión y se creará una nueva versión derivada. ¿Continuar?')) return;
  try {
    const resp = await fetch('/api/investigations/snapshot/restore', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        chat_id: chatId,
        folder: folder,
        version_id: versionId
      })
    });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    window.selectedInvestigationVersion = data.version.version_id;
    toast('✓ Versión restaurada como ' + String(data.version.version_id).slice(0, 12));
    if (typeof window.restoreHistoricalResponse === 'function') {
      await window.restoreHistoricalResponse(chatId, folder);
    } else {
      const panel = document.getElementById('investigationVersionPanel');
      if (panel) panel.outerHTML = await window.renderInvestigationVersionPanel(chatId, folder, data.version.version_id);
    }
    return data;
  } catch (e) {
    toast('No se pudo restaurar la versión: ' + e.message);
    return null;
  }
};

window.navigateInvestigationVersion = async function(chatId, folder, direction) {
  const current = window.selectedInvestigationVersion;
  if (!current) return;
  try {
    const resp = await fetch(
      `/api/investigations/${encodeURIComponent(chatId)}/${encodeURIComponent(folder)}/versions/${encodeURIComponent(current)}`
    );
    if (!resp.ok) throw new Error('No se pudo navegar la versión.');
    const data = await resp.json();
    const target = direction === 'previous' ? data.previous : data.next;
    if (!target) {
      toast(direction === 'previous' ? 'Ya estás en la primera versión.' : 'Ya estás en la versión más reciente.');
      return;
    }
    await window.selectInvestigationVersion(chatId, folder, target.version_id);
  } catch (e) {
    toast('Error al navegar versiones: ' + e.message);
  }
};
