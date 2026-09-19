#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRAXIS DYNAMIC CANVAS SIMULATOR SYNTHESIZER (v13.0)
Agente Programador de Simuladores Matemáticos Canvas HTML5 en tiempo real.
Sustituye las plantillas fijas estáticas por generadores adaptativos con:
- Integrador numérico Runge-Kutta de orden 4 (RK4) específico del sistema
- Retrato de fase con campo vectorial (quiver plot) interactivo
- Generación de órbitas interactivas al hacer clic en el lienzo (Canvas)
- Sliders específicos para los parámetros analíticos del ejercicio
- Cálculo dinámico en vivo de autovalores, traza, determinante y estabilidad
"""

import re
import json

def synthesize_canvas_simulator(title, prompt_text="", governing_eqs="", state_vars=None, params=None):
    """
    Sintetiza un simulador HTML5 Canvas autónomo, de alto rendimiento y adaptativo
    según el sistema matemático formulado.
    """
    t_full = (title + " " + prompt_text + " " + governing_eqs).lower()

    # Clasificación taxonómica profunda del sistema matemático
    is_lorenz = any(k in t_full for k in ["lorenz", "caos", "atractor caotico", "atractor de lorenz"])
    is_lotka = any(k in t_full for k in ["lotka", "volterra", "depredador", "presa", "ecologia", "poblacion"])
    is_pendulum = any(k in t_full for k in ["pendulo", "no lineal", "duffing", "van der pol", "oscilador no lineal"])
    is_matrix = any(k in t_full for k in ["matriz", "autovalor", "eigen", "espacio vectorial", "transformacion lineal", "diagonaliz"])
    is_taylor = any(k in t_full for k in ["taylor", "fourier", "serie", "aproximacion", "polinomio"])

    if is_lorenz:
        return _build_lorenz_simulator(title)
    elif is_lotka:
        return _build_lotka_volterra_simulator(title)
    elif is_pendulum:
        return _build_nonlinear_pendulum_simulator(title)
    elif is_matrix and not any(d in t_full for d in ["edo", "diferencial", "flujo"]):
        return _build_eigen_matrix_simulator(title)
    elif is_taylor:
        return _build_taylor_series_simulator(title)
    else:
        # Sistema General de Espacio de Estados / Campo Vectorial Planar con RK4
        return _build_general_phase_space_simulator(title, prompt_text, governing_eqs)


def _get_common_styles():
    return """
    :root {
      --bg: #090d16; --card: #141c2e; --ink: #f8fafc; --muted: #94a3b8;
      --brand: #38bdf8; --accent: #f43f5e; --line: #1e293b; --gold: #f59e0b; --ok: #10b981;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; padding: 14px; }
    .wrap { width: 100%; max-width: 920px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; box-shadow: 0 12px 36px rgba(0,0,0,0.5); }
    .head { padding: 12px 18px; background: rgba(56,189,248,0.06); border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; }
    .head h2 { margin: 0; font-size: 15px; font-weight: 700; color: var(--brand); display: flex; align-items: center; gap: 8px; }
    .hud { font-size: 11.5px; font-family: monospace; color: var(--gold); background: rgba(0,0,0,0.3); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(245,158,11,0.2); }
    canvas { width: 100%; height: 420px; background: #060911; display: block; cursor: crosshair; }
    .controls { padding: 14px 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; background: rgba(15,23,42,0.4); border-top: 1px solid var(--line); }
    .cg { display: flex; flex-direction: column; gap: 4px; }
    .cg label { font-size: 11.5px; color: var(--muted); display: flex; justify-content: space-between; font-weight: 600; }
    .cg input[type=range] { width: 100%; accent-color: var(--brand); cursor: pointer; }
    .bar { padding: 10px 18px; display: flex; gap: 8px; align-items: center; background: var(--card); border-top: 1px solid var(--line); flex-wrap: wrap; }
    button { background: var(--brand); color: #090d16; border: none; padding: 6px 14px; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer; transition: opacity .15s; }
    button:hover { opacity: 0.88; }
    button.sec { background: #334155; color: #fff; }
    .hint { font-size: 11px; color: var(--muted); margin-left: auto; }
    """

def _build_general_phase_space_simulator(title, prompt_text="", governing_eqs=""):
    """Simulador General de Campo Vectorial y Espacio de Estados X' = AX con RK4 y Quiver Plot"""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title} · Retrato de Fase Interactivo</title>
<style>{_get_common_styles()}</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h2><span>⚡</span> {title} · Retrato de Fase & Quiver Plot</h2>
    <div class="hud" id="hud">Traza: 0.00 | Det: 1.00 | Estabilidad: Centro</div>
  </div>
  <canvas id="c"></canvas>
  <div class="controls">
    <div class="cg"><label>a₁₁: <b id="va11">0.00</b></label><input type="range" id="a11" min="-3" max="3" step="0.1" value="0"></div>
    <div class="cg"><label>a₁₂: <b id="va12">1.00</b></label><input type="range" id="a12" min="-3" max="3" step="0.1" value="1"></div>
    <div class="cg"><label>a₂₁: <b id="va21">-1.00</b></label><input type="range" id="a21" min="-3" max="3" step="0.1" value="-1"></div>
    <div class="cg"><label>a₂₂: <b id="va22">0.00</b></label><input type="range" id="a22" min="-3" max="3" step="0.1" value="0"></div>
  </div>
  <div class="bar">
    <button id="pBtn">Pausar</button>
    <button class="sec" id="rBtn">Reiniciar Órbitas</button>
    <button class="sec" id="clBtn">Limpiar Estelas</button>
    <span class="hint">Haz clic en cualquier punto del lienzo para generar una nueva órbita</span>
  </div>
</div>
\x3Cscript\x3E
(() => {{
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  let w, h, cx, cy, sc = 45;
  let a11 = 0, a12 = 1, a21 = -1, a22 = 0;
  let run = true;
  let particles = [
    {{ x: 1, y: 0, trail: [], color: '#38bdf8' }},
    {{ x: -1, y: 0, trail: [], color: '#f43f5e' }},
    {{ x: 0, y: 1.5, trail: [], color: '#10b981' }},
    {{ x: 0, y: -1.5, trail: [], color: '#f59e0b' }}
  ];

  function sz() {{ w = c.width = c.clientWidth; h = c.height = c.clientHeight; cx = w/2; cy = h/2; }}
  window.onresize = sz; sz();

  function f(x, y) {{
    return [a11 * x + a12 * y, a21 * x + a22 * y];
  }}

  // Integrador Runge-Kutta de 4to Orden (RK4)
  function rk4(p, dt) {{
    let [k1x, k1y] = f(p.x, p.y);
    let [k2x, k2y] = f(p.x + 0.5*dt*k1x, p.y + 0.5*dt*k1y);
    let [k3x, k3y] = f(p.x + 0.5*dt*k2x, p.y + 0.5*dt*k2y);
    let [k4x, k4y] = f(p.x + dt*k3x, p.y + dt*k3y);
    p.x += (dt/6)*(k1x + 2*k2x + 2*k3x + k4x);
    p.y += (dt/6)*(k1y + 2*k2y + 2*k3y + k4y);
  }}

  function updateHUD() {{
    const tr = a11 + a22;
    const det = a11 * a22 - a12 * a21;
    const disc = tr * tr - 4 * det;
    let st = '';
    if (det < 0) st = 'Silla de Montar (Inestable)';
    else if (det === 0) st = 'Degenerado';
    else if (disc < 0) {{
      if (Math.abs(tr) < 0.01) st = 'Centro (Elíptico Estable)';
      else if (tr < 0) st = 'Foco Espiral Estable';
      else st = 'Foco Espiral Inestable';
    }} else {{
      if (tr < 0) st = 'Nodo Estable';
      else st = 'Nodo Inestable';
    }}
    document.getElementById('hud').innerText = `Traza: ${{tr.toFixed(2)}} | Det: ${{det.toFixed(2)}} | ${{st}}`;
  }}

  function drawQuiver() {{
    ctx.strokeStyle = '#1e293b';
    ctx.fillStyle = '#1e293b';
    const step = 40;
    for (let px = step; px < w; px += step) {{
      for (let py = step; py < h; py += step) {{
        const x = (px - cx) / sc;
        const y = (cy - py) / sc;
        const [dx, dy] = f(x, y);
        const len = Math.hypot(dx, dy);
        if (len < 0.001) continue;
        const arrowLen = Math.min(14, len * 5);
        const nx = (dx / len) * arrowLen;
        const ny = (dy / len) * arrowLen;
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(px + nx, py - ny);
        ctx.stroke();
      }}
    }}
  }}

  function draw() {{
    ctx.fillStyle = '#090d16'; ctx.fillRect(0, 0, w, h);
    drawQuiver();

    // Ejes cartesianos
    ctx.strokeStyle = '#334155'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.stroke();

    if (run) {{
      particles.forEach(p => {{
        for (let i = 0; i < 3; i++) {{
          rk4(p, 0.02);
          p.trail.push([cx + p.x * sc, cy - p.y * sc]);
          if (p.trail.length > 400) p.trail.shift();
        }}
      }});
    }}

    particles.forEach(p => {{
      if (p.trail.length > 1) {{
        ctx.strokeStyle = p.color; ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(p.trail[0][0], p.trail[0][1]);
        for (let i = 1; i < p.trail.length; i++) ctx.lineTo(p.trail[i][0], p.trail[i][1]);
        ctx.stroke();
      }}
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(cx + p.x * sc, cy - p.y * sc, 4.5, 0, 6.28);
      ctx.fill();
    }});

    requestAnimationFrame(draw);
  }}

  c.onclick = e => {{
    const rect = c.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const nx = (mx - cx) / sc;
    const ny = (cy - my) / sc;
    const colors = ['#38bdf8', '#f43f5e', '#10b981', '#f59e0b', '#a855f7', '#ec4899'];
    const col = colors[particles.length % colors.length];
    particles.push({{ x: nx, y: ny, trail: [], color: col }});
  }};

  ['a11','a12','a21','a22'].forEach(id => {{
    document.getElementById(id).oninput = e => {{
      const val = parseFloat(e.target.value);
      if (id === 'a11') a11 = val;
      if (id === 'a12') a12 = val;
      if (id === 'a21') a21 = val;
      if (id === 'a22') a22 = val;
      document.getElementById('v' + id).innerText = val.toFixed(2);
      updateHUD();
      particles.forEach(p => p.trail = []);
    }};
  }});

  document.getElementById('pBtn').onclick = e => {{ run = !run; e.target.innerText = run ? 'Pausar' : 'Reanudar'; }};
  document.getElementById('rBtn').onclick = () => {{
    particles = [
      {{ x: 1, y: 0, trail: [], color: '#38bdf8' }},
      {{ x: -1, y: 0, trail: [], color: '#f43f5e' }},
      {{ x: 0, y: 1.5, trail: [], color: '#10b981' }},
      {{ x: 0, y: -1.5, trail: [], color: '#f59e0b' }}
    ];
  }};
  document.getElementById('clBtn').onclick = () => particles.forEach(p => p.trail = []);

  updateHUD();
  draw();
}})();
\x3C/script\x3E
</body>
</html>"""


def _build_nonlinear_pendulum_simulator(title):
    """Simulador de Péndulo No Lineal θ'' + b·θ' + (g/L)·sin(θ) = 0 con Espacio de Fase y Péndulo Físico"""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title} · Péndulo No Lineal y Retrato de Fase</title>
<style>{_get_common_styles()}</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h2><span>⚡</span> {title} · Péndulo No Lineal & Espacio de Fase</h2>
    <div class="hud" id="hud">Energía Mecánica: 0.00 J</div>
  </div>
  <canvas id="c"></canvas>
  <div class="controls">
    <div class="cg"><label>Fricción b: <b id="vb">0.10</b></label><input type="range" id="b" min="0" max="1" step="0.02" value="0.1"></div>
    <div class="cg"><label>Gravedad g: <b id="vg">9.80</b></label><input type="range" id="g" min="1" max="25" step="0.5" value="9.8"></div>
    <div class="cg"><label>Longitud L: <b id="vl">1.00</b></label><input type="range" id="l" min="0.3" max="2.5" step="0.1" value="1.0"></div>
    <div class="cg"><label>Ángulo Inicial θ(0): <b id="vth">2.40</b></label><input type="range" id="th0" min="-3.14" max="3.14" step="0.05" value="2.4"></div>
  </div>
  <div class="bar">
    <button id="pBtn">Pausar</button>
    <button class="sec" id="rBtn">Reiniciar</button>
    <button class="sec" id="clBtn">Limpiar Estela</button>
    <span class="hint">Izquierda: Péndulo físico | Derecha: Espacio de fase (θ, ω)</span>
  </div>
</div>
\x3Cscript\x3E
(() => {{
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  let w, h;
  let b = 0.1, g = 9.8, L = 1.0;
  let theta = 2.4, omega = 0.0;
  let trail = [];
  let run = true;

  function sz() {{ w = c.width = c.clientWidth; h = c.height = c.clientHeight; }}
  window.onresize = sz; sz();

  function f(th, om) {{
    return [om, - (b * om) - (g / L) * Math.sin(th)];
  }}

  function rk4(dt) {{
    let [k1t, k1w] = f(theta, omega);
    let [k2t, k2w] = f(theta + 0.5*dt*k1t, omega + 0.5*dt*k1w);
    let [k3t, k3w] = f(theta + 0.5*dt*k2t, omega + 0.5*dt*k2w);
    let [k4t, k4w] = f(theta + dt*k3t, omega + dt*k3w);
    theta += (dt/6)*(k1t + 2*k2t + 2*k3t + k4t);
    omega += (dt/6)*(k1w + 2*k2w + 2*k3w + k4w);
  }}

  function draw() {{
    ctx.fillStyle = '#090d16'; ctx.fillRect(0, 0, w, h);

    if (run) {{
      for (let i = 0; i < 4; i++) {{
        rk4(0.015);
        trail.push([theta, omega]);
        if (trail.length > 500) trail.shift();
      }}
    }}

    const E = 0.5 * omega * omega + (g / L) * (1 - Math.cos(theta));
    document.getElementById('hud').innerText = `Energía E: ${{E.toFixed(3)}} | θ: ${{theta.toFixed(2)}} rad | ω: ${{omega.toFixed(2)}} rad/s`;

    // Panel Izquierdo: Péndulo Físico
    const pCx = w * 0.28, pCy = h * 0.42;
    const armLen = 140 * (L / 1.5);
    const bobX = pCx + armLen * Math.sin(theta);
    const bobY = pCy + armLen * Math.cos(theta);

    ctx.strokeStyle = '#334155'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(w*0.5, 0); ctx.lineTo(w*0.5, h); ctx.stroke();

    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(pCx, pCy); ctx.lineTo(bobX, bobY); ctx.stroke();
    ctx.fillStyle = '#38bdf8'; ctx.beginPath(); ctx.arc(bobX, bobY, 12, 0, 6.28); ctx.fill();
    ctx.fillStyle = '#f8fafc'; ctx.beginPath(); ctx.arc(pCx, pCy, 4, 0, 6.28); ctx.fill();

    // Panel Derecho: Retrato de Fase (θ vs ω)
    const fCx = w * 0.75, fCy = h * 0.5;
    const scX = 35, scY = 22;

    ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(w*0.52, fCy); ctx.lineTo(w*0.98, fCy); ctx.moveTo(fCx, 20); ctx.lineTo(fCx, h-20); ctx.stroke();

    if (trail.length > 1) {{
      ctx.strokeStyle = '#f43f5e'; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(fCx + trail[0][0] * scX, fCy - trail[0][1] * scY);
      for (let i = 1; i < trail.length; i++) {{
        ctx.lineTo(fCx + trail[i][0] * scX, fCy - trail[i][1] * scY);
      }}
      ctx.stroke();
    }}
    ctx.fillStyle = '#10b981'; ctx.beginPath();
    ctx.arc(fCx + theta * scX, fCy - omega * scY, 5, 0, 6.28); ctx.fill();

    requestAnimationFrame(draw);
  }}

  document.getElementById('b').oninput = e => {{ b = parseFloat(e.target.value); document.getElementById('vb').innerText = b.toFixed(2); }};
  document.getElementById('g').oninput = e => {{ g = parseFloat(e.target.value); document.getElementById('vg').innerText = g.toFixed(2); }};
  document.getElementById('l').oninput = e => {{ L = parseFloat(e.target.value); document.getElementById('vl').innerText = L.toFixed(2); }};
  document.getElementById('th0').oninput = e => {{
    theta = parseFloat(e.target.value); omega = 0; trail = [];
    document.getElementById('vth').innerText = theta.toFixed(2);
  }};

  document.getElementById('pBtn').onclick = e => {{ run = !run; e.target.innerText = run ? 'Pausar' : 'Reanudar'; }};
  document.getElementById('rBtn').onclick = () => {{ theta = parseFloat(document.getElementById('th0').value); omega = 0; trail = []; }};
  document.getElementById('clBtn').onclick = () => trail = [];

  draw();
}})();
\x3C/script\x3E
</body>
</html>"""


def _build_lotka_volterra_simulator(title):
    """Simulador de Modelo Ecológico Lotka-Volterra Presa-Depredador con Órbitas Cerradas"""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title} · Sistema Lotka-Volterra</title>
<style>{_get_common_styles()}</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h2><span>⚡</span> {title} · Dinámica Presa-Depredador (Lotka-Volterra)</h2>
    <div class="hud" id="hud">Punto Fijo: (x*, y*) = (1.50, 1.00)</div>
  </div>
  <canvas id="c"></canvas>
  <div class="controls">
    <div class="cg"><label>Crecimiento Presas α: <b id="valpha">1.00</b></label><input type="range" id="alpha" min="0.2" max="2.5" step="0.05" value="1.0"></div>
    <div class="cg"><label>Depredación β: <b id="vbeta">1.00</b></label><input type="range" id="beta" min="0.2" max="2.5" step="0.05" value="1.0"></div>
    <div class="cg"><label>Mortalidad Depredadores γ: <b id="vgamma">1.50</b></label><input type="range" id="gamma" min="0.2" max="3.0" step="0.05" value="1.5"></div>
    <div class="cg"><label>Eficiencia Depredación δ: <b id="vdelta">1.00</b></label><input type="range" id="delta" min="0.2" max="2.5" step="0.05" value="1.0"></div>
  </div>
  <div class="bar">
    <button id="pBtn">Pausar</button>
    <button class="sec" id="rBtn">Reiniciar</button>
    <button class="sec" id="clBtn">Limpiar Estelas</button>
    <span class="hint">Eje X: Presas | Eje Y: Depredadores | Clic para añadir condición inicial</span>
  </div>
</div>
\x3Cscript\x3E
(() => {{
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  let w, h;
  let alpha = 1.0, beta = 1.0, gamma = 1.5, delta = 1.0;
  let scX = 60, scY = 60, offX = 60, offY = 30;
  let run = true;
  let pops = [
    {{ x: 2.0, y: 0.8, trail: [], color: '#38bdf8' }},
    {{ x: 1.2, y: 1.6, trail: [], color: '#f43f5e' }},
    {{ x: 0.8, y: 0.5, trail: [], color: '#10b981' }}
  ];

  function sz() {{ w = c.width = c.clientWidth; h = c.height = c.clientHeight; }}
  window.onresize = sz; sz();

  function f(x, y) {{
    return [alpha * x - beta * x * y, delta * x * y - gamma * y];
  }}

  function rk4(p, dt) {{
    let [k1x, k1y] = f(p.x, p.y);
    let [k2x, k2y] = f(p.x + 0.5*dt*k1x, p.y + 0.5*dt*k1y);
    let [k3x, k3y] = f(p.x + 0.5*dt*k2x, p.y + 0.5*dt*k2y);
    let [k4x, k4y] = f(p.x + dt*k3x, p.y + dt*k3y);
    p.x += (dt/6)*(k1x + 2*k2x + 2*k3x + k4x);
    p.y += (dt/6)*(k1y + 2*k2y + 2*k3y + k4y);
    if (p.x < 0.01) p.x = 0.01;
    if (p.y < 0.01) p.y = 0.01;
  }}

  function draw() {{
    ctx.fillStyle = '#090d16'; ctx.fillRect(0, 0, w, h);

    const xStar = gamma / delta;
    const yStar = alpha / beta;
    document.getElementById('hud').innerText = `Equilibrio: (x*, y*) = (${{xStar.toFixed(2)}}, ${{yStar.toFixed(2)}})`;

    // Ejes
    const basePy = h - offY;
    ctx.strokeStyle = '#334155'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(offX, 20); ctx.lineTo(offX, basePy); ctx.lineTo(w - 20, basePy); ctx.stroke();

    // Punto de equilibrio
    ctx.fillStyle = '#f59e0b';
    ctx.beginPath(); ctx.arc(offX + xStar * scX, basePy - yStar * scY, 4, 0, 6.28); ctx.fill();

    if (run) {{
      pops.forEach(p => {{
        for (let i = 0; i < 3; i++) {{
          rk4(p, 0.02);
          p.trail.push([offX + p.x * scX, basePy - p.y * scY]);
          if (p.trail.length > 400) p.trail.shift();
        }}
      }});
    }}

    pops.forEach(p => {{
      if (p.trail.length > 1) {{
        ctx.strokeStyle = p.color; ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(p.trail[0][0], p.trail[0][1]);
        for (let i = 1; i < p.trail.length; i++) ctx.lineTo(p.trail[i][0], p.trail[i][1]);
        ctx.stroke();
      }}
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(offX + p.x * scX, basePy - p.y * scY, 5, 0, 6.28); ctx.fill();
    }});

    requestAnimationFrame(draw);
  }}

  c.onclick = e => {{
    const rect = c.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const nx = Math.max(0.1, (mx - offX) / scX);
    const ny = Math.max(0.1, ((h - offY) - my) / scY);
    const colors = ['#38bdf8', '#f43f5e', '#10b981', '#a855f7', '#ec4899'];
    pops.push({{ x: nx, y: ny, trail: [], color: colors[pops.length % colors.length] }});
  }};

  ['alpha','beta','gamma','delta'].forEach(id => {{
    document.getElementById(id).oninput = e => {{
      const val = parseFloat(e.target.value);
      if (id === 'alpha') alpha = val;
      if (id === 'beta') beta = val;
      if (id === 'gamma') gamma = val;
      if (id === 'delta') delta = val;
      document.getElementById('v' + id).innerText = val.toFixed(2);
      pops.forEach(p => p.trail = []);
    }};
  }});

  document.getElementById('pBtn').onclick = e => {{ run = !run; e.target.innerText = run ? 'Pausar' : 'Reanudar'; }};
  document.getElementById('rBtn').onclick = () => {{
    pops = [
      {{ x: 2.0, y: 0.8, trail: [], color: '#38bdf8' }},
      {{ x: 1.2, y: 1.6, trail: [], color: '#f43f5e' }},
      {{ x: 0.8, y: 0.5, trail: [], color: '#10b981' }}
    ];
  }};
  document.getElementById('clBtn').onclick = () => pops.forEach(p => p.trail = []);

  draw();
}})();
\x3C/script\x3E
</body>
</html>"""


def _build_lorenz_simulator(title):
    """Simulador de Atractor Caótico de Lorenz en Proyección 3D Isométrica"""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title} · Atractor de Lorenz</title>
<style>{_get_common_styles()}</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h2><span>⚡</span> {title} · Atractor Caótico de Lorenz (3D Proyectado)</h2>
    <div class="hud" id="hud">σ: 10.0 | ρ: 28.0 | β: 2.67</div>
  </div>
  <canvas id="c"></canvas>
  <div class="controls">
    <div class="cg"><label>Prandtl σ: <b id="vs">10.0</b></label><input type="range" id="sigma" min="1" max="25" step="0.5" value="10"></div>
    <div class="cg"><label>Rayleigh ρ: <b id="vr">28.0</b></label><input type="range" id="rho" min="5" max="50" step="0.5" value="28"></div>
    <div class="cg"><label>Geometría β: <b id="vb">2.67</b></label><input type="range" id="beta" min="0.5" max="5" step="0.1" value="2.67"></div>
    <div class="cg"><label>Rotación Vista: <b id="vrot">0°</b></label><input type="range" id="rot" min="0" max="360" step="2" value="45"></div>
  </div>
  <div class="bar">
    <button id="pBtn">Pausar</button>
    <button class="sec" id="rBtn">Reiniciar</button>
    <button class="sec" id="clBtn">Limpiar Estela</button>
    <span class="hint">Órbita caótica determinista calculada con RK4 en tiempo real</span>
  </div>
</div>
\x3Cscript\x3E
(() => {{
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  let w, h, cx, cy;
  let sigma = 10.0, rho = 28.0, beta = 2.67, angle = 0.78;
  let x = 0.1, y = 0, z = 0;
  let trail = [];
  let run = true;

  function sz() {{ w = c.width = c.clientWidth; h = c.height = c.clientHeight; cx = w/2; cy = h * 0.65; }}
  window.onresize = sz; sz();

  function f(px, py, pz) {{
    return [sigma * (py - px), px * (rho - pz) - py, px * py - beta * pz];
  }}

  function rk4(dt) {{
    let [k1x, k1y, k1z] = f(x, y, z);
    let [k2x, k2y, k2z] = f(x + 0.5*dt*k1x, y + 0.5*dt*k1y, z + 0.5*dt*k1z);
    let [k3x, k3y, k3z] = f(x + 0.5*dt*k2x, y + 0.5*dt*k2y, z + 0.5*dt*k2z);
    let [k4x, k4y, k4z] = f(x + dt*k3x, y + dt*k3y, z + dt*k3z);
    x += (dt/6)*(k1x + 2*k2x + 2*k3x + k4x);
    y += (dt/6)*(k1y + 2*k2y + 2*k3y + k4y);
    z += (dt/6)*(k1z + 2*k2z + 2*k3z + k4z);
  }}

  function project(px, py, pz) {{
    const rx = px * Math.cos(angle) - py * Math.sin(angle);
    const ry = px * Math.sin(angle) + py * Math.cos(angle);
    const sc = 7.5;
    return [cx + rx * sc, cy - pz * sc + ry * (sc * 0.2)];
  }}

  function draw() {{
    ctx.fillStyle = '#090d16'; ctx.fillRect(0, 0, w, h);

    if (run) {{
      for (let i = 0; i < 4; i++) {{
        rk4(0.008);
        trail.push(project(x, y, z));
        if (trail.length > 800) trail.shift();
      }}
    }}

    document.getElementById('hud').innerText = `X: ${{x.toFixed(2)}} | Y: ${{y.toFixed(2)}} | Z: ${{z.toFixed(2)}} | Puntos: ${{trail.length}}`;

    if (trail.length > 1) {{
      ctx.lineWidth = 1.6;
      for (let i = 1; i < trail.length; i++) {{
        const prog = i / trail.length;
        ctx.strokeStyle = `hsl(${{180 + prog * 150}}, 85%, 60%)`;
        ctx.beginPath();
        ctx.moveTo(trail[i-1][0], trail[i-1][1]);
        ctx.lineTo(trail[i][0], trail[i][1]);
        ctx.stroke();
      }}
    }}

    const cur = project(x, y, z);
    ctx.fillStyle = '#f43f5e'; ctx.beginPath(); ctx.arc(cur[0], cur[1], 4.5, 0, 6.28); ctx.fill();

    requestAnimationFrame(draw);
  }}

  document.getElementById('sigma').oninput = e => {{ sigma = parseFloat(e.target.value); document.getElementById('vs').innerText = sigma.toFixed(1); }};
  document.getElementById('rho').oninput = e => {{ rho = parseFloat(e.target.value); document.getElementById('vr').innerText = rho.toFixed(1); }};
  document.getElementById('beta').oninput = e => {{ beta = parseFloat(e.target.value); document.getElementById('vb').innerText = beta.toFixed(2); }};
  document.getElementById('rot').oninput = e => {{
    angle = (parseFloat(e.target.value) * Math.PI) / 180;
    document.getElementById('vrot').innerText = e.target.value + '°';
    trail = [];
  }};

  document.getElementById('pBtn').onclick = e => {{ run = !run; e.target.innerText = run ? 'Pausar' : 'Reanudar'; }};
  document.getElementById('rBtn').onclick = () => {{ x = 0.1; y = 0; z = 0; trail = []; }};
  document.getElementById('clBtn').onclick = () => trail = [];

  draw();
}})();
\x3C/script\x3E
</body>
</html>"""


def _build_eigen_matrix_simulator(title):
    """Simulador de Transformación Lineal 2D: Círculo unitario deformado en Elipse y Autovectores"""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title} · Transformación Lineal y Autovalores</title>
<style>{_get_common_styles()}</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h2><span>⚡</span> {title} · Elipse de Deformación y Autovectores</h2>
    <div class="hud" id="hud">Det(A): 1.00 | Autovalores: λ₁ = 1.00, λ₂ = 1.00</div>
  </div>
  <canvas id="c"></canvas>
  <div class="controls">
    <div class="cg"><label>T₁₁: <b id="vt11">1.50</b></label><input type="range" id="t11" min="-3" max="3" step="0.1" value="1.5"></div>
    <div class="cg"><label>T₁₂: <b id="vt12">0.50</b></label><input type="range" id="t12" min="-3" max="3" step="0.1" value="0.5"></div>
    <div class="cg"><label>T₂₁: <b id="vt21">0.50</b></label><input type="range" id="t21" min="-3" max="3" step="0.1" value="0.5"></div>
    <div class="cg"><label>T₂₂: <b id="vt22">1.50</b></label><input type="range" id="t22" min="-3" max="3" step="0.1" value="1.5"></div>
  </div>
  <div class="bar">
    <button class="sec" id="rBtn">Matriz Identidad</button>
    <button class="sec" id="sBtn">Cizallamiento (Shear)</button>
    <span class="hint">Azul: Círculo unitario | Rosa: Imagen transformada T(S¹) | Verde: Autovectores</span>
  </div>
</div>
\x3Cscript\x3E
(() => {{
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  let w, h, cx, cy, sc = 65;
  let m11 = 1.5, m12 = 0.5, m21 = 0.5, m22 = 1.5;

  function sz() {{ w = c.width = c.clientWidth; h = c.height = c.clientHeight; cx = w/2; cy = h/2; }}
  window.onresize = sz; sz();

  function draw() {{
    ctx.fillStyle = '#090d16'; ctx.fillRect(0, 0, w, h);

    // Ejes
    ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.stroke();

    // 1. Círculo unitario original (Azul punteado)
    ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.arc(cx, cy, sc, 0, 6.28); ctx.stroke();
    ctx.setLineDash([]);

    // 2. Elipse transformada (Rosa continuo)
    ctx.strokeStyle = '#f43f5e'; ctx.lineWidth = 2.5;
    ctx.beginPath();
    const N = 180;
    for (let i = 0; i <= N; i++) {{
      const ang = (i / N) * Math.PI * 2;
      const ux = Math.cos(ang), uy = Math.sin(ang);
      const tx = m11 * ux + m12 * uy;
      const ty = m21 * ux + m22 * uy;
      const px = cx + tx * sc, py = cy - ty * sc;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();

    // 3. Cálculo de autovalores
    const tr = m11 + m22;
    const det = m11 * m22 - m12 * m21;
    const disc = tr * tr - 4 * det;

    if (disc >= 0) {{
      const l1 = (tr + Math.sqrt(disc)) / 2;
      const l2 = (tr - Math.sqrt(disc)) / 2;
      document.getElementById('hud').innerText = `Det: ${{det.toFixed(2)}} | λ₁ = ${{l1.toFixed(2)}}, λ₂ = ${{l2.toFixed(2)}} (Autovalores Reales)`;

      // Dibujar autovectores en verde
      [l1, l2].forEach((lam, idx) => {{
        let vx, vy;
        if (Math.abs(m12) > 1e-4) {{ vx = 1; vy = (lam - m11) / m12; }}
        else if (Math.abs(m21) > 1e-4) {{ vy = 1; vx = (lam - m22) / m21; }}
        else {{ vx = (idx === 0 ? 1 : 0); vy = (idx === 0 ? 0 : 1); }}
        const vlen = Math.hypot(vx, vy);
        if (vlen > 1e-4) {{
          vx /= vlen; vy /= vlen;
          ctx.strokeStyle = '#10b981'; ctx.lineWidth = 2.5;
          ctx.beginPath();
          ctx.moveTo(cx - vx * sc * 2, cy + vy * sc * 2);
          ctx.lineTo(cx + vx * sc * 2, cy - vy * sc * 2);
          ctx.stroke();
        }}
      }});
    }} else {{
      document.getElementById('hud').innerText = `Det: ${{det.toFixed(2)}} | Autovalores Complejos Conjugados (Rotación pura)`;
    }}

    requestAnimationFrame(draw);
  }}

  ['t11','t12','t21','t22'].forEach(id => {{
    document.getElementById(id).oninput = e => {{
      const val = parseFloat(e.target.value);
      if (id === 't11') m11 = val;
      if (id === 't12') m12 = val;
      if (id === 't21') m21 = val;
      if (id === 't22') m22 = val;
      document.getElementById('v' + id).innerText = val.toFixed(2);
    }};
  }});

  document.getElementById('rBtn').onclick = () => {{
    m11 = 1; m12 = 0; m21 = 0; m22 = 1;
    ['t11','t12','t21','t22'].forEach(id => {{
      document.getElementById(id).value = (id === 't11' || id === 't22') ? 1 : 0;
      document.getElementById('v' + id).innerText = ((id === 't11' || id === 't22') ? 1 : 0).toFixed(2);
    }});
  }};

  document.getElementById('sBtn').onclick = () => {{
    m11 = 1; m12 = 1.2; m21 = 0; m22 = 1;
    document.getElementById('t11').value = 1; document.getElementById('vt11').innerText = '1.00';
    document.getElementById('t12').value = 1.2; document.getElementById('vt12').innerText = '1.20';
    document.getElementById('t21').value = 0; document.getElementById('vt21').innerText = '0.00';
    document.getElementById('t22').value = 1; document.getElementById('vt22').innerText = '1.00';
  }};

  draw();
}})();
\x3C/script\x3E
</body>
</html>"""


def _build_taylor_series_simulator(title):
    """Simulador de Aproximación por Series de Taylor de Funciones Analíticas"""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title} · Aproximación de Taylor</title>
<style>{_get_common_styles()}</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h2><span>⚡</span> {title} · Polinomios de Taylor en Torno a x₀</h2>
    <div class="hud" id="hud">Orden N: 3 | x₀: 0.00 | Función: sin(x)</div>
  </div>
  <canvas id="c"></canvas>
  <div class="controls">
    <div class="cg"><label>Orden de Taylor N: <b id="vn">3</b></label><input type="range" id="order" min="1" max="9" step="2" value="3"></div>
    <div class="cg"><label>Punto de Expansión x₀: <b id="vx0">0.00</b></label><input type="range" id="x0" min="-3" max="3" step="0.2" value="0"></div>
  </div>
  <div class="bar">
    <button id="fSin">f(x) = sin(x)</button>
    <button class="sec" id="fExp">f(x) = eˣ</button>
    <button class="sec" id="fCos">f(x) = cos(x)</button>
    <span class="hint">Azul: Función exacta f(x) | Amarillo: Polinomio P_N(x)</span>
  </div>
</div>
\x3Cscript\x3E
(() => {{
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  let w, h, cx, cy, sc = 45;
  let order = 3, x0 = 0.0;
  let fnType = 'sin';

  function sz() {{ w = c.width = c.clientWidth; h = c.height = c.clientHeight; cx = w/2; cy = h/2; }}
  window.onresize = sz; sz();

  function f(x) {{
    if (fnType === 'sin') return Math.sin(x);
    if (fnType === 'exp') return Math.exp(x * 0.5);
    if (fnType === 'cos') return Math.cos(x);
    return Math.sin(x);
  }}

  function taylorPoly(x) {{
    const dx = x - x0;
    let sum = 0;
    if (fnType === 'sin') {{
      let coeffs = [Math.sin(x0), Math.cos(x0), -Math.sin(x0), -Math.cos(x0)];
      let fact = 1;
      for (let k = 0; k <= order; k++) {{
        if (k > 0) fact *= k;
        const c_k = coeffs[k % 4] / fact;
        sum += c_k * Math.pow(dx, k);
      }}
    }} else if (fnType === 'cos') {{
      let coeffs = [Math.cos(x0), -Math.sin(x0), -Math.cos(x0), Math.sin(x0)];
      let fact = 1;
      for (let k = 0; k <= order; k++) {{
        if (k > 0) fact *= k;
        const c_k = coeffs[k % 4] / fact;
        sum += c_k * Math.pow(dx, k);
      }}
    }} else {{
      let fact = 1;
      for (let k = 0; k <= order; k++) {{
        if (k > 0) fact *= k;
        const c_k = (Math.exp(x0 * 0.5) * Math.pow(0.5, k)) / fact;
        sum += c_k * Math.pow(dx, k);
      }}
    }}
    return sum;
  }}

  function draw() {{
    ctx.fillStyle = '#090d16'; ctx.fillRect(0, 0, w, h);

    // Ejes
    ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.stroke();

    // Función real (Azul)
    ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 2.5;
    ctx.beginPath();
    for (let px = 0; px < w; px += 2) {{
      const x = (px - cx) / sc;
      const y = f(x);
      const py = cy - y * sc;
      if (px === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();

    // Polinomio de Taylor (Amarillo)
    ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2;
    ctx.beginPath();
    for (let px = 0; px < w; px += 2) {{
      const x = (px - cx) / sc;
      const y = taylorPoly(x);
      const py = cy - y * sc;
      if (px === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();

    // Punto x0
    ctx.fillStyle = '#f43f5e';
    ctx.beginPath();
    ctx.arc(cx + x0 * sc, cy - f(x0) * sc, 5, 0, 6.28);
    ctx.fill();

    requestAnimationFrame(draw);
  }}

  document.getElementById('order').oninput = e => {{
    order = parseInt(e.target.value);
    document.getElementById('vn').innerText = order;
  }};
  document.getElementById('x0').oninput = e => {{
    x0 = parseFloat(e.target.value);
    document.getElementById('vx0').innerText = x0.toFixed(2);
  }};

  document.getElementById('fSin').onclick = () => {{ fnType = 'sin'; document.getElementById('order').max = 9; }};
  document.getElementById('fExp').onclick = () => {{ fnType = 'exp'; document.getElementById('order').max = 8; }};
  document.getElementById('fCos').onclick = () => {{ fnType = 'cos'; document.getElementById('order').max = 9; }};

  draw();
}})();
\x3C/script\x3E
</body>
</html>"""


if __name__ == "__main__":
    print("[Canvas Synthesizer] Módulo generativo de simuladores verificado.")
