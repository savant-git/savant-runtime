
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlsplit

runtime = Path(__file__).resolve().parent
sys.path.insert(0, str(runtime))

from iteration_service import iteration_service
from provider_configuration import validate
from provider_environment import load
from urge_session_api import urge_session_api


class application:
    def __init__(self, service):
        self.api = urge_session_api(
            service
        )

        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()

        def run():
            asyncio.set_event_loop(
                self.loop
            )
            self.ready.set()
            self.loop.run_forever()

        self.thread = threading.Thread(
            target=run,
            daemon=True,
        )

        self.thread.start()
        self.ready.wait()

    def execute(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(
            coroutine,
            self.loop,
        )

        return future.result(
            timeout=30
        )

    def close(self):
        self.loop.call_soon_threadsafe(
            self.loop.stop
        )
        self.thread.join(timeout=5)


class handler(BaseHTTPRequestHandler):
    server_version = "savant-urge-live/2"

    def json_response(
        self,
        status,
        value,
    ):
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )
        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )
        self.end_headers()
        self.wfile.write(encoded)

    def permitted(self):
        port = self.server.server_port

        return self.headers.get("Host") in {
            f"127.0.0.1:{port}",
            f"localhost:{port}",
        }

    def request_body(self):
        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        if not 1 <= length <= 131072:
            raise ValueError(
                "invalid request length"
            )

        body = json.loads(
            self.rfile.read(length)
        )

        if not isinstance(body, dict):
            raise ValueError(
                "request must be an object"
            )

        return body

    def execute(self, coroutine):
        return self.server.application.execute(
            coroutine
        )

    def do_GET(self):
        if not self.permitted():
            self.json_response(
                403,
                {"error": "invalid host"},
            )
            return

        path = urlsplit(
            self.path
        ).path

        if path == "/health":
            self.json_response(
                200,
                {
                    "ok": True,
                    "service": "urge",
                    "interface": "live",
                },
            )
            return

        if path == "/":
            page = runtime / "urge_live.html"

            if not page.is_file():
                self.json_response(
                    404,
                    {
                        "error":
                            "urge interface unavailable"
                    },
                )
                return

            encoded = page.read_bytes()

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )
            self.send_header(
                "Cache-Control",
                "no-store",
            )
            self.send_header(
                "Content-Length",
                str(len(encoded)),
            )
            self.end_headers()
            self.wfile.write(encoded)
            return

        parts = path.strip("/").split("/")

        if (
            len(parts) not in (2, 3)
            or parts[0] != "sessions"
            or not parts[1]
        ):
            self.json_response(
                404,
                {"error": "unknown endpoint"},
            )
            return

        identity = parts[1]
        api = self.server.application.api

        try:
            if len(parts) == 2:
                result = self.execute(
                    api.status(identity)
                )
            elif parts[2] == "history":
                result = self.execute(
                    api.history(identity)
                )
            elif parts[2] == "evidence":
                result = self.execute(
                    api.evidence(identity)
                )
            else:
                self.json_response(
                    404,
                    {"error": "unknown endpoint"},
                )
                return

            self.json_response(
                200,
                result,
            )

        except Exception as exc:
            self.json_response(
                400,
                {
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    )
                },
            )

    def do_POST(self):
        if not self.permitted():
            self.json_response(
                403,
                {"error": "invalid host"},
            )
            return

        port = self.server.server_port
        origin = self.headers.get("Origin")

        if origin and origin not in {
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
        }:
            self.json_response(
                403,
                {"error": "invalid origin"},
            )
            return

        try:
            body = self.request_body()
            path = urlsplit(
                self.path
            ).path

            api = self.server.application.api

            if path == "/sessions":
                result = self.execute(
                    api.create(body)
                )
                self.json_response(
                    201,
                    result,
                )
                return

            parts = path.strip("/").split("/")

            if (
                len(parts) == 3
                and parts[0] == "sessions"
                and parts[1]
                and parts[2] in {
                    "start",
                    "pause",
                    "resume",
                }
            ):
                result = self.execute(
                    api.control(
                        parts[1],
                        parts[2],
                    )
                )

                self.json_response(
                    200,
                    result,
                )
                return

            self.json_response(
                404,
                {"error": "unknown endpoint"},
            )

        except Exception as exc:
            self.json_response(
                400,
                {
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    )
                },
            )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--port",
        type=int,
        default=18765,
    )
    parser.add_argument(
        "--model",
        required=True,
    )
    parser.add_argument(
        "--endpoint",
        required=True,
    )
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
        [
            {
                "id": args.provider_id,
                "model": args.model,
                "endpoint": args.endpoint,
                "credential_variable":
                    args.credential_variable,
            }
        ],
        require_credentials=True,
    )

    service = iteration_service(
        journal_directory=args.journal,
        providers=providers,
    )

    app = application(service)

    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        handler,
    )

    server.application = app

    try:
        server.serve_forever()
    finally:
        server.server_close()
        app.close()


if __name__ == "__main__":
    main()
