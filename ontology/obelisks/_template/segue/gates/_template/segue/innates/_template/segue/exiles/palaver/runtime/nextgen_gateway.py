#!/usr/bin/env python3

from __future__ import annotations

import json
import mimetypes
import os
import urllib.error
import urllib.request

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse


bind_host = "127.0.0.1"

bind_port = int(
    os.getenv(
        "PALAVER_NEXTGEN_PORT",
        "8789",
    )
)

palaver_backend = "http://127.0.0.1:8787"
terminal_backend = "http://127.0.0.1:8788"

dist_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver/"
    "apps/webui-nextgen/dist"
).resolve()

max_proxy_body = 8 * 1024 * 1024


class handler(BaseHTTPRequestHandler):
    server_version = "palaver-nextgen/1.1"

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        return

    def _proxy_target(
        self,
        path: str,
    ) -> str:
        if path.startswith(
            "/api/terminal/"
        ):
            return terminal_backend

        return palaver_backend

    def _send_payload(
        self,
        *,
        status: int,
        payload: bytes,
        content_type: str,
    ) -> None:
        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Length",
            str(
                len(payload)
            ),
        )

        self.end_headers()

        self.wfile.write(
            payload
        )

    def _send_json(
        self,
        payload: dict,
        *,
        status: int = 200,
    ) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )

        self._send_payload(
            status=status,
            payload=encoded,
            content_type=(
                "application/json; "
                "charset=utf-8"
            ),
        )

    def _proxy(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        target = (
            self._proxy_target(
                parsed.path
            )
            + self.path
        )

        body = None

        if self.command in {
            "POST",
            "PUT",
            "PATCH",
        }:
            try:
                length = int(
                    self.headers.get(
                        "Content-Length",
                        "0",
                    )
                )
            except ValueError:
                self._send_json(
                    {
                        "ok": False,
                        "error": (
                            "invalid content length"
                        ),
                        "gateway": True,
                    },
                    status=400,
                )
                return

            if (
                length < 0
                or length
                > max_proxy_body
            ):
                self._send_json(
                    {
                        "ok": False,
                        "error": (
                            "request too large"
                        ),
                        "gateway": True,
                    },
                    status=413,
                )
                return

            if length:
                body = self.rfile.read(
                    length
                )

        headers = {}

        for name in (
            "Content-Type",
            "Accept",
            "Authorization",
        ):
            value = self.headers.get(
                name
            )

            if value:
                headers[name] = value

        request = urllib.request.Request(
            target,
            data=body,
            headers=headers,
            method=self.command,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=310,
            ) as response:
                payload = response.read()

                content_type = (
                    response.headers.get(
                        "Content-Type"
                    )
                    or (
                        "application/"
                        "octet-stream"
                    )
                )

                self._send_payload(
                    status=response.status,
                    payload=payload,
                    content_type=
                        content_type,
                )

        except urllib.error.HTTPError as exc:
            payload = exc.read()

            content_type = (
                exc.headers.get(
                    "Content-Type"
                )
                or (
                    "application/json; "
                    "charset=utf-8"
                )
            )

            if not payload:
                payload = json.dumps(
                    {
                        "ok": False,
                        "error": (
                            f"upstream HTTP "
                            f"{exc.code}"
                        ),
                        "gateway": True,
                    },
                    separators=(
                        ",",
                        ":",
                    ),
                ).encode(
                    "utf-8"
                )

                content_type = (
                    "application/json; "
                    "charset=utf-8"
                )

            self._send_payload(
                status=exc.code,
                payload=payload,
                content_type=
                    content_type,
            )

        except urllib.error.URLError as exc:
            reason = getattr(
                exc,
                "reason",
                exc,
            )

            self._send_json(
                {
                    "ok": False,
                    "error": (
                        "gateway upstream "
                        f"unavailable: {reason}"
                    ),
                    "gateway": True,
                    "target": (
                        self._proxy_target(
                            parsed.path
                        )
                    ),
                },
                status=502,
            )

        except TimeoutError:
            self._send_json(
                {
                    "ok": False,
                    "error": (
                        "gateway upstream "
                        "timeout"
                    ),
                    "gateway": True,
                },
                status=504,
            )

        except Exception as exc:
            self._send_json(
                {
                    "ok": False,
                    "error": (
                        "gateway failure: "
                        f"{exc}"
                    ),
                    "gateway": True,
                },
                status=502,
            )

    def _static_path(
        self,
        request_path: str,
    ) -> Path | None:
        clean = request_path.lstrip(
            "/"
        )

        if not clean:
            clean = "index.html"

        candidate = (
            dist_root
            / clean
        ).resolve()

        try:
            candidate.relative_to(
                dist_root
            )
        except ValueError:
            return None

        if candidate.is_file():
            return candidate

        return None

    def _serve_file(
        self,
        path: Path,
    ) -> None:
        payload = path.read_bytes()

        content_type, _ = (
            mimetypes.guess_type(
                str(path)
            )
        )

        if not content_type:
            content_type = (
                "application/"
                "octet-stream"
            )

        if path.suffix in {
            ".js",
            ".mjs",
        }:
            content_type = (
                "text/javascript; "
                "charset=utf-8"
            )

        elif path.suffix == ".css":
            content_type = (
                "text/css; "
                "charset=utf-8"
            )

        elif path.suffix == ".html":
            content_type = (
                "text/html; "
                "charset=utf-8"
            )

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(
                len(payload)
            ),
        )

        if path.name == "index.html":
            self.send_header(
                "Cache-Control",
                "no-cache",
            )
        else:
            self.send_header(
                "Cache-Control",
                (
                    "public, "
                    "max-age=31536000, "
                    "immutable"
                ),
            )

        self.end_headers()

        self.wfile.write(
            payload
        )

    def do_GET(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        if parsed.path.startswith(
            "/api/"
        ):
            self._proxy()
            return

        target = self._static_path(
            parsed.path
        )

        if target is not None:
            self._serve_file(
                target
            )
            return

        index = (
            dist_root
            / "index.html"
        )

        if index.is_file():
            self._serve_file(
                index
            )
            return

        self.send_error(
            404,
            "nextgen build missing",
        )

    def do_POST(
        self,
    ) -> None:
        if self.path.startswith(
            "/api/"
        ):
            self._proxy()
            return

        self.send_error(
            404
        )

    def do_PUT(
        self,
    ) -> None:
        if self.path.startswith(
            "/api/"
        ):
            self._proxy()
            return

        self.send_error(
            404
        )

    def do_PATCH(
        self,
    ) -> None:
        if self.path.startswith(
            "/api/"
        ):
            self._proxy()
            return

        self.send_error(
            404
        )

    def do_DELETE(
        self,
    ) -> None:
        if self.path.startswith(
            "/api/"
        ):
            self._proxy()
            return

        self.send_error(
            404
        )

    def do_OPTIONS(
        self,
    ) -> None:
        if self.path.startswith(
            "/api/"
        ):
            self._proxy()
            return

        self.send_response(
            204
        )

        self.end_headers()


def main() -> None:
    if not (
        dist_root
        / "index.html"
    ).is_file():
        raise RuntimeError(
            (
                "Palaver nextgen build "
                "missing: "
            )
            + str(
                dist_root
            )
        )

    print(
        (
            "Palaver nextgen gateway: "
            f"http://{bind_host}:"
            f"{bind_port}"
        )
    )

    ThreadingHTTPServer(
        (
            bind_host,
            bind_port,
        ),
        handler,
    ).serve_forever()


if __name__ == "__main__":
    main()
