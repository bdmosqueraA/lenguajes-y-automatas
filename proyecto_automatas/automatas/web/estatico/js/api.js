// Llamadas al servidor Python.
export async function llamar(accion, datos) {
  try {
    const r = await fetch(`/api/${accion}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(datos ?? {}),
    });
    return await r.json();
  } catch (e) {
    return { ok: false, mensaje: 'No se pudo contactar con el servidor. ¿Sigue abierto el programa (python main.py)?' };
  }
}

export async function obtener(ruta) {
  try { return await (await fetch(ruta)).json(); } catch (e) { return { ok: false }; }
}
