// Prueba de cadenas con traza y reproductor.
import { claveArista, grafoDesdeAutomata } from './grafo.js';
import { llamar } from './api.js';
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export class Simulador {
  constructor(tarjeta, diagrama, { obtenerAutomata, alCerrar, alAvisar }) {
    this.tarjeta = tarjeta; this.diagrama = diagrama; this.obtenerAutomata = obtenerAutomata;
    this.alCerrar = alCerrar; this.alAvisar = alAvisar;
    this.traza = null; this.indice = 0; this.timer = null;
    tarjeta.innerHTML = `
      <header class="cab"><h2>Probar cadenas</h2><button class="texto" id="sm-cerrar">Cerrar</button></header>
      <div class="fila-entrada"><input id="sm-cadena" placeholder="escribe una cadena (vacía = λ)" spellcheck="false" autocomplete="off"><button class="primario" id="sm-ejecutar">Ejecutar</button></div>
      <div class="cinta" id="sm-cinta"></div>
      <div id="sm-veredicto"></div>
      <div class="nav-pasos">
        <button class="icono" id="sm-inicio" title="Inicio">⏮</button><button class="icono" id="sm-atras" title="Atrás">◀</button>
        <button class="icono principal" id="sm-play" title="Reproducir">▶</button>
        <button class="icono" id="sm-sig" title="Siguiente">▶</button><button class="icono" id="sm-fin" title="Final">⏭</button>
        <span class="contador" id="sm-contador">Sin ejecución</span>
        <span class="velocidad">velocidad <input type="range" id="sm-vel" min="0.5" max="4" step="0.5" value="1.5"></span>
      </div>
      <div class="traza" id="sm-traza"></div>`;
    const q = (id) => tarjeta.querySelector(id);
    this.entrada = q('#sm-cadena'); this.cinta = q('#sm-cinta'); this.veredicto = q('#sm-veredicto');
    this.contador = q('#sm-contador'); this.listaTraza = q('#sm-traza'); this.botonPlay = q('#sm-play'); this.vel = q('#sm-vel');
    q('#sm-cerrar').addEventListener('click', () => this.cerrar(true));
    q('#sm-ejecutar').addEventListener('click', () => this.ejecutar());
    this.entrada.addEventListener('keydown', (e) => { if (e.key === 'Enter') this.ejecutar(); });
    q('#sm-inicio').addEventListener('click', () => this.irA(0, true));
    q('#sm-atras').addEventListener('click', () => this.irA(this.indice - 1, true));
    q('#sm-sig').addEventListener('click', () => this.irA(this.indice + 1, true));
    q('#sm-fin').addEventListener('click', () => this.irA(this.traza ? this.traza.pasos.length - 1 : 0, true));
    this.botonPlay.addEventListener('click', () => this.alternar());
    this.vel.addEventListener('input', () => { if (this.timer) { this.parar(); this.alternar(); } });
  }

  abrir() {
    this.tarjeta.hidden = false;
    this.traza = null; this.indice = 0;
    this.cinta.innerHTML = ''; this.veredicto.innerHTML = ''; this.listaTraza.innerHTML = '';
    this.contador.textContent = 'Sin ejecución';
    this.entrada.focus();
    this.dibujar();
  }

  cerrar(avisar) {
    this.parar();
    this.tarjeta.hidden = true;
    this.traza = null;
    if (avisar) this.alCerrar();
  }

  async ejecutar() {
    this.parar();
    const r = await llamar('simular', { automata: this.obtenerAutomata(), cadena: this.entrada.value.trim() });
    if (!r.ok) { this.alAvisar(r.mensaje || 'No se pudo ejecutar.', 'error'); return; }
    this.traza = r; this.indice = 0;
    this.cinta.innerHTML = Array.from(r.cadena).map((c) => `<span class="simbolo">${esc(c)}</span>`).join('');
    this.listaTraza.innerHTML = r.pasos.map((p) => {
      const conj = `{${p.estados.join(', ')}}` === '{}' ? '∅' : `{${p.estados.join(', ')}}`;
      return `<div>${p.simbolo === null ? 'inicio' : `${p.indice}. leer ${esc(p.simbolo)}`}  →  ${esc(conj)}</div>`;
    }).join('');
    this.irA(0, false);
  }

  irA(i, manual) {
    if (!this.traza) return;
    if (manual) this.parar();
    const total = this.traza.pasos.length;
    this.indice = Math.min(Math.max(i, 0), total - 1);
    this.contador.textContent = `Paso ${this.indice} de ${total - 1}`;
    [...this.cinta.children].forEach((s, k) => {
      s.className = 'simbolo' + (k < this.indice ? ' leido' : k === this.indice ? ' actual' : '');
    });
    [...this.listaTraza.children].forEach((d, k) => d.classList.toggle('actual', k === this.indice));
    if (this.indice === total - 1) {
      this.veredicto.innerHTML = `<span class="insignia ${this.traza.acepta ? 'ok' : 'mal'}">${this.traza.acepta ? 'ACEPTADA' : 'RECHAZADA'}</span> <span class="ayuda">${esc(this.traza.motivo)}</span>`;
    } else {
      this.veredicto.innerHTML = '';
    }
    this.dibujar();
  }

  dibujar() {
    const a = this.obtenerAutomata();
    if (!a) return;
    const paso = this.traza ? this.traza.pasos[this.indice] : null;
    this.diagrama.mostrar(grafoDesdeAutomata(a), {
      activos: paso ? paso.estados : [],
      recorridas: paso ? paso.transiciones.map((t) => claveArista(t.origen, t.destino)) : [],
    });
  }

  alternar() {
    if (!this.traza) { this.ejecutar().then(() => this.alternar()); return; }
    if (this.timer) { this.parar(); return; }
    if (this.indice >= this.traza.pasos.length - 1) this.irA(0, false);
    if (this.traza.pasos.length <= 1) return;
    this.botonPlay.textContent = '⏸';
    this.timer = setInterval(() => {
      this.irA(this.indice + 1, false);
      if (this.indice >= this.traza.pasos.length - 1) this.parar();
    }, 1000 / Number(this.vel.value));
  }

  parar() {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    if (this.botonPlay) this.botonPlay.textContent = '▶';
  }
}
