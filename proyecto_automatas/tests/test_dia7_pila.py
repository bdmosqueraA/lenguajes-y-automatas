"""Pruebas del Día 7: autómatas de pila."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.pila import AutomataPila, PilaInvalida, acepta, ejecutar
from automatas.datos import ejemplos_pila as ej
from tests.utiles import cadenas, espera_error


def balanceada(s):
    nivel = 0
    for c in s:
        nivel += 1 if c == "(" else -1
        if nivel < 0:
            return False
    return nivel == 0


def test_ejemplo_de_clase_con_lambda_en_el_desapilado():
    ap = ej.ap_clase_a_n_b_m()
    for cadena in ["", "a", "ab", "aab", "aabb", "aaabb", "aaabbb"]:
        assert acepta(ap, cadena), cadena
    for cadena in ["b", "abb", "ba", "aabbb", "abab"]:
        assert not acepta(ap, cadena), cadena
    for cadena in cadenas({"a", "b"}, 8):       # a^n b^m con m <= n
        esperado = cadena == "a" * cadena.count("a") + "b" * cadena.count("b") \
            and cadena.count("b") <= cadena.count("a")
        assert acepta(ap, cadena) == esperado, cadena


def test_an_bn_por_estado_final_y_por_pila_vacia():
    for ap in (ej.ap_an_bn_estado_final(), ej.ap_an_bn_pila_vacia()):
        for cadena in cadenas({"a", "b"}, 9):
            n = cadena.count("a")
            esperado = n >= 1 and cadena == "a" * n + "b" * n
            assert acepta(ap, cadena) == esperado, (ap.nombre, cadena)
        assert acepta(ap, "a" * 30 + "b" * 30)


def test_palindromos_pares_no_determinista():
    ap = ej.ap_palindromos_pares()
    assert not ap.es_determinista()
    for cadena in cadenas({"0", "1"}, 8):
        esperado = len(cadena) % 2 == 0 and cadena == cadena[::-1]
        assert acepta(ap, cadena) == esperado, cadena


def test_parentesis_balanceados():
    ap = ej.ap_parentesis_balanceados()
    # Por la definición estricta es no determinista: con Z en la cima, la transición λ
    # hacia q1 compite con la que lee '('. El resultado de la ejecución es el correcto.
    assert not ap.es_determinista()
    for cadena in cadenas({"(", ")"}, 10):
        assert acepta(ap, cadena) == balanceada(cadena), cadena


def test_deteccion_de_determinismo():
    assert ej.ap_clase_a_n_b_m().es_determinista()
    assert ej.ap_an_bn_estado_final().es_determinista()
    assert ej.ap_an_bn_pila_vacia().es_determinista()
    assert not ej.ap_palindromos_pares().es_determinista()


def test_traza_muestra_la_pila():
    t = ejecutar(ej.ap_an_bn_estado_final(), "aabb")
    assert t.acepta
    pilas = [p.configuracion.pila for p in t.camino]
    assert pilas == ["Z", "AZ", "AAZ", "AZ", "Z", "Z"]
    assert t.camino[0].transicion is None and t.camino[-1].configuracion.estado == "q2"
    assert t.camino[-1].configuracion.restante == ""


def test_traza_de_rechazo_muestra_donde_se_atasco():
    t = ejecutar(ej.ap_an_bn_estado_final(), "aabbb")
    assert not t.acepta and not t.limite_alcanzado
    assert t.camino[-1].configuracion.restante == "b"        # no pudo consumir la última 'b'


def test_modo_se_puede_cambiar_al_ejecutar():
    ap = ej.ap_an_bn_estado_final()
    assert acepta(ap, "ab") and not acepta(ap, "ab", modo="pila_vacia")   # queda Z en la pila


def test_limite_de_configuraciones_en_ciclos_lambda():
    bucle = AutomataPila.desde_transiciones([("q0", "", "", "q0", "A")], inicial="q0",
                                            simbolo_inicial="Z")
    t = ejecutar(bucle, "", max_configuraciones=200)
    assert not t.acepta and t.limite_alcanzado and "límite" in t.motivo
    assert acepta(AutomataPila.desde_transiciones([("q0", "", "", "q1", "A")], "q0", {"q1"}), "")


def test_simbolo_fuera_del_alfabeto():
    t = ejecutar(ej.ap_an_bn_estado_final(), "abc")
    assert not t.acepta and "no pertenece" in t.motivo


def test_validacion_y_json():
    espera_error(PilaInvalida, lambda: AutomataPila.desde_transiciones(
        [("q0", "a", "Q", "q0", "")], "q0", simbolo_inicial="Z", pila={"Z"}), "Γ")
    espera_error(PilaInvalida, lambda: AutomataPila({"q0"}, set(), {"Z"}, [], "q9", "Z", set()), "inicial")
    espera_error(PilaInvalida, lambda: AutomataPila({"q0"}, set(), {"Z"}, [], "q0", "Z", set(), modo="x"), "Modo")
    for fabrica in ej.EJEMPLOS_PILA.values():
        original = fabrica()
        assert AutomataPila.desde_dict(original.a_dict()) == original
        assert original.descripcion()
