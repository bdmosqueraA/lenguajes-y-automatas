// Pantalla de autómatas de pila (AP).
import { llamar } from './api.js';
import { Diagrama, claveArista } from './grafo.js';
import { ControlReproductor, htmlControles } from './reproductor.js';
import { $, avisar, descargar, esc } from './util.js';

const verL = (t) => (t === '' || t === undefined || t === null ? 'λ' : t);
const textoTransicion = (t) => `${verL(t.leido ?? t.lee)},${verL(t.desapila)}/${verL(t.apila)}`;

$('vista-pila').innerHTML = `
<div class="rejilla">
  <section class="col-izq">
    <article class="tarjeta">
      <h2><span class="num">1</span>Aceptación</h2>
      <div class="segmentos" id="pl-segmentos">
        <button class="segmento activo" data-modo="estado_final"><strong>Por estado final</strong><small>Entrada consumida y en un estado de F</small></button>
        <button class="segmento" data-modo="pila_vacia"><strong>Por pila vacía</strong><small>Entrada consumida y pila vacía</small></button>
      </div>
    </article>

    <article class="tarjeta">
      <h2><span class="num">2</span>Definición</h2>
      <div class="herramientas">
        <select id="pl-ejemplos" aria-label="Cargar un ejemplo"><option value="">Cargar un ejemplo…</option></select>
        <button class="secundario" id="pl-abrir">Abrir</button><button class="secundario" id="pl-guardar">Guardar</button>
        <input type="file" id="pl-archivo" accept="application/json,.json" hidden>
      </div>
      <span class="etiqueta">Estados</span>
      <div class="tabla-scroll"><table class="matriz" id="pl-estados"></table></div>
      <div class="pie-editor"><button class="secundario" id="pl-btn-estado">＋ Estado</button>
        <label class="etiqueta" style="margin:0" for="pl-z0">Pila inicial Z₀</label><input id="pl-z0" maxlength="1" style="width:56px;text-align:center" placeholder="λ" value="Z"></div>
      <span class="etiqueta">Transiciones <small>δ(origen, lee, desapila) = (destino, apila)</small></span>
      <div class="tabla-scroll"><table class="matriz" id="pl-trans"></table></div>
      <div class="pie-editor"><button class="secundario" id="pl-btn-trans">＋ Transición</button><button class="texto" id="pl-limpiar">Limpiar todo</button>
        <span class="ayuda">«Desapila λ» no mira la pila. «Apila»: el primer símbolo queda en la cima.</span></div>
      <p class="ayuda" id="pl-alfabetos"></p>
      <div id="pl-mensajes" class="mensajes" aria-live="polite"></div>
      <button class="primario grande" id="pl-crear">Crear autómata de pila</button>
    </article>

    <article class="tarjeta" id="pl-ops" hidden>
      <h2><span class="num">3</span>Operaciones</h2>
      <div class="operaciones">
        <button class="op" data-op="simular"><strong>Probar una cadena</strong><small>Paso a paso, viendo la pila.</small></button>
        <button class="op" data-op="lote"><strong>Probar varias cadenas</strong><small>Una por línea, con tabla de resultados.</small></button>
      </div>
    </article>
  </section>

  <section class="col-der">
    <article class="tarjeta">
      <header class="cab"><h2 id="pl-titulo-diagrama">Diagrama</h2>
        <div class="acciones"><button class="texto" id="pl-btn-ajustar">Ajustar a la vista</button><button class="texto" id="pl-btn-reorganizar">Reorganizar</button><button class="texto" id="pl-btn-svg">Descargar SVG</button></div></header>
      <div id="pl-diagrama"></div>
      <p class="ayuda">Cada flecha dice <code>lee,desapila/apila</code> (λ = nada). Arrastra los estados para acomodarlos.</p>
    </article>
    <article class="tarjeta" id="pl-sim" hidden></article>
    <article class="tarjeta" id="pl-lote" hidden></article>
  </section>
</div>`;

// ------------------------------------------------------------------ editor
class EditorPila {
  constructor({ alAvisar, alCambiar }) {
    this.alAvisar = alAvisar; this.alCambiar = alCambiar;
    this.tEstados = $('pl-estados'); this.tTrans = $('pl-trans'); this.z0 = $('pl-z0'); this.alfabetos = $('pl-alfabetos');
    this.modo = 'estado_final';
    this._conectar(); this.restablecer();
  }

  restablecer() {
    this.estados = ['q0', 'q1']; this.inicial = 'q0'; this.finales = new Set(); this.trans = []; this.z0.value = 'Z'; this.render();
  }

  setModo(modo) { this.modo = modo; this.render(); }
  siguienteNombre() { let n = 0; while (this.estados.includes(`q${n}`)) n++; return `q${n}`; }

  agregarEstado() { const q = this.siguienteNombre(); this.estados.push(q); this.render(); this.alCambiar(); }

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
    const ult = this.trans[this.trans.length - 1];
    const o = ult ? ult.destino : this.inicial;
    this.trans.push({ origen: o, lee: '', desapila: '', apila: '', destino: o });
    this.render(); this.alCambiar();
    const campos = this.tTrans.querySelectorAll('tbody tr:last-child input'); if (campos[0]) campos[0].focus();
  }

  obtenerDatos() {
    return { modo: this.modo, estados: [...this.estados], inicial: this.inicial, finales: [...this.finales],
      z0: this.z0.value, transiciones: this.trans.map((t) => ({ ...t })) };
  }

  cargar(m) {
    this.modo = m.modo; this.estados = [...m.estados]; this.inicial = m.inicial; this.finales = new Set(m.finales);
    this.z0.value = m.simbolo_inicial || '';
    this.trans = m.transiciones.map((t) => ({ origen: t.origen, lee: t.leido, desapila: t.desapila, apila: t.apila, destino: t.destino }));
    this.render();
  }

  limpiarErrores() { document.querySelectorAll('#vista-pila .celda-error, #vista-pila .fila-error').forEach((e) => e.classList.remove('celda-error', 'fila-error')); }

  marcarErrores(errores) {
    this.limpiarErrores();
    for (const e of errores) {
      if (e.campo === 'transicion' && e.indice !== null && e.indice !== undefined) {
        const f = this.tTrans.querySelector(`tbody tr[data-i="${e.indice}"]`); if (f) f.classList.add('fila-error');
      } else if (e.campo === 'estados' && e.estado) {
        const c = this.tEstados.querySelector(`tr[data-q="${CSS.escape(e.estado)}"] .nombre-estado`); if (c) c.classList.add('celda-error');
      } else if (e.campo === 'z0') this.z0.classList.add('celda-error');
    }
  }

  _alfabetos() {
    const sigma = new Set(); const gamma = new Set(this.z0.value.trim() && this.z0.value.trim() !== 'λ' ? [this.z0.value.trim()] : []);
    for (const t of this.trans) {
      if (t.lee && t.lee !== 'λ') sigma.add(t.lee);
      for (const c of Array.from(`${t.desapila}${t.apila}`)) if (c !== 'λ' && !/\s/.test(c)) gamma.add(c);
    }
    return { sigma: [...sigma].sort(), gamma: [...gamma].sort() };
  }

  _actualizarAlfabetos() {
    const { sigma, gamma } = this._alfabetos();
    this.alfabetos.innerHTML = `Se deducen de las transiciones: Σ = <code>{${sigma.map(esc).join(', ')}}</code> · Γ = <code>{${gamma.map(esc).join(', ')}}</code>`;
  }

  render() {
    const conFinal = this.modo === 'estado_final';
    this.tEstados.innerHTML = `<thead><tr><th>Inicio</th>${conFinal ? '<th>Final</th>' : ''}<th>Estado</th><th></th></tr></thead><tbody>`
      + this.estados.map((q) => `<tr data-q="${esc(q)}"><td><input type="radio" name="pl-inicial" class="r-inicial" ${q === this.inicial ? 'checked' : ''}></td>`
        + (conFinal ? `<td><input type="checkbox" class="c-final" ${this.finales.has(q) ? 'checked' : ''}></td>` : '')
        + `<td><input class="nombre-estado" value="${esc(q)}" spellcheck="false" autocomplete="off"></td><td><button class="borrar" tabindex="-1" title="Eliminar estado">✕</button></td></tr>`).join('') + '</tbody>';
    const opciones = (sel) => this.estados.map((q) => `<option value="${esc(q)}" ${q === sel ? 'selected' : ''}>${esc(q)}</option>`).join('');
    this.tTrans.innerHTML = '<thead><tr><th>#</th><th>Origen</th><th>Lee</th><th>Desapila</th><th>Apila</th><th>Destino</th><th></th></tr></thead><tbody>'
      + (this.trans.length ? this.trans.map((t, i) => `<tr data-i="${i}"><td class="num-fila">${i + 1}</td><td><select data-c="origen">${opciones(t.origen)}</select></td>`
        + `<td><input data-c="lee" maxlength="1" value="${esc(t.lee)}" placeholder="λ" style="min-width:48px"></td>`
        + `<td><input data-c="desapila" maxlength="1" value="${esc(t.desapila)}" placeholder="λ" style="min-width:48px"></td>`
        + `<td><input data-c="apila" value="${esc(t.apila)}" placeholder="λ" style="min-width:60px"></td>`
        + `<td><select data-c="destino">${opciones(t.destino)}</select></td><td><button class="borrar" tabindex="-1" title="Eliminar transición">✕</button></td></tr>`).join('')
        : '<tr><td colspan="7" class="ayuda" style="padding:12px">Aún no hay transiciones: pulsa «＋ Transición».</td></tr>') + '</tbody>';
    this._actualizarAlfabetos();
  }

  _conectar() {
    this.tEstados.addEventListener('change', (e) => {
      const c = e.target; const fila = c.closest('tr'); if (!fila || !fila.dataset.q) return; const q = fila.dataset.q;
      if (c.classList.contains('nombre-estado')) { if (this.renombrar(q, c.value)) this.render(); else c.value = q; } else if (c.classList.contains('r-inicial')) { this.inicial = q; this.alCambiar(); } else if (c.classList.contains('c-final')) { if (c.checked) this.finales.add(q); else this.finales.delete(q); this.alCambiar(); }
    });
    this.tEstados.addEventListener('click', (e) => { const b = e.target.closest('.borrar'); if (b) this.eliminarEstado(b.closest('tr').dataset.q); });
    const alEditar = (e) => {
      const c = e.target; const fila = c.closest('tr'); if (!fila || fila.dataset.i === undefined || !c.dataset.c) return;
      this.trans[Number(fila.dataset.i)][c.dataset.c] = c.value; fila.classList.remove('fila-error'); this._actualizarAlfabetos(); this.alCambiar();
    };
    this.tTrans.addEventListener('input', alEditar); this.tTrans.addEventListener('change', alEditar);
    this.tTrans.addEventListener('click', (e) => {
      const b = e.target.closest('.borrar'); if (!b) return;
      this.trans.splice(Number(b.closest('tr').dataset.i), 1); this.render(); this.alCambiar();
    });
    this.z0.addEventListener('input', () => { this.z0.classList.remove('celda-error'); this._actualizarAlfabetos(); this.alCambiar(); });
    $('pl-btn-estado').addEventListener('click', () => this.agregarEstado());
    $('pl-btn-trans').addEventListener('click', () => this.agregarTransicion());
    $('pl-limpiar').addEventListener('click', () => { this.restablecer(); this.alCambiar(); });
  }
}

// ------------------------------------------------------------------ grafo
function grafoDesdePila(m) {
  const conFinal = m.modo === 'estado_final';
  const nodos = m.estados.map((q) => ({ id: q, inicial: q === m.inicial, final: conFinal && m.finales.includes(q) }));
  const mapa = new Map();
  for (const t of m.transiciones) {
    const k = claveArista(t.origen, t.destino);
    if (!mapa.has(k)) mapa.set(k, { origen: t.origen, destino: t.destino, partes: [] });
    mapa.get(k).partes.push(textoTransicion(t));
  }
  return { clave: 'actual', nodos, leyenda: [], aristas: [...mapa.values()].map((e) => ({ origen: e.origen, destino: e.destino, etiqueta: e.partes.join(' | ') })) };
}

// ------------------------------------------------------------------ probar una cadena
class SimuladorPila {
  constructor(tarjeta, diagrama, { obtenerMaquina, alCerrar }) {
    this.tarjeta = tarjeta; this.diagrama = diagrama; this.obtenerMaquina = obtenerMaquina; this.alCerrar = alCerrar; this.traza = null;
    tarjeta.innerHTML = `
      <header class="cab"><h2>Probar una cadena</h2><button class="texto" data-x="cerrar">Cerrar</button></header>
      <div class="fila-entrada"><input data-x="cadena" placeholder="cadena de entrada (vacía = λ)" spellcheck="false" autocomplete="off">
        <select data-x="modo" title="Cómo se decide si se acepta"><option value="">Según la máquina</option><option value="estado_final">Por estado final</option><option value="pila_vacia">Por pila vacía</option></select>
        <button class="primario" data-x="ejecutar">Probar</button></div>
      <div class="sim-grid"><div>
        <div class="fila-cinta"><span class="etiqueta">Entrada</span><div class="cinta" data-x="entrada"></div></div>
        <div class="estado-grande" data-x="estado"></div><div data-x="veredicto"></div>
        ${htmlControles()}<div class="traza" data-x="traza"></div></div>
        <div><div class="pila-etq">Pila</div><div class="pila-caja" data-x="pila"></div></div></div>`;
    const q = (x) => tarjeta.querySelector(`[data-x="${x}"]`);
    this.entrada = q('cadena'); this.modo = q('modo'); this.cinta = q('entrada'); this.estado = q('estado'); this.veredicto = q('veredicto');
    this.lista = q('traza'); this.pila = q('pila');
    q('cerrar').addEventListener('click', () => this.cerrar(true)); q('ejecutar').addEventListener('click', () => this.ejecutar());
    this.entrada.addEventListener('keydown', (e) => { if (e.key === 'Enter') this.ejecutar(); });
    this.ctl = new ControlReproductor(tarjeta, { alIr: (i) => this.mostrar(i) });
  }

  abrir() { this.tarjeta.hidden = false; this.traza = null; this.ctl.configurar(0); this.cinta.innerHTML = ''; this.estado.textContent = ''; this.veredicto.innerHTML = ''; this.lista.innerHTML = ''; this.pila.innerHTML = '<div class="pila-vacia">—</div>'; this.entrada.focus(); this.dibujar(null); }
  cerrar(avisarCierre) { this.ctl.parar(); this.tarjeta.hidden = true; this.traza = null; if (avisarCierre) this.alCerrar(); }

  async ejecutar() {
    this.ctl.parar();
    const r = await llamar('simular_pila', { maquina: this.obtenerMaquina(), cadena: this.entrada.value.trim(), modo: this.modo.value || null });
    if (!r.ok) { avisar(r.mensaje || 'No se pudo simular.', 'error'); return; }
    this.traza = r;
    this.cinta.innerHTML = Array.from(r.cadena).map((c) => `<span class="simbolo">${esc(c)}</span>`).join('');
    this.lista.innerHTML = r.pasos.map((p) => `<div>${p.transicion === null ? `inicio  →  (${esc(p.estado)}, ${esc(verL(p.restante))}, ${esc(verL(p.pila))})`
      : `${p.indice}. ${esc(p.transicion.origen)} —${esc(textoTransicion(p.transicion))}→ ${esc(p.transicion.destino)}  ·  pila: ${esc(verL(p.pila))}`}</div>`).join('');
    this.ctl.configurar(r.pasos.length); this.ctl.irA(0, false);
  }

  mostrar(i) {
    const r = this.traza; if (!r) return;
    const p = r.pasos[i]; const consumidos = r.cadena.length - p.restante.length;
    [...this.cinta.children].forEach((s, k) => { s.className = `simbolo${k < consumidos ? ' leido' : k === consumidos ? ' actual' : ''}`; });
    this.estado.innerHTML = `Estado: <b>${esc(p.estado)}</b>`;
    const celdas = Array.from(p.pila);
    this.pila.innerHTML = celdas.length ? celdas.map((c, k) => `<div class="pila-celda${k === 0 ? ' cima' : ''}">${esc(c)}</div>`).join('') : '<div class="pila-vacia">pila vacía</div>';
    [...this.lista.children].forEach((d, k) => d.classList.toggle('actual', k === i));
    if (i === r.pasos.length - 1) {
      const extra = r.acepta ? '' : (r.limite ? '' : ' Se muestra la rama que más entrada consumió.');
      this.veredicto.innerHTML = `<span class="insignia ${r.acepta ? 'ok' : 'mal'}">${r.acepta ? 'ACEPTADA' : 'RECHAZADA'}</span> <span class="ayuda">${esc(r.motivo)}${esc(extra)}</span>`
        + `<div class="ayuda">Configuraciones exploradas: ${r.explorado}${r.limite ? ' (búsqueda cortada por el límite)' : ''}. Modo: ${r.modo === 'estado_final' ? 'por estado final' : 'por pila vacía'}.</div>`;
    } else this.veredicto.innerHTML = '';
    this.dibujar(p);
  }

  dibujar(p) {
    const m = this.obtenerMaquina(); if (!m) return;
    this.diagrama.mostrar(grafoDesdePila(m), { activos: p ? [p.estado] : [], recorridas: p && p.transicion ? [claveArista(p.transicion.origen, p.transicion.destino)] : [] });
  }
}

// ------------------------------------------------------------------ varias cadenas
class LotePila {
  constructor(tarjeta, { obtenerMaquina, alCerrar }) {
    this.tarjeta = tarjeta; this.obtenerMaquina = obtenerMaquina; this.alCerrar = alCerrar;
    tarjeta.innerHTML = `
      <header class="cab"><h2>Probar varias cadenas</h2><button class="texto" data-x="cerrar">Cerrar</button></header>
      <textarea class="lote-texto" data-x="texto" spellcheck="false" placeholder="Una cadena por línea. Escribe λ para la cadena vacía."></textarea>
      <div class="resultado" style="border:0;margin:6px 0 0;padding:0"><button class="primario" data-x="ejecutar">Probar todas</button><span class="ayuda" data-x="nota" style="margin:0"></span></div>
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
    const r = await llamar('simular_pila_lote', { maquina: this.obtenerMaquina(), cadenas });
    if (!r.ok) { avisar(r.mensaje || 'No se pudo probar.', 'error'); return; }
    this.tabla.innerHTML = '<table><thead><tr><th>Entrada</th><th>Resultado</th><th>Configuraciones</th><th>Nota</th></tr></thead><tbody>'
      + r.filas.map((f) => `<tr class="${f.acepta ? '' : 'mala'}"><td>${f.cadena === '' ? 'λ' : esc(f.cadena)}</td><td>${f.acepta ? 'ACEPTADA' : 'RECHAZADA'}</td><td>${f.explorado}${f.limite ? '+' : ''}</td><td class="nota">${f.limite ? 'Búsqueda cortada por el límite: no se puede asegurar el rechazo.' : ''}</td></tr>`).join('') + '</tbody></table>';
    const acept = r.filas.filter((f) => f.acepta).length;
    this.nota.textContent = `${acept} aceptada${acept === 1 ? '' : 's'} de ${r.filas.length}${r.recortado ? ' (solo las primeras 300)' : ''}.`;
  }
}

// ------------------------------------------------------------------ orquestación
const estado = { maquina: null };
const diagrama = new Diagrama($('pl-diagrama'));
const editor = new EditorPila({ alAvisar: avisar, alCambiar: () => { if (estado.maquina) $('pl-crear').textContent = 'Actualizar autómata de pila (hay cambios sin aplicar)'; } });
const simulador = new SimuladorPila($('pl-sim'), diagrama, { obtenerMaquina: () => estado.maquina, alCerrar: () => { mostrarActual(); marcarOp(null); } });
const lote = new LotePila($('pl-lote'), { obtenerMaquina: () => estado.maquina, alCerrar: () => marcarOp(null) });

const mostrarMensajes = (lista) => { $('pl-mensajes').innerHTML = lista.map((m) => `<div class="mensaje ${m.tipo}">${esc(m.texto)}</div>`).join(''); };
const marcarOp = (id) => document.querySelectorAll('#pl-ops .op').forEach((b) => b.classList.toggle('activa', b.dataset.op === id));

function mostrarActual() {
  const m = estado.maquina;
  if (!m) { diagrama.limpiar('Crea un autómata de pila para verlo aquí.'); $('pl-titulo-diagrama').textContent = 'Diagrama'; return; }
  $('pl-titulo-diagrama').textContent = `Diagrama · AP ${m.determinista ? 'determinista' : 'no determinista'} con ${m.estados.length} estado${m.estados.length === 1 ? '' : 's'}`;
  diagrama.mostrar(grafoDesdePila(m));
}

function fijarModo(modo) {
  document.querySelectorAll('#pl-segmentos .segmento').forEach((b) => b.classList.toggle('activo', b.dataset.modo === modo));
  editor.setModo(modo); $('pl-mensajes').innerHTML = '';
}
document.querySelectorAll('#pl-segmentos .segmento').forEach((b) => b.addEventListener('click', () => fijarModo(b.dataset.modo)));

async function crear() {
  $('pl-mensajes').innerHTML = ''; editor.limpiarErrores();
  const boton = $('pl-crear'); boton.disabled = true;
  const r = await llamar('crear_pila', editor.obtenerDatos());
  boton.disabled = false;
  if (!r.ok) {
    const errores = r.errores || [{ mensaje: r.mensaje || 'No se pudo crear el autómata.', campo: 'general' }];
    mostrarMensajes(errores.map((e) => ({ tipo: 'error', texto: e.mensaje }))); editor.marcarErrores(errores);
    return;
  }
  estado.maquina = r.maquina; simulador.cerrar(false); lote.cerrar(false); marcarOp(null);
  diagrama.reiniciarLayouts(); mostrarActual(); $('pl-ops').hidden = false; $('pl-crear').textContent = 'Actualizar autómata de pila';
  mostrarMensajes([{ tipo: 'ok', texto: `Autómata de pila creado con ${r.maquina.estados.length} estados y ${r.maquina.transiciones.length} transiciones.` },
    ...(r.advertencias || []).map((w) => ({ tipo: 'aviso', texto: w }))]);
}
$('pl-crear').addEventListener('click', crear);

$('pl-ops').addEventListener('click', (e) => {
  const b = e.target.closest('.op'); if (!b || !estado.maquina) return;
  marcarOp(b.dataset.op);
  if (b.dataset.op === 'simular') { lote.cerrar(false); simulador.abrir(); $('pl-titulo-diagrama').textContent = 'Simulación'; $('pl-sim').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } else { simulador.cerrar(false); mostrarActual(); lote.abrir(); $('pl-lote').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
});

let ejemplos = [];
(async () => {
  const r = await llamar('ejemplos_pila', {});
  if (!r.ok) return;
  ejemplos = r.maquinas;
  $('pl-ejemplos').insertAdjacentHTML('beforeend', ejemplos.map((x, i) => `<option value="${i}">${esc(x.nombre)}</option>`).join(''));
})();
$('pl-ejemplos').addEventListener('change', (e) => {
  const v = e.target.value; e.target.value = '';
  if (v === '') return;
  const m = ejemplos[Number(v)].maquina; fijarModo(m.modo); editor.cargar(m);
  avisar('Ejemplo cargado. Pulsa «Crear autómata de pila».');
});

$('pl-guardar').addEventListener('click', () => {
  if (!estado.maquina) { avisar('Primero crea un autómata de pila.', 'error'); return; }
  descargar('automata_pila.json', JSON.stringify(estado.maquina, null, 2), 'application/json');
});
$('pl-abrir').addEventListener('click', () => $('pl-archivo').click());
$('pl-archivo').addEventListener('change', async (e) => {
  const archivo = e.target.files[0]; e.target.value = '';
  if (!archivo) return;
  try {
    const m = JSON.parse(await archivo.text());
    if (!['estado_final', 'pila_vacia'].includes(m.modo) || !Array.isArray(m.estados) || !m.inicial || !Array.isArray(m.transiciones) || !Array.isArray(m.finales)) throw new Error('formato');
    fijarModo(m.modo); editor.cargar(m); avisar('Archivo abierto. Pulsa «Crear autómata de pila».');
  } catch (err) { avisar('No se pudo leer el archivo: no tiene el formato de un autómata de pila guardado.', 'error'); }
});
$('pl-btn-reorganizar').addEventListener('click', () => diagrama.reorganizar());
$('pl-btn-ajustar').addEventListener('click', () => { $('pl-btn-ajustar').textContent = diagrama.alternarAjuste() ? 'Tamaño real' : 'Ajustar a la vista'; });
$('pl-btn-svg').addEventListener('click', () => {
  const svg = diagrama.exportarSVG();
  if (!svg) { avisar('No hay ningún dibujo para descargar.', 'error'); return; }
  descargar('automata_pila.svg', svg, 'image/svg+xml');
});

fijarModo('estado_final'); diagrama.limpiar('Crea un autómata de pila para verlo aquí.');
window.__pila = { estado, editor, diagrama, simulador, lote };
