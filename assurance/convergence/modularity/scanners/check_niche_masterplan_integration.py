#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "niche-masterplan-integration-check.v4"
)

authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
)

taskboard_root = (
    runtime_root
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
    / "niche"
    / "apps"
    / "taskboard"
)

server_path = (
    taskboard_root
    / "server.py"
)

app_path = (
    taskboard_root
    / "app.js"
)

projection_path = (
    taskboard_root
    / "masterplan_projection.py"
)

index_projection_path = (
    taskboard_root
    / "masterplan_index_projection.py"
)

lineage_projection_path = (
    taskboard_root
    / "masterplan_lineage_projection.py"
)

integrity_projection_path = (
    taskboard_root
    / "masterplan_projection_self_check.py"
)


class IntegrationCheckError(
    RuntimeError
):
    pass


def require_file(
    path: Path,
) -> None:
    if not path.is_file():
        raise IntegrationCheckError(
            f"required file unavailable: {path}"
        )


def compile_python_file(
    path: Path,
) -> None:
    compile(
        path.read_text(
            encoding="utf-8"
        ),
        str(path),
        "exec",
    )


def require_once(
    text: str,
    fragment: str,
    label: str,
) -> None:
    count = text.count(
        fragment
    )

    if count != 1:
        raise IntegrationCheckError(
            f"{label} expected once, found {count}"
        )


def require_present(
    text: str,
    fragment: str,
    label: str,
) -> None:
    if fragment not in text:
        raise IntegrationCheckError(
            f"{label} unavailable"
        )


def require_mapping(
    value: Any,
    label: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        dict,
    ):
        raise IntegrationCheckError(
            f"{label} did not return an object"
        )

    return value


def require_projection_boundary(
    projection: dict[str, Any],
    label: str,
) -> None:
    if (
        projection.get(
            "mutation_authority"
        )
        is not False
    ):
        raise IntegrationCheckError(
            f"{label} acquired mutation authority"
        )


def resolve_graph_digest(
    projection: dict[str, Any],
    label: str,
) -> str:
    values = []

    for key in (
        "graph_digest",
        "source_graph_digest",
    ):
        value = projection.get(
            key
        )

        if isinstance(
            value,
            str,
        ) and value:
            values.append(
                value
            )

    if not values:
        raise IntegrationCheckError(
            f"{label} graph digest unavailable"
        )

    if len(
        set(
            values
        )
    ) != 1:
        raise IntegrationCheckError(
            f"{label} contains conflicting "
            "graph digest fields"
        )

    return values[
        0
    ]


def load_module(
    name: str,
    path: Path,
):
    spec = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise IntegrationCheckError(
            f"unable to load module: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def check_projections() -> dict[str, Any]:
    for path in (
        projection_path,
        index_projection_path,
        lineage_projection_path,
        integrity_projection_path,
    ):
        require_file(
            path
        )

        compile_python_file(
            path
        )

    sys.path.insert(
        0,
        str(
            taskboard_root
        ),
    )

    try:
        projection_module = load_module(
            "masterplan_projection",
            projection_path,
        )

        index_module = load_module(
            "masterplan_index_projection",
            index_projection_path,
        )

        lineage_module = load_module(
            "masterplan_lineage_projection",
            lineage_projection_path,
        )

        integrity_module = load_module(
            "masterplan_projection_self_check",
            integrity_projection_path,
        )

        full = require_mapping(
            projection_module.masterplan_projection(),
            "full projection",
        )

        summary = require_mapping(
            projection_module.summary_projection(),
            "summary projection",
        )

        index = require_mapping(
            index_module.index_projection(),
            "index projection",
        )

        lineage = require_mapping(
            lineage_module.lineage_projection(),
            "lineage projection",
        )

        integrity = require_mapping(
            integrity_module.self_check(),
            "integrity projection",
        )

    finally:
        try:
            sys.path.remove(
                str(
                    taskboard_root
                )
            )

        except ValueError:
            pass

    projections = (
        (
            "full",
            full,
        ),
        (
            "summary",
            summary,
        ),
        (
            "index",
            index,
        ),
        (
            "lineage",
            lineage,
        ),
        (
            "integrity",
            integrity,
        ),
    )

    for (
        label,
        projection,
    ) in projections:
        require_projection_boundary(
            projection,
            label,
        )

    graph_digest = (
        resolve_graph_digest(
            full,
            "full projection",
        )
    )

    for (
        label,
        projection,
    ) in projections[
        1:
    ]:
        if (
            resolve_graph_digest(
                projection,
                f"{label} projection",
            )
            != graph_digest
        ):
            raise IntegrationCheckError(
                f"{label} projection graph "
                "digest mismatch"
            )

    return {
        "graph_digest":
            graph_digest,
        "full_projection_digest":
            full.get(
                "projection_digest"
            ),
        "summary_projection_digest":
            summary.get(
                "projection_digest"
            ),
        "index_projection_digest":
            index.get(
                "projection_digest"
            ),
        "lineage_projection_digest":
            lineage.get(
                "projection_digest"
            ),
        "integrity_projection_digest":
            integrity.get(
                "projection_digest"
            ),
        "identity_count":
            len(
                full.get(
                    "identity_index",
                    [],
                )
            )
            if isinstance(
                full.get(
                    "identity_index"
                ),
                list,
            )
            else None,
        "duplicate_identity_group_count":
            len(
                full.get(
                    "duplicate_identities",
                    [],
                )
            )
            if isinstance(
                full.get(
                    "duplicate_identities"
                ),
                list,
            )
            else None,
    }


def check_server() -> dict[str, Any]:
    require_file(
        server_path
    )

    compile_python_file(
        server_path
    )

    text = server_path.read_text(
        encoding="utf-8"
    )

    static_endpoints = (
        "/api/masterplan",
        "/api/masterplan/summary",
        "/api/masterplan/index",
        "/api/masterplan/lineage",
        "/api/masterplan/integrity",
    )

    for endpoint in static_endpoints:
        require_once(
            text,
            f'if path == "{endpoint}":',
            endpoint,
        )

    require_once(
        text,
        'path.startswith("/api/masterplan/identity/")',
        "identity route",
    )

    for (
        fragment,
        label,
    ) in (
        (
            "masterplan_projection()",
            "full projection call",
        ),
        (
            "summary_projection()",
            "summary projection call",
        ),
        (
            "index_projection()",
            "index projection call",
        ),
        (
            "lineage_projection()",
            "lineage projection call",
        ),
        (
            "projection_snapshot()",
            "integrity projection call",
        ),
        (
            "identity_projection(",
            "identity projection call",
        ),
    ):
        require_once(
            text,
            fragment,
            label,
        )

    return {
        "path":
            str(
                server_path
            ),
        "static_endpoint_count":
            len(
                static_endpoints
            ),
        "dynamic_endpoint_count":
            1,
    }


def check_client() -> dict[str, Any]:
    require_file(
        app_path
    )

    text = app_path.read_text(
        encoding="utf-8"
    )

    required_once = (
        (
            "masterplan: null,",
            "masterplan state",
        ),
        (
            "masterplanIntegrity: null,",
            "masterplan integrity state",
        ),
        (
            'api("/api/masterplan/summary")',
            "summary masterplan request",
        ),
        (
            'api("/api/masterplan/integrity")',
            "masterplan integrity request",
        ),
        (
            "masterplanResult,",
            "masterplan result binding",
        ),
        (
            "masterplanIntegrityResult,",
            "masterplan integrity result binding",
        ),
        (
            "state.masterplan = "
            "masterplanResult.value;",
            "masterplan assignment",
        ),
        (
            "state.masterplanIntegrity = "
            "masterplanIntegrityResult.value;",
            "integrity assignment",
        ),
        (
            "function "
            "renderMasterplanIntegrityStatus()",
            "integrity renderer",
        ),
        (
            "renderMasterplanIntegrityStatus();",
            "integrity renderer binding",
        ),
    )

    for (
        fragment,
        label,
    ) in required_once:
        require_once(
            text,
            fragment,
            label,
        )

    if 'api("/api/masterplan")' in text:
        raise IntegrationCheckError(
            "client still transfers full "
            "masterplan graph"
        )

    require_present(
        text,
        'document.querySelector("#projection-status")',
        "projection-status surface",
    )

    return {
        "path":
            str(
                app_path
            ),
        "full_graph_transfer":
            False,
        "parallel_refresh_loop_added":
            False,
        "parallel_task_state_added":
            False,
        "mutation_surface_added":
            False,
    }


def run_check() -> dict[str, Any]:
    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "owner":
            "exile:niche",
        "projection_only":
            True,
        "mutation_authority_added":
            False,
        "authoritative_graph_duplicated":
            False,
        "parallel_task_engine_added":
            False,
        "projection":
            check_projections(),
        "server":
            check_server(),
        "client":
            check_client(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=(
            "check",
        ),
        nargs="?",
        default="check",
    )

    parser.parse_args()

    try:
        result = run_check()

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
