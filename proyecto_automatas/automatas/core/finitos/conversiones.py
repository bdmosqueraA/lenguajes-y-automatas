"""Conversiones entre tipos de autómata finito.

* a_afd              : AFND / AFND-λ  ->  AFD (construcción de subconjuntos).
* completar          : AFD incompleto ->  AFD completo (agrega estado trampa).
* renombrar_estados  : renombra los estados como q0, q1, ... en orden de descubrimiento.
* eliminar_inaccesibles : quita los estados a los que no se puede llegar desde q0.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .modelo import LAMBDA, Automata, OperacionInvalida, clave_natural, formato_conjunto
from .simulacion import clausura_lambda, mover


# ---------------------------------------------------------------------- #
# AFND(-λ) -> AFD
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class FilaSubconjuntos:
    """Una fila de la tabla de la construcción de subconjuntos."""
    origen: frozenset     # subconjunto que se procesa
    simbolo: str
    mover: frozenset      # mover(origen, símbolo)
    destino: frozenset    # λ-clausura(mover)  (vacío si no hay transición)
    nuevo: bool           # el destino aparece por primera vez en esta fila


@dataclass
class ResultadoConversion:
    original: Automata
    afd: Automata
    subconjuntos: dict    # nombre del estado del AFD -> frozenset de estados originales
    clausura_inicial: frozenset
    filas: list           # FilaSubconjuntos, en el orden en que se calcularon


def a_afd(automata: Automata, renombrar: bool = False) -> ResultadoConversion:
    """Construcción de subconjuntos con λ-clausura.

    El AFD resultante puede ser incompleto: el subconjunto vacío (estado trampa)
    no se agrega; use `completar` si lo necesita.
    Con `renombrar=True` los estados quedan como q0, q1, ... (el diccionario
    `subconjuntos` conserva a qué subconjunto corresponde cada uno).
    """
    simbolos = sorted(automata.alfabeto)
    inicial = clausura_lambda(automata, {automata.inicial})
    orden = [inicial]
    descubiertos = {inicial}
    cola = deque([inicial])
    filas = []
    transiciones = {}

    while cola:
        origen = cola.popleft()
        for simbolo in simbolos:
            movido = mover(automata, origen, simbolo)
            destino = clausura_lambda(automata, movido) if movido else frozenset()
            nuevo = bool(destino) and destino not in descubiertos
            filas.append(FilaSubconjuntos(origen, simbolo, movido, destino, nuevo))
            if destino:
                transiciones[(origen, simbolo)] = destino
                if nuevo:
                    descubiertos.add(destino)
                    orden.append(destino)
                    cola.append(destino)

    nombre_de = {subconjunto: formato_conjunto(subconjunto) for subconjunto in orden}
    delta = {(nombre_de[o], s): {nombre_de[d]} for (o, s), d in transiciones.items()}
    titulo = f"AFD de {automata.nombre}" if automata.nombre else "AFD (subconjuntos)"
    afd = Automata(
        set(nombre_de.values()), automata.alfabeto, delta,
        nombre_de[inicial],
        {nombre_de[s] for s in orden if s & automata.finales},
        titulo)
    subconjuntos = {nombre_de[s]: s for s in orden}

    if renombrar:
        afd, mapa = renombrar_estados(afd)
        subconjuntos = {mapa[nombre]: s for nombre, s in subconjuntos.items()}
    return ResultadoConversion(automata, afd, subconjuntos, inicial, filas)


# ---------------------------------------------------------------------- #
# Utilidades sobre AFD
# ---------------------------------------------------------------------- #
def completar(automata: Automata, trampa: str = "∅") -> Automata:
    """Agrega un estado trampa para que el AFD tenga todas sus transiciones."""
    if not automata.es_determinista():
        raise OperacionInvalida("Solo se puede completar un AFD (sin λ ni no determinismo).")
    if automata.es_completo():
        return automata.copia()
    while trampa in automata.estados:
        trampa += "'"
    delta = {clave: set(destinos) for clave, destinos in automata.delta.items()}
    for estado in automata.estados | {trampa}:
        for simbolo in automata.alfabeto:
            delta.setdefault((estado, simbolo), {trampa})
    return Automata(automata.estados | {trampa}, automata.alfabeto, delta,
                    automata.inicial, automata.finales, automata.nombre)


def estados_accesibles(automata: Automata) -> frozenset:
    """Estados a los que se puede llegar desde el inicial (contando transiciones λ)."""
    vistos = {automata.inicial}
    cola = deque([automata.inicial])
    simbolos = sorted(automata.alfabeto) + [LAMBDA]
    while cola:
        estado = cola.popleft()
        for simbolo in simbolos:
            for destino in automata.destinos(estado, simbolo):
                if destino not in vistos:
                    vistos.add(destino)
                    cola.append(destino)
    return frozenset(vistos)


def eliminar_inaccesibles(automata: Automata) -> Automata:
    accesibles = estados_accesibles(automata)
    delta = {(o, s): set(d) for (o, s), d in automata.delta.items() if o in accesibles}
    return Automata(accesibles, automata.alfabeto, delta, automata.inicial,
                    automata.finales & accesibles, automata.nombre)


def renombrar_estados(automata: Automata, prefijo: str = "q") -> tuple:
    """Renombra los estados q0, q1, ... en orden de búsqueda a lo ancho desde el inicial.

    Devuelve (autómata renombrado, diccionario estado_viejo -> estado_nuevo).
    """
    simbolos = sorted(automata.alfabeto) + [LAMBDA]
    orden = []
    vistos = {automata.inicial}
    cola = deque([automata.inicial])
    while cola:
        estado = cola.popleft()
        orden.append(estado)
        for simbolo in simbolos:
            for destino in sorted(automata.destinos(estado, simbolo), key=clave_natural):
                if destino not in vistos:
                    vistos.add(destino)
                    cola.append(destino)
    orden += sorted(automata.estados - vistos, key=clave_natural)   # inaccesibles al final
    mapa = {viejo: f"{prefijo}{i}" for i, viejo in enumerate(orden)}
    delta = {(mapa[o], s): {mapa[d] for d in destinos}
             for (o, s), destinos in automata.delta.items()}
    nuevo = Automata(set(mapa.values()), automata.alfabeto, delta, mapa[automata.inicial],
                     {mapa[q] for q in automata.finales}, automata.nombre)
    return nuevo, mapa
