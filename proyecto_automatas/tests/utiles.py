"""Herramientas comunes para las pruebas (comparación de lenguajes por fuerza bruta)."""
import itertools
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.finitos import acepta, er  # noqa: E402


def cadenas(alfabeto, largo_max):
    """Todas las cadenas sobre `alfabeto` de longitud 0..largo_max."""
    simbolos = sorted(alfabeto)
    yield ""
    for largo in range(1, largo_max + 1):
        for tupla in itertools.product(simbolos, repeat=largo):
            yield "".join(tupla)


def espera_error(tipo, funcion, contiene=""):
    try:
        funcion()
    except tipo as error:
        assert contiene.lower() in str(error).lower(), f"mensaje inesperado: {error}"
        return
    raise AssertionError(f"Se esperaba {tipo.__name__} y no se lanzó")


def iguales(a, b, largo_max=7):
    """Dos autómatas aceptan exactamente las mismas cadenas (hasta cierta longitud)."""
    for cadena in cadenas(a.alfabeto | b.alfabeto, largo_max):
        assert acepta(a, cadena) == acepta(b, cadena), f"difieren en {cadena!r}"


def a_regex(nodo) -> str:
    """Traduce el árbol de una ER a una expresión de `re` de Python (oráculo independiente)."""
    if isinstance(nodo, er.Simbolo):
        return re.escape(nodo.c)
    if isinstance(nodo, er.Lambda):
        return "(?:)"
    if isinstance(nodo, er.Vacio):
        return "(?!)"
    if isinstance(nodo, er.Union):
        return f"(?:{a_regex(nodo.izq)}|{a_regex(nodo.der)})"
    if isinstance(nodo, er.Concat):
        return f"(?:{a_regex(nodo.izq)})(?:{a_regex(nodo.der)})"
    if isinstance(nodo, er.Estrella):
        return f"(?:{a_regex(nodo.e)})*"
    if isinstance(nodo, er.Mas):
        return f"(?:{a_regex(nodo.e)})+"
    raise TypeError(nodo)


def iguala_regex(automata, nodo, largo_max=7):
    """El autómata acepta exactamente el lenguaje de la ER (según `re`)."""
    patron = re.compile(a_regex(nodo))
    for cadena in cadenas(automata.alfabeto | er.simbolos(nodo), largo_max):
        esperado = patron.fullmatch(cadena) is not None
        assert acepta(automata, cadena) == esperado, f"difieren en {cadena!r}"
