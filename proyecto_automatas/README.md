# Laboratorio de autómatas (proyecto de Lenguajes de Programación)

Estado: **proyecto completo**: núcleo en Python probado + interfaz web con las cuatro pantallas (Finitos, Traductores, Pila y Turing): construir, dibujar y operar paso a paso.

| Familia | Módulo | Qué incluye |
|---|---|---|
| Finitos | `automatas/core/finitos/` | AFD, AFND, AFND-λ; simulación con traza; λ-clausura; AFND→AFD; completar; minimización con iteraciones; ER (analizador); Thompson; AF→ER; complemento; flujo ER→AFD mínimo |
| Traductores | `automatas/core/traductores/` | Moore y Mealy con traza y tablas de estados |
| Pila | `automatas/core/pila/` | AP no determinista (búsqueda a lo ancho), aceptación por estado final o pila vacía, pila visible en la traza |
| Turing | `automatas/core/turing/` | 1 cinta, k cintas y multipista; traza con cintas y cabezas; límite de pasos |
| Datos | `automatas/datos/` | ejemplos de clase por familia y JSON |
| Interfaz | `automatas/web/` | servidor local, API JSON, explicaciones paso a paso y página HTML/JS |

## Cómo ejecutar (desde esta carpeta)

    python main.py                # abre la interfaz en el navegador (http://127.0.0.1:8080)
    python main.py --puerto 8081  # si el 8080 está ocupado (también prueba solo con los siguientes)
    python main.py --no-abrir     # no abre el navegador

No hay que instalar nada: solo Python 3.9 o superior.

Pruebas y demostraciones:

    python ejecutar_pruebas.py    # 174 pruebas (las de navegador se omiten si falta playwright)
    python demo_nucleo.py         # recorrido por consola de todas las familias

Las pruebas de navegador usan Chromium real: `pip install playwright` y `playwright install chromium`.

## La pantalla de Finitos

1. **Tipo**: AFD, AFND, AFND-λ o expresión regular (se construye con Thompson).
2. **Definición**: matriz interactiva (estados, alfabeto, inicial, finales, destinos por celda; varios
   destinos separados por coma en AFND) o la expresión regular. El botón *Crear autómata* valida y dibuja.
3. **Operaciones** (según el tipo): probar cadenas, convertir a AFD (con tabla de λ-clausura y
   subconjuntos), minimizar (iteración por iteración), completar, complemento, autómata → ER y
   autómata → AFND-λ (vía ER y Thompson). Cada resultado se puede cargar de nuevo en la definición
   con *Usar este autómata* para encadenar operaciones.

El diagrama permite arrastrar los estados, reorganizar, ajustar a la vista y descargar como SVG.
Los autómatas se pueden guardar y abrir como JSON. Hay modo claro y oscuro.

## La pantalla de Traductores

Misma idea que Finitos: elegir **Moore** (salida en los estados) o **Mealy** (salida en las transiciones),
llenar la tabla (en Moore la columna *Salida* y el destino de cada celda; en Mealy `destino/salida`,
por ejemplo `q1/b`, con λ o nada para la salida vacía), pulsar *Crear máquina* y operar:

* **Traducir una cadena**: paso a paso, con la cinta de entrada, la cinta de salida que va creciendo,
  la transición recorrida y el estado actual resaltado en el diagrama.
* **Traducir varias cadenas**: una por línea (`λ` = cadena vacía) y una tabla de resultados.

Convención de clase: en Moore no se emite la salida del estado inicial. El alfabeto de salida Γ se deduce
de las salidas escritas. Los diez ejemplos precargados incluyen los de clase (011, paridad, suma módulo 5,
dos últimos símbolos) y detectores de 1001 y 111 con solapamiento.

## La pantalla de Pila

1. **Aceptación**: por estado final o por pila vacía.
2. **Definición**: tabla de estados (inicio, finales), símbolo inicial de la pila Z₀ y lista de transiciones
   `δ(origen, lee, desapila) = (destino, apila)`. «Desapila λ» no mira la pila y en «apila» el primer
   símbolo queda en la cima. Σ y Γ se deducen de las transiciones.
3. **Operaciones**: *Probar una cadena* (paso a paso, con la pila dibujada, la transición usada y las
   configuraciones exploradas; admite cambiar el modo de aceptación) y *Probar varias cadenas*.
   Como un AP puede ser no determinista, se exploran todas las ramas con un límite de configuraciones
   (si se alcanza, la pantalla avisa que no se puede asegurar el rechazo).

## La pantalla de Turing

1. **Tipo**: 1 cinta, multicinta (2 a 4 cintas) o multipista (2 o 3 pistas).
2. **Definición**: estados (inicio y finales), símbolo blanco, alfabeto de entrada A y transiciones
   `δ(origen, lee) = (destino, escribe, mueve)` con D, I o N; en multicinta hay un campo por cinta y en
   multipista un símbolo de varios caracteres (uno por pista, por ejemplo `0B`).
3. **Operaciones**: *Ejecutar una cadena* (cintas con la cabeza marcada, la transición usada, barra para
   saltar a cualquier paso, velocidad y límite de pasos por el problema de la parada) y *Ejecutar varias
   cadenas* (resultado en la cinta o las pistas al final). El diagrama agrupa las transiciones con
   `lee → escribe ; mueve` y usa `=` cuando se reescribe el mismo símbolo.

## Estructura

    automatas/core/       núcleo en Python (finitos, traductores, pila, Turing)
    automatas/web/        servidor.py (http.server), api.py, pasos.py (explicaciones) y estatico/ (HTML, CSS, JS)
    automatas/datos/      ejemplos de clase y JSON
    tests/                pruebas

## Convenciones tomadas de clase

* Tabla de transición: `→` estado inicial, `#` estado de aceptación.
* Moore: no emite la salida del estado inicial (Wout = γ(q2) γ(q3) …). Mealy: la salida puede ser λ.
* AP: δ(q, a, X) = (p, α); α con su primer símbolo en la cima; "desapila λ" no consulta la pila.
* Turing: cinta infinita solo a la derecha; mover a la izquierda del inicio bloquea la máquina.
* Minimización: `minimizar(a, quitar_inaccesibles=False)` replica el procedimiento de clase;
  por defecto se quitan antes los estados inaccesibles (en el ejemplo de 8 estados, q3).
