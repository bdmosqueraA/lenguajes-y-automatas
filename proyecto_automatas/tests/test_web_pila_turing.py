"""Pruebas de las APIs de autómatas de pila y de máquinas de Turing."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.web import api
from tests.utiles import cadenas

# ------------------------------------------------------------------ pila
AN_BN = dict(modo="estado_final", estados=["q0", "q1", "q2"], inicial="q0", finales=["q2"], z0="Z", transiciones=[
    dict(origen="q0", lee="a", desapila="Z", apila="AZ", destino="q0"),
    dict(origen="q0", lee="a", desapila="A", apila="AA", destino="q0"),
    dict(origen="q0", lee="b", desapila="A", apila="λ", destino="q1"),
    dict(origen="q1", lee="b", desapila="A", apila="", destino="q1"),
    dict(origen="q1", lee="λ", desapila="Z", apila="Z", destino="q2")])


def msgs(r):
    return " | ".join(e["mensaje"] for e in r["errores"])


def lote_pila(r, lista, modo=None):
    return api.manejar("simular_pila_lote", {"maquina": r["maquina"], "cadenas": lista, "modo": modo})["filas"]


def test_crear_pila_desde_filas_y_reconocer():
    r = api.manejar("crear_pila", AN_BN)
    assert r["ok"] and r["maquina"]["determinista"] is True and r["maquina"]["modo"] == "estado_final"
    assert set(r["maquina"]["entrada"]) == {"a", "b"} and set(r["maquina"]["pila"]) == {"Z", "A"}
    json.dumps(r)
    lista = list(cadenas({"a", "b"}, 8))
    for cadena, fila in zip(lista, lote_pila(r, lista)):
        n = cadena.count("a")
        assert fila["acepta"] == (n >= 1 and cadena == "a" * n + "b" * n), cadena


def test_modo_pila_vacia_y_cambio_de_modo_al_simular():
    vacia = dict(AN_BN, modo="pila_vacia", transiciones=AN_BN["transiciones"][:4] + [
        dict(origen="q1", lee="", desapila="Z", apila="", destino="q1")])
    r = api.manejar("crear_pila", vacia)
    assert r["ok"] and any("no se usan" in a for a in r["advertencias"])
    assert [f["acepta"] for f in lote_pila(r, ["ab", "aabb", "aab", ""])] == [True, True, False, False]
    assert not lote_pila(r, ["ab"], modo="estado_final")[0]["acepta"]       # sin q2 final no acepta por estado


def test_errores_de_la_definicion_de_pila():
    T = AN_BN["transiciones"]
    casos = [
        (dict(AN_BN, modo="raro"), "desconocido"),
        (dict(AN_BN, estados=[]), "al menos un estado"),
        (dict(AN_BN, estados=["q0", "q0", "q1", "q2"]), "repetido"),
        (dict(AN_BN, inicial="x"), "no existe"),
        (dict(AN_BN, finales=["x"]), "final"),
        (dict(AN_BN, z0="ZZ"), "Z₀"),
        (dict(AN_BN, transiciones=[dict(T[0], origen="x")]), "origen"),
        (dict(AN_BN, transiciones=[dict(T[0], destino="x")]), "destino"),
        (dict(AN_BN, transiciones=[dict(T[0], lee="ab")]), "«lee»"),
        (dict(AN_BN, transiciones=[dict(T[0], desapila="AB")]), "«desapila»"),
        (dict(AN_BN, transiciones=[dict(T[0], apila="aλ")]), "«apila»"),
    ]
    for datos, parte in casos:
        r = api.manejar("crear_pila", datos)
        assert not r["ok"] and parte.lower() in msgs(r).lower(), (parte, r)
    r = api.manejar("crear_pila", dict(AN_BN, transiciones=[T[0], dict(T[1], lee="xy")]))
    assert [e["indice"] for e in r["errores"] if e["campo"] == "transicion"] == [1]


def test_advertencias_de_pila():
    nd = dict(AN_BN, transiciones=AN_BN["transiciones"] + [dict(origen="q0", lee="a", desapila="Z", apila="Z", destino="q1")])
    assert any("no determinista" in a for a in api.manejar("crear_pila", nd)["advertencias"])
    assert any("ningún estado final" in a for a in api.manejar("crear_pila", dict(AN_BN, finales=[]))["advertencias"])


def test_simular_pila_muestra_la_pila_y_el_camino():
    r = api.manejar("crear_pila", AN_BN)
    s = api.manejar("simular_pila", {"maquina": r["maquina"], "cadena": "aabb"})
    assert s["acepta"] and [p["pila"] for p in s["pasos"]] == ["Z", "AZ", "AAZ", "AZ", "Z", "Z"]
    assert s["pasos"][0]["transicion"] is None and s["pasos"][1]["transicion"]["apila"] == "AZ"
    assert s["pasos"][-1]["estado"] == "q2" and s["explorado"] >= 6
    mal = api.manejar("simular_pila", {"maquina": r["maquina"], "cadena": "aabbb"})
    assert not mal["acepta"] and not mal["limite"] and mal["pasos"][-1]["restante"] == "b"
    assert "no pertenece" in api.manejar("simular_pila", {"maquina": r["maquina"], "cadena": "abc"})["motivo"]


def test_ciclo_lambda_en_pila_se_corta_con_aviso():
    bucle = dict(modo="estado_final", estados=["q0"], inicial="q0", finales=[], z0="Z", transiciones=[
        dict(origen="q0", lee="", desapila="", apila="A", destino="q0")])
    r = api.manejar("crear_pila", bucle)
    s = api.manejar("simular_pila", {"maquina": r["maquina"], "cadena": ""})
    assert not s["acepta"] and s["limite"] is True and "límite" in s["motivo"]


def test_lote_ejemplos_y_peticiones_malas_de_pila():
    e = api.manejar("ejemplos_pila", {})
    assert e["ok"] and len(e["maquinas"]) == 5
    pal = {m["nombre"]: m["maquina"] for m in e["maquinas"]}["Palíndromos pares (w wᴿ)"]
    lista = list(cadenas({"0", "1"}, 6))
    filas = api.manejar("simular_pila_lote", {"maquina": pal, "cadenas": lista})["filas"]
    assert all(f["acepta"] == (len(c) % 2 == 0 and c == c[::-1]) for c, f in zip(lista, filas))
    muchas = api.manejar("simular_pila_lote", {"maquina": pal, "cadenas": ["0"] * 500})
    assert len(muchas["filas"]) == 300 and muchas["recortado"]
    assert not api.manejar("simular_pila", {"cadena": "a"})["ok"]
    assert not api.manejar("crear_pila", {"modo": "estado_final"})["ok"]


# ------------------------------------------------------------------ Turing
CONTIENE_A = dict(cintas=1, pistas=1, estados=["q0", "qf"], entrada=["a", "b"], inicial="q0", finales=["qf"], blanco="B",
                  transiciones=[dict(origen="q0", lecturas=["b"], destino="q0", escrituras=["b"], movimientos=["D"]),
                                dict(origen="q0", lecturas=["a"], destino="qf", escrituras=["a"], movimientos=["N"])])


def ejecutar(r, cadena, **kw):
    return api.manejar("ejecutar_turing", {"maquina": r["maquina"], "cadena": cadena, **kw})


def test_crear_turing_de_una_cinta_y_ejecutar():
    r = api.manejar("crear_turing", CONTIENE_A)
    assert r["ok"] and r["maquina"]["cintas"] == 1
    json.dumps(r)
    for cadena in cadenas({"a", "b"}, 6):
        assert ejecutar(r, cadena)["acepta"] == ("a" in cadena), cadena
    t = ejecutar(r, "bba")
    assert [p["estado"] for p in t["pasos"]] == ["q0", "q0", "q0", "qf"] and t["pasos"][3]["cabezas"] == [2]
    assert t["pasos"][1]["transicion"]["movimientos"] == ["D"] and t["pasos"][0]["cintas"] == [["b", "b", "a"]]


def test_las_maquinas_de_ejemplo_se_reconstruyen_desde_el_formulario():
    ej = {m["nombre"]: m["maquina"] for m in api.manejar("ejemplos_turing", {})["maquinas"]}
    for nombre, m in ej.items():
        datos = {k: m[k] for k in ("cintas", "pistas", "estados", "entrada", "inicial", "finales", "blanco", "transiciones")}
        r = api.manejar("crear_turing", datos)
        assert r["ok"], (nombre, r)
        assert r["maquina"]["transiciones"] == m["transiciones"]
    r = api.manejar("crear_turing", {k: ej["aⁿbⁿcⁿ (2 cintas)"][k] for k in ("cintas", "pistas", "estados", "entrada", "inicial", "finales", "blanco", "transiciones")})
    assert ejecutar(r, "aabbcc")["acepta"] and not ejecutar(r, "aabbc")["acepta"]


def test_errores_de_la_definicion_de_turing():
    T = CONTIENE_A["transiciones"]
    casos = [
        (dict(CONTIENE_A, cintas=5), "entre 1 y 4"),
        (dict(CONTIENE_A, cintas="x"), "entero"),
        (dict(CONTIENE_A, cintas=2, pistas=2), "multipista"),
        (dict(CONTIENE_A, blanco="BB"), "blanco"),
        (dict(CONTIENE_A, estados=["q0", "q0"]), "repetido"),
        (dict(CONTIENE_A, inicial="zz"), "no existe"),
        (dict(CONTIENE_A, finales=["zz"]), "final"),
        (dict(CONTIENE_A, entrada=["a", "B"]), "blanco"),
        (dict(CONTIENE_A, entrada=["ab"]), "un solo carácter"),
        (dict(CONTIENE_A, transiciones=[dict(T[0], origen="x")]), "origen"),
        (dict(CONTIENE_A, transiciones=[dict(T[0], movimientos=["X"])]), "no es D, I ni N"),
        (dict(CONTIENE_A, transiciones=[dict(T[0], lecturas=["ab"])]), "un solo carácter"),
        (dict(CONTIENE_A, transiciones=[dict(T[0], lecturas=["a", "b"])]), "cada cinta"),
        (dict(CONTIENE_A, cintas=2, transiciones=[dict(T[0])]), "cada cinta"),
    ]
    for datos, parte in casos:
        r = api.manejar("crear_turing", datos)
        assert not r["ok"] and parte.lower() in msgs(r).lower(), (parte, r)
    r = api.manejar("crear_turing", dict(CONTIENE_A, transiciones=[T[0], dict(T[1], lecturas=["b"])]))
    assert not r["ok"] and "no determinista" in msgs(r) and [e["indice"] for e in r["errores"]] == [1]


def test_multipista_acepta_simbolos_de_varias_pistas():
    datos = dict(cintas=1, pistas=2, estados=["q1", "qf"], entrada=["0", "1"], inicial="q1", finales=["qf"], blanco="B",
                 transiciones=[dict(origen="q1", lecturas=["0B"], destino="q1", escrituras=["01"], movimientos=["D"]),
                               dict(origen="q1", lecturas=["1B"], destino="q1", escrituras=["10"], movimientos=["D"]),
                               dict(origen="q1", lecturas=["BB"], destino="qf", escrituras=["BB"], movimientos=["N"])])
    r = api.manejar("crear_turing", datos)
    assert r["ok"] and r["maquina"]["pistas"] == 2 and r["maquina"]["blanco_celda"] == "BB"
    t = ejecutar(r, "1100")
    assert t["acepta"] and t["pasos"][-1]["cintas"] == [["10", "10", "01", "01"]]
    mal = api.manejar("crear_turing", dict(datos, transiciones=[dict(datos["transiciones"][0], lecturas=["0"])]))
    assert not mal["ok"] and "2 caracteres" in msgs(mal)


def test_limite_de_pasos_y_lote_de_turing():
    bucle = dict(cintas=1, pistas=1, estados=["q0"], entrada=["a"], inicial="q0", finales=[], blanco="B",
                 transiciones=[dict(origen="q0", lecturas=["B"], destino="q0", escrituras=["B"], movimientos=["N"])])
    r = api.manejar("crear_turing", bucle)
    assert any("ningún estado final" in a for a in r["advertencias"])
    t = ejecutar(r, "", max_pasos=50)
    assert not t["acepta"] and not t["detenida"] and len(t["pasos"]) == 51 and "parada" in t["motivo"]
    ej = {m["nombre"]: m["maquina"] for m in api.manejar("ejemplos_turing", {})["maquinas"]}
    lote = api.manejar("ejecutar_turing_lote", {"maquina": ej["Complemento a uno (multipista)"], "cadenas": ["1100", "", "0"]})
    assert lote["etiqueta"] == "pistas" and [f["resultado"] for f in lote["filas"]] == [["1100", "0011"], ["", ""], ["0", "1"]]
    lote = api.manejar("ejecutar_turing_lote", {"maquina": ej["ω c ω (2 cintas)"], "cadenas": ["abcab", "abcba"]})
    assert [f["acepta"] for f in lote["filas"]] == [True, False] and lote["etiqueta"] == "cintas" and len(lote["filas"][0]["resultado"]) == 2
    assert not api.manejar("ejecutar_turing", {"cadena": "a"})["ok"]
    assert not api.manejar("ejecutar_turing_lote", {"maquina": ej["ω c ω (2 cintas)"], "cadenas": "x"})["ok"]
    assert len(api.manejar("ejemplos_turing", {})["maquinas"]) == 4
