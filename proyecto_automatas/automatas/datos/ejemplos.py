"""Autómatas de ejemplo tomados del material de clase.

Sirven como casos de prueba y como biblioteca precargada para la interfaz.
"""
from __future__ import annotations

from ..core.finitos import LAMBDA, Automata


def afd_intro_ab() -> Automata:
    """AFD de la introducción (Σ={a,b}, F={q0,q2}). Acepta 'aabab', rechaza 'aababa'."""
    return Automata.desde_transiciones(
        [("q0", "a", "q0"), ("q0", "b", "q1"),
         ("q1", "a", "q1"), ("q1", "b", "q2"),
         ("q2", "a", "q1"), ("q2", "b", "q1")],
        inicial="q0", finales={"q0", "q2"}, nombre="AFD de la introducción (a,b)")


def afd_intro_01() -> Automata:
    """AFD incompleto de la diapositiva 'Autómata finito' (Σ={0,1}, F={q2})."""
    return Automata.desde_transiciones(
        [("q0", "0", "q2"), ("q0", "1", "q1"),
         ("q1", "0", "q0"), ("q1", "1", "q2")],
        inicial="q0", finales={"q2"}, nombre="AFD incompleto (0,1)")


def afd_minimizacion_8_estados() -> Automata:
    """AFD de 8 estados de la clase de minimización (debe reducirse a 5 estados)."""
    return Automata.desde_transiciones(
        [("q0", "0", "q1"), ("q0", "1", "q5"),
         ("q1", "0", "q6"), ("q1", "1", "q2"),
         ("q2", "0", "q0"), ("q2", "1", "q2"),
         ("q3", "0", "q2"), ("q3", "1", "q6"),
         ("q4", "0", "q7"), ("q4", "1", "q5"),
         ("q5", "0", "q2"), ("q5", "1", "q6"),
         ("q6", "0", "q6"), ("q6", "1", "q4"),
         ("q7", "0", "q6"), ("q7", "1", "q2")],
        inicial="q0", finales={"q2"}, nombre="AFD de minimización (8 estados)")


def afnd_termina_en_01() -> Automata:
    """AFND clásico: cadenas binarias que terminan en '01'."""
    return Automata.desde_transiciones(
        [("q0", "0", "q0"), ("q0", "1", "q0"),
         ("q0", "0", "q1"), ("q1", "1", "q2")],
        inicial="q0", finales={"q2"}, nombre="AFND: termina en 01")


def afnd_lambda_a_estrella_b_estrella() -> Automata:
    """AFND-λ para a*b* (todas las 'a' antes de todas las 'b')."""
    return Automata.desde_transiciones(
        [("q0", "a", "q0"), ("q0", LAMBDA, "q1"), ("q1", "b", "q1")],
        inicial="q0", finales={"q1"}, nombre="AFND-λ: a*b*")


EJEMPLOS = {
    "AFD de la introducción (a,b)": afd_intro_ab,
    "AFD incompleto (0,1)": afd_intro_01,
    "AFD de minimización (8 estados)": afd_minimizacion_8_estados,
    "AFND: termina en 01": afnd_termina_en_01,
    "AFND-λ: a*b*": afnd_lambda_a_estrella_b_estrella,
}
