"""Pruebas en navegador real de las pestañas Pila y Turing."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.turing import ejecutar  # noqa: E402
from automatas.datos.ejemplos_turing import mt_omega_c_omega_1_cinta  # noqa: E402
from tests.test_web_navegador import Sesion  # noqa: E402


class SesionPl(Sesion):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.pag.click('.pestana[data-vista="pila"]')
        self.pag.wait_for_selector("#pl-estados tbody tr")
        self.pag.wait_for_selector('#pl-ejemplos option[value="0"]', state="attached")

    def trans(self, origen, lee, desapila, apila, destino):
        self.pag.click("#pl-btn-trans")
        f = self.pag.locator("#pl-trans tbody tr").last
        f.locator('select[data-c="origen"]').select_option(origen)
        f.locator('input[data-c="lee"]').fill(lee)
        f.locator('input[data-c="desapila"]').fill(desapila)
        f.locator('input[data-c="apila"]').fill(apila)
        f.locator('select[data-c="destino"]').select_option(destino)

    def crear(self):
        self.pag.click("#pl-crear")
        self.pag.wait_for_function("document.querySelector('#pl-mensajes').children.length > 0")

    def ejemplo(self, nombre):
        self.pag.select_option("#pl-ejemplos", label=nombre)

    def nodos(self):
        return self.pag.locator("#pl-diagrama .n-g").count()

    def probar(self, cadena, modo=""):
        self.pag.click('#pl-ops .op[data-op="simular"]')
        self.pag.wait_for_selector("#pl-sim:not([hidden])")
        self.pag.select_option('#pl-sim [data-x="modo"]', modo)
        self.pag.fill('#pl-sim [data-x="cadena"]', cadena)
        self.pag.click('#pl-sim [data-x="ejecutar"]')
        self.pag.wait_for_selector('#pl-sim [data-x="traza"] div')

    def pila(self):
        return self.pag.eval_on_selector_all("#pl-sim .pila-celda", "els => els.map(e => e.textContent)")

    def veredicto(self):
        return self.pag.inner_text('#pl-sim [data-x="veredicto"]')


class SesionTu(Sesion):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.pag.click('.pestana[data-vista="turing"]')
        self.pag.wait_for_selector("#tu-estados tbody tr")
        self.pag.wait_for_selector('#tu-ejemplos option[value="0"]', state="attached")

    def trans(self, origen, lee, destino, escribe, mueve):
        self.pag.click("#tu-btn-trans")
        f = self.pag.locator("#tu-trans tbody tr").last
        f.locator('select[data-c="origen"]').select_option(origen)
        f.locator('input[data-c="lee"][data-k="0"]').fill(lee)
        f.locator('select[data-c="destino"]').select_option(destino)
        f.locator('input[data-c="escribe"][data-k="0"]').fill(escribe)
        f.locator('select[data-c="mueve"][data-k="0"]').select_option(mueve)

    def crear(self):
        self.pag.click("#tu-crear")
        self.pag.wait_for_function("document.querySelector('#tu-mensajes').children.length > 0")

    def ejemplo(self, nombre):
        self.pag.select_option("#tu-ejemplos", label=nombre)

    def nodos(self):
        return self.pag.locator("#tu-diagrama .n-g").count()

    def ejecutar(self, cadena, maximo=None):
        self.pag.click('#tu-ops .op[data-op="ejecutar"]')
        self.pag.wait_for_selector("#tu-sim:not([hidden])")
        self.pag.fill('#tu-sim [data-x="cadena"]', cadena)
        if maximo:
            self.pag.fill('#tu-sim [data-x="max"]', str(maximo))
        self.pag.click('#tu-sim [data-x="ejecutar"]')
        self.pag.wait_for_selector("#tu-sim .cinta-t")

    def fin(self):
        self.pag.click('#tu-sim [data-x="fin"]')

    def veredicto(self):
        return self.pag.inner_text('#tu-sim [data-x="veredicto"]')


def construir_an_bn_pila(s):
    s.pag.click("#pl-btn-estado")
    s.pag.set_checked('#pl-estados tr[data-q="q2"] .c-final', True)
    s.trans("q0", "a", "Z", "AZ", "q0"); s.trans("q0", "a", "A", "AA", "q0")
    s.trans("q0", "b", "A", "", "q1"); s.trans("q1", "b", "A", "", "q1"); s.trans("q1", "", "Z", "Z", "q2")


# ------------------------------------------------------------------ pila
def test_pila_construir_a_mano_y_probar_con_la_pila_visible():
    with SesionPl() as s:
        assert s.pag.locator("#vista-pila").is_visible() and s.pag.locator("#pl-ops").is_hidden()
        construir_an_bn_pila(s)
        assert "Σ = {a, b}" in s.pag.inner_text("#pl-alfabetos") and "Γ = {A, Z}" in s.pag.inner_text("#pl-alfabetos")
        s.crear()
        assert "creado con 3 estados y 5 transiciones" in s.pag.inner_text("#pl-mensajes")
        assert s.nodos() == 3 and s.pag.locator("#pl-diagrama .n-fin").count() == 1 and "determinista" in s.pag.inner_text("#pl-titulo-diagrama")
        assert "a,Z/AZ" in s.pag.inner_text("#pl-diagrama")
        s.captura("30_pila_creada")
        s.probar("aabb")
        assert s.pila() == ["Z"] and s.pag.locator('#pl-sim [data-x="entrada"] .simbolo').count() == 4
        s.pag.click('#pl-sim [data-x="sig"]'); s.pag.click('#pl-sim [data-x="sig"]')
        assert s.pila() == ["A", "A", "Z"] and s.pag.locator("#pl-sim .pila-celda.cima").inner_text() == "A"
        assert s.pag.locator("#pl-diagrama .n-act").count() == 1 and s.pag.locator("#pl-diagrama .e-act").count() == 1
        s.pag.click('#pl-sim [data-x="fin"]')
        assert "ACEPTADA" in s.veredicto() and "Configuraciones exploradas" in s.veredicto()
        s.captura("31_pila_simulacion")
        s.pag.fill('#pl-sim [data-x="cadena"]', "aabbb"); s.pag.click('#pl-sim [data-x="ejecutar"]')
        s.pag.click('#pl-sim [data-x="fin"]')
        assert "RECHAZADA" in s.veredicto() and "rama que más entrada consumió" in s.veredicto()
        s.pag.select_option('#pl-sim [data-x="modo"]', "pila_vacia")
        s.pag.fill('#pl-sim [data-x="cadena"]', "aabb"); s.pag.click('#pl-sim [data-x="ejecutar"]')
        s.pag.click('#pl-sim [data-x="fin"]')
        assert "RECHAZADA" in s.veredicto() and "por pila vacía" in s.veredicto()                # queda Z en la pila
        s.pag.click('#pl-sim [data-x="cerrar"]')
        assert s.pag.locator("#pl-diagrama .n-act").count() == 0


def test_pila_varias_cadenas_y_reproduccion():
    with SesionPl() as s:
        s.ejemplo("aⁿbⁿ (estado final)"); s.crear()
        s.probar("aaabbb")
        s.pag.fill('#pl-sim [data-x="vel"]', "4")
        s.pag.click('#pl-sim [data-x="play"]')
        s.pag.wait_for_function("document.querySelector('#pl-sim [data-x=\"veredicto\"]').textContent.includes('ACEPTADA')", timeout=6000)
        s.pag.click('#pl-ops .op[data-op="lote"]')
        s.pag.wait_for_selector("#pl-lote:not([hidden])")
        s.pag.fill('#pl-lote [data-x="texto"]', "ab\naabb\naab\nλ\nabb")
        s.pag.click('#pl-lote [data-x="ejecutar"]')
        s.pag.wait_for_selector("#pl-lote tbody tr")
        filas = s.pag.eval_on_selector_all("#pl-lote tbody tr", "t => t.map(r => [r.children[0].textContent, r.children[1].textContent])")
        assert filas == [["ab", "ACEPTADA"], ["aabb", "ACEPTADA"], ["aab", "RECHAZADA"], ["λ", "RECHAZADA"], ["abb", "RECHAZADA"]]
        assert "2 aceptadas de 5" in s.pag.inner_text('#pl-lote [data-x="nota"]')
        s.captura("32_pila_lote")


def test_pila_no_determinista_palindromos():
    with SesionPl() as s:
        s.ejemplo("Palíndromos pares (w wᴿ)"); s.crear()
        assert "no determinista" in s.pag.inner_text("#pl-mensajes") and "no determinista" in s.pag.inner_text("#pl-titulo-diagrama")
        s.probar("0110")
        s.pag.click('#pl-sim [data-x="fin"]')
        assert "ACEPTADA" in s.veredicto()
        explorado = int(s.veredicto().split("exploradas: ")[1].split()[0].rstrip(".,"))
        assert explorado > 6                                                  # probó varias ramas
        s.pag.fill('#pl-sim [data-x="cadena"]', "0100"); s.pag.click('#pl-sim [data-x="ejecutar"]')
        s.pag.click('#pl-sim [data-x="fin"]')
        assert "RECHAZADA" in s.veredicto()
        s.captura("33_pila_palindromos")


def test_pila_errores_y_ciclos_lambda():
    with SesionPl() as s:
        s.trans("q0", "a", "Z", "aλ", "q1")
        s.crear()
        assert "«apila»" in s.pag.inner_text("#pl-mensajes") and s.pag.locator("#pl-trans tr.fila-error").count() == 1
        assert s.pag.locator("#pl-ops").is_hidden()
        s.captura("34_pila_error")
        s.pag.fill('#pl-trans tr[data-i="0"] input[data-c="apila"]', "A")
        assert s.pag.locator("#pl-trans tr.fila-error").count() == 0
        s.pag.click('#pl-trans .borrar')                                      # sin transiciones también se puede crear
        s.trans("q0", "", "", "A", "q0")                                      # λ-ciclo que apila sin parar
        s.crear()
        assert "creado con 2 estados y 1 transiciones" in s.pag.inner_text("#pl-mensajes") and "ningún estado final" in s.pag.inner_text("#pl-mensajes")
        s.probar("")
        s.pag.click('#pl-sim [data-x="fin"]')
        assert "RECHAZADA" in s.veredicto() and "cortada por el límite" in s.veredicto()


def test_pila_editor_renombra_borra_y_cambia_de_modo():
    with SesionPl() as s:
        s.trans("q0", "a", "Z", "AZ", "q1")
        s.pag.locator('#pl-estados tr[data-q="q1"] .nombre-estado').fill("meta")
        s.pag.locator('#pl-estados tr[data-q="q1"] .nombre-estado').blur()
        assert s.pag.input_value('#pl-trans tr[data-i="0"] select[data-c="destino"]') == "meta"
        assert s.pag.locator("#pl-estados th").count() == 4                    # Inicio, Final, Estado, borrar
        s.pag.click('#pl-segmentos .segmento[data-modo="pila_vacia"]')
        assert s.pag.locator("#pl-estados th").count() == 3                    # sin columna Final
        s.pag.fill("#pl-z0", "X")
        assert "X" in s.pag.inner_text("#pl-alfabetos")
        s.pag.click('#pl-estados tr[data-q="meta"] .borrar')
        assert s.pag.locator("#pl-trans tbody tr[data-i]").count() == 0 and "Aún no hay transiciones" in s.pag.inner_text("#pl-trans")


def test_pila_guardar_y_abrir():
    with SesionPl() as s:
        s.ejemplo("aⁿbⁿ (pila vacía)"); s.crear()
        with s.pag.expect_download() as d:
            s.pag.click("#pl-guardar")
        ruta = d.value.path()
        datos = json.load(open(ruta, encoding="utf-8"))
        assert datos["modo"] == "pila_vacia" and datos["determinista"] is True and len(datos["transiciones"]) == 5
        with s.pag.expect_download() as d2:
            s.pag.click("#pl-btn-svg")
        assert open(d2.value.path(), encoding="utf-8").read().startswith("<svg")
        s.pag.click("#pl-limpiar")
        s.pag.click('#pl-segmentos .segmento[data-modo="estado_final"]')
        s.pag.set_input_files("#pl-archivo", ruta)
        s.pag.wait_for_function("document.querySelectorAll('#pl-trans tbody tr[data-i]').length === 5")
        assert s.pag.locator('#pl-segmentos .segmento[data-modo="pila_vacia"].activo').count() == 1
        s.crear()
        assert "creado con 2 estados y 5 transiciones" in s.pag.inner_text("#pl-mensajes")
        mala = os.path.join(os.path.dirname(ruta), "mala_pila.json")
        open(mala, "w").write('{"x": 1}')
        s.pag.set_input_files("#pl-archivo", mala)
        s.pag.wait_for_function("document.querySelector('#avisos').textContent.includes('formato')")


# ------------------------------------------------------------------ Turing
def test_turing_construir_una_maquina_de_una_cinta_y_ejecutarla():
    with SesionTu() as s:
        assert s.pag.locator("#vista-turing").is_visible() and s.pag.locator("#tu-ops").is_hidden()
        s.pag.fill("#tu-nuevo", "ab"); s.pag.click("#tu-btn-simbolo")
        s.trans("q0", "b", "q0", "b", "D"); s.trans("q0", "a", "qf", "a", "N")
        assert "{B, a, b}" in s.pag.inner_text("#tu-gamma")
        s.crear()
        assert "de 1 cinta creada con 2 estados y 2 transiciones" in s.pag.inner_text("#tu-mensajes")
        assert s.nodos() == 2 and s.pag.locator("#tu-diagrama .n-fin").count() == 1
        s.captura("40_turing_creada")
        s.ejecutar("bba")
        assert s.pag.locator("#tu-sim .celda-t.cabeza").count() == 1
        s.pag.click('#tu-sim [data-x="sig"]'); s.pag.click('#tu-sim [data-x="sig"]')
        assert s.pag.locator("#tu-sim .celda-t.cabeza .idx").inner_text() == "2"
        assert "δ(q0, b) = (q0, b, D)" in s.pag.inner_text("#tu-sim .estado-grande")
        s.pag.click('#tu-sim [data-x="sig"]')
        assert "ACEPTA" in s.veredicto() and "Paso 3 de 3" in s.pag.inner_text('#tu-sim [data-x="contador"]')
        assert s.pag.locator("#tu-diagrama .n-act").count() == 1
        s.captura("41_turing_ejecucion")
        s.pag.fill('#tu-sim [data-x="cadena"]', "bb"); s.pag.click('#tu-sim [data-x="ejecutar"]')
        s.fin()
        assert "RECHAZA" in s.veredicto() and "no hay transición" in s.veredicto()


def test_turing_multicinta_dos_cintas_visibles():
    with SesionTu() as s:
        s.ejemplo("ω c ω (2 cintas)"); s.crear()
        assert "de 2 cintas creada" in s.pag.inner_text("#tu-mensajes") and s.nodos() == 5
        assert s.pag.locator('#tu-segmentos .segmento[data-tipo="multicinta"].activo').count() == 1 and s.pag.input_value("#tu-k") == "2"
        s.ejecutar("abcab")
        assert s.pag.locator("#tu-sim .cinta-t").count() == 2 and s.pag.locator("#tu-sim .etq-cinta").count() == 2
        s.fin()
        assert "ACEPTA" in s.veredicto()
        copia = s.pag.eval_on_selector_all('#tu-sim .cinta-t[data-k="1"] .celda-t:not(.vacia)', "els => els.map(e => e.firstChild.textContent)")
        assert copia == ["X", "a", "b"]                                       # la cinta 2 guarda ω marcado con X
        s.captura("42_turing_multicinta")


def test_turing_multipista_y_tabla_de_resultados():
    with SesionTu() as s:
        s.ejemplo("Complemento a uno (multipista)"); s.crear()
        assert "multipista de 2 pistas" in s.pag.inner_text("#tu-mensajes")
        s.ejecutar("1100")
        assert s.pag.locator("#tu-sim .celda-t span:not(.idx)").count() >= 2 * 4
        s.fin()
        pistas = s.pag.eval_on_selector_all("#tu-sim .celda-t:not(.vacia)", "els => els.map(e => [...e.querySelectorAll('span:not(.idx)')].map(x => x.textContent).join(''))")
        assert pistas == ["10", "10", "01", "01"]
        s.captura("43_turing_multipista")
        s.pag.click('#tu-ops .op[data-op="lote"]')
        s.pag.fill('#tu-lote [data-x="texto"]', "1100\n\nλ\n0")
        s.pag.click('#tu-lote [data-x="ejecutar"]')
        s.pag.wait_for_selector("#tu-lote tbody tr")
        filas = s.pag.eval_on_selector_all("#tu-lote tbody tr", "t => t.map(r => [r.children[0].textContent, r.children[1].textContent, r.children[3].textContent])")
        assert filas == [["1100", "ACEPTA", "1100 / 0011"], ["λ", "ACEPTA", "— / —"], ["0", "ACEPTA", "0 / 1"]]
        s.captura("44_turing_lote")


def test_turing_limite_de_pasos_y_barra_de_pasos():
    with SesionTu() as s:
        bucle = dict(cintas=1, pistas=1, estados=["q0"], entrada=["a"], inicial="q0", finales=[], blanco="B", nombre="",
                     transiciones=[dict(origen="q0", lecturas=["B"], destino="q0", escrituras=["B"], movimientos=["N"])])
        s.pag.evaluate("m => window.__turing.editor.cargar(m)", bucle)
        s.crear()
        assert "ningún estado final" in s.pag.inner_text("#tu-mensajes")
        s.ejecutar("", maximo=30)
        s.fin()
        assert "NO SE DETUVO" in s.veredicto() and "parada" in s.veredicto() and "Paso 30 de 30" in s.pag.inner_text('#tu-sim [data-x="contador"]')
        s.pag.evaluate("() => { const b = document.querySelector('#tu-sim [data-x=\"barra\"]'); b.value = 12; b.dispatchEvent(new Event('input')); }")
        assert "Paso 12 de 30" in s.pag.inner_text('#tu-sim [data-x="contador"]') and s.veredicto() == ""


def test_turing_errores_de_definicion():
    with SesionTu() as s:
        s.pag.fill("#tu-nuevo", "a"); s.pag.click("#tu-btn-simbolo")
        s.trans("q0", "a", "qf", "a", "D"); s.trans("q0", "a", "q0", "a", "D")
        s.crear()
        assert "no determinista" in s.pag.inner_text("#tu-mensajes") and s.pag.locator("#tu-trans tr.fila-error").count() == 1
        assert s.pag.locator('#tu-trans tr.fila-error').get_attribute("data-i") == "1"
        s.captura("45_turing_error")
        s.pag.click('#tu-trans tr[data-i="1"] .borrar')
        s.pag.evaluate("document.querySelector('#tu-blanco').value = 'BB'")        # el campo limita a 1 carácter al teclear
        s.crear()
        assert "blanco" in s.pag.inner_text("#tu-mensajes").lower()
        s.pag.fill("#tu-blanco", "B")
        s.crear()
        assert "creada con 2 estados y 1 transiciones" in s.pag.inner_text("#tu-mensajes")


def test_turing_el_editor_se_adapta_al_tipo():
    with SesionTu() as s:
        s.pag.click("#tu-btn-trans")
        assert s.pag.locator('#tu-trans tbody tr input[data-c="lee"]').count() == 1
        s.pag.click('#tu-segmentos .segmento[data-tipo="multicinta"]')
        s.pag.select_option("#tu-k", "3")
        assert s.pag.locator('#tu-trans tbody tr input[data-c="lee"]').count() == 3
        assert s.pag.locator('#tu-trans tbody tr select[data-c="mueve"]').count() == 3 and "por cinta" in s.pag.inner_text("#tu-trans thead").lower()
        s.pag.click('#tu-segmentos .segmento[data-tipo="multipista"]')
        assert s.pag.locator('#tu-opcion-pistas').is_visible() and s.pag.locator('#tu-opcion-cintas').is_hidden()
        assert s.pag.locator('#tu-trans tbody tr input[data-c="lee"]').count() == 1
        assert s.pag.get_attribute('#tu-trans tbody tr input[data-c="lee"]', "maxlength") == "2"
        s.pag.select_option("#tu-p", "3")
        assert s.pag.get_attribute('#tu-trans tbody tr input[data-c="lee"]', "maxlength") == "3"
        s.pag.click('#tu-segmentos .segmento[data-tipo="una"]')
        assert s.pag.locator('#tu-opcion-pistas').is_hidden() and s.pag.locator('#tu-trans tbody tr input[data-c="lee"]').count() == 1


def test_turing_diagrama_compacto_y_arrastre():
    with SesionTu() as s:
        s.ejemplo("ω c ω (1 cinta)"); s.crear()
        assert s.nodos() == 10 and "→ = ; I" in s.pag.inner_text("#tu-diagrama")
        s.pag.click("#tu-btn-ajustar")                                         # que todo el diagrama quepa en pantalla
        c = s.pag.locator('#tu-diagrama .n-g[data-id="e3"] circle.n-c')
        a = c.bounding_box(); cx, cy = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
        s.pag.mouse.move(cx, cy); s.pag.mouse.down(); s.pag.mouse.move(cx + 70, cy + 40, steps=6); s.pag.mouse.up()
        b = c.bounding_box()
        assert abs((b["x"] + b["width"] / 2) - (cx + 70)) < 4
        assert s.pag.inner_text("#tu-btn-ajustar") == "Tamaño real"
        s.captura("46_turing_diagrama")
        s.ejecutar("abcab")
        s.pag.click('#tu-sim [data-x="fin"]')
        assert "ACEPTA" in s.veredicto()
        pasos = int(s.pag.inner_text('#tu-sim [data-x="contador"]').split(" de ")[1])
        assert pasos == len(ejecutar(mt_omega_c_omega_1_cinta(), "abcab").pasos) - 1      # coincide con el núcleo en Python


def test_turing_guardar_y_abrir():
    with SesionTu() as s:
        s.ejemplo("aⁿbⁿcⁿ (2 cintas)"); s.crear()
        with s.pag.expect_download() as d:
            s.pag.click("#tu-guardar")
        ruta = d.value.path()
        datos = json.load(open(ruta, encoding="utf-8"))
        assert datos["cintas"] == 2 and datos["pistas"] == 1 and datos["blanco"] == "B" and len(datos["transiciones"]) == 10
        s.pag.click('#tu-segmentos .segmento[data-tipo="una"]'); s.pag.click("#tu-limpiar")
        s.pag.set_input_files("#tu-archivo", ruta)
        s.pag.wait_for_function("document.querySelectorAll('#tu-trans tbody tr[data-i]').length === 10")
        assert s.pag.locator('#tu-segmentos .segmento[data-tipo="multicinta"].activo').count() == 1 and s.pag.input_value("#tu-k") == "2"
        s.crear()
        assert "de 2 cintas creada con 5 estados y 10 transiciones" in s.pag.inner_text("#tu-mensajes")
        s.ejecutar("aabbcc"); s.fin()
        assert "ACEPTA" in s.veredicto()
        mala = os.path.join(os.path.dirname(ruta), "mala_tm.json")
        open(mala, "w").write('{"x": 1}')
        s.pag.set_input_files("#tu-archivo", mala)
        s.pag.wait_for_function("document.querySelector('#avisos').textContent.includes('formato')")


def test_las_cuatro_pestanas_conviven():
    with SesionPl() as s:
        s.ejemplo("aⁿbⁿ (estado final)"); s.crear()
        s.pag.click('.pestana[data-vista="turing"]')
        s.pag.select_option("#tu-ejemplos", label="ω c ω (1 cinta)")
        s.pag.click("#tu-crear")
        s.pag.wait_for_function("document.querySelector('#tu-mensajes').children.length > 0")
        s.pag.click('.pestana[data-vista="pila"]')
        assert s.pag.locator("#pl-diagrama .n-g").count() == 3 and s.pag.locator("#tu-diagrama .n-g").count() == 10
        s.pag.click('.pestana[data-vista="finitos"]')
        assert s.pag.locator("#segmentos-tipo .segmento").count() == 4 and s.pag.locator("#matriz tbody tr").count() == 2
        s.pag.click(".interruptor")
        s.captura("47_oscuro_pila")
        assert s.pag.get_attribute("html", "data-tema") == "oscuro"
