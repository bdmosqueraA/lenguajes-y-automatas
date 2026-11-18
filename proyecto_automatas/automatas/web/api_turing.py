"""Acciones de la API para las máquinas de Turing (1 cinta, k cintas y multipista)."""
from __future__ import annotations

import re

from ..core.turing import MaquinaTuring, TuringInvalida, contenido
from ..core.turing import ejecutar as _ejecutar
from ..datos import ejemplos_turing

MAX_LOTE = 200
MOVS = ("D", "I", "N")


def maquina_a_json(m: MaquinaTuring) -> dict:
    datos = m.a_dict()
    datos["blanco_celda"] = m.blanco_celda
    return datos


def _error(mensaje: str, campo: str = "general", indice=None, estado=None) -> dict:
    return {"mensaje": mensaje, "campo": campo, "indice": indice, "estado": estado}


def crear_turing(datos: dict) -> dict:
    try:
        cintas = int(datos.get("cintas", 1)); pistas = int(datos.get("pistas", 1))
    except (TypeError, ValueError):
        return {"ok": False, "errores": [_error("El número de cintas y de pistas debe ser un entero.")]}
    errores: list = []
    if not 1 <= cintas <= 4:
        errores.append(_error("Usa entre 1 y 4 cintas."))
    if not 1 <= pistas <= 3 or (pistas > 1 and cintas != 1):
        errores.append(_error("Multipista usa una sola cinta con 2 o 3 pistas."))
    estados = [str(e).strip() for e in datos.get("estados", [])]
    inicial = str(datos.get("inicial") or "").strip()
    finales = [str(f).strip() for f in datos.get("finales", [])]
    entrada = [str(s) for s in datos.get("entrada", [])]
    blanco = str(datos.get("blanco") or "B")
    filas = datos.get("transiciones", []) or []

    if len(blanco) != 1 or blanco.isspace():
        errores.append(_error("El símbolo blanco debe ser un solo carácter.", "blanco"))
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
    for s in entrada:
        if len(s) != 1 or s.isspace():
            errores.append(_error(f"El símbolo de entrada «{s}» debe ser un solo carácter.", "entrada"))
        elif s == blanco:
            errores.append(_error("El blanco no puede ser parte del alfabeto de entrada.", "entrada"))

    trans, claves = [], {}
    for i, fila in enumerate(filas):
        n = i + 1
        o, d = str(fila.get("origen", "")).strip(), str(fila.get("destino", "")).strip()
        lec = [str(x) for x in fila.get("lecturas", [])]
        esc = [str(x) for x in fila.get("escrituras", [])]
        mov = [str(x).upper() for x in fila.get("movimientos", [])]
        if o not in estados:
            errores.append(_error(f"Transición {n}: el origen «{o}» no existe.", "transicion", i))
        if d not in estados:
            errores.append(_error(f"Transición {n}: el destino «{d}» no existe.", "transicion", i))
        if not (len(lec) == len(esc) == len(mov) == cintas if pistas == 1 else len(lec) == len(esc) == len(mov) == 1):
            errores.append(_error(f"Transición {n}: debe indicar lo que lee, escribe y mueve en cada cinta.", "transicion", i))
            continue
        for simbolo in lec + esc:
            if len(simbolo) != pistas or simbolo.isspace() or re.search(r"\s", simbolo):
                dondes = "un texto de {} caracteres (uno por pista)".format(pistas) if pistas > 1 else "un solo carácter"
                errores.append(_error(f"Transición {n}: cada símbolo debe ser {dondes}; hay «{simbolo}».", "transicion", i))
                break
        for m_ in mov:
            if m_ not in MOVS:
                errores.append(_error(f"Transición {n}: el movimiento «{m_}» no es D, I ni N.", "transicion", i))
                break
        clave = (o, tuple(lec))
        if clave in claves:
            errores.append(_error(f"Transición {n}: la máquina sería no determinista; ya hay otra desde {o} leyendo "
                                  f"{','.join(lec)} (transición {claves[clave] + 1}).", "transicion", i))
        claves.setdefault(clave, i)
        trans.append((o, tuple(lec), d, tuple(esc), tuple(mov)))
    if errores:
        return {"ok": False, "errores": errores}

    try:
        m = MaquinaTuring.desde_transiciones(trans, inicial, finales, set(entrada), blanco=blanco, cintas=cintas,
                                             pistas=pistas, nombre=str(datos.get("nombre", "")))
        m.estados |= set(estados)
        m.validar()
    except TuringInvalida as error:
        return {"ok": False, "errores": [_error(str(error))]}

    advertencias = []
    if not m.finales:
        advertencias.append("No marcaste ningún estado final: la máquina nunca aceptará (solo se detendrá rechazando).")
    if not entrada:
        advertencias.append("El alfabeto de entrada está vacío: solo podrás probar la cadena vacía.")
    return {"ok": True, "maquina": maquina_a_json(m), "advertencias": advertencias}


def _maquina(datos: dict) -> MaquinaTuring:
    if not isinstance(datos, dict) or "maquina" not in datos:
        raise ValueError("Falta la máquina de Turing en la petición.")
    return MaquinaTuring.desde_dict(datos["maquina"])


def _max_pasos(datos: dict, por_defecto: int) -> int:
    try:
        return max(1, min(int(datos.get("max_pasos", por_defecto)), 20_000))
    except (TypeError, ValueError):
        return por_defecto


def ejecutar_turing(datos: dict) -> dict:
    m = _maquina(datos)
    t = _ejecutar(m, str(datos.get("cadena", "")), _max_pasos(datos, 2000))
    pasos = []
    for p in t.pasos:
        tr = p.transicion
        c = p.configuracion
        pasos.append({
            "indice": p.indice,
            "transicion": None if tr is None else {"origen": tr.origen, "lecturas": list(tr.lecturas), "destino": tr.destino,
                                                   "escrituras": list(tr.escrituras), "movimientos": list(tr.movimientos)},
            "estado": c.estado, "cintas": [list(x) for x in c.cintas], "cabezas": list(c.cabezas)})
    return {"ok": True, "cadena": t.cadena, "acepta": t.acepta, "detenida": t.detenida, "motivo": t.motivo, "pasos": pasos}


def ejecutar_turing_lote(datos: dict) -> dict:
    m = _maquina(datos)
    cadenas = datos.get("cadenas", [])
    if not isinstance(cadenas, list):
        raise ValueError("Las cadenas deben ir en una lista.")
    filas = []
    for c in cadenas[:MAX_LOTE]:
        t = _ejecutar(m, str(c), _max_pasos(datos, 2000))
        fin = t.final
        if m.pistas > 1:
            resultado = [contenido(m, fin, 0, pista=j) for j in range(m.pistas)]
        else:
            resultado = [contenido(m, fin, i) for i in range(m.cintas)]
        filas.append({"cadena": t.cadena, "acepta": t.acepta, "detenida": t.detenida, "pasos": len(t.pasos) - 1,
                      "estado_final": fin.estado, "resultado": resultado, "motivo": t.motivo})
    return {"ok": True, "filas": filas, "recortado": len(cadenas) > MAX_LOTE,
            "etiqueta": "pistas" if m.pistas > 1 else "cintas"}


def lista_ejemplos(_datos=None) -> dict:
    return {"ok": True, "maquinas": [{"nombre": n, "maquina": maquina_a_json(f())} for n, f in ejemplos_turing.EJEMPLOS_TURING.items()]}


ACCIONES = {"crear_turing": crear_turing, "ejecutar_turing": ejecutar_turing, "ejecutar_turing_lote": ejecutar_turing_lote,
            "ejemplos_turing": lista_ejemplos}
