#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from masterplan_projection import identity_projection, masterplan_projection, summary_projection
from masterplan_index_projection import index_projection
from masterplan_lineage_projection import lineage_projection
from masterplan_projection_self_check import projection_snapshot

from atlas_adapter import (
    reject_atlas_mutation,
    try_handle_get as try_handle_atlas_get,
)



savant_root = Path(
    "/root/savant-runtime"
).resolve()

niche_root = (
    savant_root
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche"
)

runtime_root = niche_root / "runtime"
app_root = niche_root / "apps/taskboard"

default_db = (
    savant_root
    / "runtime/niche/tasks.sqlite3"
)

living_state_root = (
    savant_root
    / "runtime/living-state"
)

living_governance_root = (
    savant_root
    / "canon-system/projections/living"
)

living_fabric_root = (
    savant_root
    / "runtime/living-fabric"
)

living_sources = {
    "state": {
        "current":
            living_state_root
            / "current.json",

        "health":
            living_state_root
            / "health.json",
    },

    "governance": {
        "status":
            living_governance_root
            / "status.json",

        "snapshot":
            living_governance_root
            / "snapshot.json",

        "graph":
            living_governance_root
            / "graph.json",
    },

    "fabric": {
        "current":
            living_fabric_root
            / "current.json",

        "health":
            living_fabric_root
            / "health.json",

        "receipt":
            living_fabric_root
            / "receipt.json",
    },
}

if str(runtime_root) not in sys.path:
    sys.path.insert(
        0,
        str(runtime_root),
    )


from living_task import NicheTaskError  # noqa: E402
from task_engine import (  # noqa: E402
    NicheTaskEngineError,
    engine,
)


max_body_bytes = 1024 * 1024

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


def read_json_projection(
    path: Path,
) -> dict[str, Any] | None:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        value,
        dict,
    ):
        return None

    return value


def projection_file_state(
    path: Path,
) -> dict[str, Any]:
    try:
        info = path.stat()

    except OSError:
        return {
            "path":
                str(path),
            "present":
                False,
            "mtime_ns":
                None,
            "size":
                None,
        }

    return {
        "path":
            str(path),
        "present":
            True,
        "mtime_ns":
            info.st_mtime_ns,
        "size":
            info.st_size,
    }


def fabric_projection() -> dict[str, Any]:
    current = read_json_projection(
        living_sources[
            "fabric"
        ][
            "current"
        ]
    )

    health = read_json_projection(
        living_sources[
            "fabric"
        ][
            "health"
        ]
    )

    receipt = read_json_projection(
        living_sources[
            "fabric"
        ][
            "receipt"
        ]
    )

    if current is None:
        return {
            "present":
                False,
            "healthy":
                (
                    health.get(
                        "healthy"
                    )
                    if health
                    else None
                ),
            "projection_only":
                True,
            "authority_effect":
                "none",
            "surface_count":
                0,
            "surfaces":
                {},
            "catalog":
                {},
            "sources": {
                name:
                    projection_file_state(
                        path
                    )
                for name, path
                in living_sources[
                    "fabric"
                ].items()
            },
        }

    surfaces = current.get(
        "surfaces",
        {}
    )

    if not isinstance(
        surfaces,
        dict,
    ):
        surfaces = {}

    catalog = current.get(
        "catalog",
        {}
    )

    if not isinstance(
        catalog,
        dict,
    ):
        catalog = {}

    changed_surfaces = current.get(
        "changed_surfaces",
        []
    )

    if not isinstance(
        changed_surfaces,
        list,
    ):
        changed_surfaces = []

    unchanged_surfaces = current.get(
        "unchanged_surfaces",
        []
    )

    if not isinstance(
        unchanged_surfaces,
        list,
    ):
        unchanged_surfaces = []

    classes: dict[str, int] = {}
    owners: dict[str, int] = {}
    modes: dict[str, int] = {}

    for specification in catalog.values():
        if not isinstance(
            specification,
            dict,
        ):
            continue

        surface_class = str(
            specification.get(
                "class",
                "unknown",
            )
        )

        owner = str(
            specification.get(
                "owner",
                "unknown",
            )
        )

        mode = str(
            specification.get(
                "mode",
                "unknown",
            )
        )

        classes[
            surface_class
        ] = (
            classes.get(
                surface_class,
                0,
            )
            + 1
        )

        owners[
            owner
        ] = (
            owners.get(
                owner,
                0,
            )
            + 1
        )

        modes[
            mode
        ] = (
            modes.get(
                mode,
                0,
            )
            + 1
        )

    return {
        "present":
            True,

        "healthy":
            (
                health.get(
                    "healthy"
                )
                if health
                else None
            ),

        "id":
            current.get(
                "id"
            ),

        "schema":
            current.get(
                "schema"
            ),

        "sequence":
            current.get(
                "sequence"
            ),

        "fabric_hash":
            current.get(
                "fabric_hash"
            ),

        "previous_fabric_hash":
            current.get(
                "previous_fabric_hash"
            ),

        "generated_at_unix_ns":
            current.get(
                "generated_at_unix_ns"
            ),

        "projection_only":
            current.get(
                "projection_only",
                True,
            ),

        "authority_effect":
            current.get(
                "authority_effect",
                "none",
            ),

        "source_authority_preserved":
            current.get(
                "source_authority_preserved",
                True,
            ),

        "filesystem_presence_establishes_authority":
            current.get(
                "filesystem_presence_establishes_authority",
                False,
            ),

        "single_fabric":
            current.get(
                "single_fabric",
                True,
            ),

        "surface_count":
            current.get(
                "surface_count",
                len(
                    surfaces
                ),
            ),

        "change_count":
            current.get(
                "change_count",
                len(
                    changed_surfaces
                ),
            ),

        "changed_surfaces":
            changed_surfaces,

        "unchanged_surfaces":
            unchanged_surfaces,

        "catalog_digest":
            current.get(
                "catalog_digest"
            ),

        "catalog":
            catalog,

        "surface_classes":
            dict(
                sorted(
                    classes.items()
                )
            ),

        "surface_owners":
            dict(
                sorted(
                    owners.items()
                )
            ),

        "surface_modes":
            dict(
                sorted(
                    modes.items()
                )
            ),

        "capabilities":
            current.get(
                "capabilities",
                {},
            ),

        "surfaces":
            surfaces,

        "health":
            health,

        "receipt":
            receipt,

        "sources": {
            name:
                projection_file_state(
                    path
                )
            for name, path
            in living_sources[
                "fabric"
            ].items()
        },
    }


def living_projection() -> dict[str, Any]:
    state_current = read_json_projection(
        living_sources[
            "state"
        ][
            "current"
        ]
    )

    state_health = read_json_projection(
        living_sources[
            "state"
        ][
            "health"
        ]
    )

    governance_status = read_json_projection(
        living_sources[
            "governance"
        ][
            "status"
        ]
    )

    governance_snapshot = read_json_projection(
        living_sources[
            "governance"
        ][
            "snapshot"
        ]
    )

    governance_graph = read_json_projection(
        living_sources[
            "governance"
        ][
            "graph"
        ]
    )

    fabric = fabric_projection()

    state_delta = (
        state_current.get(
            "delta",
            {}
        )
        if state_current
        else {}
    )

    state_filesystem = (
        state_current.get(
            "filesystem",
            {}
        )
        if state_current
        else {}
    )

    services = (
        state_current.get(
            "services",
            []
        )
        if state_current
        else []
    )

    active_services = sum(
        1
        for item in services
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "active_state"
        )
        == "active"
    )

    processes = (
        state_current.get(
            "processes",
            []
        )
        if state_current
        else []
    )

    listening_tcp = (
        state_current.get(
            "listening_tcp",
            []
        )
        if state_current
        else []
    )

    streams = (
        governance_status.get(
            "streams",
            []
        )
        if governance_status
        else []
    )

    conflicts = (
        governance_snapshot.get(
            "conflicts",
            []
        )
        if governance_snapshot
        else []
    )

    graph_nodes = (
        governance_graph.get(
            "nodes",
            []
        )
        if governance_graph
        else []
    )

    graph_edges = (
        governance_graph.get(
            "edges",
            []
        )
        if governance_graph
        else []
    )

    source_state = {
        group: {
            name:
                projection_file_state(
                    path
                )
            for name, path
            in sources.items()
        }
        for group, sources
        in living_sources.items()
    }

    return {
        "schema":
            "savant.niche.living-observatory.v2",

        "owner":
            "exile:niche",

        "projection_only":
            True,

        "authority_effect":
            "none",

        "filesystem_presence_establishes_authority":
            False,

        "fabric":
            fabric,

        "engines": {
            "living_state": {
                "present":
                    state_current
                    is not None,

                "healthy":
                    (
                        state_health.get(
                            "healthy"
                        )
                        if state_health
                        else None
                    ),

                "sequence":
                    (
                        state_current.get(
                            "sequence"
                        )
                        if state_current
                        else None
                    ),

                "snapshot_hash":
                    (
                        state_current.get(
                            "snapshot_hash"
                        )
                        if state_current
                        else None
                    ),

                "previous_snapshot_hash":
                    (
                        state_current.get(
                            "previous_snapshot_hash"
                        )
                        if state_current
                        else None
                    ),

                "generated_at_unix_ns":
                    (
                        state_current.get(
                            "generated_at_unix_ns"
                        )
                        if state_current
                        else None
                    ),

                "duration_seconds":
                    (
                        state_health.get(
                            "duration_seconds"
                        )
                        if state_health
                        else None
                    ),

                "delta":
                    state_delta,

                "filesystem": {
                    "files":
                        state_filesystem.get(
                            "files"
                        ),

                    "source_candidates":
                        state_filesystem.get(
                            "source_candidates"
                        ),

                    "bytes":
                        state_filesystem.get(
                            "bytes"
                        ),

                    "symlink_count":
                        state_filesystem.get(
                            "symlink_count"
                        ),

                    "failure_count":
                        len(
                            state_filesystem.get(
                                "failures",
                                [],
                            )
                            or []
                        ),

                    "evidence_classes":
                        state_filesystem.get(
                            "evidence_classes",
                            {},
                        ),
                },

                "services": {
                    "known":
                        len(
                            services
                        ),

                    "active":
                        active_services,

                    "records":
                        services,
                },

                "processes": {
                    "count":
                        len(
                            processes
                        ),

                    "records":
                        processes,
                },

                "listening_tcp": {
                    "count":
                        len(
                            listening_tcp
                        ),

                    "records":
                        listening_tcp,
                },

                "capabilities":
                    (
                        state_current.get(
                            "capabilities",
                            {}
                        )
                        if state_current
                        else {}
                    ),

                "system":
                    (
                        state_current.get(
                            "system",
                            {}
                        )
                        if state_current
                        else {}
                    ),

                "git":
                    (
                        state_current.get(
                            "git"
                        )
                        if state_current
                        else None
                    ),

                "latest_sdump":
                    (
                        state_current.get(
                            "latest_sdump"
                        )
                        if state_current
                        else None
                    ),
            },

            "living_governance": {
                "present":
                    governance_status
                    is not None,

                "digest":
                    (
                        governance_status.get(
                            "digest"
                        )
                        if governance_status
                        else None
                    ),

                "ledger_present":
                    (
                        governance_status.get(
                            "ledger_present"
                        )
                        if governance_status
                        else None
                    ),

                "ledger_events":
                    (
                        governance_status.get(
                            "ledger_events"
                        )
                        if governance_status
                        else None
                    ),

                "current_records":
                    (
                        governance_status.get(
                            "current_records"
                        )
                        if governance_status
                        else None
                    ),

                "streams":
                    streams,

                "stream_count":
                    len(
                        streams
                    ),

                "conflict_count":
                    len(
                        conflicts
                    ),

                "conflicts":
                    conflicts,

                "graph": {
                    "nodes":
                        len(
                            graph_nodes
                        ),

                    "edges":
                        len(
                            graph_edges
                        ),

                    "records":
                        governance_graph,
                },
            },

            "living_fabric": {
                "present":
                    fabric.get(
                        "present",
                        False,
                    ),

                "healthy":
                    fabric.get(
                        "healthy"
                    ),

                "sequence":
                    fabric.get(
                        "sequence"
                    ),

                "fabric_hash":
                    fabric.get(
                        "fabric_hash"
                    ),

                "surface_count":
                    fabric.get(
                        "surface_count",
                        0,
                    ),

                "change_count":
                    fabric.get(
                        "change_count",
                        0,
                    ),

                "single_fabric":
                    fabric.get(
                        "single_fabric",
                        True,
                    ),
            },
        },

        "sources":
            source_state,
    }


class TaskboardServer(
    ThreadingHTTPServer
):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
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
        "savant-niche-taskboard/1.2"
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
        length: int | None = None,
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
                str(length),
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
            separators=(",", ":"),
            default=str,
        ).encode(
            "utf-8"
        )

        self._headers(
            int(status),
            (
                "application/json; "
                "charset=utf-8"
            ),
            len(body),
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
        content_type = self.headers.get(
            "Content-Type",
            "",
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

        raw_length = self.headers.get(
            "Content-Length"
        )

        if not raw_length:
            return {}

        length = int(
            raw_length
        )

        if (
            length < 0
            or length > max_body_bytes
        ):
            raise NicheTaskEngineError(
                "request body exceeds limit"
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
        if try_handle_atlas_get(self):
            return

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
                str(exc),
            )

        except Exception as exc:
            self.send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                (
                    type(exc).__name__
                    + ": "
                    + str(exc)
                ),
            )

    def do_POST(
        self,
    ) -> None:
        if reject_atlas_mutation(self):
            return

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
                str(exc),
            )

        except Exception as exc:
            self.send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                (
                    type(exc).__name__
                    + ": "
                    + str(exc)
                ),
            )

    def do_PATCH(
        self,
    ) -> None:
        if reject_atlas_mutation(self):
            return

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
                str(exc),
            )

        except Exception as exc:
            self.send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                (
                    type(exc).__name__
                    + ": "
                    + str(exc)
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

        if path == "/api/living":
            self.send_json(
                living_projection()
            )
            return

        if path == "/api/living/fabric":
            self.send_json(
                fabric_projection()
            )
            return


        if path == "/api/masterplan":
            self.send_json(
                masterplan_projection()
            )
            return

        if path == "/api/masterplan/summary":
            self.send_json(
                summary_projection()
            )
            return

        if path == "/api/masterplan/index":
            self.send_json(
                index_projection()
            )
            return

        if path == "/api/masterplan/lineage":
            self.send_json(
                lineage_projection()
            )
            return

        if path == "/api/masterplan/integrity":
            self.send_json(
                projection_snapshot()
            )
            return

        if path.startswith("/api/masterplan/identity/"):
            identity = path[
                len("/api/masterplan/identity/"):
            ]

            if identity:
                self.send_json(
                    identity_projection(
                        identity
                    )
                )
                return

        if path == "/api/history":
            task_id = query.get(
                "task_id",
                [None],
            )[0]

            self.send_json(
                {
                    "events":
                        self.task_engine.history(
                            task_id
                        )
                }
            )
            return

        if path == "/api/tasks":
            statuses = tuple(
                value
                for item in query.get(
                    "status",
                    [],
                )
                for value in item.split(",")
                if value
            )

            priorities = tuple(
                value
                for item in query.get(
                    "priority",
                    [],
                )
                for value in item.split(",")
                if value
            )

            include_terminal = (
                query.get(
                    "include_terminal",
                    ["true"],
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
                                    [None],
                                )[0],

                            statuses=
                                statuses,

                            priorities=
                                priorities,

                            owner_filter=
                                query.get(
                                    "owner",
                                    [None],
                                )[0],

                            assignee=
                                query.get(
                                    "assignee",
                                    [None],
                                )[0],

                            label=
                                query.get(
                                    "label",
                                    [None],
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
                self.task_engine.public_task(
                    task_id
                )
            )
            return

        if (
            path == "/"
            or path.startswith(
                "/assets/"
            )
            or path in {
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
        path = urlparse(
            self.path
        ).path

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
                    self.task_engine.transition(
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
                    self.task_engine.lease(
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
                    self.task_engine.release(
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
                / request_path.lstrip("/")
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

        body = candidate.read_bytes()

        content_type = (
            mimetypes.guess_type(
                candidate.name
            )[0]
            or "application/octet-stream"
        )

        if (
            content_type.startswith(
                "text/"
            )
            or content_type in {
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
            len(body),
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
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8787,
    )

    parser.add_argument(
        "--db",
        default=str(
            default_db
        ),
    )

    return parser


def main(
) -> int:
    args = build_parser().parse_args()

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
                        + str(args.port)
                        + "/"
                    ),

                "database":
                    str(
                        Path(
                            args.db
                        ).resolve()
                    ),

                "living_observatory":
                    (
                        "http://"
                        + args.bind
                        + ":"
                        + str(args.port)
                        + "/api/living"
                    ),

                "living_fabric":
                    (
                        "http://"
                        + args.bind
                        + ":"
                        + str(args.port)
                        + "/api/living/fabric"
                    ),

                "authority_effect":
                    "none",
            },
            sort_keys=True,
        )
    )

    try:
        server.serve_forever(
            poll_interval=0.25
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
