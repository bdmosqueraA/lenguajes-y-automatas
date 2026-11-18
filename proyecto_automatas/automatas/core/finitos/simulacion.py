"""Simulación de autómatas finitos (AFD, AFND y AFND-λ) con traza paso a paso.

La simulación trabaja siempre con *conjuntos* de estados activos. Un AFD es el
caso particular en que el conjunto tiene un solo elemento, así que un único
algoritmo sirve para los tres tipos.
"""
from __future__ import annotations

from dataclasses import dataclass

from .modelo import LAMBDA, Automata, formato_conjunto


@dataclass(frozen=True)
class Paso:
    """Configuración del autómata después de leer `indice` símbolos."""
    indice: int            # 0 = configuración inicial (antes de leer nada)
    simbolo: str | None    # símbolo leído para llegar aquí (None en el paso 0)
    estados: frozenset     # estados activos (ya con λ-clausura aplicada)
    transiciones: frozenset  # (origen, símbolo, destino) recorridas en este paso


@dataclass(frozen=True)
class Traza:
    cadena: str
    pasos: tuple
    acepta: bool
    motivo: str

    def resumen(self) -> str:
        lineas = []
        for paso in self.pasos:
            if paso.simbolo is None:
                lineas.append(f"  {paso.indice}:      {formato_conjunto(paso.estados)}")
            else:
                lineas.append(f"  {paso.indice}: {paso.simbolo} -> {formato_conjunto(paso.estados)}")
        veredicto = "ACEPTADA" if self.acepta else "RECHAZADA"
        cadena = self.cadena if self.cadena else "λ (cadena vacía)"
        return f"'{cadena}' {veredicto}\n" + "\n".join(lineas) + f"\n  {self.motivo}"


def _clausura(automata: Automata, estados) -> tuple:
    """λ-clausura de un conjunto de estados.

    Devuelve (clausura, transiciones λ recorridas). La clausura incluye a los
    propios estados de partida y se calcula con una búsqueda que termina aunque
    haya ciclos de transiciones λ.
    """
    clausura = set(estados)
    usadas = set()
    pendientes = list(clausura)
    while pendientes:
        origen = pendientes.pop()
        for destino in automata.destinos(origen, LAMBDA):
            usadas.add((origen, LAMBDA, destino))
            if destino not in clausura:
                clausura.add(destino)
                pendientes.append(destino)
    return frozenset(clausura), frozenset(usadas)


def clausura_lambda(automata: Automata, estados) -> frozenset:
    """λ-clausura (clausura nula) de un estado o de un conjunto de estados."""
    if isinstance(estados, str):
        estados = [estados]
    return _clausura(automata, estados)[0]


def mover(automata: Automata, estados, simbolo: str) -> frozenset:
    """Estados alcanzables desde `estados` leyendo `simbolo` (sin λ-clausura)."""
    return frozenset(
        destino for estado in estados for destino in automata.destinos(estado, simbolo))


def ejecutar(automata: Automata, cadena: str) -> Traza:
    """Procesa `cadena` y devuelve la traza completa con el veredicto."""
    actuales, usadas = _clausura(automata, {automata.inicial})
    pasos = [Paso(0, None, actuales, usadas)]

    for indice, simbolo in enumerate(cadena, start=1):
        if simbolo not in automata.alfabeto:
            return Traza(cadena, tuple(pasos), False,
                         f"El símbolo '{simbolo}' (posición {indice}) no pertenece al alfabeto.")
        recorridas = {(o, simbolo, d) for o in actuales for d in automata.destinos(o, simbolo)}
        destinos = mover(automata, actuales, simbolo)
        actuales, lambdas = _clausura(automata, destinos)
        pasos.append(Paso(indice, simbolo, actuales, frozenset(recorridas) | lambdas))
        if not actuales:
            return Traza(cadena, tuple(pasos), False,
                         f"No hay transición con '{simbolo}' (posición {indice}): el autómata se bloquea.")

    aceptadores = actuales & automata.finales
    if aceptadores:
        motivo = f"Termina en {formato_conjunto(aceptadores)}, estado de aceptación."
    else:
        motivo = f"Termina en {formato_conjunto(actuales)}, sin estados de aceptación."
    return Traza(cadena, tuple(pasos), bool(aceptadores), motivo)


def acepta(automata: Automata, cadena: str) -> bool:
    return ejecutar(automata, cadena).acepta
