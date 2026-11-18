"""Construcción de Thompson: expresión regular -> AFND-λ.

Cada subexpresión se convierte en un fragmento con un único estado inicial y un
único estado final, que luego se combina según el operador:

    símbolo a      i --a--> f
    λ              i --λ--> f
    ∅              i  f            (sin transiciones)
    A | B          nuevo i, nuevo f;  i -λ-> inicio(A), inicio(B);  fin(A), fin(B) -λ-> f
    A B            fin(A) -λ-> inicio(B)
    A*             nuevo i, nuevo f;  i -λ-> inicio(A);  fin(A) -λ-> inicio(A);
                   fin(A) -λ-> f;  i -λ-> f
    A+             igual que A* pero sin el atajo  i -λ-> f

Los estados se numeran q0, q1, ... de modo que q0 es siempre el estado inicial.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import er as _er
from .modelo import LAMBDA, Automata


@dataclass(frozen=True)
class PasoThompson:
    descripcion: str
    estados: tuple          # estados creados en este paso
    transiciones: tuple     # transiciones agregadas en este paso
    inicio: str = ""        # estado inicial del fragmento construido en este paso
    fin: str = ""           # estado final de ese fragmento


@dataclass
class ResultadoThompson:
    er: object              # árbol de la expresión
    texto: str
    automata: Automata
    pasos: list


class _Constructor:
    def __init__(self):
        self.contador = 0
        self.transiciones = []
        self.pasos = []

    def estado(self) -> str:
        nombre = f"q{self.contador}"
        self.contador += 1
        return nombre

    def registrar(self, descripcion, estados, transiciones, inicio="", fin=""):
        self.transiciones.extend(transiciones)
        self.pasos.append(PasoThompson(descripcion, tuple(estados), tuple(transiciones), inicio, fin))

    def construir(self, nodo) -> tuple:
        """Devuelve (estado inicial, estado final) del fragmento."""
        if isinstance(nodo, _er.Simbolo):
            i, f = self.estado(), self.estado()
            self.registrar(f"Símbolo '{nodo.c}': {i} —{nodo.c}→ {f}", (i, f), [(i, nodo.c, f)], i, f)
            return i, f
        if isinstance(nodo, _er.Lambda):
            i, f = self.estado(), self.estado()
            self.registrar(f"λ: {i} —λ→ {f}", (i, f), [(i, LAMBDA, f)], i, f)
            return i, f
        if isinstance(nodo, _er.Vacio):
            i, f = self.estado(), self.estado()
            self.registrar(f"∅: dos estados ({i}, {f}) sin transiciones entre ellos", (i, f), [], i, f)
            return i, f

        texto = _er.a_texto(nodo)
        if isinstance(nodo, _er.Union):
            i = self.estado()
            ai, af = self.construir(nodo.izq)
            bi, bf = self.construir(nodo.der)
            f = self.estado()
            self.registrar(
                f"Unión ({texto}): nuevo inicio {i} con λ hacia {ai} y {bi}; "
                f"λ desde {af} y {bf} hacia el nuevo fin {f}",
                (i, f),
                [(i, LAMBDA, ai), (i, LAMBDA, bi), (af, LAMBDA, f), (bf, LAMBDA, f)], i, f)
            return i, f
        if isinstance(nodo, _er.Concat):
            ai, af = self.construir(nodo.izq)
            bi, bf = self.construir(nodo.der)
            self.registrar(f"Concatenación ({texto}): λ de {af} a {bi}", (),
                           [(af, LAMBDA, bi)], ai, bf)
            return ai, bf
        if isinstance(nodo, _er.Estrella):
            i = self.estado()
            ai, af = self.construir(nodo.e)
            f = self.estado()
            self.registrar(
                f"Estrella ({texto}): nuevo inicio {i} y fin {f}; λ de {i} a {ai}, "
                f"de {af} a {ai}, de {af} a {f} y de {i} a {f} (para aceptar la cadena vacía)",
                (i, f),
                [(i, LAMBDA, ai), (af, LAMBDA, ai), (af, LAMBDA, f), (i, LAMBDA, f)], i, f)
            return i, f
        if isinstance(nodo, _er.Mas):
            i = self.estado()
            ai, af = self.construir(nodo.e)
            f = self.estado()
            self.registrar(
                f"Cierre positivo ({texto}): nuevo inicio {i} y fin {f}; λ de {i} a {ai}, "
                f"de {af} a {ai} y de {af} a {f}",
                (i, f),
                [(i, LAMBDA, ai), (af, LAMBDA, ai), (af, LAMBDA, f)], i, f)
            return i, f
        raise TypeError(f"Nodo desconocido: {nodo!r}")


def thompson(er, alfabeto=None) -> ResultadoThompson:
    """Construye el AFND-λ de una expresión regular (texto o árbol).

    `alfabeto` permite agregar símbolos que no aparecen en la expresión.
    """
    nodo = _er.analizar(er) if isinstance(er, str) else er
    texto = _er.a_texto(nodo)
    constructor = _Constructor()
    inicio, fin = constructor.construir(nodo)
    automata = Automata.desde_transiciones(
        constructor.transiciones, inicio, {fin},
        estados={f"q{k}" for k in range(constructor.contador)},
        alfabeto=_er.simbolos(nodo) | set(alfabeto or ()),
        nombre=f"Thompson: {texto}")
    return ResultadoThompson(nodo, texto, automata, constructor.pasos)
