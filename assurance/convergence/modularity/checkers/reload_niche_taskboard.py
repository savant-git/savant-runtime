#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "reload-niche-taskboard.v1"
)

authority_effect = "none"

host = "127.0.0.1"
port = 8765

server_path = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/taskboard/server.py"
)


class ReloadError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ReloadError(message)


def listening_socket_inode() -> str | None:
    target_port = f"{port:04X}"

    for table_path in (
        Path("/proc/net/tcp"),
        Path("/proc/net/tcp6"),
    ):
        if not table_path.is_file():
            continue

        lines = table_path.read_text(
            encoding="utf-8"
        ).splitlines()[1:]

        for line in lines:
            fields = line.split()

            if len(fields) < 10:
                continue

            local_address = fields[1]
            state = fields[3]
            inode = fields[9]

            _, local_port = local_address.rsplit(
                ":",
                1,
            )

            if (
                local_port.upper() == target_port
                and state == "0A"
            ):
                return inode

    return None


def pid_for_socket_inode(
    inode: str,
) -> int | None:
    target = f"socket:[{inode}]"

    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue

        fd_root = proc / "fd"

        if not fd_root.is_dir():
            continue

        try:
            descriptors = list(
                fd_root.iterdir()
            )
        except (
            PermissionError,
            FileNotFoundError,
        ):
            continue

        for descriptor in descriptors:
            try:
                link = os.readlink(
                    descriptor
                )
            except (
                FileNotFoundError,
                PermissionError,
                OSError,
            ):
                continue

            if link == target:
                return int(
                    proc.name
                )

    return None


def read_cmdline(
    pid: int,
) -> list[str]:
    raw = (
        Path(f"/proc/{pid}/cmdline")
        .read_bytes()
    )

    return [
        part.decode(
            "utf-8",
            errors="surrogateescape",
        )
        for part in raw.split(b"\0")
        if part
    ]


def read_cwd(
    pid: int,
) -> str:
    return os.readlink(
        f"/proc/{pid}/cwd"
    )


def read_environment(
    pid: int,
) -> dict[str, str]:
    raw = (
        Path(f"/proc/{pid}/environ")
        .read_bytes()
    )

    environment: dict[
        str,
        str,
    ] = {}

    for entry in raw.split(
        b"\0"
    ):
        if not entry or b"=" not in entry:
            continue

        key, value = entry.split(
            b"=",
            1,
        )

        environment[
            key.decode(
                "utf-8",
                errors="surrogateescape",
            )
        ] = value.decode(
            "utf-8",
            errors="surrogateescape",
        )

    return environment


def command_owns_taskboard(
    command: list[str],
) -> bool:
    canonical = str(
        server_path
    )

    return any(
        argument == canonical
        for argument in command
    )


def wait_until_closed(
    timeout: float = 5.0,
) -> None:
    deadline = (
        time.monotonic()
        + timeout
    )

    while (
        time.monotonic()
        < deadline
    ):
        inode = listening_socket_inode()

        if inode is None:
            return

        time.sleep(
            0.1
        )

    raise ReloadError(
        "existing Niche taskboard did not release port 8765"
    )


def wait_until_open(
    timeout: float = 8.0,
) -> None:
    deadline = (
        time.monotonic()
        + timeout
    )

    while (
        time.monotonic()
        < deadline
    ):
        try:
            with socket.create_connection(
                (
                    host,
                    port,
                ),
                timeout=0.5,
            ):
                return

        except OSError:
            time.sleep(
                0.1
            )

    raise ReloadError(
        "restarted Niche taskboard did not bind port 8765"
    )


def reload_taskboard() -> dict[str, Any]:
    require(
        server_path.is_file(),
        "Niche taskboard server unavailable",
    )

    compile(
        server_path.read_text(
            encoding="utf-8"
        ),
        str(server_path),
        "exec",
    )

    inode = listening_socket_inode()

    require(
        inode is not None,
        "nothing is listening on port 8765",
    )

    pid = pid_for_socket_inode(
        inode
    )

    require(
        pid is not None,
        "cannot resolve process listening on port 8765",
    )

    command = read_cmdline(
        pid
    )

    require(
        command_owns_taskboard(
            command
        ),
        "port 8765 is not owned by the canonical Niche taskboard; "
        f"refusing to terminate pid {pid}: {command!r}",
    )

    cwd = read_cwd(
        pid
    )

    environment = read_environment(
        pid
    )

    os.kill(
        pid,
        signal.SIGTERM,
    )

    wait_until_closed()

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )

    wait_until_open()

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "server":
            str(server_path),
        "old_pid":
            pid,
        "new_pid":
            process.pid,
        "host":
            host,
        "port":
            port,
        "command":
            command,
        "projection_only":
            True,
        "mutation_authority_added":
            False,
    }


def main() -> int:
    try:
        result = reload_taskboard()

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
                        str(exc),
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
