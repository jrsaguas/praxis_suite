# Cinemática en SE(3)

## 1. Estrategia
Formulación en álgebra de Lie.

$$
X' = A X
$$


---

## Anexo: Código Fuente del Visualizador Matemático Interactivo (Canvas HTML5)

El siguiente código genera el simulador interactivo autónomo con deslizadores paramétricos:

```html
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cinemática en SE(3) · Laboratorio Interactivo Praxis</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0f172a; --card: #1e293b; --ink: #f8fafc; --muted: #94a3b8;
  --brand: #38bdf8; --accent: #f43f5e; --line: #334155; --canvas-bg: #090d16;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: 'IBM Plex Sans', sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; }
.container { width: 100%; max-width: 900px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
.header { padding: 18px 24px; border-bottom: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; }
.header h1 { margin: 0; font-size: 19px; font-weight: 700; color: var(--brand); }
.header .badge { font-size: 11px; font-weight: 600; background: rgba(56,189,248,0.15); color: var(--brand); padding: 4px 10px; border-radius: 20px; text-transform: uppercase; }
.canvas-wrap { position: relative; width: 100%; height: 500px; background: var(--canvas-bg); }
canvas { width: 100%; height: 100%; display: block; }
.controls { padding: 20px 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; background: rgba(15,23,42,0.6); border-top: 1px solid var(--line); }
.control-group { display: flex; flex-direction: column; gap: 6px; }
.control-group label { font-size: 12px; color: var(--muted); display: flex; justify-content: space-between; }
.control-group input[type=range] { width: 100%; accent-color: var(--brand); cursor: pointer; }
.actions { padding: 14px 24px; display: flex; gap: 10px; align-items: center; border-top: 1px solid var(--line); background: var(--card); }
.btn { background: var(--brand); color: #090d16; font-weight: 700; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: opacity .2s; }
.btn:hover { opacity: 0.9; }
.btn.sec { background: #334155; color: var(--ink); }
.formula-tag { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--brand); margin-left: auto; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Cinemática en SE(3)</h1>
    <span class="badge">Simulador Interactivo HTML5 Canvas</span>
  </div>
  <div class="canvas-wrap">
    <canvas id="simCanvas"></canvas>
  </div>
  <div class="controls">
    
        <div class="control-group">
          <label for="x0">Condición inicial x(0): <b id="val_x0">1.0</b></label>
          <input type="range" id="x0" min="-3.0" max="3.0" step="0.1" value="1.0">
        </div>
        <div class="control-group">
          <label for="y0">Condición inicial y(0): <b id="val_y0">0.0</b></label>
          <input type="range" id="y0" min="-3.0" max="3.0" step="0.1" value="0.0">
        </div>
        <div class="control-group">
          <label for="omega">Frecuencia angular ω: <b id="val_omega">1.0</b></label>
          <input type="range" id="omega" min="0.1" max="4.0" step="0.1" value="1.0">
        </div>
        <div class="control-group">
          <label for="gamma">Amortiguamiento γ: <b id="val_gamma">0.0</b></label>
          <input type="range" id="gamma" min="-1.0" max="1.0" step="0.05" value="0.0">
        </div>
  </div>
  <div class="actions">
    <button class="btn" id="playBtn">⏸ Pausar</button>
    <button class="btn sec" id="resetBtn">↺ Reiniciar Órbita</button>
    <button class="btn sec" id="clearBtn">Limpiar Rastro</button>
    <span class="formula-tag">dx/dt = y, dy/dt = -ω²x - γy</span>
  </div>
</div>

<script>
(() => {
  const canvas = document.getElementById('simCanvas');
  const ctx = canvas.getContext('2d');
  let width, height, cx, cy;
  const scale = 70; // px por unidad matemática

  let x0 = 1.0;
let y0 = 0.0;
let omega = 1.0;
let gamma = 0.0;

  let x = x0, y = y0;
  let running = true;
  let trail = [];
  const maxTrail = 800;

  function resize() {
    width = canvas.width = canvas.parentElement.clientWidth;
    height = canvas.height = canvas.parentElement.clientHeight;
    cx = width / 2;
    cy = height / 2;
  }
  window.addEventListener('resize', resize);
  resize();

  function toScreen(gx, gy) {
    return [cx + gx * scale, cy - gy * scale];
  }

  function drawGrid() {
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let gx = -10; gx <= 10; gx++) {
      const [sx] = toScreen(gx, 0);
      ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx, height); ctx.stroke();
    }
    for (let gy = -10; gy <= 10; gy++) {
      const [, sy] = toScreen(0, gy);
      ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(width, sy); ctx.stroke();
    }
    // Ejes
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(width, cy); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, height); ctx.stroke();
  }

  function drawVectorField() {
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.15)';
    ctx.fillStyle = 'rgba(56, 189, 248, 0.3)';
    ctx.lineWidth = 1;
    const step = 0.5;
    for (let gx = -4; gx <= 4; gx += step) {
      for (let gy = -4; gy <= 4; gy += step) {
        const vx = gy;
        const vy = - (omega * omega) * gx - gamma * gy;
        const norm = Math.hypot(vx, vy);
        if (norm < 0.001) continue;
        const len = 14;
        const [sx, sy] = toScreen(gx, gy);
        const ex = sx + (vx / norm) * len;
        const ey = sy - (vy / norm) * len;
        ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
      }
    }
  }

  function stepRK4(dt) {
    function f(px, py) {
      return [py, - (omega * omega) * px - gamma * py];
    }
    const [k1x, k1y] = f(x, y);
    const [k2x, k2y] = f(x + 0.5 * dt * k1x, y + 0.5 * dt * k1y);
    const [k3x, k3y] = f(x + 0.5 * dt * k2x, y + 0.5 * dt * k2y);
    const [k4x, k4y] = f(x + dt * k3x, y + dt * k3y);

    x += (dt / 6) * (k1x + 2 * k2x + 2 * k3x + k4x);
    y += (dt / 6) * (k1y + 2 * k2y + 2 * k3y + k4y);
  }

  function resetSimulation() {
    x = x0; y = y0;
    trail = [];
  }

  function render() {
    ctx.fillStyle = '#090d16';
    ctx.fillRect(0, 0, width, height);
    drawGrid();
    drawVectorField();

    if (running) {
      for (let i = 0; i < 4; i++) {
        stepRK4(0.015);
        trail.push(toScreen(x, y));
        if (trail.length > maxTrail) trail.shift();
      }
    }

    // Dibujar trayectoria
    if (trail.length > 1) {
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(trail[0][0], trail[0][1]);
      for (let i = 1; i < trail.length; i++) {
        ctx.lineTo(trail[i][0], trail[i][1]);
      }
      ctx.stroke();
    }

    // Punto actual
    const [currX, currY] = toScreen(x, y);
    ctx.fillStyle = '#f43f5e';
    ctx.beginPath(); ctx.arc(currX, currY, 6, 0, 2 * Math.PI); ctx.fill();
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2; ctx.stroke();

    requestAnimationFrame(render);
  }

  
  document.getElementById('x0').addEventListener('input', (e) => {
    x0 = parseFloat(e.target.value);
    document.getElementById('val_x0').innerText = x0.toFixed(2);
    resetSimulation();
  });

  document.getElementById('y0').addEventListener('input', (e) => {
    y0 = parseFloat(e.target.value);
    document.getElementById('val_y0').innerText = y0.toFixed(2);
    resetSimulation();
  });

  document.getElementById('omega').addEventListener('input', (e) => {
    omega = parseFloat(e.target.value);
    document.getElementById('val_omega').innerText = omega.toFixed(2);
    resetSimulation();
  });

  document.getElementById('gamma').addEventListener('input', (e) => {
    gamma = parseFloat(e.target.value);
    document.getElementById('val_gamma').innerText = gamma.toFixed(2);
    resetSimulation();
  });


  document.getElementById('playBtn').addEventListener('click', (e) => {
    running = !running;
    e.target.innerText = running ? '⏸ Pausar' : '▶ Reanudar';
  });
  document.getElementById('resetBtn').addEventListener('click', resetSimulation);
  document.getElementById('clearBtn').addEventListener('click', () => { trail = []; });

  render();
})();
</script>
</body>
</html>
```
