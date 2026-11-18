"""Punto de entrada:  python main.py   (abre la interfaz en el navegador, no instala nada)."""
import argparse

from automatas.web.servidor import iniciar

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Laboratorio de autómatas")
    parser.add_argument("--puerto", type=int, default=8080, help="puerto local (por defecto 8080)")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador automáticamente")
    argumentos = parser.parse_args()
    iniciar(argumentos.puerto, abrir=not argumentos.no_abrir)
