"""Pruebas de la API web: creación desde tabla/ER, simulación, operaciones y su paso a paso."""
import json
import os
import sys
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.finitos import Automata, analizar
from automatas.datos import ejemplos
from automatas.web import api
from automatas.web.servidor import crear_servidor
from tests.utiles import cadenas, iguala_regex, iguales

AFD_AB = dict(modo="AFD", estados=["q0", "q1", "q2"], alfabeto=["a", "b"], inicial="q0", finales=["q0", "q2"],
              tabla={"q0": {"a": "q0", "b": "q1"}, "q1": {"a": "q1", "b": "q2"}, "q2": {"a": "q1", "b": "q1"}})


def automata_de(respuesta):
    return Automata.desde_dict(respuesta["automata"])


def hacer(modo_ejemplo):
    return api.automata_a_json(modo_ejemplo)


def mensajes(r):
    return " | ".join(e["mensaje"] for e in r["errores"])


# ---------------------------------------------------------------- crear desde la tabla
def test_crear_afd_desde_la_tabla():
    r = api.manejar("crear", AFD_AB)
    assert r["ok"] and r["automata"]["tipo"] == "AFD" and r["automata"]["completo"] is True
    iguales(automata_de(r), ejemplos.afd_intro_ab())
    json.dumps(r)


def test_crear_afnd_y_afnd_lambda():
    r = api.manejar("crear", dict(modo="AFND", estados=["q0", "q1", "q2"], alfabeto=["0", "1"], inicial="q0",
                                  finales=["q2"], tabla={"q0": {"0": "q0, q1", "1": "q0"}, "q1": {"1": "q2"}}))
    assert r["ok"] and r["automata"]["tipo"] == "AFND"
    iguales(automata_de(r), ejemplos.afnd_termina_en_01())
    r = api.manejar("crear", dict(modo="AFND-LAMBDA", estados=["q0", "q1"], alfabeto=["a", "b"], inicial="q0",
                                  finales=["q1"], tabla={"q0": {"a": "q0", "λ": "q1"}, "q1": {"b": "q1"}}))
    assert r["ok"] and r["automata"]["tipo"] == "AFND-λ"
    iguales(automata_de(r), ejemplos.afnd_lambda_a_estrella_b_estrella())


def test_la_columna_lambda_se_ignora_fuera_de_afnd_lambda():
    datos = dict(AFD_AB, tabla={**AFD_AB["tabla"], "q0": {"a": "q0", "b": "q1", "λ": "q2"}})
    assert api.manejar("crear", datos)["automata"]["tipo"] == "AFD"


def test_separadores_y_celdas_vacias():
    r = api.manejar("crear", dict(modo="AFND", estados=["q0", "q1", "q2"], alfabeto=["a"], inicial="q0", finales=[],
                                  tabla={"q0": {"a": "q1;q2"}, "q1": {"a": " q2  q0 "}, "q2": {"a": "∅"}}))
    a = automata_de(r)
    assert a.destinos("q0", "a") == {"q1", "q2"} and a.destinos("q1", "a") == {"q2", "q0"} and not a.destinos("q2", "a")


def test_errores_de_validacion():
    casos = [
        (dict(AFD_AB, estados=[], inicial=""), "al menos un estado"),
        (dict(AFD_AB, estados=["q0", "q0", "q2"]), "repetido"),
        (dict(AFD_AB, estados=["q 0", "q1", "q2"]), "espacios"),
        (dict(AFD_AB, inicial=""), "inicial"),
        (dict(AFD_AB, inicial="zz"), "no existe"),
        (dict(AFD_AB, finales=["q9"]), "final"),
        (dict(AFD_AB, alfabeto=["a", "bc"]), "un solo carácter"),
        (dict(AFD_AB, alfabeto=["a", "λ"]), "λ"),
        (dict(AFD_AB, alfabeto=["a", "a"]), "repetido"),
        (dict(AFD_AB, modo="XYZ"), "desconocido"),
    ]
    for datos, parte in casos:
        r = api.manejar("crear", datos)
        assert not r["ok"] and parte.lower() in mensajes(r).lower(), (parte, r)


def test_errores_en_celdas_indican_cual():
    r = api.manejar("crear", dict(AFD_AB, tabla={**AFD_AB["tabla"], "q0": {"a": "q9", "b": "q1, q2"}}))
    celdas = [(e["estado"], e["simbolo"]) for e in r["errores"] if e["campo"] == "celda"]
    assert ("q0", "a") in celdas and ("q0", "b") in celdas
    assert "no existe" in mensajes(r) and "un solo destino" in mensajes(r)
    r = api.manejar("crear", dict(AFD_AB, modo="AFND", tabla={**AFD_AB["tabla"], "q0": {"a": "q0, q1", "b": "q1"}}))
    assert r["ok"]                                    # el mismo contenido sí vale como AFND


def test_advertencias():
    r = api.manejar("crear", dict(AFD_AB, tabla={"q0": {"a": "q1"}, "q1": {}, "q2": {}}, finales=[]))
    textos = " | ".join(r["advertencias"])
    assert r["ok"] and "incompleto" in textos and "No hay estados finales" in textos and "inaccesibles" in textos
    r = api.manejar("crear", dict(AFD_AB, modo="AFND"))
    assert "determinista" in " ".join(r["advertencias"])


# ---------------------------------------------------------------- crear desde una ER
def test_crear_desde_expresion_regular():
    r = api.manejar("crear", {"modo": "ER", "er": "(a|b)*abb"})
    assert r["ok"] and r["automata"]["tipo"] == "AFND-λ" and len(r["automata"]["estados"]) == 14
    assert r["operacion"]["id"] == "thompson" and r["operacion"]["resultado"]["tipo"] == "automata"
    iguala_regex(automata_de(r), analizar("(a|b)*abb"), 7)
    r = api.manejar("crear", {"modo": "ER", "er": "a", "alfabeto_extra": "b c, "})
    assert set(r["automata"]["alfabeto"]) == {"a", "b", "c"}


def test_errores_de_la_expresion_regular():
    r = api.manejar("crear", {"modo": "ER", "er": "ab|"})
    assert not r["ok"] and r["errores"][0]["campo"] == "er" and r["errores"][0]["posicion"] == 3
    assert not api.manejar("crear", {"modo": "ER", "er": ""})["ok"]
    assert not api.manejar("crear", {"modo": "ER", "er": "(a"})["ok"]


# ---------------------------------------------------------------- simular
def test_simular_devuelve_la_traza():
    r = api.manejar("simular", {"automata": hacer(ejemplos.afd_intro_ab()), "cadena": "aabab"})
    assert r["ok"] and r["acepta"] and len(r["pasos"]) == 6
    assert r["pasos"][0] == {"indice": 0, "simbolo": None, "estados": ["q0"], "transiciones": []}
    assert r["pasos"][3]["estados"] == ["q1"]
    assert r["pasos"][3]["transiciones"] == [{"origen": "q0", "simbolo": "b", "destino": "q1"}]
    assert not api.manejar("simular", {"automata": hacer(ejemplos.afd_intro_ab()), "cadena": "aababa"})["acepta"]
    r = api.manejar("simular", {"automata": hacer(ejemplos.afnd_lambda_a_estrella_b_estrella()), "cadena": ""})
    assert r["acepta"] and r["pasos"][0]["estados"] == ["q0", "q1"]


# ---------------------------------------------------------------- operaciones
def operar(a, operacion):
    return api.manejar("operacion", {"automata": hacer(a), "operacion": operacion})


def comprobar_pasos(operacion):
    json.dumps(operacion)
    assert operacion["pasos"] and operacion["titulo"]
    for paso in operacion["pasos"]:
        assert paso["titulo"] and isinstance(paso["texto"], str)
        for t in paso["tablas"]:
            assert t["columnas"] and all(len(f) == len(t["columnas"]) for f in t["filas"]), (paso["titulo"], t)
            assert all(0 <= i < len(t["filas"]) for i in t.get("filas_resaltadas", []))
        g = paso["grafo"]
        if g:
            ids = [n["id"] for n in g["nodos"]]
            assert len(ids) == len(set(ids)) and g["clave"]
            assert all(a["origen"] in ids and a["destino"] in ids for a in g["aristas"]), paso["titulo"]
            assert all(isinstance(l["color"], int) for l in g["leyenda"])


def test_a_afd_con_paso_a_paso():
    for fabrica in (ejemplos.afnd_termina_en_01, ejemplos.afnd_lambda_a_estrella_b_estrella):
        original = fabrica()
        r = operar(original, "a_afd")
        assert r["ok"]
        comprobar_pasos(r["operacion"])
        resultado = Automata.desde_dict(r["operacion"]["resultado"]["automata"])
        assert resultado.es_determinista()
        iguales(original, resultado)
    r = operar(ejemplos.afnd_lambda_a_estrella_b_estrella(), "a_afd")
    titulos = [p["titulo"] for p in r["operacion"]["pasos"]]
    assert titulos == ["λ-clausura de cada estado", "Estado inicial del AFD", "Procesar {q0,q1}",
                       "Procesar {q1}", "AFD obtenido", "Renombrar los estados"]
    clausura = r["operacion"]["pasos"][0]["tablas"][0]
    assert clausura["filas"] == [["q0", "{q0,q1}"], ["q1", "{q1}"]]
    procesar = r["operacion"]["pasos"][2]["tablas"][0]
    assert procesar["columnas"][:3] == ["Símbolo", "mover(S, símbolo)", "λ-clausura"]
    assert procesar["filas"] == [["a", "{q0}", "{q0,q1}", "no"], ["b", "{q1}", "{q1}", "sí"]]
    sin_lambda = operar(ejemplos.afnd_termina_en_01(), "a_afd")["operacion"]["pasos"]
    assert sin_lambda[0]["titulo"] == "Estado inicial del AFD"          # sin λ no hay tabla de clausura


def test_la_construccion_va_creciendo():
    pasos = operar(ejemplos.afnd_termina_en_01(), "a_afd")["operacion"]["pasos"]
    crecimiento = [len(p["grafo"]["nodos"]) for p in pasos if p["grafo"]["clave"] == "afd"]
    assert crecimiento == sorted(crecimiento) and crecimiento[0] == 1 and crecimiento[-1] == 3


def test_minimizar_con_iteraciones():
    original = ejemplos.afd_minimizacion_8_estados()
    r = operar(original, "minimizar")
    assert r["ok"]
    comprobar_pasos(r["operacion"])
    titulos = [p["titulo"] for p in r["operacion"]["pasos"]]
    assert titulos == ["Preparación", "Partición inicial", "Iteración 1", "Iteración 2", "Iteración 3", "Autómata mínimo"]
    minimo = Automata.desde_dict(r["operacion"]["resultado"]["automata"])
    assert len(minimo.estados) == 5 and minimo.es_determinista()
    iguales(original, minimo)
    it1 = r["operacion"]["pasos"][2]
    assert it1["tablas"][0]["columnas"] == ["Estado", "Conjunto actual", "0", "1", "Conjunto nuevo"]
    assert len(it1["grafo"]["leyenda"]) == 4                         # X, M, Z, N de la clase (q3 ya no está)
    assert all(n["color"] is not None for n in it1["grafo"]["nodos"])
    assert "q3" in r["operacion"]["pasos"][0]["texto"]               # se avisa del inaccesible eliminado
    assert "estable" in r["operacion"]["pasos"][4]["texto"]


def test_completar_y_complemento():
    for fabrica in (ejemplos.afd_intro_01, ejemplos.afd_intro_ab):
        original = fabrica()
        r = operar(original, "completar")
        assert r["ok"]
        comprobar_pasos(r["operacion"])
        completo = Automata.desde_dict(r["operacion"]["resultado"]["automata"])
        assert completo.es_completo()
        iguales(original, completo)
    for nombre, fabrica in ejemplos.EJEMPLOS.items():
        original = fabrica()
        r = operar(original, "complemento")
        assert r["ok"], nombre
        comprobar_pasos(r["operacion"])
        c = Automata.desde_dict(r["operacion"]["resultado"]["automata"])
        for cadena in cadenas(original.alfabeto, 6):
            from automatas.core.finitos import acepta
            assert acepta(c, cadena) != acepta(original, cadena), (nombre, cadena)


def test_automata_a_er_y_a_thompson():
    for nombre, fabrica in ejemplos.EJEMPLOS.items():
        original = fabrica()
        r = operar(original, "a_er")
        assert r["ok"], nombre
        comprobar_pasos(r["operacion"])
        assert r["operacion"]["resultado"]["tipo"] == "er"
        iguala_regex(original, analizar(r["operacion"]["resultado"]["texto"]), 6)
        r = operar(original, "a_thompson")
        assert r["ok"], nombre
        comprobar_pasos(r["operacion"])
        resultado = Automata.desde_dict(r["operacion"]["resultado"]["automata"])
        assert resultado.tipo() in ("AFND-λ", "AFD")
        iguales(original, resultado, 6)


def test_pasos_de_thompson():
    r = api.manejar("crear", {"modo": "ER", "er": "(a|b)*abb"})
    pasos = r["operacion"]["pasos"]
    comprobar_pasos(r["operacion"])
    assert pasos[0]["titulo"] == "Expresión regular" and pasos[0]["grafo"] is None
    assert pasos[-1]["titulo"] == "AFND-λ completo" and len(pasos[-1]["grafo"]["nodos"]) == 14
    construccion = [p for p in pasos if p["grafo"] and p["grafo"]["clave"] == "thompson"]
    tamanos = [len(p["grafo"]["nodos"]) for p in construccion]
    assert tamanos == sorted(tamanos)
    assert any(n["resaltado"] for n in construccion[0]["grafo"]["nodos"])


def test_pasos_de_eliminacion_de_estados():
    pasos = operar(ejemplos.afnd_termina_en_01(), "a_er")["operacion"]["pasos"]
    assert pasos[0]["titulo"] == "Estados inicial y final únicos"
    assert [p["titulo"] for p in pasos[1:4]] == ["Eliminar q0", "Eliminar q1", "Eliminar q2"] or len(pasos) == 6
    assert pasos[-1]["titulo"] == "Expresión regular obtenida"
    nodos = [len(p["grafo"]["nodos"]) for p in pasos if p["grafo"]]
    assert nodos == sorted(nodos, reverse=True)                      # van quedando menos estados


def test_operaciones_invalidas_devuelven_mensajes():
    for operacion, original in [("minimizar", ejemplos.afnd_termina_en_01()),
                                ("minimizar", ejemplos.afnd_lambda_a_estrella_b_estrella()),
                                ("completar", ejemplos.afnd_termina_en_01())]:
        r = operar(original, operacion)
        assert not r["ok"] and "AFD" in r["mensaje"]
    assert not api.manejar("operacion", {"automata": hacer(ejemplos.afd_intro_ab()), "operacion": "volar"})["ok"]
    assert not api.manejar("operacion", {"operacion": "a_afd"})["ok"]
    assert not api.manejar("operacion", {"automata": {"estados": []}, "operacion": "a_afd"})["ok"]
    assert not api.manejar("nada", {})["ok"]


def test_ejemplos_para_la_interfaz():
    r = api.manejar("ejemplos", {})
    assert r["ok"] and len(r["automatas"]) == len(ejemplos.EJEMPLOS) and r["expresiones"]
    json.dumps(r)


# ---------------------------------------------------------------- servidor
def _servidor():
    srv = crear_servidor(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _pedir(url, datos=None, crudo=None):
    cuerpo = crudo if crudo is not None else (json.dumps(datos).encode() if datos is not None else None)
    peticion = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": "application/json"} if cuerpo is not None else {})
    try:
        with urllib.request.urlopen(peticion) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


def test_servidor_entrega_la_pagina_y_responde_a_la_api():
    srv, base = _servidor()
    try:
        estado, tipo, cuerpo = _pedir(base + "/")
        assert estado == 200 and "text/html" in tipo and "Laboratorio de autómatas" in cuerpo.decode()
        estado, tipo, _ = _pedir(base + "/estatico/js/main.js")
        assert estado == 200 and "javascript" in tipo
        estado, _, cuerpo = _pedir(base + "/api/crear", AFD_AB)
        assert estado == 200 and json.loads(cuerpo)["ok"]
        estado, _, cuerpo = _pedir(base + "/api/ejemplos")
        assert json.loads(cuerpo)["ok"]
        estado, _, cuerpo = _pedir(base + "/api/operacion", {"automata": hacer(ejemplos.afd_intro_ab()), "operacion": "minimizar"})
        assert json.loads(cuerpo)["ok"]
    finally:
        srv.shutdown(); srv.server_close()


def test_servidor_rechaza_rutas_peligrosas_y_peticiones_malas():
    srv, base = _servidor()
    try:
        for ruta in ("/estatico/../servidor.py", "/estatico/..%2f..%2fmain.py", "/main.py", "/estatico/no_existe.js"):
            assert _pedir(base + ruta)[0] == 404, ruta
        assert _pedir(base + "/api/crear", crudo=b"{no es json")[0] == 400
        estado, _, cuerpo = _pedir(base + "/api/inexistente", {})
        assert estado == 200 and json.loads(cuerpo)["ok"] is False
    finally:
        srv.shutdown(); srv.server_close()


def test_crear_servidor_usa_otro_puerto_si_esta_ocupado():
    primero = crear_servidor(0)
    try:
        ocupado = primero.server_address[1]
        segundo = crear_servidor(ocupado)
        assert segundo.server_address[1] != ocupado
        segundo.server_close()
    finally:
        primero.server_close()


def test_main_py_arranca_y_responde():
    import subprocess
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proceso = subprocess.Popen([sys.executable, "main.py", "--no-abrir", "--puerto", "0"], cwd=raiz,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        linea = proceso.stdout.readline()
        url = linea.split(" en ", 1)[1].split()[0]
        estado, tipo, cuerpo = _pedir(url)
        assert estado == 200 and "Laboratorio de autómatas" in cuerpo.decode()
        assert _pedir(url + "estatico/js/main.js")[1].startswith("text/javascript")
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)
