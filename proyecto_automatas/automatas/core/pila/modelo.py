"""Autómatas de pila (AP) con traza paso a paso y manejo del no determinismo.

AP = (Q, Σ, Γ, δ, q0, Z0, F), como en clase. Una transición se escribe

    (origen, leído, desapila / apila, destino)        o, como arco:   a, X / α

* leído    : símbolo de entrada o λ (λ = no consume entrada).
* desapila : símbolo que debe estar en la cima y se retira; λ = no consulta la pila
             (como en el ejemplo de clase  δ(q0, a, λ) = (q0, A) ).
* apila    : palabra que se coloca en la pila; su primer carácter queda en la cima.

Aceptación (se elige al ejecutar):
* "estado_final": toda la entrada consumida y el autómata en un estado de F.
* "pila_vacia"  : toda la entrada consumida y la pila vacía.

Como un AP puede ser no determinista, la ejecución explora todas las ramas a lo
ancho (BFS), con un límite de configuraciones para no quedar atrapada en ciclos
de transiciones λ que apilan sin fin.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from ..finitos.modelo import LAMBDA, clave_natural, formato_conjunto

MODOS = ("estado_final", "pila_vacia")


class PilaInvalida(ValueError):
    """La definición del autómata de pila es inconsistente."""


def _vacio(texto: str) -> str:
    """λ se guarda internamente como cadena vacía."""
    return "" if texto in ("", LAMBDA) else texto


def _mostrar(texto: str) -> str:
    return texto if texto else LAMBDA


@dataclass(frozen=True)
class TransicionAP:
    origen: str
    leido: str        # "" = λ
    desapila: str     # "" = λ (no consulta la pila)
    destino: str
    apila: str        # "" = λ ; el primer carácter queda en la cima

    def texto(self) -> str:
        return (f"{self.origen} —{_mostrar(self.leido)},{_mostrar(self.desapila)}"
                f"/{_mostrar(self.apila)}→ {self.destino}")


@dataclass(frozen=True)
class Configuracion:
    estado: str
    restante: str     # entrada sin consumir
    pila: str         # cima a la izquierda; "" = pila vacía


@dataclass(frozen=True)
class PasoAP:
    indice: int
    transicion: TransicionAP | None    # None en la configuración inicial
    configuracion: Configuracion


@dataclass(frozen=True)
class TrazaAP:
    cadena: str
    modo: str
    acepta: bool
    camino: tuple             # PasoAP: el camino aceptador o, si se rechaza, el que más entrada consumió
    explorado: int            # configuraciones distintas visitadas
    limite_alcanzado: bool    # la búsqueda se cortó: puede haber ramas sin explorar
    motivo: str

    def resumen(self) -> str:
        lineas = []
        for p in self.camino:
            c = p.configuracion
            usada = p.transicion.texto() if p.transicion else "inicio"
            lineas.append(f"  {p.indice}: ({c.estado}, {c.restante or 'λ'}, {c.pila or 'λ'})   {usada}")
        veredicto = "ACEPTADA" if self.acepta else "RECHAZADA"
        return f"'{self.cadena or 'λ'}' {veredicto}\n" + "\n".join(lineas) + f"\n  {self.motivo}"


@dataclass
class AutomataPila:
    estados: set
    entrada: set
    pila: set                 # Γ
    transiciones: list        # [TransicionAP]
    inicial: str
    simbolo_inicial: str      # Z0 ("" = pila inicial vacía)
    finales: set
    modo: str = "estado_final"
    nombre: str = ""

    def __post_init__(self):
        self.estados = set(self.estados)
        self.entrada = set(self.entrada)
        self.pila = set(self.pila)
        self.finales = set(self.finales)
        self.simbolo_inicial = _vacio(self.simbolo_inicial)
        self.transiciones = sorted(set(self.transiciones), key=lambda t: (
            clave_natural(t.origen), t.leido, t.desapila, clave_natural(t.destino), t.apila))
        self.validar()

    @classmethod
    def desde_transiciones(cls, transiciones, inicial, finales=(), simbolo_inicial="Z",
                           modo="estado_final", nombre="", entrada=None, pila=None):
        """transiciones: tuplas (origen, leído, desapila, destino, apila); "" o "λ" = λ."""
        lista = [TransicionAP(o, _vacio(a), _vacio(x), d, _vacio(w)) for o, a, x, d, w in transiciones]
        estados = {inicial} | set(finales)
        for t in lista:
            estados |= {t.origen, t.destino}
        entrada = set(entrada) if entrada is not None else {t.leido for t in lista if t.leido}
        if pila is None:
            pila = set(_vacio(simbolo_inicial))
            for t in lista:
                pila |= set(t.desapila) | set(t.apila)
        return cls(estados, entrada, pila, lista, inicial, simbolo_inicial, set(finales), modo, nombre)

    # ------------------------------------------------------------------ #
    def validar(self) -> None:
        if not self.estados:
            raise PilaInvalida("El autómata debe tener al menos un estado.")
        if self.inicial not in self.estados:
            raise PilaInvalida(f"El estado inicial '{self.inicial}' no está en Q.")
        if self.finales - self.estados:
            raise PilaInvalida(f"Estados finales que no están en Q: {formato_conjunto(self.finales - self.estados)}.")
        if self.modo not in MODOS:
            raise PilaInvalida(f"Modo de aceptación desconocido: '{self.modo}'.")
        if len(self.simbolo_inicial) > 1:
            raise PilaInvalida("El símbolo inicial de la pila (Z0) debe ser un solo carácter o λ.")
        for simbolo in self.entrada | self.pila:
            if len(simbolo) != 1:
                raise PilaInvalida(f"Los símbolos deben ser de un carácter: '{simbolo}'.")
        if self.simbolo_inicial and self.simbolo_inicial not in self.pila:
            raise PilaInvalida(f"Z0 = '{self.simbolo_inicial}' no está en Γ.")
        for t in self.transiciones:
            if t.origen not in self.estados or t.destino not in self.estados:
                raise PilaInvalida(f"Transición con estados desconocidos: {t.texto()}.")
            if len(t.leido) > 1 or len(t.desapila) > 1:
                raise PilaInvalida(f"El símbolo leído y el que se desapila son de un carácter: {t.texto()}.")
            if t.leido and t.leido not in self.entrada:
                raise PilaInvalida(f"'{t.leido}' no está en Σ ({t.texto()}).")
            if t.desapila and t.desapila not in self.pila:
                raise PilaInvalida(f"'{t.desapila}' no está en Γ ({t.texto()}).")
            for c in t.apila:
                if c not in self.pila:
                    raise PilaInvalida(f"'{c}' no está en Γ ({t.texto()}).")

    # ------------------------------------------------------------------ #
    def es_determinista(self) -> bool:
        """Ningún par de transiciones del mismo estado puede aplicarse a la vez."""
        compatible = lambda x, y: x == "" or y == "" or x == y
        for i, t in enumerate(self.transiciones):
            for u in self.transiciones[i + 1:]:
                if (t.origen == u.origen and compatible(t.leido, u.leido)
                        and compatible(t.desapila, u.desapila)):
                    return False
        return True

    def descripcion(self) -> str:
        z0 = self.simbolo_inicial or "λ"
        tipo = "determinista" if self.es_determinista() else "no determinista"
        return (f"{self.nombre + ' — ' if self.nombre else ''}AP {tipo}  Q={formato_conjunto(self.estados)}  "
                f"Σ={formato_conjunto(self.entrada)}  Γ={formato_conjunto(self.pila)}  q0={self.inicial}  "
                f"Z0={z0}  F={formato_conjunto(self.finales)}  (acepta por {self.modo.replace('_', ' ')})")

    def a_dict(self) -> dict:
        return {
            "nombre": self.nombre, "modo": self.modo,
            "estados": sorted(self.estados, key=clave_natural),
            "entrada": sorted(self.entrada), "pila": sorted(self.pila),
            "inicial": self.inicial, "simbolo_inicial": self.simbolo_inicial,
            "finales": sorted(self.finales, key=clave_natural),
            "transiciones": [{"origen": t.origen, "leido": t.leido, "desapila": t.desapila,
                              "destino": t.destino, "apila": t.apila} for t in self.transiciones],
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "AutomataPila":
        try:
            trans = [(t["origen"], t["leido"], t["desapila"], t["destino"], t["apila"])
                     for t in datos["transiciones"]]
            ap = cls.desde_transiciones(
                trans, datos["inicial"], datos.get("finales", []),
                simbolo_inicial=datos.get("simbolo_inicial", ""), modo=datos.get("modo", "estado_final"),
                nombre=datos.get("nombre", ""), entrada=datos["entrada"], pila=datos["pila"])
        except KeyError as error:
            raise PilaInvalida(f"Falta el campo {error} en la definición.") from error
        ap.estados |= set(datos.get("estados", []))
        ap.validar()
        return ap


# ---------------------------------------------------------------------- #
# Ejecución
# ---------------------------------------------------------------------- #
def _aplicables(ap: AutomataPila, c: Configuracion):
    for t in ap.transiciones:
        if t.origen != c.estado:
            continue
        if t.leido and not (c.restante and c.restante[0] == t.leido):
            continue
        if t.desapila and not (c.pila and c.pila[0] == t.desapila):
            continue
        yield t


def _aplicar(c: Configuracion, t: TransicionAP) -> Configuracion:
    restante = c.restante[1:] if t.leido else c.restante
    resto_pila = c.pila[1:] if t.desapila else c.pila
    return Configuracion(t.destino, restante, t.apila + resto_pila)


def _termina_aceptando(ap: AutomataPila, c: Configuracion, modo: str) -> bool:
    if c.restante:
        return False
    return c.estado in ap.finales if modo == "estado_final" else c.pila == ""


def ejecutar(ap: AutomataPila, cadena: str, modo: str | None = None,
             max_configuraciones: int = 50_000) -> TrazaAP:
    """Busca, a lo ancho, un camino que acepte `cadena` (el más corto si existe)."""
    modo = modo or ap.modo
    if modo not in MODOS:
        raise PilaInvalida(f"Modo de aceptación desconocido: '{modo}'.")
    for i, simbolo in enumerate(cadena, start=1):
        if simbolo not in ap.entrada:
            inicial = Configuracion(ap.inicial, cadena, ap.simbolo_inicial)
            return TrazaAP(cadena, modo, False, (PasoAP(0, None, inicial),), 1, False,
                           f"El símbolo '{simbolo}' (posición {i}) no pertenece a Σ.")

    inicial = Configuracion(ap.inicial, cadena, ap.simbolo_inicial)
    padres = {inicial: None}                 # configuración -> (configuración anterior, transición)
    cola = deque([inicial])
    mejor = inicial                          # la que más entrada consumió (para mostrar si se rechaza)
    limite = False

    def camino_hasta(destino: Configuracion) -> tuple:
        pasos = []
        actual = destino
        while actual is not None:
            previo = padres[actual]
            pasos.append((actual, previo[1] if previo else None))
            actual = previo[0] if previo else None
        pasos.reverse()
        return tuple(PasoAP(i, t, c) for i, (c, t) in enumerate(pasos))

    while cola:
        actual = cola.popleft()
        if _termina_aceptando(ap, actual, modo):
            motivo = (f"Entrada consumida y estado de aceptación {actual.estado}."
                      if modo == "estado_final" else "Entrada consumida y pila vacía.")
            return TrazaAP(cadena, modo, True, camino_hasta(actual), len(padres), False, motivo)
        if len(actual.restante) < len(mejor.restante):
            mejor = actual
        for t in _aplicables(ap, actual):
            nueva = _aplicar(actual, t)
            if nueva in padres:
                continue
            if len(padres) >= max_configuraciones:
                limite = True
                continue
            padres[nueva] = (actual, t)
            cola.append(nueva)

    if limite:
        motivo = (f"Se alcanzó el límite de {max_configuraciones} configuraciones sin aceptar: "
                  "no se puede asegurar que la cadena sea rechazada.")
    else:
        motivo = f"Ninguna de las {len(padres)} configuraciones alcanzadas acepta la cadena."
    return TrazaAP(cadena, modo, False, camino_hasta(mejor), len(padres), limite, motivo)


def acepta(ap: AutomataPila, cadena: str, modo: str | None = None) -> bool:
    return ejecutar(ap, cadena, modo).acepta
