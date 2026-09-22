#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys

from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any
from urllib.parse import (
    parse_qs,
    unquote,
    urlparse,
)


niche_root = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/"
    "segue/gates/_template/segue/"
    "innates/_template/segue/"
    "exiles/niche"
)

runtime_root = (
    niche_root
    / "runtime"
)

app_root = (
    niche_root
    / "apps/taskboard"
)

default_db = Path(
    "/root/savant-runtime/"
    "runtime/niche/tasks.sqlite3"
)

if str(
    runtime_root
) not in sys.path:
    sys.path.insert(
        0,
        str(
            runtime_root
        ),
    )


from living_task import (  # noqa: E402
    NicheTaskError,
)

from task_engine import (  # noqa: E402
    NicheTaskEngineError,
    engine,
)


max_body_bytes = (
    1024
    * 1024
)


task_route = re.compile(
    r"^/api/tasks/(?P<task_id>[^/]+)$"
)


action_route = re.compile(
    (
        r"^/api/tasks/"
        r"(?P<task_id>[^/]+)/"
        r"(?P<action>"
        r"transition|lease|release"
        r")$"
    )
)


class TaskboardServer(
    ThreadingHTTPServer
):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[
            str,
            int,
        ],
        db_path: Path,
    ) -> None:
        self.task_engine = engine(
            db_path
        )

        super().__init__(
            address,
            TaskboardHandler,
        )


class TaskboardHandler(
    BaseHTTPRequestHandler
):
    server_version = (
        "savant-niche-taskboard/1.0"
    )

    @property
    def task_engine(
        self,
    ):
        return self.server.task_engine  # type: ignore[attr-defined]

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return

    def _headers(
        self,
        status: int,
        content_type: str,
        length: int
        | None = None,
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
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "X-Frame-Options",
            "DENY",
        )

        self.send_header(
            "Referrer-Policy",
            "no-referrer",
        )

        self.send_header(
            "Content-Security-Policy",
            (
                "default-src 'self'; "
                "img-src 'self' data:; "
                "style-src 'self'; "
                "script-src 'self'; "
                "connect-src 'self'"
            ),
        )

        if length is not None:
            self.send_header(
                "Content-Length",
                str(
                    length
                ),
            )

        self.end_headers()

    def send_json(
        self,
        payload: Any,
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
            default=str,
        ).encode(
            "utf-8"
        )

        self._headers(
            int(
                status
            ),
            (
                "application/json; "
                "charset=utf-8"
            ),
            len(
                body
            ),
        )

        self.wfile.write(
            body
        )

    def send_error_json(
        self,
        status: int,
        message: str,
    ) -> None:
        self.send_json(
            {
                "ok":
                    False,

                "owner":
                    "exile:niche",

                "error":
                    message,

                "authority_effect":
                    "none",
            },
            status,
        )

    def read_json(
        self,
    ) -> dict[str, Any]:
        content_type = (
            self.headers.get(
                "Content-Type",
                "",
            )
        )

        if (
            "application/json"
            not in content_type
        ):
            raise NicheTaskEngineError(
                (
                    "Content-Type must be "
                    "application/json"
                )
            )

        raw_length = (
            self.headers.get(
                "Content-Length"
            )
        )

        if not raw_length:
            return {}

        length = int(
            raw_length
        )

        if (
            length < 0
            or length
            > max_body_bytes
        ):
            raise NicheTaskEngineError(
                (
                    "request body "
                    "exceeds limit"
                )
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
            raise NicheTaskEngineError(
                (
                    "request body must "
                    "be a JSON object"
                )
            )

        return value

    def do_GET(
        self,
    ) -> None:
        try:
            self._get()

        except (
            NicheTaskError,
            NicheTaskEngineError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            self.send_error_json(
                HTTPStatus.BAD_REQUEST,
                str(
                    exc
                ),
            )

        except Exception as exc:
            self.send_error_json(
                (
                    HTTPStatus
                    .INTERNAL_SERVER_ERROR
                ),
                (
                    type(
                        exc
                    ).__name__
                    + ": "
                    + str(
                        exc
                    )
                ),
            )

    def do_POST(
        self,
    ) -> None:
        try:
            self._post()

        except (
            NicheTaskError,
            NicheTaskEngineError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            self.send_error_json(
                HTTPStatus.BAD_REQUEST,
                str(
                    exc
                ),
            )

        except Exception as exc:
            self.send_error_json(
                (
                    HTTPStatus
                    .INTERNAL_SERVER_ERROR
                ),
                (
                    type(
                        exc
                    ).__name__
                    + ": "
                    + str(
                        exc
                    )
                ),
            )

    def do_PATCH(
        self,
    ) -> None:
        try:
            self._patch()

        except (
            NicheTaskError,
            NicheTaskEngineError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            self.send_error_json(
                HTTPStatus.BAD_REQUEST,
                str(
                    exc
                ),
            )

        except Exception as exc:
            self.send_error_json(
                (
                    HTTPStatus
                    .INTERNAL_SERVER_ERROR
                ),
                (
                    type(
                        exc
                    ).__name__
                    + ": "
                    + str(
                        exc
                    )
                ),
            )

    def _get(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        path = parsed.path

        query = parse_qs(
            parsed.query
        )

        if path == "/api/health":
            self.send_json(
                self.task_engine.health()
            )

            return

        if path == "/api/dashboard":
            self.send_json(
                self.task_engine.dashboard()
            )

            return

        if path == "/api/state":
            self.send_json(
                self.task_engine.state()
            )

            return

        if path == "/api/history":
            task_id = query.get(
                "task_id",
                [
                    None
                ],
            )[0]

            self.send_json(
                {
                    "events":
                        self.task_engine
                        .history(
                            task_id
                        )
                }
            )

            return

        if path == "/api/tasks":
            statuses = tuple(
                value
                for item
                in query.get(
                    "status",
                    [],
                )
                for value
                in item.split(
                    ","
                )
                if value
            )

            priorities = tuple(
                value
                for item
                in query.get(
                    "priority",
                    [],
                )
                for value
                in item.split(
                    ","
                )
                if value
            )

            include_terminal = (
                query.get(
                    "include_terminal",
                    [
                        "true"
                    ],
                )[0].lower()
                != "false"
            )

            self.send_json(
                {
                    "tasks":
                        self.task_engine.tasks(
                            query=
                                query.get(
                                    "q",
                                    [
                                        None
                                    ],
                                )[0],

                            statuses=
                                statuses,

                            priorities=
                                priorities,

                            owner_filter=
                                query.get(
                                    "owner",
                                    [
                                        None
                                    ],
                                )[0],

                            assignee=
                                query.get(
                                    "assignee",
                                    [
                                        None
                                    ],
                                )[0],

                            label=
                                query.get(
                                    "label",
                                    [
                                        None
                                    ],
                                )[0],

                            include_terminal=
                                include_terminal,
                        )
                }
            )

            return

        match = task_route.match(
            path
        )

        if match:
            task_id = unquote(
                match.group(
                    "task_id"
                )
            )

            self.send_json(
                self.task_engine
                .public_task(
                    task_id
                )
            )

            return

        if (
            path == "/"
            or path.startswith(
                "/assets/"
            )
            or path
            in {
                "/app.js",
                "/styles.css",
                "/favicon.svg",
            }
        ):
            self.serve_static(
                path
            )

            return

        self.send_error_json(
            HTTPStatus.NOT_FOUND,
            "not found",
        )

    def _post(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        path = parsed.path

        if path == "/api/tasks":
            self.send_json(
                self.task_engine.create(
                    self.read_json()
                ),
                HTTPStatus.CREATED,
            )

            return

        match = action_route.match(
            path
        )

        if match:
            task_id = unquote(
                match.group(
                    "task_id"
                )
            )

            action = match.group(
                "action"
            )

            body = self.read_json()

            if action == "transition":
                output = (
                    self.task_engine
                    .transition(
                        task_id,
                        str(
                            body.get(
                                "state"
                            )
                            or ""
                        ),
                        receipts=
                            body.get(
                                "receipts"
                            )
                            or (),
                        reason=
                            body.get(
                                "reason"
                            ),
                    )
                )

            elif action == "lease":
                output = (
                    self.task_engine
                    .lease(
                        task_id,
                        assignee=
                            str(
                                body.get(
                                    "assignee"
                                )
                                or ""
                            ),
                        minutes=
                            int(
                                body.get(
                                    "minutes"
                                )
                                or 60
                            ),
                    )
                )

            else:
                output = (
                    self.task_engine
                    .release(
                        task_id
                    )
                )

            self.send_json(
                output
            )

            return

        self.send_error_json(
            HTTPStatus.NOT_FOUND,
            "not found",
        )

    def _patch(
        self,
    ) -> None:
        parsed = urlparse(
            self.path
        )

        match = task_route.match(
            parsed.path
        )

        if not match:
            self.send_error_json(
                HTTPStatus.NOT_FOUND,
                "not found",
            )

            return

        task_id = unquote(
            match.group(
                "task_id"
            )
        )

        self.send_json(
            self.task_engine.amend(
                task_id,
                self.read_json(),
            )
        )

    def serve_static(
        self,
        request_path: str,
    ) -> None:
        mapping = {
            "/":
                app_root
                / "index.html",

            "/app.js":
                app_root
                / "app.js",

            "/styles.css":
                app_root
                / "styles.css",

            "/favicon.svg":
                app_root
                / "favicon.svg",
        }

        if request_path.startswith(
            "/assets/"
        ):
            candidate = (
                app_root
                / request_path
                .lstrip(
                    "/"
                )
            ).resolve()

            if (
                app_root.resolve()
                not in candidate.parents
            ):
                self.send_error_json(
                    HTTPStatus.NOT_FOUND,
                    "not found",
                )

                return

        else:
            candidate = mapping.get(
                request_path
            )

        if (
            candidate is None
            or not candidate.is_file()
        ):
            self.send_error_json(
                HTTPStatus.NOT_FOUND,
                "not found",
            )

            return

        body = (
            candidate.read_bytes()
        )

        content_type = (
            mimetypes.guess_type(
                candidate.name
            )[0]
            or (
                "application/"
                "octet-stream"
            )
        )

        if (
            content_type.startswith(
                "text/"
            )
            or content_type
            in {
                "application/javascript",
                "image/svg+xml",
            }
        ):
            content_type += (
                "; charset=utf-8"
            )

        self._headers(
            HTTPStatus.OK,
            content_type,
            len(
                body
            ),
        )

        self.wfile.write(
            body
        )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=
            "Niche taskboard local UI"
    )

    parser.add_argument(
        "--bind",
        default=
            "127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=
            8787,
    )

    parser.add_argument(
        "--db",
        default=
            str(
                default_db
            ),
    )

    return parser


def main(
) -> int:
    args = (
        build_parser()
        .parse_args()
    )

    server = TaskboardServer(
        (
            args.bind,
            args.port,
        ),
        Path(
            args.db
        ),
    )

    print(
        json.dumps(
            {
                "owner":
                    "exile:niche",

                "taskboard":
                    (
                        "http://"
                        + args.bind
                        + ":"
                        + str(
                            args.port
                        )
                        + "/"
                    ),

                "database":
                    str(
                        Path(
                            args.db
                        ).resolve()
                    ),

                "authority_effect":
                    "none",
            },
            sort_keys=True,
        )
    )

    try:
        server.serve_forever(
            poll_interval=
                0.25
        )

    except KeyboardInterrupt:
        pass

    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
