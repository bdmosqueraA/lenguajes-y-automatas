"""Expresiones regulares: árbol sintáctico, analizador y escritura de vuelta a texto.

Sintaxis de entrada (de menor a mayor precedencia):

    unión            a|b
    concatenación    ab          (implícita)
    estrella         a*          cierre de Kleene
    cierre positivo  a+          (equivale a aa*)
    agrupación       (a|b)
    cadena vacía     λ  (también ε)
    lenguaje vacío   ∅
    escape           \\*  \\|  \\(  ...  (para usar un carácter especial como símbolo)

Cualquier otro carácter es un símbolo del alfabeto. Los espacios se ignoran.
"""
from __future__ import annotations

from dataclasses import dataclass

LAMBDAS = ("λ", "ε")
VACIO = "∅"
_ESPECIALES = set("|*+()\\")


class ErrorER(ValueError):
    """Error de sintaxis en una expresión regular."""

    def __init__(self, mensaje: str, posicion: int | None = None):
        self.mensaje = mensaje
        self.posicion = posicion
        texto = mensaje if posicion is None else f"{mensaje} (posición {posicion + 1})"
        super().__init__(texto)


# ---------------------------------------------------------------------- #
# Árbol sintáctico
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class Simbolo:
    c: str


@dataclass(frozen=True)
class Lambda:
    pass


@dataclass(frozen=True)
class Vacio:
    pass


@dataclass(frozen=True)
class Union:
    izq: object
    der: object


@dataclass(frozen=True)
class Concat:
    izq: object
    der: object


@dataclass(frozen=True)
class Estrella:
    e: object


@dataclass(frozen=True)
class Mas:
    e: object


# ---------------------------------------------------------------------- #
# Analizador (descenso recursivo)
# ---------------------------------------------------------------------- #
def _tokens(texto: str) -> list:
    tokens = []
    i = 0
    while i < len(texto):
        c = texto[i]
        if c.isspace():
            i += 1
            continue
        if c == "\\":
            if i + 1 >= len(texto):
                raise ErrorER("La barra invertida debe ir seguida de un carácter", i)
            tokens.append(("sim", texto[i + 1], i))
            i += 2
            continue
        if c in "|*+()":
            tokens.append((c, c, i))
        elif c in LAMBDAS:
            tokens.append(("lambda", c, i))
        elif c == VACIO:
            tokens.append(("vacio", c, i))
        else:
            tokens.append(("sim", c, i))
        i += 1
    return tokens


class _Analizador:
    def __init__(self, texto: str):
        self.texto = texto
        self.tokens = _tokens(texto)
        self.pos = 0

    def tipo(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def analizar(self):
        if not self.tokens:
            raise ErrorER("La expresión regular está vacía (use λ para la cadena vacía)")
        nodo = self.union()
        if self.pos < len(self.tokens):                  # sólo puede sobrar un ')'
            raise ErrorER("Paréntesis de cierre sin su apertura", self.tokens[self.pos][2])
        return nodo

    def union(self):
        nodo = self.concatenacion()
        while self.tipo() == "|":
            self.pos += 1
            nodo = Union(nodo, self.concatenacion())
        return nodo

    def concatenacion(self):
        factores = []
        while self.tipo() in ("sim", "lambda", "vacio", "("):
            factores.append(self.factor())
        if not factores:
            if self.pos < len(self.tokens):
                tipo, valor, posicion = self.tokens[self.pos]
                if tipo in ("*", "+"):
                    raise ErrorER(f"El operador '{valor}' no tiene operando", posicion)
                raise ErrorER("Falta un operando", posicion)
            raise ErrorER("Falta un operando al final de la expresión", len(self.texto))
        nodo = factores[0]
        for factor in factores[1:]:
            nodo = Concat(nodo, factor)
        return nodo

    def factor(self):
        nodo = self.base()
        while self.tipo() in ("*", "+"):
            nodo = Estrella(nodo) if self.tokens[self.pos][0] == "*" else Mas(nodo)
            self.pos += 1
        return nodo

    def base(self):
        tipo, valor, posicion = self.tokens[self.pos]
        self.pos += 1
        if tipo == "sim":
            return Simbolo(valor)
        if tipo == "lambda":
            return Lambda()
        if tipo == "vacio":
            return Vacio()
        nodo = self.union()                              # tipo == "("
        if self.tipo() != ")":
            raise ErrorER("Falta cerrar este paréntesis", posicion)
        self.pos += 1
        return nodo


def analizar(texto: str):
    """Convierte el texto de una ER en su árbol sintáctico (lanza ErrorER si es inválida)."""
    return _Analizador(texto).analizar()


# ---------------------------------------------------------------------- #
# Escritura (árbol -> texto) con los paréntesis mínimos
# ---------------------------------------------------------------------- #
def _escapar(c: str) -> str:
    if c in _ESPECIALES or c in LAMBDAS or c == VACIO or c.isspace():
        return "\\" + c
    return c


def _texto(nodo) -> tuple:
    """Devuelve (texto, precedencia). 1 unión, 2 concatenación, 3 postfijo, 4 átomo."""
    if isinstance(nodo, Simbolo):
        return _escapar(nodo.c), 4
    if isinstance(nodo, Lambda):
        return "λ", 4
    if isinstance(nodo, Vacio):
        return VACIO, 4
    if isinstance(nodo, Union):
        return f"{_con(nodo.izq, 1)}|{_con(nodo.der, 1)}", 1
    if isinstance(nodo, Concat):
        return f"{_con(nodo.izq, 2)}{_con(nodo.der, 2)}", 2
    if isinstance(nodo, (Estrella, Mas)):
        operador = "*" if isinstance(nodo, Estrella) else "+"
        return _con(nodo.e, 3) + operador, 3
    raise TypeError(f"Nodo desconocido: {nodo!r}")


def _con(nodo, minimo: int) -> str:
    texto, precedencia = _texto(nodo)
    return texto if precedencia >= minimo else f"({texto})"


def a_texto(nodo) -> str:
    return _texto(nodo)[0]


# ---------------------------------------------------------------------- #
# Consultas y constructores que simplifican
# ---------------------------------------------------------------------- #
def simbolos(nodo) -> set:
    """Símbolos del alfabeto que aparecen en la expresión."""
    if isinstance(nodo, Simbolo):
        return {nodo.c}
    if isinstance(nodo, (Union, Concat)):
        return simbolos(nodo.izq) | simbolos(nodo.der)
    if isinstance(nodo, (Estrella, Mas)):
        return simbolos(nodo.e)
    return set()


def acepta_vacia(nodo) -> bool:
    """¿La cadena vacía pertenece al lenguaje de la expresión?"""
    if isinstance(nodo, (Lambda, Estrella)):
        return True
    if isinstance(nodo, Union):
        return acepta_vacia(nodo.izq) or acepta_vacia(nodo.der)
    if isinstance(nodo, Concat):
        return acepta_vacia(nodo.izq) and acepta_vacia(nodo.der)
    if isinstance(nodo, Mas):
        return acepta_vacia(nodo.e)
    return False


def unir(a, b):
    if isinstance(a, Vacio):
        return b
    if isinstance(b, Vacio):
        return a
    if a == b:
        return a
    if isinstance(a, Lambda) and acepta_vacia(b):
        return b
    if isinstance(b, Lambda) and acepta_vacia(a):
        return a
    return Union(a, b)


def concatenar(a, b):
    if isinstance(a, Vacio) or isinstance(b, Vacio):
        return Vacio()
    if isinstance(a, Lambda):
        return b
    if isinstance(b, Lambda):
        return a
    return Concat(a, b)


def cerrar(a):
    """Estrella de Kleene simplificada: ∅* = λ* = λ, (a*)* = a*."""
    if isinstance(a, (Vacio, Lambda)):
        return Lambda()
    if isinstance(a, Estrella):
        return a
    if isinstance(a, Mas):
        return Estrella(a.e)
    return Estrella(a)
