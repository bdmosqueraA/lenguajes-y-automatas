
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.finitos import (LAMBDA, Automata, AutomataInvalido, acepta,
                                    clausura_lambda, ejecutar)
from automatas.datos import ejemplos
from automatas.datos.archivos import cargar_json, guardar_json


def espera_error(funcion):
    try:
        funcion()
    except AutomataInvalido:
        return
    raise AssertionError("Se esperaba AutomataInvalido y no se lanzó")


# ---------------------------------------------------------------- clasificación
def test_tipo_de_cada_ejemplo():
    assert ejemplos.afd_intro_ab().tipo() == "AFD"
    assert ejemplos.afd_intro_ab().es_completo()
    assert ejemplos.afd_intro_01().tipo() == "AFD"
    assert not ejemplos.afd_intro_01().es_completo()      # q2 no tiene transiciones
    assert ejemplos.afd_minimizacion_8_estados().es_completo()
    assert ejemplos.afnd_termina_en_01().tipo() == "AFND"
    assert ejemplos.afnd_lambda_a_estrella_b_estrella().tipo() == "AFND-λ"


# ---------------------------------------------------------------- reconocimiento
def test_afd_de_la_introduccion():
    a = ejemplos.afd_intro_ab()
    assert acepta(a, "aabab")          # ejemplo de clase: aceptada
    assert not acepta(a, "aababa")     # ejemplo de clase: rechazada
    assert acepta(a, "")               # q0 también es de aceptación


def test_afd_incompleto_se_bloquea():
    a = ejemplos.afd_intro_01()
    for cadena in ["0", "11", "100"]:
        assert acepta(a, cadena), cadena
    for cadena in ["", "1", "10", "00", "111", "101"]:
        assert not acepta(a, cadena), cadena
    traza = ejecutar(a, "00")
    assert "se bloquea" in traza.motivo
    assert traza.pasos[-1].estados == frozenset()


def test_afd_de_minimizacion():
    a = ejemplos.afd_minimizacion_8_estados()
    assert acepta(a, "01") and acepta(a, "10")        # q0-0->q1-1->q2 y q0-1->q5-0->q2
    assert not acepta(a, "") and not acepta(a, "00")  # q0 no es final; 00 termina en q6


def test_afnd_termina_en_01():
    a = ejemplos.afnd_termina_en_01()
    for cadena in ["01", "1101", "0001", "101"]:
        assert acepta(a, cadena), cadena
    for cadena in ["", "0", "1", "10", "011", "110"]:
        assert not acepta(a, cadena), cadena


def test_afnd_lambda_a_estrella_b_estrella():
    a = ejemplos.afnd_lambda_a_estrella_b_estrella()
    for cadena in ["", "a", "b", "aabb", "aaab", "abbb"]:
        assert acepta(a, cadena), cadena
    for cadena in ["ba", "aba", "bab"]:
        assert not acepta(a, cadena), cadena


def test_simbolo_fuera_del_alfabeto():
    traza = ejecutar(ejemplos.afd_intro_ab(), "abc")
    assert not traza.acepta and "alfabeto" in traza.motivo


# ---------------------------------------------------------------- λ-clausura
def test_clausura_con_ciclo_lambda():
    a = Automata.desde_transiciones(
        [("q0", LAMBDA, "q1"), ("q1", LAMBDA, "q2"),
         ("q2", LAMBDA, "q0"), ("q2", "a", "q3")],
        inicial="q0", finales={"q3"})
    assert clausura_lambda(a, "q0") == {"q0", "q1", "q2"}
    assert clausura_lambda(a, "q1") == {"q0", "q1", "q2"}
    assert clausura_lambda(a, {"q3"}) == {"q3"}
    assert acepta(a, "a")


def test_clausura_sin_transiciones_lambda_es_el_mismo_conjunto():
    a = ejemplos.afd_intro_ab()
    assert clausura_lambda(a, {"q0", "q2"}) == {"q0", "q2"}


# ---------------------------------------------------------------- traza
def test_traza_paso_a_paso_afd():
    traza = ejecutar(ejemplos.afd_intro_ab(), "aab")
    assert [p.estados for p in traza.pasos] == [
        frozenset({"q0"}), frozenset({"q0"}), frozenset({"q0"}), frozenset({"q1"})]
    assert traza.pasos[3].transiciones == frozenset({("q0", "b", "q1")})
    assert traza.pasos[0].simbolo is None and traza.pasos[3].simbolo == "b"


def test_traza_incluye_transiciones_lambda():
    traza = ejecutar(ejemplos.afnd_lambda_a_estrella_b_estrella(), "ab")
    assert traza.pasos[0].estados == frozenset({"q0", "q1"})
    assert traza.pasos[0].transiciones == frozenset({("q0", LAMBDA, "q1")})
    assert traza.pasos[1].transiciones == frozenset({("q0", "a", "q0"), ("q0", LAMBDA, "q1")})
    assert traza.pasos[2].estados == frozenset({"q1"})
    assert traza.acepta


# ---------------------------------------------------------------- validación
def test_validacion_rechaza_definiciones_inconsistentes():
    espera_error(lambda: Automata({"q0"}, {"a"}, {}, "qX", set()))              # inicial inexistente
    espera_error(lambda: Automata({"q0"}, {"a"}, {}, "q0", {"q9"}))             # final inexistente
    espera_error(lambda: Automata({"q0"}, {LAMBDA}, {}, "q0", set()))           # λ en el alfabeto
    espera_error(lambda: Automata({"q0"}, {"ab"}, {}, "q0", set()))             # símbolo de 2 caracteres
    espera_error(lambda: Automata({"q0"}, {"a"}, {("q0", "b"): {"q0"}}, "q0", set()))  # símbolo fuera de Σ
    espera_error(lambda: Automata({"q0"}, {"a"}, {("q0", "a"): {"q7"}}, "q0", set()))  # destino inexistente
    espera_error(lambda: Automata(set(), {"a"}, {}, "q0", set()))               # sin estados


# ---------------------------------------------------------------- JSON y tabla
def test_ida_y_vuelta_json(tmp_path=None):
    import tempfile
    carpeta = tmp_path or tempfile.mkdtemp()
    for fabrica in ejemplos.EJEMPLOS.values():
        original = fabrica()
        ruta = os.path.join(str(carpeta), "a.json")
        guardar_json(original, ruta)
        assert cargar_json(ruta) == original
        assert Automata.desde_dict(original.a_dict()) == original


def test_tabla_usa_la_notacion_de_clase():
    texto = ejemplos.afd_intro_01().tabla()
    assert "→q0" in texto and "#q2" in texto
    assert "∅" in texto                      # q2 sin transiciones


def test_orden_natural_de_estados():
    texto = ejemplos.afd_minimizacion_8_estados().tabla().splitlines()
    nombres = [fila.split("|")[0].strip().lstrip("→#") for fila in texto[2:]]
    assert nombres == [f"q{i}" for i in range(8)]


# ---------------------------------------------------------------- ejecutor simple
if __name__ == "__main__":
    pruebas = [(n, f) for n, f in sorted(globals().items())
               if n.startswith("test_") and callable(f)]
    fallos = 0
    for nombre, funcion in pruebas:
        try:
            funcion()
            print(f"  OK     {nombre}")
        except Exception as error:  # noqa: BLE001
            fallos += 1
            print(f"  FALLÓ  {nombre}: {error!r}")
    print(f"\n{len(pruebas) - fallos}/{len(pruebas)} pruebas correctas")
    sys.exit(1 if fallos else 0)
