#!/usr/bin/env python3

from __future__ import annotations

import json
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


schema = "savant.assurance.atlas-runtime-check.v1"
authority_effect = "none"
owner = "exile:niche"

host = "127.0.0.1"
port = 8777

assets_root = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/assets"
)

required_files = (
    assets_root / "index.html",
    assets_root / "atlas.css",
    assets_root / "atlas.js",
    assets_root / "atlas-static-bridge.js",
    assets_root / "atlas.json",
)

required_units = (
    "savant-atlas-static.service",
    "savant-atlas-masterplan.path",
    "savant-atlas-niche-tasks.path",
    "savant-atlas.target",
)


class AtlasRuntimeError(RuntimeError):
    pass


def run(
    *command: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
    )


def unit_properties(
    unit: str,
) -> dict[str, str]:
    process = run(
        "systemctl",
        "show",
        unit,
        "--property=LoadState",
        "--property=ActiveState",
        "--property=SubState",
        "--property=Result",
    )

    if process.returncode != 0:
        raise AtlasRuntimeError(
            f"{unit}: "
            + process.stderr.strip()
        )

    properties: dict[str, str] = {}

    for line in process.stdout.splitlines():
        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1,
        )

        properties[key] = value

    return properties


def require_unit(
    unit: str,
) -> dict[str, str]:
    properties = unit_properties(
        unit
    )

    if properties.get("LoadState") != "loaded":
        raise AtlasRuntimeError(
            f"{unit} is not loaded"
        )

    if unit.endswith(".service"):
        if properties.get("ActiveState") != "active":
            raise AtlasRuntimeError(
                f"{unit} is not active"
            )

        if properties.get("SubState") != "running":
            raise AtlasRuntimeError(
                f"{unit} is not running"
            )

    if unit.endswith(".path"):
        if properties.get("ActiveState") != "active":
            raise AtlasRuntimeError(
                f"{unit} is not active"
            )

    return properties


def validate_files() -> list[dict[str, Any]]:
    result = []

    for path in required_files:
        if not path.is_file():
            raise AtlasRuntimeError(
                f"missing Atlas artifact: {path}"
            )

        size = path.stat().st_size

        if size <= 0:
            raise AtlasRuntimeError(
                f"empty Atlas artifact: {path}"
            )

        result.append(
            {
                "path": str(path),
                "bytes": size,
            }
        )

    return result


def validate_projection() -> dict[str, Any]:
    path = assets_root / "atlas.json"

    projection = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if projection.get("projection_only") is not True:
        raise AtlasRuntimeError(
            "Atlas projection is not projection-only"
        )

    if projection.get("mutation_authority") is not False:
        raise AtlasRuntimeError(
            "Atlas projection has mutation authority"
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
        raise AtlasRuntimeError(
            "Atlas nodes are not a list"
        )

    if not isinstance(edges, list):
        raise AtlasRuntimeError(
            "Atlas edges are not a list"
        )

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "projection_only": True,
        "mutation_authority": False,
    }


def validate_listener() -> dict[str, Any]:
    with socket.create_connection(
        (
            host,
            port,
        ),
        timeout=3.0,
    ):
        pass

    return {
        "host": host,
        "port": port,
        "status": "reachable",
    }


def fetch(
    path: str,
    expected_content: str,
) -> dict[str, Any]:
    url = (
        f"http://{host}:{port}{path}"
    )

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Cache-Control": "no-cache",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5.0,
        ) as response:
            status = response.status
            content_type = response.headers.get(
                "Content-Type",
                "",
            )
            body = response.read()

    except urllib.error.URLError as exc:
        raise AtlasRuntimeError(
            f"{path} failed: {exc}"
        ) from exc

    if status != 200:
        raise AtlasRuntimeError(
            f"{path} returned HTTP {status}"
        )

    if expected_content not in content_type:
        raise AtlasRuntimeError(
            f"{path} returned unexpected content type "
            f"{content_type!r}"
        )

    if not body:
        raise AtlasRuntimeError(
            f"{path} returned an empty body"
        )

    return {
        "path": path,
        "http_status": status,
        "content_type": content_type,
        "bytes": len(body),
    }


def main() -> int:
    try:
        files = validate_files()

        projection = validate_projection()

        units = {
            unit: require_unit(unit)
            for unit in required_units
        }

        listener = validate_listener()

        http = {
            "index": fetch(
                "/",
                "text/html",
            ),
            "css": fetch(
                "/atlas.css",
                "text/css",
            ),
            "javascript": fetch(
                "/atlas.js",
                "javascript",
            ),
            "bridge": fetch(
                "/atlas-static-bridge.js",
                "javascript",
            ),
            "projection": fetch(
                "/atlas.json",
                "application/json",
            ),
        }

        result = {
            "schema": schema,
            "authority_effect": authority_effect,
            "owner": owner,
            "status": "passed",
            "projection_only": True,
            "mutation_authority": False,
            "files": files,
            "projection": projection,
            "units": units,
            "listener": listener,
            "http": http,
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
                    "authority_effect": authority_effect,
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
    raise SystemExit(
        main()
    )
