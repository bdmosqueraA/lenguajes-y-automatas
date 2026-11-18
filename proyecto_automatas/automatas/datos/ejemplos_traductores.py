"""Máquinas de Moore y Mealy de las diapositivas de clase (ejemplos y ejercicios)."""
from __future__ import annotations

from ..core.traductores import Traductor


def moore_secuencia_011() -> Traductor:
    """Moore que detecta 011: la salida es 1 al reconocerla y 0 en otro caso."""
    return Traductor.moore(
        [("E0", "0", "E1"), ("E0", "1", "E0"),
         ("E1", "0", "E1"), ("E1", "1", "E2"),
         ("E2", "0", "E1"), ("E2", "1", "E3"),
         ("E3", "0", "E1"), ("E3", "1", "E0")],
        {"E0": "0", "E1": "0", "E2": "0", "E3": "1"},
        inicial="E0", nombre="Moore: detecta 011")


def mealy_secuencia_011() -> Traductor:
    """Mealy que detecta 011: la salida es 1 en la transición que completa la secuencia."""
    return Traductor.mealy(
        [("E0", "0", "E1", "0"), ("E0", "1", "E0", "0"),
         ("E1", "0", "E1", "0"), ("E1", "1", "E2", "0"),
         ("E2", "0", "E1", "0"), ("E2", "1", "E0", "1")],
        inicial="E0", nombre="Mealy: detecta 011")


def moore_paridad_de_unos() -> Traductor:
    """Moore: 'b' si la cantidad de unos leídos es impar y 'a' si es par."""
    return Traductor.moore(
        [("P", "0", "P"), ("P", "1", "I"), ("I", "0", "I"), ("I", "1", "P")],
        {"P": "a", "I": "b"}, inicial="P", nombre="Moore: paridad de unos")


def mealy_paridad_de_unos() -> Traductor:
    """Mealy equivalente a la anterior."""
    return Traductor.mealy(
        [("P", "0", "P", "a"), ("P", "1", "I", "b"), ("I", "0", "I", "b"), ("I", "1", "P", "a")],
        inicial="P", nombre="Mealy: paridad de unos")


def moore_suma_modulo_5() -> Traductor:
    """Ejercicio de laboratorio: suma parcial módulo 5 de dígitos {0,1,2,3}. 32130 -> 30144."""
    transiciones = [(f"s{k}", str(d), f"s{(k + d) % 5}") for k in range(5) for d in range(4)]
    return Traductor.moore(transiciones, {f"s{k}": str(k) for k in range(5)},
                           inicial="s0", nombre="Moore: suma parcial módulo 5")


def mealy_dos_ultimos_simbolos() -> Traductor:
    """Ejercicio de laboratorio: a si ninguno de los dos últimos símbolos es 1, b si
    exactamente uno lo es, λ en otro caso (y λ con el primer símbolo). 01101001 -> bbbbab."""
    return Traductor.mealy(
        [("S", "0", "A", ""), ("S", "1", "B", ""),
         ("A", "0", "A", "a"), ("A", "1", "B", "b"),
         ("B", "0", "A", "b"), ("B", "1", "B", "")],
        inicial="S", nombre="Mealy: dos últimos símbolos")


def _fallo(secuencia: str) -> list:
    """fallo[k] = longitud del borde más largo (prefijo = sufijo) de secuencia[:k]."""
    fallo = [0] * (len(secuencia) + 1)
    k = 0
    for i in range(1, len(secuencia)):
        while k and secuencia[i] != secuencia[k]:
            k = fallo[k]
        if secuencia[i] == secuencia[k]:
            k += 1
        fallo[i + 1] = k
    return fallo


def detector_de_secuencia(secuencia: str, tipo: str, alfabeto: str = "01") -> Traductor:
    """Traductor que emite 1 cuando acaba de leer `secuencia` (con solapamiento) y 0 en otro caso.

    Estado Ek = "llevo k símbolos de la secuencia". Moore usa E0..En (En emite 1);
    Mealy usa E0..E(n-1) y emite 1 en la transición que completa la secuencia.
    """
    n, fallo = len(secuencia), _fallo(secuencia)

    def avanzar(k: int, c: str) -> int:
        if k == n:
            k = fallo[n]
        while k and secuencia[k] != c:
            k = fallo[k]
        return k + 1 if secuencia[k] == c else k

    if tipo == "moore":
        transiciones = [(f"E{k}", c, f"E{avanzar(k, c)}") for k in range(n + 1) for c in alfabeto]
        salidas = {f"E{k}": "1" if k == n else "0" for k in range(n + 1)}
        return Traductor.moore(transiciones, salidas, "E0", entrada=set(alfabeto),
                               nombre=f"Moore: detecta {secuencia}")
    transiciones = []
    for k in range(n):
        for c in alfabeto:
            nuevo = avanzar(k, c)
            completa = nuevo == n
            transiciones.append((f"E{k}", c, f"E{fallo[n] if completa else nuevo}", "1" if completa else "0"))
    return Traductor.mealy(transiciones, "E0", entrada=set(alfabeto), nombre=f"Mealy: detecta {secuencia}")


EJEMPLOS_TRADUCTORES = {
    "Moore: detecta 011": moore_secuencia_011,
    "Mealy: detecta 011": mealy_secuencia_011,
    "Moore: paridad de unos": moore_paridad_de_unos,
    "Mealy: paridad de unos": mealy_paridad_de_unos,
    "Moore: suma parcial módulo 5": moore_suma_modulo_5,
    "Mealy: dos últimos símbolos": mealy_dos_ultimos_simbolos,
    "Moore: detecta 1001": lambda: detector_de_secuencia("1001", "moore"),
    "Mealy: detecta 1001": lambda: detector_de_secuencia("1001", "mealy"),
    "Moore: detecta 111": lambda: detector_de_secuencia("111", "moore"),
    "Mealy: detecta 111": lambda: detector_de_secuencia("111", "mealy"),
}
