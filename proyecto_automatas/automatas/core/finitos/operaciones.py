"""Operaciones sobre autómatas finitos."""
from __future__ import annotations

from .conversiones import a_afd, completar
from .modelo import Automata


def complemento(automata: Automata) -> Automata:
    """Autómata que acepta exactamente las cadenas de Σ* que `automata` rechaza.

    Si el autómata no es un AFD se convierte primero; después se completa
    (estado trampa) y se intercambian los estados de aceptación y de no aceptación.
    """
    afd = automata if automata.es_determinista() else a_afd(automata).afd
    completo = completar(afd)
    nombre = f"complemento de {automata.nombre}" if automata.nombre else "complemento"
    return Automata(completo.estados, completo.alfabeto, completo.delta, completo.inicial,
                    completo.estados - completo.finales, nombre)
