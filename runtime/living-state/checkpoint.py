#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from typing import Any


runtime_root = Path("/root/savant-runtime")
living_root = runtime_root / "runtime" / "living-state"

current_path = living_root / "current.json"
policy_path = living_root / "checkpoint-policy.json"

state_root = Path("/var/lib/savant/living-state-checkpoint")
state_path = state_root / "state.json"
journal_path = state_root / "journal.jsonl"
lock_path = state_root / "checkpoint.lock"
force_path = state_root / "force"

schema = "savant.living-state.checkpoint.v1"

stop_event = threading.Event()


default_policy: dict[str, Any] = {
    "schema": "savant.living-state.checkpoint-policy.v1",
    "enabled": True,
    "runtime_root": "/root/savant-runtime",
    "sdump_command": "/usr/local/bin/sdump",
    "workers": 16,
    "keep_local": False,
    "quiet_seconds": 90,
    "priority_quiet_seconds": 30,
    "maximum_quiet_seconds": 900,
    "minimum_checkpoint_interval_seconds": 3600,
    "maximum_checkpoint_interval_seconds": 21600,
    "score_threshold": 8,
    "priority_score_threshold": 20,
    "maximum_pending_paths": 2048,
    "minimum_free_disk_bytes": 2147483648,
    "maximum_load_per_cpu": 2.0,
    "checkpoint_timeout_seconds": 1800,
    "failure_backoff_initial_seconds": 60,
    "failure_backoff_maximum_seconds": 3600,
    "poll_fallback_seconds": 5,
    "generated_path_prefixes": [
        "source/",
        "exports/",
        "audit/",
        "_reports/",
        "repair_backups/",
        "relics/",
        "runtime/living-state/",
        "vault/sdump-receipts/",
        "vault/sdump/",
    ],
    "generated_path_suffixes": [
        "-shm",
        "-wal",
        "-journal",
        ".sqlite-shm",
        ".sqlite-wal",
        ".sqlite-journal",
        ".sqlite3-shm",
        ".sqlite3-wal",
        ".sqlite3-journal",
        ".db-shm",
        ".db-wal",
        ".db-journal",
        ".tmp",
        ".swp",
        ".swx",
        "~",
    ],
    "priority_path_prefixes": [
        "authority/",
        "canon/",
        "canon-system/",
        "ontology/",
        "tools/sdump-enterprise/",
        "runtime/",
    ],
}


def compact_json(value: Any) -> str:
    try:
        import orjson

        return orjson.dumps(
            value,
            option=orjson.OPT_SORT_KEYS,
        ).decode("utf-8")

    except ImportError:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def stable_hash(value: Any) -> str:
    payload = compact_json(value).encode("utf-8")

    try:
        import blake3

        return "blake3:" + blake3.blake3(payload).hexdigest()

    except ImportError:
        return "sha256:" + hashlib.sha256(payload).hexdigest()


def read_json(
    path: Path,
    default: Any = None,
) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return default


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=str(path.parent),
    )

    temporary = Path(name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                compact_json(value)
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary,
            0o600,
        )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def append_journal(
    event: dict[str, Any],
) -> None:
    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with journal_path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            compact_json(event)
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_policy() -> dict[str, Any]:
    policy = dict(default_policy)

    supplied = read_json(
        policy_path,
        {},
    )

    if isinstance(
        supplied,
        dict,
    ):
        policy.update(
            supplied
        )

    return policy


def initial_state() -> dict[str, Any]:
    now = time.time_ns()

    return {
        "schema":
            schema,
        "projection_only":
            True,
        "authority_effect":
            "none",
        "running":
            True,
        "started_at_unix_ns":
            now,
        "updated_at_unix_ns":
            now,

        "last_seen_sequence":
            None,
        "last_seen_snapshot_hash":
            None,

        "baseline_snapshot_hash":
            None,

        "last_material_snapshot_hash":
            None,

        "last_checkpoint_snapshot_hash":
            None,
        "last_checkpoint_at_unix_ns":
            None,
        "last_checkpoint_artifact":
            None,
        "last_checkpoint_sha256":
            None,
        "last_checkpoint_s3":
            None,
        "last_checkpoint_receipt":
            None,
        "last_checkpoint_reason":
            None,

        "pending":
            False,
        "pending_since_unix_ns":
            None,
        "last_material_change_unix_ns":
            None,
        "pending_score":
            0,
        "pending_paths":
            [],
        "pending_fingerprint":
            None,

        "checkpoint_running":
            False,
        "checkpoint_pid":
            None,

        "success_count":
            0,
        "failure_count":
            0,
        "consecutive_failures":
            0,
        "next_retry_at_unix_ns":
            None,
        "last_error":
            None,

        "ignored_transient_change_count":
            0,

        "last_decision":
            "startup",
    }


def load_state() -> dict[str, Any]:
    existing = read_json(
        state_path
    )

    if not isinstance(
        existing,
        dict,
    ):
        return initial_state()

    state = initial_state()
    state.update(existing)

    state["running"] = True
    state["checkpoint_running"] = False
    state["checkpoint_pid"] = None
    state["updated_at_unix_ns"] = (
        time.time_ns()
    )

    return state


def persist_state(
    state: dict[str, Any],
) -> None:
    state["updated_at_unix_ns"] = (
        time.time_ns()
    )

    atomic_write_json(
        state_path,
        state,
    )


def normalize_path(
    value: Any,
) -> str | None:
    if not isinstance(
        value,
        str,
    ):
        return None

    value = value.replace(
        "\\",
        "/",
    )

    while value.startswith("./"):
        value = value[2:]

    return value or None


def delta_paths(
    snapshot: dict[str, Any],
) -> list[str]:
    delta = snapshot.get(
        "delta"
    )

    if not isinstance(
        delta,
        dict,
    ):
        return []

    paths: set[str] = set()

    for key in (
        "added",
        "changed",
        "deleted",
    ):
        values = delta.get(
            key,
            [],
        )

        if not isinstance(
            values,
            list,
        ):
            continue

        for value in values:
            path = normalize_path(
                value
            )

            if path:
                paths.add(path)

    return sorted(
        paths,
        key=str.casefold,
    )


def is_generated(
    path: str,
    policy: dict[str, Any],
) -> bool:
    lowered = path.casefold()

    for prefix in policy.get(
        "generated_path_prefixes",
        [],
    ):
        if lowered.startswith(
            str(prefix).casefold()
        ):
            return True

    for suffix in policy.get(
        "generated_path_suffixes",
        [],
    ):
        if lowered.endswith(
            str(suffix).casefold()
        ):
            return True

    return False


def path_weight(
    path: str,
    policy: dict[str, Any],
) -> int:
    lowered = path.casefold()
    weight = 1

    for prefix in policy.get(
        "priority_path_prefixes",
        [],
    ):
        if lowered.startswith(
            str(prefix).casefold()
        ):
            weight = max(
                weight,
                5,
            )

    if lowered.endswith(
        (
            ".service",
            ".socket",
            ".timer",
            ".path",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".py",
            ".sh",
            ".bash",
            ".ts",
            ".tsx",
            ".js",
            ".mjs",
            ".cjs",
        )
    ):
        weight += 1

    return weight


def classify_change(
    snapshot: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    list[str],
    list[str],
    int,
]:
    material: list[str] = []
    transient: list[str] = []

    for path in delta_paths(
        snapshot
    ):
        if is_generated(
            path,
            policy,
        ):
            transient.append(
                path
            )
        else:
            material.append(
                path
            )

    score = sum(
        path_weight(
            path,
            policy,
        )
        for path in material
    )

    return (
        material,
        transient,
        score,
    )


def clear_pending(
    state: dict[str, Any],
) -> None:
    state["pending"] = False
    state["pending_since_unix_ns"] = None
    state[
        "last_material_change_unix_ns"
    ] = None
    state["pending_score"] = 0
    state["pending_paths"] = []
    state["pending_fingerprint"] = None


def normalize_pending(
    state: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    existing = [
        normalize_path(value)
        for value in state.get(
            "pending_paths",
            [],
        )
    ]

    material = sorted(
        {
            path
            for path in existing
            if (
                path
                and not is_generated(
                    path,
                    policy,
                )
            )
        },
        key=str.casefold,
    )

    if not material:
        clear_pending(
            state
        )

        if state.get(
            "last_decision"
        ) not in {
            "startup",
            "checkpoint_completed",
        }:
            state[
                "last_decision"
            ] = (
                "transient_pending_normalized"
            )

        return

    state["pending"] = True
    state["pending_paths"] = material

    state[
        "pending_fingerprint"
    ] = stable_hash(
        material
    )

    state["pending_score"] = sum(
        path_weight(
            path,
            policy,
        )
        for path in material
    )


def merge_pending(
    state: dict[str, Any],
    paths: list[str],
    score: int,
    policy: dict[str, Any],
) -> None:
    if not paths:
        return

    now = time.time_ns()

    existing = {
        str(value)
        for value in state.get(
            "pending_paths",
            [],
        )
        if isinstance(
            value,
            str,
        )
    }

    existing.update(
        paths
    )

    existing = {
        path
        for path in existing
        if not is_generated(
            path,
            policy,
        )
    }

    limit = max(
        1,
        int(
            policy.get(
                "maximum_pending_paths",
                2048,
            )
        ),
    )

    ordered = sorted(
        existing,
        key=str.casefold,
    )[:limit]

    if not ordered:
        clear_pending(
            state
        )
        return

    if not state.get(
        "pending"
    ):
        state[
            "pending_since_unix_ns"
        ] = now

    state["pending"] = True

    state[
        "last_material_change_unix_ns"
    ] = now

    state[
        "pending_score"
    ] = (
        int(
            state.get(
                "pending_score",
                0,
            )
        )
        + score
    )

    state["pending_paths"] = ordered

    state[
        "pending_fingerprint"
    ] = stable_hash(
        ordered
    )


def seconds_since_ns(
    value: Any,
) -> float | None:
    if not isinstance(
        value,
        int,
    ):
        return None

    return max(
        0.0,
        (
            time.time_ns()
            - value
        )
        / 1_000_000_000,
    )


def resource_gate(
    policy: dict[str, Any],
) -> tuple[
    bool,
    str,
]:
    free = shutil.disk_usage(
        runtime_root
    ).free

    minimum_free = int(
        policy.get(
            "minimum_free_disk_bytes",
            0,
        )
    )

    if free < minimum_free:
        return (
            False,
            "insufficient_disk",
        )

    try:
        load = os.getloadavg()[0]

        maximum = (
            float(
                policy.get(
                    "maximum_load_per_cpu",
                    2.0,
                )
            )
            * max(
                1,
                os.cpu_count()
                or 1,
            )
        )

        if load > maximum:
            return (
                False,
                "load_pressure",
            )

    except OSError:
        pass

    return (
        True,
        "ready",
    )


def retry_allowed(
    state: dict[str, Any],
) -> bool:
    retry = state.get(
        "next_retry_at_unix_ns"
    )

    return (
        not isinstance(
            retry,
            int,
        )
        or time.time_ns()
        >= retry
    )


def checkpoint_decision(
    state: dict[str, Any],
    policy: dict[str, Any],
    *,
    force: bool = False,
) -> tuple[
    bool,
    str,
]:
    if force:
        return (
            True,
            "manual_force",
        )

    if not bool(
        policy.get(
            "enabled",
            True,
        )
    ):
        return (
            False,
            "disabled",
        )

    if not state.get(
        "pending"
    ):
        return (
            False,
            "no_material_change",
        )

    if not retry_allowed(
        state
    ):
        return (
            False,
            "failure_backoff",
        )

    checkpoint_age = (
        seconds_since_ns(
            state.get(
                "last_checkpoint_at_unix_ns"
            )
        )
    )

    if (
        checkpoint_age
        is not None
        and checkpoint_age
        < float(
            policy.get(
                "minimum_checkpoint_interval_seconds",
                3600,
            )
        )
    ):
        return (
            False,
            "minimum_interval",
        )

    pending_age = (
        seconds_since_ns(
            state.get(
                "pending_since_unix_ns"
            )
        )
        or 0.0
    )

    quiet_age = (
        seconds_since_ns(
            state.get(
                "last_material_change_unix_ns"
            )
        )
        or 0.0
    )

    score = int(
        state.get(
            "pending_score",
            0,
        )
    )

    if (
        checkpoint_age is not None
        and checkpoint_age
        >= float(
            policy.get(
                "maximum_checkpoint_interval_seconds",
                21600,
            )
        )
    ):
        return (
            True,
            "maximum_age",
        )

    if pending_age >= float(
        policy.get(
            "maximum_quiet_seconds",
            900,
        )
    ):
        return (
            True,
            "maximum_quiescence_wait",
        )

    if (
        score
        >= int(
            policy.get(
                "priority_score_threshold",
                20,
            )
        )
        and quiet_age
        >= float(
            policy.get(
                "priority_quiet_seconds",
                30,
            )
        )
    ):
        return (
            True,
            "priority_quiescence",
        )

    base_quiet = float(
        policy.get(
            "quiet_seconds",
            90,
        )
    )

    burst_factor = min(
        4.0,
        1.0
        + (
            len(
                state.get(
                    "pending_paths",
                    [],
                )
            )
            / 100.0
        ),
    )

    adaptive_quiet = min(
        float(
            policy.get(
                "maximum_quiet_seconds",
                900,
            )
        ),
        base_quiet
        * burst_factor,
    )

    if (
        score
        >= int(
            policy.get(
                "score_threshold",
                8,
            )
        )
        and quiet_age
        >= adaptive_quiet
    ):
        return (
            True,
            "adaptive_quiescence",
        )

    return (
        False,
        "accumulating",
    )


def parse_summary(
    stdout: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for line in stdout.splitlines():
        key, separator, value = (
            line.partition(
                ": "
            )
        )

        if not separator:
            continue

        if key in {
            "output",
            "sha256",
            "receipt",
            "snapshot_hash",
        }:
            result[key] = value.strip()

        elif key == "s3":
            try:
                result["s3"] = (
                    json.loads(value)
                )

            except json.JSONDecodeError:
                result["s3"] = {
                    "raw": value,
                }

    return result


def schedule_backoff(
    state: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    failures = int(
        state.get(
            "consecutive_failures",
            0,
        )
    )

    initial = float(
        policy.get(
            "failure_backoff_initial_seconds",
            60,
        )
    )

    maximum = float(
        policy.get(
            "failure_backoff_maximum_seconds",
            3600,
        )
    )

    delay = min(
        maximum,
        initial
        * (
            2
            ** max(
                0,
                failures - 1,
            )
        ),
    )

    state[
        "next_retry_at_unix_ns"
    ] = (
        time.time_ns()
        + int(
            delay
            * 1_000_000_000
        )
    )


def run_checkpoint(
    state: dict[str, Any],
    policy: dict[str, Any],
    reason: str,
) -> bool:
    ready, resource_reason = (
        resource_gate(
            policy
        )
    )

    if not ready:
        state[
            "last_decision"
        ] = resource_reason

        persist_state(
            state
        )

        return False

    command = [
        str(
            policy.get(
                "sdump_command",
                "/usr/local/bin/sdump",
            )
        ),
        "dump",
        str(
            policy.get(
                "runtime_root",
                "/root/savant-runtime",
            )
        ),
        "--workers",
        str(
            int(
                policy.get(
                    "workers",
                    16,
                )
            )
        ),
    ]

    if bool(
        policy.get(
            "keep_local",
            False,
        )
    ):
        command.append(
            "--keep-local"
        )

    state["checkpoint_running"] = True
    state["checkpoint_pid"] = None

    state[
        "last_decision"
    ] = (
        "checkpoint:"
        + reason
    )

    persist_state(
        state
    )

    started = time.time_ns()

    append_journal(
        {
            "schema":
                "savant.living-state.checkpoint-event.v1",
            "event":
                "checkpoint_started",
            "reason":
                reason,
            "started_at_unix_ns":
                started,
            "living_snapshot_hash":
                state.get(
                    "last_material_snapshot_hash"
                ),
            "pending_fingerprint":
                state.get(
                    "pending_fingerprint"
                ),
            "pending_score":
                state.get(
                    "pending_score"
                ),
        }
    )

    process: subprocess.Popen[str] | None = (
        None
    )

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(runtime_root),
            env=os.environ.copy(),
        )

        state[
            "checkpoint_pid"
        ] = process.pid

        persist_state(
            state
        )

        stdout, stderr = (
            process.communicate(
                timeout=float(
                    policy.get(
                        "checkpoint_timeout_seconds",
                        1800,
                    )
                )
            )
        )

        if process.returncode != 0:
            raise RuntimeError(
                (
                    "sdump exited "
                    f"{process.returncode}: "
                    f"{stderr[-4000:]}"
                )
            )

        summary = parse_summary(
            stdout
        )

        s3 = summary.get(
            "s3"
        )

        if not (
            isinstance(
                s3,
                dict,
            )
            and s3.get(
                "uploaded"
            )
            is True
            and s3.get(
                "verified"
            )
            is True
        ):
            raise RuntimeError(
                "sdump did not report verified upload"
            )

        now = time.time_ns()

        state[
            "last_checkpoint_at_unix_ns"
        ] = now

        state[
            "last_checkpoint_snapshot_hash"
        ] = state.get(
            "last_material_snapshot_hash"
        )

        state[
            "last_checkpoint_artifact"
        ] = summary.get(
            "output"
        )

        state[
            "last_checkpoint_sha256"
        ] = summary.get(
            "sha256"
        )

        state[
            "last_checkpoint_s3"
        ] = s3

        state[
            "last_checkpoint_receipt"
        ] = summary.get(
            "receipt"
        )

        state[
            "last_checkpoint_reason"
        ] = reason

        state["success_count"] = (
            int(
                state.get(
                    "success_count",
                    0,
                )
            )
            + 1
        )

        state[
            "consecutive_failures"
        ] = 0

        state[
            "next_retry_at_unix_ns"
        ] = None

        state[
            "last_error"
        ] = None

        state[
            "last_decision"
        ] = "checkpoint_completed"

        clear_pending(
            state
        )

        append_journal(
            {
                "schema":
                    "savant.living-state.checkpoint-event.v1",
                "event":
                    "checkpoint_completed",
                "reason":
                    reason,
                "finished_at_unix_ns":
                    now,
                "duration_seconds":
                    (
                        now
                        - started
                    )
                    / 1_000_000_000,
                "artifact":
                    summary.get(
                        "output"
                    ),
                "sha256":
                    summary.get(
                        "sha256"
                    ),
                "s3":
                    s3,
                "receipt":
                    summary.get(
                        "receipt"
                    ),
            }
        )

        return True

    except subprocess.TimeoutExpired:
        if process is not None:
            try:
                process.kill()

            except Exception:
                pass

        state[
            "last_error"
        ] = "checkpoint_timeout"

    except Exception as error:
        state[
            "last_error"
        ] = (
            type(
                error
            ).__name__
            + ": "
            + str(
                error
            )
        )

    state["failure_count"] = (
        int(
            state.get(
                "failure_count",
                0,
            )
        )
        + 1
    )

    state[
        "consecutive_failures"
    ] = (
        int(
            state.get(
                "consecutive_failures",
                0,
            )
        )
        + 1
    )

    schedule_backoff(
        state,
        policy,
    )

    state[
        "last_decision"
    ] = "checkpoint_failed"

    append_journal(
        {
            "schema":
                "savant.living-state.checkpoint-event.v1",
            "event":
                "checkpoint_failed",
            "reason":
                reason,
            "finished_at_unix_ns":
                time.time_ns(),
            "error":
                state.get(
                    "last_error"
                ),
            "consecutive_failures":
                state.get(
                    "consecutive_failures"
                ),
            "next_retry_at_unix_ns":
                state.get(
                    "next_retry_at_unix_ns"
                ),
        }
    )

    return False


def finalize_checkpoint_state(
    state: dict[str, Any],
) -> None:
    state["checkpoint_running"] = False
    state["checkpoint_pid"] = None

    persist_state(
        state
    )


def process_snapshot(
    state: dict[str, Any],
    policy: dict[str, Any],
    *,
    startup: bool = False,
) -> None:
    snapshot = read_json(
        current_path
    )

    if not isinstance(
        snapshot,
        dict,
    ):
        state[
            "last_decision"
        ] = "living_state_unavailable"

        persist_state(
            state
        )

        return

    snapshot_hash = snapshot.get(
        "snapshot_hash"
    )

    sequence = snapshot.get(
        "sequence"
    )

    state[
        "last_seen_snapshot_hash"
    ] = snapshot_hash

    state[
        "last_seen_sequence"
    ] = sequence

    material, transient, score = (
        classify_change(
            snapshot,
            policy,
        )
    )

    if transient:
        state[
            "ignored_transient_change_count"
        ] = (
            int(
                state.get(
                    "ignored_transient_change_count",
                    0,
                )
            )
            + len(
                transient
            )
        )

    if startup:
        normalize_pending(
            state,
            policy,
        )

        if (
            state.get(
                "baseline_snapshot_hash"
            )
            is None
        ):
            state[
                "baseline_snapshot_hash"
            ] = snapshot_hash

        state[
            "last_decision"
        ] = (
            "startup_baseline"
            if not state.get(
                "pending"
            )
            else "startup_pending_restored"
        )

        persist_state(
            state
        )

        return

    if material:
        state[
            "last_material_snapshot_hash"
        ] = snapshot_hash

        merge_pending(
            state,
            material,
            score,
            policy,
        )

        state[
            "last_decision"
        ] = "material_change"

        append_journal(
            {
                "schema":
                    "savant.living-state.checkpoint-event.v1",
                "event":
                    "material_change",
                "sequence":
                    sequence,
                "snapshot_hash":
                    snapshot_hash,
                "score":
                    score,
                "paths":
                    material[:100],
                "path_count":
                    len(
                        material
                    ),
                "transient_ignored":
                    len(
                        transient
                    ),
            }
        )

    elif transient:
        state[
            "last_decision"
        ] = "transient_change_ignored"

    else:
        state[
            "last_decision"
        ] = "empty_delta"

    persist_state(
        state
    )


def maybe_process_current(
    state: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    snapshot = read_json(
        current_path
    )

    if not isinstance(
        snapshot,
        dict,
    ):
        return

    snapshot_hash = snapshot.get(
        "snapshot_hash"
    )

    if (
        snapshot_hash
        == state.get(
            "last_seen_snapshot_hash"
        )
    ):
        return

    process_snapshot(
        state,
        policy,
    )


def maybe_checkpoint(
    state: dict[str, Any],
    policy: dict[str, Any],
    *,
    force: bool = False,
) -> bool:
    normalize_pending(
        state,
        policy,
    )

    should_run, reason = (
        checkpoint_decision(
            state,
            policy,
            force=force,
        )
    )

    state[
        "last_decision"
    ] = reason

    persist_state(
        state
    )

    if not should_run:
        return False

    try:
        return run_checkpoint(
            state,
            policy,
            reason,
        )

    finally:
        finalize_checkpoint_state(
            state
        )


def acquire_lock() -> int:
    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor = os.open(
        lock_path,
        os.O_CREAT
        | os.O_RDWR,
        0o600,
    )

    try:
        fcntl.flock(
            descriptor,
            fcntl.LOCK_EX
            | fcntl.LOCK_NB,
        )

    except BlockingIOError as error:
        os.close(
            descriptor
        )

        raise RuntimeError(
            "checkpoint engine already running"
        ) from error

    os.ftruncate(
        descriptor,
        0,
    )

    os.write(
        descriptor,
        str(
            os.getpid()
        ).encode(
            "ascii"
        ),
    )

    return descriptor


def signal_handler(
    signum: int,
    frame: Any,
) -> None:
    del signum
    del frame

    stop_event.set()


def event_loop() -> int:
    policy = load_policy()
    state = load_state()

    process_snapshot(
        state,
        policy,
        startup=True,
    )

    try:
        from watchfiles import watch

        for changes in watch(
            living_root,
            stop_event=stop_event,
            debounce=500,
            step=250,
            recursive=False,
            yield_on_timeout=True,
            rust_timeout=5000,
        ):
            if stop_event.is_set():
                break

            policy = load_policy()

            if any(
                Path(
                    raw_path
                ).name
                == current_path.name
                for _,
                raw_path
                in changes
            ):
                maybe_process_current(
                    state,
                    policy,
                )

            if force_path.exists():
                try:
                    force_path.unlink()

                except OSError:
                    pass

                maybe_checkpoint(
                    state,
                    policy,
                    force=True,
                )

            else:
                maybe_checkpoint(
                    state,
                    policy,
                )

    except ImportError:
        previous_mtime = None

        while not stop_event.wait(
            max(
                1.0,
                float(
                    policy.get(
                        "poll_fallback_seconds",
                        5,
                    )
                ),
            )
        ):
            policy = load_policy()

            try:
                mtime = (
                    current_path
                    .stat()
                    .st_mtime_ns
                )

            except OSError:
                mtime = None

            if mtime != previous_mtime:
                previous_mtime = mtime

                maybe_process_current(
                    state,
                    policy,
                )

            if force_path.exists():
                try:
                    force_path.unlink()

                except OSError:
                    pass

                maybe_checkpoint(
                    state,
                    policy,
                    force=True,
                )

            else:
                maybe_checkpoint(
                    state,
                    policy,
                )

    state["running"] = False
    state["last_decision"] = "stopped"

    persist_state(
        state
    )

    return 0


def status() -> int:
    state = read_json(
        state_path
    )

    if not isinstance(
        state,
        dict,
    ):
        print(
            compact_json(
                {
                    "schema":
                        schema,
                    "available":
                        False,
                }
            )
        )

        return 1

    print(
        json.dumps(
            state,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


def force_checkpoint() -> int:
    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    force_path.touch(
        mode=0o600,
        exist_ok=True,
    )

    print(
        compact_json(
            {
                "requested":
                    True,
                "path":
                    str(
                        force_path
                    ),
            }
        )
    )

    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="savant-living-checkpoint"
    )

    value.add_argument(
        "--status",
        action="store_true",
    )

    value.add_argument(
        "--force",
        action="store_true",
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    state_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if arguments.status:
        return status()

    if arguments.force:
        return force_checkpoint()

    descriptor = acquire_lock()

    signal.signal(
        signal.SIGTERM,
        signal_handler,
    )

    signal.signal(
        signal.SIGINT,
        signal_handler,
    )

    try:
        return event_loop()

    finally:
        os.close(
            descriptor
        )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
