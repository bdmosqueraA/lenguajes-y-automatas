"""Pruebas del Día 6 (parte traductores): máquinas de Moore y Mealy."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.traductores import Traductor, TraductorInvalido, traducir
from automatas.datos import ejemplos_traductores as ej
from tests.utiles import cadenas, espera_error


def salida(maquina, entrada):
    return traducir(maquina, entrada).salida


def test_secuencia_011_en_moore_y_mealy():
    for maquina in (ej.moore_secuencia_011(), ej.mealy_secuencia_011()):
        assert salida(maquina, "011") == "001"
        assert salida(maquina, "0110") == "0010"
        assert salida(maquina, "1011") == "0001"
        assert salida(maquina, "011011") == "001001"
        assert salida(maquina, "111") == "000"
        assert salida(maquina, "") == ""


def test_moore_no_emite_la_salida_del_estado_inicial():
    t = traducir(ej.moore_paridad_de_unos(), "0110")
    assert len(t.salida) == 4                      # una salida por símbolo leído
    assert t.pasos[0].salida == "" and t.pasos[0].estado == "P"


def test_paridad_de_unos_moore_igual_a_mealy():
    moore, mealy = ej.moore_paridad_de_unos(), ej.mealy_paridad_de_unos()
    assert salida(moore, "0110") == "abaa"
    for cadena in cadenas({"0", "1"}, 8):
        assert salida(moore, cadena) == salida(mealy, cadena), cadena


def test_ejercicio_suma_modulo_5():
    assert salida(ej.moore_suma_modulo_5(), "32130") == "30144"      # ejemplo de la clase
    assert salida(ej.moore_suma_modulo_5(), "") == ""


def test_ejercicio_dos_ultimos_simbolos_con_salida_lambda():
    m = ej.mealy_dos_ultimos_simbolos()
    assert salida(m, "01101001") == "bbbbab"                         # (= λbλbbbab)
    t = traducir(m, "01101001")
    assert [p.salida for p in t.pasos[1:]] == ["", "b", "", "b", "b", "b", "a", "b"]


def test_traza_bloqueo_y_simbolo_invalido():
    parcial = Traductor.mealy([("q0", "a", "q1", "x")], "q0", entrada={"a", "b"})
    t = traducir(parcial, "ab")            # 'b' está en Σ pero no hay transición con 'b' desde q1
    assert not t.completa and t.salida == "x" and "No hay transición" in t.motivo
    t = traducir(ej.moore_paridad_de_unos(), "012")   # '2' no está en Σ
    assert not t.completa and "no pertenece" in t.motivo and t.salida == "ab"


def test_validacion():
    espera_error(TraductorInvalido, lambda: Traductor.moore([("q0", "a", "q1")], {"q0": "x"}, "q0"), "faltan")
    espera_error(TraductorInvalido, lambda: Traductor.mealy([("q0", "a", "q1", "xy")], "q0", salida={"x"}), "Γ")
    espera_error(TraductorInvalido, lambda: Traductor.mealy([("q0", "ab", "q1", "x")], "q0"), "un carácter")
    espera_error(TraductorInvalido,
                 lambda: Traductor("mealy", {"q0"}, {"a"}, {"x"}, {}, {}, "zz"), "inicial")


def test_json_y_tabla():
    for fabrica in ej.EJEMPLOS_TRADUCTORES.values():
        original = fabrica()
        copia = Traductor.desde_dict(original.a_dict())
        assert copia == original
        assert original.tabla()
    t = ej.mealy_secuencia_011().tabla()
    assert "E1/0" in t and "E0/1" in t
    t = ej.moore_secuencia_011().tabla()
    assert "Salida" in t and "→E0" in t
