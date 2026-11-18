"""Pruebas de la interfaz en un navegador real (Chromium con Playwright).

Se omiten solas si playwright no está instalado:   pip install playwright && playwright install chromium
Con AUTOMATAS_CAPTURAS=carpeta guardan capturas de pantalla de cada escenario.
"""
import atexit
import json
import os
import re
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.web.servidor import crear_servidor  # noqa: E402

_E: dict = {}
CAPTURAS = os.environ.get("AUTOMATAS_CAPTURAS")


def _cerrar():
    for clave in ("navegador", "pw"):
        try:
            if clave in _E:
                (_E[clave].close if clave == "navegador" else _E[clave].stop)()
        except Exception:  # noqa: BLE001
            pass
    if "srv" in _E:
        _E["srv"].shutdown()
        _E["srv"].server_close()


def _entorno():
    if "navegador" in _E:
        return _E
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise unittest.SkipTest("falta playwright")
    srv = crear_servidor(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _E["srv"] = srv
    _E["base"] = f"http://127.0.0.1:{srv.server_address[1]}/"
    atexit.register(_cerrar)
    try:
        _E["pw"] = sync_playwright().start()
        _E["navegador"] = _E["pw"].chromium.launch()
    except Exception as error:  # noqa: BLE001
        raise unittest.SkipTest(f"no hay navegador para playwright ({error.__class__.__name__})")
    return _E


class Sesion:
    """Una página nueva con registro de errores de consola."""

    def __init__(self, ancho=1440, alto=900):
        e = _entorno()
        self.contexto = e["navegador"].new_context(viewport={"width": ancho, "height": alto}, accept_downloads=True)
        self.pag = self.contexto.new_page()
        self.pag.set_default_timeout(8000)
        self.errores = []
        self.pag.on("console", lambda m: self.errores.append(m.text) if m.type == "error" else None)
        self.pag.on("pageerror", lambda x: self.errores.append(str(x)))
        self.pag.goto(e["base"])
        self.pag.wait_for_selector("#matriz tbody tr")
        self.pag.wait_for_selector('#ejemplos option[value^="a:"]', state="attached")

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        if tipo is None:
            assert not self.errores, f"errores en la consola del navegador: {self.errores}"
        self.contexto.close()

    def captura(self, nombre):
        if CAPTURAS:
            os.makedirs(CAPTURAS, exist_ok=True)
            self.pag.screenshot(path=os.path.join(CAPTURAS, f"{nombre}.png"), full_page=True)

    # --- acciones frecuentes
    def modo(self, modo):
        self.pag.click(f'.segmento[data-modo="{modo}"]')

    def celda(self, q, s, valor):
        self.pag.fill(f'#matriz tr[data-q="{q}"] .celda[data-s="{s}"]', valor)

    def final(self, q, marcado=True):
        self.pag.set_checked(f'#matriz tr[data-q="{q}"] .c-final', marcado)

    def ejemplo(self, nombre):
        self.pag.select_option("#ejemplos", label=nombre)

    def crear(self):
        self.pag.click("#btn-crear")
        self.pag.wait_for_function("document.querySelector('#mensajes').children.length > 0")

    def nodos(self):
        return self.pag.locator("#diagrama .n-g").count()

    def operacion(self, id_):
        self.pag.click(f'.op[data-op="{id_}"]')
        self.pag.wait_for_selector("#tarjeta-pasos:not([hidden])")
        self.pag.wait_for_function(
            "document.querySelector('#pv-titulo').textContent.length > 0 && document.querySelector('#pv-contador').textContent.includes('Paso 1')")

    def paso(self):
        return self.pag.inner_text("#pv-paso")

    def contador(self):
        return self.pag.inner_text("#pv-contador")

    def total_pasos(self):
        return int(re.search(r"de (\d+)", self.contador()).group(1))

    def al_final(self):
        self.pag.click("#pv-fin")

    def filas_editor(self):
        return self.pag.locator("#matriz tbody tr").count()


def construir_afd_intro_ab(s):
    s.pag.click("#btn-estado")                      # q2
    for q, a, b in (("q0", "q0", "q1"), ("q1", "q1", "q2"), ("q2", "q1", "q1")):
        s.celda(q, "a", a); s.celda(q, "b", b)
    s.final("q0"); s.final("q2")


# ---------------------------------------------------------------- pruebas
def test_la_pagina_abre_sin_errores_y_con_su_estructura():
    with Sesion() as s:
        assert s.pag.title() == "Laboratorio de autómatas"
        assert s.pag.locator("#segmentos-tipo .segmento").count() == 4 and s.filas_editor() == 2
        assert s.pag.locator("#tarjeta-operaciones").is_hidden()
        assert "Crea un autómata" in s.pag.inner_text("#diagrama")
        s.captura("01_inicio")


def test_construir_un_afd_a_mano_y_dibujarlo():
    with Sesion() as s:
        construir_afd_intro_ab(s)
        s.crear()
        assert "Autómata creado: AFD con 3 estados" in s.pag.inner_text("#mensajes")
        assert s.nodos() == 3 and s.pag.locator("#diagrama .n-fin").count() == 2
        assert s.pag.locator("#tarjeta-operaciones").is_visible()
        habilitadas = {b.get_attribute("data-op") for b in s.pag.locator("#lista-ops .op:not([disabled])").all()}
        assert habilitadas == {"simular", "minimizar", "completar", "complemento", "a_er", "a_thompson"}
        assert s.pag.locator('.op[data-op="a_afd"]').is_disabled()
        assert "AFD con 3 estados" in s.pag.inner_text("#titulo-diagrama")
        s.captura("02_afd_creado")


def test_errores_de_la_definicion_se_marcan_en_la_tabla():
    with Sesion() as s:
        s.celda("q0", "a", "q9")
        s.celda("q0", "b", "q0, q1")
        s.crear()
        texto = s.pag.inner_text("#mensajes")
        assert "no existe" in texto and "un solo destino" in texto and "Elige el estado inicial" not in texto
        assert s.pag.locator("#matriz .celda-error").count() == 2
        assert s.pag.locator("#tarjeta-operaciones").is_hidden()
        s.captura("03_errores")
        s.celda("q0", "a", "q1")                                # al corregir desaparece la marca roja
        assert s.pag.locator('#matriz tr[data-q="q0"] .celda[data-s="a"].celda-error').count() == 0


def test_tipo_afnd_acepta_varios_destinos_y_afnd_lambda_agrega_columna():
    with Sesion() as s:
        s.modo("AFND")
        s.celda("q0", "a", "q0, q1"); s.celda("q0", "b", "q0"); s.celda("q1", "b", "q1")
        s.final("q1")
        s.crear()
        assert "AFND con 2 estados" in s.pag.inner_text("#mensajes")
        assert s.pag.locator('.op[data-op="a_afd"]').is_enabled() and s.pag.locator('.op[data-op="minimizar"]').is_disabled()
        s.modo("AFND-LAMBDA")
        assert s.pag.locator("#matriz th.col-lambda").count() == 1
        s.celda("q0", "λ", "q1")
        s.crear()
        assert "AFND-λ con 2 estados" in s.pag.inner_text("#mensajes")
        assert "λ" in s.pag.inner_text("#diagrama")
        s.captura("04_afnd_lambda")


def test_probar_una_cadena_paso_a_paso_y_con_play():
    with Sesion() as s:
        s.ejemplo("AFD de la introducción (a,b)"); s.crear()
        s.pag.click('.op[data-op="simular"]')
        s.pag.wait_for_selector("#tarjeta-simulacion:not([hidden])")
        s.pag.fill("#sm-cadena", "aabab")
        s.pag.click("#sm-ejecutar")
        s.pag.wait_for_selector("#sm-cinta .simbolo")
        assert s.pag.locator("#sm-cinta .simbolo").count() == 5 and s.pag.locator("#sm-traza div").count() == 6
        assert s.pag.locator("#diagrama .n-act").count() == 1 and s.pag.locator("#sm-veredicto .insignia").count() == 0
        s.pag.click("#sm-sig"); s.pag.click("#sm-sig"); s.pag.click("#sm-sig")
        assert s.pag.locator('#diagrama .n-act[data-id="q1"]').count() == 1
        assert s.pag.locator("#diagrama .e-act").count() == 1
        assert s.pag.locator("#sm-cinta .simbolo.leido").count() == 3
        s.pag.click("#sm-atras")
        assert s.pag.locator("#sm-cinta .simbolo.leido").count() == 2
        s.pag.click("#sm-fin")
        assert s.pag.inner_text("#sm-veredicto .insignia") == "ACEPTADA"
        s.captura("05_simulacion")
        s.pag.fill("#sm-cadena", "aababa"); s.pag.click("#sm-ejecutar")
        s.pag.fill("#sm-vel", "4")
        s.pag.click("#sm-play")
        s.pag.wait_for_selector("#sm-veredicto .insignia", timeout=6000)
        assert s.pag.inner_text("#sm-veredicto .insignia") == "RECHAZADA"
        s.pag.click("#sm-cerrar")
        assert s.pag.locator("#diagrama .n-act").count() == 0 and "Diagrama" in s.pag.inner_text("#titulo-diagrama")


def test_cadena_vacia_y_simbolo_invalido():
    with Sesion() as s:
        s.ejemplo("AFND-λ: a*b*"); s.crear()
        s.pag.click('.op[data-op="simular"]'); s.pag.click("#sm-ejecutar")
        s.pag.wait_for_selector("#sm-veredicto .insignia")
        assert s.pag.inner_text("#sm-veredicto .insignia") == "ACEPTADA"
        assert s.pag.locator("#diagrama .n-act").count() == 2                # {q0, q1} por la λ-clausura
        s.pag.fill("#sm-cadena", "abc"); s.pag.click("#sm-ejecutar")
        s.pag.click("#sm-fin")
        assert "no pertenece" in s.pag.inner_text("#sm-veredicto")


def test_afnd_lambda_a_afd_muestra_clausura_y_subconjuntos():
    with Sesion() as s:
        s.ejemplo("AFND-λ: a*b*"); s.crear()
        s.operacion("a_afd")
        assert s.total_pasos() == 6 and "λ-clausura de cada estado" in s.paso()
        assert "{q0,q1}" in s.pag.inner_text("#pv-paso table")
        assert s.pag.locator("#diagrama .e-act").count() >= 1                    # flechas λ resaltadas
        s.captura("06_clausura")
        s.pag.click("#pv-sig"); s.pag.click("#pv-sig")
        assert "Procesar {q0,q1}" in s.paso() and "mover(S, símbolo)" in s.paso() and s.pag.locator("#pv-paso table").count() == 2
        assert s.nodos() == 2
        s.captura("07_subconjuntos")
        s.al_final()
        assert "renombrar" in s.paso().lower() and "equivalencia de nombres" in s.paso().lower()
        assert s.pag.locator("#pv-usar").is_visible()
        s.captura("08_afd_final")


def test_minimizar_muestra_cada_iteracion_y_el_automata_final():
    with Sesion() as s:
        s.ejemplo("AFD de minimización (8 estados)"); s.crear()
        assert s.nodos() == 8
        s.operacion("minimizar")
        assert s.total_pasos() == 6
        assert "q3" in s.paso() and "inaccesibles" in s.paso()
        s.pag.click("#pv-sig")
        assert "Partición inicial" in s.paso() and s.pag.locator("#diagrama .leyenda span").count() == 2
        s.pag.click("#pv-sig")
        assert "Iteración 1" in s.paso() and s.pag.locator("#diagrama .leyenda span").count() == 4
        assert s.pag.locator('#diagrama [class*="n-col"]').count() == 7           # todos los nodos coloreados
        s.captura("09_iteracion1")
        s.pag.click("#pv-sig"); s.pag.click("#pv-sig")
        assert "estable" in s.paso()
        s.pag.click("#pv-sig")
        assert "Autómata mínimo" in s.paso() and s.nodos() == 5
        assert "tenía 7 estados y el mínimo tiene 5" in s.paso() or "8 estados y el mínimo tiene 5" in s.paso()
        s.captura("10_minimo")
        s.pag.click("#pv-usar")
        assert s.filas_editor() == 5 and s.pag.locator("#tarjeta-pasos").is_hidden() and s.nodos() == 5


def test_no_se_puede_minimizar_un_afnd_y_el_boton_lo_explica():
    with Sesion() as s:
        s.ejemplo("AFND: termina en 01"); s.crear()
        boton = s.pag.locator('.op[data-op="minimizar"]')
        assert boton.is_disabled() and "AFD" in boton.get_attribute("title")


def test_expresion_regular_thompson_y_encadenar_operaciones():
    with Sesion() as s:
        s.modo("ER")
        assert s.pag.locator("#panel-er").is_visible() and s.pag.locator("#panel-tabla").is_hidden()
        s.pag.fill("#er-texto", "(a|b)*abb")
        s.crear()
        assert "AFND-λ con 14 estados" in s.pag.inner_text("#mensajes")
        assert "Thompson" in s.pag.inner_text("#pv-titulo") and s.total_pasos() >= 10
        s.pag.click("#pv-sig"); s.pag.click("#pv-sig")
        assert s.nodos() >= 2
        s.captura("11_thompson_inicio")
        s.al_final()
        assert s.nodos() == 14
        s.captura("12_thompson_final")
        s.pag.click("#pv-usar")                                              # el AFND-λ pasa a la tabla
        assert s.filas_editor() == 14 and s.pag.locator('.segmento[data-modo="AFND-LAMBDA"].activo').count() == 1
        s.operacion("a_afd"); s.al_final()
        s.pag.click("#pv-usar")
        assert s.filas_editor() == 5
        s.operacion("minimizar"); s.al_final()
        assert s.nodos() == 4
        s.captura("13_minimo_er")


def test_errores_de_sintaxis_en_la_expresion_regular():
    with Sesion() as s:
        s.modo("ER")
        s.pag.fill("#er-texto", "ab|")
        s.crear()
        assert "Falta un operando" in s.pag.inner_text("#mensajes") and s.pag.locator("#tarjeta-operaciones").is_hidden()
        s.pag.fill("#er-texto", "")
        s.pag.press("#er-texto", "Enter")
        s.pag.wait_for_function("document.querySelector('#mensajes').textContent.includes('vacía')")


def test_atajos_de_la_expresion_regular_insertan_en_el_cursor():
    with Sesion() as s:
        s.modo("ER")
        s.pag.fill("#er-texto", "ab")
        s.pag.click('#atajos-er button[data-ins="()"]')
        s.pag.keyboard.type("c")
        assert s.pag.input_value("#er-texto") == "ab(c)"
        s.pag.click('#atajos-er button[data-ins="λ"]')                          # se inserta donde está el cursor
        assert s.pag.input_value("#er-texto") == "ab(cλ)"


def test_automata_a_er_y_a_thompson():
    with Sesion() as s:
        s.ejemplo("AFND: termina en 01"); s.crear()
        s.operacion("a_er"); s.al_final()
        er = s.pag.inner_text("#pv-er")
        assert er and "Expresión regular obtenida" in s.paso()
        s.captura("14_a_er")
        s.pag.click("#pv-usar-er")
        assert s.pag.input_value("#er-texto") == er and s.pag.locator('.segmento[data-modo="ER"].activo').count() == 1
        s.crear()
        assert "AFND-λ" in s.pag.inner_text("#mensajes")
        s.ejemplo("AFD de la introducción (a,b)"); s.crear()
        s.operacion("a_thompson"); s.al_final()
        assert "AFND-λ completo" in s.paso()


def test_completar_y_complemento():
    with Sesion() as s:
        s.ejemplo("AFD incompleto (0,1)"); s.crear()
        assert "incompleto" in s.pag.inner_text("#mensajes")
        s.operacion("completar")
        assert "Transiciones que faltan" in s.paso() and s.nodos() == 4
        s.operacion("complemento"); s.al_final()
        assert "Intercambiar" in s.paso()
        s.captura("15_complemento")


def test_arrastrar_un_estado_mueve_el_nodo_y_sus_flechas():
    with Sesion() as s:
        s.ejemplo("AFD de la introducción (a,b)"); s.crear()
        circulo = s.pag.locator('#diagrama .n-g[data-id="q1"] circle.n-c')
        antes = circulo.bounding_box()
        trazos_antes = s.pag.eval_on_selector_all("#diagrama .e-l", "els => els.map(e => e.getAttribute('d'))")
        cx, cy = antes["x"] + antes["width"] / 2, antes["y"] + antes["height"] / 2
        s.pag.mouse.move(cx, cy); s.pag.mouse.down()
        s.pag.mouse.move(cx + 90, cy + 70, steps=8)
        s.pag.mouse.up()
        despues = circulo.bounding_box()
        assert abs((despues["x"] + despues["width"] / 2) - (cx + 90)) < 4
        assert abs((despues["y"] + despues["height"] / 2) - (cy + 70)) < 4
        trazos_despues = s.pag.eval_on_selector_all("#diagrama .e-l", "els => els.map(e => e.getAttribute('d'))")
        assert trazos_antes != trazos_despues
        s.captura("16_arrastrado")
        s.pag.click("#btn-reorganizar")
        vuelto = circulo.bounding_box()
        assert abs(vuelto["x"] - antes["x"]) < 4 and abs(vuelto["y"] - antes["y"]) < 4


def test_ajustar_un_diagrama_grande_a_la_vista():
    with Sesion() as s:
        s.modo("ER"); s.pag.fill("#er-texto", "(a|b)*abb"); s.crear()
        s.pag.click("#pv-cerrar")
        ancho_lienzo = s.pag.evaluate("document.querySelector('#diagrama .lienzo').clientWidth")
        real = s.pag.evaluate("document.querySelector('#diagrama svg').getBoundingClientRect().width")
        assert real > ancho_lienzo + 20                                     # hay que desplazarse
        s.pag.click("#btn-ajustar")
        ajustado = s.pag.evaluate("document.querySelector('#diagrama svg').getBoundingClientRect().width")
        assert ajustado <= ancho_lienzo + 1 and s.pag.inner_text("#btn-ajustar") == "Tamaño real"
        s.pag.click("#btn-ajustar")
        assert s.pag.inner_text("#btn-ajustar") == "Ajustar a la vista"


def test_editar_la_tabla_renombrar_agregar_y_quitar():
    with Sesion() as s:
        s.pag.click("#btn-estado")
        assert s.filas_editor() == 3 and s.pag.locator('#matriz tr[data-q="q2"]').count() == 1
        s.celda("q0", "a", "q1, q2")
        s.pag.locator('#matriz tr[data-q="q1"] .nombre-estado').fill("meta")
        s.pag.locator('#matriz tr[data-q="q1"] .nombre-estado').blur()
        assert s.pag.locator('#matriz tr[data-q="meta"]').count() == 1
        assert s.pag.input_value('#matriz tr[data-q="q0"] .celda[data-s="a"]') == "meta, q2"
        s.pag.locator('#matriz tr[data-q="q2"] .nombre-estado').fill("meta")             # nombre repetido: se rechaza
        s.pag.locator('#matriz tr[data-q="q2"] .nombre-estado').blur()
        assert s.pag.locator('#matriz tr[data-q="q2"]').count() == 1 and "Ya existe" in s.pag.inner_text("#avisos")
        s.pag.click('#matriz tr[data-q="q2"] .borrar')
        assert s.filas_editor() == 2 and s.pag.input_value('#matriz tr[data-q="q0"] .celda[data-s="a"]') == "meta"
        s.pag.fill("#nuevo-simbolo", "01λ")
        s.pag.click("#btn-simbolo")
        assert s.pag.locator("#chips-alfabeto .chip").count() == 4
        s.pag.click('#chips-alfabeto .chip button[data-s="a"]')
        assert s.pag.locator("#chips-alfabeto .chip").count() == 3 and s.pag.locator('#matriz .celda[data-s="a"]').count() == 0
        s.pag.click("#btn-limpiar")
        assert s.filas_editor() == 2 and s.pag.locator("#chips-alfabeto .chip").count() == 2


def test_la_tabla_avisa_mientras_se_escribe():
    with Sesion() as s:
        s.celda("q0", "a", "zz")
        assert s.pag.locator('#matriz tr[data-q="q0"] .celda[data-s="a"].celda-aviso').count() == 1
        s.celda("q0", "a", "q1, q0")                                          # varios destinos en un AFD
        assert s.pag.locator('#matriz tr[data-q="q0"] .celda[data-s="a"].celda-aviso').count() == 1
        s.modo("AFND")
        assert s.pag.locator("#matriz .celda-aviso").count() == 0


def test_guardar_y_abrir_un_automata():
    with Sesion() as s:
        s.ejemplo("AFND: termina en 01"); s.crear()
        with s.pag.expect_download() as descarga:
            s.pag.click("#btn-guardar")
        ruta = descarga.value.path()
        datos = json.load(open(ruta, encoding="utf-8"))
        assert datos["tipo"] == "AFND" and datos["estados"] == ["q0", "q1", "q2"] and datos["finales"] == ["q2"]
        s.pag.click("#btn-limpiar")
        s.pag.set_input_files("#archivo", ruta)
        s.pag.wait_for_function("document.querySelectorAll('#matriz tbody tr').length === 3")
        assert s.pag.locator('.segmento[data-modo="AFND"].activo').count() == 1
        assert s.pag.input_value('#matriz tr[data-q="q0"] .celda[data-s="0"]') in ("q0, q1", "q1, q0")
        s.crear()
        assert "AFND con 3 estados" in s.pag.inner_text("#mensajes")


def test_abrir_un_archivo_invalido_avisa():
    with Sesion() as s:
        import tempfile
        ruta = os.path.join(tempfile.mkdtemp(), "malo.json")
        open(ruta, "w").write('{"hola": 1}')
        s.pag.set_input_files("#archivo", ruta)
        s.pag.wait_for_function("document.querySelector('#avisos').textContent.includes('formato')")


def test_descargar_el_diagrama_como_svg():
    with Sesion() as s:
        s.ejemplo("AFD de la introducción (a,b)"); s.crear()
        with s.pag.expect_download() as descarga:
            s.pag.click("#btn-svg")
        contenido = open(descarga.value.path(), encoding="utf-8").read()
        assert contenido.startswith("<svg") and "<style>" in contenido and "--fondo:" in contenido and contenido.count("n-g") >= 3


def test_modo_oscuro_se_recuerda_y_el_diagrama_lo_sigue():
    with Sesion() as s:
        s.ejemplo("AFD de la introducción (a,b)"); s.crear()
        fondo_claro = s.pag.evaluate("getComputedStyle(document.body).backgroundColor")
        s.pag.click(".interruptor")
        assert s.pag.get_attribute("html", "data-tema") == "oscuro"
        assert s.pag.evaluate("getComputedStyle(document.body).backgroundColor") != fondo_claro
        s.captura("17_oscuro")
        s.pag.reload()
        s.pag.wait_for_selector("#matriz tbody tr")
        assert s.pag.get_attribute("html", "data-tema") == "oscuro"
        s.pag.click(".interruptor")
        assert s.pag.get_attribute("html", "data-tema") == "claro"


def test_pestanas_pendientes():
    with Sesion() as s:
        s.pag.click('.pestana[data-vista="pila"]')
        assert s.pag.locator("#vista-pila").is_visible() and s.pag.locator("#vista-finitos").is_hidden()
        s.pag.click('.pestana[data-vista="finitos"]')
        assert s.pag.locator("#vista-finitos").is_visible()


def test_cambiar_la_definicion_despues_de_crear_avisa_y_se_puede_actualizar():
    with Sesion() as s:
        s.ejemplo("AFD de la introducción (a,b)"); s.crear()
        s.celda("q0", "a", "q2")
        assert "cambios sin aplicar" in s.pag.inner_text("#btn-crear")
        s.crear()
        assert s.pag.inner_text("#btn-crear") == "Actualizar autómata"


def test_pantalla_angosta_apila_las_columnas():
    with Sesion(ancho=800, alto=900) as s:
        a = s.pag.locator("#tarjeta-tipo").bounding_box()
        b = s.pag.locator("#tarjeta-diagrama").bounding_box()
        assert b["y"] > a["y"] and abs(b["x"] - a["x"]) < 5
        s.captura("18_angosto")
