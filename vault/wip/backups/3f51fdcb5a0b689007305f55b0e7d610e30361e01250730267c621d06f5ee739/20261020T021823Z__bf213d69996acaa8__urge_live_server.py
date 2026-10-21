
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

runtime = Path(__file__).resolve().parent
sys.path.insert(0, str(runtime))

from iteration_service import iteration_service
from provider_configuration import validate
from provider_environment import load


class live_server:
    def __init__(self, service):
        self.service = service
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(
            target=self.loop.run_forever,
            daemon=True,
        )
        self.thread.start()

    def call(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(
            coroutine,
            self.loop,
        )
        return future.result(timeout=30)


class handler(BaseHTTPRequestHandler):
    server_version = "savant-urge-live/1"

    def _send(self, status, value):
        data = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 131072:
            raise ValueError("invalid request length")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("request must be an object")
        return value

    def _authorized(self):
        host = self.headers.get("Host", "")
        return host in {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }

    def do_GET(self):
        if not self._authorized():
            self._send(403, {"error": "invalid host"})
            return

        path = urlsplit(self.path).path
        if path == "/health":
            self._send(200, {
                "ok": True,
                "engine": "urge",
                "orchestration": "opus",
                "personas": "envoy",
                "mode": "live",
            })
            return

        if path == "/":
            page = Path(__file__).with_name("urge_live.html")
            data = page.read_bytes()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path.startswith("/sessions/"):
            parts = path.strip("/").split("/")
            if len(parts) not in (2, 3):
                self._send(404, {"error": "unknown endpoint"})
                return
            identity = parts[1]
            if not identity:
                self._send(400, {"error": "missing session"})
                return
            try:
                service = self.server.application.service
                if len(parts) == 3 and parts[2] == "history":
                    result = self.server.application.call(
                        service.history(identity)
                    )
                elif len(parts) == 2:
                    result = self.server.application.call(
                        service.status(identity)
                    )
                else:
                    self._send(404, {"error": "unknown endpoint"})
                    return
                self._send(200, result)
            except Exception as exc:
                self._send(400, {
                    "error": f"{type(exc).__name__}: {exc}"
                })
            return

        self._send(404, {"error": "unknown endpoint"})

    def do_POST(self):
        if not self._authorized():
            self._send(403, {"error": "invalid host"})
            return

        origin = self.headers.get("Origin")
        allowed = {
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        }
        if origin and origin not in allowed:
            self._send(403, {"error": "invalid origin"})
            return

        try:
            body = self._body()
            service = self.server.application.service
            path = urlsplit(self.path).path

            if path == "/sessions":
                goal = body["goal"]
                if not isinstance(goal, str) or not goal.strip():
                    raise ValueError("goal is required")
                if len(goal) > 16000:
                    raise ValueError("goal exceeds limit")

                settings = body.get("settings", {})
                if not isinstance(settings, dict):
                    raise ValueError("settings must be an object")

                identity = uuid.uuid4().hex
                result = self.server.application.call(
                    service.create_session(
                        session_id=identity,
                        goal=goal,
                        iteration_limit=body.get(
                            "iteration_limit", 3
                        ),
                        interval_seconds=body.get(
                            "interval_seconds", 1.0
                        ),
                        settings=settings,
                    )
                )
                self._send(201, result)
                return

            parts = path.strip("/").split("/")
            if (
                len(parts) == 3
                and parts[0] == "sessions"
                and parts[2] in {"start", "pause", "resume"}
            ):
                operation = getattr(service, parts[2])
                result = self.server.application.call(
                    operation(parts[1])
                )
                self._send(200, result)
                return

            self._send(404, {"error": "unknown endpoint"})
        except Exception as exc:
            self._send(400, {
                "error": f"{type(exc).__name__}: {exc}"
            })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument(
        "--credential-variable",
        required=True,
    )
    parser.add_argument(
        "--provider-id",
        default="primary",
    )
    parser.add_argument(
        "--journal",
        default="/root/savant-runtime/var/urge/sessions",
    )
    args = parser.parse_args()

    load()

    providers = validate(
        [{
            "id": args.provider_id,
            "model": args.model,
            "endpoint": args.endpoint,
            "credential_variable": args.credential_variable,
        }],
        require_credentials=True,
    )

    service = iteration_service(
        journal_directory=args.journal,
        providers=providers,
    )

    application = live_server(service)
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        handler,
    )
    server.application = application

    try:
        server.serve_forever()
    finally:
        server.server_close()
        application.loop.call_soon_threadsafe(
            application.loop.stop
        )


if __name__ == "__main__":
    main()
