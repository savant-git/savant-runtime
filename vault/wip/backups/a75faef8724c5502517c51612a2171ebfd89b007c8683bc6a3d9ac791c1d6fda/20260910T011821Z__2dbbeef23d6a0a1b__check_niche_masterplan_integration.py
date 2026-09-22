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
    "niche-masterplan-integration-check.v1"
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


def require_at_least_once(
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

        load_module(
            "masterplan_index_projection",
            index_projection_path,
        )

        load_module(
            "masterplan_lineage_projection",
            lineage_projection_path,
        )

        integrity_module = load_module(
            "masterplan_projection_self_check",
            integrity_projection_path,
        )

        projection = (
            projection_module.masterplan_projection()
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

    if not isinstance(
        projection,
        dict,
    ):
        raise IntegrationCheckError(
            "masterplan projection "
            "did not return an object"
        )

    if not isinstance(
        integrity,
        dict,
    ):
        raise IntegrationCheckError(
            "integrity self-check "
            "did not return an object"
        )

    if (
        projection.get(
            "mutation_authority"
        )
        is not False
    ):
        raise IntegrationCheckError(
            "masterplan projection acquired "
            "mutation authority"
        )

    if (
        integrity.get(
            "mutation_authority"
        )
        is not False
    ):
        raise IntegrationCheckError(
            "integrity projection acquired "
            "mutation authority"
        )

    if (
        integrity.get(
            "self_check"
        )
        != "passed"
    ):
        raise IntegrationCheckError(
            "integrity self-check did not pass"
        )

    if (
        integrity.get(
            "source_graph_digest"
        )
        != projection.get(
            "graph_digest"
        )
    ):
        raise IntegrationCheckError(
            "projection graph digest mismatch"
        )

    return {
        "graph_digest":
            projection.get(
                "graph_digest"
            ),
        "projection_digest":
            projection.get(
                "projection_digest"
            ),
        "integrity_digest":
            integrity.get(
                "projection_digest"
            ),
        "identity_count":
            integrity.get(
                "identity_count"
            ),
        "lineage_count":
            integrity.get(
                "lineage_count"
            ),
        "duplicate_identity_group_count":
            integrity.get(
                "duplicate_identity_group_count"
            ),
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

    endpoints = (
        "/api/masterplan",
        "/api/masterplan/summary",
        "/api/masterplan/index",
        "/api/masterplan/lineage",
        "/api/masterplan/integrity",
    )

    for endpoint in endpoints:
        require_once(
            text,
            f'if path == "{endpoint}":',
            endpoint,
        )

    require_once(
        text,
        "masterplan_projection()",
        "masterplan projection call",
    )

    require_once(
        text,
        "summary_projection()",
        "summary projection call",
    )

    require_once(
        text,
        "index_projection()",
        "index projection call",
    )

    require_once(
        text,
        "lineage_projection()",
        "lineage projection call",
    )

    require_once(
        text,
        "projection_snapshot()",
        "integrity projection call",
    )

    return {
        "path":
            str(
                server_path
            ),
        "endpoint_count":
            len(
                endpoints
            ),
        "endpoints":
            list(
                endpoints
            ),
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
            "masterplanIntegrityResult,",
            "masterplan integrity result binding",
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

    require_at_least_once(
        text,
        'document.querySelector("#projection-status")',
        "existing projection-status surface binding",
    )

    require_at_least_once(
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
        "new_dom_surface_required":
            False,
    }


def run_check() -> dict[
    str,
    Any,
]:
    projection = (
        check_projection_modules()
    )

    server = check_server()

    client = check_client()

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "owner":
            "exile:niche",
        "mutation_authority_added":
            False,
        "authoritative_graph_duplicated":
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
