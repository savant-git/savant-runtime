#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


schema = "savant.assurance.atlas-projection-refresh-check.v1"
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


def require_path_unit(
    name: str,
) -> dict[str, Any]:
    process = command(
        "systemctl",
        "show",
        name,
        "--property=LoadState,ActiveState,SubState",
        "--value",
    )

    if process.returncode != 0:
        raise AtlasRefreshCheckError(
            f"{name} could not be inspected: "
            + process.stderr.strip()
        )

    values = [
        value.strip()
        for value in process.stdout.splitlines()
    ]

    if len(values) != 3:
        raise AtlasRefreshCheckError(
            f"{name} returned unexpected systemd state"
        )

    load_state, active_state, sub_state = values

    if load_state != "loaded":
        raise AtlasRefreshCheckError(
            f"{name} is not loaded"
        )

    if active_state != "active":
        raise AtlasRefreshCheckError(
            f"{name} is not active"
        )

    return {
        "load_state": load_state,
        "active_state": active_state,
        "sub_state": sub_state,
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

    if projection.get("projection_only") is not True:
        raise AtlasRefreshCheckError(
            "Atlas projection is not projection-only"
        )

    if projection.get("mutation_authority") is not False:
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

    if not isinstance(nodes, list):
        raise AtlasRefreshCheckError(
            "Atlas projection nodes are not a list"
        )

    if not isinstance(edges, list):
        raise AtlasRefreshCheckError(
            "Atlas projection edges are not a list"
        )

    return {
        "path": str(projection_path),
        "bytes": projection_path.stat().st_size,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "projection_only": True,
        "mutation_authority": False,
    }


def main() -> int:
    try:
        projection = validate_projection()

        units = {
            name: require_path_unit(name)
            for name in path_units
        }

        service = command(
            "systemctl",
            "show",
            service_name,
            "--property=LoadState,Result",
            "--value",
        )

        if service.returncode != 0:
            raise AtlasRefreshCheckError(
                service.stderr.strip()
            )

        service_values = [
            value.strip()
            for value in service.stdout.splitlines()
        ]

        if (
            len(service_values) != 2
            or service_values[0] != "loaded"
        ):
            raise AtlasRefreshCheckError(
                "Atlas projection refresh service "
                "is not loaded"
            )

        result = {
            "schema": schema,
            "authority_effect":
                authority_effect,
            "owner": owner,
            "status": "passed",
            "projection": projection,
            "refresh": {
                "strategy":
                    "systemd-path-event",
                "frontend_polling":
                    False,
                "duplicate_task_authority":
                    False,
                "service":
                    service_name,
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
                    "schema": schema,
                    "authority_effect":
                        authority_effect,
                    "owner": owner,
                    "status": "failed",
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
