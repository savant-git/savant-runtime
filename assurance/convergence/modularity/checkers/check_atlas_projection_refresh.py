#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


schema = "savant.assurance.atlas-projection-refresh-check.v2"
authority_effect = "none"
owner = "exile:niche"

projection_path = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/assets/"
    "atlas.json"
)

service_name = "savant-atlas-project.service"

path_units = (
    "savant-atlas-masterplan.path",
    "savant-atlas-niche-tasks.path",
)


class AtlasRefreshCheckError(RuntimeError):
    pass


def command(
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
    )


def systemd_properties(
    unit: str,
    *properties: str,
) -> dict[str, str]:
    arguments = [
        "systemctl",
        "show",
        unit,
    ]

    for name in properties:
        arguments.append(
            f"--property={name}"
        )

    process = command(
        *arguments
    )

    if process.returncode != 0:
        raise AtlasRefreshCheckError(
            f"{unit} could not be inspected: "
            + process.stderr.strip()
        )

    values: dict[str, str] = {}

    for line in process.stdout.splitlines():
        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1,
        )

        values[
            key.strip()
        ] = value.strip()

    missing = [
        name
        for name in properties
        if name not in values
    ]

    if missing:
        raise AtlasRefreshCheckError(
            f"{unit} omitted systemd properties: "
            + ", ".join(missing)
        )

    return values


def require_path_unit(
    name: str,
) -> dict[str, Any]:
    properties = systemd_properties(
        name,
        "LoadState",
        "ActiveState",
        "SubState",
    )

    if properties["LoadState"] != "loaded":
        raise AtlasRefreshCheckError(
            f"{name} is not loaded: "
            + properties["LoadState"]
        )

    if properties["ActiveState"] != "active":
        raise AtlasRefreshCheckError(
            f"{name} is not active: "
            + properties["ActiveState"]
        )

    return {
        "load_state":
            properties["LoadState"],
        "active_state":
            properties["ActiveState"],
        "sub_state":
            properties["SubState"],
    }


def validate_projection() -> dict[str, Any]:
    if not projection_path.is_file():
        raise AtlasRefreshCheckError(
            f"missing Atlas projection: {projection_path}"
        )

    projection = json.loads(
        projection_path.read_text(
            encoding="utf-8"
        )
    )

    if projection.get(
        "projection_only"
    ) is not True:
        raise AtlasRefreshCheckError(
            "Atlas projection is not projection-only"
        )

    if projection.get(
        "mutation_authority"
    ) is not False:
        raise AtlasRefreshCheckError(
            "Atlas projection acquired mutation authority"
        )

    nodes = projection.get(
        "nodes",
        [],
    )

    edges = projection.get(
        "edges",
        [],
    )

    if not isinstance(
        nodes,
        list,
    ):
        raise AtlasRefreshCheckError(
            "Atlas projection nodes are not a list"
        )

    if not isinstance(
        edges,
        list,
    ):
        raise AtlasRefreshCheckError(
            "Atlas projection edges are not a list"
        )

    return {
        "path":
            str(projection_path),
        "bytes":
            projection_path.stat().st_size,
        "node_count":
            len(nodes),
        "edge_count":
            len(edges),
        "projection_only":
            True,
        "mutation_authority":
            False,
    }


def validate_service() -> dict[str, Any]:
    properties = systemd_properties(
        service_name,
        "LoadState",
        "ActiveState",
        "SubState",
        "Result",
        "ExecMainCode",
        "ExecMainStatus",
    )

    if properties["LoadState"] != "loaded":
        raise AtlasRefreshCheckError(
            "Atlas projection refresh service "
            "is not loaded: "
            + properties["LoadState"]
        )

    result = properties["Result"]

    if result not in (
        "",
        "success",
    ):
        raise AtlasRefreshCheckError(
            "Atlas projection refresh service "
            "last result was "
            + result
        )

    if properties["ExecMainStatus"] not in (
        "",
        "0",
    ):
        raise AtlasRefreshCheckError(
            "Atlas projection refresh service "
            "last exit status was "
            + properties["ExecMainStatus"]
        )

    return {
        "load_state":
            properties["LoadState"],
        "active_state":
            properties["ActiveState"],
        "sub_state":
            properties["SubState"],
        "result":
            properties["Result"],
        "exec_main_code":
            properties["ExecMainCode"],
        "exec_main_status":
            properties["ExecMainStatus"],
    }


def main() -> int:
    try:
        projection = validate_projection()

        units = {
            name: require_path_unit(
                name
            )
            for name in path_units
        }

        service = validate_service()

        result = {
            "schema":
                schema,
            "authority_effect":
                authority_effect,
            "owner":
                owner,
            "status":
                "passed",
            "projection":
                projection,
            "refresh": {
                "strategy":
                    "systemd-path-event",
                "frontend_polling":
                    False,
                "duplicate_task_authority":
                    False,
                "service":
                    service_name,
                "service_state":
                    service,
                "path_units":
                    units,
            },
        }

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "authority_effect":
                        authority_effect,
                    "owner":
                        owner,
                    "status":
                        "failed",
                    "error":
                        str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
