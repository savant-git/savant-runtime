#!/usr/bin/env python3

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
from pathlib import Path
import posixpath
from urllib.parse import urlsplit

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)


schema = (
    "savant://runtime/palaver/"
    "production-frontend-server/1.0.0"
)

owner = "exile:palaver"
authority_effect = "none"

palaver_root = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/palaver"
)

dist_root = (
    palaver_root
    / "apps"
    / "webui-nextgen"
    / "dist"
)

backend_host = "127.0.0.1"
backend_port = 8787

hop_by_hop_headers = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _safe_static_path(
    request_path: str,
) -> Path | None:
    raw = urlsplit(
        request_path
    ).path

    normalized = posixpath.normpath(
        raw
    ).lstrip("/")

    candidate = (
        dist_root
        / normalized
    ).resolve()

    root = dist_root.resolve()

    try:
        candidate.relative_to(
            root
        )
    except ValueError:
        return None

    return candidate


class palaver_frontend_handler(
    BaseHTTPRequestHandler
):
    server_version = (
        "palaver-production-frontend/1.0"
    )

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        return

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str,
        cache_control: str,
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
                len(
                    body
                )
            ),
        )

        self.send_header(
            "Cache-Control",
            cache_control,
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "Referrer-Policy",
            "same-origin",
        )

        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(
                body
            )

    def _send_json(
        self,
        status: int,
        payload: dict,
    ) -> None:
        body = json.dumps(
            payload,
            separators=(
                ",",
                ":",
            ),
            sort_keys=True,
        ).encode(
            "utf-8"
        )

        self._send_bytes(
            status,
            body,
            content_type=(
                "application/json; charset=utf-8"
            ),
            cache_control="no-store",
        )

    def _health(
        self,
    ) -> None:
        self._send_json(
            200,
            {
                "ok": True,
                "schema": schema,
                "owner": owner,
                "dist_present":
                    dist_root.is_dir(),
                "backend":
                    f"{backend_host}:{backend_port}",
                "authority_effect":
                    authority_effect,
            },
        )

    def _proxy(
        self,
    ) -> None:
        parsed = urlsplit(
            self.path
        )

        target = parsed.path

        if parsed.query:
            target += (
                "?"
                + parsed.query
            )

        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
            or "0"
        )

        body = (
            self.rfile.read(
                length
            )
            if length > 0
            else None
        )

        forwarded_headers: dict[
            str,
            str,
        ] = {}

        for key, value in self.headers.items():
            low = key.lower()

            if low in hop_by_hop_headers:
                continue

            if low in {
                "host",
                "content-length",
            }:
                continue

            forwarded_headers[
                key
            ] = value

        forwarded_headers[
            "Host"
        ] = (
            f"{backend_host}:"
            f"{backend_port}"
        )

        forwarded_headers[
            "X-Forwarded-Host"
        ] = self.headers.get(
            "Host",
            "",
        )

        forwarded_headers[
            "X-Forwarded-Proto"
        ] = self.headers.get(
            "X-Forwarded-Proto",
            "http",
        )

        forwarded_headers[
            "X-Forwarded-For"
        ] = self.client_address[
            0
        ]

        connection = (
            http.client.HTTPConnection(
                backend_host,
                backend_port,
                timeout=120,
            )
        )

        try:
            connection.request(
                self.command,
                target,
                body=body,
                headers=forwarded_headers,
            )

            response = (
                connection.getresponse()
            )

            response_body = (
                response.read()
            )

            self.send_response(
                response.status,
                response.reason,
            )

            for key, value in (
                response.getheaders()
            ):
                low = key.lower()

                if (
                    low
                    in hop_by_hop_headers
                    or low
                    == "content-length"
                ):
                    continue

                self.send_header(
                    key,
                    value,
                )

            self.send_header(
                "Content-Length",
                str(
                    len(
                        response_body
                    )
                ),
            )

            self.end_headers()

            if self.command != "HEAD":
                self.wfile.write(
                    response_body
                )

        except Exception as exc:
            self._send_json(
                502,
                {
                    "ok": False,
                    "error":
                        "palaver_backend_unavailable",
                    "diagnostic":
                        str(
                            exc
                        ),
                    "authority_effect":
                        authority_effect,
                },
            )

        finally:
            connection.close()

    def _static(
        self,
    ) -> None:
        parsed = urlsplit(
            self.path
        )

        if parsed.path in {
            "/__palaver_frontend_health",
        }:
            self._health()
            return

        candidate = _safe_static_path(
            self.path
        )

        if (
            candidate is not None
            and candidate.is_file()
        ):
            target = candidate
        else:
            target = (
                dist_root
                / "index.html"
            )

        if not target.is_file():
            self._send_json(
                503,
                {
                    "ok": False,
                    "error":
                        "palaver_frontend_build_missing",
                    "dist_root":
                        str(
                            dist_root
                        ),
                    "authority_effect":
                        authority_effect,
                },
            )
            return

        body = target.read_bytes()

        guessed, _ = (
            mimetypes.guess_type(
                str(
                    target
                )
            )
        )

        content_type = (
            guessed
            or "application/octet-stream"
        )

        if content_type.startswith(
            "text/"
        ):
            content_type += (
                "; charset=utf-8"
            )

        immutable = (
            "/assets/"
            in str(
                target
            )
        )

        self._send_bytes(
            200,
            body,
            content_type=content_type,
            cache_control=(
                "public, max-age=31536000, immutable"
                if immutable
                else "no-cache"
            ),
        )

    def _dispatch(
        self,
    ) -> None:
        path = urlsplit(
            self.path
        ).path

        if (
            path == "/api"
            or path.startswith(
                "/api/"
            )
        ):
            self._proxy()
            return

        if self.command not in {
            "GET",
            "HEAD",
        }:
            self._send_json(
                405,
                {
                    "ok": False,
                    "error":
                        "method_not_allowed",
                    "authority_effect":
                        authority_effect,
                },
            )
            return

        self._static()

    def do_GET(
        self,
    ) -> None:
        self._dispatch()

    def do_HEAD(
        self,
    ) -> None:
        self._dispatch()

    def do_POST(
        self,
    ) -> None:
        self._dispatch()

    def do_PUT(
        self,
    ) -> None:
        self._dispatch()

    def do_PATCH(
        self,
    ) -> None:
        self._dispatch()

    def do_DELETE(
        self,
    ) -> None:
        self._dispatch()

    def do_OPTIONS(
        self,
    ) -> None:
        self._dispatch()


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        default="0.0.0.0",
    )

    parser.add_argument(
        "--port",
        default=5173,
        type=int,
    )

    args = parser.parse_args()

    if not dist_root.is_dir():
        raise RuntimeError(
            "Palaver production build "
            f"is missing: {dist_root}"
        )

    server = ThreadingHTTPServer(
        (
            args.host,
            args.port,
        ),
        palaver_frontend_handler,
    )

    print(
        "Palaver frontend running: "
        f"http://{args.host}:{args.port}"
    )

    server.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
