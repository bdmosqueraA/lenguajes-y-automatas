"""Demostración por consola del Día 1: tabla, tipo y trazas de los ejemplos."""
from automatas.core.finitos import ejecutar
from automatas.datos.ejemplos import EJEMPLOS

CADENAS = {
    "AFD de la introducción (a,b)": ["aabab", "aababa"],
    "AFD incompleto (0,1)": ["0", "100", "00"],
    "AFD de minimización (8 estados)": ["01", "00"],
    "AFND: termina en 01": ["1101", "110"],
    "AFND-λ: a*b*": ["aabb", "ba", ""],
}

for nombre, fabrica in EJEMPLOS.items():
    automata = fabrica()
    print("=" * 70)
    print(automata.descripcion())
    print()
    print(automata.tabla())
    for cadena in CADENAS[nombre]:
        print()
        print(ejecutar(automata, cadena).resumen())
    print()
