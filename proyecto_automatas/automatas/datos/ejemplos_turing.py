"""Máquinas de Turing de los apuntes y las diapositivas de clase."""
from __future__ import annotations

from ..core.turing import MaquinaTuring


def mt_omega_c_omega_1_cinta() -> MaquinaTuring:
    """L = { ω c ω : ω ∈ {a,b}* } con una cinta (tabla δ1' de los apuntes)."""
    return MaquinaTuring.desde_transiciones(
        [("e0", "a", "e2", "X", "D"), ("e0", "b", "e5", "X", "D"), ("e0", "c", "e7", "c", "D"),
         ("e1", "a", "e2", "X", "D"), ("e1", "b", "e5", "X", "D"), ("e1", "c", "e8", "c", "D"),
         ("e2", "a", "e2", "a", "D"), ("e2", "b", "e2", "b", "D"), ("e2", "c", "e3", "c", "D"),
         ("e3", "a", "e4", "Y", "I"), ("e3", "Y", "e3", "Y", "D"),
         ("e4", "a", "e4", "a", "I"), ("e4", "b", "e4", "b", "I"), ("e4", "c", "e4", "c", "I"),
         ("e4", "Y", "e4", "Y", "I"), ("e4", "X", "e1", "X", "D"),
         ("e5", "a", "e5", "a", "D"), ("e5", "b", "e5", "b", "D"), ("e5", "c", "e6", "c", "D"),
         ("e6", "b", "e4", "Y", "I"), ("e6", "Y", "e6", "Y", "D"),
         ("e7", "B", "e9", "B", "N"),
         ("e8", "Y", "e8", "Y", "D"), ("e8", "B", "e9", "B", "N")],
        inicial="e0", finales={"e9"}, entrada={"a", "b", "c"}, nombre="ω c ω (1 cinta)")


def mt_omega_c_omega_2_cintas() -> MaquinaTuring:
    """La misma lengua con dos cintas (tabla δ1 de los apuntes): copia ω a la cinta 2 y compara."""
    return MaquinaTuring.desde_transiciones(
        [("e0", "aB", "e1", "aX", "ND"), ("e0", "bB", "e1", "bX", "ND"), ("e0", "cB", "e3", "cB", "DN"),
         ("e1", "aB", "e1", "aa", "DD"), ("e1", "bB", "e1", "bb", "DD"), ("e1", "cB", "e2", "cB", "NI"),
         ("e2", "ca", "e2", "ca", "NI"), ("e2", "cb", "e2", "cb", "NI"), ("e2", "cX", "e3", "cX", "DD"),
         ("e3", "bb", "e3", "bb", "DD"), ("e3", "aa", "e3", "aa", "DD"), ("e3", "BB", "e4", "BB", "NN")],
        inicial="e0", finales={"e4"}, entrada={"a", "b", "c"}, cintas=2, nombre="ω c ω (2 cintas)")


def mt_an_bn_cn_2_cintas() -> MaquinaTuring:
    """L = { aⁿbⁿcⁿ : n ≥ 0 } con dos cintas: la cinta 2 es un contador (Z marca el inicio)."""
    return MaquinaTuring.desde_transiciones(
        [("q0", "aB", "q1", "aZ", "ND"), ("q0", "bB", "q1", "bZ", "ND"), ("q0", "cB", "q1", "cZ", "ND"),
         ("q0", "BB", "q4", "BB", "NN"),
         ("q1", "aB", "q1", "aX", "DD"), ("q1", "bB", "q2", "bB", "NI"),
         ("q2", "bX", "q2", "bX", "DI"), ("q2", "cZ", "q3", "cZ", "ND"),
         ("q3", "cX", "q3", "cX", "DD"), ("q3", "BB", "q4", "BB", "NN")],
        inicial="q0", finales={"q4"}, entrada={"a", "b", "c"}, cintas=2, nombre="aⁿbⁿcⁿ (2 cintas)")


def mt_complemento_a_uno_multipista() -> MaquinaTuring:
    """Multipista de 2 pistas: la entrada binaria está en la pista 1 y el complemento
    a uno se escribe en la pista 2 (ejemplo de las diapositivas de multipista)."""
    return MaquinaTuring.desde_transiciones(
        [("q1", "0B", "q1", "01", "D"), ("q1", "1B", "q1", "10", "D"), ("q1", "BB", "qf", "BB", "N")],
        inicial="q1", finales={"qf"}, entrada={"0", "1"}, cinta={"0", "1", "B"},
        pistas=2, nombre="Complemento a uno (multipista)")


EJEMPLOS_TURING = {
    "ω c ω (1 cinta)": mt_omega_c_omega_1_cinta,
    "ω c ω (2 cintas)": mt_omega_c_omega_2_cintas,
    "aⁿbⁿcⁿ (2 cintas)": mt_an_bn_cn_2_cintas,
    "Complemento a uno (multipista)": mt_complemento_a_uno_multipista,
}
