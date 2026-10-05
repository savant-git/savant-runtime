#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


palaver_runtime = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver/runtime"
)

runtime_path = str(
    palaver_runtime
)

if runtime_path not in sys.path:
    sys.path.insert(
        0,
        runtime_path,
    )


import plan_b_resilient

from attachment_context import (
    merge_context,
)
from .json_encoding import json_bytes


schema = (
    "savant.palaver.compat-gateway.v2"
)

default_host = "127.0.0.1"
default_port = 8787


def compatibility_response(
    result: dict[str, Any],
    attachment_projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = (
        result.get(
            "response"
        )
        or {}
    )

    text = str(
        response.get(
            "text"
        )
        or ""
    )

    payload = {
        "ok": True,
        "answer": text,
        "text": text,
        "response": text,
        "persona": (
            result.get(
                "persona"
            )
            or {}
        ),
        "lineage": (
            result.get(
                "lineage"
            )
            or {}
        ),
        "runtime": {
            "schema": schema,
            "owner": "palaver",
            "mode": (
                "plan_b_resilient"
            ),
            "authority_effect": "none",
        },
    }

    if (
        attachment_projection
        and attachment_projection.get(
            "count",
            0,
        )
    ):
        payload[
            "attachments"
        ] = {
            "schema": (
                attachment_projection.get(
                    "schema"
                )
            ),
            "count": (
                attachment_projection.get(
                    "count",
                    0,
                )
            ),
            "text_count": (
                attachment_projection.get(
                    "text_count",
                    0,
                )
            ),
            "items": (
                attachment_projection.get(
                    "attachments",
                    [],
                )
            ),
            "authority_effect": "none",
        }

    return payload


class handler(
    BaseHTTPRequestHandler
):
    server_version = (
        "palaver-compat/2"
    )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return

    def send_json(
        self,
        status: int,
        value: dict[str, Any],
    ) -> None:
        encoded = json_bytes(
            value
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(
                len(
                    encoded
                )
            ),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            encoded
        )

    def request_body(
        self,
    ) -> dict[str, Any]:
        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
            or 0
        )

        if length <= 0:
            return {}

        raw = self.rfile.read(
            length
        )

        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )

        if not isinstance(
            value,
            dict,
        ):
            raise RuntimeError(
                "request body must be object"
            )

        return value

    def do_GET(
        self,
    ) -> None:
        path = urlparse(
            self.path
        ).path.rstrip(
            "/"
        )

        if path in (
            "",
            "/health",
            "/api/health",
        ):
            result = (
                plan_b_resilient.health()
            )

            self.send_json(
                200,
                {
                    "ok": bool(
                        result.get(
                            "ready"
                        )
                    ),
                    "ready": bool(
                        result.get(
                            "ready"
                        )
                    ),
                    "schema": schema,
                    "owner": "palaver",
                    "mode": (
                        "plan_b_resilient"
                    ),
                    "runtime": result,
                    "attachments": {
                        "supported": True,
                        "projection": (
                            "palaver attachment context"
                        ),
                        "authority_effect": "none",
                    },
                    "authority_effect": "none",
                },
            )

            return

        self.send_json(
            404,
            {
                "ok": False,
                "error": "not_found",
                "schema": schema,
                "authority_effect": "none",
            },
        )

    def do_POST(
        self,
    ) -> None:
        path = urlparse(
            self.path
        ).path.rstrip(
            "/"
        )

        accepted_paths = (
            "/api/palaver",
            "/api/chat",
            "/api/message",
            "/infer",
            "/chat",
            "/message",
        )

        if path not in accepted_paths:
            self.send_json(
                404,
                {
                    "ok": False,
                    "error": "not_found",
                    "schema": schema,
                    "authority_effect": "none",
                },
            )

            return

        try:
            payload = (
                self.request_body()
            )

            message = str(
                payload.get(
                    "message"
                )
                or payload.get(
                    "text"
                )
                or payload.get(
                    "prompt"
                )
                or payload.get(
                    "query"
                )
                or ""
            ).strip()

            persona_id = str(
                payload.get(
                    "persona_id"
                )
                or payload.get(
                    "persona"
                )
                or "orobouros"
            ).strip()

            base_context = (
                payload.get(
                    "context"
                )
                or ""
            )

            attachments = (
                payload.get(
                    "attachments"
                )
                or []
            )

            if not isinstance(
                attachments,
                list,
            ):
                raise RuntimeError(
                    "attachments must be an array"
                )

            context, attachment_projection = (
                merge_context(
                    base_context,
                    attachments,
                )
            )

            result = (
                plan_b_resilient.infer(
                    message=message,
                    persona_id=persona_id,
                    context=context,
                )
            )

            if path.startswith(
                "/api/"
            ):
                result = (
                    compatibility_response(
                        result,
                        attachment_projection,
                    )
                )

            else:
                if (
                    attachment_projection.get(
                        "count",
                        0,
                    )
                ):
                    result = dict(
                        result
                    )

                    result[
                        "attachments"
                    ] = {
                        "schema": (
                            attachment_projection.get(
                                "schema"
                            )
                        ),
                        "count": (
                            attachment_projection.get(
                                "count",
                                0,
                            )
                        ),
                        "text_count": (
                            attachment_projection.get(
                                "text_count",
                                0,
                            )
                        ),
                        "items": (
                            attachment_projection.get(
                                "attachments",
                                [],
                            )
                        ),
                        "authority_effect": "none",
                    }

            self.send_json(
                200,
                result,
            )

        except Exception as exc:
            self.send_json(
                503,
                {
                    "ok": False,
                    "schema": schema,
                    "error": (
                        type(
                            exc
                        ).__name__
                    ),
                    "message": str(
                        exc
                    ),
                    "authority_effect": "none",
                },
            )


def serve(
    host: str,
    port: int,
) -> None:
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
                "ok": True,
                "schema": schema,
                "owner": "palaver",
                "mode": (
                    "plan_b_resilient"
                ),
                "host": host,
                "port": port,
                "health": (
                    f"http://{host}:"
                    f"{port}/api/health"
                ),
                "chat": (
                    f"http://{host}:"
                    f"{port}/api/palaver"
                ),
                "attachments": {
                    "accepted": True,
                    "context_projection": True,
                },
                "authority_effect": "none",
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    try:
        server.serve_forever()

    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="palaver-server"
    )

    parser.add_argument(
        "--host",
        default=default_host,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
    )

    args = parser.parse_args()

    try:
        serve(
            args.host,
            args.port,
        )

        return 0

    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
