#!/usr/bin/env python3

from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


schema = "savant.niche.atlas-server.v3"
authority_effect = "none"
projection_only = True
mutation_authority = False

host = "127.0.0.1"
port = 8766

app_root = Path(__file__).resolve().parent
assets_root = app_root / "assets"

if str(app_root) not in sys.path:
    sys.path.insert(
        0,
        str(app_root),
    )

from atlas_projection import (  # noqa: E402
    atlas_projection,
    self_check,
    summary_projection,
)


class AtlasHandler(
    BaseHTTPRequestHandler
):
    server_version = "savant-atlas/3"

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        return

    def _security_headers(
        self,
    ) -> None:
        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "X-Frame-Options",
            "SAMEORIGIN",
        )

        self.send_header(
            "Referrer-Policy",
            "same-origin",
        )

        self.send_header(
            "Content-Security-Policy",
            (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'self'"
            ),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

    def _send_bytes(
        self,
        body: bytes,
        content_type: str,
        status: int = HTTPStatus.OK,
    ) -> None:
        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(
                len(body)
            ),
        )

        self._security_headers()

        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(
                body
            )

    def _send_json(
        self,
        payload,
        status: int = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )

        self._send_bytes(
            body,
            "application/json; charset=utf-8",
            status,
        )

    def _send_error_json(
        self,
        status: int,
        message: str,
    ) -> None:
        self._send_json(
            {
                "schema":
                    schema,
                "authority_effect":
                    authority_effect,
                "projection_only":
                    projection_only,
                "mutation_authority":
                    mutation_authority,
                "status":
                    "failed",
                "error":
                    message,
            },
            status,
        )

    def _normalized_path(
        self,
    ) -> str:
        path = urlsplit(
            self.path
        ).path

        if path == "/atlas":
            return "/"

        if path.startswith(
            "/atlas/"
        ):
            stripped = path[
                len("/atlas"):
            ]

            return (
                stripped
                if stripped
                else "/"
            )

        return path

    def _serve_file(
        self,
        path: Path,
    ) -> None:
        try:
            resolved = path.resolve(
                strict=True
            )

        except FileNotFoundError:
            self._send_error_json(
                HTTPStatus.NOT_FOUND,
                "resource not found",
            )

            return

        try:
            resolved.relative_to(
                assets_root.resolve()
            )

        except ValueError:
            self._send_error_json(
                HTTPStatus.FORBIDDEN,
                "resource outside Atlas assets",
            )

            return

        if not resolved.is_file():
            self._send_error_json(
                HTTPStatus.NOT_FOUND,
                "resource not found",
            )

            return

        content_type, _ = mimetypes.guess_type(
            resolved.name
        )

        if resolved.suffix == ".css":
            content_type = (
                "text/css; charset=utf-8"
            )

        elif resolved.suffix == ".js":
            content_type = (
                "application/javascript; charset=utf-8"
            )

        elif resolved.suffix == ".html":
            content_type = (
                "text/html; charset=utf-8"
            )

        elif not content_type:
            content_type = (
                "application/octet-stream"
            )

        self._send_bytes(
            resolved.read_bytes(),
            content_type,
        )

    def _serve_index(
        self,
    ) -> None:
        index_path = (
            assets_root
            / "index.html"
        )

        if not index_path.is_file():
            self._send_error_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "Atlas frontend is not installed",
            )

            return

        self._send_bytes(
            index_path.read_bytes(),
            "text/html; charset=utf-8",
        )

    def _serve_asset(
        self,
        request_path: str,
    ) -> None:
        prefix = "/assets/"

        relative = request_path[
            len(prefix):
        ]

        if (
            not relative
            or relative.startswith("/")
        ):
            self._send_error_json(
                HTTPStatus.NOT_FOUND,
                "resource not found",
            )

            return

        target = (
            assets_root
            / relative
        )

        self._serve_file(
            target
        )

    def _health(
        self,
    ) -> dict:
        return {
            "schema":
                schema,
            "authority_effect":
                authority_effect,
            "projection_only":
                projection_only,
            "mutation_authority":
                mutation_authority,
            "owner":
                "exile:niche",
            "surface":
                "atlas",
            "status":
                "ok",
        }

    def _dispatch_get(
        self,
    ) -> None:
        path = (
            self._normalized_path()
        )

        if path in (
            "",
            "/",
            "/index.html",
        ):
            self._serve_index()
            return

        if path.startswith(
            "/assets/"
        ):
            self._serve_asset(
                path
            )
            return

        if path in (
            "/api/health",
            "/api/atlas/health",
        ):
            self._send_json(
                self._health()
            )
            return

        if path == "/api/atlas":
            self._send_json(
                atlas_projection()
            )
            return

        if path == "/api/atlas/summary":
            self._send_json(
                summary_projection()
            )
            return

        if path == "/api/atlas/self-check":
            self._send_json(
                self_check()
            )
            return

        self._send_error_json(
            HTTPStatus.NOT_FOUND,
            "resource not found",
        )

    def do_GET(
        self,
    ) -> None:
        try:
            self._dispatch_get()

        except Exception as exc:
            self._send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                str(
                    exc
                ),
            )

    def do_HEAD(
        self,
    ) -> None:
        self.do_GET()

    def _reject_mutation(
        self,
    ) -> None:
        self._send_json(
            {
                "schema":
                    schema,
                "authority_effect":
                    authority_effect,
                "projection_only":
                    projection_only,
                "mutation_authority":
                    mutation_authority,
                "status":
                    "rejected",
                "error":
                    "Atlas is projection-only",
            },
            HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def do_POST(
        self,
    ) -> None:
        self._reject_mutation()

    def do_PUT(
        self,
    ) -> None:
        self._reject_mutation()

    def do_PATCH(
        self,
    ) -> None:
        self._reject_mutation()

    def do_DELETE(
        self,
    ) -> None:
        self._reject_mutation()


def main() -> int:
    server = ThreadingHTTPServer(
        (
            host,
            port,
        ),
        AtlasHandler,
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        pass

    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
