"""Guardar y cargar autómatas en archivos JSON."""
from __future__ import annotations

import json

from ..core.finitos import Automata


def guardar_json(automata: Automata, ruta: str) -> None:
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(automata.a_dict(), archivo, ensure_ascii=False, indent=2)


def cargar_json(ruta: str) -> Automata:
    with open(ruta, "r", encoding="utf-8") as archivo:
        return Automata.desde_dict(json.load(archivo))
