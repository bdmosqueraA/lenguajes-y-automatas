"""Pruebas del Día 8: máquinas de Turing de una cinta, k cintas y multipista."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.turing import (MaquinaTuring, TuringInvalida, acepta, contenido, ejecutar)
from automatas.datos import ejemplos_turing as ej
from tests.utiles import cadenas, espera_error


def es_omega_c_omega(s):
    if s.count("c") != 1:
        return False
    izq, der = s.split("c")
    return set(izq) <= {"a", "b"} and izq == der


def es_an_bn_cn(s):
    n = len(s) // 3
    return len(s) % 3 == 0 and s == "a" * n + "b" * n + "c" * n


def test_omega_c_omega_con_una_y_con_dos_cintas():
    for maquina in (ej.mt_omega_c_omega_1_cinta(), ej.mt_omega_c_omega_2_cintas()):
        for cadena in cadenas({"a", "b", "c"}, 7):
            assert acepta(maquina, cadena) == es_omega_c_omega(cadena), (maquina.nombre, cadena)
        assert acepta(maquina, "abbacabba") and not acepta(maquina, "abbacabbb")


def test_an_bn_cn_con_dos_cintas():
    m = ej.mt_an_bn_cn_2_cintas()
    for cadena in cadenas({"a", "b", "c"}, 8):
        assert acepta(m, cadena) == es_an_bn_cn(cadena), cadena
    for n in (9, 15, 25):
        assert acepta(m, "a" * n + "b" * n + "c" * n)
        assert not acepta(m, "a" * n + "b" * (n - 1) + "c" * n)


def test_complemento_a_uno_multipista():
    m = ej.mt_complemento_a_uno_multipista()
    assert m.pistas == 2 and m.cintas == 1
    for cadena in cadenas({"0", "1"}, 8):
        t = ejecutar(m, cadena)
        assert t.acepta, cadena
        esperado = "".join("1" if c == "0" else "0" for c in cadena)
        assert contenido(m, t.final, 0, pista=1) == esperado, cadena
        assert contenido(m, t.final, 0, pista=0) == cadena, cadena       # la entrada no se altera
    t = ejecutar(m, "1100")
    assert contenido(m, t.final, 0, pista=1) == "0011"                   # ejemplo de las diapositivas


def test_traza_paso_a_paso():
    m = ej.mt_omega_c_omega_2_cintas()
    t = ejecutar(m, "abcab")
    assert t.acepta and t.detenida
    assert t.pasos[0].transicion is None and t.pasos[0].configuracion.estado == "e0"
    assert t.pasos[0].configuracion.cintas == (("a", "b", "c", "a", "b"), ())   # cinta 2 vacía
    assert t.final.estado == "e4"
    assert contenido(m, t.final, 1) == "Xab"                                    # la copia de ω en la cinta 2
    assert len(t.pasos) == len(set(p.indice for p in t.pasos))


def test_rechazo_por_falta_de_transicion():
    t = ejecutar(ej.mt_omega_c_omega_1_cinta(), "abcba")
    assert not t.acepta and t.detenida and "no hay transición" in t.motivo


def test_limite_de_pasos_por_bucle_infinito():
    bucle = MaquinaTuring.desde_transiciones([("q0", "B", "q0", "B", "N")], "q0", set(), {"a"})
    t = ejecutar(bucle, "", max_pasos=100)
    assert not t.acepta and not t.detenida and "parada" in t.motivo
    assert len(t.pasos) == 101


def test_mover_a_la_izquierda_del_inicio_bloquea():
    m = MaquinaTuring.desde_transiciones([("q0", "a", "q1", "a", "I")], "q0", {"q1"}, {"a"})
    t = ejecutar(m, "a")
    assert not t.acepta and "izquierda" in t.motivo


def test_estado_inicial_final_acepta_de_inmediato():
    m = MaquinaTuring.desde_transiciones([], "q0", {"q0"}, {"a"})
    assert acepta(m, "") and acepta(m, "aaa")


def test_alias_de_movimientos_en_ingles():
    m = MaquinaTuring.desde_transiciones(
        [("q0", "a", "q0", "a", "R"), ("q0", "B", "q1", "B", "S")], "q0", {"q1"}, {"a"})
    assert acepta(m, "aaa") and m.transiciones[0].movimientos in (("D",), ("N",))


def test_simbolo_fuera_del_alfabeto_de_entrada():
    t = ejecutar(ej.mt_omega_c_omega_1_cinta(), "abz")
    assert not t.acepta and "no pertenece" in t.motivo


def test_validacion():
    espera_error(TuringInvalida, lambda: MaquinaTuring.desde_transiciones(
        [("q0", "a", "q1", "a", "D"), ("q0", "a", "q2", "b", "D")], "q0", {"q1"}, {"a"}), "no determinista")
    espera_error(TuringInvalida, lambda: MaquinaTuring.desde_transiciones(
        [("q0", "a", "q1", "a", "D")], "q0", {"q1"}, {"a", "B"}), "blanco")
    espera_error(TuringInvalida, lambda: MaquinaTuring.desde_transiciones(
        [("q0", "aB", "q1", "aB", "D")], "q0", {"q1"}, {"a"}), "inválido")          # 1 cinta, símbolo de 2 caracteres
    espera_error(TuringInvalida, lambda: MaquinaTuring.desde_transiciones(
        [("q0", "ab", "q1", "ab", "DD")], "q0", {"q1"}, {"a"}, cintas=2, pistas=2), "una sola cinta")
    espera_error(TuringInvalida, lambda: MaquinaTuring.desde_transiciones(
        [("q0", "ab", "q1", "ab", "D")], "q0", {"q1"}, {"a"}, cintas=2), "2 cinta")


def test_json_y_tabla():
    for fabrica in ej.EJEMPLOS_TURING.values():
        original = fabrica()
        copia = MaquinaTuring.desde_dict(original.a_dict())
        assert copia == original
        assert original.tabla() and original.descripcion()
