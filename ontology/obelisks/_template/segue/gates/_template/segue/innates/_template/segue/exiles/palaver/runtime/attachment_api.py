#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any


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


from attachment_limits import (
    max_attachment_bytes,
    max_attachment_mib,
)

from attachment_store import (
    get_attachment,
    store_attachment,
)
from .json_encoding import json_bytes as encode_json


schema = "savant.palaver.attachment-api.v1"
owner = "palaver"

default_host = "127.0.0.1"
default_port = 8791


class handler(
    BaseHTTPRequestHandler
):
    server_version = "palaver-attachment/1"

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
        data = encode_json(
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
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Length",
            str(
                len(
                    data
                )
            ),
        )

        self.end_headers()

        self.wfile.write(
            data
        )

    def do_GET(
        self,
    ) -> None:
        parsed = urllib.parse.urlparse(
            self.path
        )

        path = parsed.path.rstrip(
            "/"
        )

        if path in {
            "",
            "/health",
            "/api/attachment/health",
            "/api/attachment/limits",
        }:
            self.send_json(
                200,
                {
                    "ok": True,
                    "schema": schema,
                    "owner": owner,
                    "max_attachment_bytes": (
                        max_attachment_bytes
                    ),
                    "max_attachment_mib": (
                        max_attachment_mib
                    ),
                    "authority_effect": "none",
                },
            )

            return

        prefix = "/api/attachment/"

        if path.startswith(
            prefix
        ):
            identifier = path[
                len(
                    prefix
                ):
            ].strip()

            if not identifier:
                self.send_json(
                    400,
                    {
                        "ok": False,
                        "error": (
                            "attachment id missing"
                        ),
                    },
                )

                return

            try:
                record = get_attachment(
                    identifier
                )

                self.send_json(
                    200,
                    {
                        "ok": True,
                        "attachment": record,
                    },
                )

            except FileNotFoundError:
                self.send_json(
                    404,
                    {
                        "ok": False,
                        "error": (
                            "attachment not found"
                        ),
                    },
                )

            except Exception as exc:
                self.send_json(
                    500,
                    {
                        "ok": False,
                        "error": str(
                            exc
                        ),
                    },
                )

            return

        self.send_json(
            404,
            {
                "ok": False,
                "error": "not found",
            },
        )

    def do_POST(
        self,
    ) -> None:
        parsed = urllib.parse.urlparse(
            self.path
        )

        path = parsed.path.rstrip(
            "/"
        )

        if path != "/api/attachment/upload":
            self.send_json(
                404,
                {
                    "ok": False,
                    "error": "not found",
                },
            )

            return

        try:
            length_text = (
                self.headers.get(
                    "Content-Length"
                )
                or "0"
            )

            length = int(
                length_text
            )

            if length < 0:
                raise ValueError(
                    "invalid content length"
                )

            if length > max_attachment_bytes:
                self.send_json(
                    413,
                    {
                        "ok": False,
                        "error": (
                            "attachment exceeds "
                            f"{max_attachment_mib} MiB limit"
                        ),
                        "max_attachment_bytes": (
                            max_attachment_bytes
                        ),
                    },
                )

                return

            filename_encoded = (
                self.headers.get(
                    "X-Palaver-Filename"
                )
                or ""
            )

            filename = urllib.parse.unquote(
                filename_encoded
            ).strip()

            if not filename:
                self.send_json(
                    400,
                    {
                        "ok": False,
                        "error": (
                            "X-Palaver-Filename "
                            "header required"
                        ),
                    },
                )

                return

            content_type = (
                self.headers.get(
                    "X-Palaver-Content-Type"
                )
                or self.headers.get(
                    "Content-Type"
                )
                or "application/octet-stream"
            )

            data = self.rfile.read(
                length
            )

            if len(
                data
            ) != length:
                raise RuntimeError(
                    "incomplete attachment body"
                )

            record = store_attachment(
                filename=filename,
                data=data,
                content_type=content_type,
                source="palaver-webui",
            )

            self.send_json(
                201,
                {
                    "ok": True,
                    "attachment": record,
                },
            )

        except ValueError as exc:
            self.send_json(
                400,
                {
                    "ok": False,
                    "error": str(
                        exc
                    ),
                },
            )

        except Exception as exc:
            self.send_json(
                500,
                {
                    "ok": False,
                    "error": str(
                        exc
                    ),
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

    try:
        server.serve_forever()

    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="palaver-attachment-api"
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
