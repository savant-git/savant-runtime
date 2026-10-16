#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import (
    unquote,
    urlparse,
)


app_root = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas"
)

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


schema_version = "savant.niche.atlas-server.v1"
authority_effect = "none"
owner = "exile:niche"

assets_root = (
    app_root
    / "assets"
)

index_path = (
    assets_root
    / "index.html"
)


class AtlasHandler(
    BaseHTTPRequestHandler
):
    server_version = (
        "savant-atlas/1"
    )

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        return

    def send_json(
        self,
        value,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        substance = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(substance)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "Referrer-Policy",
            "no-referrer",
        )

        self.send_header(
            "X-Savant-Authority-Effect",
            authority_effect,
        )

        self.send_header(
            "X-Savant-Mutation-Authority",
            "false",
        )

        self.end_headers()

        self.wfile.write(
            substance
        )

    def send_file(
        self,
        path: Path,
    ) -> None:
        try:
            resolved = path.resolve(
                strict=True
            )
        except FileNotFoundError:
            self.send_error(
                HTTPStatus.NOT_FOUND
            )
            return

        try:
            resolved.relative_to(
                assets_root.resolve()
            )
        except ValueError:
            self.send_error(
                HTTPStatus.FORBIDDEN
            )
            return

        if not resolved.is_file():
            self.send_error(
                HTTPStatus.NOT_FOUND
            )
            return

        substance = resolved.read_bytes()

        content_type = (
            mimetypes.guess_type(
                resolved.name
            )[0]
            or "application/octet-stream"
        )

        self.send_response(
            HTTPStatus.OK
        )

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(len(substance)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "Referrer-Policy",
            "no-referrer",
        )

        self.send_header(
            "Content-Security-Policy",
            (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: blob:; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'none';"
            ),
        )

        self.end_headers()

        self.wfile.write(
            substance
        )

    def reject_mutation(
        self,
    ) -> None:
        self.send_json(
            {
                "schema":
                    schema_version,
                "authority_effect":
                    authority_effect,
                "status":
                    "method-not-allowed",
                "mutation_authority":
                    False,
            },
            HTTPStatus.METHOD_NOT_ALLOWED,
        )

    do_POST = reject_mutation
    do_PUT = reject_mutation
    do_PATCH = reject_mutation
    do_DELETE = reject_mutation

    def do_GET(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        path = parsed.path

        try:
            if path == "/api/health":
                self.send_json(
                    {
                        "schema":
                            schema_version,
                        "authority_effect":
                            authority_effect,
                        "status":
                            "ok",
                        "owner":
                            owner,
                        "projection_only":
                            True,
                        "mutation_authority":
                            False,
                    }
                )
                return

            if path == "/api/atlas":
                self.send_json(
                    atlas_projection()
                )
                return

            if path == "/api/atlas/summary":
                self.send_json(
                    summary_projection()
                )
                return

            if path == "/api/atlas/self-check":
                self.send_json(
                    self_check()
                )
                return

            if (
                path == "/"
                or path
                == "/index.html"
            ):
                if not index_path.is_file():
                    self.send_json(
                        {
                            "schema":
                                schema_version,
                            "authority_effect":
                                authority_effect,
                            "status":
                                "frontend-not-installed",
                            "projection_only":
                                True,
                            "mutation_authority":
                                False,
                            "api":
                                "/api/atlas",
                        },
                        HTTPStatus.SERVICE_UNAVAILABLE,
                    )
                    return

                self.send_file(
                    index_path
                )
                return

            if path.startswith(
                "/assets/"
            ):
                relative = unquote(
                    path[
                        len(
                            "/assets/"
                        ):
                    ]
                )

                self.send_file(
                    assets_root
                    / relative
                )
                return

            self.send_error(
                HTTPStatus.NOT_FOUND
            )

        except Exception as exc:
            self.send_json(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "mutation_authority":
                        False,
                    "error":
                        str(exc),
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        default=8766,
        type=int,
    )

    parser.add_argument(
        "--self-check",
        action="store_true",
    )

    arguments = parser.parse_args()

    if arguments.self_check:
        print(
            json.dumps(
                self_check(),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    server = ThreadingHTTPServer(
        (
            arguments.host,
            arguments.port,
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
