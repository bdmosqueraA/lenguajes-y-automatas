"""Minimización de AFD por refinamiento de particiones (método de la clase).

Se parte de dos conjuntos: estados de aceptación y de no aceptación. En cada
iteración se mira a qué conjunto lleva cada símbolo desde cada estado; los
estados de un mismo conjunto con "filas" distintas se separan. El proceso
termina cuando una iteración no crea conjuntos nuevos.
"""
from __future__ import annotations

from dataclasses import dataclass

from .conversiones import completar, eliminar_inaccesibles, estados_accesibles
from .modelo import Automata, OperacionInvalida, clave_natural, formato_conjunto

_LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _etiqueta(i: int) -> str:
    vuelta = i // len(_LETRAS)
    return _LETRAS[i % len(_LETRAS)] + (str(vuelta) if vuelta else "")


def _menor(bloque) -> list:
    return clave_natural(min(bloque, key=clave_natural))


@dataclass(frozen=True)
class Iteracion:
    """Una iteración del refinamiento (la 0 es la partición inicial)."""
    numero: int
    previa: tuple          # bloques de la partición anterior (vacío en la iteración 0)
    etiquetas_previas: tuple
    tabla: dict            # estado -> etiquetas de los bloques a los que lleva cada símbolo
    bloques: tuple         # partición resultante
    etiquetas: tuple

    def resumen(self, simbolos=()) -> str:
        lineas = []
        if self.numero == 0:
            lineas.append("Partición inicial (aceptación / no aceptación):")
        else:
            lineas.append(f"Iteración {self.numero}. Partición anterior: " + "  ".join(
                f"{e}={formato_conjunto(b)}" for e, b in zip(self.etiquetas_previas, self.previa)))
            encabezado = "  estado | " + " ".join(f"{s:>3}" for s in simbolos)
            lineas.append(encabezado)
            for estado in sorted(self.tabla, key=clave_natural):
                fila = " ".join(f"{e:>3}" for e in self.tabla[estado])
                lineas.append(f"  {estado:<6} | {fila}")
            lineas.append("Partición resultante:")
        lineas.append("  " + "  ".join(
            f"{e}={formato_conjunto(b)}" for e, b in zip(self.etiquetas, self.bloques)))
        return "\n".join(lineas)


@dataclass
class ResultadoMinimizacion:
    original: Automata
    preparado: Automata        # tras quitar inaccesibles y completar (lo que se minimizó)
    minimo: Automata
    inaccesibles: frozenset    # estados eliminados por inaccesibles
    trampa: str | None         # estado trampa agregado (None si no hizo falta)
    iteraciones: list
    clases: tuple              # bloques finales de estados equivalentes


def _sin_estado(automata: Automata, estado: str) -> Automata:
    delta = {(o, s): d - {estado} for (o, s), d in automata.delta.items() if o != estado}
    return Automata(automata.estados - {estado}, automata.alfabeto, delta,
                    automata.inicial, automata.finales - {estado}, automata.nombre)


def minimizar(automata: Automata, quitar_inaccesibles: bool = True,
              ocultar_trampa: bool = True) -> ResultadoMinimizacion:
    """Minimiza un AFD.

    * quitar_inaccesibles: elimina antes los estados inalcanzables desde q0.
      Con False se replica exactamente el procedimiento de la clase.
    * ocultar_trampa: si el AFD era incompleto, se completa para minimizar y
      después se oculta el estado muerto, de modo que el resultado vuelve a ser
      un AFD sin transiciones hacia un estado trampa.
    """
    if not automata.es_determinista():
        raise OperacionInvalida(
            "Para minimizar hace falta un AFD. Convierta primero el autómata con a_afd.")

    trabajo = automata.copia()
    inaccesibles = frozenset()
    if quitar_inaccesibles:
        inaccesibles = frozenset(trabajo.estados - estados_accesibles(trabajo))
        if inaccesibles:
            trabajo = eliminar_inaccesibles(trabajo)

    trampa = None
    if not trabajo.es_completo():
        completo = completar(trabajo)
        trampa = next(iter(completo.estados - trabajo.estados))
        trabajo = completo

    simbolos = sorted(trabajo.alfabeto)
    siguiente = lambda q, a: next(iter(trabajo.destinos(q, a)))

    inicial = tuple(b for b in (frozenset(trabajo.finales),
                                frozenset(trabajo.estados - trabajo.finales)) if b)
    etiquetas = lambda bloques: tuple(_etiqueta(i) for i in range(len(bloques)))
    iteraciones = [Iteracion(0, (), (), {}, inicial, etiquetas(inicial))]

    while True:
        previa = iteraciones[-1]
        indice = {q: i for i, bloque in enumerate(previa.bloques) for q in bloque}
        tabla = {q: tuple(previa.etiquetas[indice[siguiente(q, a)]] for a in simbolos)
                 for q in trabajo.estados}
        grupos: dict = {}
        for q in sorted(trabajo.estados, key=clave_natural):
            firma = (indice[q], tuple(indice[siguiente(q, a)] for a in simbolos))
            grupos.setdefault(firma, set()).add(q)
        nuevos = tuple(sorted((frozenset(g) for g in grupos.values()), key=_menor))
        iteraciones.append(Iteracion(previa.numero + 1, previa.bloques, previa.etiquetas,
                                     tabla, nuevos, etiquetas(nuevos)))
        if len(nuevos) == len(previa.bloques):
            break

    bloques = iteraciones[-1].bloques
    nombre = {b: (next(iter(b)) if len(b) == 1 else formato_conjunto(b)) for b in bloques}
    bloque_de = {q: b for b in bloques for q in b}
    delta = {}
    for bloque in bloques:
        representante = min(bloque, key=clave_natural)
        for simbolo in simbolos:
            delta[(nombre[bloque], simbolo)] = {nombre[bloque_de[siguiente(representante, simbolo)]]}
    minimo = Automata(
        set(nombre.values()), trabajo.alfabeto, delta,
        nombre[bloque_de[trabajo.inicial]],
        {nombre[b] for b in bloques if b & trabajo.finales},
        f"{automata.nombre} (mínimo)" if automata.nombre else "AFD mínimo")

    if ocultar_trampa and trampa is not None:
        muerto = nombre[bloque_de[trampa]]
        if muerto != minimo.inicial:        # si el lenguaje es vacío no hay nada que ocultar
            minimo = _sin_estado(minimo, muerto)

    return ResultadoMinimizacion(automata, trabajo, minimo, inaccesibles, trampa,
                                 iteraciones, bloques)
