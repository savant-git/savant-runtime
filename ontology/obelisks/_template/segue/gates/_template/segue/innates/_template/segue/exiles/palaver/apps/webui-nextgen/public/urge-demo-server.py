#!/usr/bin/env python3
"""Allowlisted, execution-disabled portable Urge showcase."""

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
FILES = {
    "/": "urge-demo.html",
    "/urge-demo.html": "urge-demo.html",
    "/urge-demo-shades.js": "urge-demo-shades.js",
    "/urge-logo-studio-v7.html": "urge-logo-studio-v7.html",
}
LIMIT = 8 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "urge-showcase/2"

    def do_GET(self):
        self.serve_file(False)

    def do_HEAD(self):
        self.serve_file(True)

    def do_POST(self):
        self.send_error(405, "AI execution is disabled")

    def do_PUT(self):
        self.send_error(405)

    def do_PATCH(self):
        self.send_error(405)

    def do_DELETE(self):
        self.send_error(405)

    def serve_file(self, head_only):
        try:
            path = unquote(urlsplit(self.path).path, errors="strict")
        except UnicodeError:
            self.send_error(400)
            return

        if path == "/health":
            self.respond(
                b'{"ok":true,"mode":"static-showcase","ai":false}',
                "application/json; charset=utf-8",
                head_only,
            )
            return

        filename = FILES.get(path)

        if filename is None:
            self.send_error(404)
            return

        try:
            target = (ROOT / filename).resolve(strict=True)

            if target.parent != ROOT:
                self.send_error(403)
                return

            if not target.is_file():
                self.send_error(404)
                return

            if target.stat().st_size > LIMIT:
                self.send_error(413)
                return

            content = target.read_bytes()

        except FileNotFoundError:
            self.send_error(404)
            return
        except OSError:
            self.send_error(500)
            return

        content_type = mimetypes.guess_type(filename)[0]

        if filename.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif filename.endswith(".js"):
            content_type = "text/javascript; charset=utf-8"

        self.respond(
            content,
            content_type or "application/octet-stream",
            head_only,
        )

    def respond(self, content, content_type, head_only):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' data: blob:; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'self'",
        )
        self.end_headers()

        if not head_only:
            self.wfile.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18766)
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("Invalid port")

    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        Handler,
    )

    print(
        f"Urge showcase: http://127.0.0.1:{args.port}/",
        flush=True,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
