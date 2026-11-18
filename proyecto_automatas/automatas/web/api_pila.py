"""Acciones de la API para los autómatas de pila."""
from __future__ import annotations

import re

from ..core.pila import AutomataPila, PilaInvalida
from ..core.pila import ejecutar as _ejecutar
from ..datos import ejemplos_pila

LAMBDA = "λ"
MAX_LOTE = 300
LIMITE_UI = 5_000


def pila_a_json(ap: AutomataPila) -> dict:
    datos = ap.a_dict()
    datos["determinista"] = ap.es_determinista()
    return datos


def _error(mensaje: str, campo: str = "general", indice=None, estado=None) -> dict:
    return {"mensaje": mensaje, "campo": campo, "indice": indice, "estado": estado}


def _vacio(texto) -> str:
    t = str(texto or "").strip()
    return "" if t == LAMBDA else t


def crear_pila(datos: dict) -> dict:
    modo = datos.get("modo", "estado_final")
    if modo not in ("estado_final", "pila_vacia"):
        return {"ok": False, "errores": [_error(f"Modo de aceptación desconocido: {modo}.")]}
    errores: list = []
    estados = [str(e).strip() for e in datos.get("estados", [])]
    inicial = str(datos.get("inicial") or "").strip()
    finales = [str(f).strip() for f in datos.get("finales", [])]
    z0 = _vacio(datos.get("z0"))
    filas = datos.get("transiciones", []) or []

    if not estados:
        errores.append(_error("Agrega al menos un estado.", "estados"))
    vistos = set()
    for q in estados:
        if not q:
            errores.append(_error("Hay un estado sin nombre.", "estados"))
        elif re.search(r"[,;\s/]", q):
            errores.append(_error(f"El nombre «{q}» no puede tener espacios, comas, punto y coma ni «/».", "estados", estado=q))
        elif q in vistos:
            errores.append(_error(f"El estado «{q}» está repetido.", "estados", estado=q))
        vistos.add(q)
    if estados and inicial not in estados:
        errores.append(_error("Elige el estado inicial." if not inicial else f"El estado inicial «{inicial}» no existe.", "inicial"))
    for f in finales:
        if f not in estados:
            errores.append(_error(f"El estado final «{f}» no existe.", "finales", estado=f))
    if len(z0) > 1 or re.search(r"\s", z0):
        errores.append(_error("El símbolo inicial de la pila (Z₀) debe ser un solo carácter o λ.", "z0"))

    trans = []
    for i, fila in enumerate(filas):
        o, d = str(fila.get("origen", "")).strip(), str(fila.get("destino", "")).strip()
        lee, des, ap = _vacio(fila.get("lee")), _vacio(fila.get("desapila")), _vacio(fila.get("apila"))
        n = i + 1
        if o not in estados:
            errores.append(_error(f"Transición {n}: el origen «{o}» no existe.", "transicion", i))
        if d not in estados:
            errores.append(_error(f"Transición {n}: el destino «{d}» no existe.", "transicion", i))
        if len(lee) > 1 or re.search(r"\s", lee):
            errores.append(_error(f"Transición {n}: «lee» debe ser un solo símbolo o λ.", "transicion", i))
        if len(des) > 1 or re.search(r"\s", des):
            errores.append(_error(f"Transición {n}: «desapila» debe ser un solo símbolo o λ.", "transicion", i))
        if LAMBDA in ap or re.search(r"\s", ap):
            errores.append(_error(f"Transición {n}: «apila» es una palabra sin espacios (o λ sola).", "transicion", i))
        trans.append((o, lee, des, d, ap))
    if errores:
        return {"ok": False, "errores": errores}

    try:
        ap = AutomataPila.desde_transiciones(trans, inicial, finales, simbolo_inicial=z0, modo=modo,
                                             nombre=str(datos.get("nombre", "")))
        ap.estados |= set(estados)
        ap.validar()
    except PilaInvalida as error:
        return {"ok": False, "errores": [_error(str(error))]}

    advertencias = []
    if not ap.es_determinista():
        advertencias.append("Es un autómata de pila no determinista: la simulación explora todas las ramas posibles.")
    if modo == "estado_final" and not ap.finales:
        advertencias.append("Aceptas por estado final pero no marcaste ningún estado final: no aceptará ninguna cadena.")
    if modo == "pila_vacia" and ap.finales:
        advertencias.append("Aceptas por pila vacía: los estados finales marcados no se usan para aceptar.")
    return {"ok": True, "maquina": pila_a_json(ap), "advertencias": advertencias}


def _ap(datos: dict) -> AutomataPila:
    if not isinstance(datos, dict) or "maquina" not in datos:
        raise ValueError("Falta el autómata de pila en la petición.")
    return AutomataPila.desde_dict(datos["maquina"])


def _modo(datos: dict):
    modo = datos.get("modo")
    return modo if modo in ("estado_final", "pila_vacia") else None


def simular_pila(datos: dict) -> dict:
    ap = _ap(datos)
    t = _ejecutar(ap, str(datos.get("cadena", "")), _modo(datos), LIMITE_UI)
    pasos = []
    for p in t.camino:
        tr = p.transicion
        pasos.append({
            "indice": p.indice,
            "transicion": None if tr is None else {"origen": tr.origen, "leido": tr.leido, "desapila": tr.desapila,
                                                   "apila": tr.apila, "destino": tr.destino},
            "estado": p.configuracion.estado, "restante": p.configuracion.restante, "pila": p.configuracion.pila})
    return {"ok": True, "cadena": t.cadena, "modo": t.modo, "acepta": t.acepta, "motivo": t.motivo,
            "explorado": t.explorado, "limite": t.limite_alcanzado, "pasos": pasos}


def simular_pila_lote(datos: dict) -> dict:
    ap = _ap(datos)
    cadenas = datos.get("cadenas", [])
    if not isinstance(cadenas, list):
        raise ValueError("Las cadenas deben ir en una lista.")
    filas = []
    for c in cadenas[:MAX_LOTE]:
        t = _ejecutar(ap, str(c), _modo(datos), 2_000)
        filas.append({"cadena": t.cadena, "acepta": t.acepta, "explorado": t.explorado,
                      "limite": t.limite_alcanzado, "motivo": t.motivo})
    return {"ok": True, "filas": filas, "recortado": len(cadenas) > MAX_LOTE}


def lista_ejemplos(_datos=None) -> dict:
    return {"ok": True, "maquinas": [{"nombre": n, "maquina": pila_a_json(f())} for n, f in ejemplos_pila.EJEMPLOS_PILA.items()]}


ACCIONES = {"crear_pila": crear_pila, "simular_pila": simular_pila, "simular_pila_lote": simular_pila_lote,
            "ejemplos_pila": lista_ejemplos}
