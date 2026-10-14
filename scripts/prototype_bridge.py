"""Browser QA transport when the executor cannot bind a loopback TCP socket.

Requests are parsed by the real HTTP handler, with byte streams in place of a socket.
No network server and no fake game state are used.
"""

import io
import json
import sys
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citygame.__main__ import Handler
from citygame.game import Game


class Socket:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()

    def makefile(self, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.extend(data)


game = Game(sys.argv[1])
server = SimpleNamespace(game=game, server_port=8092)
for line in sys.stdin:
    try:
        req = json.loads(line)
        body = json.dumps(req["payload"]).encode() if "payload" in req else b""
        headers = {**req.get("headers", {}), "Host": "localhost:8092", "Content-Length": str(len(body))}
        if body:
            headers["Content-Type"] = "application/json"
        raw = f"{req.get('method', 'GET')} {req['path']} HTTP/1.0\r\n".encode()
        raw += "".join(f"{k}: {v}\r\n" for k, v in headers.items()).encode() + b"\r\n" + body
        socket = Socket(raw)
        with redirect_stderr(io.StringIO()):
            Handler(socket, ("127.0.0.1", 1234), server)
        head, response = bytes(socket.output).split(b"\r\n\r\n", 1)
        parts = head.decode().split("\r\n")
        result = {"status": int(parts[0].split()[1]), "headers": {k.lower(): v.strip() for k, v in (p.split(":", 1) for p in parts[1:])}, "body": response.decode()}
        print(json.dumps(result), flush=True)
    except Exception as error:
        print(json.dumps({"error": str(error)}), flush=True)
game.close()
