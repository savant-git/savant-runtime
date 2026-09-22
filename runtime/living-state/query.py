#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


state_root = Path(
    "/root/savant-runtime/runtime/living-state"
)

current_path = (
    state_root
    / "current.json"
)

health_path = (
    state_root
    / "health.json"
)

journal_path = (
    state_root
    / "journal.jsonl"
)

checkpoint_state_path = Path(
    "/var/lib/savant/living-state-checkpoint/state.json"
)

living_service = (
    "savant-living-state.service"
)

checkpoint_service = (
    "savant-living-checkpoint.service"
)


def read_json(
    path: Path,
) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def read_json_dict(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        return {}

    try:
        value = read_json(
            path
        )

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return {}

    return (
        value
        if isinstance(
            value,
            dict,
        )
        else {}
    )


def dotted_get(
    value: Any,
    dotted: str,
) -> Any:
    current = value

    for component in dotted.split(
        "."
    ):
        if not isinstance(
            current,
            dict,
        ):
            raise KeyError(
                dotted
            )

        current = current[
            component
        ]

    return current


def service_state(
    service: str,
) -> str:
    try:
        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                service,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=3.0,
        )

    except Exception:
        return "unknown"

    value = result.stdout.strip()

    return (
        value
        or "unknown"
    )


def age_seconds(
    unix_ns: Any,
) -> float | None:
    if not isinstance(
        unix_ns,
        int,
    ):
        return None

    return max(
        0.0,
        (
            time.time_ns()
            - unix_ns
        )
        / 1_000_000_000,
    )


def retry_waiting(
    checkpoint: dict[str, Any],
) -> bool:
    if checkpoint.get(
        "pending"
    ) is not True:
        return False

    retry_at = checkpoint.get(
        "next_retry_at_unix_ns"
    )

    return (
        isinstance(
            retry_at,
            int,
        )
        and retry_at
        > time.time_ns()
    )


def status_projection() -> dict[str, Any]:
    current = read_json_dict(
        current_path
    )

    health = read_json_dict(
        health_path
    )

    checkpoint = read_json_dict(
        checkpoint_state_path
    )

    living_state = service_state(
        living_service
    )

    checkpoint_state = service_state(
        checkpoint_service
    )

    health_age = age_seconds(
        health.get(
            "updated_at_unix_ns"
        )
    )

    checkpoint_age = age_seconds(
        checkpoint.get(
            "last_checkpoint_at_unix_ns"
        )
    )

    checkpoint_state_age = age_seconds(
        checkpoint.get(
            "updated_at_unix_ns"
        )
    )

    living_healthy = (
        living_state
        == "active"
        and health.get(
            "healthy"
        )
        is True
    )

    checkpoint_process_healthy = (
        checkpoint_state
        == "active"
        and checkpoint.get(
            "running"
        )
        is True
    )

    pending = (
        checkpoint.get(
            "pending"
        )
        is True
    )

    checkpoint_running = (
        checkpoint.get(
            "checkpoint_running"
        )
        is True
    )

    blocked_by_backoff = (
        retry_waiting(
            checkpoint
        )
    )

    current_error = (
        checkpoint.get(
            "last_error"
        )
        if (
            pending
            or checkpoint_running
            or blocked_by_backoff
        )
        else None
    )

    autonomous = (
        living_healthy
        and checkpoint_process_healthy
    )

    healthy = (
        autonomous
        and not blocked_by_backoff
        and current_error is None
    )

    status = (
        "on"
        if healthy
        else (
            "degraded"
            if autonomous
            else "off"
        )
    )

    return {
        "schema":
            "savant.living-state.status.v3",
        "projection_only":
            True,
        "authority_effect":
            "none",

        "status":
            status,

        "on":
            healthy,

        "healthy":
            healthy,

        "autonomous":
            autonomous,

        "manual_sdump_required":
            not autonomous,

        "living_state": {
            "service":
                living_service,

            "service_state":
                living_state,

            "healthy":
                living_healthy,

            "sequence":
                current.get(
                    "sequence"
                ),

            "snapshot_hash":
                current.get(
                    "snapshot_hash"
                ),

            "previous_snapshot_hash":
                current.get(
                    "previous_snapshot_hash"
                ),

            "health_age_seconds":
                (
                    round(
                        health_age,
                        3,
                    )
                    if health_age
                    is not None
                    else None
                ),

            "current_path":
                str(
                    current_path
                ),

            "health_path":
                str(
                    health_path
                ),
        },

        "checkpoint": {
            "service":
                checkpoint_service,

            "service_state":
                checkpoint_state,

            "healthy":
                checkpoint_process_healthy
                and not blocked_by_backoff,

            "running":
                checkpoint.get(
                    "running"
                ),

            "checkpoint_running":
                checkpoint_running,

            "checkpoint_pid":
                checkpoint.get(
                    "checkpoint_pid"
                ),

            "pending":
                pending,

            "pending_score":
                checkpoint.get(
                    "pending_score"
                ),

            "pending_paths":
                checkpoint.get(
                    "pending_paths",
                    [],
                ),

            "pending_fingerprint":
                checkpoint.get(
                    "pending_fingerprint"
                ),

            "blocked_by_backoff":
                blocked_by_backoff,

            "last_decision":
                checkpoint.get(
                    "last_decision"
                ),

            "last_checkpoint_reason":
                checkpoint.get(
                    "last_checkpoint_reason"
                ),

            "last_checkpoint_snapshot_hash":
                checkpoint.get(
                    "last_checkpoint_snapshot_hash"
                ),

            "last_checkpoint_artifact":
                checkpoint.get(
                    "last_checkpoint_artifact"
                ),

            "last_checkpoint_sha256":
                checkpoint.get(
                    "last_checkpoint_sha256"
                ),

            "last_checkpoint_s3":
                checkpoint.get(
                    "last_checkpoint_s3"
                ),

            "last_checkpoint_receipt":
                checkpoint.get(
                    "last_checkpoint_receipt"
                ),

            "last_checkpoint_age_seconds":
                (
                    round(
                        checkpoint_age,
                        3,
                    )
                    if checkpoint_age
                    is not None
                    else None
                ),

            "state_age_seconds":
                (
                    round(
                        checkpoint_state_age,
                        3,
                    )
                    if checkpoint_state_age
                    is not None
                    else None
                ),

            "success_count":
                checkpoint.get(
                    "success_count",
                    0,
                ),

            "historical_failure_count":
                checkpoint.get(
                    "failure_count",
                    0,
                ),

            "historical_consecutive_failures":
                checkpoint.get(
                    "consecutive_failures",
                    0,
                ),

            "historical_last_error":
                checkpoint.get(
                    "last_error"
                ),

            "current_error":
                current_error,

            "next_retry_at_unix_ns":
                (
                    checkpoint.get(
                        "next_retry_at_unix_ns"
                    )
                    if blocked_by_backoff
                    else None
                ),

            "ignored_transient_change_count":
                checkpoint.get(
                    "ignored_transient_change_count",
                    0,
                ),

            "state_path":
                str(
                    checkpoint_state_path
                ),
        },

        "semantics": {
            "filesystem_changes_update_living_state_immediately":
                True,

            "material_changes_accumulate_checkpoint_pressure":
                True,

            "transient_database_sidecars_do_not_create_checkpoint_pressure":
                True,

            "stable_material_state_generates_sdump_automatically":
                True,

            "verified_s3_upload_required_for_checkpoint_success":
                True,

            "historical_failures_are_preserved":
                True,

            "historical_failures_do_not_define_current_health":
                True,

            "current_pending_failure_backoff_degrades_health":
                True,

            "manual_checkpoint_available":
                True,

            "projection_establishes_authority":
                False,
        },
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="savant-state"
    )

    value.add_argument(
        "field",
        nargs="?",
    )

    value.add_argument(
        "--health",
        action="store_true",
    )

    value.add_argument(
        "--status",
        action="store_true",
    )

    value.add_argument(
        "--journal",
        type=int,
        metavar="N",
    )

    value.add_argument(
        "--compact",
        action="store_true",
    )

    return value


def tail_lines(
    path: Path,
    count: int,
) -> list[str]:
    if not path.is_file():
        return []

    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    return lines[
        -max(
            0,
            count,
        ):
    ]


def emit(
    value: Any,
    compact: bool,
) -> None:
    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ) or value is None:
        print(
            value
        )

        return

    if compact:
        print(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            )
        )

        return

    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


def main() -> int:
    arguments = parser().parse_args()

    if arguments.status:
        value = status_projection()

        if arguments.field:
            try:
                value = dotted_get(
                    value,
                    arguments.field,
                )

            except KeyError:
                print(
                    (
                        "field unavailable: "
                        + arguments.field
                    ),
                    file=sys.stderr,
                )

                return 2

        emit(
            value,
            arguments.compact,
        )

        if arguments.field is not None:
            return 0

        return (
            0
            if value[
                "healthy"
            ]
            else 1
        )

    if arguments.journal is not None:
        for line in tail_lines(
            journal_path,
            arguments.journal,
        ):
            print(
                line
            )

        return 0

    path = (
        health_path
        if arguments.health
        else current_path
    )

    if not path.is_file():
        print(
            f"state unavailable: {path}",
            file=sys.stderr,
        )

        return 1

    value = read_json(
        path
    )

    if arguments.field:
        try:
            value = dotted_get(
                value,
                arguments.field,
            )

        except (
            KeyError,
            IndexError,
        ):
            print(
                (
                    "field unavailable: "
                    + arguments.field
                ),
                file=sys.stderr,
            )

            return 2

    emit(
        value,
        arguments.compact,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
