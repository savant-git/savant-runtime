
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


class urge_live_application:
    def __init__(self, service):
        self.service = service
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()

        def run():
            asyncio.set_event_loop(self.loop)
            self.ready.set()
            self.loop.run_forever()

        self.thread = threading.Thread(
            target=run,
            daemon=True,
        )
        self.thread.start()
        self.ready.wait()

    def call(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(
            coroutine,
            self.loop,
        )
        return future.result(timeout=30)

    def close(self):
        self.loop.call_soon_threadsafe(
            self.loop.stop
        )
        self.thread.join(timeout=5)


class urge_live_handler(BaseHTTPRequestHandler):
    server_version = "savant-urge-live/1"

    def send_json(self, status, value):
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
            "Content-Length",
            str(len(encoded)),
        )
        self.end_headers()
        self.wfile.write(encoded)

    def authorized(self):
        host = self.headers.get("Host", "")
        allowed = {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }
        return host in allowed

    def body(self):
        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )
        except ValueError as exc:
            raise ValueError(
                "invalid content length"
            ) from exc

        if not 1 <= length <= 131072:
            raise ValueError(
                "invalid request length"
            )

        value = json.loads(
            self.rfile.read(length)
        )

        if not isinstance(value, dict):
            raise ValueError(
                "request must be an object"
            )

        return value

    def do_GET(self):
        if not self.authorized():
            self.send_json(
                403,
                {"error": "invalid host"},
            )
            return

        path = urlsplit(self.path).path

        if path == "/health":
            self.send_json(
                200,
                {
                    "ok": True,
                    "engine": "urge",
                    "orchestration": "opus",
                    "persona_binding": "envoy",
                    "execution": "live",
                },
            )
            return

        if path == "/":
            page = runtime / "urge_live.html"

            if not page.is_file():
                self.send_json(
                    404,
                    {"error": "interface unavailable"},
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
            self.send_json(
                404,
                {"error": "unknown endpoint"},
            )
            return

        identity = parts[1]

        try:
            application = self.server.application
            service = application.service

            if len(parts) == 2:
                result = application.call(
                    service.status(identity)
                )
            elif parts[2] == "history":
                result = application.call(
                    service.history(identity)
                )
            else:
                self.send_json(
                    404,
                    {"error": "unknown endpoint"},
                )
                return

            self.send_json(200, result)

        except Exception as exc:
            self.send_json(
                400,
                {
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    )
                },
            )

    def do_POST(self):
        if not self.authorized():
            self.send_json(
                403,
                {"error": "invalid host"},
            )
            return

        allowed_origins = {
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        }

        origin = self.headers.get("Origin")

        if origin and origin not in allowed_origins:
            self.send_json(
                403,
                {"error": "invalid origin"},
            )
            return

        try:
            body = self.body()
            path = urlsplit(self.path).path
            application = self.server.application
            service = application.service

            if path == "/sessions":
                goal = body.get("goal")

                if (
                    not isinstance(goal, str)
                    or not goal.strip()
                    or len(goal) > 16000
                ):
                    raise ValueError(
                        "invalid session goal"
                    )

                settings = body.get(
                    "settings",
                    {},
                )

                if not isinstance(settings, dict):
                    raise ValueError(
                        "settings must be an object"
                    )

                limit = body.get(
                    "iteration_limit",
                    3,
                )

                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 20
                ):
                    raise ValueError(
                        "iteration limit must be 1 through 20"
                    )

                identity = uuid.uuid4().hex

                result = application.call(
                    service.create_session(
                        session_id=identity,
                        goal=goal,
                        iteration_limit=limit,
                        interval_seconds=body.get(
                            "interval_seconds",
                            1.0,
                        ),
                        settings=settings,
                    )
                )

                self.send_json(201, result)
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
                operation = getattr(
                    service,
                    parts[2],
                )

                result = application.call(
                    operation(parts[1])
                )

                self.send_json(200, result)
                return

            self.send_json(
                404,
                {"error": "unknown endpoint"},
            )

        except Exception as exc:
            self.send_json(
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

    application = urge_live_application(
        service
    )

    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        urge_live_handler,
    )

    server.application = application

    try:
        server.serve_forever()
    finally:
        server.server_close()
        application.close()


if __name__ == "__main__":
    main()
