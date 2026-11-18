// Orquestación de la pantalla de autómatas finitos.
import { llamar, obtener } from './api.js';
import { Diagrama, grafoDesdeAutomata } from './grafo.js';
import { EditorTabla } from './editor.js';
import { VisorPasos } from './pasos.js';
import { Simulador } from './simulacion.js';
import { $, esc, avisar, descargar } from './util.js';
import './traductores.js';
import './pila.js';
import './turing.js';

const estado = { modo: 'AFD', automata: null };

const OPERACIONES = [
  { id: 'simular', titulo: 'Probar cadenas', desc: 'Ejecuta una cadena y recorre cada paso.', aplica: () => true },
  { id: 'a_afd', titulo: 'Convertir a AFD', desc: 'Subconjuntos con λ-clausura, tabla por tabla.', aplica: (t) => t !== 'AFD', motivo: 'Ya es un AFD' },
  { id: 'minimizar', titulo: 'Minimizar', desc: 'Partición de estados equivalentes, iteración por iteración.', aplica: (t) => t === 'AFD', motivo: 'Primero conviértelo a AFD' },
  { id: 'completar', titulo: 'Completar', desc: 'Agrega el estado trampa.', aplica: (t) => t === 'AFD', motivo: 'Primero conviértelo a AFD' },
  { id: 'complemento', titulo: 'Complemento', desc: 'Acepta justo lo que el autómata rechaza.', aplica: () => true },
  { id: 'a_er', titulo: 'Autómata → expresión regular', desc: 'Eliminación de estados.', aplica: () => true },
  { id: 'a_thompson', titulo: 'Autómata → AFND-λ (Thompson)', desc: 'Pasa por la expresión regular y aplica Thompson.', aplica: () => true },
];

// ------------------------------------------------------------------ avisos
function mostrarMensajes(lista) {
  $('mensajes').innerHTML = lista.map((m) => `<div class="mensaje ${m.tipo}">${esc(m.texto)}</div>`).join('');
}

// ------------------------------------------------------------------ componentes
const diagrama = new Diagrama($('diagrama'));
const editor = new EditorTabla({
  alAvisar: avisar,
  alCambiar: () => { if (estado.automata) $('btn-crear').textContent = 'Actualizar autómata (hay cambios sin aplicar)'; },
});
const visor = new VisorPasos($('tarjeta-pasos'), diagrama, {
  alUsarResultado: usarResultado,
  alCerrar: () => { mostrarActual(); marcarOperacion(null); },
  alAvisar: avisar,
});
const simulador = new Simulador($('tarjeta-simulacion'), diagrama, {
  obtenerAutomata: () => estado.automata,
  alCerrar: () => { mostrarActual(); marcarOperacion(null); },
  alAvisar: avisar,
});

// ------------------------------------------------------------------ tema y pestañas
function fijarTema(oscuro) {
  document.documentElement.dataset.tema = oscuro ? 'oscuro' : 'claro';
  $('tema').checked = oscuro;
  try { localStorage.setItem('tema', oscuro ? 'oscuro' : 'claro'); } catch (e) { /* sin almacenamiento */ }
}
let temaGuardado = null;
try { temaGuardado = localStorage.getItem('tema'); } catch (e) { /* ignorar */ }
fijarTema(temaGuardado === 'oscuro');
$('tema').addEventListener('change', (e) => fijarTema(e.target.checked));

document.querySelectorAll('.pestana').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('.pestana').forEach((x) => x.classList.toggle('activa', x === b));
  document.querySelectorAll('.vista').forEach((v) => v.classList.toggle('activa', v.id === `vista-${b.dataset.vista}`));
}));

// ------------------------------------------------------------------ tipo de autómata
function fijarModo(modo) {
  estado.modo = modo;
  document.querySelectorAll('#segmentos-tipo .segmento').forEach((b) => b.classList.toggle('activo', b.dataset.modo === modo));
  $('panel-tabla').hidden = modo === 'ER';
  $('panel-er').hidden = modo !== 'ER';
  if (modo !== 'ER') editor.setModo(modo);
  $('mensajes').innerHTML = '';
}
document.querySelectorAll('#segmentos-tipo .segmento').forEach((b) => b.addEventListener('click', () => fijarModo(b.dataset.modo)));
const modoDeTipo = (tipo) => (tipo === 'AFD' ? 'AFD' : tipo === 'AFND' ? 'AFND' : 'AFND-LAMBDA');

// atajos de la expresión regular
$('atajos-er').addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b) return;
  const campo = $('er-texto'); const ins = b.dataset.ins;
  const ini = campo.selectionStart ?? campo.value.length; const fin = campo.selectionEnd ?? ini;
  campo.value = campo.value.slice(0, ini) + ins + campo.value.slice(fin);
  const caret = ins === '()' ? ini + 1 : ini + ins.length;
  campo.focus(); campo.setSelectionRange(caret, caret);
});
$('er-texto').addEventListener('keydown', (e) => { if (e.key === 'Enter') crear(); });

// ------------------------------------------------------------------ crear
function mostrarActual() {
  if (!estado.automata) { diagrama.limpiar(); $('titulo-diagrama').textContent = 'Diagrama'; return; }
  const a = estado.automata;
  $('titulo-diagrama').textContent = `Diagrama · ${a.tipo} con ${a.estados.length} estado${a.estados.length === 1 ? '' : 's'}`;
  diagrama.mostrar(grafoDesdeAutomata(a));
}

function establecerAutomata(a) {
  estado.automata = a;
  simulador.cerrar(false);
  visor.cerrar(false);
  diagrama.reiniciarLayouts();
  marcarOperacion(null);
  mostrarActual();
  $('tarjeta-operaciones').hidden = false;
  actualizarOperaciones();
  $('btn-crear').textContent = 'Actualizar autómata';
}

async function crear() {
  $('mensajes').innerHTML = '';
  editor.limpiarErrores();
  const datos = estado.modo === 'ER'
    ? { modo: 'ER', er: $('er-texto').value, alfabeto_extra: $('er-extra').value }
    : editor.obtenerDatos();
  const boton = $('btn-crear'); boton.disabled = true;
  const r = await llamar('crear', datos);
  boton.disabled = false;
  if (!r.ok) {
    const errores = r.errores || [{ mensaje: r.mensaje || 'No se pudo crear el autómata.', campo: 'general' }];
    mostrarMensajes(errores.map((e) => ({ tipo: 'error', texto: e.mensaje })));
    editor.marcarErrores(errores);
    return;
  }
  establecerAutomata(r.automata);
  const mensajes = [{ tipo: 'ok', texto: `Autómata creado: ${r.automata.tipo} con ${r.automata.estados.length} estados.` }];
  for (const w of r.advertencias || []) mensajes.push({ tipo: 'aviso', texto: w });
  if (r.operacion) mensajes.push({ tipo: 'ok', texto: 'Mira el paso a paso de la construcción de Thompson más abajo.' });
  mostrarMensajes(mensajes);
  if (r.operacion) mostrarOperacion(r.operacion, 'thompson');
}
$('btn-crear').addEventListener('click', crear);

// ------------------------------------------------------------------ operaciones
function renderizarOperaciones() {
  $('lista-ops').innerHTML = OPERACIONES.map((o) =>
    `<button class="op" data-op="${o.id}"><strong>${esc(o.titulo)}</strong><small>${esc(o.desc)}</small></button>`).join('');
}
function actualizarOperaciones() {
  const tipo = estado.automata ? estado.automata.tipo : null;
  document.querySelectorAll('#lista-ops .op').forEach((b) => {
    const o = OPERACIONES.find((x) => x.id === b.dataset.op);
    const ok = !!tipo && o.aplica(tipo);
    b.disabled = !ok;
    b.title = ok ? '' : o.motivo || '';
  });
}
function marcarOperacion(id) {
  document.querySelectorAll('#lista-ops .op').forEach((b) => b.classList.toggle('activa', b.dataset.op === id));
}
function mostrarOperacion(operacion, id) {
  simulador.cerrar(false);
  diagrama.reiniciarLayouts(['actual']);
  visor.mostrar(operacion);
  marcarOperacion(id);
}
async function ejecutarOperacion(id) {
  if (!estado.automata) return;
  if (id === 'simular') {
    visor.cerrar(false);
    simulador.abrir();
    marcarOperacion('simular');
    $('titulo-diagrama').textContent = 'Simulación';
    $('tarjeta-simulacion').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    return;
  }
  const r = await llamar('operacion', { automata: estado.automata, operacion: id });
  if (!r.ok) { avisar(r.mensaje || 'No se pudo realizar la operación.', 'error'); return; }
  mostrarOperacion(r.operacion, id);
}
renderizarOperaciones();
$('lista-ops').addEventListener('click', (e) => {
  const b = e.target.closest('.op');
  if (b && !b.disabled) ejecutarOperacion(b.dataset.op);
});

function usarResultado(r) {
  if (r.er !== undefined) {
    visor.cerrar(false); mostrarActual(); marcarOperacion(null);
    fijarModo('ER'); $('er-texto').value = r.er;
    avisar('Expresión cargada. Pulsa «Crear autómata» para construirla con Thompson.');
    return;
  }
  editor.cargar(r);
  fijarModo(modoDeTipo(r.tipo));
  establecerAutomata(r);
  avisar('Autómata cargado en la definición: ya puedes seguir operando con él.');
}

// ------------------------------------------------------------------ ejemplos, archivos, dibujo
let listaEjemplos = { automatas: [], expresiones: [] };
(async () => {
  const r = await obtener('/api/ejemplos');
  if (!r.ok) return;
  listaEjemplos = r;
  const sel = $('ejemplos');
  sel.insertAdjacentHTML('beforeend',
    `<optgroup label="Autómatas de clase">${r.automatas.map((x, i) => `<option value="a:${i}">${esc(x.nombre)}</option>`).join('')}</optgroup>`
    + `<optgroup label="Expresiones regulares">${r.expresiones.map((x, i) => `<option value="e:${i}">${esc(x)}</option>`).join('')}</optgroup>`);
})();
$('ejemplos').addEventListener('change', (e) => {
  const v = e.target.value; e.target.value = '';
  if (!v) return;
  const i = Number(v.slice(2));
  if (v.startsWith('a:')) {
    const a = listaEjemplos.automatas[i].automata;
    editor.cargar(a); fijarModo(modoDeTipo(a.tipo));
    avisar('Ejemplo cargado en la tabla. Pulsa «Crear autómata».');
  } else {
    fijarModo('ER'); $('er-texto').value = listaEjemplos.expresiones[i];
    avisar('Expresión cargada. Pulsa «Crear autómata».');
  }
});

$('btn-guardar').addEventListener('click', () => {
  if (!estado.automata) { avisar('Primero crea un autómata.', 'error'); return; }
  descargar('automata.json', JSON.stringify(estado.automata, null, 2), 'application/json');
});
$('btn-abrir').addEventListener('click', () => $('archivo').click());
$('archivo').addEventListener('change', async (e) => {
  const archivo = e.target.files[0]; e.target.value = '';
  if (!archivo) return;
  try {
    const a = JSON.parse(await archivo.text());
    if (!Array.isArray(a.estados) || !Array.isArray(a.alfabeto) || !a.inicial || !Array.isArray(a.finales) || !Array.isArray(a.transiciones)) {
      throw new Error('formato');
    }
    editor.cargar(a); fijarModo(modoDeTipo(editor.modo === 'AFND-LAMBDA' ? 'AFND-λ' : editor.modo));
    avisar('Archivo abierto. Pulsa «Crear autómata».');
  } catch (err) {
    avisar('No se pudo leer el archivo: no tiene el formato de un autómata guardado.', 'error');
  }
});

$('btn-reorganizar').addEventListener('click', () => diagrama.reorganizar());
$('btn-ajustar').addEventListener('click', () => {
  $('btn-ajustar').textContent = diagrama.alternarAjuste() ? 'Tamaño real' : 'Ajustar a la vista';
});
$('btn-svg').addEventListener('click', () => {
  const svg = diagrama.exportarSVG();
  if (!svg) { avisar('No hay ningún dibujo para descargar.', 'error'); return; }
  descargar('diagrama.svg', svg, 'image/svg+xml');
});

fijarModo('AFD');
mostrarActual();
window.__laboratorio = { estado, editor, diagrama, visor, simulador };   // para depurar desde la consola
