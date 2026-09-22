#!/usr/bin/env python3

from __future__ import annotations

import http.client
import json
import subprocess
from typing import Any


schema_version = "savant.assurance.diagnose-atlas-service.v1"
authority_effect = "none"

service_name = "savant-atlas.service"
host = "127.0.0.1"
port = 8776


def run(
    command: list[str],
) -> dict[str, Any]:
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    return {
        "returncode": process.returncode,
        "stdout": process.stdout.strip(),
        "stderr": process.stderr.strip(),
    }


def request(
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
                "Connection": "close",
            },
        )

        response = connection.getresponse()
        body = response.read()

        return {
            "connected": True,
            "http_status": response.status,
            "content_type": response.getheader(
                "Content-Type"
            ),
            "bytes": len(body),
            "body_prefix": body[:300].decode(
                "utf-8",
                errors="replace",
            ),
        }

    except Exception as exc:
        return {
            "connected": False,
            "error": str(exc),
        }

    finally:
        connection.close()


def main() -> int:
    result = {
        "schema": schema_version,
        "authority_effect": authority_effect,
        "projection_only": True,
        "mutation_authority": False,
        "service": run(
            [
                "systemctl",
                "show",
                service_name,
                "--no-pager",
                "--property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,NRestarts,MainPID",
            ]
        ),
        "listener": run(
            [
                "ss",
                "-ltnp",
                f"sport = :{port}",
            ]
        ),
        "direct_health": request(
            "/api/atlas/health"
        ),
        "journal": run(
            [
                "journalctl",
                "-u",
                service_name,
                "-n",
                "40",
                "--no-pager",
                "-o",
                "cat",
            ]
        ),
    }

    healthy = (
        result["direct_health"].get(
            "http_status"
        )
        == 200
    )

    result["status"] = (
        "passed"
        if healthy
        else "diagnosed"
    )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if healthy
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
