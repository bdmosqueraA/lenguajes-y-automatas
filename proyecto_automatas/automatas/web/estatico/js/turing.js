// Pantalla de máquinas de Turing: una cinta, k cintas y multipista.
import { llamar } from './api.js';
import { Diagrama, claveArista } from './grafo.js';
import { ControlReproductor, htmlControles } from './reproductor.js';
import { $, avisar, descargar, esc } from './util.js';

$('vista-turing').innerHTML = `
<div class="rejilla">
  <section class="col-izq">
    <article class="tarjeta">
      <h2><span class="num">1</span>Tipo de máquina</h2>
      <div class="segmentos" id="tu-segmentos" style="grid-template-columns:1fr 1fr 1fr">
        <button class="segmento activo" data-tipo="una"><strong>1 cinta</strong><small>Máquina clásica</small></button>
        <button class="segmento" data-tipo="multicinta"><strong>Multicinta</strong><small>Varias cintas y cabezas</small></button>
        <button class="segmento" data-tipo="multipista"><strong>Multipista</strong><small>Una cinta, varias pistas</small></button>
      </div>
      <div class="tarea-aparte" id="tu-opcion-cintas" hidden><label for="tu-k">Número de cintas</label><select id="tu-k"><option>2</option><option>3</option><option>4</option></select></div>
      <div class="tarea-aparte" id="tu-opcion-pistas" hidden><label for="tu-p">Número de pistas</label><select id="tu-p"><option>2</option><option>3</option></select></div>
    </article>

    <article class="tarjeta">
      <h2><span class="num">2</span>Definición</h2>
      <div class="herramientas">
        <select id="tu-ejemplos" aria-label="Cargar un ejemplo"><option value="">Cargar un ejemplo…</option></select>
        <button class="secundario" id="tu-abrir">Abrir</button><button class="secundario" id="tu-guardar">Guardar</button>
        <input type="file" id="tu-archivo" accept="application/json,.json" hidden>
      </div>
      <span class="etiqueta">Estados</span>
      <div class="tabla-scroll"><table class="matriz" id="tu-estados"></table></div>
      <div class="pie-editor"><button class="secundario" id="tu-btn-estado">＋ Estado</button>
        <label class="etiqueta" style="margin:0 0 0 auto" for="tu-blanco">Blanco</label><input id="tu-blanco" maxlength="1" value="B" style="width:56px;text-align:center"></div>
      <div class="fila-alfabeto" style="margin-top:10px"><span class="etiqueta">Entrada A</span><div class="chips" id="tu-chips"></div>
        <input id="tu-nuevo" maxlength="12" placeholder="a, b, 0…" aria-label="Símbolos de entrada nuevos"><button class="secundario" id="tu-btn-simbolo">＋ Símbolo</button></div>
      <span class="etiqueta">Transiciones <small id="tu-formato">δ(origen, lee) = (destino, escribe, mueve)</small></span>
      <div class="tabla-scroll"><table class="matriz" id="tu-trans"></table></div>
      <div class="pie-editor"><button class="secundario" id="tu-btn-trans">＋ Transición</button><button class="texto" id="tu-limpiar">Limpiar todo</button>
        <span class="ayuda">Mueve: D derecha · I izquierda · N no mover. Usa el blanco para leer una celda vacía.</span></div>
      <p class="ayuda" id="tu-gamma"></p>
      <div id="tu-mensajes" class="mensajes" aria-live="polite"></div>
      <button class="primario grande" id="tu-crear">Crear máquina de Turing</button>
    </article>

    <article class="tarjeta" id="tu-ops" hidden>
      <h2><span class="num">3</span>Operaciones</h2>
      <div class="operaciones">
        <button class="op" data-op="ejecutar"><strong>Ejecutar una cadena</strong><small>Paso a paso, con las cintas y la cabeza.</small></button>
        <button class="op" data-op="lote"><strong>Ejecutar varias cadenas</strong><small>Una por línea, con el resultado en la cinta.</small></button>
      </div>
    </article>
  </section>

  <section class="col-der">
    <article class="tarjeta">
      <header class="cab"><h2 id="tu-titulo-diagrama">Diagrama</h2>
        <div class="acciones"><button class="texto" id="tu-btn-ajustar">Ajustar a la vista</button><button class="texto" id="tu-btn-reorganizar">Reorganizar</button><button class="texto" id="tu-btn-svg">Descargar SVG</button></div></header>
      <div id="tu-diagrama"></div>
      <p class="ayuda">Cada flecha dice <code>lee → escribe ; mueve</code>. «=» significa que se reescribe el mismo símbolo. Arrastra los estados para acomodarlos.</p>
    </article>
    <article class="tarjeta" id="tu-sim" hidden></article>
    <article class="tarjeta" id="tu-lote" hidden></article>
  </section>
</div>`;

// ------------------------------------------------------------------ editor
class EditorTuring {
  constructor({ alAvisar, alCambiar }) {
    this.alAvisar = alAvisar; this.alCambiar = alCambiar;
    this.tEstados = $('tu-estados'); this.tTrans = $('tu-trans'); this.chips = $('tu-chips'); this.nuevo = $('tu-nuevo'); this.blanco = $('tu-blanco'); this.gamma = $('tu-gamma');
    this.tipo = 'una'; this.k = 2; this.p = 2;
    this._conectar(); this.restablecer();
  }

  cintas() { return this.tipo === 'multicinta' ? this.k : 1; }
  pistas() { return this.tipo === 'multipista' ? this.p : 1; }

  restablecer() {
    this.estados = ['q0', 'qf']; this.inicial = 'q0'; this.finales = new Set(['qf']); this.entrada = []; this.blanco.value = 'B'; this.trans = []; this.render();
  }

  setTipo(tipo, n) {
    this.tipo = tipo;
    if (tipo === 'multicinta' && n) { this.k = n; $('tu-k').value = String(n); }
    if (tipo === 'multipista' && n) { this.p = n; $('tu-p').value = String(n); }
    $('tu-opcion-cintas').hidden = tipo !== 'multicinta'; $('tu-opcion-pistas').hidden = tipo !== 'multipista';
    for (const t of this.trans) this._ajustar(t);
    this.render();
  }

  _ajustar(t) {                                         // la fila siempre tiene una entrada por cinta
    const n = this.cintas();
    for (const [c, relleno] of [['lee', ''], ['escribe', ''], ['mueve', this.cintas() > 1 ? 'N' : 'D']]) {
      t[c] = (t[c] || []).slice(0, n); while (t[c].length < n) t[c].push(relleno);
    }
  }

  siguienteNombre() { let n = 0; while (this.estados.includes(`q${n}`)) n++; return `q${n}`; }
  agregarEstado() { this.estados.push(this.siguienteNombre()); this.render(); this.alCambiar(); }

  eliminarEstado(q) {
    if (this.estados.length <= 1) { this.alAvisar('Debe quedar al menos un estado.', 'error'); return; }
    this.estados = this.estados.filter((x) => x !== q); this.finales.delete(q);
    if (this.inicial === q) this.inicial = this.estados[0];
    this.trans = this.trans.filter((t) => t.origen !== q && t.destino !== q);
    this.render(); this.alCambiar();
  }

  renombrar(viejo, nuevo) {
    nuevo = nuevo.trim();
    if (nuevo === viejo) return true;
    if (!nuevo || /[,;\s/]/.test(nuevo)) { this.alAvisar('El nombre no puede estar vacío ni tener espacios, comas o «/».', 'error'); return false; }
    if (this.estados.includes(nuevo)) { this.alAvisar(`Ya existe un estado llamado «${nuevo}».`, 'error'); return false; }
    this.estados = this.estados.map((q) => (q === viejo ? nuevo : q));
    if (this.inicial === viejo) this.inicial = nuevo;
    if (this.finales.delete(viejo)) this.finales.add(nuevo);
    for (const t of this.trans) { if (t.origen === viejo) t.origen = nuevo; if (t.destino === viejo) t.destino = nuevo; }
    this.alCambiar();
    return true;
  }

  agregarTransicion() {
    const ult = this.trans[this.trans.length - 1]; const o = ult ? ult.destino : this.inicial;
    const t = { origen: o, destino: o, lee: [], escribe: [], mueve: [] }; this._ajustar(t); this.trans.push(t);
    this.render(); this.alCambiar();
    const c = this.tTrans.querySelector('tbody tr:last-child input'); if (c) c.focus();
  }

  agregarSimbolos(texto) {
    const b = this.blanco.value || 'B'; const nuevos = [];
    for (const c of Array.from(texto)) { if (/\s|,|;/.test(c) || c === b) continue; if (!this.entrada.includes(c) && !nuevos.includes(c)) nuevos.push(c); }
    if (!nuevos.length) return;
    this.entrada.push(...nuevos); this.render(); this.alCambiar();
  }

  obtenerDatos() {
    return { cintas: this.cintas(), pistas: this.pistas(), estados: [...this.estados], inicial: this.inicial, finales: [...this.finales],
      entrada: [...this.entrada], blanco: this.blanco.value,
      transiciones: this.trans.map((t) => ({ origen: t.origen, destino: t.destino, lecturas: [...t.lee], escrituras: [...t.escribe], movimientos: [...t.mueve] })) };
  }

  cargar(m) {
    const tipo = m.pistas > 1 ? 'multipista' : m.cintas > 1 ? 'multicinta' : 'una';
    this.estados = [...m.estados]; this.inicial = m.inicial; this.finales = new Set(m.finales); this.entrada = [...m.entrada]; this.blanco.value = m.blanco;
    this.trans = m.transiciones.map((t) => ({ origen: t.origen, destino: t.destino, lee: [...t.lecturas], escribe: [...t.escrituras], mueve: [...t.movimientos] }));
    this.setTipo(tipo, tipo === 'multicinta' ? m.cintas : tipo === 'multipista' ? m.pistas : undefined);
  }

  limpiarErrores() { document.querySelectorAll('#vista-turing .celda-error, #vista-turing .fila-error').forEach((e) => e.classList.remove('celda-error', 'fila-error')); }

  marcarErrores(errores) {
    this.limpiarErrores();
    for (const e of errores) {
      if (e.campo === 'transicion' && e.indice !== null && e.indice !== undefined) { const f = this.tTrans.querySelector(`tbody tr[data-i="${e.indice}"]`); if (f) f.classList.add('fila-error'); } else if (e.campo === 'estados' && e.estado) { const c = this.tEstados.querySelector(`tr[data-q="${CSS.escape(e.estado)}"] .nombre-estado`); if (c) c.classList.add('celda-error'); } else if (e.campo === 'blanco') this.blanco.classList.add('celda-error');
    }
  }

  _gamma() {
    const g = new Set(this.entrada); if (this.blanco.value) g.add(this.blanco.value);
    for (const t of this.trans) for (const s of [...t.lee, ...t.escribe]) for (const c of Array.from(s)) if (!/\s/.test(c)) g.add(c);
    return [...g].sort();
  }
  _actualizarGamma() { this.gamma.innerHTML = `Alfabeto de la cinta Γ (se deduce): <code>{${this._gamma().map(esc).join(', ')}}</code>`; }

  render() {
    this.tEstados.innerHTML = '<thead><tr><th>Inicio</th><th>Final</th><th>Estado</th><th></th></tr></thead><tbody>'
      + this.estados.map((q) => `<tr data-q="${esc(q)}"><td><input type="radio" name="tu-inicial" class="r-inicial" ${q === this.inicial ? 'checked' : ''}></td>`
        + `<td><input type="checkbox" class="c-final" ${this.finales.has(q) ? 'checked' : ''}></td><td><input class="nombre-estado" value="${esc(q)}" spellcheck="false" autocomplete="off"></td>`
        + '<td><button class="borrar" tabindex="-1" title="Eliminar estado">✕</button></td></tr>').join('') + '</tbody>';
    this.chips.innerHTML = this.entrada.map((s) => `<span class="chip">${esc(s)}<button data-s="${esc(s)}" title="Quitar el símbolo">✕</button></span>`).join('') || '<span class="ayuda">Agrega los símbolos de entrada.</span>';
    const n = this.cintas(); const p = this.pistas();
    const opc = (sel) => this.estados.map((q) => `<option value="${esc(q)}" ${q === sel ? 'selected' : ''}>${esc(q)}</option>`).join('');
    const campo = (c, t, k) => `<input data-c="${c}" data-k="${k}" maxlength="${p}" value="${esc(t[c][k] ?? '')}" spellcheck="false" autocomplete="off" style="width:${p > 1 ? 54 : 42}px">`;
    const movs = (t, k) => `<select data-c="mueve" data-k="${k}">${['D', 'I', 'N'].map((m) => `<option ${t.mueve[k] === m ? 'selected' : ''}>${m}</option>`).join('')}</select>`;
    const rango = (f) => Array.from({ length: n }, (_, k) => f(k)).join('');
    this.tTrans.innerHTML = `<thead><tr><th>#</th><th>Origen</th><th>Lee${n > 1 ? ' (por cinta)' : p > 1 ? ' (por pista)' : ''}</th><th>Destino</th><th>Escribe</th><th>Mueve</th><th></th></tr></thead><tbody>`
      + (this.trans.length ? this.trans.map((t, i) => `<tr data-i="${i}"><td class="num-fila">${i + 1}</td><td><select data-c="origen">${opc(t.origen)}</select></td>`
        + `<td><div class="multi">${rango((k) => campo('lee', t, k))}</div></td><td><select data-c="destino">${opc(t.destino)}</select></td>`
        + `<td><div class="multi">${rango((k) => campo('escribe', t, k))}</div></td><td><div class="multi">${rango((k) => movs(t, k))}</div></td>`
        + '<td><button class="borrar" tabindex="-1" title="Eliminar transición">✕</button></td></tr>').join('')
        : '<tr><td colspan="7" class="ayuda" style="padding:12px">Aún no hay transiciones: pulsa «＋ Transición».</td></tr>') + '</tbody>';
    $('tu-formato').textContent = n > 1 ? 'δ(origen, lee en cada cinta) = (destino, escribe y mueve en cada cinta)' : p > 1 ? 'cada símbolo tiene un carácter por pista (ej. 0B)' : 'δ(origen, lee) = (destino, escribe, mueve)';
    this._actualizarGamma();
  }

  _conectar() {
    this.tEstados.addEventListener('change', (e) => {
      const c = e.target; const fila = c.closest('tr'); if (!fila || !fila.dataset.q) return; const q = fila.dataset.q;
      if (c.classList.contains('nombre-estado')) { if (this.renombrar(q, c.value)) this.render(); else c.value = q; } else if (c.classList.contains('r-inicial')) { this.inicial = q; this.alCambiar(); } else if (c.classList.contains('c-final')) { if (c.checked) this.finales.add(q); else this.finales.delete(q); this.alCambiar(); }
    });
    this.tEstados.addEventListener('click', (e) => { const b = e.target.closest('.borrar'); if (b) this.eliminarEstado(b.closest('tr').dataset.q); });
    const alEditar = (e) => {
      const c = e.target; const fila = c.closest('tr'); if (!fila || fila.dataset.i === undefined || !c.dataset.c) return;
      const t = this.trans[Number(fila.dataset.i)];
      if (c.dataset.k !== undefined) t[c.dataset.c][Number(c.dataset.k)] = c.value; else t[c.dataset.c] = c.value;
      fila.classList.remove('fila-error'); this._actualizarGamma(); this.alCambiar();
    };
    this.tTrans.addEventListener('input', alEditar); this.tTrans.addEventListener('change', alEditar);
    this.tTrans.addEventListener('click', (e) => { const b = e.target.closest('.borrar'); if (!b) return; this.trans.splice(Number(b.closest('tr').dataset.i), 1); this.render(); this.alCambiar(); });
    this.chips.addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; this.entrada = this.entrada.filter((x) => x !== b.dataset.s); this.render(); this.alCambiar(); });
    const agregar = () => { this.agregarSimbolos(this.nuevo.value); this.nuevo.value = ''; this.nuevo.focus(); };
    $('tu-btn-simbolo').addEventListener('click', agregar);
    this.nuevo.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); agregar(); } });
    this.blanco.addEventListener('input', () => { this.blanco.classList.remove('celda-error'); this._actualizarGamma(); this.alCambiar(); });
    $('tu-k').addEventListener('change', (e) => { this.k = Number(e.target.value); this.setTipo('multicinta'); this.alCambiar(); });
    $('tu-p').addEventListener('change', (e) => { this.p = Number(e.target.value); this.setTipo('multipista'); this.alCambiar(); });
    $('tu-btn-estado').addEventListener('click', () => this.agregarEstado());
    $('tu-btn-trans').addEventListener('click', () => this.agregarTransicion());
    $('tu-limpiar').addEventListener('click', () => { this.restablecer(); this.alCambiar(); });
  }
}

// ------------------------------------------------------------------ grafo
function etiquetaTuring(m, trs) {
  if (m.cintas > 1) return trs.map((t) => `${t.lecturas.join(',')} → ${t.escrituras.join(',')} ; ${t.movimientos.join(',')}`).join(' | ');
  const identidad = new Map(); const otros = new Map();
  for (const t of trs) {
    const lee = t.lecturas[0]; const esc_ = t.escrituras[0]; const mov = t.movimientos[0];
    if (lee === esc_) identidad.set(mov, [...(identidad.get(mov) || []), lee]);
    else { const k = `${esc_}\u0001${mov}`; const g = otros.get(k) || { esc: esc_, mov, lees: [] }; g.lees.push(lee); otros.set(k, g); }
  }
  const partes = [];
  for (const [mov, lees] of identidad) partes.push(`${lees.join(',')} → = ; ${mov}`);
  for (const g of otros.values()) partes.push(`${g.lees.join(',')} → ${g.esc} ; ${g.mov}`);
  return partes.join(' | ');
}

function grafoDesdeTuring(m) {
  const nodos = m.estados.map((q) => ({ id: q, inicial: q === m.inicial, final: m.finales.includes(q) }));
  const mapa = new Map();
  for (const t of m.transiciones) { const k = claveArista(t.origen, t.destino); if (!mapa.has(k)) mapa.set(k, { origen: t.origen, destino: t.destino, trs: [] }); mapa.get(k).trs.push(t); }
  return { clave: 'actual', nodos, leyenda: [], aristas: [...mapa.values()].map((e) => ({ origen: e.origen, destino: e.destino, etiqueta: etiquetaTuring(m, e.trs) })) };
}

const textoDelta = (t) => `δ(${t.origen}, ${t.lecturas.join(',')}) = (${t.destino}, ${t.escrituras.join(',')}, ${t.movimientos.join(',')})`;

function htmlCinta(m, simbolos, cabeza) {
  const largo = Math.max(simbolos.length, cabeza + 1) + 8; let h = '';
  for (let i = 0; i < largo; i++) {
    const s = i < simbolos.length ? simbolos[i] : m.blanco_celda;
    const cuerpo = Array.from(s).map((c) => `<span>${esc(c)}</span>`).join('');
    h += `<div class="celda-t${s === m.blanco_celda ? ' vacia' : ''}${i === cabeza ? ' cabeza' : ''}">${cuerpo}<span class="idx">${i}</span></div>`;
  }
  return h;
}

// ------------------------------------------------------------------ ejecutar una cadena
class SimuladorTuring {
  constructor(tarjeta, diagrama, { obtenerMaquina, alCerrar }) {
    this.tarjeta = tarjeta; this.diagrama = diagrama; this.obtenerMaquina = obtenerMaquina; this.alCerrar = alCerrar; this.traza = null;
    tarjeta.innerHTML = `
      <header class="cab"><h2>Ejecutar una cadena</h2><button class="texto" data-x="cerrar">Cerrar</button></header>
      <div class="fila-entrada"><input data-x="cadena" placeholder="cadena de entrada (vacía = cinta en blanco)" spellcheck="false" autocomplete="off"><button class="primario" data-x="ejecutar">Ejecutar</button></div>
      <div class="tarea-aparte"><label for="tu-max">Pasos máximos</label><input type="number" id="tu-max" data-x="max" min="1" max="20000" value="2000"><span class="ayuda" style="margin:0">Si la máquina no se detiene, se corta aquí (problema de la parada).</span></div>
      <div class="estado-grande" data-x="estado"></div><div data-x="cintas"></div><div data-x="veredicto"></div>
      ${htmlControles()}<div class="traza" data-x="traza"></div>`;
    const q = (x) => tarjeta.querySelector(`[data-x="${x}"]`);
    this.entrada = q('cadena'); this.max = q('max'); this.estado = q('estado'); this.cintas = q('cintas'); this.veredicto = q('veredicto'); this.lista = q('traza');
    q('cerrar').addEventListener('click', () => this.cerrar(true)); q('ejecutar').addEventListener('click', () => this.ejecutar());
    this.entrada.addEventListener('keydown', (e) => { if (e.key === 'Enter') this.ejecutar(); });
    this.ctl = new ControlReproductor(tarjeta, { alIr: (i) => this.mostrar(i), velMin: 1, velMax: 60, velPaso: 1, velIni: 6 });
  }

  abrir() { this.tarjeta.hidden = false; this.traza = null; this.ctl.configurar(0); this.cintas.innerHTML = ''; this.estado.textContent = ''; this.veredicto.innerHTML = ''; this.lista.innerHTML = ''; this.entrada.focus(); this.dibujar(null); }
  cerrar(avisarCierre) { this.ctl.parar(); this.tarjeta.hidden = true; this.traza = null; if (avisarCierre) this.alCerrar(); }

  async ejecutar() {
    this.ctl.parar();
    const r = await llamar('ejecutar_turing', { maquina: this.obtenerMaquina(), cadena: this.entrada.value.trim(), max_pasos: Number(this.max.value) || 2000 });
    if (!r.ok) { avisar(r.mensaje || 'No se pudo ejecutar.', 'error'); return; }
    this.traza = r; this.ctl.configurar(r.pasos.length); this.ctl.irA(0, false);
  }

  mostrar(i) {
    const r = this.traza; if (!r) return; const m = this.obtenerMaquina(); const p = r.pasos[i];
    this.estado.innerHTML = `Estado: <b>${esc(p.estado)}</b> · paso ${p.indice}${p.transicion ? ` · <span class="ayuda" style="margin:0">${esc(textoDelta(p.transicion))}</span>` : ''}`;
    this.cintas.innerHTML = p.cintas.map((c, k) => `${m.cintas > 1 ? `<div class="etq-cinta">Cinta ${k + 1}</div>` : m.pistas > 1 ? '<div class="etq-cinta">Cinta (cada celda muestra sus pistas)</div>' : ''}<div class="cinta-t" data-k="${k}">${htmlCinta(m, c, p.cabezas[k])}</div>`).join('');
    this.cintas.querySelectorAll('.cinta-t').forEach((c) => { const h = c.querySelector('.cabeza'); if (h) c.scrollLeft = h.offsetLeft - c.clientWidth / 2 + h.offsetWidth / 2; });
    const ini = Math.max(0, i - 6); const fin = Math.min(r.pasos.length - 1, i + 4);
    this.lista.innerHTML = (ini > 0 ? '<div>…</div>' : '') + r.pasos.slice(ini, fin + 1).map((q) => `<div class="${q.indice === i ? 'actual' : ''}">${q.transicion ? `${q.indice}. ${esc(textoDelta(q.transicion))}` : `inicio  →  ${esc(q.estado)}`}</div>`).join('') + (fin < r.pasos.length - 1 ? '<div>…</div>' : '');
    if (i === r.pasos.length - 1) {
      const tipo = r.acepta ? ['ok', 'ACEPTA'] : r.detenida ? ['mal', 'RECHAZA'] : ['mal', 'NO SE DETUVO'];
      this.veredicto.innerHTML = `<span class="insignia ${tipo[0]}">${tipo[1]}</span> <span class="ayuda">${esc(r.motivo)}</span>`;
    } else this.veredicto.innerHTML = '';
    this.dibujar(p);
  }

  dibujar(p) {
    const m = this.obtenerMaquina(); if (!m) return;
    this.diagrama.mostrar(grafoDesdeTuring(m), { activos: p ? [p.estado] : [], recorridas: p && p.transicion ? [claveArista(p.transicion.origen, p.transicion.destino)] : [] });
  }
}

// ------------------------------------------------------------------ varias cadenas
class LoteTuring {
  constructor(tarjeta, { obtenerMaquina, alCerrar }) {
    this.tarjeta = tarjeta; this.obtenerMaquina = obtenerMaquina; this.alCerrar = alCerrar;
    tarjeta.innerHTML = `
      <header class="cab"><h2>Ejecutar varias cadenas</h2><button class="texto" data-x="cerrar">Cerrar</button></header>
      <textarea class="lote-texto" data-x="texto" spellcheck="false" placeholder="Una cadena por línea. Escribe λ para la cadena vacía."></textarea>
      <div class="resultado" style="border:0;margin:6px 0 0;padding:0"><button class="primario" data-x="ejecutar">Ejecutar todas</button><span class="ayuda" data-x="nota" style="margin:0"></span></div>
      <div class="tabla-lote" data-x="tabla"></div>`;
    const q = (x) => tarjeta.querySelector(`[data-x="${x}"]`);
    this.texto = q('texto'); this.nota = q('nota'); this.tabla = q('tabla');
    q('cerrar').addEventListener('click', () => this.cerrar(true)); q('ejecutar').addEventListener('click', () => this.ejecutar());
  }

  abrir() { this.tarjeta.hidden = false; this.tabla.innerHTML = ''; this.nota.textContent = ''; this.texto.focus(); }
  cerrar(avisarCierre) { this.tarjeta.hidden = true; if (avisarCierre) this.alCerrar(); }

  async ejecutar() {
    const cadenas = this.texto.value.split('\n').map((l) => l.trim()).filter((l) => l !== '').map((l) => (l === 'λ' ? '' : l));
    if (!cadenas.length) { avisar('Escribe al menos una cadena (una por línea).', 'error'); return; }
    const r = await llamar('ejecutar_turing_lote', { maquina: this.obtenerMaquina(), cadenas });
    if (!r.ok) { avisar(r.mensaje || 'No se pudo ejecutar.', 'error'); return; }
    const sep = r.etiqueta === 'pistas' ? ' / ' : ' | ';
    this.tabla.innerHTML = `<table><thead><tr><th>Entrada</th><th>Resultado</th><th>Pasos</th><th>${r.etiqueta === 'pistas' ? 'Pistas finales' : 'Cintas finales'}</th><th>Nota</th></tr></thead><tbody>`
      + r.filas.map((f) => `<tr class="${f.acepta ? '' : 'mala'}"><td>${f.cadena === '' ? 'λ' : esc(f.cadena)}</td><td>${f.acepta ? 'ACEPTA' : f.detenida ? 'RECHAZA' : 'NO SE DETUVO'}</td><td>${f.pasos}</td>`
        + `<td>${f.resultado.map((x) => (x === '' ? '—' : esc(x))).join(sep)}</td><td class="nota">${f.acepta ? '' : esc(f.motivo)}</td></tr>`).join('') + '</tbody></table>';
    const n = r.filas.filter((f) => f.acepta).length;
    this.nota.textContent = `${n} aceptada${n === 1 ? '' : 's'} de ${r.filas.length}${r.recortado ? ' (solo las primeras 200)' : ''}.`;
  }
}

// ------------------------------------------------------------------ orquestación
const estado = { maquina: null };
const diagrama = new Diagrama($('tu-diagrama'));
const editor = new EditorTuring({ alAvisar: avisar, alCambiar: () => { if (estado.maquina) $('tu-crear').textContent = 'Actualizar máquina de Turing (hay cambios sin aplicar)'; } });
const simulador = new SimuladorTuring($('tu-sim'), diagrama, { obtenerMaquina: () => estado.maquina, alCerrar: () => { mostrarActual(); marcarOp(null); } });
const lote = new LoteTuring($('tu-lote'), { obtenerMaquina: () => estado.maquina, alCerrar: () => marcarOp(null) });

const mostrarMensajes = (lista) => { $('tu-mensajes').innerHTML = lista.map((m) => `<div class="mensaje ${m.tipo}">${esc(m.texto)}</div>`).join(''); };
const marcarOp = (id) => document.querySelectorAll('#tu-ops .op').forEach((b) => b.classList.toggle('activa', b.dataset.op === id));
const descripcionTipo = (m) => (m.pistas > 1 ? `multipista de ${m.pistas} pistas` : m.cintas > 1 ? `de ${m.cintas} cintas` : 'de 1 cinta');

function mostrarActual() {
  const m = estado.maquina;
  if (!m) { diagrama.limpiar('Crea una máquina de Turing para verla aquí.'); $('tu-titulo-diagrama').textContent = 'Diagrama'; return; }
  $('tu-titulo-diagrama').textContent = `Diagrama · Máquina de Turing ${descripcionTipo(m)} con ${m.estados.length} estados`;
  diagrama.mostrar(grafoDesdeTuring(m));
}

function fijarTipo(tipo) {
  document.querySelectorAll('#tu-segmentos .segmento').forEach((b) => b.classList.toggle('activo', b.dataset.tipo === tipo));
  editor.setTipo(tipo); $('tu-mensajes').innerHTML = '';
}
document.querySelectorAll('#tu-segmentos .segmento').forEach((b) => b.addEventListener('click', () => fijarTipo(b.dataset.tipo)));

async function crear() {
  $('tu-mensajes').innerHTML = ''; editor.limpiarErrores();
  const boton = $('tu-crear'); boton.disabled = true;
  const r = await llamar('crear_turing', editor.obtenerDatos());
  boton.disabled = false;
  if (!r.ok) {
    const errores = r.errores || [{ mensaje: r.mensaje || 'No se pudo crear la máquina.', campo: 'general' }];
    mostrarMensajes(errores.map((e) => ({ tipo: 'error', texto: e.mensaje }))); editor.marcarErrores(errores);
    return;
  }
  estado.maquina = r.maquina; simulador.cerrar(false); lote.cerrar(false); marcarOp(null);
  diagrama.reiniciarLayouts(); mostrarActual(); $('tu-ops').hidden = false; $('tu-crear').textContent = 'Actualizar máquina de Turing';
  mostrarMensajes([{ tipo: 'ok', texto: `Máquina de Turing ${descripcionTipo(r.maquina)} creada con ${r.maquina.estados.length} estados y ${r.maquina.transiciones.length} transiciones.` },
    ...(r.advertencias || []).map((w) => ({ tipo: 'aviso', texto: w }))]);
}
$('tu-crear').addEventListener('click', crear);

$('tu-ops').addEventListener('click', (e) => {
  const b = e.target.closest('.op'); if (!b || !estado.maquina) return;
  marcarOp(b.dataset.op);
  if (b.dataset.op === 'ejecutar') { lote.cerrar(false); simulador.abrir(); $('tu-titulo-diagrama').textContent = 'Ejecución'; $('tu-sim').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } else { simulador.cerrar(false); mostrarActual(); lote.abrir(); $('tu-lote').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
});

let ejemplos = [];
(async () => {
  const r = await llamar('ejemplos_turing', {});
  if (!r.ok) return;
  ejemplos = r.maquinas;
  $('tu-ejemplos').insertAdjacentHTML('beforeend', ejemplos.map((x, i) => `<option value="${i}">${esc(x.nombre)}</option>`).join(''));
})();
$('tu-ejemplos').addEventListener('change', (e) => {
  const v = e.target.value; e.target.value = '';
  if (v === '') return;
  const m = ejemplos[Number(v)].maquina;
  document.querySelectorAll('#tu-segmentos .segmento').forEach((b) => b.classList.toggle('activo', b.dataset.tipo === (m.pistas > 1 ? 'multipista' : m.cintas > 1 ? 'multicinta' : 'una')));
  editor.cargar(m); $('tu-mensajes').innerHTML = '';
  avisar('Ejemplo cargado. Pulsa «Crear máquina de Turing».');
});

$('tu-guardar').addEventListener('click', () => {
  if (!estado.maquina) { avisar('Primero crea una máquina de Turing.', 'error'); return; }
  descargar('maquina_turing.json', JSON.stringify(estado.maquina, null, 2), 'application/json');
});
$('tu-abrir').addEventListener('click', () => $('tu-archivo').click());
$('tu-archivo').addEventListener('change', async (e) => {
  const archivo = e.target.files[0]; e.target.value = '';
  if (!archivo) return;
  try {
    const m = JSON.parse(await archivo.text());
    if (!Array.isArray(m.estados) || !Array.isArray(m.entrada) || !m.inicial || !Array.isArray(m.transiciones) || !Array.isArray(m.finales) || !m.cintas || !m.pistas || !m.blanco) throw new Error('formato');
    document.querySelectorAll('#tu-segmentos .segmento').forEach((b) => b.classList.toggle('activo', b.dataset.tipo === (m.pistas > 1 ? 'multipista' : m.cintas > 1 ? 'multicinta' : 'una')));
    editor.cargar(m); avisar('Archivo abierto. Pulsa «Crear máquina de Turing».');
  } catch (err) { avisar('No se pudo leer el archivo: no tiene el formato de una máquina de Turing guardada.', 'error'); }
});
$('tu-btn-reorganizar').addEventListener('click', () => diagrama.reorganizar());
$('tu-btn-ajustar').addEventListener('click', () => { $('tu-btn-ajustar').textContent = diagrama.alternarAjuste() ? 'Tamaño real' : 'Ajustar a la vista'; });
$('tu-btn-svg').addEventListener('click', () => {
  const svg = diagrama.exportarSVG();
  if (!svg) { avisar('No hay ningún dibujo para descargar.', 'error'); return; }
  descargar('maquina_turing.svg', svg, 'image/svg+xml');
});

diagrama.limpiar('Crea una máquina de Turing para verla aquí.');
window.__turing = { estado, editor, diagrama, simulador, lote };
