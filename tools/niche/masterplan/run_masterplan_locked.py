#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

SUBJECT_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
)

RUNTIME_ROOT = (
    SUBJECT_ROOT
    / "runtime"
)

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )


from masterplan_lock import (  # noqa: E402
    GRAPH_PATH,
    MasterplanLock,
    MasterplanLockError,
    deterministic_projection,
    digest,
    graph_digest,
)


RUN_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "locked-runs"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "locked-runs"
)

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
    "acquired_at",
    "released_at",
    "heartbeat_at",
    "expires_at",
}


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def semantic_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(
                value
            )
        )
    ).hexdigest()


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
            hasher.update(
                chunk
            )

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
        dir=str(
            path.parent
        ),
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
            handle.write(
                value
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

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


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(
            path
        )


def validate_command(
    command: list[str],
) -> None:
    if not command:
        raise ValueError(
            "A locked command is required."
        )

    executable = command[0]

    if "/" in executable:
        path = Path(
            executable
        ).expanduser()

        if not path.is_absolute():
            path = (
                ROOT
                / path
            ).resolve()

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if not os.access(
            path,
            os.X_OK,
        ):
            raise PermissionError(
                f"Command is not executable: {path}"
            )


def run_command(
    command: list[str],
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(
            ROOT
        ),
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def build_environment(
    lock: MasterplanLock,
    pre_graph_digest: str | None,
) -> dict[str, str]:
    environment = dict(
        os.environ
    )

    environment[
        "SAVANT_MASTERPLAN_LOCKED"
    ] = "1"

    environment[
        "SAVANT_MASTERPLAN_LOCK_ID"
    ] = str(
        lock._lock_id
        or ""
    )

    environment[
        "SAVANT_MASTERPLAN_LOCK_OWNER"
    ] = lock.owner

    environment[
        "SAVANT_MASTERPLAN_OPERATION"
    ] = lock.operation

    environment[
        "SAVANT_MASTERPLAN_EXPECTED_DIGEST"
    ] = (
        pre_graph_digest
        or ""
    )

    return environment


def run_locked(
    *,
    owner: str,
    operation: str,
    command: list[str],
    expected_graph_digest: str | None,
    timeout_seconds: float,
    poll_seconds: float,
    lease_seconds: int,
    require_graph_change: bool,
    forbid_graph_change: bool,
) -> dict[str, Any]:
    validate_command(
        command
    )

    if (
        require_graph_change
        and forbid_graph_change
    ):
        raise ValueError(
            "Graph change cannot be both required and forbidden."
        )

    pre_graph_digest = (
        graph_digest(
            GRAPH_PATH
        )
        if GRAPH_PATH.is_file()
        else None
    )

    if (
        expected_graph_digest
        is not None
        and expected_graph_digest
        != pre_graph_digest
    ):
        raise RuntimeError(
            json.dumps(
                {
                    "code": (
                        "masterplan.lock."
                        "expected_digest_mismatch"
                    ),
                    "expected_graph_digest": (
                        expected_graph_digest
                    ),
                    "actual_graph_digest": (
                        pre_graph_digest
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    run_seed = {
        "owner": owner,
        "operation": operation,
        "command": command,
        "pre_graph_digest": (
            pre_graph_digest
        ),
    }

    run_id = (
        f"{timestamp()}__"
        f"{semantic_digest(run_seed)[:16]}"
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

    lock = MasterplanLock(
        owner=owner,
        operation=operation,
        expected_graph_digest=(
            pre_graph_digest
        ),
        timeout_seconds=(
            timeout_seconds
        ),
        poll_seconds=(
            poll_seconds
        ),
        lease_seconds=(
            lease_seconds
        ),
    )

    lock.acquire()

    completed: (
        subprocess.CompletedProcess[str]
        | None
    ) = None

    failure: dict[str, Any] | None = None

    try:
        lock.validate_graph_precondition()

        environment = build_environment(
            lock,
            pre_graph_digest,
        )

        completed = run_command(
            command,
            environment,
        )

        post_graph_digest = (
            graph_digest(
                GRAPH_PATH
            )
            if GRAPH_PATH.is_file()
            else None
        )

        graph_changed = (
            pre_graph_digest
            != post_graph_digest
        )

        policy_passed = True
        policy_failure = None

        if (
            require_graph_change
            and not graph_changed
        ):
            policy_passed = False
            policy_failure = (
                "masterplan.lock."
                "required_graph_change_missing"
            )

        if (
            forbid_graph_change
            and graph_changed
        ):
            policy_passed = False
            policy_failure = (
                "masterplan.lock."
                "forbidden_graph_change_detected"
            )

        passed = (
            completed.returncode
            == 0
            and policy_passed
        )

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
                "locked-run/1.0.0"
            ),
            "operation": (
                "run_masterplan_locked"
            ),
            "generated_at": utc_now(),
            "started_at": started_at,
            "finished_at": utc_now(),
            "passed": passed,
            "owner": owner,
            "guarded_operation": (
                operation
            ),
            "lock": {
                "lock_id": (
                    lock._lock_id
                ),
                "owner": lock.owner,
                "operation": (
                    lock.operation
                ),
                "pre_graph_digest": (
                    pre_graph_digest
                ),
                "post_graph_digest": (
                    post_graph_digest
                ),
            },
            "command": command,
            "command_shell": shlex.join(
                command
            ),
            "returncode": (
                completed.returncode
            ),
            "graph_changed": (
                graph_changed
            ),
            "graph_change_policy": {
                "require_graph_change": (
                    require_graph_change
                ),
                "forbid_graph_change": (
                    forbid_graph_change
                ),
                "passed": (
                    policy_passed
                ),
                "failure_code": (
                    policy_failure
                ),
            },
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

        result[
            "semantic_digest"
        ] = semantic_digest(
            result
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
            / f"{run_id}__locked-run.json",
            result,
        )

        atomic_write_json(
            REPORT_ROOT
            / "latest.json",
            result,
        )

        lock.release(
            passed=passed,
            post_graph_digest=(
                post_graph_digest
            ),
            failure_code=(
                None
                if passed
                else (
                    policy_failure
                    or (
                        "masterplan.lock."
                        "command_failed"
                    )
                )
            ),
        )

        return result

    except Exception as exc:
        failure = {
            "type": type(
                exc
            ).__name__,
            "message": str(
                exc
            ),
        }

        post_graph_digest = (
            graph_digest(
                GRAPH_PATH
            )
            if GRAPH_PATH.is_file()
            else None
        )

        lock.release(
            passed=False,
            post_graph_digest=(
                post_graph_digest
            ),
            failure_code=(
                "masterplan.lock."
                "guarded_operation_failed"
            ),
        )

        result = {
            "schema": (
                "savant://niche/masterplan/"
                "locked-run/1.0.0"
            ),
            "operation": (
                "run_masterplan_locked"
            ),
            "generated_at": utc_now(),
            "started_at": started_at,
            "finished_at": utc_now(),
            "passed": False,
            "owner": owner,
            "guarded_operation": (
                operation
            ),
            "command": command,
            "command_shell": shlex.join(
                command
            ),
            "lock": {
                "lock_id": (
                    lock._lock_id
                ),
                "pre_graph_digest": (
                    pre_graph_digest
                ),
                "post_graph_digest": (
                    post_graph_digest
                ),
            },
            "failure": failure,
            "run_root": relative_path(
                run_root
            ),
        }

        result[
            "semantic_digest"
        ] = semantic_digest(
            result
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
            / f"{run_id}__locked-run.json",
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
            "Execute a Masterplan mutation under "
            "exclusive graph locking and stale-write protection."
        )
    )

    parser.add_argument(
        "--owner",
        required=True,
    )

    parser.add_argument(
        "--operation",
        required=True,
    )

    parser.add_argument(
        "--expected-graph-digest",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
    )

    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=0.1,
    )

    parser.add_argument(
        "--lease-seconds",
        type=int,
        default=300,
    )

    parser.add_argument(
        "--require-graph-change",
        action="store_true",
    )

    parser.add_argument(
        "--forbid-graph-change",
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
        and command[0]
        == "--"
    ):
        command = command[
            1:
        ]

    try:
        if (
            arguments.timeout_seconds
            < 0
        ):
            raise ValueError(
                "Lock timeout cannot be negative."
            )

        if (
            arguments.poll_seconds
            <= 0
        ):
            raise ValueError(
                "Lock poll interval must be positive."
            )

        if (
            arguments.lease_seconds
            < 1
        ):
            raise ValueError(
                "Lock lease must be at least one second."
            )

        result = run_locked(
            owner=arguments.owner,
            operation=(
                arguments.operation
            ),
            command=command,
            expected_graph_digest=(
                arguments.expected_graph_digest
            ),
            timeout_seconds=(
                arguments.timeout_seconds
            ),
            poll_seconds=(
                arguments.poll_seconds
            ),
            lease_seconds=(
                arguments.lease_seconds
            ),
            require_graph_change=(
                arguments.require_graph_change
            ),
            forbid_graph_change=(
                arguments.forbid_graph_change
            ),
        )

    except (
        MasterplanLockError,
        Exception,
    ) as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "run_masterplan_locked"
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

    if result[
        "passed"
    ]:
        return 0

    return int(
        result.get(
            "returncode",
            1,
        )
        or 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
