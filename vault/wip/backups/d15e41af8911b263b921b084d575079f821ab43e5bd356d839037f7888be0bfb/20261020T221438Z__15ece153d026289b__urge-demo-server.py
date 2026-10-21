#!/usr/bin/env python3
"""Portable, static-only Urge demonstration server."""

import argparse
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent

PUBLIC_FILES = {
    "/": "urge-demo.html",
    "/urge-demo.html": "urge-demo.html",
    "/urge-demo-shades.js": "urge-demo-shades.js",
    "/urge-logo-studio-v7.html": "urge-logo-studio-v7.html",
    "/health": None,
}

MAX_FILE_BYTES = 8 * 1024 * 1024


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "savant-urge-showcase/1"

    def do_GET(self):
        self.serve(head_only=False)

    def do_HEAD(self):
        self.serve(head_only=True)

    def do_POST(self):
        self.send_error(405, "Static showcase: execution unavailable")

    def do_PUT(self):
        self.send_error(405, "Method not allowed")

    def do_DELETE(self):
        self.send_error(405, "Method not allowed")

    def serve(self, head_only):
        raw_path = urlsplit(self.path).path

        try:
            path = unquote(raw_path, errors="strict")
        except UnicodeError:
            self.send_error(400, "Invalid path")
            return

        if path not in PUBLIC_FILES:
            self.send_error(404, "Not found")
            return

        if path == "/health":
            payload = json.dumps({
                "ok": True,
                "service": "urge-showcase",
                "execution": "disabled",
            }).encode("utf-8")

            self.respond(
                200,
                payload,
                "application/json; charset=utf-8",
                head_only,
            )
            return

        filename = PUBLIC_FILES[path]
        target = ROOT / filename

        try:
            resolved = target.resolve(strict=True)

            if resolved.parent != ROOT.resolve():
                self.send_error(403, "Invalid file location")
                return

            if not resolved.is_file():
                self.send_error(404, "Not found")
                return

            stat = resolved.stat()

            if stat.st_size > MAX_FILE_BYTES:
                self.send_error(413, "File too large")
                return

            content = resolved.read_bytes()

        except FileNotFoundError:
            self.send_error(404, "File unavailable")
            return
        except OSError:
            self.send_error(500, "Unable to read file")
            return

        content_type = mimetypes.guess_type(filename)[0]

        if filename.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif filename.endswith(".js"):
            content_type = "text/javascript; charset=utf-8"
        elif not content_type:
            content_type = "application/octet-stream"

        self.respond(200, content, content_type, head_only)

    def respond(self, status, content, content_type, head_only):
        self.send_response(status)
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
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'self'",
        )
        self.end_headers()

        if not head_only:
            self.wfile.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18766)
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")

    if args.host not in ("127.0.0.1", "::1"):
        parser.error(
            "Only loopback binding is supported. "
            "Use an HTTPS reverse proxy for public deployment."
        )

    server = ThreadingHTTPServer(
        (args.host, args.port),
        DemoHandler,
    )

    print(
        f"urge showcase listening on "
        f"http://{args.host}:{args.port}/",
        flush=True,
    )

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
