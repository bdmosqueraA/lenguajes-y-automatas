"""Modelo común para autómatas finitos: AFD, AFND y AFND-λ.

Un solo tipo de dato (`Automata`) representa los tres. La diferencia está en
cómo se usa la función de transición δ:

    δ : (estado, símbolo o λ) -> conjunto de estados

* AFD    : sin transiciones λ y a lo sumo un destino por (estado, símbolo).
* AFND   : sin transiciones λ, pero algún (estado, símbolo) con varios destinos.
* AFND-λ : con al menos una transición λ.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

LAMBDA = "λ"


class AutomataInvalido(ValueError):
    """La definición del autómata es inconsistente."""


class OperacionInvalida(ValueError):
    """La operación no se puede aplicar a este autómata (p. ej. minimizar un AFND)."""


def clave_natural(texto: str) -> list:
    """Orden natural: q2 < q10 (en vez de q10 < q2)."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", texto)]


def formato_conjunto(conjunto) -> str:
    """{q0,q1,q2} con orden natural; ∅ si está vacío."""
    if not conjunto:
        return "∅"
    return "{" + ",".join(sorted(conjunto, key=clave_natural)) + "}"


@dataclass
class Automata:
    estados: set
    alfabeto: set
    delta: dict          # {(origen, símbolo): {destinos}}
    inicial: str
    finales: set
    nombre: str = ""

    def __post_init__(self):
        self.estados = set(self.estados)
        self.alfabeto = set(self.alfabeto)
        self.finales = set(self.finales)
        self.delta = {clave: set(dest) for clave, dest in self.delta.items() if dest}
        self.validar()

    # ------------------------------------------------------------------ #
    # Construcción
    # ------------------------------------------------------------------ #
    @classmethod
    def desde_transiciones(cls, transiciones, inicial, finales,
                           estados=None, alfabeto=None, nombre=""):
        """Crea un autómata a partir de una lista de (origen, símbolo, destino).

        Si no se indican `estados` o `alfabeto`, se deducen de las transiciones.
        """
        transiciones = list(transiciones)
        finales = set(finales)
        if estados is None:
            estados = {inicial} | finales
            for origen, _, destino in transiciones:
                estados |= {origen, destino}
        if alfabeto is None:
            alfabeto = {s for _, s, _ in transiciones if s != LAMBDA}
        delta: dict = {}
        for origen, simbolo, destino in transiciones:
            delta.setdefault((origen, simbolo), set()).add(destino)
        return cls(estados, alfabeto, delta, inicial, finales, nombre)

    def copia(self, nombre=None) -> "Automata":
        return Automata(set(self.estados), set(self.alfabeto),
                        {k: set(v) for k, v in self.delta.items()},
                        self.inicial, set(self.finales),
                        self.nombre if nombre is None else nombre)

    # ------------------------------------------------------------------ #
    # Validación
    # ------------------------------------------------------------------ #
    def validar(self) -> None:
        if not self.estados:
            raise AutomataInvalido("El autómata debe tener al menos un estado.")
        if self.inicial not in self.estados:
            raise AutomataInvalido(f"El estado inicial '{self.inicial}' no está en Q.")
        fuera = self.finales - self.estados
        if fuera:
            raise AutomataInvalido(
                f"Estados finales que no están en Q: {formato_conjunto(fuera)}.")
        if LAMBDA in self.alfabeto:
            raise AutomataInvalido("λ no puede formar parte del alfabeto.")
        for simbolo in self.alfabeto:
            if len(simbolo) != 1:
                raise AutomataInvalido(
                    f"Cada símbolo del alfabeto debe ser un solo carácter: '{simbolo}'.")
        for (origen, simbolo), destinos in self.delta.items():
            if origen not in self.estados:
                raise AutomataInvalido(f"Transición desde un estado desconocido: '{origen}'.")
            if simbolo != LAMBDA and simbolo not in self.alfabeto:
                raise AutomataInvalido(
                    f"Transición con el símbolo '{simbolo}', que no está en Σ.")
            desconocidos = destinos - self.estados
            if desconocidos:
                raise AutomataInvalido(
                    f"Transición hacia estados desconocidos: {formato_conjunto(desconocidos)}.")

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def destinos(self, estado: str, simbolo: str) -> frozenset:
        return frozenset(self.delta.get((estado, simbolo), ()))

    def transiciones(self) -> list:
        """Lista ordenada de (origen, símbolo, destino)."""
        lista = [(o, s, d) for (o, s), ds in self.delta.items() for d in ds]
        return sorted(lista, key=lambda t: (clave_natural(t[0]), t[1], clave_natural(t[2])))

    def tiene_lambda(self) -> bool:
        return any(s == LAMBDA for (_, s) in self.delta)

    def es_determinista(self) -> bool:
        """Sin λ y a lo sumo un destino por (estado, símbolo)."""
        return not self.tiene_lambda() and all(len(d) <= 1 for d in self.delta.values())

    def es_completo(self) -> bool:
        """Determinista y con transición definida para todo (estado, símbolo)."""
        return self.es_determinista() and all(
            (q, a) in self.delta for q in self.estados for a in self.alfabeto)

    def tipo(self) -> str:
        if self.tiene_lambda():
            return "AFND-λ"
        return "AFD" if self.es_determinista() else "AFND"

    # ------------------------------------------------------------------ #
    # Presentación
    # ------------------------------------------------------------------ #
    def tabla(self) -> str:
        """Tabla de transición en texto (→ inicial, # aceptación, como en clase)."""
        simbolos = sorted(self.alfabeto) + ([LAMBDA] if self.tiene_lambda() else [])

        def celda(destinos) -> str:
            if len(destinos) == 1:
                return next(iter(destinos))
            return formato_conjunto(destinos)

        filas = []
        for q in sorted(self.estados, key=clave_natural):
            marca = ("→" if q == self.inicial else "") + ("#" if q in self.finales else "")
            filas.append([marca + q] + [celda(self.destinos(q, s)) for s in simbolos])
        encabezado = ["δ"] + simbolos
        anchos = [max(len(f[i]) for f in [encabezado] + filas) for i in range(len(encabezado))]
        formato = lambda fila: " | ".join(c.ljust(anchos[i]) for i, c in enumerate(fila)).rstrip()
        separador = "-+-".join("-" * a for a in anchos)
        return "\n".join([formato(encabezado), separador] + [formato(f) for f in filas])

    def descripcion(self) -> str:
        titulo = f"{self.nombre} — " if self.nombre else ""
        return (f"{titulo}{self.tipo()}  "
                f"Q={formato_conjunto(self.estados)}  "
                f"Σ={formato_conjunto(self.alfabeto)}  "
                f"q0={self.inicial}  F={formato_conjunto(self.finales)}")

    # ------------------------------------------------------------------ #
    # Serialización (JSON)
    # ------------------------------------------------------------------ #
    def a_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "estados": sorted(self.estados, key=clave_natural),
            "alfabeto": sorted(self.alfabeto),
            "inicial": self.inicial,
            "finales": sorted(self.finales, key=clave_natural),
            "transiciones": [
                {"origen": o, "simbolo": s, "destino": d} for o, s, d in self.transiciones()
            ],
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Automata":
        try:
            transiciones = [(t["origen"], t["simbolo"], t["destino"])
                            for t in datos.get("transiciones", [])]
            return cls.desde_transiciones(
                transiciones,
                inicial=datos["inicial"],
                finales=datos.get("finales", []),
                estados=datos["estados"],
                alfabeto=datos["alfabeto"],
                nombre=datos.get("nombre", ""),
            )
        except KeyError as error:
            raise AutomataInvalido(f"Falta el campo {error} en la definición.") from error
