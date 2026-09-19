#!/usr/bin/env python3
"""
PRAXIS KNOWLEDGE ENGINE (v9.0)
Motor de Consolidación Incremental y Unificación de Conocimiento Matemático.
Deduplica, sintetiza y robustece conceptos, teoremas y demostraciones
a lo largo de las interacciones, evitando redundancias y generando
una base de conocimiento viva y acumulativa.
"""

import os
import json
import re
import datetime

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historial", "base_conocimiento")
JSON_PATH = os.path.join(KNOWLEDGE_DIR, "conocimiento_unificado.json")
MD_PATH = os.path.join(KNOWLEDGE_DIR, "base_conocimiento.md")
HTML_PATH = os.path.join(KNOWLEDGE_DIR, "base_conocimiento.html")

# Diccionario de normalización para mapear sinónimos a claves canónicas
CANONICAL_CONCEPT_MAP = {
    # Sistemas Dinámicos y EDOs
    "sistema lineal": "sistema_lineal_autonomo_plano",
    "sistema lineal autonomo": "sistema_lineal_autonomo_plano",
    "sistema dinamico lineal": "sistema_lineal_autonomo_plano",
    "sistema dinamico lineal plano": "sistema_lineal_autonomo_plano",
    "sistema planar": "sistema_lineal_autonomo_plano",
    "centro": "centro_topologico_espacio_fase",
    "centro lineal": "centro_topologico_espacio_fase",
    "centro topologico": "centro_topologico_espacio_fase",
    "estabilidad marginal": "centro_topologico_espacio_fase",
    "estabilidad lyapunov": "estabilidad_lyapunov",
    "funcion lyapunov": "estabilidad_lyapunov",
    "teorema picard": "teorema_picard_lindelof",
    "picard-lindelof": "teorema_picard_lindelof",
    "existencia y unicidad": "teorema_picard_lindelof",
    "teorema liouville": "teorema_liouville_conservacion_area",
    "conservacion de area": "teorema_liouville_conservacion_area",
    
    # Álgebra Lineal y Teoría Espectral
    "exponencial de matriz": "exponencial_de_matriz",
    "exponencial matricial": "exponencial_de_matriz",
    "polinomio caracteristico": "espectro_y_polinomio_caracteristico",
    "espectro matricial": "espectro_y_polinomio_caracteristico",
    "eigenvalores": "espectro_y_polinomio_caracteristico",
    "teorema cayley-hamilton": "teorema_cayley_hamilton",
    "cayley hamilton": "teorema_cayley_hamilton",
    "espacio vectorial": "espacio_vectorial_y_matriz_asociada",
    "transformacion lineal": "espacio_vectorial_y_matriz_asociada",
    "matriz asociada": "espacio_vectorial_y_matriz_asociada",

    # Análisis Real y Topología
    "teorema bolzano-weierstrass": "teorema_bolzano_weierstrass",
    "bolzano-weierstrass": "teorema_bolzano_weierstrass",
    "subsucesion monotona": "lema_subsucesiones_monotonas",
    "lema picos": "lema_subsucesiones_monotonas",
    "diagonalizacion cantor": "proceso_diagonalizacion_cantor",
    "diagonal cantor": "proceso_diagonalizacion_cantor",
    "espacio metrico": "espacio_euclidiano_y_norma",
    "norma euclidiana": "espacio_euclidiano_y_norma",
    "desigualdad cauchy-schwarz": "espacio_euclidiano_y_norma",
    "teorema heine-borel": "teorema_heine_borel_compacidad",
    "compacidad por sucesiones": "teorema_heine_borel_compacidad",
    "cerrado y acotado": "teorema_heine_borel_compacidad",
    "teorema riesz": "teorema_riesz_compacidad_bola",
    "compacidad bola unitaria": "teorema_riesz_compacidad_bola",

    # Mecánica Hamiltoniana y Geometría Simpléctica
    "sistema hamiltoniano": "sistemas_hamiltonianos_y_variedades_simplecticas",
    "hamiltoniano": "sistemas_hamiltonianos_y_variedades_simplecticas",
    "integral primera": "sistemas_hamiltonianos_y_variedades_simplecticas",
    "variedad simplectica": "sistemas_hamiltonianos_y_variedades_simplecticas",

    # Fundamentos Lógicos
    "conjunto vacio": "fundamentos_conjunto_vacio_y_explosion",
    "principio de explosion": "fundamentos_conjunto_vacio_y_explosion",
    "ex falso quodlibet": "fundamentos_conjunto_vacio_y_explosion",
    "objeto inicial": "fundamentos_conjunto_vacio_y_explosion"
}

def normalize_text(text):
    if not text: return ""
    t = text.lower()
    t = re.sub(r'[áàäâ]', 'a', t)
    t = re.sub(r'[éèëê]', 'e', t)
    t = re.sub(r'[íìïî]', 'i', t)
    t = re.sub(r'[óòöô]', 'o', t)
    t = re.sub(r'[úùüû]', 'u', t)
    t = re.sub(r'[^a-z0-9\s_-]', ' ', t)
    return " ".join(t.split())

def identify_canonical_key(name_or_desc):
    norm = normalize_text(name_or_desc)
    for trigger, canon_key in CANONICAL_CONCEPT_MAP.items():
        if trigger in norm:
            return canon_key
    # Si no hay match exacto, usar clave normalizada segura
    clean = re.sub(r'\s+', '_', norm)[:40].strip('_')
    return clean if clean else "concepto_general"

def load_knowledge_db():
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "metadata": {
            "version": "9.0",
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_conceptos": 0,
            "total_teoremas": 0,
            "total_demostraciones": 0
        },
        "dominios": {},
        "conceptos": {}
    }

def save_knowledge_db(db):
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    db["metadata"]["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db["metadata"]["total_conceptos"] = len(db.get("conceptos", {}))
    
    total_theorems = 0
    total_demos = 0
    for c in db.get("conceptos", {}).values():
        total_theorems += len(c.get("teoremas_asociados", []))
        total_demos += len(c.get("demostraciones", []))
    db["metadata"]["total_teoremas"] = total_theorems
    db["metadata"]["total_demostraciones"] = total_demos

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    export_knowledge_markdown(db)
    export_knowledge_html(db)

def deduplicate_and_merge_strings(existing_list, new_item):
    if not new_item: return existing_list
    norm_new = normalize_text(new_item)
    for item in existing_list:
        if normalize_text(item) == norm_new or (len(norm_new) > 20 and norm_new in normalize_text(item)):
            return existing_list # Ya cubierto
    existing_list.append(new_item.strip())
    return existing_list

def update_or_add_concept(db, canon_key, concept_data, investigation_ref):
    conceptos = db.setdefault("conceptos", {})
    
    if canon_key not in conceptos:
        # Nuevo concepto
        conceptos[canon_key] = {
            "id": canon_key,
            "nombre": concept_data.get("nombre", canon_key.replace('_', ' ').title()),
            "dominio": concept_data.get("dominio", "Matemáticas"),
            "definicion_unificada": concept_data.get("definicion", "").strip(),
            "formulas_clave": concept_data.get("formulas", []),
            "propiedades_unificadas": concept_data.get("propiedades", []),
            "teoremas_asociados": concept_data.get("teoremas", []),
            "demostraciones": concept_data.get("demostraciones", []),
            "aplicaciones": concept_data.get("aplicaciones", []),
            "generalizaciones": concept_data.get("generalizaciones", []),
            "relaciones_cruzadas": concept_data.get("relaciones", []),
            "historial_contribuciones": [investigation_ref],
            "nivel_madurez": "Formalizado (1 investigación)",
            "veces_enriquecido": 1
        }
    else:
        # Robustecer y unificar concepto existente (NO duplicar)
        c = conceptos[canon_key]
        c["veces_enriquecido"] += 1
        c["nivel_madurez"] = f"Consolidado ({len(c['historial_contribuciones']) + 1} investigaciones)"
        
        # Enriquecer contribuciones sin duplicar id
        if investigation_ref not in c["historial_contribuciones"]:
            c["historial_contribuciones"].append(investigation_ref)

        # Mejorar o sintetizar definición si la nueva es más detallada
        new_def = concept_data.get("definicion", "").strip()
        if new_def and (len(new_def) > len(c.get("definicion_unificada", "")) or not c.get("definicion_unificada")):
            if c.get("definicion_unificada") and normalize_text(new_def) != normalize_text(c["definicion_unificada"]):
                # Complementar si aporta ángulos nuevos
                c["definicion_unificada"] = c["definicion_unificada"] + "\n\n*Perspectiva complementaria:* " + new_def
            else:
                c["definicion_unificada"] = new_def

        # Unificar fórmulas
        for f in concept_data.get("formulas", []):
            deduplicate_and_merge_strings(c["formulas_clave"], f)

        # Unificar propiedades
        for p in concept_data.get("propiedades", []):
            deduplicate_and_merge_strings(c["propiedades_unificadas"], p)

        # Unificar teoremas
        for t in concept_data.get("teoremas", []):
            t_norm = normalize_text(t.get("nombre", ""))
            exists = any(normalize_text(et.get("nombre", "")) == t_norm for et in c["teoremas_asociados"])
            if not exists:
                c["teoremas_asociados"].append(t)

        # Unificar demostraciones
        for d in concept_data.get("demostraciones", []):
            d_norm = normalize_text(d.get("enfoque", "") + " " + d.get("demostracion", "")[:100])
            exists = any(normalize_text(ed.get("enfoque", "") + " " + ed.get("demostracion", "")[:100]) == d_norm for ed in c["demostraciones"])
            if not exists:
                c["demostraciones"].append(d)

        # Unificar aplicaciones y generalizaciones
        for a in concept_data.get("aplicaciones", []):
            deduplicate_and_merge_strings(c["aplicaciones"], a)
        for g in concept_data.get("generalizaciones", []):
            deduplicate_and_merge_strings(c["generalizaciones"], g)

        # Relaciones cruzadas
        for r in concept_data.get("relaciones", []):
            if r not in c["relaciones_cruzadas"] and r != canon_key:
                c["relaciones_cruzadas"].append(r)

def process_investigation_run(run_data, investigation_id, investigation_title):
    db = load_knowledge_db()
    
    inv_ref = {
        "id": investigation_id,
        "titulo": investigation_title,
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 1. Extraer ítems teóricos formales
    theory = run_data.get("theory") or {}
    ramas = theory.get("ramas") or []
    for r in ramas:
        dom = r.get("nombre", "Teoría General")
        items = r.get("items") or []
        for it in items:
            it_name = it.get("nombre", "")
            canon = identify_canonical_key(it_name)
            
            c_data = {
                "nombre": it_name,
                "dominio": dom,
                "definicion": it.get("explicacion", ""),
                "propiedades": [it.get("explicacion", "")] if it.get("explicacion") else [],
                "formulas": [],
                "teoremas": [],
                "demostraciones": []
            }
            
            if it.get("enunciado"):
                c_data["teoremas"].append({
                    "nombre": it_name,
                    "tipo": it.get("tipo", "Teorema"),
                    "enunciado": it.get("enunciado", "")
                })

            if it.get("demostracion_html") or it.get("demostracion"):
                demo_text = it.get("demostracion_html") or it.get("demostracion") or ""
                c_data["demostraciones"].append({
                    "teorema": it_name,
                    "enfoque": "Demostración constructiva formal",
                    "demostracion": demo_text
                })

            update_or_add_concept(db, canon, c_data, inv_ref)

    # 2. Extraer del resolutor (fórmulas e invariantes)
    resolver = run_data.get("resolver") or {}
    pasos = resolver.get("pasos") or []
    for p in pasos:
        p_tit = p.get("titulo", "")
        p_tool = p.get("herramienta", "")
        canon = identify_canonical_key(p_tit + " " + p_tool)
        
        c_data = {
            "nombre": p_tit or p_tool,
            "dominio": "Resolución y Métodos Operacionales",
            "definicion": p.get("explicacion", "") or p.get("html", ""),
            "formulas": [p.get("latex")] if p.get("latex") else [],
            "propiedades": [f"Herramienta: {p_tool}"] if p_tool else []
        }
        update_or_add_concept(db, canon, c_data, inv_ref)

    # 3. Extraer investigación y extensiones
    research = run_data.get("research") or {}
    generalizaciones = research.get("generalizaciones") or []
    for g in generalizaciones:
        g_tit = g.get("titulo", "") if isinstance(g, dict) else str(g)
        g_desc = g.get("descripcion", "") if isinstance(g, dict) else ""
        canon = identify_canonical_key(g_tit)
        c_data = {
            "nombre": g_tit,
            "dominio": "Investigación y Generalizaciones",
            "generalizaciones": [g_desc] if g_desc else [g_tit]
        }
        update_or_add_concept(db, canon, c_data, inv_ref)

    # Guardar base unificada
    save_knowledge_db(db)
    return db

def export_knowledge_markdown(db):
    lines = [
        "# Praxis · Base de Conocimiento Matemático Unificada",
        "",
        "> Compendio incremental, sintetizado y libre de duplicaciones.",
        f"> **Última actualización:** {db['metadata']['last_updated']} | **Conceptos:** {db['metadata']['total_conceptos']} | **Teoremas formalizados:** {db['metadata']['total_teoremas']}",
        "",
        "---",
        "",
        "## Índice Temático Consolidado",
        ""
    ]

    conceptos = db.get("conceptos", {})
    # Agrupar por dominio
    by_domain = {}
    for cid, c in conceptos.items():
        dom = c.get("dominio", "General")
        by_domain.setdefault(dom, []).append(c)

    for dom, clist in sorted(by_domain.items()):
        lines.append(f"### {dom}")
        for c in clist:
            lines.append(f"- [{c['nombre']}](#{c['id']}) — *{c.get('nivel_madurez', 'Activo')}*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Tratado Axiomático y Teórico Unificado")
    lines.append("")

    for dom, clist in sorted(by_domain.items()):
        lines.append(f"## Dominio: {dom}")
        lines.append("")
        for c in clist:
            lines.append(f"### <a id=\"{c['id']}\"></a>{c['nombre']}")
            lines.append(f"**Estado de Consolidación:** {c.get('nivel_madurez', 'v1')} | **Contribuciones:** {len(c.get('historial_contribuciones', []))} investigaciones")
            lines.append("")
            
            if c.get("definicion_unificada"):
                lines.append(f"**Definición Canónica:**")
                lines.append(f"> {c['definicion_unificada']}")
                lines.append("")

            if c.get("formulas_clave"):
                lines.append("**Fórmulas Clave e Invariantes:**")
                for f in c["formulas_clave"]:
                    clean_f = f.strip().strip('$')
                    lines.append(f"$$\n{clean_f}\n$$")
                lines.append("")

            if c.get("teoremas_asociados"):
                lines.append("**Teoremas y Lemas Formalizados:**")
                for t in c["teoremas_asociados"]:
                    lines.append(f"> **{t.get('tipo', 'Teorema')} ({t.get('nombre', '')}):** {t.get('enunciado', '')}")
                lines.append("")

            if c.get("demostraciones"):
                lines.append("**Demostraciones Rigurosas:**")
                for d in c["demostraciones"]:
                    lines.append(f"#### Demostración ({d.get('teorema', '')})")
                    clean_demo = re.sub(r'<[^>]+>', ' ', d.get('demostracion', ''))
                    lines.append(f"{clean_demo.strip()}")
                    lines.append("")

            if c.get("propiedades_unificadas"):
                lines.append("**Propiedades Clave:**")
                for p in c["propiedades_unificadas"]:
                    lines.append(f"- {p}")
                lines.append("")

            if c.get("generalizaciones") or c.get("aplicaciones"):
                lines.append("**Generalizaciones y Aplicaciones:**")
                for g in c.get("generalizaciones", []):
                    lines.append(f"- *Generalización:* {g}")
                for a in c.get("aplicaciones", []):
                    lines.append(f"- *Aplicación:* {a}")
                lines.append("")

            if c.get("relaciones_cruzadas"):
                lines.append(f"**Conceptos Relacionados:** {', '.join(c['relaciones_cruzadas'])}")
                lines.append("")

            lines.append("---")
            lines.append("")

    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def export_knowledge_html(db):
    # Generar versión HTML autónoma estilizada con MathJax
    md_content = ""
    if os.path.exists(MD_PATH):
        with open(MD_PATH, "r", encoding="utf-8") as f:
            md_content = f.read()

    # Convertir markdown básico a HTML para visualización limpia
    html_body = f"""<article class="doc report">
      <div class="doc-head">
        <div class="kicker">Praxis Epistemic Engine · v9.0</div>
        <h2>Base de Conocimiento Matemático Unificada</h2>
        <div class="prob"><b>Memoria Consolidada:</b> {db['metadata']['total_conceptos']} conceptos unificados, {db['metadata']['total_teoremas']} teoremas y {db['metadata']['total_demostraciones']} demostraciones formalizadas.</div>
      </div>
      <div class="doc-body" style="padding:20px 30px;">
        <pre style="white-space:pre-wrap;font-family:'IBM Plex Sans',sans-serif;font-size:14px;line-height:1.6;color:#171d29;">{md_content}</pre>
      </div>
    </article>"""

    doc_html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Praxis · Base de Conocimiento Matemático Unificada</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600;900&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<script>
window.MathJax = {{
  tex: {{ inlineMath: [["$", "$"]], displayMath: [["$$", "$$"]], processEscapes: true }},
  options: {{ skipHtmlTags: ["script", "noscript", "style", "textarea", "pre", "code"] }},
  startup: {{ typeset: true }}
}};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
:root{{--paper:#e7e6df;--card:#fbfaf5;--ink:#171d29;--brand:#1a73e8;--accent:#d93025;--line:#d7d6cc;--brand-tint:#e8f0fe;}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans',sans-serif;padding:32px 16px;}}
.wrap{{max-width:1040px;margin:0 auto;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px 32px;box-shadow:0 10px 30px rgba(20,30,40,.08);}}
.doc-head h2{{font-family:'Fraunces',serif;font-size:32px;margin:10px 0;color:var(--brand);}}
.prob{{background:var(--brand-tint);border-left:4px solid var(--brand);padding:12px 16px;border-radius:0 8px 8px 0;margin:16px 0;}}
</style>
</head><body><div class="wrap">{html_body}</div></body></html>"""

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(doc_html)

def query_relevant_knowledge(user_query, max_items=3):
    """Busca y extrae los conceptos consolidados más afines a la consulta para inyectarlos en agentes"""
    db = load_knowledge_db()
    conceptos = db.get("conceptos", {})
    if not conceptos:
        return ""

    query_norm = normalize_text(user_query)
    matches = []
    
    for cid, c in conceptos.items():
        score = 0
        c_norm = normalize_text(c["nombre"] + " " + cid.replace('_', ' ') + " " + c.get("dominio", ""))
        for word in query_norm.split():
            if len(word) >= 4 and word in c_norm:
                score += 2
            elif len(word) >= 4 and word in normalize_text(c.get("definicion_unificada", "")):
                score += 1
        if score > 0:
            matches.append((score, c))

    matches.sort(key=lambda x: x[0], reverse=True)
    selected = [m[1] for m in matches[:max_items]]

    if not selected:
        return ""

    ctx_lines = [
        "[CONOCIMIENTO PREVIO UNIFICADO DE PRAXIS]:",
        "A continuación se presentan los conceptos y teoremas formalizados en investigaciones previas. Construye y robustece directamente sobre ellos sin contradecirlos ni duplicarlos:"
    ]
    for sc in selected:
        ctx_lines.append(f"• CONCEPTO: {sc['nombre']} ({sc.get('dominio', '')}) [{sc.get('nivel_madurez', '')}]:")
        if sc.get("definicion_unificada"):
            ctx_lines.append(f"  Definición: {sc['definicion_unificada'][:300]}...")
        if sc.get("formulas_clave"):
            ctx_lines.append(f"  Fórmula: {sc['formulas_clave'][0]}")
        if sc.get("teoremas_asociados"):
            t = sc['teoremas_asociados'][0]
            ctx_lines.append(f"  Teorema consolidado: {t.get('nombre')}: {t.get('enunciado')[:250]}...")
        ctx_lines.append("")

    return "\n".join(ctx_lines)

if __name__ == "__main__":
    print("[Knowledge Engine] Base de conocimiento inicializada.")
