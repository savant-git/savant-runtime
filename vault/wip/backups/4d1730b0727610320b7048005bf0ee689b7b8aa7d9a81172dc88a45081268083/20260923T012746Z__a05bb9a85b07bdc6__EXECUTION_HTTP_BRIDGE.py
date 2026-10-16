from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


SCHEMA = (
    "savant://runtime/exile-runtime/"
    "execution-http-bridge/1.0.0"
)

OWNER = "exile_runtime"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

CAPABILITY_PATH = (
    "/api/execution/dispatch"
)

HEALTH_PATH = (
    "/api/execution/health"
)


EXECUTION_DIR = (
    Path(__file__).resolve().parent
)

EXILE_RUNTIME_DIR = (
    EXECUTION_DIR.parent
)

EXILES_DIR = (
    EXILE_RUNTIME_DIR.parents[1]
)


if str(EXECUTION_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(EXECUTION_DIR),
    )


from EXECUTION_MANAGER import manager
from dispatcher.DISPATCHER import dispatcher


class execution_http_bridge_error(
    RuntimeError
):
    pass


def _json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
        sort_keys=True,
        default=str,
    ).encode(
        "utf-8"
    )


def _send_json(
    request_handler: BaseHTTPRequestHandler,
    payload: Mapping[str, Any],
    status: int = 200,
) -> None:
    body = _json_bytes(
        payload
    )

    request_handler.send_response(
        status
    )

    request_handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8",
    )

    request_handler.send_header(
        "Content-Length",
        str(len(body)),
    )

    request_handler.send_header(
        "Cache-Control",
        "no-store",
    )

    request_handler.send_header(
        "X-Content-Type-Options",
        "nosniff",
    )

    request_handler.end_headers()

    request_handler.wfile.write(
        body
    )


def _read_json(
    request_handler: BaseHTTPRequestHandler,
) -> dict[str, Any]:
    raw_length = (
        request_handler.headers.get(
            "Content-Length",
            "0",
        )
    )

    try:
        length = int(
            raw_length
        )
    except ValueError as exc:
        raise execution_http_bridge_error(
            "invalid content length"
        ) from exc

    if length <= 0:
        raise execution_http_bridge_error(
            "request body is required"
        )

    if length > 1_048_576:
        raise execution_http_bridge_error(
            "request body exceeds 1 MiB"
        )

    raw = request_handler.rfile.read(
        length
    )

    try:
        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise execution_http_bridge_error(
            "request body must be valid JSON"
        ) from exc

    if not isinstance(
        value,
        Mapping,
    ):
        raise execution_http_bridge_error(
            "request body must be an object"
        )

    return dict(
        value
    )


def register_builtin_capabilities(
) -> tuple[str, ...]:
    registered: list[str] = []

    urge_runtime = (
        EXILES_DIR
        / "urge"
        / "runtime"
    )

    if urge_runtime.is_dir():
        runtime_root = (
            EXILE_RUNTIME_DIR.parents[7]
        )

        runtime_root_text = str(
            runtime_root
        )

        if (
            runtime_root_text
            not in sys.path
        ):
            sys.path.insert(
                0,
                runtime_root_text,
            )

        from ontology.obelisks._template.segue.gates._template.segue.innates._template.segue.exiles.urge.runtime.execution_binding import (
            register as register_urge,
        )

        registered.append(
            register_urge(
                dispatcher
            )
        )

    return tuple(
        registered
    )


def dispatch_request(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    capability = str(
        request.get(
            "capability",
            "",
        )
    ).strip()

    if not capability:
        raise execution_http_bridge_error(
            "capability is required"
        )

    payload = request.get(
        "payload",
        {},
    )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise execution_http_bridge_error(
            "payload must be an object"
        )

    result = manager.dispatch(
        capability,
        dict(payload),
    )

    return {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "ok":
            True,
        "capability":
            capability,
        "result":
            result,
        "authority_effect":
            "none",
    }


class handler(
    BaseHTTPRequestHandler
):
    server_version = (
        "savant-execution/1.0"
    )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return None

    def do_GET(
        self,
    ) -> None:
        path = urlparse(
            self.path
        ).path

        if path != HEALTH_PATH:
            _send_json(
                self,
                {
                    "ok": False,
                    "error": "not found",
                },
                404,
            )
            return

        _send_json(
            self,
            {
                "schema":
                    SCHEMA,
                "owner":
                    OWNER,
                "ok":
                    True,
                "routes": {
                    "health":
                        HEALTH_PATH,
                    "dispatch":
                        CAPABILITY_PATH,
                },
                "capabilities":
                    sorted(
                        dispatcher.routes
                    ),
                "authority_effect":
                    "none",
            },
            200,
        )

    def do_POST(
        self,
    ) -> None:
        path = urlparse(
            self.path
        ).path

        if path != CAPABILITY_PATH:
            _send_json(
                self,
                {
                    "ok": False,
                    "error": "not found",
                },
                404,
            )
            return

        try:
            request = _read_json(
                self
            )

            response = dispatch_request(
                request
            )

        except KeyError as exc:
            _send_json(
                self,
                {
                    "schema":
                        SCHEMA,
                    "owner":
                        OWNER,
                    "ok":
                        False,
                    "error":
                        "unknown capability",
                    "detail":
                        str(exc),
                    "authority_effect":
                        "none",
                },
                404,
            )
            return

        except (
            execution_http_bridge_error,
            ValueError,
            TypeError,
        ) as exc:
            _send_json(
                self,
                {
                    "schema":
                        SCHEMA,
                    "owner":
                        OWNER,
                    "ok":
                        False,
                    "error":
                        str(exc),
                    "authority_effect":
                        "none",
                },
                400,
            )
            return

        except Exception as exc:
            _send_json(
                self,
                {
                    "schema":
                        SCHEMA,
                    "owner":
                        OWNER,
                    "ok":
                        False,
                    "error":
                        "capability execution failed",
                    "detail":
                        str(exc),
                    "authority_effect":
                        "none",
                },
                500,
            )
            return

        _send_json(
            self,
            response,
            200,
        )


def serve(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    registered = (
        register_builtin_capabilities()
    )

    server = ThreadingHTTPServer(
        (
            host,
            port,
        ),
        handler,
    )

    print(
        json.dumps(
            {
                "schema":
                    SCHEMA,
                "owner":
                    OWNER,
                "status":
                    "ready",
                "host":
                    host,
                "port":
                    port,
                "dispatch":
                    CAPABILITY_PATH,
                "health":
                    HEALTH_PATH,
                "capabilities":
                    list(registered),
                "authority_effect":
                    "none",
            },
            sort_keys=True,
        ),
        flush=True,
    )

    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="savant-execution-http"
    )

    parser.add_argument(
        "--host",
        default=os.getenv(
            "SAVANT_EXECUTION_HOST",
            DEFAULT_HOST,
        ),
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(
            os.getenv(
                "SAVANT_EXECUTION_PORT",
                str(DEFAULT_PORT),
            )
        ),
    )

    args = parser.parse_args()

    serve(
        host=args.host,
        port=args.port,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
