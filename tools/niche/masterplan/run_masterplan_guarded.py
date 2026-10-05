#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

MASTERPLAN_BUILD = (
    ROOT
    / "bin"
    / "masterplan-build"
)

MASTERPLAN_GATE = (
    ROOT
    / "bin"
    / "masterplan-gate"
)

LEASE_PATH = (
    ROOT
    / "runtime"
    / "masterplan"
    / "gate"
    / "active-lease.json"
)

RUN_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "guarded-runs"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "guarded-runs"
)

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
    "issued_at",
    "expires_at",
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def execute(
    command: list[str],
    *,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=capture,
        text=True,
    )


def refresh_masterplan() -> None:
    completed = execute(
        [
            str(MASTERPLAN_BUILD),
            "strict",
        ],
        capture=True,
    )

    if completed.returncode:
        raise RuntimeError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "Masterplan refresh failed."
        )


def create_lease(
    agent: str,
    paths: list[str],
    ttl_minutes: int,
) -> dict[str, Any]:
    completed = execute(
        [
            str(MASTERPLAN_GATE),
            "lease",
            "--agent",
            agent,
            "--ttl-minutes",
            str(ttl_minutes),
            *paths,
        ],
        capture=True,
    )

    if completed.returncode:
        raise RuntimeError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "Masterplan lease creation failed."
        )

    if not LEASE_PATH.is_file():
        raise FileNotFoundError(
            LEASE_PATH
        )

    lease = load_json(
        LEASE_PATH
    )

    if lease.get("passed") is not True:
        raise RuntimeError(
            "Masterplan lease was not admitted."
        )

    return lease


def validate_lease() -> dict[str, Any]:
    completed = execute(
        [
            str(MASTERPLAN_GATE),
            "validate",
        ],
        capture=True,
    )

    try:
        payload = json.loads(
            completed.stdout
        )

    except Exception:
        payload = {
            "passed": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    if (
        completed.returncode
        or payload.get("passed") is not True
    ):
        raise RuntimeError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "Masterplan lease validation failed."
        )

    return payload


def revoke_lease() -> dict[str, Any]:
    completed = execute(
        [
            str(MASTERPLAN_GATE),
            "revoke",
        ],
        capture=True,
    )

    try:
        return json.loads(
            completed.stdout
        )

    except Exception:
        return {
            "passed": (
                completed.returncode == 0
            ),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }


def run_guarded(
    *,
    agent: str,
    paths: list[str],
    command: list[str],
    ttl_minutes: int,
    refresh: bool,
    keep_lease: bool,
) -> dict[str, Any]:
    if not command:
        raise ValueError(
            "A guarded command is required."
        )

    if refresh:
        refresh_masterplan()

    lease = create_lease(
        agent,
        paths,
        ttl_minutes,
    )

    validation = validate_lease()

    run_id = (
        f"{timestamp()}__"
        f"{digest({'command': command})[:16]}"
    )

    run_root = (
        RUN_ROOT
        / run_id
    )

    run_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    started_at = utc_now()

    try:
        completed = execute(
            command,
            capture=True,
        )

    finally:
        revocation = (
            None
            if keep_lease
            else revoke_lease()
        )

    finished_at = utc_now()

    stdout_path = (
        run_root
        / "stdout.log"
    )

    stderr_path = (
        run_root
        / "stderr.log"
    )

    atomic_write_text(
        stdout_path,
        completed.stdout,
    )

    atomic_write_text(
        stderr_path,
        completed.stderr,
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "guarded-run/1.0.0"
        ),
        "operation": (
            "run_masterplan_guarded"
        ),
        "generated_at": finished_at,
        "started_at": started_at,
        "finished_at": finished_at,
        "agent": agent,
        "task_id": lease.get(
            "task_id"
        ),
        "lease": {
            "path": relative_path(
                LEASE_PATH
            ),
            "lease_id": lease.get(
                "lease_id"
            ),
            "digest": lease.get(
                "digest"
            ),
            "validation": validation,
            "kept": keep_lease,
            "revocation": revocation,
        },
        "authorization": lease.get(
            "authorization"
        ),
        "command": command,
        "command_shell": shlex.join(
            command
        ),
        "returncode": completed.returncode,
        "passed": (
            completed.returncode == 0
        ),
        "stdout": {
            "path": relative_path(
                stdout_path
            ),
            "sha256": sha256_path(
                stdout_path
            ),
            "byte_count": (
                stdout_path.stat().st_size
            ),
        },
        "stderr": {
            "path": relative_path(
                stderr_path
            ),
            "sha256": sha256_path(
                stderr_path
            ),
            "byte_count": (
                stderr_path.stat().st_size
            ),
        },
        "run_root": relative_path(
            run_root
        ),
    }

    result["digest"] = digest(
        deterministic_projection(
            result
        )
    )

    atomic_write_json(
        run_root
        / "result.json",
        result,
    )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(
        REPORT_ROOT
        / f"{run_id}__guarded-run.json",
        result,
    )

    atomic_write_json(
        REPORT_ROOT
        / "latest.json",
        result,
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a command only after the "
            "Masterplan grants a valid path lease."
        )
    )

    parser.add_argument(
        "--agent",
        required=True,
    )

    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        required=True,
    )

    parser.add_argument(
        "--ttl-minutes",
        type=int,
        default=60,
    )

    parser.add_argument(
        "--no-refresh",
        action="store_true",
    )

    parser.add_argument(
        "--keep-lease",
        action="store_true",
    )

    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
    )

    arguments = parser.parse_args()

    command = list(
        arguments.command
    )

    if (
        command
        and command[0] == "--"
    ):
        command = command[1:]

    try:
        if arguments.ttl_minutes < 1:
            raise ValueError(
                "Lease TTL must be at least one minute."
            )

        result = run_guarded(
            agent=arguments.agent,
            paths=arguments.paths,
            command=command,
            ttl_minutes=arguments.ttl_minutes,
            refresh=(
                not arguments.no_refresh
            ),
            keep_lease=arguments.keep_lease,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "run_masterplan_guarded"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result["passed"]
        else result["returncode"] or 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
