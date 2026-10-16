#!/usr/bin/env python3

from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


ROOT = Path("/root/savant-runtime")

FILAMENT_RUNTIME = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "filament"
    / "runtime"
)

COALESCE_PUBLIC = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "modus"
    / "segue"
    / "prodigals"
    / "coalesce"
    / "static"
    / "public"
)

if str(FILAMENT_RUNTIME) not in sys.path:
    sys.path.insert(
        0,
        str(FILAMENT_RUNTIME),
    )

from filament_projection import project


HOST = "127.0.0.1"
PORT = 8789

MAX_REQUEST_BYTES = 9 * 1024 * 1024


def json_bytes(
    value: Any,
) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


class CoalesceHandler(
    BaseHTTPRequestHandler
):
    server_version = (
        "Savant-Filament-Coalesce"
    )

    def send_json(
        self,
        status: int,
        value: Any,
    ) -> None:
        payload = json_bytes(
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
            "Content-Length",
            str(len(payload)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            payload
        )

    def send_file(
        self,
        path: Path,
    ) -> None:
        if not path.is_file():
            self.send_error(
                404,
                "Not Found",
            )

            return

        payload = path.read_bytes()

        content_type = (
            mimetypes.guess_type(
                path.name
            )[0]
            or "application/octet-stream"
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
            str(len(payload)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            payload
        )

    def read_json(
        self,
    ) -> dict[str, Any]:
        raw_length = self.headers.get(
            "Content-Length",
            "0",
        )

        try:
            length = int(
                raw_length
            )
        except ValueError as exc:
            raise ValueError(
                "invalid Content-Length"
            ) from exc

        if length < 0:
            raise ValueError(
                "invalid Content-Length"
            )

        if length > MAX_REQUEST_BYTES:
            raise ValueError(
                "request exceeds maximum size"
            )

        raw = self.rfile.read(
            length
        )

        if not raw:
            return {}

        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "request body must be an object"
            )

        return value

    def do_GET(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        path = unquote(
            parsed.path
        )

        if path == "/api/health":
            self.send_json(
                200,
                {
                    "ok": True,
                    "owner": (
                        "exile:filament"
                    ),
                    "source": (
                        "prodigal:modus:"
                        "coalesce"
                    ),
                    "projection": (
                        "coalesce"
                    ),
                },
            )

            return

        if path in (
            "",
            "/",
        ):
            target = (
                COALESCE_PUBLIC
                / "index.html"
            )

            self.send_file(
                target
            )

            return

        relative = path.lstrip(
            "/"
        )

        target = (
            COALESCE_PUBLIC
            / relative
        ).resolve()

        public_root = (
            COALESCE_PUBLIC.resolve()
        )

        try:
            target.relative_to(
                public_root
            )
        except ValueError:
            self.send_error(
                403,
                "Forbidden",
            )

            return

        self.send_file(
            target
        )

    def do_POST(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        if (
            parsed.path
            != "/api/coalesce/project"
        ):
            self.send_error(
                404,
                "Not Found",
            )

            return

        try:
            body = self.read_json()

            recipe = str(
                body.get(
                    "recipe",
                    "chronology-explorer",
                )
            )

            records = body.get(
                "records",
                [],
            )

            state = body.get(
                "state",
                {},
            )

            parameters = body.get(
                "parameters",
                {},
            )

            if not isinstance(
                records,
                list,
            ):
                raise ValueError(
                    "records must be an array"
                )

            if not isinstance(
                state,
                dict,
            ):
                raise ValueError(
                    "state must be an object"
                )

            if not isinstance(
                parameters,
                dict,
            ):
                raise ValueError(
                    "parameters must be an object"
                )

            result = project(
                "",
                view="coalesce",
                recipe=recipe,
                context={
                    "records": records,
                    "state": state,
                    "parameters": parameters,
                },
            )

        except (
            ValueError,
            TypeError,
            KeyError,
            json.JSONDecodeError,
        ) as exc:
            self.send_json(
                400,
                {
                    "ok": False,
                    "error": str(exc),
                },
            )

            return

        except Exception as exc:
            self.send_json(
                500,
                {
                    "ok": False,
                    "error": str(exc),
                },
            )

            return

        self.send_json(
            200,
            result,
        )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        sys.stderr.write(
            "[coalesce] "
            + (
                format
                % args
            )
            + "\n"
        )


def main() -> int:
    if not COALESCE_PUBLIC.is_dir():
        raise RuntimeError(
            (
                "Coalesce public projection "
                f"missing: {COALESCE_PUBLIC}"
            )
        )

    server = ThreadingHTTPServer(
        (
            HOST,
            PORT,
        ),
        CoalesceHandler,
    )

    print(
        (
            "COALESCE UI: "
            f"http://{HOST}:{PORT}"
        )
    )

    print(
        (
            "COALESCE API: "
            f"http://{HOST}:{PORT}"
            "/api/coalesce/project"
        )
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
