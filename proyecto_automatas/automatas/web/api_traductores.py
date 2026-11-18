"""Acciones de la API para las máquinas de Moore y Mealy."""
from __future__ import annotations

import re

from ..core.finitos.modelo import clave_natural
from ..core.traductores import Traductor, TraductorInvalido
from ..core.traductores import traducir as _traducir
from ..datos import ejemplos_traductores

LAMBDA = "λ"
MAX_LOTE = 300


def maquina_a_json(m: Traductor) -> dict:
    datos = m.a_dict()
    datos["completa"] = m.es_completa()
    return datos


def _error(mensaje: str, campo: str = "general", estado=None, simbolo=None) -> dict:
    return {"mensaje": mensaje, "campo": campo, "estado": estado, "simbolo": simbolo}


def _leer_salida(texto: str):
    """'' o 'λ' = cadena vacía. Devuelve (salida, error)."""
    t = str(texto or "").strip()
    if t in ("", LAMBDA):
        return "", None
    if LAMBDA in t:
        return "", "λ (cadena vacía) no se mezcla con otros símbolos de salida."
    if re.search(r"\s", t):
        return "", "La salida no puede tener espacios."
    return t, None


def crear_traductor(datos: dict) -> dict:
    tipo = datos.get("tipo")
    if tipo not in ("moore", "mealy"):
        return {"ok": False, "errores": [_error(f"Tipo de máquina desconocido: {tipo}.")]}
    errores: list = []
    estados = [str(e).strip() for e in datos.get("estados", [])]
    entrada = [str(s) for s in datos.get("entrada", [])]
    inicial = str(datos.get("inicial") or "").strip()
    tabla = datos.get("tabla", {}) or {}
    salidas_in = datos.get("salidas", {}) or {}

    if not estados:
        errores.append(_error("Agrega al menos un estado.", "estados"))
    vistos = set()
    for q in estados:
        if not q:
            errores.append(_error("Hay un estado sin nombre.", "estados"))
        elif re.search(r"[,;\s/]", q):
            errores.append(_error(f"El nombre «{q}» no puede tener espacios, comas, punto y coma ni «/».", "estados", q))
        elif q in vistos:
            errores.append(_error(f"El estado «{q}» está repetido.", "estados", q))
        vistos.add(q)
    vistos_s = set()
    for s in entrada:
        if len(s) != 1 or s.isspace() or s == "/":
            errores.append(_error(f"El símbolo de entrada «{s}» debe ser un solo carácter (no «/» ni espacio).", "alfabeto", simbolo=s))
        elif s in vistos_s:
            errores.append(_error(f"El símbolo «{s}» está repetido.", "alfabeto", simbolo=s))
        vistos_s.add(s)
    if estados and inicial not in estados:
        errores.append(_error("Elige el estado inicial." if not inicial else f"El estado inicial «{inicial}» no existe.", "inicial"))

    transiciones, salidas = [], {}
    for q in estados:
        if tipo == "moore":
            salida, problema = _leer_salida(salidas_in.get(q, ""))
            if problema:
                errores.append(_error(f"Salida de {q}: {problema}", "salida", q))
            salidas[q] = salida
        for s in entrada:
            texto = str((tabla.get(q) or {}).get(s, "")).strip()
            if not texto or texto == "∅":
                continue
            if tipo == "moore":
                destinos = [d for d in re.split(r"[,;\s]+", texto) if d]
                if len(destinos) > 1:
                    errores.append(_error(f"En una máquina de Moore, δ({q}, {s}) debe tener un solo destino.", "celda", q, s))
                    continue
                if destinos[0] not in estados:
                    errores.append(_error(f"En δ({q}, {s}) el estado «{destinos[0]}» no existe.", "celda", q, s))
                    continue
                transiciones.append((q, s, destinos[0]))
            else:
                if re.search(r"[,;]", texto):
                    errores.append(_error(f"En δ({q}, {s}) solo cabe una transición (destino/salida).", "celda", q, s))
                    continue
                destino, _, resto = texto.partition("/")
                destino = destino.strip()
                salida, problema = _leer_salida(resto)
                if destino not in estados:
                    errores.append(_error(f"En δ({q}, {s}) el estado «{destino}» no existe.", "celda", q, s))
                elif problema:
                    errores.append(_error(f"En δ({q}, {s}): {problema}", "celda", q, s))
                else:
                    transiciones.append((q, s, destino, salida))
    if errores:
        return {"ok": False, "errores": errores}

    try:
        if tipo == "moore":
            m = Traductor.moore(transiciones, salidas, inicial, entrada=set(entrada), nombre=str(datos.get("nombre", "")))
        else:
            m = Traductor.mealy(transiciones, inicial, entrada=set(entrada), nombre=str(datos.get("nombre", "")))
        m.estados |= set(estados)
        m.validar()
    except TraductorInvalido as error:
        return {"ok": False, "errores": [_error(str(error))]}

    advertencias = []
    if tipo == "moore":
        advertencias.append("Convención de clase: no se emite la salida del estado inicial; "
                            "por cada símbolo leído se emite la salida del estado al que se llega.")
    if not m.es_completa():
        faltan = [f"({q}, {s})" for q in sorted(m.estados, key=clave_natural) for s in sorted(m.entrada)
                  if (q, s) not in m.delta]
        advertencias.append("Faltan transiciones en " + ", ".join(faltan[:6]) + ("…" if len(faltan) > 6 else "")
                            + ": si la máquina llega ahí, la traducción se detiene.")
    return {"ok": True, "maquina": maquina_a_json(m), "advertencias": advertencias}


def _maquina(datos: dict) -> Traductor:
    if not isinstance(datos, dict) or "maquina" not in datos:
        raise ValueError("Falta la máquina en la petición.")
    return Traductor.desde_dict(datos["maquina"])


def traducir(datos: dict) -> dict:
    m = _maquina(datos)
    t = _traducir(m, str(datos.get("cadena", "")))
    return {
        "ok": True, "cadena": t.cadena, "salida": t.salida, "completa": t.completa, "motivo": t.motivo,
        "pasos": [{"indice": p.indice, "simbolo": p.simbolo, "origen": p.origen, "estado": p.estado,
                   "salida": p.salida, "acumulada": p.acumulada} for p in t.pasos],
    }


def traducir_lote(datos: dict) -> dict:
    m = _maquina(datos)
    cadenas = datos.get("cadenas", [])
    if not isinstance(cadenas, list):
        raise ValueError("Las cadenas deben ir en una lista.")
    filas = []
    for cadena in cadenas[:MAX_LOTE]:
        t = _traducir(m, str(cadena))
        filas.append({"cadena": t.cadena, "salida": t.salida, "completa": t.completa,
                      "estado_final": t.pasos[-1].estado, "motivo": t.motivo})
    return {"ok": True, "filas": filas, "recortado": len(cadenas) > MAX_LOTE}


def lista_ejemplos(_datos=None) -> dict:
    return {"ok": True, "maquinas": [{"nombre": n, "maquina": maquina_a_json(f())}
                                     for n, f in ejemplos_traductores.EJEMPLOS_TRADUCTORES.items()]}


ACCIONES = {"crear_traductor": crear_traductor, "traducir": traducir, "traducir_lote": traducir_lote,
            "ejemplos_traductores": lista_ejemplos}
