"""Pruebas del Día 6 (parte finitos): AF → ER por eliminación de estados y complemento."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.finitos import Automata, a_er, acepta, analizar, complemento, thompson
from automatas.datos import ejemplos
from tests.utiles import cadenas, iguala_regex, iguales


def test_a_er_de_todos_los_ejemplos():
    for nombre, fabrica in ejemplos.EJEMPLOS.items():
        a = fabrica()
        r = a_er(a)
        nodo = analizar(r.texto)                       # el texto producido se puede volver a leer
        iguala_regex(a, nodo, largo_max=7)             # y describe el lenguaje original
        iguales(a, thompson(nodo, a.alfabeto).automata)


def test_a_er_casos_pequenos():
    solo_lambda = Automata.desde_transiciones([], "q0", {"q0"}, alfabeto=set())
    assert a_er(solo_lambda).texto == "λ"
    nada = Automata.desde_transiciones([("q0", "a", "q1")], "q0", set())
    assert a_er(nada).texto == "∅"
    a_estrella = Automata.desde_transiciones([("q0", "a", "q0")], "q0", {"q0"})
    assert a_er(a_estrella).texto == "a*"
    una_a = Automata.desde_transiciones([("q0", "a", "q1")], "q0", {"q1"})
    assert a_er(una_a).texto == "a"


def test_a_er_pasos():
    a = ejemplos.afd_intro_ab()
    r = a_er(a)
    assert len(r.pasos) == len(a.estados) + 1
    assert r.pasos[0].estado is None and r.pasos[-1].estado is not None
    assert ("ini", "fin") in r.pasos[-1].aristas


def test_a_er_no_se_confunde_con_estados_llamados_ini():
    a = Automata.desde_transiciones([("ini", "a", "fin")], "ini", {"fin"})
    assert a_er(a).texto == "a"


def test_complemento_de_todos_los_ejemplos():
    for nombre, fabrica in ejemplos.EJEMPLOS.items():
        a = fabrica()
        c = complemento(a)
        assert c.es_completo()
        for cadena in cadenas(a.alfabeto, 7):
            assert acepta(c, cadena) != acepta(a, cadena), (nombre, cadena)


def test_doble_complemento():
    for fabrica in (ejemplos.afd_intro_01, ejemplos.afnd_termina_en_01):
        a = fabrica()
        iguales(a, complemento(complemento(a)))
