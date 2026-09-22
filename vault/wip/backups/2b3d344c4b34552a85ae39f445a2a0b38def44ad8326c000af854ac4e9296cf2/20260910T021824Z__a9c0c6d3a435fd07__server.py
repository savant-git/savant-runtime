#!/usr/bin/env python3

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


schema = "savant.niche.atlas-server.v5"
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


def build_frontend() -> tuple[
    bytes,
    str,
]:
    required = (
        index_path,
        css_path,
        javascript_path,
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise AtlasServerError(
            "Atlas frontend source unavailable: "
            + ", ".join(
                missing
            )
        )

    html = index_path.read_text(
        encoding="utf-8"
    )

    css = css_path.read_text(
        encoding="utf-8"
    )

    javascript = javascript_path.read_text(
        encoding="utf-8"
    )

    if "</style" in css.lower():
        raise AtlasServerError(
            "Atlas stylesheet contains unsafe closing style token"
        )

    if "</script" in javascript.lower():
        raise AtlasServerError(
            "Atlas JavaScript contains unsafe closing script token"
        )

    stylesheet_pattern = re.compile(
        r"<link\b"
        r"(?=[^>]*\brel=[\"']stylesheet[\"'])"
        r"(?=[^>]*\bhref=[\"']"
        r"(?:/atlas)?/assets/atlas\.css[\"'])"
        r"[^>]*>",
        re.IGNORECASE,
    )

    javascript_pattern = re.compile(
        r"<script\b"
        r"(?=[^>]*\bsrc=[\"']"
        r"(?:/atlas)?/assets/atlas\.js[\"'])"
        r"[^>]*>\s*</script>",
        re.IGNORECASE,
    )

    html, stylesheet_count = (
        stylesheet_pattern.subn(
            "<style>\n"
            + css
            + "\n</style>",
            html,
            count=1,
        )
    )

    html, javascript_count = (
        javascript_pattern.subn(
            "<script>\n"
            + javascript
            + "\n</script>",
            html,
            count=1,
        )
    )

    if stylesheet_count != 1:
        raise AtlasServerError(
            "Atlas stylesheet reference was not uniquely bundleable"
        )

    if javascript_count != 1:
        raise AtlasServerError(
            "Atlas JavaScript reference was not uniquely bundleable"
        )

    css_hash = sha256_csp(
        css.encode(
            "utf-8"
        )
    )

    javascript_hash = sha256_csp(
        javascript.encode(
            "utf-8"
        )
    )

    csp = (
        "default-src 'self'; "
        f"script-src 'self' {javascript_hash}; "
        f"style-src 'self' {css_hash}; "
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
    server_version = "savant-atlas/5"

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
            str(
                len(body)
            ),
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
                "single-document-bundle",
            "host":
                host,
            "port":
                port,
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
    build_frontend()

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
