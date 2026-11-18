// Editor interactivo de la tabla de transición (la "matriz").
const LAMBDA = 'λ';
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const dividir = (texto) => String(texto || '').split(/[,;\s]+/).filter((t) => t && !['∅', '-', '—'].includes(t));

export class EditorTabla {
  constructor({ alAvisar = () => {}, alCambiar = () => {} } = {}) {
    this.alAvisar = alAvisar;
    this.alCambiar = alCambiar;
    this.matriz = document.getElementById('matriz');
    this.chips = document.getElementById('chips-alfabeto');
    this.nuevoSimbolo = document.getElementById('nuevo-simbolo');
    this.ayuda = document.getElementById('ayuda-celdas');
    this.modo = 'AFD';
    this._conectar();
    this.restablecer();
  }

  // ------------------------------------------------------------ modelo
  restablecer() {
    this.estados = ['q0', 'q1'];
    this.alfabeto = ['a', 'b'];
    this.inicial = 'q0';
    this.finales = new Set();
    this.tabla = {};
    this.render();
  }

  columnas() { return this.alfabeto.concat(this.modo === 'AFND-LAMBDA' ? [LAMBDA] : []); }

  setModo(modo) {
    this.modo = modo;
    if (modo !== 'AFND-LAMBDA') for (const q of Object.keys(this.tabla)) delete this.tabla[q][LAMBDA];
    this.render();
  }

  siguienteNombre() {
    let n = 0;
    while (this.estados.includes(`q${n}`)) n++;
    return `q${n}`;
  }

  agregarEstado() {
    const q = this.siguienteNombre();
    this.estados.push(q);
    if (!this.inicial) this.inicial = q;
    this.render();
    const campo = this.matriz.querySelector(`tr[data-q="${CSS.escape(q)}"] .celda`);
    if (campo) campo.focus();
    this.alCambiar();
  }

  eliminarEstado(q) {
    if (this.estados.length <= 1) { this.alAvisar('Debe quedar al menos un estado.', 'error'); return; }
    this.estados = this.estados.filter((x) => x !== q);
    delete this.tabla[q];
    this.finales.delete(q);
    if (this.inicial === q) this.inicial = this.estados[0];
    for (const o of Object.keys(this.tabla)) {
      for (const s of Object.keys(this.tabla[o])) {
        this.tabla[o][s] = dividir(this.tabla[o][s]).filter((x) => x !== q).join(', ');
      }
    }
    this.render();
    this.alCambiar();
  }

  renombrar(viejo, nuevo) {
    nuevo = nuevo.trim();
    if (nuevo === viejo) return true;
    if (!nuevo || /[,;\s]/.test(nuevo)) { this.alAvisar('El nombre no puede estar vacío ni tener espacios o comas.', 'error'); return false; }
    if (this.estados.includes(nuevo)) { this.alAvisar(`Ya existe un estado llamado «${nuevo}».`, 'error'); return false; }
    this.estados = this.estados.map((q) => (q === viejo ? nuevo : q));
    if (this.tabla[viejo]) { this.tabla[nuevo] = this.tabla[viejo]; delete this.tabla[viejo]; }
    if (this.inicial === viejo) this.inicial = nuevo;
    if (this.finales.delete(viejo)) this.finales.add(nuevo);
    for (const o of Object.keys(this.tabla)) {
      for (const s of Object.keys(this.tabla[o])) {
        this.tabla[o][s] = dividir(this.tabla[o][s]).map((x) => (x === viejo ? nuevo : x)).join(', ');
      }
    }
    this.alCambiar();
    return true;
  }

  agregarSimbolos(texto) {
    const nuevos = [];
    for (const c of Array.from(texto)) {
      if (/\s|,|;/.test(c)) continue;
      if (c === LAMBDA) { this.alAvisar('λ no es un símbolo del alfabeto: en AFND-λ aparece como columna propia.', 'aviso'); continue; }
      if (!this.alfabeto.includes(c) && !nuevos.includes(c)) nuevos.push(c);
    }
    if (!nuevos.length) return;
    this.alfabeto.push(...nuevos);
    this.render();
    this.alCambiar();
  }

  eliminarSimbolo(s) {
    this.alfabeto = this.alfabeto.filter((x) => x !== s);
    for (const q of Object.keys(this.tabla)) delete this.tabla[q][s];
    this.render();
    this.alCambiar();
  }

  // ------------------------------------------------------------ datos
  obtenerDatos() {
    return {
      modo: this.modo, estados: [...this.estados], alfabeto: [...this.alfabeto],
      inicial: this.inicial, finales: [...this.finales],
      tabla: JSON.parse(JSON.stringify(this.tabla)),
    };
  }

  cargar(a) {
    this.estados = [...a.estados];
    this.alfabeto = [...a.alfabeto];
    this.inicial = a.inicial;
    this.finales = new Set(a.finales);
    this.tabla = {};
    for (const t of a.transiciones) {
      const fila = this.tabla[t.origen] || (this.tabla[t.origen] = {});
      fila[t.simbolo] = fila[t.simbolo] ? `${fila[t.simbolo]}, ${t.destino}` : t.destino;
    }
    let tipo = a.tipo;
    if (!tipo) {                                  // archivos guardados a mano pueden no traer el tipo
      const cuenta = new Map();
      for (const t of a.transiciones) { const k = `${t.origen}\u0001${t.simbolo}`; cuenta.set(k, (cuenta.get(k) || 0) + 1); }
      tipo = a.transiciones.some((t) => t.simbolo === LAMBDA) ? 'AFND-λ' : [...cuenta.values()].some((n) => n > 1) ? 'AFND' : 'AFD';
    }
    this.modo = tipo === 'AFD' ? 'AFD' : tipo === 'AFND' ? 'AFND' : 'AFND-LAMBDA';
    this.render();
  }

  // ------------------------------------------------------------ errores
  limpiarErrores() {
    this.matriz.querySelectorAll('.celda-error').forEach((e) => e.classList.remove('celda-error'));
  }

  marcarErrores(errores) {
    this.limpiarErrores();
    for (const e of errores) {
      if (e.campo === 'celda' && e.estado != null) {
        const c = this.matriz.querySelector(`tr[data-q="${CSS.escape(e.estado)}"] .celda[data-s="${CSS.escape(e.simbolo)}"]`);
        if (c) c.classList.add('celda-error');
      } else if (e.campo === 'estados' && e.estado) {
        const c = this.matriz.querySelector(`tr[data-q="${CSS.escape(e.estado)}"] .nombre-estado`);
        if (c) c.classList.add('celda-error');
      }
    }
  }

  // ------------------------------------------------------------ dibujo
  render() {
    const cols = this.columnas();
    const cabecera = `<thead><tr><th title="Estado inicial">Inicio</th><th title="Estado de aceptación">Final</th><th>Estado</th>`
      + cols.map((s) => `<th class="col-simbolo${s === LAMBDA ? ' col-lambda' : ''}">${esc(s)}</th>`).join('') + '<th></th></tr></thead>';
    const marcador = this.modo === 'AFD' ? 'q1' : 'q1, q2';
    const filas = this.estados.map((q) => {
      const celdas = cols.map((s) => {
        const valor = (this.tabla[q] && this.tabla[q][s]) || '';
        return `<td><input class="celda" data-s="${esc(s)}" value="${esc(valor)}" placeholder="∅" spellcheck="false" autocomplete="off"></td>`;
      }).join('');
      return `<tr data-q="${esc(q)}"><td><input type="radio" name="inicial" class="r-inicial" ${q === this.inicial ? 'checked' : ''} title="Estado inicial"></td>`
        + `<td><input type="checkbox" class="c-final" ${this.finales.has(q) ? 'checked' : ''} title="Estado de aceptación"></td>`
        + `<td><input class="nombre-estado" value="${esc(q)}" spellcheck="false" autocomplete="off"></td>${celdas}`
        + '<td><button class="borrar" title="Eliminar estado" tabindex="-1">✕</button></td></tr>';
    }).join('');
    this.matriz.innerHTML = `${cabecera}<tbody>${filas}</tbody>`;
    this.chips.innerHTML = this.alfabeto.map((s) => `<span class="chip">${esc(s)}<button data-s="${esc(s)}" title="Quitar el símbolo">✕</button></span>`).join('')
      || '<span class="ayuda">Agrega al menos un símbolo.</span>';
    this.ayuda.textContent = this.modo === 'AFD'
      ? `Cada celda: un estado (ej. ${marcador}) o vacía.` : `Varios destinos separados por coma (ej. ${marcador}).`;
    this.matriz.querySelectorAll('.celda').forEach((c) => this._validarCelda(c));
  }

  _validarCelda(campo) {
    const destinos = dividir(campo.value);
    const desconocido = destinos.some((d) => !this.estados.includes(d));
    const demasiados = this.modo === 'AFD' && destinos.length > 1;
    campo.classList.toggle('celda-aviso', desconocido || demasiados);
    campo.title = desconocido ? 'Hay un estado que no existe' : demasiados ? 'En un AFD solo puede haber un destino' : '';
  }

  _conectar() {
    this.matriz.addEventListener('input', (e) => {
      const c = e.target;
      if (!c.classList.contains('celda')) return;
      const q = c.closest('tr').dataset.q;
      (this.tabla[q] || (this.tabla[q] = {}))[c.dataset.s] = c.value;
      c.classList.remove('celda-error');
      this._validarCelda(c);
      this.alCambiar();
    });
    this.matriz.addEventListener('change', (e) => {
      const c = e.target; const fila = c.closest('tr'); if (!fila) return;
      const q = fila.dataset.q;
      if (c.classList.contains('nombre-estado')) {
        if (this.renombrar(q, c.value)) this.render(); else c.value = q;
      } else if (c.classList.contains('r-inicial')) {
        this.inicial = q; this.alCambiar();
      } else if (c.classList.contains('c-final')) {
        if (c.checked) this.finales.add(q); else this.finales.delete(q);
        this.alCambiar();
      }
    });
    this.matriz.addEventListener('click', (e) => {
      const b = e.target.closest('.borrar');
      if (b) this.eliminarEstado(b.closest('tr').dataset.q);
    });
    this.matriz.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || !e.target.classList.contains('celda')) return;
      e.preventDefault();
      const filas = [...this.matriz.querySelectorAll('tbody tr')];
      const i = filas.indexOf(e.target.closest('tr'));
      const destino = filas[i + 1] || filas[0];
      const campo = destino.querySelector(`.celda[data-s="${CSS.escape(e.target.dataset.s)}"]`);
      if (campo) campo.focus();
    });
    this.chips.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (b) this.eliminarSimbolo(b.dataset.s);
    });
    const agregar = () => { this.agregarSimbolos(this.nuevoSimbolo.value); this.nuevoSimbolo.value = ''; this.nuevoSimbolo.focus(); };
    document.getElementById('btn-simbolo').addEventListener('click', agregar);
    this.nuevoSimbolo.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); agregar(); } });
    document.getElementById('btn-estado').addEventListener('click', () => this.agregarEstado());
    document.getElementById('btn-limpiar').addEventListener('click', () => { this.restablecer(); this.alCambiar(); });
  }
}
