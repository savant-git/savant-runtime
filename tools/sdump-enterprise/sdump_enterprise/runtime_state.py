from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any


schema = "savant.sdump.runtime-state.v1"

known_services = (
    "palaver.service",
    "palaver-attachment.service",
    "palaver-frontend.service",
    "palaver-tunnel.service",
)


def _run(
    command: list[str],
    timeout: float = 3.0,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
            env={
                **os.environ,
                "LC_ALL": "C",
            },
        )

        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }


def _service_state(
    name: str,
) -> dict[str, Any]:
    result = _run(
        [
            "systemctl",
            "show",
            name,
            "--no-pager",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=FragmentPath",
            "--property=WorkingDirectory",
            "--property=MainPID",
        ]
    )

    fields: dict[str, str] = {}

    if result.get("stdout"):
        for line in str(
            result["stdout"]
        ).splitlines():
            key, separator, value = line.partition("=")

            if separator:
                fields[key] = value

    return {
        "service": name,
        "query_ok": result.get(
            "ok",
            False,
        ),
        "load_state": fields.get(
            "LoadState"
        ),
        "active_state": fields.get(
            "ActiveState"
        ),
        "sub_state": fields.get(
            "SubState"
        ),
        "fragment_path": fields.get(
            "FragmentPath"
        ),
        "working_directory": fields.get(
            "WorkingDirectory"
        ),
        "main_pid": fields.get(
            "MainPID"
        ),
    }


def _nginx_sites() -> list[dict[str, Any]]:
    root = Path(
        "/etc/nginx/sites-enabled"
    )

    if not root.is_dir():
        return []

    records: list[dict[str, Any]] = []

    for path in sorted(
        root.iterdir(),
        key=lambda item: item.name.casefold(),
    ):
        record: dict[str, Any] = {
            "name": path.name,
            "path": str(path),
            "is_symlink": path.is_symlink(),
        }

        if path.is_symlink():
            try:
                record["target"] = str(
                    path.resolve(
                        strict=False
                    )
                )

            except OSError:
                record["target"] = None

        records.append(record)

    return records


def _listening_ports() -> list[dict[str, Any]]:
    result = _run(
        [
            "ss",
            "-H",
            "-ltnp",
        ]
    )

    if not result.get("ok"):
        return []

    records: list[dict[str, Any]] = []

    for line in str(
        result.get("stdout")
        or ""
    ).splitlines():
        columns = line.split(
            None,
            5,
        )

        if len(columns) < 4:
            continue

        records.append(
            {
                "state": columns[0],
                "recv_q": columns[1],
                "send_q": columns[2],
                "local_address": columns[3],
                "peer_address": (
                    columns[4]
                    if len(columns) > 4
                    else None
                ),
                "process": (
                    columns[5]
                    if len(columns) > 5
                    else None
                ),
            }
        )

    return records


def projection() -> dict[str, Any]:
    return {
        "schema": schema,
        "projection_only": True,
        "authority_effect": "none",
        "scope_note": (
            "runtime-state evidence is supplementary "
            "and is not part of the source/tree capture scope"
        ),
        "services": [
            _service_state(name)
            for name in known_services
        ],
        "nginx_enabled_sites": _nginx_sites(),
        "listening_tcp_ports": _listening_ports(),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            projection(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
