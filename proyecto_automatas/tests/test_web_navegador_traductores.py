"""Pruebas en navegador real de la pestaña Traductores (Moore y Mealy)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_web_navegador import Sesion  # noqa: E402


class SesionTr(Sesion):
    """Abre la pestaña Traductores y trae atajos para su editor."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.pag.click('.pestana[data-vista="traductores"]')
        self.pag.wait_for_selector("#tr-matriz tbody tr")
        self.pag.wait_for_selector('#tr-ejemplos option[value="0"]', state="attached")

    def tipo(self, tipo):
        self.pag.click(f'#tr-segmentos .segmento[data-tipo="{tipo}"]')

    def celda(self, q, s, valor):
        self.pag.fill(f'#tr-matriz tr[data-q="{q}"] .celda[data-s="{s}"]', valor)

    def salida(self, q, valor):
        self.pag.fill(f'#tr-matriz tr[data-q="{q}"] .celda-salida', valor)

    def nombre(self, q, nuevo):
        campo = self.pag.locator(f'#tr-matriz tr[data-q="{q}"] .nombre-estado')
        campo.fill(nuevo)
        campo.blur()

    def ejemplo(self, nombre):
        self.pag.select_option("#tr-ejemplos", label=nombre)

    def crear(self):
        self.pag.click("#tr-crear")
        self.pag.wait_for_function("document.querySelector('#tr-mensajes').children.length > 0")

    def nodos(self):
        return self.pag.locator("#tr-diagrama .n-g").count()

    def filas(self):
        return self.pag.locator("#tr-matriz tbody tr").count()

    def traducir(self, cadena):
        self.pag.click('#tr-ops .op[data-op="traducir"]')
        self.pag.wait_for_selector("#tr-sim:not([hidden])")
        self.pag.fill('#tr-sim [data-x="cadena"]', cadena)
        self.pag.click('#tr-sim [data-x="ejecutar"]')
        self.pag.wait_for_selector('#tr-sim [data-x="traza"] div')


def construir_moore_paridad(s):
    s.nombre("q0", "P"); s.nombre("q1", "I")
    s.salida("P", "a"); s.salida("I", "b")
    s.celda("P", "0", "P"); s.celda("P", "1", "I"); s.celda("I", "0", "I"); s.celda("I", "1", "P")


def test_la_pestana_se_abre_y_el_editor_cambia_con_el_tipo():
    with SesionTr() as s:
        assert s.pag.locator("#vista-traductores").is_visible() and s.pag.locator("#vista-finitos").is_hidden()
        assert s.filas() == 2 and s.pag.locator("#tr-matriz th.col-salida").count() == 1      # Moore: columna Salida
        assert "Γ" in s.pag.inner_text("#tr-gamma") and s.pag.locator("#tr-ops").is_hidden()
        s.tipo("mealy")
        assert s.pag.locator("#tr-matriz th.col-salida").count() == 0 and "destino/salida" in s.pag.inner_text("#tr-ayuda")
        assert s.pag.locator('#tr-segmentos .segmento[data-tipo="mealy"].activo').count() == 1
        s.captura("20_tr_inicio")


def test_construir_un_moore_a_mano_y_traducir_paso_a_paso():
    with SesionTr() as s:
        construir_moore_paridad(s)
        assert "{a, b}" in s.pag.inner_text("#tr-gamma")
        s.crear()
        assert "Máquina de Moore creada con 2 estados" in s.pag.inner_text("#tr-mensajes")
        assert "no se emite la salida del estado inicial" in s.pag.inner_text("#tr-mensajes")
        assert s.nodos() == 2 and s.pag.locator("#tr-diagrama .n-sub").count() == 2
        assert "/a" in s.pag.inner_text("#tr-diagrama") and "/b" in s.pag.inner_text("#tr-diagrama")
        s.captura("21_moore_creado")
        s.traducir("0110")
        assert s.pag.locator('#tr-sim [data-x="entrada"] .simbolo').count() == 4
        assert "(aún no hay salida)" in s.pag.inner_text('#tr-sim [data-x="salida"]')
        assert s.pag.locator("#tr-diagrama .n-act").count() == 1
        s.pag.click('#tr-sim [data-x="sig"]'); s.pag.click('#tr-sim [data-x="sig"]')
        assert s.pag.inner_text('#tr-sim [data-x="salida"]').replace("\n", "") == "ab"
        assert s.pag.locator('#tr-sim [data-x="salida"] .simbolo.nuevo').count() == 1
        assert s.pag.locator("#tr-diagrama .e-act").count() == 1
        assert "emite b" in s.pag.inner_text('#tr-sim [data-x="traza"] .actual')
        s.pag.click('#tr-sim [data-x="fin"]')
        assert s.pag.inner_text('#tr-sim [data-x="veredicto"] .insignia') == "SALIDA: abaa"
        s.captura("22_moore_traduccion")
        s.pag.click('#tr-sim [data-x="atras"]')
        assert s.pag.locator('#tr-sim [data-x="veredicto"] .insignia').count() == 0
        s.pag.click('#tr-sim [data-x="cerrar"]')
        assert s.pag.locator("#tr-diagrama .n-act").count() == 0


def test_mealy_de_clase_con_salidas_en_las_flechas_y_play():
    with SesionTr() as s:
        s.ejemplo("Mealy: detecta 011"); s.crear()
        assert s.pag.locator('#tr-segmentos .segmento[data-tipo="mealy"].activo').count() == 1
        assert "Máquina de Mealy creada con 3 estados" in s.pag.inner_text("#tr-mensajes")
        assert s.nodos() == 3 and s.pag.locator("#tr-diagrama .n-sub").count() == 0
        assert "1/1" in s.pag.inner_text("#tr-diagrama") and "0/0" in s.pag.inner_text("#tr-diagrama")
        s.captura("23_mealy_creado")
        s.traducir("011011")
        s.pag.fill('#tr-sim [data-x="vel"]', "4")
        s.pag.click('#tr-sim [data-x="play"]')
        s.pag.wait_for_selector('#tr-sim [data-x="veredicto"] .insignia', timeout=6000)
        assert s.pag.inner_text('#tr-sim [data-x="veredicto"] .insignia') == "SALIDA: 001001"


def test_traducir_en_lote():
    with SesionTr() as s:
        s.ejemplo("Moore: suma parcial módulo 5"); s.crear()
        s.pag.click('#tr-ops .op[data-op="lote"]')
        s.pag.wait_for_selector("#tr-lote:not([hidden])")
        s.pag.fill('#tr-lote [data-x="texto"]', "32130\nλ\n\n0\n3x")
        s.pag.click('#tr-lote [data-x="ejecutar"]')
        s.pag.wait_for_selector("#tr-lote tbody tr")
        filas = s.pag.eval_on_selector_all("#tr-lote tbody tr", "trs => trs.map(t => [...t.children].map(c => c.textContent))")
        assert [f[:2] for f in filas] == [["32130", "30144"], ["λ", "λ"], ["0", "0"], ["3x", "3"]]
        assert s.pag.locator("#tr-lote tr.mala").count() == 1 and "no pertenece" in filas[3][3]
        assert "4 cadenas traducidas" in s.pag.inner_text('#tr-lote [data-x="nota"]')
        s.captura("24_lote")
        s.pag.fill('#tr-lote [data-x="texto"]', "")
        s.pag.click('#tr-lote [data-x="ejecutar"]')
        assert "al menos una cadena" in s.pag.inner_text("#avisos")


def test_errores_de_la_definicion_se_marcan():
    with SesionTr() as s:
        s.celda("q0", "0", "zz"); s.celda("q0", "1", "q0, q1")
        s.crear()
        texto = s.pag.inner_text("#tr-mensajes")
        assert "no existe" in texto and "un solo destino" in texto
        assert s.pag.locator("#tr-matriz .celda-error").count() == 2 and s.pag.locator("#tr-ops").is_hidden()
        s.captura("25_tr_errores")
        s.tipo("mealy")
        s.celda("q0", "0", "q1/a, q0/b"); s.celda("q0", "1", "q9/x")
        s.crear()
        texto = s.pag.inner_text("#tr-mensajes")
        assert "solo cabe una transición" in texto and "no existe" in texto
        s.celda("q0", "0", "q1/λa")
        s.celda("q0", "1", "q0/b")
        s.crear()
        assert "no se mezcla" in s.pag.inner_text("#tr-mensajes")


def test_aviso_de_transiciones_que_faltan_y_traduccion_que_se_detiene():
    with SesionTr() as s:
        s.tipo("mealy")
        s.celda("q0", "0", "q1/x")
        s.crear()
        assert "Faltan transiciones" in s.pag.inner_text("#tr-mensajes")
        s.traducir("00")
        s.pag.click('#tr-sim [data-x="fin"]')
        assert "SE DETUVO" in s.pag.inner_text('#tr-sim [data-x="veredicto"]') and "No hay transición" in s.pag.inner_text('#tr-sim [data-x="veredicto"]')


def test_editar_la_tabla_de_traductores():
    with SesionTr() as s:
        s.tipo("mealy")
        s.celda("q0", "0", "q1/a")
        s.nombre("q1", "meta")
        assert s.pag.input_value('#tr-matriz tr[data-q="q0"] .celda[data-s="0"]') == "meta/a"        # el destino se renombra
        s.pag.click("#tr-btn-estado")
        assert s.filas() == 3 and s.pag.locator('#tr-matriz tr[data-q="q1"]').count() == 1       # reutiliza el nombre libre q1
        s.celda("q1", "1", "q1/z")
        assert "z" in s.pag.inner_text("#tr-gamma") and "a" in s.pag.inner_text("#tr-gamma")
        s.pag.click('#tr-matriz tr[data-q="meta"] .borrar')
        assert s.filas() == 2 and s.pag.input_value('#tr-matriz tr[data-q="q0"] .celda[data-s="0"]') == ""
        s.pag.fill("#tr-nuevo", "ab/")
        s.pag.click("#tr-btn-simbolo")
        assert s.pag.locator("#tr-chips .chip").count() == 4                                        # 0, 1, a, b (la «/» se descarta)
        s.pag.click('#tr-chips .chip button[data-s="0"]')
        assert s.pag.locator('#tr-matriz .celda[data-s="0"]').count() == 0
        s.pag.click("#tr-limpiar")
        assert s.filas() == 2 and s.pag.locator("#tr-chips .chip").count() == 2
        s.tipo("moore")
        s.celda("q0", "0", "zz")
        assert s.pag.locator('#tr-matriz tr[data-q="q0"] .celda[data-s="0"].celda-aviso').count() == 1


def test_guardar_abrir_y_descargar_svg_de_una_maquina():
    with SesionTr() as s:
        s.ejemplo("Mealy: paridad de unos"); s.crear()
        with s.pag.expect_download() as d:
            s.pag.click("#tr-guardar")
        ruta = d.value.path()
        datos = json.load(open(ruta, encoding="utf-8"))
        assert datos["tipo"] == "mealy" and datos["estados"] == ["I", "P"] and datos["inicial"] == "P"
        with s.pag.expect_download() as d2:
            s.pag.click("#tr-btn-svg")
        svg = open(d2.value.path(), encoding="utf-8").read()
        assert svg.startswith("<svg") and "1/b" in svg
        s.pag.click("#tr-limpiar"); s.tipo("moore")
        s.pag.set_input_files("#tr-archivo", ruta)
        s.pag.wait_for_function("document.querySelector('#tr-segmentos .segmento[data-tipo=\"mealy\"].activo') !== null")
        assert s.pag.input_value('#tr-matriz tr[data-q="P"] .celda[data-s="1"]') == "I/b"
        s.crear()
        assert "Mealy creada con 2 estados" in s.pag.inner_text("#tr-mensajes")
        ruta_mala = os.path.join(os.path.dirname(ruta), "mala.json")
        open(ruta_mala, "w").write('{"tipo": "otra"}')
        s.pag.set_input_files("#tr-archivo", ruta_mala)
        s.pag.wait_for_function("document.querySelector('#avisos').textContent.includes('formato')")


def test_el_diagrama_de_traductores_se_arrastra_y_las_dos_pestanas_no_se_mezclan():
    with SesionTr() as s:
        s.ejemplo("Moore: detecta 011"); s.crear()
        c = s.pag.locator('#tr-diagrama .n-g[data-id="E1"] circle.n-c')
        a = c.bounding_box(); cx, cy = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
        s.pag.mouse.move(cx, cy); s.pag.mouse.down(); s.pag.mouse.move(cx + 60, cy + 50, steps=6); s.pag.mouse.up()
        b = c.bounding_box()
        assert abs((b["x"] + b["width"] / 2) - (cx + 60)) < 4
        s.pag.click(".interruptor")
        s.captura("26_tr_oscuro")
        s.pag.click(".interruptor")
        s.pag.click('.pestana[data-vista="finitos"]')                      # la pantalla de finitos sigue intacta
        assert s.pag.locator("#segmentos-tipo .segmento").count() == 4 and s.pag.locator("#matriz tbody tr").count() == 2
        s.pag.select_option("#ejemplos", label="AFD de la introducción (a,b)")
        s.pag.click("#btn-crear")
        s.pag.wait_for_function("document.querySelector('#mensajes').children.length > 0")
        assert s.pag.locator("#diagrama .n-g").count() == 3
        s.pag.click('.pestana[data-vista="traductores"]')
        assert s.pag.locator("#tr-diagrama .n-g").count() == 4
