// Pantalla de traductores: máquinas de Moore y de Mealy.
import { llamar } from './api.js';
import { Diagrama, claveArista, grafoDesdeTraductor } from './grafo.js';
import { $, avisar, descargar, esc } from './util.js';

const dividir = (t) => String(t || '').split(/[,;\s]+/).filter(Boolean);
const NOMBRE_TIPO = { moore: 'Moore', mealy: 'Mealy' };

$('vista-traductores').innerHTML = `
<div class="rejilla">
  <section class="col-izq">
    <article class="tarjeta">
      <h2><span class="num">1</span>Tipo de máquina</h2>
      <div class="segmentos" id="tr-segmentos">
        <button class="segmento activo" data-tipo="moore"><strong>Moore</strong><small>Salida en los estados · γ: Q → Γ</small></button>
        <button class="segmento" data-tipo="mealy"><strong>Mealy</strong><small>Salida en las transiciones · γ: Q×Σ → Γ</small></button>
      </div>
    </article>

    <article class="tarjeta">
      <h2><span class="num">2</span>Definición</h2>
      <div class="herramientas">
        <select id="tr-ejemplos" aria-label="Cargar un ejemplo"><option value="">Cargar un ejemplo…</option></select>
        <button class="secundario" id="tr-abrir" title="Abrir una máquina guardada (.json)">Abrir</button>
        <button class="secundario" id="tr-guardar" title="Guardar la máquina creada (.json)">Guardar</button>
        <input type="file" id="tr-archivo" accept="application/json,.json" hidden>
      </div>
      <div class="fila-alfabeto">
        <span class="etiqueta">Entrada Σ</span>
        <div class="chips" id="tr-chips"></div>
        <input id="tr-nuevo" maxlength="12" placeholder="0, 1, a…" aria-label="Símbolos de entrada nuevos">
        <button class="secundario" id="tr-btn-simbolo">＋ Símbolo</button>
      </div>
      <div class="tabla-scroll"><table class="matriz" id="tr-matriz"></table></div>
      <div class="pie-editor">
        <button class="secundario" id="tr-btn-estado">＋ Estado</button>
        <button class="texto" id="tr-limpiar">Limpiar tabla</button>
        <span class="ayuda" id="tr-ayuda"></span>
      </div>
      <p class="ayuda" id="tr-gamma"></p>
      <div id="tr-mensajes" class="mensajes" aria-live="polite"></div>
      <button class="primario grande" id="tr-crear">Crear máquina</button>
    </article>

    <article class="tarjeta" id="tr-ops" hidden>
      <h2><span class="num">3</span>Operaciones</h2>
      <div class="operaciones">
        <button class="op" data-op="traducir"><strong>Traducir una cadena</strong><small>Paso a paso: estado, transición y salida.</small></button>
        <button class="op" data-op="lote"><strong>Traducir varias cadenas</strong><small>Una por línea, con una tabla de resultados.</small></button>
      </div>
    </article>
  </section>

  <section class="col-der">
    <article class="tarjeta">
      <header class="cab">
        <h2 id="tr-titulo-diagrama">Diagrama</h2>
        <div class="acciones">
          <button class="texto" id="tr-btn-ajustar">Ajustar a la vista</button>
          <button class="texto" id="tr-btn-reorganizar">Reorganizar</button>
          <button class="texto" id="tr-btn-svg">Descargar SVG</button>
        </div>
      </header>
      <div id="tr-diagrama"></div>
      <p class="ayuda" id="tr-ayuda-diagrama">Arrastra los estados con el ratón para acomodarlos.</p>
    </article>
    <article class="tarjeta" id="tr-sim" hidden></article>
    <article class="tarjeta" id="tr-lote" hidden></article>
  </section>
</div>`;

// ------------------------------------------------------------------ editor
class EditorTraductor {
  constructor({ alAvisar, alCambiar }) {
    this.alAvisar = alAvisar; this.alCambiar = alCambiar;
    this.matriz = $('tr-matriz'); this.chips = $('tr-chips'); this.nuevo = $('tr-nuevo');
    this.ayuda = $('tr-ayuda'); this.gamma = $('tr-gamma');
    this.tipo = 'moore';
    this._conectar();
    this.restablecer();
  }

  restablecer() {
    this.estados = ['q0', 'q1']; this.entrada = ['0', '1']; this.inicial = 'q0'; this.tabla = {}; this.salidas = {};
    this.render();
  }

  setTipo(tipo) { this.tipo = tipo; this.render(); }

  siguienteNombre() { let n = 0; while (this.estados.includes(`q${n}`)) n++; return `q${n}`; }

  agregarEstado() {
    const q = this.siguienteNombre(); this.estados.push(q);
    if (!this.inicial) this.inicial = q;
    this.render();
    const campo = this.matriz.querySelector(`tr[data-q="${CSS.escape(q)}"] .celda, tr[data-q="${CSS.escape(q)}"] .celda-salida`);
    if (campo) campo.focus();
    this.alCambiar();
  }

  _reescribir(texto, viejo, nuevo) {            // cambia el destino de una celda al renombrar o borrar un estado
    if (this.tipo === 'moore') return dividir(texto).map((x) => (x === viejo ? nuevo : x)).filter(Boolean).join(', ');
    const [d, ...resto] = String(texto).split('/');
    const destino = d.trim() === viejo ? nuevo : d.trim();
    return destino ? destino + (resto.length ? `/${resto.join('/')}` : '') : '';
  }

  eliminarEstado(q) {
    if (this.estados.length <= 1) { this.alAvisar('Debe quedar al menos un estado.', 'error'); return; }
    this.estados = this.estados.filter((x) => x !== q);
    delete this.tabla[q]; delete this.salidas[q];
    if (this.inicial === q) this.inicial = this.estados[0];
    for (const o of Object.keys(this.tabla)) for (const s of Object.keys(this.tabla[o])) this.tabla[o][s] = this._reescribir(this.tabla[o][s], q, '');
    this.render(); this.alCambiar();
  }

  renombrar(viejo, nuevo) {
    nuevo = nuevo.trim();
    if (nuevo === viejo) return true;
    if (!nuevo || /[,;\s/]/.test(nuevo)) { this.alAvisar('El nombre no puede estar vacío ni tener espacios, comas o «/».', 'error'); return false; }
    if (this.estados.includes(nuevo)) { this.alAvisar(`Ya existe un estado llamado «${nuevo}».`, 'error'); return false; }
    this.estados = this.estados.map((q) => (q === viejo ? nuevo : q));
    if (this.tabla[viejo]) { this.tabla[nuevo] = this.tabla[viejo]; delete this.tabla[viejo]; }
    if (viejo in this.salidas) { this.salidas[nuevo] = this.salidas[viejo]; delete this.salidas[viejo]; }
    if (this.inicial === viejo) this.inicial = nuevo;
    for (const o of Object.keys(this.tabla)) for (const s of Object.keys(this.tabla[o])) this.tabla[o][s] = this._reescribir(this.tabla[o][s], viejo, nuevo);
    this.alCambiar();
    return true;
  }

  agregarSimbolos(texto) {
    const nuevos = [];
    for (const c of Array.from(texto)) {
      if (/\s|,|;|\//.test(c)) continue;
      if (!this.entrada.includes(c) && !nuevos.includes(c)) nuevos.push(c);
    }
    if (!nuevos.length) return;
    this.entrada.push(...nuevos); this.render(); this.alCambiar();
  }

  eliminarSimbolo(s) {
    this.entrada = this.entrada.filter((x) => x !== s);
    for (const q of Object.keys(this.tabla)) delete this.tabla[q][s];
    this.render(); this.alCambiar();
  }

  obtenerDatos() {
    return { tipo: this.tipo, estados: [...this.estados], entrada: [...this.entrada], inicial: this.inicial,
      tabla: JSON.parse(JSON.stringify(this.tabla)), salidas: { ...this.salidas } };
  }

  cargar(m) {
    this.tipo = m.tipo; this.estados = [...m.estados]; this.entrada = [...m.entrada]; this.inicial = m.inicial;
    this.tabla = {}; this.salidas = {};
    for (const t of m.transiciones) {
      (this.tabla[t.origen] || (this.tabla[t.origen] = {}))[t.simbolo] = m.tipo === 'moore' ? t.destino : `${t.destino}/${t.salida || 'λ'}`;
    }
    if (m.tipo === 'moore') for (const q of m.estados) this.salidas[q] = (m.salidas_estados && m.salidas_estados[q]) || '';
    this.render();
  }

  limpiarErrores() { this.matriz.querySelectorAll('.celda-error').forEach((e) => e.classList.remove('celda-error')); }

  marcarErrores(errores) {
    this.limpiarErrores();
    for (const e of errores) {
      let c = null;
      if (e.campo === 'celda' && e.estado != null) c = this.matriz.querySelector(`tr[data-q="${CSS.escape(e.estado)}"] .celda[data-s="${CSS.escape(e.simbolo)}"]`);
      else if (e.campo === 'salida' && e.estado) c = this.matriz.querySelector(`tr[data-q="${CSS.escape(e.estado)}"] .celda-salida`);
      else if (e.campo === 'estados' && e.estado) c = this.matriz.querySelector(`tr[data-q="${CSS.escape(e.estado)}"] .nombre-estado`);
      if (c) c.classList.add('celda-error');
    }
  }

  _gamma() {
    const g = new Set();
    const anotar = (t) => { for (const c of Array.from(String(t || '').trim())) if (c !== 'λ' && !/\s/.test(c)) g.add(c); };
    if (this.tipo === 'moore') for (const q of this.estados) anotar(this.salidas[q]);
    else for (const q of this.estados) for (const s of this.entrada) { const t = (this.tabla[q] || {})[s]; if (t && t.includes('/')) anotar(t.split('/').slice(1).join('/')); }
    return [...g].sort();
  }

  _actualizarGamma() {
    const g = this._gamma();
    this.gamma.innerHTML = `Alfabeto de salida Γ (se deduce de las salidas): <code>{${g.map(esc).join(', ')}}</code>`;
  }

  render() {
    const moore = this.tipo === 'moore';
    const cab = `<thead><tr><th title="Estado inicial">Inicio</th><th>Estado</th>${moore ? '<th class="col-salida" title="Salida del estado (γ)">Salida</th>' : ''}`
      + this.entrada.map((s) => `<th class="col-simbolo">${esc(s)}</th>`).join('') + '<th></th></tr></thead>';
    const filas = this.estados.map((q) => {
      const celdas = this.entrada.map((s) => `<td><input class="celda" data-s="${esc(s)}" value="${esc((this.tabla[q] && this.tabla[q][s]) || '')}" placeholder="∅" spellcheck="false" autocomplete="off"></td>`).join('');
      return `<tr data-q="${esc(q)}"><td><input type="radio" name="tr-inicial" class="r-inicial" ${q === this.inicial ? 'checked' : ''} title="Estado inicial"></td>`
        + `<td><input class="nombre-estado" value="${esc(q)}" spellcheck="false" autocomplete="off"></td>`
        + (moore ? `<td><input class="celda-salida" value="${esc(this.salidas[q] || '')}" placeholder="λ" spellcheck="false" autocomplete="off"></td>` : '')
        + `${celdas}<td><button class="borrar" title="Eliminar estado" tabindex="-1">✕</button></td></tr>`;
    }).join('');
    this.matriz.innerHTML = `${cab}<tbody>${filas}</tbody>`;
    this.chips.innerHTML = this.entrada.map((s) => `<span class="chip">${esc(s)}<button data-s="${esc(s)}" title="Quitar el símbolo">✕</button></span>`).join('')
      || '<span class="ayuda">Agrega al menos un símbolo.</span>';
    this.ayuda.textContent = moore ? 'Cada celda: el estado destino (ej. q1). La salida va en su columna.'
      : 'Cada celda: destino/salida (ej. q1/b). Sin salida o λ = cadena vacía.';
    this.matriz.querySelectorAll('.celda').forEach((c) => this._validarCelda(c));
    this._actualizarGamma();
  }

  _validarCelda(campo) {
    const t = campo.value.trim(); let malo = false; let aviso = '';
    if (t) {
      if (this.tipo === 'moore') {
        const d = dividir(t);
        if (d.length > 1) { malo = true; aviso = 'En Moore solo puede haber un destino'; } else if (d[0] && !this.estados.includes(d[0])) { malo = true; aviso = 'Ese estado no existe'; }
      } else if (/[,;]/.test(t)) { malo = true; aviso = 'Solo una transición por celda'; } else {
        const d = t.split('/')[0].trim();
        if (d && !this.estados.includes(d)) { malo = true; aviso = 'Ese estado no existe'; }
      }
    }
    campo.classList.toggle('celda-aviso', malo); campo.title = aviso;
  }

  _conectar() {
    this.matriz.addEventListener('input', (e) => {
      const c = e.target; const fila = c.closest('tr'); if (!fila) return;
      const q = fila.dataset.q;
      if (c.classList.contains('celda')) {
        (this.tabla[q] || (this.tabla[q] = {}))[c.dataset.s] = c.value; c.classList.remove('celda-error'); this._validarCelda(c);
      } else if (c.classList.contains('celda-salida')) { this.salidas[q] = c.value; c.classList.remove('celda-error'); } else return;
      this._actualizarGamma(); this.alCambiar();
    });
    this.matriz.addEventListener('change', (e) => {
      const c = e.target; const fila = c.closest('tr'); if (!fila) return;
      const q = fila.dataset.q;
      if (c.classList.contains('nombre-estado')) { if (this.renombrar(q, c.value)) this.render(); else c.value = q; } else if (c.classList.contains('r-inicial')) { this.inicial = q; this.alCambiar(); }
    });
    this.matriz.addEventListener('click', (e) => { const b = e.target.closest('.borrar'); if (b) this.eliminarEstado(b.closest('tr').dataset.q); });
    this.matriz.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || !e.target.classList.contains('celda')) return;
      e.preventDefault();
      const filas = [...this.matriz.querySelectorAll('tbody tr')]; const i = filas.indexOf(e.target.closest('tr'));
      const campo = (filas[i + 1] || filas[0]).querySelector(`.celda[data-s="${CSS.escape(e.target.dataset.s)}"]`);
      if (campo) campo.focus();
    });
    this.chips.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) this.eliminarSimbolo(b.dataset.s); });
    const agregar = () => { this.agregarSimbolos(this.nuevo.value); this.nuevo.value = ''; this.nuevo.focus(); };
    $('tr-btn-simbolo').addEventListener('click', agregar);
    this.nuevo.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); agregar(); } });
    $('tr-btn-estado').addEventListener('click', () => this.agregarEstado());
    $('tr-limpiar').addEventListener('click', () => { this.restablecer(); this.alCambiar(); });
  }
}

// ------------------------------------------------------------------ traducir una cadena
class SimuladorTraductor {
  constructor(tarjeta, diagrama, { obtenerMaquina, alCerrar }) {
    this.tarjeta = tarjeta; this.diagrama = diagrama; this.obtenerMaquina = obtenerMaquina; this.alCerrar = alCerrar;
    this.traza = null; this.indice = 0; this.timer = null;
    tarjeta.innerHTML = `
      <header class="cab"><h2>Traducir una cadena</h2><button class="texto" data-x="cerrar">Cerrar</button></header>
      <div class="fila-entrada"><input data-x="cadena" placeholder="cadena de entrada (vacía = λ)" spellcheck="false" autocomplete="off"><button class="primario" data-x="ejecutar">Traducir</button></div>
      <div class="fila-cinta"><span class="etiqueta">Entrada</span><div class="cinta" data-x="entrada"></div></div>
      <div class="fila-cinta"><span class="etiqueta">Salida</span><div class="cinta" data-x="salida"></div></div>
      <div data-x="veredicto"></div>
      <div class="nav-pasos">
        <button class="icono" data-x="inicio" title="Inicio">⏮</button><button class="icono" data-x="atras" title="Atrás">◀</button>
        <button class="icono principal" data-x="play" title="Reproducir">▶</button>
        <button class="icono" data-x="sig" title="Siguiente">▶</button><button class="icono" data-x="fin" title="Final">⏭</button>
        <span class="contador" data-x="contador">Sin ejecución</span>
        <span class="velocidad">velocidad <input type="range" data-x="vel" min="0.5" max="4" step="0.5" value="1.5"></span>
      </div>
      <div class="traza" data-x="traza"></div>`;
    const q = (x) => tarjeta.querySelector(`[data-x="${x}"]`);
    this.entrada = q('cadena'); this.cintaEntrada = q('entrada'); this.cintaSalida = q('salida'); this.veredicto = q('veredicto');
    this.contador = q('contador'); this.lista = q('traza'); this.botonPlay = q('play'); this.vel = q('vel');
    q('cerrar').addEventListener('click', () => this.cerrar(true));
    q('ejecutar').addEventListener('click', () => this.ejecutar());
    this.entrada.addEventListener('keydown', (e) => { if (e.key === 'Enter') this.ejecutar(); });
    q('inicio').addEventListener('click', () => this.irA(0, true));
    q('atras').addEventListener('click', () => this.irA(this.indice - 1, true));
    q('sig').addEventListener('click', () => this.irA(this.indice + 1, true));
    q('fin').addEventListener('click', () => this.irA(this.traza ? this.traza.pasos.length - 1 : 0, true));
    this.botonPlay.addEventListener('click', () => this.alternar());
    this.vel.addEventListener('input', () => { if (this.timer) { this.parar(); this.alternar(); } });
  }

  abrir() {
    this.tarjeta.hidden = false; this.traza = null; this.indice = 0;
    this.cintaEntrada.innerHTML = ''; this.cintaSalida.innerHTML = ''; this.veredicto.innerHTML = ''; this.lista.innerHTML = '';
    this.contador.textContent = 'Sin ejecución';
    this.entrada.focus(); this.dibujar();
  }

  cerrar(avisarCierre) { this.parar(); this.tarjeta.hidden = true; this.traza = null; if (avisarCierre) this.alCerrar(); }

  async ejecutar() {
    this.parar();
    const r = await llamar('traducir', { maquina: this.obtenerMaquina(), cadena: this.entrada.value.trim() });
    if (!r.ok) { avisar(r.mensaje || 'No se pudo traducir.', 'error'); return; }
    this.traza = r; this.indice = 0;
    this.cintaEntrada.innerHTML = Array.from(r.cadena).map((c) => `<span class="simbolo">${esc(c)}</span>`).join('');
    this.lista.innerHTML = r.pasos.map((p) => `<div>${p.simbolo === null ? `inicio  →  ${esc(p.estado)}`
      : `${p.indice}. leer ${esc(p.simbolo)}:  ${esc(p.origen)} → ${esc(p.estado)}  ·  emite ${p.salida ? esc(p.salida) : 'λ'}`}</div>`).join('');
    this.irA(0, false);
  }

  irA(i, manual) {
    if (!this.traza) return;
    if (manual) this.parar();
    const total = this.traza.pasos.length;
    this.indice = Math.min(Math.max(i, 0), total - 1);
    const paso = this.traza.pasos[this.indice];
    this.contador.textContent = `Paso ${this.indice} de ${total - 1}`;
    [...this.cintaEntrada.children].forEach((s, k) => { s.className = `simbolo${k < this.indice ? ' leido' : k === this.indice ? ' actual' : ''}`; });
    const acumulada = Array.from(paso.acumulada); const nuevos = Array.from(paso.salida).length;
    this.cintaSalida.innerHTML = acumulada.map((c, k) => `<span class="simbolo salida${k >= acumulada.length - nuevos ? ' nuevo' : ''}">${esc(c)}</span>`).join('')
      || '<span class="ayuda" style="margin:0">(aún no hay salida)</span>';
    [...this.lista.children].forEach((d, k) => d.classList.toggle('actual', k === this.indice));
    if (this.indice === total - 1) {
      const final = this.traza.salida ? esc(this.traza.salida) : 'λ';
      this.veredicto.innerHTML = this.traza.completa
        ? `<span class="insignia ok">SALIDA: ${final}</span> <span class="ayuda">${esc(this.traza.motivo)}</span>`
        : `<span class="insignia mal">SE DETUVO · salida hasta ahora: ${final}</span> <span class="ayuda">${esc(this.traza.motivo)}</span>`;
    } else this.veredicto.innerHTML = '';
    this.dibujar();
  }

  dibujar() {
    const m = this.obtenerMaquina(); if (!m) return;
    const paso = this.traza ? this.traza.pasos[this.indice] : null;
    this.diagrama.mostrar(grafoDesdeTraductor(m), {
      activos: paso ? [paso.estado] : [],
      recorridas: paso && paso.origen !== null ? [claveArista(paso.origen, paso.estado)] : [],
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

  parar() { if (this.timer) { clearInterval(this.timer); this.timer = null; } if (this.botonPlay) this.botonPlay.textContent = '▶'; }
}

// ------------------------------------------------------------------ traducir varias cadenas
class LoteTraductor {
  constructor(tarjeta, { obtenerMaquina, alCerrar }) {
    this.tarjeta = tarjeta; this.obtenerMaquina = obtenerMaquina; this.alCerrar = alCerrar;
    tarjeta.innerHTML = `
      <header class="cab"><h2>Traducir varias cadenas</h2><button class="texto" data-x="cerrar">Cerrar</button></header>
      <textarea class="lote-texto" data-x="texto" spellcheck="false" placeholder="Una cadena por línea. Escribe λ para la cadena vacía."></textarea>
      <div class="resultado" style="border:0;margin:6px 0 0;padding:0"><button class="primario" data-x="ejecutar">Traducir todas</button><span class="ayuda" data-x="nota" style="margin:0"></span></div>
      <div class="tabla-lote" data-x="tabla"></div>`;
    const q = (x) => tarjeta.querySelector(`[data-x="${x}"]`);
    this.texto = q('texto'); this.nota = q('nota'); this.tabla = q('tabla');
    q('cerrar').addEventListener('click', () => this.cerrar(true));
    q('ejecutar').addEventListener('click', () => this.ejecutar());
  }

  abrir() { this.tarjeta.hidden = false; this.tabla.innerHTML = ''; this.nota.textContent = ''; this.texto.focus(); }
  cerrar(avisarCierre) { this.tarjeta.hidden = true; if (avisarCierre) this.alCerrar(); }

  async ejecutar() {
    const cadenas = this.texto.value.split('\n').map((l) => l.trim()).filter((l) => l !== '').map((l) => (l === 'λ' ? '' : l));
    if (!cadenas.length) { avisar('Escribe al menos una cadena (una por línea).', 'error'); return; }
    const r = await llamar('traducir_lote', { maquina: this.obtenerMaquina(), cadenas });
    if (!r.ok) { avisar(r.mensaje || 'No se pudo traducir.', 'error'); return; }
    const ver = (t) => (t === '' ? 'λ' : esc(t));
    this.tabla.innerHTML = '<table><thead><tr><th>Entrada</th><th>Salida</th><th>Estado final</th><th>Nota</th></tr></thead><tbody>'
      + r.filas.map((f) => `<tr class="${f.completa ? '' : 'mala'}"><td>${ver(f.cadena)}</td><td>${ver(f.salida)}</td><td>${esc(f.estado_final)}</td><td class="nota">${f.completa ? '' : esc(f.motivo)}</td></tr>`).join('')
      + '</tbody></table>';
    this.nota.textContent = `${r.filas.length} cadena${r.filas.length === 1 ? '' : 's'} traducida${r.filas.length === 1 ? '' : 's'}${r.recortado ? ' (solo las primeras 300)' : ''}.`;
  }
}

// ------------------------------------------------------------------ orquestación
const estado = { maquina: null };
const diagrama = new Diagrama($('tr-diagrama'));
const editor = new EditorTraductor({
  alAvisar: avisar,
  alCambiar: () => { if (estado.maquina) $('tr-crear').textContent = 'Actualizar máquina (hay cambios sin aplicar)'; },
});
const simulador = new SimuladorTraductor($('tr-sim'), diagrama, { obtenerMaquina: () => estado.maquina, alCerrar: () => { mostrarActual(); marcarOp(null); } });
const lote = new LoteTraductor($('tr-lote'), { obtenerMaquina: () => estado.maquina, alCerrar: () => marcarOp(null) });

function mostrarMensajes(lista) { $('tr-mensajes').innerHTML = lista.map((m) => `<div class="mensaje ${m.tipo}">${esc(m.texto)}</div>`).join(''); }
function marcarOp(id) { document.querySelectorAll('#tr-ops .op').forEach((b) => b.classList.toggle('activa', b.dataset.op === id)); }

function mostrarActual() {
  const m = estado.maquina;
  if (!m) { diagrama.limpiar('Crea una máquina para verla aquí.'); $('tr-titulo-diagrama').textContent = 'Diagrama'; return; }
  $('tr-titulo-diagrama').textContent = `Diagrama · Máquina de ${NOMBRE_TIPO[m.tipo]} con ${m.estados.length} estado${m.estados.length === 1 ? '' : 's'}`;
  $('tr-ayuda-diagrama').textContent = m.tipo === 'moore'
    ? 'Dentro de cada estado, debajo de su nombre, está su salida (/a). Arrastra los estados para acomodarlos.'
    : 'Cada flecha dice entrada/salida (λ = cadena vacía). Arrastra los estados para acomodarlos.';
  diagrama.mostrar(grafoDesdeTraductor(m));
}

function fijarTipo(tipo) {
  document.querySelectorAll('#tr-segmentos .segmento').forEach((b) => b.classList.toggle('activo', b.dataset.tipo === tipo));
  editor.setTipo(tipo);
  $('tr-mensajes').innerHTML = '';
}
document.querySelectorAll('#tr-segmentos .segmento').forEach((b) => b.addEventListener('click', () => fijarTipo(b.dataset.tipo)));

async function crear() {
  $('tr-mensajes').innerHTML = ''; editor.limpiarErrores();
  const boton = $('tr-crear'); boton.disabled = true;
  const r = await llamar('crear_traductor', editor.obtenerDatos());
  boton.disabled = false;
  if (!r.ok) {
    const errores = r.errores || [{ mensaje: r.mensaje || 'No se pudo crear la máquina.', campo: 'general' }];
    mostrarMensajes(errores.map((e) => ({ tipo: 'error', texto: e.mensaje }))); editor.marcarErrores(errores);
    return;
  }
  estado.maquina = r.maquina;
  simulador.cerrar(false); lote.cerrar(false); marcarOp(null);
  diagrama.reiniciarLayouts(); mostrarActual();
  $('tr-ops').hidden = false; $('tr-crear').textContent = 'Actualizar máquina';
  mostrarMensajes([{ tipo: 'ok', texto: `Máquina de ${NOMBRE_TIPO[r.maquina.tipo]} creada con ${r.maquina.estados.length} estados.` },
    ...(r.advertencias || []).map((w) => ({ tipo: 'aviso', texto: w }))]);
}
$('tr-crear').addEventListener('click', crear);

document.querySelector('#tr-ops').addEventListener('click', (e) => {
  const b = e.target.closest('.op'); if (!b || !estado.maquina) return;
  marcarOp(b.dataset.op);
  if (b.dataset.op === 'traducir') {
    lote.cerrar(false); simulador.abrir(); $('tr-titulo-diagrama').textContent = 'Traducción';
    $('tr-sim').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } else {
    simulador.cerrar(false); mostrarActual(); lote.abrir();
    $('tr-lote').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
});

let ejemplos = [];
(async () => {
  const r = await llamar('ejemplos_traductores', {});
  if (!r.ok) return;
  ejemplos = r.maquinas;
  $('tr-ejemplos').insertAdjacentHTML('beforeend', ejemplos.map((x, i) => `<option value="${i}">${esc(x.nombre)}</option>`).join(''));
})();
$('tr-ejemplos').addEventListener('change', (e) => {
  const v = e.target.value; e.target.value = '';
  if (v === '') return;
  const m = ejemplos[Number(v)].maquina;
  fijarTipo(m.tipo); editor.cargar(m);
  avisar('Ejemplo cargado en la tabla. Pulsa «Crear máquina».');
});

$('tr-guardar').addEventListener('click', () => {
  if (!estado.maquina) { avisar('Primero crea una máquina.', 'error'); return; }
  descargar('maquina.json', JSON.stringify(estado.maquina, null, 2), 'application/json');
});
$('tr-abrir').addEventListener('click', () => $('tr-archivo').click());
$('tr-archivo').addEventListener('change', async (e) => {
  const archivo = e.target.files[0]; e.target.value = '';
  if (!archivo) return;
  try {
    const m = JSON.parse(await archivo.text());
    if (!['moore', 'mealy'].includes(m.tipo) || !Array.isArray(m.estados) || !Array.isArray(m.entrada) || !m.inicial || !Array.isArray(m.transiciones)) throw new Error('formato');
    fijarTipo(m.tipo); editor.cargar(m);
    avisar('Archivo abierto. Pulsa «Crear máquina».');
  } catch (err) { avisar('No se pudo leer el archivo: no tiene el formato de una máquina guardada.', 'error'); }
});

$('tr-btn-reorganizar').addEventListener('click', () => diagrama.reorganizar());
$('tr-btn-ajustar').addEventListener('click', () => { $('tr-btn-ajustar').textContent = diagrama.alternarAjuste() ? 'Tamaño real' : 'Ajustar a la vista'; });
$('tr-btn-svg').addEventListener('click', () => {
  const svg = diagrama.exportarSVG();
  if (!svg) { avisar('No hay ningún dibujo para descargar.', 'error'); return; }
  descargar('maquina.svg', svg, 'image/svg+xml');
});

fijarTipo('moore');
diagrama.limpiar('Crea una máquina para verla aquí.');
window.__traductores = { estado, editor, diagrama, simulador, lote };
