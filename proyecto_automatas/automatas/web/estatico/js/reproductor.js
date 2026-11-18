// Controles de reproducción reutilizables: inicio, atrás, play, siguiente, final, velocidad y barra de pasos.
export function htmlControles() {
  return `<div class="nav-pasos">
      <button class="icono" data-x="inicio" title="Primer paso">⏮</button><button class="icono" data-x="atras" title="Paso anterior">◀</button>
      <button class="icono principal" data-x="play" title="Reproducir">▶</button>
      <button class="icono" data-x="sig" title="Paso siguiente">▶</button><button class="icono" data-x="fin" title="Último paso">⏭</button>
      <span class="contador" data-x="contador">Sin ejecución</span>
      <span class="velocidad">velocidad <input type="range" data-x="vel"></span>
    </div>
    <input type="range" class="barra-pasos" data-x="barra" min="0" max="0" value="0" aria-label="Ir a un paso">`;
}

export class ControlReproductor {
  constructor(raiz, { alIr, velMin = 0.5, velMax = 4, velPaso = 0.5, velIni = 1.5 }) {
    this.alIr = alIr; this.total = 0; this.indice = 0; this.timer = null;
    const q = (x) => raiz.querySelector(`[data-x="${x}"]`);
    this.contador = q('contador'); this.botonPlay = q('play'); this.vel = q('vel'); this.barra = q('barra');
    Object.assign(this.vel, { min: velMin, max: velMax, step: velPaso, value: velIni });
    q('inicio').addEventListener('click', () => this.irA(0, true));
    q('atras').addEventListener('click', () => this.irA(this.indice - 1, true));
    q('sig').addEventListener('click', () => this.irA(this.indice + 1, true));
    q('fin').addEventListener('click', () => this.irA(this.total - 1, true));
    this.botonPlay.addEventListener('click', () => this.alternar());
    this.vel.addEventListener('input', () => { if (this.timer) { this.parar(); this.alternar(); } });
    this.barra.addEventListener('input', () => this.irA(Number(this.barra.value), true));
  }

  configurar(total) {
    this.parar(); this.total = total; this.indice = 0;
    this.barra.max = Math.max(0, total - 1); this.barra.value = 0;
    this.contador.textContent = total ? `Paso 0 de ${total - 1}` : 'Sin ejecución';
  }

  irA(i, manual) {
    if (!this.total) return;
    if (manual) this.parar();
    this.indice = Math.min(Math.max(i, 0), this.total - 1);
    this.barra.value = this.indice;
    this.contador.textContent = `Paso ${this.indice} de ${this.total - 1}`;
    this.alIr(this.indice);
  }

  alternar() {
    if (!this.total) return false;
    if (this.timer) { this.parar(); return false; }
    if (this.total <= 1) return false;
    if (this.indice >= this.total - 1) this.irA(0, false);
    this.botonPlay.textContent = '⏸';
    this.timer = setInterval(() => {
      this.irA(this.indice + 1, false);
      if (this.indice >= this.total - 1) this.parar();
    }, 1000 / Number(this.vel.value));
    return true;
  }

  parar() {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    if (this.botonPlay) this.botonPlay.textContent = '▶';
  }
}
