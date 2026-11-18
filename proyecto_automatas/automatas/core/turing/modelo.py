"""Máquinas de Turing deterministas de k cintas, con soporte para multipista.

Sigue los apuntes de clase: MT = <E, A, C, δ, e0, B, F>.

* Cinta: infinita a la derecha; la celda 0 es el inicio. Mover la cabeza a la
  izquierda de la celda 0 no está permitido (la máquina se bloquea).
* δ : E x C^k -> E x (C x {D, I, N})^k   (D derecha, I izquierda, N no mover;
  también se aceptan R, L y S como en las diapositivas).
* La entrada se escribe en la cinta 1; las demás cintas empiezan en blanco.
* La máquina acepta apenas llega a un estado final. Se bloquea (rechaza) si no
  hay transición aplicable, y se corta con un aviso si supera `max_pasos`
  (puede ser un bucle infinito: el problema de la parada no se puede decidir).
* Multipista (`pistas` > 1): una sola cinta cuyas celdas guardan una tupla de
  símbolos, uno por pista. Un símbolo de celda es un texto de `pistas`
  caracteres, p. ej. "0B" = pista 1 con '0' y pista 2 en blanco.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..finitos.modelo import clave_natural, formato_conjunto

_MOVIMIENTOS = {"D": "D", "R": "D", "I": "I", "L": "I", "N": "N", "S": "N"}


class TuringInvalida(ValueError):
    """La definición de la máquina es inconsistente."""


@dataclass(frozen=True)
class TransicionMT:
    origen: str
    lecturas: tuple        # un símbolo por cinta
    destino: str
    escrituras: tuple
    movimientos: tuple     # "D" | "I" | "N" por cinta

    def texto(self) -> str:
        izq = ",".join(self.lecturas)
        der = ",".join(f"{w}{m}" for w, m in zip(self.escrituras, self.movimientos))
        return f"{self.origen}, {izq} → {self.destino}, {der}"


@dataclass(frozen=True)
class ConfigMT:
    estado: str
    cintas: tuple          # una tupla de símbolos por cinta (sin blancos al final)
    cabezas: tuple         # posición de la cabeza de cada cinta


@dataclass(frozen=True)
class PasoMT:
    indice: int
    transicion: TransicionMT | None
    configuracion: ConfigMT


@dataclass(frozen=True)
class TrazaMT:
    cadena: str
    pasos: tuple
    acepta: bool
    detenida: bool         # False si se cortó por llegar a max_pasos
    motivo: str

    @property
    def final(self) -> ConfigMT:
        return self.pasos[-1].configuracion


def _como_tupla(valor, k: int, que: str) -> tuple:
    """str de un solo símbolo (k=1), str con un carácter por cinta (k>1) o secuencia."""
    if isinstance(valor, str):
        return (valor,) if k == 1 else tuple(valor)
    return tuple(valor)


@dataclass
class MaquinaTuring:
    estados: set
    entrada: set            # A
    cinta: set              # C (caracteres; en multipista, los que puede tener cada pista)
    blanco: str
    inicial: str
    finales: set
    transiciones: list      # [TransicionMT]
    cintas: int = 1
    pistas: int = 1
    nombre: str = ""

    def __post_init__(self):
        self.estados = set(self.estados)
        self.entrada = set(self.entrada)
        self.cinta = set(self.cinta) | {self.blanco}
        self.finales = set(self.finales)
        self.transiciones = sorted(set(self.transiciones), key=lambda t: (
            clave_natural(t.origen), t.lecturas, clave_natural(t.destino)))
        self.validar()

    @classmethod
    def desde_transiciones(cls, transiciones, inicial, finales, entrada, cinta=None, blanco="B",
                           cintas=1, pistas=1, nombre=""):
        """transiciones: (origen, lecturas, destino, escrituras, movimientos).

        Con k cintas, lecturas/escrituras pueden ser una cadena con un carácter por cinta
        ("aB") y movimientos una cadena como "ND". Con una cinta, `lecturas` y `escrituras`
        son un solo símbolo (con `pistas` > 1, un texto de `pistas` caracteres).
        """
        lista = []
        for o, lec, d, esc, mov in transiciones:
            movs = tuple(_MOVIMIENTOS.get(m, m) for m in (mov if not isinstance(mov, str) else tuple(mov)))
            lista.append(TransicionMT(o, _como_tupla(lec, cintas, "lecturas"), d,
                                      _como_tupla(esc, cintas, "escrituras"), movs))
        estados = {inicial} | set(finales)
        for t in lista:
            estados |= {t.origen, t.destino}
        if cinta is None:
            cinta = set(entrada) | {blanco}
            for t in lista:
                for simbolo in t.lecturas + t.escrituras:
                    cinta |= set(simbolo)
        return cls(estados, entrada, cinta, blanco, inicial, set(finales), lista, cintas, pistas, nombre)

    # ------------------------------------------------------------------ #
    @property
    def blanco_celda(self) -> str:
        """Símbolo de una celda vacía (en multipista, el blanco de todas las pistas)."""
        return self.blanco * self.pistas

    def validar(self) -> None:
        if len(self.blanco) != 1:
            raise TuringInvalida("El blanco debe ser un solo carácter.")
        if self.cintas < 1 or self.pistas < 1:
            raise TuringInvalida("Debe haber al menos una cinta y una pista.")
        if self.pistas > 1 and self.cintas != 1:
            raise TuringInvalida("Multipista usa una sola cinta (cintas = 1).")
        if not self.estados:
            raise TuringInvalida("La máquina debe tener al menos un estado.")
        if self.inicial not in self.estados:
            raise TuringInvalida(f"El estado inicial '{self.inicial}' no está en E.")
        if self.finales - self.estados:
            raise TuringInvalida(f"Estados finales que no están en E: {formato_conjunto(self.finales - self.estados)}.")
        if self.blanco in self.entrada:
            raise TuringInvalida("El blanco no puede formar parte del alfabeto de entrada.")
        if not self.entrada <= self.cinta:
            raise TuringInvalida("El alfabeto de entrada debe estar contenido en el de la cinta.")
        for simbolo in self.cinta | self.entrada:
            if len(simbolo) != 1:
                raise TuringInvalida(f"Los símbolos de A y C son de un carácter: '{simbolo}'.")
        vistas = set()
        for t in self.transiciones:
            if t.origen not in self.estados or t.destino not in self.estados:
                raise TuringInvalida(f"Transición con estados desconocidos: {t.texto()}.")
            if not (len(t.lecturas) == len(t.escrituras) == len(t.movimientos) == self.cintas):
                raise TuringInvalida(f"La transición debe indicar {self.cintas} cinta(s): {t.texto()}.")
            for simbolo in t.lecturas + t.escrituras:
                if len(simbolo) != self.pistas or not set(simbolo) <= self.cinta:
                    raise TuringInvalida(f"Símbolo inválido '{simbolo}' en {t.texto()}.")
            for m in t.movimientos:
                if m not in ("D", "I", "N"):
                    raise TuringInvalida(f"Movimiento desconocido '{m}' en {t.texto()}.")
            clave = (t.origen, t.lecturas)
            if clave in vistas:
                raise TuringInvalida(f"Máquina no determinista: hay dos transiciones desde {t.origen} "
                                     f"leyendo {','.join(t.lecturas)}.")
            vistas.add(clave)

    def descripcion(self) -> str:
        forma = (f"{self.cintas} cintas" if self.cintas > 1
                 else f"multipista ({self.pistas} pistas)" if self.pistas > 1 else "1 cinta")
        return (f"{self.nombre + ' — ' if self.nombre else ''}Máquina de Turing, {forma}  "
                f"E={formato_conjunto(self.estados)}  A={formato_conjunto(self.entrada)}  "
                f"C={formato_conjunto(self.cinta)}  e0={self.inicial}  B={self.blanco}  "
                f"F={formato_conjunto(self.finales)}")

    def tabla(self) -> str:
        return "\n".join(t.texto() for t in self.transiciones)

    def a_dict(self) -> dict:
        return {
            "nombre": self.nombre, "cintas": self.cintas, "pistas": self.pistas,
            "estados": sorted(self.estados, key=clave_natural),
            "entrada": sorted(self.entrada), "cinta": sorted(self.cinta), "blanco": self.blanco,
            "inicial": self.inicial, "finales": sorted(self.finales, key=clave_natural),
            "transiciones": [{"origen": t.origen, "lecturas": list(t.lecturas), "destino": t.destino,
                              "escrituras": list(t.escrituras), "movimientos": list(t.movimientos)}
                             for t in self.transiciones],
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "MaquinaTuring":
        try:
            trans = [(t["origen"], tuple(t["lecturas"]), t["destino"], tuple(t["escrituras"]),
                      tuple(t["movimientos"])) for t in datos["transiciones"]]
            maquina = cls.desde_transiciones(
                trans, datos["inicial"], datos.get("finales", []), datos["entrada"],
                cinta=datos["cinta"], blanco=datos.get("blanco", "B"),
                cintas=datos.get("cintas", 1), pistas=datos.get("pistas", 1),
                nombre=datos.get("nombre", ""))
        except KeyError as error:
            raise TuringInvalida(f"Falta el campo {error} en la definición.") from error
        maquina.estados |= set(datos.get("estados", []))
        maquina.validar()
        return maquina


# ---------------------------------------------------------------------- #
# Ejecución
# ---------------------------------------------------------------------- #
def _instantanea(cintas: list, cabezas: list, estado: str, blanco: str) -> ConfigMT:
    recortadas = []
    for cinta in cintas:
        fin = len(cinta)
        while fin > 0 and cinta[fin - 1] == blanco:
            fin -= 1
        recortadas.append(tuple(cinta[:fin]))
    return ConfigMT(estado, tuple(recortadas), tuple(cabezas))


def simbolo_en(maquina: MaquinaTuring, config: ConfigMT, cinta: int, posicion: int | None = None) -> str:
    """Símbolo de la celda indicada (por defecto, la que apunta la cabeza)."""
    pos = config.cabezas[cinta] if posicion is None else posicion
    contenido = config.cintas[cinta]
    return contenido[pos] if pos < len(contenido) else maquina.blanco_celda


def contenido(maquina: MaquinaTuring, config: ConfigMT, cinta: int = 0, pista: int | None = None) -> str:
    """Texto de una cinta sin blancos al final. En multipista, `pista` elige una pista."""
    simbolos = config.cintas[cinta]
    if pista is None:
        return "".join(simbolos)
    texto = "".join(s[pista] for s in simbolos)
    return texto.rstrip(maquina.blanco)


def ejecutar(maquina: MaquinaTuring, cadena: str, max_pasos: int = 10_000) -> TrazaMT:
    for i, simbolo in enumerate(cadena, start=1):
        if simbolo not in maquina.entrada:
            vacia = _instantanea([[]] * maquina.cintas, [0] * maquina.cintas, maquina.inicial, maquina.blanco_celda)
            return TrazaMT(cadena, (PasoMT(0, None, vacia),), False, True,
                           f"El símbolo '{simbolo}' (posición {i}) no pertenece al alfabeto de entrada.")

    blanco = maquina.blanco_celda
    relleno = maquina.blanco * (maquina.pistas - 1)
    cintas = [[c + relleno for c in cadena]] + [[] for _ in range(maquina.cintas - 1)]
    cabezas = [0] * maquina.cintas
    estado = maquina.inicial
    tabla = {(t.origen, t.lecturas): t for t in maquina.transiciones}
    pasos = [PasoMT(0, None, _instantanea(cintas, cabezas, estado, blanco))]

    for paso in range(max_pasos + 1):
        if estado in maquina.finales:
            return TrazaMT(cadena, tuple(pasos), True, True, f"Acepta: llegó al estado final {estado}.")
        lecturas = tuple(c[h] if h < len(c) else blanco for c, h in zip(cintas, cabezas))
        t = tabla.get((estado, lecturas))
        if t is None:
            return TrazaMT(cadena, tuple(pasos), False, True,
                           f"Rechaza: no hay transición desde {estado} leyendo {','.join(lecturas)}.")
        if paso == max_pasos:
            break
        nuevas = list(cabezas)
        for i, (w, m) in enumerate(zip(t.escrituras, t.movimientos)):
            while len(cintas[i]) <= cabezas[i]:
                cintas[i].append(blanco)
            cintas[i][cabezas[i]] = w
            nuevas[i] += {"D": 1, "I": -1, "N": 0}[m]
            if nuevas[i] < 0:
                pasos.append(PasoMT(len(pasos), t, _instantanea(cintas, cabezas, estado, blanco)))
                return TrazaMT(cadena, tuple(pasos), False, True,
                               f"Rechaza: la cinta {i + 1} intentó moverse a la izquierda de su celda de inicio.")
        cabezas = nuevas
        estado = t.destino
        pasos.append(PasoMT(len(pasos), t, _instantanea(cintas, cabezas, estado, blanco)))

    return TrazaMT(cadena, tuple(pasos), False, False,
                   f"No se detuvo en {max_pasos} pasos: puede ser un bucle infinito "
                   "(el problema de la parada no se puede decidir en general).")


def acepta(maquina: MaquinaTuring, cadena: str, max_pasos: int = 10_000) -> bool:
    return ejecutar(maquina, cadena, max_pasos).acepta
