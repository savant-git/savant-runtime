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
    "niche-masterplan-integration-check.v2"
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


def compile_python_file(
    path: Path,
) -> None:
    text = path.read_text(
        encoding="utf-8"
    )

    compile(
        text,
        str(path),
        "exec",
    )


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


def check_projection_modules() -> dict[
    str,
    Any,
]:
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

        full = (
            projection_module.masterplan_projection()
        )

        summary = (
            projection_module.summary_projection()
        )

        index = (
            index_module.index_projection()
        )

        lineage = (
            lineage_module.lineage_projection()
        )

        integrity = (
            integrity_module.self_check()
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

    for (
        name,
        value,
    ) in (
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
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise IntegrationCheckError(
                f"{name} projection "
                "did not return an object"
            )

        if (
            value.get(
                "mutation_authority"
            )
            is not False
        ):
            raise IntegrationCheckError(
                f"{name} projection acquired "
                "mutation authority"
            )

    graph_digest = full.get(
        "graph_digest"
    )

    if not isinstance(
        graph_digest,
        str,
    ) or not graph_digest:
        raise IntegrationCheckError(
            "full projection graph digest unavailable"
        )

    digest_candidates = (
        summary.get(
            "graph_digest"
        ),
        index.get(
            "source_graph_digest"
        ),
        lineage.get(
            "source_graph_digest"
        ),
        integrity.get(
            "source_graph_digest"
        ),
    )

    for digest in digest_candidates:
        if digest != graph_digest:
            raise IntegrationCheckError(
                "cross-projection graph digest mismatch"
            )

    identity_index = full.get(
        "identity_index"
    )

    if not isinstance(
        identity_index,
        list,
    ):
        raise IntegrationCheckError(
            "identity index unavailable"
        )

    identity_check = {
        "performed":
            False,
        "identity":
            None,
        "match_count":
            0,
    }

    if identity_index:
        first = identity_index[
            0
        ]

        if not isinstance(
            first,
            dict,
        ):
            raise IntegrationCheckError(
                "identity index member is not an object"
            )

        identity = first.get(
            "identity"
        )

        if not isinstance(
            identity,
            str,
        ) or not identity:
            raise IntegrationCheckError(
                "identity index member lacks identity"
            )

        identity_projection = (
            projection_module.identity_projection(
                identity
            )
        )

        if not isinstance(
            identity_projection,
            dict,
        ):
            raise IntegrationCheckError(
                "identity projection did not "
                "return an object"
            )

        if (
            identity_projection.get(
                "mutation_authority"
            )
            is not False
        ):
            raise IntegrationCheckError(
                "identity projection acquired "
                "mutation authority"
            )

        if (
            identity_projection.get(
                "source_graph_digest"
            )
            != graph_digest
        ):
            raise IntegrationCheckError(
                "identity projection graph "
                "digest mismatch"
            )

        matches = (
            identity_projection.get(
                "matches"
            )
        )

        if not isinstance(
            matches,
            list,
        ) or not matches:
            raise IntegrationCheckError(
                "identity projection returned "
                "no matches for indexed identity"
            )

        if any(
            not isinstance(
                match,
                dict,
            )
            or match.get(
                "identity"
            )
            != identity
            for match in matches
        ):
            raise IntegrationCheckError(
                "identity projection returned "
                "foreign identity data"
            )

        identity_check = {
            "performed":
                True,
            "identity":
                identity,
            "match_count":
                len(
                    matches
                ),
        }

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
                identity_index
            ),
        "duplicate_identity_group_count":
            len(
                full.get(
                    "duplicate_identities",
                    [],
                )
            ),
        "identity_lookup":
            identity_check,
    }


def check_server() -> dict[
    str,
    Any,
]:
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
        "masterplan identity endpoint",
    )

    required_calls = (
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
    )

    for (
        fragment,
        label,
    ) in required_calls:
        require_once(
            text,
            fragment,
            label,
        )

    require_present(
        text,
        "identity_projection,",
        "identity projection import",
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
        "static_endpoints":
            list(
                static_endpoints
            ),
        "dynamic_endpoints": [
            "/api/masterplan/identity/{identity}"
        ],
    }


def check_client() -> dict[
    str,
    Any,
]:
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
            'api("/api/masterplan")',
            "masterplan request",
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
            "masterplan integrity assignment",
        ),
        (
            "function "
            "renderMasterplanIntegrityStatus()",
            "masterplan integrity renderer",
        ),
        (
            "renderMasterplanIntegrityStatus();",
            "masterplan integrity render binding",
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

    require_present(
        text,
        'document.querySelector("#projection-status")',
        "projection-status surface binding",
    )

    require_present(
        text,
        '"masterplan linked"',
        "masterplan linked status",
    )

    return {
        "path":
            str(
                app_path
            ),
        "parallel_refresh_loop_added":
            False,
        "parallel_task_state_added":
            False,
        "mutation_surface_added":
            False,
    }


def run_check() -> dict[
    str,
    Any,
]:
    projection = (
        check_projection_modules()
    )

    server = (
        check_server()
    )

    client = (
        check_client()
    )

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
            projection,
        "server":
            server,
        "client":
            client,
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
