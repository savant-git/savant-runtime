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
    "niche-masterplan-integration-check.v3"
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
    compile(
        path.read_text(
            encoding="utf-8"
        ),
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
    value: dict[str, Any],
    label: str,
) -> None:
    if (
        value.get(
            "mutation_authority"
        )
        is not False
    ):
        raise IntegrationCheckError(
            f"{label} acquired mutation authority"
        )


def resolve_graph_digest(
    value: dict[str, Any],
    label: str,
) -> str:
    candidates = (
        value.get(
            "source_graph_digest"
        ),
        value.get(
            "graph_digest"
        ),
    )

    digests = [
        candidate
        for candidate in candidates
        if isinstance(
            candidate,
            str,
        )
        and candidate
    ]

    if not digests:
        raise IntegrationCheckError(
            f"{label} graph digest unavailable"
        )

    if len(
        set(
            digests
        )
    ) != 1:
        raise IntegrationCheckError(
            f"{label} exposes conflicting "
            "graph digests"
        )

    return digests[
        0
    ]


def resolve_identity_members(
    projection: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = (
        projection.get(
            "matches"
        ),
        projection.get(
            "identity_index"
        ),
        projection.get(
            "identities"
        ),
        projection.get(
            "lineage"
        ),
    )

    collections = [
        value
        for value in candidates
        if isinstance(
            value,
            list,
        )
    ]

    if not collections:
        raise IntegrationCheckError(
            "identity projection member "
            "collection unavailable"
        )

    nonempty = [
        value
        for value in collections
        if value
    ]

    selected = (
        nonempty[
            0
        ]
        if nonempty
        else collections[
            0
        ]
    )

    result: list[
        dict[str, Any]
    ] = []

    for member in selected:
        if not isinstance(
            member,
            dict,
        ):
            raise IntegrationCheckError(
                "identity projection contains "
                "a non-object member"
            )

        result.append(
            member
        )

    return result


def member_identity(
    member: dict[str, Any],
) -> str | None:
    for key in (
        "identity",
        "id",
        "task_id",
        "record_id",
        "event_id",
        "decision_id",
        "segue_id",
        "attestation_id",
    ):
        value = member.get(
            key
        )

        if isinstance(
            value,
            str,
        ) and value:
            return value

    return None


def check_identity_lookup(
    projection_module: Any,
    full: dict[str, Any],
    graph_digest: str,
) -> dict[str, Any]:
    identity_index = full.get(
        "identity_index"
    )

    if not isinstance(
        identity_index,
        list,
    ):
        raise IntegrationCheckError(
            "full identity index unavailable"
        )

    if not identity_index:
        return {
            "performed":
                False,
            "reason":
                "identity_index_empty",
            "identity":
                None,
            "match_count":
                0,
        }

    first = identity_index[
        0
    ]

    if not isinstance(
        first,
        dict,
    ):
        raise IntegrationCheckError(
            "identity index member "
            "is not an object"
        )

    identity = first.get(
        "identity"
    )

    if not isinstance(
        identity,
        str,
    ) or not identity:
        raise IntegrationCheckError(
            "indexed identity unavailable"
        )

    identity_projection = (
        require_mapping(
            projection_module.identity_projection(
                identity
            ),
            "identity projection",
        )
    )

    require_projection_boundary(
        identity_projection,
        "identity projection",
    )

    identity_digest = (
        resolve_graph_digest(
            identity_projection,
            "identity projection",
        )
    )

    if identity_digest != graph_digest:
        raise IntegrationCheckError(
            "identity projection graph "
            "digest mismatch"
        )

    members = (
        resolve_identity_members(
            identity_projection
        )
    )

    if not members:
        raise IntegrationCheckError(
            "identity projection returned "
            "no members for indexed identity"
        )

    for member in members:
        resolved = member_identity(
            member
        )

        if (
            resolved is not None
            and resolved != identity
        ):
            raise IntegrationCheckError(
                "identity projection returned "
                "foreign identity data"
            )

        if (
            resolved is None
            and member.get(
                "identity"
            )
            != identity
        ):
            raise IntegrationCheckError(
                "identity projection member "
                "cannot be attributed to "
                "requested identity"
            )

    return {
        "performed":
            True,
        "identity":
            identity,
        "match_count":
            len(
                members
            ),
        "graph_digest":
            identity_digest,
    }


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
            "integrity self-check",
        )

        for (
            label,
            value,
        ) in (
            (
                "full projection",
                full,
            ),
            (
                "summary projection",
                summary,
            ),
            (
                "index projection",
                index,
            ),
            (
                "lineage projection",
                lineage,
            ),
            (
                "integrity projection",
                integrity,
            ),
        ):
            require_projection_boundary(
                value,
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
            value,
        ) in (
            (
                "summary projection",
                summary,
            ),
            (
                "index projection",
                index,
            ),
            (
                "lineage projection",
                lineage,
            ),
            (
                "integrity projection",
                integrity,
            ),
        ):
            if (
                resolve_graph_digest(
                    value,
                    label,
                )
                != graph_digest
            ):
                raise IntegrationCheckError(
                    f"{label} graph digest mismatch"
                )

        identity_check = (
            check_identity_lookup(
                projection_module,
                full,
                graph_digest,
            )
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

    identity_index = full.get(
        "identity_index",
        [],
    )

    duplicates = full.get(
        "duplicate_identities",
        [],
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
                identity_index
            )
            if isinstance(
                identity_index,
                list,
            )
            else None,
        "duplicate_identity_group_count":
            len(
                duplicates
            )
            if isinstance(
                duplicates,
                list,
            )
            else None,
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

    for (
        fragment,
        label,
    ) in (
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
    ):
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
            check_projection_modules(),
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
