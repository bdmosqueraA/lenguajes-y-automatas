// Dibujo de diagramas de estados (SVG) con distribución automática y arrastre de nodos.
export const RADIO_MIN = 26;
export const claveArista = (o, d) => `${o}\u0001${d}`;
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fuente = (n) => (n.length <= 4 ? 15 : n.length <= 8 ? 13 : 11);
export const radio = (n) => Math.max(RADIO_MIN, 0.31 * fuente(n) * n.length + 12);
export const radioNodo = (n) => Math.max(radio(n.id), n.subtitulo !== undefined && n.subtitulo !== null ? 34 : 0);
const f1 = (x) => x.toFixed(1);

const VARIABLES = ['--fondo', '--punto', '--nodo', '--borde-n', '--texto-n', '--arista', '--etq-fondo', '--etq-txt',
  '--acento-n', '--acento-n-txt', '--c0', '--c1', '--c2', '--c3', '--c4', '--c5', '--c6', '--c7'];

export const REGLAS_SVG = `
.auto-svg .n-g{cursor:grab}
.auto-svg .n-c{fill:var(--nodo);stroke:var(--borde-n);stroke-width:2;transition:fill .25s,stroke .25s}
.auto-svg .n-fin{fill:none;stroke:var(--borde-n);stroke-width:2}
.auto-svg .n-t{fill:var(--texto-n);font-family:Inter,'Segoe UI',system-ui,sans-serif;font-weight:600;text-anchor:middle;dominant-baseline:central;pointer-events:none;user-select:none}
.auto-svg .n-act .n-c{fill:var(--acento-n);stroke:var(--acento-n)}
.auto-svg .n-act .n-fin{stroke:var(--acento-n-txt)}
.auto-svg .n-act .n-t{fill:var(--acento-n-txt)}
.auto-svg .n-sub{fill:var(--acento-n);font-family:Inter,'Segoe UI',system-ui,sans-serif;font-weight:700;font-size:12.5px;text-anchor:middle;dominant-baseline:central;pointer-events:none;user-select:none}
.auto-svg .n-act .n-sub{fill:var(--acento-n-txt)}
.auto-svg .n-act{filter:drop-shadow(0 0 7px var(--acento-n))}
${[0, 1, 2, 3, 4, 5, 6, 7].map((i) => `.auto-svg .n-col${i} .n-c{fill:var(--c${i})}`).join('\n')}
.auto-svg .e-l{fill:none;stroke:var(--arista);stroke-width:1.8;transition:stroke .25s}
.auto-svg .e-act .e-l{stroke:var(--acento-n);stroke-width:3.2}
.auto-svg .e-bg{fill:var(--etq-fondo)}
.auto-svg .e-t{fill:var(--etq-txt);font-family:Inter,'Segoe UI',system-ui,sans-serif;font-weight:500;font-size:13px;text-anchor:middle;dominant-baseline:central;pointer-events:none;user-select:none}
.auto-svg .e-act .e-t{fill:var(--acento-n);font-weight:700}
.auto-svg .fl{fill:var(--arista)}
.auto-svg .fl-act{fill:var(--acento-n)}
`;

if (typeof document !== 'undefined' && !document.getElementById('reglas-svg')) {
  const estilo = document.createElement('style');
  estilo.id = 'reglas-svg';
  estilo.textContent = REGLAS_SVG;
  document.head.appendChild(estilo);
}

// ------------------------------------------------------------------ //
// Del JSON de un autómata al grafo que se dibuja
// ------------------------------------------------------------------ //
export function grafoDesdeAutomata(a, clave = 'actual') {
  const nodos = a.estados.map((q) => ({ id: q, inicial: q === a.inicial, final: a.finales.includes(q) }));
  const mapa = new Map();
  for (const t of a.transiciones) {
    const k = claveArista(t.origen, t.destino);
    if (!mapa.has(k)) mapa.set(k, { origen: t.origen, destino: t.destino, simbolos: [] });
    mapa.get(k).simbolos.push(t.simbolo);
  }
  const orden = (x, y) => ((x === 'λ') - (y === 'λ')) || (x < y ? -1 : x > y ? 1 : 0);
  const aristas = [...mapa.values()].map((e) => ({
    origen: e.origen, destino: e.destino, etiqueta: e.simbolos.sort(orden).join(', '),
  }));
  return { clave, nodos, aristas, leyenda: [] };
}

// Moore: la salida va dentro del nodo ("/a"). Mealy: la flecha lleva "entrada/salida".
export function grafoDesdeTraductor(m, clave = 'actual') {
  const moore = m.tipo === 'moore';
  const nodos = m.estados.map((q) => {
    const n = { id: q, inicial: q === m.inicial, final: false };
    if (moore) n.subtitulo = `/${(m.salidas_estados && m.salidas_estados[q]) || 'λ'}`;
    return n;
  });
  const mapa = new Map();
  for (const t of m.transiciones) {
    const k = claveArista(t.origen, t.destino);
    if (!mapa.has(k)) mapa.set(k, { origen: t.origen, destino: t.destino, partes: [] });
    mapa.get(k).partes.push(moore ? t.simbolo : `${t.simbolo}/${t.salida || 'λ'}`);
  }
  const aristas = [...mapa.values()].map((e) => ({ origen: e.origen, destino: e.destino, etiqueta: e.partes.join(', ') }));
  return { clave, nodos, aristas, leyenda: [] };
}

// ------------------------------------------------------------------ //
// Distribución: una columna por distancia al estado inicial
// ------------------------------------------------------------------ //
function ordenar(capa, referencia, vecinos) {
  const punt = capa.map((n, i) => {
    const idx = (vecinos[n] || []).filter((v) => v in referencia && v !== n).map((v) => referencia[v]);
    return { n, i, p: idx.length ? idx.reduce((a, b) => a + b, 0) / idx.length : null };
  });
  const con = punt.filter((x) => x.p !== null).sort((a, b) => a.p - b.p || a.i - b.i);
  const res = con.map((x) => x.n);
  for (const x of punt.filter((y) => y.p === null)) res.splice(Math.min(x.i, res.length), 0, x.n);
  return res;
}

export function distribuir(nodos, aristas) {
  const ids = nodos.map((n) => n.id);
  if (!ids.length) return { pos: {}, ancho: 640, alto: 340 };
  const suc = {}; const pre = {};
  ids.forEach((i) => { suc[i] = []; pre[i] = []; });
  for (const a of aristas) {
    if (!suc[a.origen] || !pre[a.destino]) continue;
    if (!suc[a.origen].includes(a.destino)) { suc[a.origen].push(a.destino); pre[a.destino].push(a.origen); }
  }
  let iniciales = nodos.filter((n) => n.inicial).map((n) => n.id);
  if (!iniciales.length) iniciales = [ids[0]];
  const capaDe = {};
  iniciales.forEach((i) => { capaDe[i] = 0; });
  const cola = [...iniciales];
  const capas = [];
  while (cola.length) {
    const u = cola.shift();
    while (capas.length <= capaDe[u]) capas.push([]);
    capas[capaDe[u]].push(u);
    for (const v of suc[u]) if (!(v in capaDe)) { capaDe[v] = capaDe[u] + 1; cola.push(v); }
  }
  for (const id of ids) if (!(id in capaDe)) { capaDe[id] = 0; capas[0].push(id); }   // inalcanzables: 1.ª columna

  for (let vuelta = 0; vuelta < 2; vuelta++) {
    for (let i = 1; i < capas.length; i++) {
      const ref = {}; capas[i - 1].forEach((n, k) => { ref[n] = k; });
      capas[i] = ordenar(capas[i], ref, pre);
    }
    for (let i = capas.length - 2; i >= 0; i--) {
      const ref = {}; capas[i + 1].forEach((n, k) => { ref[n] = k; });
      let nueva = ordenar(capas[i], ref, suc);
      if (i === 0) {
        const fijos = capas[0].filter((n) => iniciales.includes(n));
        nueva = fijos.concat(nueva.filter((n) => !fijos.includes(n)));
      }
      capas[i] = nueva;
    }
  }

  const margenIzq = 130; const margenDer = 90; const pasoX = 160; const pasoY = 120;
  const maxCapa = Math.max(...capas.map((c) => c.length));
  const ancho = Math.max(640, margenIzq + margenDer + (capas.length - 1) * pasoX);
  const alto = Math.max(340, 230 + (maxCapa - 1) * pasoY);
  const x0 = margenIzq + (ancho - margenIzq - margenDer - (capas.length - 1) * pasoX) / 2;
  const pos = {};
  capas.forEach((capa, i) => {
    const y0 = alto / 2 - ((capa.length - 1) * pasoY) / 2;
    capa.forEach((n, j) => { pos[n] = [x0 + i * pasoX, y0 + j * pasoY]; });
  });
  return { pos, ancho, alto };
}

// ------------------------------------------------------------------ //
// Geometría de las flechas
// ------------------------------------------------------------------ //
function unitario(dx, dy) { const l = Math.hypot(dx, dy) || 1; return [dx / l, dy / l]; }

function flecha(pos, a, hayInversa, radios) {
  const [ox, oy] = pos[a.origen]; const [px, py] = pos[a.destino];
  const ro = radios[a.origen]; const rd = radios[a.destino];
  if (a.origen === a.destino) {                                           // bucle sobre el nodo
    const ini = [ox - ro * 0.55, oy - ro * 0.835]; const fin = [ox + ro * 0.55 + 1.5, oy - ro * 0.835 - 1.5];
    const c1 = [ox - ro * 1.15, oy - ro * 2.75]; const c2 = [ox + ro * 1.15, oy - ro * 2.75];
    return { d: `M${f1(ini[0])},${f1(ini[1])} C${f1(c1[0])},${f1(c1[1])} ${f1(c2[0])},${f1(c2[1])} ${f1(fin[0])},${f1(fin[1])}`,
      lx: ox, ly: oy - ro * 2.23 - 11 };
  }
  const [ux, uy] = unitario(px - ox, py - oy);
  const nx = -uy; const ny = ux;
  const largo = Math.hypot(px - ox, py - oy);
  let arco = 0;
  if (hayInversa) arco = Math.min(Math.max(0.17 * largo, 24), 56);
  else if (px < ox - 1 || Math.abs(px - ox) < 1) arco = Math.min(Math.max(0.22 * largo, 20), 70);
  const mx = (ox + px) / 2; const my = (oy + py) / 2;
  const cx = mx + nx * arco * 2; const cy = my + ny * arco * 2;
  const ui = unitario(cx - ox, cy - oy); const uf = unitario(cx - px, cy - py);
  const sx = ox + ui[0] * ro; const sy = oy + ui[1] * ro;
  const ex = px + uf[0] * (rd + 2.5); const ey = py + uf[1] * (rd + 2.5);
  let lx; let ly;
  if (arco) { lx = mx + nx * (arco + 12); ly = my + ny * (arco + 12); }
  else { const lado = ny > 0 ? -1 : 1; lx = mx + nx * 14 * lado; ly = my + ny * 14 * lado; }
  return { d: `M${f1(sx)},${f1(sy)} Q${f1(cx)},${f1(cy)} ${f1(ex)},${f1(ey)}`, lx, ly };
}

// ------------------------------------------------------------------ //
// Componente
// ------------------------------------------------------------------ //
export class Diagrama {
  constructor(contenedor) {
    this.cont = contenedor;
    this.layouts = {};       // clave -> { pos, ancho, alto }
    this.uniones = {};       // clave -> { nodos, aristas } con los que se calculó la distribución
    this.grafo = null;
    this.activos = new Set();
    this.recorridas = new Set();
    this.arrastrando = null;
    this.ajustar = false;
    this.cont.innerHTML = '<div class="vacio">Crea un autómata para verlo aquí.</div>';
  }

  reiniciarLayouts(conservar = []) {
    for (const k of Object.keys(this.layouts)) {
      if (!conservar.includes(k)) { delete this.layouts[k]; delete this.uniones[k]; }
    }
  }

  limpiar(mensaje = 'Crea un autómata para verlo aquí.') {
    this.grafo = null;
    this.cont.innerHTML = `<div class="vacio">${esc(mensaje)}</div>`;
  }

  mostrar(grafo, { union = null, activos = [], recorridas = [] } = {}) {
    const clave = grafo.clave || 'actual';
    this.grafo = grafo;
    this.radios = Object.fromEntries(grafo.nodos.map((n) => [n.id, radioNodo(n)]));
    this.activos = new Set(activos);
    this.recorridas = new Set(recorridas);
    if (!this.layouts[clave]) {
      const base = union || grafo;
      this.uniones[clave] = base;
      this.layouts[clave] = distribuir(base.nodos, base.aristas);
    }
    const lay = this.layouts[clave];
    let k = 0;
    for (const n of grafo.nodos) {                    // nodos que no estaban en la distribución
      if (!lay.pos[n.id]) { lay.pos[n.id] = [lay.ancho / 2 + 40 * k, lay.alto / 2 + 40 * k]; k++; }
    }
    this._montar();
    this._dibujar();
  }

  alternarAjuste() {
    this.ajustar = !this.ajustar;
    if (this.grafo) this._dibujar();
    return this.ajustar;
  }

  reorganizar() {
    if (!this.grafo) return;
    const clave = this.grafo.clave || 'actual';
    const base = this.uniones[clave] || this.grafo;
    this.layouts[clave] = distribuir(base.nodos, base.aristas);
    this._dibujar();
  }

  _montar() {
    if (this.svg && this.cont.contains(this.svg)) return;
    this.cont.innerHTML = '<div class="lienzo"><svg class="diagrama-svg" xmlns="http://www.w3.org/2000/svg"></svg></div><div class="leyenda"></div>';
    this.svg = this.cont.querySelector('svg');
    this.leyenda = this.cont.querySelector('.leyenda');
    this.svg.addEventListener('pointerdown', (e) => this._alPresionar(e));
    this.svg.addEventListener('pointermove', (e) => this._alMover(e));
    const soltar = (e) => this._alSoltar(e);
    this.svg.addEventListener('pointerup', soltar);
    this.svg.addEventListener('pointercancel', soltar);
  }

  _lay() { return this.layouts[this.grafo.clave || 'actual']; }

  _punto(e) {
    const p = this.svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY;
    return p.matrixTransform(this.svg.getScreenCTM().inverse());
  }

  _alPresionar(e) {
    const g = e.target.closest ? e.target.closest('.n-g') : null;
    if (!g || !this.grafo) return;
    const id = g.dataset.id; const p = this._punto(e); const [x, y] = this._lay().pos[id];
    this.arrastrando = { id, dx: p.x - x, dy: p.y - y };
    this.svg.setPointerCapture(e.pointerId);
    this.svg.classList.add('arrastrando');
    e.preventDefault();
  }

  _alMover(e) {
    if (!this.arrastrando) return;
    const lay = this._lay(); const { id, dx, dy } = this.arrastrando; const p = this._punto(e); const r = this.radios[id] ?? radio(id);
    lay.pos[id] = [Math.min(Math.max(p.x - dx, r + 8), lay.ancho - r - 8), Math.min(Math.max(p.y - dy, r + 8), lay.alto - r - 8)];
    this._dibujar();
  }

  _alSoltar() {
    this.arrastrando = null;
    if (this.svg) this.svg.classList.remove('arrastrando');
  }

  _dibujar() {
    const g = this.grafo; const lay = this._lay(); const pos = lay.pos;
    this.svg.setAttribute('viewBox', `0 0 ${lay.ancho} ${lay.alto}`);
    const disponible = this.cont.clientWidth || 800;            // los grafos grandes no se encogen más del 80 %: se desplazan
    this.svg.style.width = `${this.ajustar ? disponible : Math.max(disponible, lay.ancho * 0.8)}px`;
    const existentes = new Set(g.aristas.map((a) => claveArista(a.origen, a.destino)));
    const p = [
      `<defs><marker id="afl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto"><path class="fl" d="M0,0.8 L10,5 L0,9.2 z"/></marker>`,
      `<marker id="afl-act" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="13" markerHeight="13" markerUnits="userSpaceOnUse" orient="auto"><path class="fl-act" d="M0,0.8 L10,5 L0,9.2 z"/></marker>`,
      `<pattern id="apuntos" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.2" style="fill:var(--punto)"/></pattern></defs>`,
      `<rect width="${lay.ancho}" height="${lay.alto}" style="fill:var(--fondo)"/>`,
      `<rect width="${lay.ancho}" height="${lay.alto}" fill="url(#apuntos)"/>`,
    ];
    for (const a of g.aristas) {
      if (!pos[a.origen] || !pos[a.destino]) continue;
      const inversa = a.origen !== a.destino && existentes.has(claveArista(a.destino, a.origen));
      const { d, lx, ly } = flecha(pos, a, inversa, this.radios);
      const activa = a.resaltada || this.recorridas.has(claveArista(a.origen, a.destino));
      const w = 7.6 * String(a.etiqueta).length + 14;
      p.push(`<g class="e-g${activa ? ' e-act' : ''}"><path class="e-l" d="${d}" marker-end="url(#${activa ? 'afl-act' : 'afl'})"/>`
        + `<rect class="e-bg" x="${f1(lx - w / 2)}" y="${f1(ly - 10)}" width="${f1(w)}" height="20" rx="6"/>`
        + `<text class="e-t" x="${f1(lx)}" y="${f1(ly)}">${esc(a.etiqueta)}</text></g>`);
    }
    for (const n of g.nodos) {
      if (!pos[n.id]) continue;
      const [x, y] = pos[n.id]; const r = this.radios[n.id];
      if (n.inicial) p.push(`<path class="e-l" d="M${f1(x - r - 50)},${f1(y)} L${f1(x - r - 2)},${f1(y)}" marker-end="url(#afl)"/>`);
      const act = n.resaltado || this.activos.has(n.id);
      const color = n.color !== null && n.color !== undefined ? ` n-col${n.color % 8}` : '';
      p.push(`<g class="n-g${act ? ' n-act' : ''}${color}" data-id="${esc(n.id)}"><circle class="n-c" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}"/>`
        + (n.final ? `<circle class="n-fin" cx="${f1(x)}" cy="${f1(y)}" r="${f1(r - 5)}"/>` : '')
        + (n.subtitulo !== undefined && n.subtitulo !== null
          ? `<text class="n-t" x="${f1(x)}" y="${f1(y - 7)}" style="font-size:${Math.min(fuente(n.id), 14)}px">${esc(n.id)}</text>`
            + `<text class="n-sub" x="${f1(x)}" y="${f1(y + 11)}">${esc(n.subtitulo)}</text></g>`
          : `<text class="n-t" x="${f1(x)}" y="${f1(y)}" style="font-size:${fuente(n.id)}px">${esc(n.id)}</text></g>`));
    }
    this.svg.innerHTML = `<g class="auto-svg">${p.join('')}</g>`;
    this.leyenda.innerHTML = (g.leyenda || []).map((l) => `<span><i style="background:var(--c${l.color % 8})"></i>${esc(l.texto)}</span>`).join('');
  }

  exportarSVG() {
    if (!this.grafo || !this.svg) return null;
    const lay = this._lay();
    const cs = getComputedStyle(document.documentElement);
    const vars = VARIABLES.map((n) => `${n}:${cs.getPropertyValue(n).trim()}`).join(';');
    const copia = this.svg.cloneNode(true);
    copia.setAttribute('width', lay.ancho); copia.setAttribute('height', lay.alto);
    const estilo = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    estilo.textContent = `.auto-svg{${vars}}${REGLAS_SVG}`;
    copia.insertBefore(estilo, copia.firstChild);
    return new XMLSerializer().serializeToString(copia);
  }
}
