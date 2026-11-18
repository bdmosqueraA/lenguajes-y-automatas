"""Acciones que la interfaz web pide al servidor. Todo entra y sale como diccionarios JSON."""
from __future__ import annotations

import re

from ..core.finitos import (LAMBDA, Automata, AutomataInvalido, ErrorER, OperacionInvalida, ejecutar,
                            thompson)
from ..core.finitos.conversiones import estados_accesibles
from ..core.finitos.modelo import clave_natural
from ..core.pila import PilaInvalida
from ..core.traductores import TraductorInvalido
from ..core.turing import TuringInvalida
from ..datos import ejemplos
from . import api_pila as _api_pila
from . import api_traductores as _api_traductores
from . import api_turing as _api_turing
from . import pasos as _pasos

MODOS_TABLA = ("AFD", "AFND", "AFND-LAMBDA")
EJEMPLOS_ER = ["(a|b)*abb", "a*b*", "(0|1)*1(0|1)(0|1)", "(ab|a)*", "a(b|c)*d"]


def automata_a_json(a: Automata) -> dict:
    datos = a.a_dict()
    datos["tipo"] = a.tipo()
    datos["completo"] = a.es_completo()
    return datos


def _automata(datos: dict) -> Automata:
    if not isinstance(datos, dict) or "automata" not in datos:
        raise ValueError("Falta el autómata en la petición.")
    return Automata.desde_dict(datos["automata"])


def _destinos(texto) -> list:
    partes = re.split(r"[,;\s]+", str(texto or "").strip())
    return [p for p in partes if p and p not in ("∅", "-", "—")]


def _error(mensaje: str, campo: str = "general", estado=None, simbolo=None) -> dict:
    return {"mensaje": mensaje, "campo": campo, "estado": estado, "simbolo": simbolo}


# ---------------------------------------------------------------------- #
# Crear
# ---------------------------------------------------------------------- #
def crear_desde_tabla(datos: dict) -> dict:
    modo = datos.get("modo", "AFD")
    if modo not in MODOS_TABLA:
        return {"ok": False, "errores": [_error(f"Tipo de autómata desconocido: {modo}.")]}
    errores: list = []
    estados = [str(e).strip() for e in datos.get("estados", [])]
    alfabeto = [str(s) for s in datos.get("alfabeto", [])]
    inicial = str(datos.get("inicial") or "").strip()
    finales = [str(f).strip() for f in datos.get("finales", [])]
    tabla = datos.get("tabla", {}) or {}

    if not estados:
        errores.append(_error("Agrega al menos un estado.", "estados"))
    vistos = set()
    for q in estados:
        if not q:
            errores.append(_error("Hay un estado sin nombre.", "estados"))
        elif re.search(r"[,;\s]", q):
            errores.append(_error(f"El nombre «{q}» no puede tener espacios, comas ni punto y coma.", "estados", q))
        elif q in vistos:
            errores.append(_error(f"El estado «{q}» está repetido.", "estados", q))
        vistos.add(q)
    vistos_s = set()
    for s in alfabeto:
        if len(s) != 1 or s.isspace():
            errores.append(_error(f"El símbolo «{s}» debe ser un solo carácter.", "alfabeto", simbolo=s))
        elif s == LAMBDA:
            errores.append(_error("λ no puede ser un símbolo del alfabeto: se usa solo en AFND-λ.", "alfabeto", simbolo=s))
        elif s in vistos_s:
            errores.append(_error(f"El símbolo «{s}» está repetido.", "alfabeto", simbolo=s))
        vistos_s.add(s)
    if estados and inicial not in estados:
        errores.append(_error("Elige el estado inicial." if not inicial else f"El estado inicial «{inicial}» no existe.", "inicial"))
    for f in finales:
        if f not in estados:
            errores.append(_error(f"El estado final «{f}» no existe.", "finales", f))

    columnas = alfabeto + ([LAMBDA] if modo == "AFND-LAMBDA" else [])
    transiciones = []
    for q in estados:
        for s in columnas:
            destinos = _destinos((tabla.get(q) or {}).get(s, ""))
            for dest in destinos:
                if dest not in estados:
                    errores.append(_error(f"En δ({q}, {s}) el estado «{dest}» no existe.", "celda", q, s))
            if modo == "AFD" and len(destinos) > 1:
                errores.append(_error(f"En un AFD, δ({q}, {s}) debe tener un solo destino "
                                      f"(tiene {len(destinos)}). Usa el tipo AFND si quieres varios.", "celda", q, s))
            transiciones += [(q, s, dest) for dest in destinos if dest in estados]
    if errores:
        return {"ok": False, "errores": errores}

    try:
        a = Automata.desde_transiciones(transiciones, inicial, finales, estados=set(estados),
                                        alfabeto=set(alfabeto), nombre=str(datos.get("nombre", "")))
    except AutomataInvalido as error:
        return {"ok": False, "errores": [_error(str(error))]}

    advertencias = []
    if modo != "AFD" and a.tipo() == "AFD":
        advertencias.append("La tabla resultó determinista, así que el autómata se trata como AFD.")
    if a.tipo() == "AFD" and not a.es_completo():
        faltan = [f"({q}, {s})" for q in sorted(a.estados, key=clave_natural) for s in sorted(a.alfabeto)
                  if not a.destinos(q, s)]
        resumen = ", ".join(faltan[:6]) + ("…" if len(faltan) > 6 else "")
        advertencias.append(f"El AFD es incompleto: faltan transiciones en {resumen}. Si una cadena llega ahí, "
                            "se rechaza. Puedes usar «Completar».")
    if not a.finales:
        advertencias.append("No hay estados finales: el autómata no acepta ninguna cadena.")
    inaccesibles = a.estados - estados_accesibles(a)
    if inaccesibles:
        advertencias.append("Estados inaccesibles desde el inicial: " + ", ".join(sorted(inaccesibles, key=clave_natural)) + ".")
    return {"ok": True, "automata": automata_a_json(a), "advertencias": advertencias}


def crear_desde_er(datos: dict) -> dict:
    texto = str(datos.get("er", ""))
    extra = {c for c in str(datos.get("alfabeto_extra", "")) if not c.isspace() and c not in ",;"}
    try:
        resultado = thompson(texto, extra or None)
    except ErrorER as error:
        return {"ok": False, "errores": [{**_error(error.mensaje, "er"), "posicion": error.posicion}]}
    except AutomataInvalido as error:
        return {"ok": False, "errores": [_error(str(error), "er")]}
    pasos, final = _pasos.pasos_thompson(resultado)
    return {"ok": True, "automata": automata_a_json(resultado.automata), "advertencias": [],
            "er": resultado.texto,
            "operacion": _operacion_json("thompson", "Expresión regular → AFND-λ (Thompson)", pasos, final)}


def crear(datos: dict) -> dict:
    return crear_desde_er(datos) if datos.get("modo") == "ER" else crear_desde_tabla(datos)


# ---------------------------------------------------------------------- #
# Simular y operar
# ---------------------------------------------------------------------- #
def simular(datos: dict) -> dict:
    a = _automata(datos)
    traza = ejecutar(a, str(datos.get("cadena", "")))
    return {
        "ok": True, "cadena": traza.cadena, "acepta": traza.acepta, "motivo": traza.motivo,
        "pasos": [{"indice": p.indice, "simbolo": p.simbolo,
                   "estados": sorted(p.estados, key=clave_natural),
                   "transiciones": [{"origen": o, "simbolo": s, "destino": d} for o, s, d in sorted(p.transiciones)]}
                  for p in traza.pasos],
    }


def _operacion_json(identificador: str, titulo: str, pasos: list, resultado: dict) -> dict:
    final = ({"tipo": "automata", "automata": automata_a_json(resultado["automata"])}
             if resultado["tipo"] == "automata" else resultado)
    return {"id": identificador, "titulo": titulo, "pasos": pasos, "resultado": final}


def operacion(datos: dict) -> dict:
    identificador = datos.get("operacion")
    if identificador not in _pasos.OPERACIONES:
        return {"ok": False, "mensaje": f"Operación desconocida: {identificador}."}
    titulo, funcion = _pasos.OPERACIONES[identificador]
    pasos, resultado = funcion(_automata(datos))
    return {"ok": True, "operacion": _operacion_json(identificador, titulo, pasos, resultado)}


def lista_ejemplos(_datos=None) -> dict:
    return {"ok": True,
            "automatas": [{"nombre": nombre, "automata": automata_a_json(fabrica())}
                          for nombre, fabrica in ejemplos.EJEMPLOS.items()],
            "expresiones": EJEMPLOS_ER}


ACCIONES = {"crear": crear, "simular": simular, "operacion": operacion, "ejemplos": lista_ejemplos}
ACCIONES.update(_api_traductores.ACCIONES)
ACCIONES.update(_api_pila.ACCIONES)
ACCIONES.update(_api_turing.ACCIONES)


def manejar(accion: str, datos: dict) -> dict:
    """Punto de entrada único: nunca lanza; los errores se devuelven como {"ok": False, ...}."""
    funcion = ACCIONES.get(accion)
    if funcion is None:
        return {"ok": False, "mensaje": f"Acción desconocida: {accion}."}
    try:
        return funcion(datos)
    except (OperacionInvalida, AutomataInvalido, ErrorER, TraductorInvalido, PilaInvalida, TuringInvalida, ValueError, KeyError, TypeError) as error:
        return {"ok": False, "mensaje": str(error) or error.__class__.__name__}
