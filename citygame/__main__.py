from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from citysim.engine import RuleError
from .game import Game, ROOT


class Handler(BaseHTTPRequestHandler):
    def authorized(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookie["city_session"].value if "city_session" in cookie else ""
            return secrets.compare_digest(token, self.server.game.token)
        except Exception:
            return False

    def send(self, status, body, content_type="application/json", cookie=False):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") or content_type == "application/json" else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if cookie:
            self.send_header("Set-Cookie", f"city_session={self.server.game.token}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        with self.server.game.lock:
            if path == "/api/world":
                return self.send(200, self.server.game.public_snapshot())
            if path in ("/api/me", "/api/backup"):
                if not self.authorized():
                    return self.send(401, {"error": "Installe-toi pour retrouver ton carnet"})
                return self.send(200, self.server.game.backup() if path == "/api/backup" else self.server.game.snapshot())
        names = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/scene.js": "scene.js", "/style.css": "style.css", "/favicon.svg": "favicon.svg"}
        if path not in names:
            return self.send(404, {"error": "Lieu introuvable"})
        file = ROOT / "prototype/dist" / names[path]
        return self.send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "application/octet-stream")

    def do_POST(self):
        host = self.headers.get("Host", "")
        origins = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        if "http://" + host not in origins or self.headers.get("Origin") not in origins:
            return self.send(403, {"error": "Cette action doit venir du jeu local"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Commande JSON attendue"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise RuleError("Commande trop longue ou vide")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise RuleError("Commande invalide")
            path = urlsplit(self.path).path
            if path == "/api/session":
                return self.send(200, self.server.game.snapshot(), cookie=True)
            if not self.authorized():
                return self.send(401, {"error": "Installe-toi d'abord"})
            if path == "/api/move":
                self.server.game.move(body.get("x"), body.get("y"))
                return self.send(200, {"saved": True})
            if path == "/api/action":
                response = self.server.game.command(body.get("id"), body.get("action"), body.get("payload", {}))
                return self.send(200, response)
            return self.send(404, {"error": "Action inconnue"})
        except (ValueError, RuleError) as error:
            return self.send(400, {"error": str(error)})


def make_server(game, host="127.0.0.1", port=8092):
    server = ThreadingHTTPServer((host, port), Handler)
    server.game = game
    return server


def main():
    parser = argparse.ArgumentParser(description="City : prototype local jouable")
    parser.add_argument("--port", type=int, default=8092)
    parser.add_argument("--save", type=Path, default=ROOT / "data/prototype.sqlite")
    parser.add_argument("--restore", type=Path, help="Restaurer un export JSON dans un nouveau fichier --save")
    args = parser.parse_args()
    game = Game(args.save)
    if args.restore:
        if args.restore.stat().st_size > 2 * 1024 * 1024:
            parser.error("La sauvegarde dépasse la taille autorisée")
        game.restore_backup(json.loads(args.restore.read_text(encoding="utf-8")))
    server = make_server(game, port=args.port)
    print(f"City local : http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        game.close()


if __name__ == "__main__":
    main()
