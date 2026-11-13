"""A minimal local web page for the triage app, on the standard library alone.

It listens on 127.0.0.1 only, answers only requests addressed to this machine by name (a guard
against DNS rebinding), serves one self-contained page whose Content-Security-Policy lets it
load nothing from elsewhere, and handles one ticket at a time, since one GPU runs one model.
"""

from __future__ import annotations

import json
import threading
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from .app import Generate, TriageError, triage
from .config import GenerationSettings

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_BODY_BYTES = 16_384

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
        "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

EXAMPLE_TICKET = (
    "Hello, my order #ORD-48213 for the Nimbus 2 wireless earbuds arrived yesterday, but the "
    "left earbud does not charge at all. I have tried two cables and two chargers. I would "
    "like a replacement sent before Friday, as they are a birthday gift. Thanks, Priya Raman "
    "(priya.raman@example.com)"
)


class TriageServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self, port: int, model: str, settings: GenerationSettings, generate: Generate
    ) -> None:
        self.model = model
        self.settings = settings
        self.generate = generate
        self.lock = threading.Lock()
        super().__init__((HOST, port), Handler)

    @property
    def allowed_hosts(self) -> set[str]:
        port = self.server_address[1]
        return {f"{HOST}:{port}", f"localhost:{port}"}


class Handler(BaseHTTPRequestHandler):
    server: TriageServer
    server_version = "local-ai-benchmark"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        """One line per request, never its body: tickets stay out of every log."""
        print(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _addressed_to_this_machine(self) -> bool:
        if self.headers.get("Host", "") not in self.server.allowed_hosts:
            self._json(HTTPStatus.FORBIDDEN, {"error": "this server answers only on localhost"})
            return False
        return True

    def do_GET(self) -> None:
        if not self._addressed_to_this_machine():
            return
        path = self.path.split("?")[0]
        if path == "/":
            self._send(HTTPStatus.OK, page(self.server.model), "text/html; charset=utf-8")
        elif path == "/api/health":
            self._json(HTTPStatus.OK, {"model": self.server.model, "host": HOST})
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._addressed_to_this_machine():
            return
        if self.path != "/api/triage":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        origin = self.headers.get("Origin")
        if origin is not None and origin.removeprefix("http://") not in self.server.allowed_hosts:
            self._json(HTTPStatus.FORBIDDEN, {"error": "requests from other sites are refused"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "the request is too large"})
            return
        try:
            data = json.loads(self.rfile.read(length) or b"null")
            ticket = data["ticket"]
            if not isinstance(ticket, str):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": 'send JSON: {"ticket": "..."}'})
            return
        try:
            with self.server.lock:
                result = triage(
                    ticket, self.server.model, self.server.settings, self.server.generate
                )
        except TriageError as exc:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(exc)})
            return
        self._json(HTTPStatus.OK, result.record())


def make_server(
    model: str, settings: GenerationSettings, generate: Generate, port: int = DEFAULT_PORT
) -> TriageServer:
    return TriageServer(port, model, settings, generate)


def page(model: str) -> bytes:
    """The whole app as one page: no external stylesheet, script, font or image."""
    example = json.dumps(EXAMPLE_TICKET)
    template = files(__package__).joinpath("static", "triage.html").read_text(encoding="utf-8")
    return (
        template.replace("{{MODEL}}", escape(model))
        .replace("{{EXAMPLE}}", example.replace("</", "<\\/"))
        .encode("utf-8")
    )
