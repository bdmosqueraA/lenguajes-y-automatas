"""Pruebas del Día 2: AFND→AFD (subconjuntos), completar, renombrar y minimización."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.finitos import (Automata, OperacionInvalida, a_afd, completar,
                                    estados_accesibles, minimizar, renombrar_estados)
from automatas.datos import ejemplos
from tests.utiles import espera_error, iguales


# ---------------------------------------------------------------- subconjuntos
def test_subconjuntos_afnd_termina_en_01():
    a = ejemplos.afnd_termina_en_01()
    r = a_afd(a)
    assert r.afd.es_determinista()
    assert set(r.afd.estados) == {"{q0}", "{q0,q1}", "{q0,q2}"}
    assert r.afd.inicial == "{q0}" and r.afd.finales == {"{q0,q2}"}
    assert len(r.filas) == 6                       # 3 subconjuntos x 2 símbolos
    assert sum(1 for f in r.filas if f.nuevo) == 2  # {q0,q1} y {q0,q2} (el inicial no cuenta)
    iguales(a, r.afd)


def test_subconjuntos_con_lambda():
    a = ejemplos.afnd_lambda_a_estrella_b_estrella()
    r = a_afd(a)
    assert r.clausura_inicial == {"q0", "q1"}
    assert set(r.afd.estados) == {"{q0,q1}", "{q1}"}
    assert r.afd.finales == {"{q0,q1}", "{q1}"}
    assert not r.afd.tiene_lambda()
    iguales(a, r.afd)


def test_subconjuntos_con_renombrado():
    r = a_afd(ejemplos.afnd_termina_en_01(), renombrar=True)
    assert r.afd.estados == {"q0", "q1", "q2"} and r.afd.inicial == "q0"
    assert r.subconjuntos == {"q0": {"q0"}, "q1": {"q0", "q1"}, "q2": {"q0", "q2"}}
    iguales(ejemplos.afnd_termina_en_01(), r.afd)


def test_subconjuntos_de_un_afd_conserva_el_lenguaje():
    for fabrica in (ejemplos.afd_intro_ab, ejemplos.afd_intro_01, ejemplos.afd_minimizacion_8_estados):
        a = fabrica()
        iguales(a, a_afd(a).afd)


# ---------------------------------------------------------------- utilidades
def test_completar_agrega_trampa():
    a = ejemplos.afd_intro_01()
    c = completar(a)
    assert c.es_completo() and "∅" in c.estados
    assert c.destinos("q2", "0") == {"∅"} and c.destinos("∅", "1") == {"∅"}
    assert "∅" not in c.finales
    iguales(a, c)
    assert completar(ejemplos.afd_intro_ab()).estados == ejemplos.afd_intro_ab().estados


def test_completar_exige_afd():
    espera_error(OperacionInvalida, lambda: completar(ejemplos.afnd_termina_en_01()), "AFD")


def test_estados_accesibles():
    a = ejemplos.afd_minimizacion_8_estados()
    assert estados_accesibles(a) == a.estados - {"q3"}      # nadie llega a q3


def test_renombrar_en_orden_de_descubrimiento():
    a = Automata.desde_transiciones(
        [("x", "0", "z"), ("x", "1", "y"), ("y", "0", "x"), ("z", "1", "z")],
        inicial="x", finales={"z"})
    nuevo, mapa = renombrar_estados(a)
    assert mapa == {"x": "q0", "z": "q1", "y": "q2"}        # q0, luego por 0 -> z, por 1 -> y
    iguales(a, nuevo)


# ---------------------------------------------------------------- minimización
def test_minimizacion_replica_la_clase():
    original = ejemplos.afd_minimizacion_8_estados()
    r = minimizar(original, quitar_inaccesibles=False)
    assert set(r.clases) == {frozenset({"q0", "q4"}), frozenset({"q1", "q7"}),
                             frozenset({"q3", "q5"}), frozenset({"q2"}), frozenset({"q6"})}
    assert [len(i.bloques) for i in r.iteraciones] == [2, 4, 5, 5]
    assert set(r.iteraciones[1].bloques) == {            # X, M, Z y N de las diapositivas
        frozenset({"q2"}), frozenset({"q0", "q4", "q6"}),
        frozenset({"q1", "q7"}), frozenset({"q3", "q5"})}
    m = r.minimo
    nombre = {"A": "{q0,q4}", "Z": "{q1,q7}", "N": "{q3,q5}", "X": "q2", "B": "q6"}
    tabla_de_clase = {("A", "0"): "Z", ("A", "1"): "N", ("X", "0"): "A", ("X", "1"): "X",
                      ("B", "0"): "B", ("B", "1"): "A", ("Z", "0"): "B", ("Z", "1"): "X",
                      ("N", "0"): "X", ("N", "1"): "B"}
    for (origen, simbolo), destino in tabla_de_clase.items():
        assert m.destinos(nombre[origen], simbolo) == {nombre[destino]}, (origen, simbolo)
    assert m.inicial == nombre["A"] and m.finales == {nombre["X"]}
    assert len(m.estados) == 5
    iguales(original, m)


def test_minimizacion_quita_el_inaccesible():
    original = ejemplos.afd_minimizacion_8_estados()
    r = minimizar(original)
    assert r.inaccesibles == {"q3"}
    assert len(r.minimo.estados) == 5 and "q5" in r.minimo.estados
    iguales(original, r.minimo)


def test_minimizacion_de_afd_incompleto_oculta_la_trampa():
    a = ejemplos.afd_intro_01()
    r = minimizar(a)
    assert r.trampa == "∅" and "∅" not in r.minimo.estados
    assert len(r.minimo.estados) == 3 and not r.minimo.es_completo()
    iguales(a, r.minimo)
    assert len(minimizar(a, ocultar_trampa=False).minimo.estados) == 4


def test_minimizacion_fusiona_estados_equivalentes():
    a = Automata.desde_transiciones(
        [("p", "a", "q"), ("p", "b", "r"), ("r", "a", "q"), ("r", "b", "p"),
         ("q", "a", "q"), ("q", "b", "p")],
        inicial="p", finales={"q"}, nombre="termina en a, con un estado repetido")
    r = minimizar(a)
    assert len(r.minimo.estados) == 2
    assert frozenset({"p", "r"}) in r.clases
    iguales(a, r.minimo)


def test_minimizar_un_minimo_no_cambia_su_tamano():
    a = ejemplos.afd_intro_ab()
    assert len(minimizar(a).minimo.estados) == 3


def test_minimizar_exige_afd():
    espera_error(OperacionInvalida, lambda: minimizar(ejemplos.afnd_termina_en_01()), "AFD")
    espera_error(OperacionInvalida,
                 lambda: minimizar(ejemplos.afnd_lambda_a_estrella_b_estrella()), "AFD")


def test_resumen_de_iteraciones_se_puede_imprimir():
    r = minimizar(ejemplos.afd_minimizacion_8_estados(), quitar_inaccesibles=False)
    texto = "\n".join(i.resumen(sorted(r.preparado.alfabeto)) for i in r.iteraciones)
    assert "Partición inicial" in texto and "Iteración 3" in texto
