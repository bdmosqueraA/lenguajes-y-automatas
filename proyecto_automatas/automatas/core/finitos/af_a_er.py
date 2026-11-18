"""Autómata finito -> expresión regular por eliminación de estados.

1. Se agregan un estado inicial nuevo `ini` (con λ hacia q0) y un estado final
   nuevo `fin` (con λ desde cada estado de aceptación). Así hay un único inicial
   sin entradas y un único final sin salidas.
2. Cada arista lleva como etiqueta una expresión regular.
3. Se eliminan uno a uno los estados originales. Al eliminar q, por cada par
   p -> q y q -> r se agrega (o se une a la arista existente) la arista
   p -> r con la etiqueta  R(p,q) R(q,q)* R(q,r).
4. Al final, la etiqueta de la arista ini -> fin es la expresión regular.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import er as _er
from .modelo import LAMBDA, Automata, clave_natural


@dataclass(frozen=True)
class PasoEliminacion:
    estado: str | None       # estado eliminado (None en el paso inicial)
    descripcion: str
    aristas: dict            # {(origen, destino): texto de la ER} después del paso
    modificadas: tuple = ()  # pares (origen, destino) creados o cambiados en este paso


@dataclass
class ResultadoAFaER:
    er: object
    texto: str
    pasos: list
    ini: str = "ini"         # nombre del estado inicial agregado
    fin: str = "fin"         # nombre del estado final agregado


def _nombre_libre(base: str, usados) -> str:
    while base in usados:
        base += "'"
    return base


def a_er(automata: Automata) -> ResultadoAFaER:
    ini = _nombre_libre("ini", automata.estados)
    fin = _nombre_libre("fin", automata.estados | {ini})

    aristas: dict = {}

    def agregar(origen, destino, etiqueta):
        clave = (origen, destino)
        aristas[clave] = _er.unir(aristas.get(clave, _er.Vacio()), etiqueta)

    for origen, simbolo, destino in automata.transiciones():
        agregar(origen, destino, _er.Lambda() if simbolo == LAMBDA else _er.Simbolo(simbolo))
    agregar(ini, automata.inicial, _er.Lambda())
    for final in automata.finales:
        agregar(final, fin, _er.Lambda())

    def instantanea():
        return {clave: _er.a_texto(e) for clave, e in sorted(
            aristas.items(), key=lambda kv: (clave_natural(kv[0][0]), clave_natural(kv[0][1])))}

    pasos = [PasoEliminacion(
        None,
        f"Se agregan el estado inicial '{ini}' (λ hacia {automata.inicial}) y el final "
        f"'{fin}' (λ desde cada estado de aceptación).",
        instantanea())]

    pendientes = set(automata.estados)
    while pendientes:
        # Se elimina primero el estado que genera menos aristas nuevas.
        def costo(q):
            entran = sum(1 for (p, r) in aristas if r == q and p != q)
            salen = sum(1 for (p, r) in aristas if p == q and r != q)
            return (entran * salen, clave_natural(q))

        q = min(pendientes, key=costo)
        pendientes.discard(q)

        bucle = aristas.pop((q, q), None)
        estrella = _er.cerrar(bucle) if bucle is not None else _er.Lambda()
        entran = [(p, aristas.pop((p, q))) for (p, r) in list(aristas) if r == q]
        salen = [(r, aristas.pop((q, r))) for (p, r) in list(aristas) if p == q]

        lineas = []
        modificadas = []
        for p, e_pq in entran:
            for r, e_qr in salen:
                nueva = _er.concatenar(_er.concatenar(e_pq, estrella), e_qr)
                agregar(p, r, nueva)
                lineas.append(f"{p} → {r}: {_er.a_texto(aristas[(p, r)])}")
                if (p, r) not in modificadas:
                    modificadas.append((p, r))
        detalle = ("\n".join(lineas)) if lineas else "No se crean aristas nuevas."
        pasos.append(PasoEliminacion(q, f"Se elimina {q}.\n{detalle}", instantanea(),
                                     tuple(modificadas)))

    resultado = aristas.get((ini, fin), _er.Vacio())
    return ResultadoAFaER(resultado, _er.a_texto(resultado), pasos, ini, fin)
