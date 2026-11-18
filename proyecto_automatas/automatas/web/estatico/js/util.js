// Utilidades compartidas por todas las pantallas.
export const $ = (id) => document.getElementById(id);
export const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function avisar(texto, tipo = 'info') {
  const el = document.createElement('div');
  el.className = `aviso-flotante ${tipo === 'error' ? 'error' : ''}`;
  el.textContent = texto;
  $('avisos').appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

export function descargar(nombre, contenido, tipo) {
  const url = URL.createObjectURL(new Blob([contenido], { type: tipo }));
  const a = document.createElement('a');
  a.href = url; a.download = nombre; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
