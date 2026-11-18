"""Ejecuta todas las pruebas de la carpeta tests/ sin necesitar pytest.

    python ejecutar_pruebas.py
"""
import glob
import importlib
import os
import sys
import traceback
import unittest

raiz = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, raiz)

total = fallos = omitidas = 0
for ruta in sorted(glob.glob(os.path.join(raiz, "tests", "test_*.py"))):
    modulo = importlib.import_module("tests." + os.path.basename(ruta)[:-3])
    print(f"\n{modulo.__name__}")
    for nombre in sorted(n for n in dir(modulo) if n.startswith("test_")):
        total += 1
        try:
            getattr(modulo, nombre)()
            print(f"  OK     {nombre}")
        except unittest.SkipTest as motivo:
            omitidas += 1
            print(f"  OMITIDA {nombre}: {motivo}")
        except Exception:  # noqa: BLE001
            fallos += 1
            print(f"  FALLÓ  {nombre}")
            traceback.print_exc()
print(f"\n{total - fallos - omitidas}/{total - omitidas} pruebas correctas"
      + (f" ({omitidas} omitidas: requieren playwright)" if omitidas else ""))
sys.exit(1 if fallos else 0)
