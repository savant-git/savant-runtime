#!/usr/bin/env python3

from __future__ import annotations

import argparse
import http.server
import socketserver
from pathlib import Path


ROOT = Path("/root/savant-runtime/present").resolve()


class ObservatoryHandler(
    http.server.SimpleHTTPRequestHandler
):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            directory=str(ROOT),
            **kwargs,
        )

    def end_headers(self) -> None:
        self.send_header(
            "Cache-Control",
            "no-store",
        )
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
            "no-referrer",
        )
        super().end_headers()

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        return


class ReusableTCPServer(
    socketserver.ThreadingTCPServer
):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Serve the Savant Observatory."
        )
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8765,
    )

    args = parser.parse_args()

    with ReusableTCPServer(
        (args.host, args.port),
        ObservatoryHandler,
    ) as server:
        print(
            "Savant Observatory: "
            f"http://{args.host}:{args.port}/web/"
        )

        server.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
