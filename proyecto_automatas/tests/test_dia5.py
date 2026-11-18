"""Pruebas del Día 5: expresiones regulares, Thompson y el flujo ER → AFND-λ → AFD → mínimo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automatas.core.finitos import ErrorER, a_texto, analizar, er, er_a_afd_minimo, thompson
from tests.utiles import espera_error, iguala_regex

EXPRESIONES = ["a", "ab", "a|b", "a*", "a+", "(a|b)*abb", "λ", "∅", "(ab)*|c", "a(b|c)*",
               "(a|λ)b", "a**", "(a*b*)*", "0|1(0|1)*", "(01|10)+", "a|b|c", "a(b|c)d*e"]


# ---------------------------------------------------------------- analizador
def test_precedencia_union_concatenacion_estrella():
    esperado = er.Union(er.Simbolo("a"), er.Concat(er.Simbolo("b"), er.Estrella(er.Simbolo("c"))))
    assert analizar("a|bc*") == esperado
    assert analizar("(a|b)*") == er.Estrella(er.Union(er.Simbolo("a"), er.Simbolo("b")))
    assert analizar("a+") == er.Mas(er.Simbolo("a"))
    assert analizar(" a | b ") == er.Union(er.Simbolo("a"), er.Simbolo("b"))


def test_lambda_vacio_y_escapes():
    assert analizar("λ") == er.Lambda() and analizar("ε") == er.Lambda()
    assert analizar("∅") == er.Vacio()
    assert analizar(r"\*") == er.Simbolo("*")
    assert a_texto(er.Simbolo("*")) == r"\*"
    assert a_texto(analizar(r"a\|b")) == r"a\|b"


def test_escritura_es_estable():
    for texto in EXPRESIONES:
        una_vez = a_texto(analizar(texto))
        assert a_texto(analizar(una_vez)) == una_vez, texto
    assert a_texto(analizar("(a|b)c")) == "(a|b)c"
    assert a_texto(analizar("(ab)*")) == "(ab)*"
    assert a_texto(analizar("a|(bc)")) == "a|bc"


def test_errores_de_sintaxis():
    for texto, parte in [("", "vacía"), ("a|", "operando"), ("|a", "operando"),
                         ("*a", "no tiene operando"), ("(a", "cerrar"), ("a)", "cierre"),
                         ("()", "operando"), ("a||b", "operando"), ("\\", "barra")]:
        espera_error(ErrorER, lambda t=texto: analizar(t), parte)
    try:
        analizar("ab(c")
    except ErrorER as error:
        assert error.posicion == 2          # el paréntesis abierto sin cerrar


# ---------------------------------------------------------------- Thompson
def test_thompson_cantidad_de_estados():
    cuentas = {"a": 2, "ab": 4, "a|b": 6, "a*": 4, "a+": 4, "λ": 2, "∅": 2}
    for texto, cantidad in cuentas.items():
        r = thompson(texto)
        assert len(r.automata.estados) == cantidad, texto
        assert r.automata.inicial == "q0" and len(r.automata.finales) == 1, texto
        assert r.pasos, texto


def test_thompson_tipo_y_pasos():
    assert thompson("a").automata.tipo() == "AFD"
    assert thompson("ab").automata.tipo() == "AFND-λ"
    r = thompson("a|b")
    assert [p.descripcion.split(":")[0] for p in r.pasos] == ["Símbolo 'a'", "Símbolo 'b'", "Unión (a|b)"]
    # cada transición del autómata se registró exactamente en un paso
    registradas = sorted(t for p in r.pasos for t in p.transiciones)
    assert registradas == r.automata.transiciones()


def test_thompson_con_alfabeto_extra():
    r = thompson("a", alfabeto={"b", "c"})
    assert r.automata.alfabeto == {"a", "b", "c"}


def test_thompson_lenguaje_contra_re_de_python():
    for texto in EXPRESIONES:
        r = thompson(texto)
        iguala_regex(r.automata, r.er, largo_max=6)


def test_thompson_con_simbolo_escapado():
    from automatas.core.finitos import acepta
    r = thompson(r"a\*b")
    assert acepta(r.automata, "a*b") and not acepta(r.automata, "ab")


# ---------------------------------------------------------------- flujo completo
def test_flujo_completo_conserva_el_lenguaje():
    for texto in EXPRESIONES:
        p = er_a_afd_minimo(texto)
        nodo = p.thompson.er
        iguala_regex(p.thompson.automata, nodo, 6)
        iguala_regex(p.conversion.afd, nodo, 6)
        iguala_regex(p.afd_minimo, nodo, 6)
        assert p.conversion.afd.es_determinista() and p.afd_minimo.es_determinista(), texto
        assert len(p.afd_minimo.estados) <= len(p.conversion.afd.estados), texto


def test_tamanos_minimos_clasicos():
    tamanos = {"(a|b)*abb": 4, "(a|b)*": 1, "a*b*": 2, "ab": 3, "a": 2, "λ": 1, "∅": 1}
    for texto, cantidad in tamanos.items():
        assert len(er_a_afd_minimo(texto).afd_minimo.estados) == cantidad, texto


def test_vacio_con_alfabeto_extra_no_acepta_nada():
    from automatas.core.finitos import acepta
    p = er_a_afd_minimo("∅", alfabeto={"a"})
    assert len(p.afd_minimo.estados) == 1 and not acepta(p.afd_minimo, "") and not acepta(p.afd_minimo, "aa")


def test_estados_del_afd_minimo_son_q0_en_adelante():
    p = er_a_afd_minimo("(a|b)*abb")
    assert p.afd_minimo.estados == {"q0", "q1", "q2", "q3"} and p.afd_minimo.inicial == "q0"
