"""Servidor local: entrega la página y responde a la API. Solo biblioteca estándar de Python."""
from __future__ import annotations

import json
import mimetypes
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import api

RAIZ_ESTATICA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estatico")
LIMITE_CUERPO = 2 * 1024 * 1024
# En Windows el registro del sistema a veces declara .js como text/plain y el navegador rechaza los módulos
for _tipo, _ext in (("text/javascript", ".js"), ("text/css", ".css"), ("text/html", ".html"), ("image/svg+xml", ".svg")):
    mimetypes.add_type(_tipo, _ext)


class Manejador(BaseHTTPRequestHandler):
    server_version = "LaboratorioAutomatas/1.0"

    def log_message(self, formato, *args):          # sin ruido en la consola
        pass

    def _responder(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos: dict, codigo: int = 200) -> None:
        self._responder(codigo, json.dumps(datos, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8")

    def do_GET(self):
        ruta = self.path.split("?", 1)[0]
        if ruta in ("/", "/index.html"):
            ruta = "/estatico/index.html"
        if ruta == "/api/ejemplos":
            return self._json(api.manejar("ejemplos", {}))
        if not ruta.startswith("/estatico/"):
            return self._json({"ok": False, "mensaje": "No encontrado."}, 404)
        relativa = os.path.normpath(ruta[len("/estatico/"):])
        archivo = os.path.normpath(os.path.join(RAIZ_ESTATICA, relativa))
        if not archivo.startswith(RAIZ_ESTATICA + os.sep) or not os.path.isfile(archivo):
            return self._json({"ok": False, "mensaje": "No encontrado."}, 404)
        tipo = mimetypes.guess_type(archivo)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/json", "image/svg+xml"):
            tipo += "; charset=utf-8"
        with open(archivo, "rb") as f:
            self._responder(200, f.read(), tipo)

    def do_POST(self):
        if not self.path.startswith("/api/"):
            return self._json({"ok": False, "mensaje": "No encontrado."}, 404)
        accion = self.path[len("/api/"):].split("?", 1)[0]
        largo = int(self.headers.get("Content-Length") or 0)
        if largo > LIMITE_CUERPO:
            return self._json({"ok": False, "mensaje": "La petición es demasiado grande."}, 413)
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except ValueError:
            return self._json({"ok": False, "mensaje": "JSON inválido."}, 400)
        self._json(api.manejar(accion, datos))


def crear_servidor(puerto: int = 8080, intentos: int = 20) -> ThreadingHTTPServer:
    """Abre el servidor en 127.0.0.1; si el puerto está ocupado prueba con los siguientes."""
    ultimo_error = None
    for p in range(puerto, puerto + max(intentos, 1)):
        try:
            return ThreadingHTTPServer(("127.0.0.1", p), Manejador)
        except OSError as error:
            ultimo_error = error
            if puerto == 0:
                break
    raise ultimo_error


def iniciar(puerto: int = 8080, abrir: bool = True) -> None:
    servidor = crear_servidor(puerto)
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"Laboratorio de autómatas en {url}   (Ctrl+C para cerrar)", flush=True)
    if abrir:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando…")
    finally:
        servidor.server_close()
