"""Traductores secuenciales: máquinas de Moore y de Mealy.

Siguen la convención de la clase: M = (Q, Σ, Γ, δ, γ, q0), sin estados de aceptación.

* Moore : γ : Q -> Γ*        la salida depende del estado al que se llega.
          La salida del estado inicial NO se emite; por cada símbolo leído
          se emite γ del estado alcanzado (Wout = γ(q2) γ(q3) ...).
* Mealy : γ : Q x Σ -> Γ*    la salida depende de la transición recorrida.

La salida de un paso puede ser la cadena vacía λ (se escribe "" en el código).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..finitos.modelo import clave_natural, formato_conjunto


class TraductorInvalido(ValueError):
    """La definición de la máquina es inconsistente."""


def _mostrar(salida: str) -> str:
    return salida if salida else "λ"


@dataclass(frozen=True)
class PasoTraduccion:
    indice: int            # 0 = configuración inicial
    simbolo: str | None
    origen: str | None
    estado: str
    salida: str            # salida emitida en este paso ("" = λ)
    acumulada: str         # salida total hasta aquí


@dataclass(frozen=True)
class TrazaTraduccion:
    cadena: str
    pasos: tuple
    salida: str
    completa: bool         # False si la máquina se bloqueó antes de leer toda la entrada
    motivo: str

    def resumen(self) -> str:
        lineas = []
        for p in self.pasos:
            if p.simbolo is None:
                lineas.append(f"  {p.indice}:      {p.estado}")
            else:
                lineas.append(f"  {p.indice}: {p.simbolo} -> {p.estado}   emite {_mostrar(p.salida)}")
        entrada = self.cadena if self.cadena else "λ"
        return (f"entrada '{entrada}'  salida '{self.salida if self.salida else 'λ'}'\n"
                + "\n".join(lineas) + f"\n  {self.motivo}")


@dataclass
class Traductor:
    tipo: str              # "moore" | "mealy"
    estados: set
    entrada: set           # Σ
    salida: set            # Γ
    delta: dict            # (estado, símbolo) -> estado
    salidas: dict          # Moore: estado -> texto ; Mealy: (estado, símbolo) -> texto
    inicial: str
    nombre: str = ""

    def __post_init__(self):
        self.estados = set(self.estados)
        self.entrada = set(self.entrada)
        self.salida = set(self.salida)
        self.delta = dict(self.delta)
        self.salidas = dict(self.salidas)
        if self.tipo == "mealy":          # transición sin salida indicada = λ
            for clave in self.delta:
                self.salidas.setdefault(clave, "")
        self.validar()

    # ------------------------------------------------------------------ #
    @classmethod
    def moore(cls, transiciones, salidas, inicial, entrada=None, salida=None, nombre=""):
        """transiciones: (origen, símbolo, destino); salidas: {estado: texto}."""
        transiciones = list(transiciones)
        estados = {inicial} | set(salidas)
        for origen, _, destino in transiciones:
            estados |= {origen, destino}
        entrada = set(entrada) if entrada is not None else {s for _, s, _ in transiciones}
        salida = set(salida) if salida is not None else {c for t in salidas.values() for c in t}
        delta = {(o, s): d for o, s, d in transiciones}
        return cls("moore", estados, entrada, salida, delta, salidas, inicial, nombre)

    @classmethod
    def mealy(cls, transiciones, inicial, entrada=None, salida=None, nombre=""):
        """transiciones: (origen, símbolo, destino, salida)."""
        transiciones = list(transiciones)
        estados = {inicial}
        for origen, _, destino, _ in transiciones:
            estados |= {origen, destino}
        entrada = set(entrada) if entrada is not None else {s for _, s, _, _ in transiciones}
        salida = set(salida) if salida is not None else {c for *_, t in transiciones for c in t}
        delta = {(o, s): d for o, s, d, _ in transiciones}
        salidas = {(o, s): t for o, s, _, t in transiciones}
        return cls("mealy", estados, entrada, salida, delta, salidas, inicial, nombre)

    # ------------------------------------------------------------------ #
    def validar(self) -> None:
        if self.tipo not in ("moore", "mealy"):
            raise TraductorInvalido(f"Tipo desconocido: '{self.tipo}'.")
        if not self.estados:
            raise TraductorInvalido("La máquina debe tener al menos un estado.")
        if self.inicial not in self.estados:
            raise TraductorInvalido(f"El estado inicial '{self.inicial}' no está en Q.")
        for simbolo in self.entrada | self.salida:
            if len(simbolo) != 1:
                raise TraductorInvalido(f"Los símbolos deben ser de un carácter: '{simbolo}'.")
        for (origen, simbolo), destino in self.delta.items():
            if origen not in self.estados or destino not in self.estados:
                raise TraductorInvalido(f"Transición con estados desconocidos: {origen} -> {destino}.")
            if simbolo not in self.entrada:
                raise TraductorInvalido(f"El símbolo '{simbolo}' no está en Σ.")
        if self.tipo == "moore":
            faltan = self.estados - set(self.salidas)
            if faltan:
                raise TraductorInvalido(
                    f"Cada estado de una máquina de Moore necesita salida; faltan: {formato_conjunto(faltan)}.")
            claves_salida = set(self.salidas)
            if claves_salida - self.estados:
                raise TraductorInvalido("Hay salidas definidas para estados que no existen.")
        else:
            sobran = set(self.salidas) - set(self.delta)
            if sobran:
                raise TraductorInvalido(f"Hay salidas para transiciones inexistentes: {sorted(sobran)}.")
        for texto in self.salidas.values():
            for c in texto:
                if c not in self.salida:
                    raise TraductorInvalido(f"La salida usa '{c}', que no está en Γ.")

    # ------------------------------------------------------------------ #
    def destino(self, estado: str, simbolo: str):
        return self.delta.get((estado, simbolo))

    def salida_de(self, estado: str, simbolo: str, destino: str) -> str:
        if self.tipo == "moore":
            return self.salidas[destino]
        return self.salidas[(estado, simbolo)]

    def transiciones(self) -> list:
        """Lista ordenada de (origen, símbolo, destino, salida). En Moore la salida es la del destino."""
        filas = [(o, s, d, self.salida_de(o, s, d)) for (o, s), d in self.delta.items()]
        return sorted(filas, key=lambda t: (clave_natural(t[0]), t[1]))

    def es_completa(self) -> bool:
        return all((q, a) in self.delta for q in self.estados for a in self.entrada)

    def descripcion(self) -> str:
        titulo = f"{self.nombre} — " if self.nombre else ""
        return (f"{titulo}Máquina de {self.tipo.capitalize()}  Q={formato_conjunto(self.estados)}  "
                f"Σ={formato_conjunto(self.entrada)}  Γ={formato_conjunto(self.salida)}  q0={self.inicial}")

    def tabla(self) -> str:
        """Tabla de estados como en clase: Moore (δ y salida) o Mealy (destino/salida)."""
        simbolos = sorted(self.entrada)
        encabezado = ["Estado"] + simbolos + (["Salida"] if self.tipo == "moore" else [])
        filas = []
        for q in sorted(self.estados, key=clave_natural):
            marca = "→" if q == self.inicial else ""
            fila = [marca + q]
            for s in simbolos:
                d = self.destino(q, s)
                if d is None:
                    fila.append("∅")
                elif self.tipo == "mealy":
                    fila.append(f"{d}/{_mostrar(self.salidas[(q, s)])}")
                else:
                    fila.append(d)
            if self.tipo == "moore":
                fila.append(_mostrar(self.salidas[q]))
            filas.append(fila)
        anchos = [max(len(f[i]) for f in [encabezado] + filas) for i in range(len(encabezado))]
        dar = lambda f: " | ".join(c.ljust(anchos[i]) for i, c in enumerate(f)).rstrip()
        return "\n".join([dar(encabezado), "-+-".join("-" * a for a in anchos)] + [dar(f) for f in filas])

    # ------------------------------------------------------------------ #
    def a_dict(self) -> dict:
        datos = {
            "tipo": self.tipo, "nombre": self.nombre,
            "estados": sorted(self.estados, key=clave_natural),
            "entrada": sorted(self.entrada), "salida": sorted(self.salida),
            "inicial": self.inicial,
        }
        if self.tipo == "moore":
            datos["transiciones"] = [{"origen": o, "simbolo": s, "destino": d}
                                     for o, s, d, _ in self.transiciones()]
            datos["salidas_estados"] = {q: self.salidas[q] for q in sorted(self.estados, key=clave_natural)}
        else:
            datos["transiciones"] = [{"origen": o, "simbolo": s, "destino": d, "salida": t}
                                     for o, s, d, t in self.transiciones()]
        return datos

    @classmethod
    def desde_dict(cls, datos: dict) -> "Traductor":
        try:
            comunes = dict(inicial=datos["inicial"], entrada=datos["entrada"],
                           salida=datos["salida"], nombre=datos.get("nombre", ""))
            if datos["tipo"] == "moore":
                trans = [(t["origen"], t["simbolo"], t["destino"]) for t in datos["transiciones"]]
                maquina = cls.moore(trans, datos["salidas_estados"], **comunes)
            elif datos["tipo"] == "mealy":
                trans = [(t["origen"], t["simbolo"], t["destino"], t.get("salida", ""))
                         for t in datos["transiciones"]]
                maquina = cls.mealy(trans, **comunes)
            else:
                raise TraductorInvalido(f"Tipo desconocido: '{datos['tipo']}'.")
        except KeyError as error:
            raise TraductorInvalido(f"Falta el campo {error} en la definición.") from error
        maquina.estados |= set(datos.get("estados", []))
        maquina.validar()
        return maquina


def traducir(maquina: Traductor, cadena: str) -> TrazaTraduccion:
    """Procesa `cadena` y devuelve la traza con la salida producida."""
    estado = maquina.inicial
    acumulada = ""
    pasos = [PasoTraduccion(0, None, None, estado, "", "")]
    for indice, simbolo in enumerate(cadena, start=1):
        if simbolo not in maquina.entrada:
            return TrazaTraduccion(cadena, tuple(pasos), acumulada, False,
                                   f"El símbolo '{simbolo}' (posición {indice}) no pertenece a Σ.")
        destino = maquina.destino(estado, simbolo)
        if destino is None:
            return TrazaTraduccion(cadena, tuple(pasos), acumulada, False,
                                   f"No hay transición desde {estado} con '{simbolo}' (posición {indice}).")
        emitida = maquina.salida_de(estado, simbolo, destino)
        acumulada += emitida
        pasos.append(PasoTraduccion(indice, simbolo, estado, destino, emitida, acumulada))
        estado = destino
    return TrazaTraduccion(cadena, tuple(pasos), acumulada, True,
                           f"Termina en {estado}.")
