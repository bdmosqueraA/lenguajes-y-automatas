"""Pruebas de la API de traductores (Moore y Mealy) y de los detectores de secuencia de ejemplo."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.traductores import Traductor, traducir
from automatas.datos import ejemplos_traductores as ej
from automatas.web import api
from tests.utiles import cadenas

MOORE = dict(tipo="moore", estados=["P", "I"], entrada=["0", "1"], inicial="P", salidas={"P": "a", "I": "b"},
             tabla={"P": {"0": "P", "1": "I"}, "I": {"0": "I", "1": "P"}})
MEALY = dict(tipo="mealy", estados=["P", "I"], entrada=["0", "1"], inicial="P",
             tabla={"P": {"0": "P/a", "1": "I/b"}, "I": {"0": "I/b", "1": "P/a"}})


def textos(r):
    return " | ".join(e["mensaje"] for e in r["errores"])


def salida(r, cadena):
    return api.manejar("traducir", {"maquina": r["maquina"], "cadena": cadena})["salida"]


def test_detectores_de_secuencia_con_solapamiento():
    for secuencia in ("1001", "111", "011", "0110"):
        for tipo in ("moore", "mealy"):
            m = ej.detector_de_secuencia(secuencia, tipo)
            for cadena in cadenas({"0", "1"}, 9):
                esperado = "".join("1" if cadena[:i + 1].endswith(secuencia) else "0" for i in range(len(cadena)))
                assert traducir(m, cadena).salida == esperado, (secuencia, tipo, cadena)
    assert len(ej.detector_de_secuencia("1001", "moore").estados) == 5
    assert len(ej.detector_de_secuencia("1001", "mealy").estados) == 4      # Mealy necesita un estado menos
    assert traducir(ej.detector_de_secuencia("111", "mealy"), "11111").salida == "00111"


def test_crear_moore_y_mealy_equivalentes():
    moore = api.manejar("crear_traductor", MOORE)
    mealy = api.manejar("crear_traductor", MEALY)
    assert moore["ok"] and mealy["ok"] and moore["maquina"]["tipo"] == "moore" and mealy["maquina"]["tipo"] == "mealy"
    assert set(moore["maquina"]["salida"]) == {"a", "b"} and moore["maquina"]["completa"] is True
    for cadena in cadenas({"0", "1"}, 7):
        assert salida(moore, cadena) == salida(mealy, cadena)
    assert salida(moore, "0110") == "abaa"
    assert any("no se emite la salida del estado inicial" in a for a in moore["advertencias"])
    json.dumps(moore)


def test_la_salida_lambda_y_las_salidas_largas():
    r = api.manejar("crear_traductor", dict(MEALY, tabla={"P": {"0": "P/λ", "1": "I/xy"}, "I": {"0": "I", "1": "P/"}}))
    assert r["ok"]
    assert salida(r, "0110") == "xy"                                   # 0→λ, 1→xy, 1→λ, 0→λ
    r2 = api.manejar("crear_traductor", dict(MOORE, salidas={"P": "λ", "I": ""}))
    assert r2["ok"] and salida(r2, "0110") == ""


def test_el_mealy_conserva_estados_sin_transiciones():
    r = api.manejar("crear_traductor", dict(MEALY, estados=["P", "I", "Z"]))
    assert r["ok"] and "Z" in r["maquina"]["estados"]


def test_errores_de_validacion():
    casos = [
        (dict(MOORE, tipo="x"), "desconocido"),
        (dict(MOORE, estados=[], inicial=""), "al menos un estado"),
        (dict(MOORE, estados=["P", "P"]), "repetido"),
        (dict(MOORE, estados=["P/1", "I"]), "«/»"),
        (dict(MOORE, inicial=""), "estado inicial"),
        (dict(MOORE, entrada=["0", "/"]), "un solo carácter"),
        (dict(MOORE, entrada=["0", "0"]), "repetido"),
        (dict(MOORE, salidas={"P": "aλ", "I": "b"}), "λ"),
        (dict(MOORE, salidas={"P": "a b", "I": "b"}), "espacios"),
        (dict(MOORE, tabla={"P": {"0": "Q9"}}), "no existe"),
        (dict(MOORE, tabla={"P": {"0": "P, I"}}), "un solo destino"),
        (dict(MEALY, tabla={"P": {"0": "P/a, I/b"}}), "una transición"),
        (dict(MEALY, tabla={"P": {"0": "Z/a"}}), "no existe"),
        (dict(MEALY, tabla={"P": {"0": "P/aλ"}}), "λ"),
    ]
    for datos, parte in casos:
        r = api.manejar("crear_traductor", datos)
        assert not r["ok"] and parte.lower() in textos(r).lower(), (parte, r)
    r = api.manejar("crear_traductor", dict(MOORE, tabla={"P": {"0": "Q9", "1": "P, I"}}))
    assert {(e["estado"], e["simbolo"]) for e in r["errores"] if e["campo"] == "celda"} == {("P", "0"), ("P", "1")}


def test_advertencia_de_transiciones_que_faltan():
    r = api.manejar("crear_traductor", dict(MEALY, tabla={"P": {"0": "P/a"}}))
    assert r["ok"] and r["maquina"]["completa"] is False and any("Faltan transiciones" in a for a in r["advertencias"])
    t = api.manejar("traducir", {"maquina": r["maquina"], "cadena": "01"})
    assert t["completa"] is False and t["salida"] == "a" and "No hay transición" in t["motivo"]


def test_traducir_devuelve_la_traza():
    r = api.manejar("crear_traductor", MOORE)
    t = api.manejar("traducir", {"maquina": r["maquina"], "cadena": "011"})
    assert t["ok"] and t["salida"] == "aba" and t["completa"] is True
    assert [p["acumulada"] for p in t["pasos"]] == ["", "a", "ab", "aba"]
    assert t["pasos"][0] == {"indice": 0, "simbolo": None, "origen": None, "estado": "P", "salida": "", "acumulada": ""}
    assert t["pasos"][2]["origen"] == "P" and t["pasos"][2]["estado"] == "I" and t["pasos"][2]["salida"] == "b"
    assert api.manejar("traducir", {"maquina": r["maquina"], "cadena": "0x"})["completa"] is False


def test_traducir_en_lote():
    r = api.manejar("crear_traductor", MEALY)
    lote = api.manejar("traducir_lote", {"maquina": r["maquina"], "cadenas": ["", "1", "0110", "012"]})
    assert lote["ok"] and [f["salida"] for f in lote["filas"]] == ["", "b", "abaa", "ab"]
    assert [f["completa"] for f in lote["filas"]] == [True, True, True, False]
    assert lote["filas"][2]["estado_final"] == "P"
    assert not api.manejar("traducir_lote", {"maquina": r["maquina"], "cadenas": "no lista"})["ok"]
    muchas = api.manejar("traducir_lote", {"maquina": r["maquina"], "cadenas": ["0"] * 500})
    assert len(muchas["filas"]) == 300 and muchas["recortado"] is True


def test_peticiones_malas_no_revientan():
    assert not api.manejar("traducir", {"cadena": "01"})["ok"]
    assert not api.manejar("traducir", {"maquina": {"tipo": "moore"}, "cadena": "01"})["ok"]
    assert not api.manejar("crear_traductor", {})["ok"]


def test_ejemplos_de_traductores_para_la_interfaz():
    r = api.manejar("ejemplos_traductores", {})
    assert r["ok"] and len(r["maquinas"]) == len(ej.EJEMPLOS_TRADUCTORES) == 10
    json.dumps(r)
    for item in r["maquinas"]:
        assert Traductor.desde_dict(item["maquina"]) is not None
    por_nombre = {i["nombre"]: i["maquina"] for i in r["maquinas"]}
    assert api.manejar("traducir", {"maquina": por_nombre["Moore: suma parcial módulo 5"], "cadena": "32130"})["salida"] == "30144"
    assert api.manejar("traducir", {"maquina": por_nombre["Mealy: dos últimos símbolos"], "cadena": "01101001"})["salida"] == "bbbbab"
