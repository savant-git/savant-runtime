#!/usr/bin/env python3

from __future__ import annotations

import base64
import hashlib
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


schema = "savant.niche.atlas-server.v6"
authority_effect = "none"
projection_only = True
mutation_authority = False

host = "127.0.0.1"
port = 8776

app_root = Path(__file__).resolve().parent
assets_root = app_root / "assets"

index_path = assets_root / "index.html"
css_path = assets_root / "atlas.css"
javascript_path = assets_root / "atlas.js"

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


class AtlasServerError(RuntimeError):
    pass


def sha256_csp(
    substance: bytes,
) -> str:
    digest = hashlib.sha256(
        substance
    ).digest()

    encoded = base64.b64encode(
        digest
    ).decode(
        "ascii"
    )

    return f"'sha256-{encoded}'"


def require_frontend_sources() -> None:
    missing = [
        str(path)
        for path in (
            index_path,
            css_path,
            javascript_path,
        )
        if not path.is_file()
    ]

    if missing:
        raise AtlasServerError(
            "Atlas frontend source unavailable: "
            + ", ".join(missing)
        )


def build_frontend() -> tuple[
    bytes,
    str,
]:
    require_frontend_sources()

    html = index_path.read_text(
        encoding="utf-8",
    )

    css = css_path.read_text(
        encoding="utf-8",
    )

    javascript = javascript_path.read_text(
        encoding="utf-8",
    )

    css_bytes = css.encode(
        "utf-8"
    )

    javascript_bytes = javascript.encode(
        "utf-8"
    )

    style_block = (
        "\n<style data-savant-atlas-inline=\"true\">\n"
        + css
        + "\n</style>\n"
    )

    script_block = (
        "\n<script data-savant-atlas-inline=\"true\">\n"
        + javascript
        + "\n</script>\n"
    )

    lower_html = html.lower()

    head_index = lower_html.rfind(
        "</head>"
    )

    body_index = lower_html.rfind(
        "</body>"
    )

    if head_index >= 0:
        html = (
            html[:head_index]
            + style_block
            + html[head_index:]
        )
    else:
        html = (
            style_block
            + html
        )

    lower_html = html.lower()

    body_index = lower_html.rfind(
        "</body>"
    )

    if body_index >= 0:
        html = (
            html[:body_index]
            + script_block
            + html[body_index:]
        )
    else:
        html = (
            html
            + script_block
        )

    csp = (
        "default-src 'self'; "
        f"script-src 'self' {sha256_csp(javascript_bytes)}; "
        f"style-src 'self' {sha256_csp(css_bytes)}; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'self'"
    )

    return (
        html.encode(
            "utf-8"
        ),
        csp,
    )


class AtlasHandler(
    BaseHTTPRequestHandler
):
    server_version = "savant-atlas/6"

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        return

    def _security_headers(
        self,
        csp: str | None = None,
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
            csp
            or (
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
        csp: str | None = None,
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
            str(len(body)),
        )

        self._security_headers(
            csp
        )

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
            "delivery":
                "inline-composed",
            "host":
                host,
            "port":
                port,
            "status":
                "ok",
        }

    def _serve_frontend(
        self,
    ) -> None:
        body, csp = build_frontend()

        self._send_bytes(
            body,
            "text/html; charset=utf-8",
            HTTPStatus.OK,
            csp,
        )

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
            self._serve_frontend()
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
                str(exc),
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
    require_frontend_sources()

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
