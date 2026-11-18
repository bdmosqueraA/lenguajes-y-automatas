"""Flujo completo: expresión regular -> AFND-λ -> AFD -> AFD mínimo."""
from __future__ import annotations

from dataclasses import dataclass

from .conversiones import ResultadoConversion, a_afd, renombrar_estados
from .minimizacion import ResultadoMinimizacion, minimizar
from .modelo import Automata
from .thompson import ResultadoThompson, thompson


@dataclass
class ResultadoPipeline:
    thompson: ResultadoThompson
    conversion: ResultadoConversion
    minimizacion: ResultadoMinimizacion
    afd_minimo: Automata       # el mínimo con estados q0, q1, ...


def er_a_afd_minimo(er, alfabeto=None) -> ResultadoPipeline:
    paso_thompson = thompson(er, alfabeto)
    conversion = a_afd(paso_thompson.automata, renombrar=True)
    conversion.afd.nombre = f"AFD de {paso_thompson.texto}"
    minimizacion = minimizar(conversion.afd)
    minimo, _ = renombrar_estados(minimizacion.minimo)
    minimo.nombre = f"AFD mínimo de {paso_thompson.texto}"
    return ResultadoPipeline(paso_thompson, conversion, minimizacion, minimo)
