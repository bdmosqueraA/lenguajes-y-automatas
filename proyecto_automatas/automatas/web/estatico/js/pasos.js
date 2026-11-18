// Visor del paso a paso de una operación.
import { claveArista } from './grafo.js';
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export class VisorPasos {
  constructor(tarjeta, diagrama, { alUsarResultado, alCerrar, alAvisar }) {
    this.tarjeta = tarjeta;
    this.diagrama = diagrama;
    this.alUsarResultado = alUsarResultado;
    this.alCerrar = alCerrar;
    this.alAvisar = alAvisar;
    this.operacion = null;
    this.indice = 0;
    this.timer = null;
    tarjeta.innerHTML = `
      <header class="cab"><h2 id="pv-titulo"></h2><button class="texto" id="pv-cerrar">Cerrar</button></header>
      <div class="nav-pasos">
        <button class="icono" id="pv-inicio" title="Primer paso">⏮</button>
        <button class="icono" id="pv-atras" title="Paso anterior">◀</button>
        <button class="icono principal" id="pv-play" title="Reproducir">▶</button>
        <button class="icono" id="pv-sig" title="Paso siguiente">▶</button>
        <button class="icono" id="pv-fin" title="Último paso">⏭</button>
        <span class="contador" id="pv-contador"></span>
      </div>
      <div class="puntos" id="pv-puntos"></div>
      <div class="paso" id="pv-paso"></div>
      <div class="resultado" id="pv-resultado"></div>`;
    const q = (id) => tarjeta.querySelector(id);
    this.titulo = q('#pv-titulo'); this.contador = q('#pv-contador'); this.puntos = q('#pv-puntos');
    this.cuerpo = q('#pv-paso'); this.pie = q('#pv-resultado'); this.botonPlay = q('#pv-play');
    q('#pv-cerrar').addEventListener('click', () => this.cerrar(true));
    q('#pv-inicio').addEventListener('click', () => this.irA(0, true));
    q('#pv-atras').addEventListener('click', () => this.irA(this.indice - 1, true));
    q('#pv-sig').addEventListener('click', () => this.irA(this.indice + 1, true));
    q('#pv-fin').addEventListener('click', () => this.irA(this.operacion.pasos.length - 1, true));
    this.botonPlay.addEventListener('click', () => this.alternar());
    this.puntos.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) this.irA(Number(b.dataset.i), true); });
  }

  mostrar(operacion) {
    this.parar();
    this.operacion = operacion;
    this.uniones = {};
    for (const p of operacion.pasos) {
      if (!p.grafo) continue;
      const u = this.uniones[p.grafo.clave] || (this.uniones[p.grafo.clave] = { nodos: new Map(), aristas: new Map() });
      for (const n of p.grafo.nodos) u.nodos.set(n.id, { id: n.id, inicial: n.inicial, final: n.final });   // gana la última
      for (const a of p.grafo.aristas) u.aristas.set(claveArista(a.origen, a.destino), { origen: a.origen, destino: a.destino });
    }
    for (const k of Object.keys(this.uniones)) {
      this.uniones[k] = { nodos: [...this.uniones[k].nodos.values()], aristas: [...this.uniones[k].aristas.values()] };
    }
    this.titulo.textContent = operacion.titulo;
    this.puntos.innerHTML = operacion.pasos.map((_, i) => `<button class="punto" data-i="${i}" title="Paso ${i + 1}"></button>`).join('');
    this.tarjeta.hidden = false;
    this.irA(0, false);
    this.tarjeta.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  cerrar(avisar) {
    this.parar();
    this.tarjeta.hidden = true;
    this.operacion = null;
    if (avisar) this.alCerrar();
  }

  irA(i, manual) {
    if (!this.operacion) return;
    if (manual) this.parar();
    const total = this.operacion.pasos.length;
    this.indice = Math.min(Math.max(i, 0), total - 1);
    const paso = this.operacion.pasos[this.indice];
    this.contador.textContent = `Paso ${this.indice + 1} de ${total}`;
    this.puntos.querySelectorAll('.punto').forEach((p, k) => {
      p.classList.toggle('actual', k === this.indice); p.classList.toggle('hecho', k < this.indice);
    });
    this.cuerpo.innerHTML = `<h3>${esc(paso.titulo)}</h3>`
      + paso.texto.split('\n').map((l) => `<p>${esc(l)}</p>`).join('')
      + paso.tablas.map((t) => this._tabla(t)).join('');
    if (paso.grafo) {
      this.diagrama.mostrar(paso.grafo, { union: this.uniones[paso.grafo.clave] });
    }
    this.pie.innerHTML = '';
    if (this.indice === total - 1) this._resultado();
  }

  _tabla(t) {
    const marcadas = new Set(t.filas_resaltadas || []);
    return `<div class="tabla-paso"><div class="cap">${esc(t.titulo)}</div><table><thead><tr>${t.columnas.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>`
      + t.filas.map((f, i) => `<tr class="${marcadas.has(i) ? 'res' : ''}">${f.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')
      + '</tbody></table></div>';
  }

  _resultado() {
    const r = this.operacion.resultado;
    if (r.tipo === 'automata') {
      const a = r.automata;
      this.pie.innerHTML = `<span class="insignia ok">${esc(a.tipo)} · ${a.estados.length} estados</span>`
        + '<button class="primario" id="pv-usar">Usar este autómata</button>'
        + '<span class="ayuda" style="margin:0">Lo carga en la definición para seguir operando con él.</span>';
      this.pie.querySelector('#pv-usar').addEventListener('click', () => this.alUsarResultado(a));
    } else {
      this.pie.innerHTML = `<div class="caja-er" id="pv-er">${esc(r.texto)}</div>`
        + '<button class="secundario" id="pv-copiar">Copiar</button>'
        + '<button class="primario" id="pv-usar-er">Usar como expresión regular</button>';
      this.pie.querySelector('#pv-copiar').addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(r.texto); this.alAvisar('Expresión copiada.'); } catch (e) { this.alAvisar('No se pudo copiar.', 'error'); }
      });
      this.pie.querySelector('#pv-usar-er').addEventListener('click', () => this.alUsarResultado({ er: r.texto }));
    }
  }

  alternar() {
    if (!this.operacion) return;
    if (this.timer) { this.parar(); return; }
    if (this.indice >= this.operacion.pasos.length - 1) this.irA(0, false);
    this.botonPlay.textContent = '⏸';
    this.timer = setInterval(() => {
      if (this.indice >= this.operacion.pasos.length - 1) { this.parar(); return; }
      this.irA(this.indice + 1, false);
      if (this.indice >= this.operacion.pasos.length - 1) this.parar();
    }, 2000);
  }

  parar() {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    if (this.botonPlay) this.botonPlay.textContent = '▶';
  }
}
