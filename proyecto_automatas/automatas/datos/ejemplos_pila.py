"""Autómatas de pila de las diapositivas de clase y ejercicios típicos."""
from __future__ import annotations

from ..core.pila import AutomataPila


def ap_clase_a_n_b_m() -> AutomataPila:
    """AP del ejemplo de clase: δ(q0,a,λ)=(q0,A); δ(q0,b,A)=(q1,λ); δ(q1,b,A)=(q1,λ),
    F={q0,q1}, pila inicial vacía. Acepta aⁿbᵐ con m ≤ n (por estado final)."""
    return AutomataPila.desde_transiciones(
        [("q0", "a", "", "q0", "A"), ("q0", "b", "A", "q1", ""), ("q1", "b", "A", "q1", "")],
        inicial="q0", finales={"q0", "q1"}, simbolo_inicial="",
        nombre="AP de clase (aⁿbᵐ, m ≤ n)")


def ap_an_bn_estado_final() -> AutomataPila:
    """L = {aⁿbⁿ : n ≥ 1}, aceptación por estado final."""
    return AutomataPila.desde_transiciones(
        [("q0", "a", "Z", "q0", "AZ"), ("q0", "a", "A", "q0", "AA"),
         ("q0", "b", "A", "q1", ""), ("q1", "b", "A", "q1", ""),
         ("q1", "", "Z", "q2", "Z")],
        inicial="q0", finales={"q2"}, nombre="aⁿbⁿ (estado final)")


def ap_an_bn_pila_vacia() -> AutomataPila:
    """L = {aⁿbⁿ : n ≥ 1}, aceptación por pila vacía."""
    return AutomataPila.desde_transiciones(
        [("q0", "a", "Z", "q0", "AZ"), ("q0", "a", "A", "q0", "AA"),
         ("q0", "b", "A", "q1", ""), ("q1", "b", "A", "q1", ""),
         ("q1", "", "Z", "q1", "")],
        inicial="q0", modo="pila_vacia", nombre="aⁿbⁿ (pila vacía)")


def ap_palindromos_pares() -> AutomataPila:
    """Ejercicio de clase: L = {w wᴿ : w ∈ {0,1}*}. No determinista: adivina el centro."""
    trans = []
    for leido in "01":
        for cima in "Z01":
            trans.append(("q0", leido, cima, "q0", leido + cima))      # apila lo leído
    for cima in "Z01":
        trans.append(("q0", "", cima, "q1", cima))                     # adivina el centro
    for c in "01":
        trans.append(("q1", c, c, "q1", ""))                           # compara y desapila
    trans.append(("q1", "", "Z", "q2", "Z"))
    return AutomataPila.desde_transiciones(trans, inicial="q0", finales={"q2"},
                                           nombre="Palíndromos pares (w wᴿ)")


def ap_parentesis_balanceados() -> AutomataPila:
    """Paréntesis bien balanceados. Con Z en la cima, la transición λ hacia q1 compite con la
    que lee '(', así que por la definición estricta es no determinista (la ejecución es correcta)."""
    return AutomataPila.desde_transiciones(
        [("q0", "(", "Z", "q0", "(Z"), ("q0", "(", "(", "q0", "(("),
         ("q0", ")", "(", "q0", ""), ("q0", "", "Z", "q1", "Z")],
        inicial="q0", finales={"q1"}, nombre="Paréntesis balanceados")


EJEMPLOS_PILA = {
    "AP de clase (aⁿbᵐ, m ≤ n)": ap_clase_a_n_b_m,
    "aⁿbⁿ (estado final)": ap_an_bn_estado_final,
    "aⁿbⁿ (pila vacía)": ap_an_bn_pila_vacia,
    "Palíndromos pares (w wᴿ)": ap_palindromos_pares,
    "Paréntesis balanceados": ap_parentesis_balanceados,
}
