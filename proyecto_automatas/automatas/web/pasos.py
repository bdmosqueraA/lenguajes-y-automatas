from __future__ import annotations

from ..core.finitos import (LAMBDA, Automata, a_afd, a_er, clausura_lambda, completar, minimizar,
                            renombrar_estados, thompson)
from ..core.finitos import er as _er
from ..core.finitos.modelo import OperacionInvalida, clave_natural, formato_conjunto

# ---------------------------------------------------------------------- #
# Utilidades de construcción
# ---------------------------------------------------------------------- #
def _etiqueta(simbolos) -> str:
    return ", ".join(sorted(simbolos, key=lambda s: (s == LAMBDA, s)))


def _celda(destinos) -> str:
    if len(destinos) == 1:
        return next(iter(destinos))
    return formato_conjunto(destinos)


def _paso(titulo: str, texto: str, tablas=(), grafo=None) -> dict:
    return {"titulo": titulo, "texto": texto, "tablas": list(tablas), "grafo": grafo}


def _grafo(clave: str, nodos: list, aristas: list, leyenda=None) -> dict:
    return {"clave": clave, "nodos": nodos, "aristas": aristas, "leyenda": leyenda or []}


def grafo_de_automata(a: Automata, clave: str, nodos_res=(), aristas_res=(), colores=None,
                      leyenda=None, solo_estados=None) -> dict:
    colores = colores or {}
    nodos = [{"id": q, "inicial": q == a.inicial, "final": q in a.finales,
              "resaltado": q in nodos_res, "color": colores.get(q)}
             for q in sorted(a.estados, key=clave_natural)
             if solo_estados is None or q in solo_estados]
    agrupadas: dict = {}
    for origen, simbolo, destino in a.transiciones():
        agrupadas.setdefault((origen, destino), []).append(simbolo)
    aristas = [{"origen": o, "destino": d, "etiqueta": _etiqueta(ss), "resaltada": (o, d) in aristas_res}
               for (o, d), ss in agrupadas.items()]
    return _grafo(clave, nodos, aristas, leyenda)


def tabla_automata(a: Automata, titulo: str = "Tabla de transición", resaltar=()) -> dict:
    simbolos = sorted(a.alfabeto) + ([LAMBDA] if a.tiene_lambda() else [])
    filas, marcadas = [], []
    for i, q in enumerate(sorted(a.estados, key=clave_natural)):
        marca = ("→" if q == a.inicial else "") + ("#" if q in a.finales else "")
        filas.append([marca + q] + [_celda(a.destinos(q, s)) for s in simbolos])
        if q in resaltar:
            marcadas.append(i)
    return {"titulo": titulo, "columnas": ["δ"] + simbolos, "filas": filas, "filas_resaltadas": marcadas}


def _bloques_texto(etiquetas, bloques) -> list:
    return [[e, formato_conjunto(b)] for e, b in zip(etiquetas, bloques)]


# ---------------------------------------------------------------------- #
# AFND / AFND-λ  ->  AFD
# ---------------------------------------------------------------------- #
def pasos_a_afd(a: Automata) -> tuple:
    res = a_afd(a)
    renombrado = a_afd(a, renombrar=True)
    simbolos = sorted(a.alfabeto)
    con_lambda = a.tiene_lambda()
    nombre = formato_conjunto
    pasos = []

    if con_lambda:
        filas = [[q, formato_conjunto(clausura_lambda(a, q))] for q in sorted(a.estados, key=clave_natural)]
        con_l = {(o, d) for o, s, d in a.transiciones() if s == LAMBDA}
        pasos.append(_paso(
            "λ-clausura de cada estado",
            "La λ-clausura de un estado q es el conjunto de estados a los que se llega desde q usando "
            "solo transiciones λ (q siempre se incluye). Las flechas con λ están resaltadas.",
            [{"titulo": "λ-clausura", "columnas": ["Estado q", "λ-clausura(q)"], "filas": filas,
              "filas_resaltadas": []}],
            grafo_de_automata(a, "original", aristas_res=con_l)))

    inicial = res.clausura_inicial
    texto = (f"El estado inicial del AFD es la λ-clausura del inicial {a.inicial}: {nombre(inicial)}."
             if con_lambda else f"El estado inicial del AFD es {nombre(inicial)} (el inicial del autómata).")

    descubiertos = [inicial]
    transiciones: dict = {}

    def grafo_parcial(actual=None):
        nodos = [{"id": nombre(s), "inicial": s == inicial, "final": bool(s & a.finales),
                  "resaltado": s == actual, "color": None} for s in descubiertos]
        agrupadas: dict = {}
        for (s, simbolo), t in transiciones.items():
            agrupadas.setdefault((nombre(s), nombre(t)), []).append(simbolo)
        aristas = [{"origen": o, "destino": d, "etiqueta": _etiqueta(ss),
                    "resaltada": actual is not None and o == nombre(actual)}
                   for (o, d), ss in agrupadas.items()]
        return _grafo("afd", nodos, aristas)

    pasos.append(_paso("Estado inicial del AFD", texto, [], grafo_parcial(inicial)))

    por_origen: dict = {}
    for fila in res.filas:
        por_origen.setdefault(fila.origen, []).append(fila)
    procesados = []
    for origen, filas in por_origen.items():
        encabezado = (["Símbolo", "mover(S, símbolo)", "λ-clausura", "¿Estado nuevo?"] if con_lambda
                      else ["Símbolo", "mover(S, símbolo) = destino", "¿Estado nuevo?"])
        tabla_filas = []
        for f in filas:
            nuevo = "sí" if f.nuevo else ("no" if f.destino else "—")
            if con_lambda:
                tabla_filas.append([f.simbolo, nombre(f.mover), nombre(f.destino), nuevo])
            else:
                tabla_filas.append([f.simbolo, nombre(f.destino), nuevo])
            if f.destino:
                transiciones[(origen, f.simbolo)] = f.destino
                if f.nuevo:
                    descubiertos.append(f.destino)
        procesados.append(origen)
        pendientes = [s for s in descubiertos if s not in procesados]
        acumulada = {"titulo": "Tabla del AFD hasta ahora", "columnas": ["δ"] + simbolos,
                     "filas": [[("→" if s == inicial else "") + ("#" if s & a.finales else "") + nombre(s)]
                               + [nombre(transiciones[(s, x)]) if (s, x) in transiciones else "∅" for x in simbolos]
                               for s in procesados],
                     "filas_resaltadas": [len(procesados) - 1]}
        texto = (f"Se procesa el subconjunto {nombre(origen)}: para cada símbolo se calcula "
                 f"{'mover y su λ-clausura' if con_lambda else 'mover'}. ")
        texto += ("Pendientes por procesar: " + ", ".join(nombre(s) for s in pendientes) + "."
                  if pendientes else "No quedan subconjuntos pendientes.")
        pasos.append(_paso(f"Procesar {nombre(origen)}", texto,
                           [{"titulo": f"Transiciones de {nombre(origen)}", "columnas": encabezado,
                             "filas": tabla_filas, "filas_resaltadas": []}, acumulada],
                           grafo_parcial(origen)))

    afd = res.afd
    pasos.append(_paso(
        "AFD obtenido",
        "Cuando no quedan subconjuntos pendientes, la construcción termina. Cada subconjunto es un estado; "
        "es de aceptación si contiene algún estado de aceptación del autómata original. "
        "El subconjunto vacío (estado trampa) no se dibuja: use «Completar» si lo necesita.",
        [tabla_automata(afd, "Tabla de transición del AFD")],
        grafo_de_automata(afd, "afd")))

    nuevo_afd = renombrado.afd
    mapa = [[n, nombre(s), "sí" if n in nuevo_afd.finales else "no"]
            for n, s in sorted(renombrado.subconjuntos.items(), key=lambda kv: clave_natural(kv[0]))]
    pasos.append(_paso(
        "Renombrar los estados",
        "Para trabajar más cómodo, cada subconjunto recibe un nombre corto.",
        [{"titulo": "Equivalencia de nombres", "columnas": ["Estado nuevo", "Subconjunto", "¿Aceptación?"],
          "filas": mapa, "filas_resaltadas": []},
         tabla_automata(nuevo_afd, "AFD final")],
        grafo_de_automata(nuevo_afd, "afd_final")))
    return pasos, {"tipo": "automata", "automata": nuevo_afd}


# ---------------------------------------------------------------------- #
# Minimización de AFD
# ---------------------------------------------------------------------- #
def pasos_minimizar(a: Automata) -> tuple:
    r = minimizar(a)                      # lanza OperacionInvalida si no es AFD
    simbolos = sorted(r.preparado.alfabeto)
    pasos = []

    cambios = []
    if r.inaccesibles:
        cambios.append(f"Se eliminan los estados inaccesibles (no se puede llegar a ellos desde el inicial): "
                       f"{formato_conjunto(r.inaccesibles)}.")
    if r.trampa:
        cambios.append(f"El AFD es incompleto: se agrega el estado trampa {r.trampa} para que todas las "
                       "transiciones estén definidas (se ocultará al final).")
    if cambios:
        pasos.append(_paso("Preparación", " ".join(cambios),
                           [tabla_automata(r.preparado, "AFD preparado")],
                           grafo_de_automata(r.preparado, "preparado", nodos_res=({r.trampa} if r.trampa else ()))))
    else:
        pasos.append(_paso("Preparación",
                           "Todos los estados son accesibles y el AFD es completo: no hace falta preparar nada.",
                           [tabla_automata(a, "AFD de partida")], grafo_de_automata(a, "preparado")))

    def coloreado(iteracion, clave="preparado"):
        colores = {q: i for i, bloque in enumerate(iteracion.bloques) for q in bloque}
        leyenda = [{"color": i, "texto": f"{e} = {formato_conjunto(b)}"}
                   for i, (e, b) in enumerate(zip(iteracion.etiquetas, iteracion.bloques))]
        return grafo_de_automata(r.preparado, clave, colores=colores, leyenda=leyenda)

    inicial = r.iteraciones[0]
    pasos.append(_paso(
        "Partición inicial",
        "Se separan los estados de aceptación de los que no lo son: dos estados de distinto tipo nunca "
        "pueden ser equivalentes.",
        [{"titulo": "Conjuntos", "columnas": ["Conjunto", "Estados"],
          "filas": _bloques_texto(inicial.etiquetas, inicial.bloques), "filas_resaltadas": []}],
        coloreado(inicial)))

    for it in r.iteraciones[1:]:
        bloque_previo = {q: it.etiquetas_previas[i] for i, b in enumerate(it.previa) for q in b}
        bloque_nuevo = {q: it.etiquetas[i] for i, b in enumerate(it.bloques) for q in b}
        orden = [q for b in it.bloques for q in sorted(b, key=clave_natural)]
        filas = [[q, bloque_previo[q]] + list(it.tabla[q]) + [bloque_nuevo[q]] for q in orden]
        cambio = len(it.bloques) != len(it.previa)
        if cambio:
            texto = (f"Para cada estado se mira a qué conjunto lleva cada símbolo. Los estados de un mismo "
                     f"conjunto con filas distintas se separan: la partición pasa de {len(it.previa)} a "
                     f"{len(it.bloques)} conjuntos.")
        else:
            texto = ("Ningún conjunto se separó: la partición es estable y el proceso termina. "
                     "Los estados que quedaron juntos son equivalentes.")
        pasos.append(_paso(
            f"Iteración {it.numero}", texto,
            [{"titulo": "Conjunto al que lleva cada símbolo", "columnas": ["Estado", "Conjunto actual"] + simbolos + ["Conjunto nuevo"],
              "filas": filas, "filas_resaltadas": []},
             {"titulo": "Partición resultante", "columnas": ["Conjunto", "Estados"],
              "filas": _bloques_texto(it.etiquetas, it.bloques), "filas_resaltadas": []}],
            coloreado(it)))

    minimo, mapa = renombrar_estados(r.minimo)
    minimo.nombre = r.minimo.nombre
    equivalentes = [[mapa[nombre], nombre]
                    for nombre in sorted(r.minimo.estados, key=lambda n: clave_natural(mapa[n]))]
    texto = (f"Cada conjunto de estados equivalentes se convierte en un solo estado. El AFD tenía "
             f"{len(a.estados)} estados y el mínimo tiene {len(minimo.estados)}.")
    if r.trampa:
        texto += " El estado trampa que se agregó para minimizar no se dibuja."
    pasos.append(_paso(
        "Autómata mínimo", texto,
        [{"titulo": "Estados del mínimo", "columnas": ["Estado nuevo", "Estados equivalentes"],
          "filas": equivalentes, "filas_resaltadas": []},
         tabla_automata(minimo, "Tabla de transición del AFD mínimo")],
        grafo_de_automata(minimo, "minimo")))
    return pasos, {"tipo": "automata", "automata": minimo}


# ---------------------------------------------------------------------- #
# Completar y complemento
# ---------------------------------------------------------------------- #
def pasos_completar(a: Automata) -> tuple:
    if not a.es_determinista():
        raise OperacionInvalida("Solo se puede completar un AFD. Conviértalo primero con «Convertir a AFD».")
    if a.es_completo():
        return ([_paso("Ya es completo", "El AFD ya tiene todas las transiciones definidas.",
                       [tabla_automata(a)], grafo_de_automata(a, "completo"))],
                {"tipo": "automata", "automata": a.copia()})
    completo = completar(a)
    trampa = next(iter(completo.estados - a.estados))
    faltantes = [[q, s, trampa] for q in sorted(a.estados, key=clave_natural)
                 for s in sorted(a.alfabeto) if not a.destinos(q, s)]
    añadidas = {(o, d) for o, _, d in completo.transiciones() if d == trampa}
    pasos = [
        _paso("Transiciones que faltan",
              f"Se agrega el estado trampa {trampa}. Toda transición que faltaba va hacia él y el trampa "
              "se queda en sí mismo con todos los símbolos.",
              [{"titulo": "Transiciones agregadas", "columnas": ["Estado", "Símbolo", "Destino"],
                "filas": faltantes + [[trampa, s, trampa] for s in sorted(a.alfabeto)], "filas_resaltadas": []}],
              grafo_de_automata(completo, "completo", nodos_res={trampa}, aristas_res=añadidas)),
        _paso("AFD completo", "Ahora cada estado tiene una transición con cada símbolo.",
              [tabla_automata(completo, "Tabla de transición", resaltar={trampa})],
              grafo_de_automata(completo, "completo")),
    ]
    return pasos, {"tipo": "automata", "automata": completo}


def pasos_complemento(a: Automata) -> tuple:
    pasos = []
    base = a
    if not a.es_determinista():
        pasos_conv, resultado = pasos_a_afd(a)
        pasos += pasos_conv
        base = resultado["automata"]                 # para complementar hace falta un AFD
    if not base.es_completo():
        pasos_comp, resultado = pasos_completar(base)
        pasos += pasos_comp
        base = resultado["automata"]
    nuevo = Automata(base.estados, base.alfabeto, base.delta, base.inicial,
                     base.estados - base.finales, f"complemento de {a.nombre}" if a.nombre else "complemento")
    filas = [[q, "sí" if q in base.finales else "no", "sí" if q in nuevo.finales else "no"]
             for q in sorted(base.estados, key=clave_natural)]
    pasos.append(_paso(
        "Intercambiar estados de aceptación",
        "El complemento acepta justo las cadenas que el autómata rechazaba: los estados de aceptación pasan a "
        "ser de no aceptación y viceversa. El inicial y las transiciones no cambian.",
        [{"titulo": "Estados de aceptación", "columnas": ["Estado", "¿Final antes?", "¿Final ahora?"],
          "filas": filas, "filas_resaltadas": []},
         tabla_automata(nuevo, "Tabla de transición del complemento")],
        grafo_de_automata(nuevo, "complemento", nodos_res=set(nuevo.estados))))
    return pasos, {"tipo": "automata", "automata": nuevo}


# ---------------------------------------------------------------------- #
# Autómata -> ER (eliminación de estados)
# ---------------------------------------------------------------------- #
def pasos_a_er(a: Automata) -> tuple:
    r = a_er(a)
    pasos = []
    eliminados: list = []

    def grafo_gnfa(paso, resaltar_nodo=None):
        restantes = [q for q in sorted(a.estados, key=clave_natural) if q not in eliminados]
        nodos = [{"id": r.ini, "inicial": True, "final": False, "resaltado": False, "color": None},
                 {"id": r.fin, "inicial": False, "final": True, "resaltado": False, "color": None}]
        nodos += [{"id": q, "inicial": False, "final": False, "resaltado": q == resaltar_nodo, "color": None}
                  for q in restantes]
        aristas = [{"origen": o, "destino": d, "etiqueta": texto, "resaltada": (o, d) in paso.modificadas}
                   for (o, d), texto in paso.aristas.items()]
        return _grafo("gnfa", nodos, aristas)

    def tabla_aristas(paso):
        filas = [[o, d, texto] for (o, d), texto in paso.aristas.items()]
        marcadas = [i for i, (o, d) in enumerate(paso.aristas) if (o, d) in paso.modificadas]
        return {"titulo": "Aristas y sus expresiones", "columnas": ["Origen", "Destino", "Expresión"],
                "filas": filas, "filas_resaltadas": marcadas}

    for i, paso in enumerate(r.pasos):
        if paso.estado is None:
            pasos.append(_paso("Estados inicial y final únicos", paso.descripcion,
                               [tabla_aristas(paso)], grafo_gnfa(paso)))
        else:
            eliminados.append(paso.estado)
            pasos.append(_paso(
                f"Eliminar {paso.estado}",
                "Por cada flecha que entra a q y cada flecha que sale de q se crea (o se une) una flecha "
                "directa con la expresión  entrada · salida,  poniendo (bucle)* en medio si q tiene un "
                f"bucle. Después se borra q.\n{paso.descripcion.split(chr(10), 1)[1] if chr(10) in paso.descripcion else ''}",
                [tabla_aristas(paso)], grafo_gnfa(paso)))
    pasos.append(_paso("Expresión regular obtenida",
                       f"La etiqueta de la flecha {r.ini} → {r.fin} es la expresión regular del lenguaje:\n{r.texto}",
                       [], None))
    return pasos, {"tipo": "er", "texto": r.texto}


# ---------------------------------------------------------------------- #
# ER -> AFND-λ (Thompson)
# ---------------------------------------------------------------------- #
def pasos_thompson(res) -> tuple:
    pasos = []
    titulos = [p.descripcion.split(":")[0] for p in res.pasos]
    pasos.append(_paso(
        "Expresión regular",
        f"Expresión analizada: {res.texto}\nSe construye de adentro hacia afuera, un fragmento por "
        "operador (cada fragmento tiene un solo estado inicial y uno final). Orden: " + " → ".join(titulos) + ".",
        [], None))

    estados: list = []
    transiciones: list = []
    for i, p in enumerate(res.pasos, start=1):
        estados += list(p.estados)
        transiciones += list(p.transiciones)
        nuevos = set(p.estados)
        nodos = [{"id": q, "inicial": q == p.inicio, "final": q == p.fin, "resaltado": q in nuevos, "color": None}
                 for q in sorted(estados, key=clave_natural)]
        agrupadas: dict = {}
        for o, s, d in transiciones:
            agrupadas.setdefault((o, d), []).append(s)
        recientes = {(o, d) for o, _, d in p.transiciones}
        aristas = [{"origen": o, "destino": d, "etiqueta": _etiqueta(ss), "resaltada": (o, d) in recientes}
                   for (o, d), ss in agrupadas.items()]
        filas = [[o, s, d] for o, s, d in p.transiciones]
        tablas = ([{"titulo": "Transiciones agregadas en este paso", "columnas": ["Origen", "Símbolo", "Destino"],
                    "filas": filas, "filas_resaltadas": []}] if filas else [])
        pasos.append(_paso(f"Paso {i}: {p.descripcion.split(':')[0]}", p.descripcion, tablas,
                           _grafo("thompson", nodos, aristas)))

    a = res.automata
    pasos.append(_paso(
        "AFND-λ completo",
        f"El fragmento final es el autómata: inicial {a.inicial}, final {formato_conjunto(a.finales)}. "
        f"Tiene {len(a.estados)} estados.",
        [tabla_automata(a, "Tabla de transición del AFND-λ")],
        grafo_de_automata(a, "thompson")))
    return pasos, {"tipo": "automata", "automata": a}


def pasos_a_thompson(a: Automata) -> tuple:
    pasos_er, resultado_er = pasos_a_er(a)
    res = thompson(resultado_er["texto"], a.alfabeto)
    pasos_t, resultado = pasos_thompson(res)
    return pasos_er + pasos_t, resultado


OPERACIONES = {
    "a_afd": ("Convertir a AFD", pasos_a_afd),
    "minimizar": ("Minimizar", pasos_minimizar),
    "completar": ("Completar", pasos_completar),
    "complemento": ("Complemento", pasos_complemento),
    "a_er": ("Autómata → expresión regular", pasos_a_er),
    "a_thompson": ("Autómata → AFND-λ (vía ER y Thompson)", pasos_a_thompson),
}
