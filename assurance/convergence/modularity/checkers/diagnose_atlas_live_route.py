#!/usr/bin/env python3

from __future__ import annotations

import http.client
import json
import re
import subprocess
from pathlib import Path
from typing import Any


schema_version = "savant.assurance.diagnose-atlas-live-route.v1"
authority_effect = "none"

frontend_path = "/atlas/assets/atlas.css"
upstream_path = "/assets/atlas.css"

nginx_host = "127.0.0.1"
nginx_port = 8765
atlas_host = "127.0.0.1"
atlas_port = 8766

expected_asset = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/assets/atlas.css"
)


class DiagnoseError(RuntimeError):
    pass


def request(
    host: str,
    port: int,
    path: str,
) -> dict[str, Any]:
    connection = http.client.HTTPConnection(
        host,
        port,
        timeout=5,
    )

    try:
        connection.request(
            "GET",
            path,
            headers={
                "Host": host,
                "Accept": "*/*",
                "Connection": "close",
            },
        )

        response = connection.getresponse()
        body = response.read()

        return {
            "status": response.status,
            "reason": response.reason,
            "content_type": response.getheader(
                "Content-Type"
            ),
            "server": response.getheader(
                "Server"
            ),
            "bytes": len(body),
            "body_prefix": body[:160].decode(
                "utf-8",
                errors="replace",
            ),
        }

    finally:
        connection.close()


def nginx_configuration() -> str:
    process = subprocess.run(
        [
            "nginx",
            "-T",
        ],
        capture_output=True,
        text=True,
    )

    if process.returncode != 0:
        raise DiagnoseError(
            "nginx -T failed: "
            + (
                process.stdout
                + process.stderr
            ).strip()
        )

    return (
        process.stdout
        + process.stderr
    )


def atlas_location_fragments(
    nginx_text: str,
) -> list[str]:
    fragments = []

    lines = nginx_text.splitlines()

    for index, line in enumerate(lines):
        if (
            "/atlas"
            not in line
            and "8766"
            not in line
        ):
            continue

        start = max(
            0,
            index - 3,
        )

        end = min(
            len(lines),
            index + 8,
        )

        fragments.append(
            "\n".join(
                lines[start:end]
            )
        )

    unique = []
    seen = set()

    for fragment in fragments:
        if fragment in seen:
            continue

        seen.add(fragment)
        unique.append(fragment)

    return unique


def exact_atlas_locations(
    nginx_text: str,
) -> list[str]:
    results = []

    for match in re.finditer(
        r"location\s+(?:=|~\*?|@\S+|\^~)?\s*"
        r"[^\{\n]*atlas[^\{\n]*\{",
        nginx_text,
        re.IGNORECASE,
    ):
        results.append(
            match.group(0).strip()
        )

    return sorted(
        set(results)
    )


def main() -> int:
    result: dict[str, Any] = {
        "schema": schema_version,
        "authority_effect": authority_effect,
        "projection_only": True,
        "mutation_authority": False,
        "asset": {
            "path": str(expected_asset),
            "exists": expected_asset.is_file(),
            "bytes": (
                expected_asset.stat().st_size
                if expected_asset.is_file()
                else None
            ),
        },
    }

    try:
        result["direct_upstream"] = request(
            atlas_host,
            atlas_port,
            upstream_path,
        )

        result["direct_upstream_prefixed"] = request(
            atlas_host,
            atlas_port,
            frontend_path,
        )

        result["through_nginx"] = request(
            nginx_host,
            nginx_port,
            frontend_path,
        )

        nginx_text = nginx_configuration()

        result["nginx_atlas_locations"] = (
            exact_atlas_locations(
                nginx_text
            )
        )

        result["nginx_fragments"] = (
            atlas_location_fragments(
                nginx_text
            )
        )

        direct = result[
            "direct_upstream"
        ]

        prefixed = result[
            "direct_upstream_prefixed"
        ]

        proxied = result[
            "through_nginx"
        ]

        if not expected_asset.is_file():
            diagnosis = (
                "atlas stylesheet is absent on disk"
            )

        elif direct["status"] != 200:
            diagnosis = (
                "atlas standalone server is not serving "
                "/assets/atlas.css correctly"
            )

        elif proxied["status"] == 200:
            diagnosis = (
                "atlas stylesheet route is healthy"
            )

        elif (
            direct["status"] == 200
            and prefixed["status"] == 200
            and proxied["status"] == 404
        ):
            diagnosis = (
                "nginx is producing or routing the 404 before "
                "the healthy atlas server response reaches the client"
            )

        elif (
            direct["status"] == 200
            and prefixed["status"] != 200
            and proxied["status"] == 404
        ):
            diagnosis = (
                "nginx is forwarding the atlas-prefixed path "
                "without the intended prefix rewrite"
            )

        else:
            diagnosis = (
                "route failure is localized by the recorded "
                "upstream and nginx responses"
            )

        result[
            "diagnosis"
        ] = diagnosis

        result[
            "status"
        ] = (
            "passed"
            if proxied["status"] == 200
            else "diagnosed"
        )

    except Exception as exc:
        result[
            "status"
        ] = "failed"

        result[
            "error"
        ] = str(exc)

        print(
            json.dumps(
                result,
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

    return (
        0
        if result["status"] == "passed"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
