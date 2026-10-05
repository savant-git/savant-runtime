#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

EXECUTION_PACKET_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "execution"
)

RUN_REPORT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "runs"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "identity-promotion"
    / "transactions"
)

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}

ALLOWED_AUTOMATED_STAGES = {
    "preflight",
    "backup",
    "verification",
    "promotion_queue_refresh",
}

CONTENT_IMPLEMENTATION_STAGES = {
    "contracts",
    "runtime",
    "controller",
    "tests",
    "definition_attachment",
    "parent_attachment",
    "attestation",
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


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rendered = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
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
            handle.write(rendered)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_text(
    path: Path,
    value: str,
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
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def safe_key(
    value: str,
) -> str:
    return "".join(
        character
        if (
            character.isalnum()
            or character
            in {
                ".",
                "_",
                "-",
            }
        )
        else "_"
        for character in value
    ).strip("_")


def latest_execution_packets() -> list[Path]:
    if not EXECUTION_PACKET_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in EXECUTION_PACKET_ROOT.glob(
                "*/latest.json"
            )
            if path.is_file()
        ),
        key=lambda path: (
            path.stat().st_mtime_ns,
            path.as_posix(),
        ),
        reverse=True,
    )


def latest_execution_packet() -> Path:
    paths = latest_execution_packets()

    if not paths:
        raise FileNotFoundError(
            "No promotion execution packet exists."
        )

    return paths[0]


def resolve_packet(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_execution_packet()

    path = declared.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def validate_packet(
    packet: dict[str, Any],
) -> None:
    subject = packet.get(
        "subject"
    )

    if not isinstance(subject, dict):
        raise ValueError(
            "Execution packet has no subject."
        )

    identifier = subject.get(
        "id"
    )

    if (
        not isinstance(identifier, str)
        or not identifier.strip()
    ):
        raise ValueError(
            "Execution packet subject has no identifier."
        )

    stages = packet.get(
        "stages"
    )

    if (
        not isinstance(stages, list)
        or not stages
    ):
        raise ValueError(
            "Execution packet has no stages."
        )

    policy = packet.get(
        "execution_policy"
    )

    if not isinstance(policy, dict):
        raise ValueError(
            "Execution packet has no policy."
        )

    if policy.get(
        "replace_existing_authority"
    ) is not False:
        raise ValueError(
            "Execution policy permits authority replacement."
        )

    if policy.get(
        "authority_transfer"
    ) is not False:
        raise ValueError(
            "Execution policy permits authority transfer."
        )


def command_result(
    command: list[str],
) -> dict[str, Any]:
    started_at = utc_now()

    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )

    return {
        "command": command,
        "started_at": started_at,
        "finished_at": utc_now(),
        "returncode": completed.returncode,
        "passed": (
            completed.returncode == 0
        ),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_sha256": hashlib.sha256(
            completed.stdout.encode(
                "utf-8"
            )
        ).hexdigest(),
        "stderr_sha256": hashlib.sha256(
            completed.stderr.encode(
                "utf-8"
            )
        ).hexdigest(),
    }


def verify_source_hash(
    operation: dict[str, Any],
) -> dict[str, Any]:
    source_value = operation.get(
        "source"
    )

    expected = operation.get(
        "source_sha256"
    )

    if not isinstance(
        source_value,
        str,
    ):
        return {
            "passed": False,
            "code": (
                "backup.source_missing"
            ),
            "message": (
                "Backup operation has no source."
            ),
        }

    source = (
        ROOT
        / source_value
    ).resolve()

    if not source.is_file():
        return {
            "passed": False,
            "code": (
                "backup.source_not_found"
            ),
            "source": source_value,
        }

    actual = sha256_path(
        source
    )

    return {
        "passed": (
            expected is None
            or expected == actual
        ),
        "source": source_value,
        "expected_sha256": expected,
        "actual_sha256": actual,
    }


def execute_backup_operation(
    operation: dict[str, Any],
    transaction_root: Path,
) -> dict[str, Any]:
    source_value = operation.get(
        "source"
    )

    destination_value = operation.get(
        "destination"
    )

    if (
        not isinstance(
            source_value,
            str,
        )
        or not isinstance(
            destination_value,
            str,
        )
    ):
        return {
            "passed": False,
            "code": (
                "backup.operation_invalid"
            ),
            "operation": operation,
        }

    source = (
        ROOT
        / source_value
    ).resolve()

    declared_destination = (
        ROOT
        / destination_value
    ).resolve()

    try:
        relative_source = source.relative_to(
            ROOT
        )

    except ValueError:
        return {
            "passed": False,
            "code": (
                "backup.source_outside_root"
            ),
            "source": str(source),
        }

    destination = (
        transaction_root
        / "backup"
        / relative_source
    )

    hash_check = verify_source_hash(
        operation
    )

    if not hash_check[
        "passed"
    ]:
        return {
            "passed": False,
            "code": (
                "backup.source_hash_mismatch"
            ),
            "hash_check": hash_check,
        }

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    copied_sha256 = sha256_path(
        destination
    )

    passed = (
        copied_sha256
        == hash_check[
            "actual_sha256"
        ]
    )

    return {
        "passed": passed,
        "source": relative_path(
            source
        ),
        "declared_destination": (
            relative_path(
                declared_destination
            )
        ),
        "transaction_destination": (
            relative_path(
                destination
            )
        ),
        "source_sha256": hash_check[
            "actual_sha256"
        ],
        "copied_sha256": copied_sha256,
    }


def execute_preflight_stage(
    stage: dict[str, Any],
) -> dict[str, Any]:
    operations = stage.get(
        "operations",
        []
    )

    results: list[
        dict[str, Any]
    ] = []

    for operation in operations:
        if not isinstance(
            operation,
            dict,
        ):
            results.append(
                {
                    "passed": False,
                    "code": (
                        "preflight.operation_invalid"
                    ),
                }
            )
            continue

        results.append(
            {
                **operation,
                "passed": bool(
                    operation.get(
                        "passed",
                        False,
                    )
                ),
            }
        )

    return {
        "passed": all(
            result.get(
                "passed",
                False,
            )
            for result in results
        ),
        "results": results,
    }


def execute_backup_stage(
    stage: dict[str, Any],
    transaction_root: Path,
) -> dict[str, Any]:
    operations = stage.get(
        "operations",
        []
    )

    results = [
        execute_backup_operation(
            operation,
            transaction_root,
        )
        for operation in operations
        if isinstance(
            operation,
            dict,
        )
    ]

    return {
        "passed": all(
            result.get(
                "passed",
                False,
            )
            for result in results
        ),
        "results": results,
    }


def execute_command_stage(
    stage: dict[str, Any],
) -> dict[str, Any]:
    operations = stage.get(
        "operations",
        []
    )

    results: list[
        dict[str, Any]
    ] = []

    for operation in operations:
        if not isinstance(
            operation,
            dict,
        ):
            results.append(
                {
                    "passed": False,
                    "code": (
                        "command.operation_invalid"
                    ),
                }
            )
            continue

        command = operation.get(
            "command"
        )

        if (
            not isinstance(
                command,
                list,
            )
            or not command
            or not all(
                isinstance(
                    value,
                    str,
                )
                for value in command
            )
        ):
            results.append(
                {
                    "passed": False,
                    "code": (
                        "command.missing"
                    ),
                    "operation": operation,
                }
            )
            continue

        result = command_result(
            command
        )

        result[
            "role"
        ] = operation.get(
            "role"
        )

        results.append(
            result
        )

    return {
        "passed": all(
            result.get(
                "passed",
                False,
            )
            for result in results
        ),
        "results": results,
    }


def planned_content_stage(
    stage: dict[str, Any],
) -> dict[str, Any]:
    operations = stage.get(
        "operations",
        []
    )

    return {
        "passed": True,
        "planned_only": True,
        "blocked_reason": (
            "Content implementation requires explicit "
            "file contents and cannot be inferred safely "
            "from the execution packet alone."
        ),
        "operations": operations,
    }


def stage_dependency_passed(
    dependency: str,
    results: dict[str, dict[str, Any]],
) -> bool:
    result = results.get(
        dependency
    )

    return bool(
        result
        and result.get(
            "passed",
            False,
        )
    )


def run_stage(
    stage: dict[str, Any],
    *,
    transaction_root: Path,
    apply: bool,
    previous_results: dict[
        str,
        dict[str, Any]
    ],
) -> dict[str, Any]:
    stage_id = stage.get(
        "id"
    )

    if not isinstance(
        stage_id,
        str,
    ):
        return {
            "passed": False,
            "state": "failed",
            "code": "stage.id_missing",
        }

    dependencies = stage.get(
        "depends_on",
        []
    )

    unmet = [
        dependency
        for dependency in dependencies
        if not stage_dependency_passed(
            dependency,
            previous_results,
        )
    ]

    if unmet:
        return {
            "id": stage_id,
            "passed": False,
            "state": "skipped",
            "code": (
                "stage.dependencies_failed"
            ),
            "unmet_dependencies": unmet,
        }

    started_at = utc_now()

    if stage_id == "preflight":
        body = execute_preflight_stage(
            stage
        )

    elif stage_id == "backup":
        body = execute_backup_stage(
            stage,
            transaction_root,
        )

    elif (
        stage_id
        in CONTENT_IMPLEMENTATION_STAGES
    ):
        body = planned_content_stage(
            stage
        )

    elif (
        stage_id
        in {
            "verification",
            "promotion_queue_refresh",
        }
    ):
        if apply:
            body = execute_command_stage(
                stage
            )

        else:
            body = {
                "passed": True,
                "planned_only": True,
                "operations": stage.get(
                    "operations",
                    []
                ),
            }

    else:
        body = {
            "passed": False,
            "code": (
                "stage.unsupported"
            ),
        }

    passed = bool(
        body.get(
            "passed",
            False,
        )
    )

    return {
        "id": stage_id,
        "started_at": started_at,
        "finished_at": utc_now(),
        "passed": passed,
        "state": (
            "completed"
            if passed
            else "failed"
        ),
        "apply": apply,
        "body": body,
    }


def rollback_transaction(
    transaction_root: Path,
) -> dict[str, Any]:
    backup_root = (
        transaction_root
        / "backup"
    )

    results: list[
        dict[str, Any]
    ] = []

    if not backup_root.is_dir():
        return {
            "passed": True,
            "restored_count": 0,
            "results": [],
        }

    for backup in sorted(
        path
        for path in backup_root.rglob("*")
        if path.is_file()
    ):
        relative = backup.relative_to(
            backup_root
        )

        destination = (
            ROOT
            / relative
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            backup,
            destination,
        )

        source_sha256 = sha256_path(
            backup
        )

        restored_sha256 = sha256_path(
            destination
        )

        results.append(
            {
                "source": relative_path(
                    backup
                ),
                "destination": relative_path(
                    destination
                ),
                "source_sha256": source_sha256,
                "restored_sha256": (
                    restored_sha256
                ),
                "passed": (
                    source_sha256
                    == restored_sha256
                ),
            }
        )

    return {
        "passed": all(
            result[
                "passed"
            ]
            for result in results
        ),
        "restored_count": len(
            results
        ),
        "results": results,
    }


def markdown(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Identity Promotion Run",
        "",
        (
            f"- Generated: "
            f"`{result['generated_at']}`"
        ),
        (
            f"- Subject: "
            f"`{result['subject']['id']}`"
        ),
        (
            f"- Mode: "
            f"`{result['mode']}`"
        ),
        (
            f"- Passed: "
            f"**{result['passed']}**"
        ),
        (
            f"- Digest: "
            f"`{result['digest']}`"
        ),
        "",
        "## Stages",
        "",
    ]

    for stage in result[
        "stages"
    ]:
        lines.extend(
            [
                (
                    f"### `{stage['id']}`"
                ),
                "",
                (
                    f"- State: "
                    f"`{stage['state']}`"
                ),
                (
                    f"- Passed: "
                    f"**{stage['passed']}**"
                ),
                "",
            ]
        )

    if result.get(
        "rollback"
    ):
        lines.extend(
            [
                "## Rollback",
                "",
                (
                    f"- Passed: "
                    f"**{result['rollback']['passed']}**"
                ),
                (
                    f"- Restored: "
                    f"**{result['rollback']['restored_count']}**"
                ),
                "",
            ]
        )

    return "\n".join(
        lines
    )


def run_execution(
    packet_path: Path,
    *,
    apply: bool,
    rollback_on_failure: bool,
) -> dict[str, Any]:
    packet = load_json(
        packet_path
    )

    validate_packet(
        packet
    )

    subject = packet[
        "subject"
    ]

    subject_id = subject[
        "id"
    ]

    transaction_id = (
        f"promotion-{timestamp()}-"
        f"{digest(packet)[:16]}"
    )

    transaction_root = (
        TRANSACTION_ROOT
        / safe_key(
            subject_id
        )
        / transaction_id
    )

    transaction_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    packet_snapshot = (
        transaction_root
        / "execution_packet.json"
    )

    atomic_write_json(
        packet_snapshot,
        packet,
    )

    results_by_id: dict[
        str,
        dict[str, Any]
    ] = {}

    stage_results: list[
        dict[str, Any]
    ] = []

    halted = False

    for stage in packet[
        "stages"
    ]:
        if halted:
            result = {
                "id": stage.get(
                    "id",
                    "unknown",
                ),
                "passed": False,
                "state": "skipped",
                "code": (
                    "execution.halted"
                ),
            }

        else:
            result = run_stage(
                stage,
                transaction_root=(
                    transaction_root
                ),
                apply=apply,
                previous_results=(
                    results_by_id
                ),
            )

        stage_id = result[
            "id"
        ]

        results_by_id[
            stage_id
        ] = result

        stage_results.append(
            result
        )

        if (
            not result[
                "passed"
            ]
            and packet[
                "execution_policy"
            ].get(
                "stop_on_failure",
                True,
            )
        ):
            halted = True

    passed = all(
        stage[
            "passed"
        ]
        for stage in stage_results
    )

    rollback_result: dict[
        str,
        Any
    ] | None = None

    if (
        not passed
        and apply
        and rollback_on_failure
    ):
        rollback_result = (
            rollback_transaction(
                transaction_root
            )
        )

    result: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-run/1.0.0"
        ),
        "operation": (
            "run_promotion_execution"
        ),
        "generated_at": utc_now(),
        "mode": (
            "apply"
            if apply
            else "plan"
        ),
        "packet": {
            "path": relative_path(
                packet_path
            ),
            "sha256": sha256_path(
                packet_path
            ),
            "digest": packet.get(
                "digest"
            ),
        },
        "transaction": {
            "id": transaction_id,
            "root": relative_path(
                transaction_root
            ),
            "packet_snapshot": (
                relative_path(
                    packet_snapshot
                )
            ),
        },
        "subject": subject,
        "stages": stage_results,
        "halted": halted,
        "passed": passed,
        "rollback": rollback_result,
        "statistics": {
            "stage_count": len(
                stage_results
            ),
            "passed_count": sum(
                stage[
                    "passed"
                ]
                for stage in stage_results
            ),
            "failed_count": sum(
                not stage[
                    "passed"
                ]
                for stage in stage_results
            ),
            "planned_content_stage_count": sum(
                bool(
                    stage.get(
                        "body",
                        {},
                    ).get(
                        "planned_only",
                        False,
                    )
                )
                for stage in stage_results
                if isinstance(
                    stage.get(
                        "body"
                    ),
                    dict,
                )
            ),
        },
    }

    result[
        "digest"
    ] = digest(
        deterministic_projection(
            result
        )
    )

    transaction_result = (
        transaction_root
        / "result.json"
    )

    atomic_write_json(
        transaction_result,
        result,
    )

    transaction_markdown = (
        transaction_root
        / "result.md"
    )

    atomic_write_text(
        transaction_markdown,
        markdown(
            result
        ),
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a transaction-safe identity promotion "
            "execution packet."
        )
    )

    parser.add_argument(
        "--packet",
        type=Path,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    parser.add_argument(
        "--no-rollback",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=RUN_REPORT_ROOT,
    )

    arguments = parser.parse_args()

    try:
        packet_path = resolve_packet(
            arguments.packet
        )

        result = run_execution(
            packet_path,
            apply=arguments.apply,
            rollback_on_failure=(
                not arguments.no_rollback
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "run_promotion_execution"
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

    subject_key = safe_key(
        result[
            "subject"
        ][
            "id"
        ]
    )

    output_root = (
        arguments.output_root
        .expanduser()
        .resolve()
        / subject_key
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-run.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-run.md"
        )
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    atomic_write_json(
        json_path,
        result,
    )

    atomic_write_json(
        latest_json,
        result,
    )

    rendered = markdown(
        result
    )

    atomic_write_text(
        markdown_path,
        rendered,
    )

    atomic_write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": (
            result[
                "generated_at"
            ]
        ),
        "subject": (
            result[
                "subject"
            ][
                "id"
            ]
        ),
        "run_digest": (
            result[
                "digest"
            ]
        ),
        "mode": (
            result[
                "mode"
            ]
        ),
        "passed": (
            result[
                "passed"
            ]
        ),
        "files": {
            json_path.name: (
                sha256_path(
                    json_path
                )
            ),
            markdown_path.name: (
                sha256_path(
                    markdown_path
                )
            ),
            latest_json.name: (
                sha256_path(
                    latest_json
                )
            ),
            latest_markdown.name: (
                sha256_path(
                    latest_markdown
                )
            ),
        },
    }

    manifest_path = (
        output_root
        / (
            f"{run_id}__manifest.json"
        )
    )

    atomic_write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "run_promotion_execution"
                ),
                "passed": result[
                    "passed"
                ],
                "mode": result[
                    "mode"
                ],
                "subject": result[
                    "subject"
                ],
                "digest": result[
                    "digest"
                ],
                "statistics": result[
                    "statistics"
                ],
                "transaction": result[
                    "transaction"
                ],
                "rollback": result[
                    "rollback"
                ],
                "reports": {
                    "json": str(
                        json_path
                    ),
                    "markdown": str(
                        markdown_path
                    ),
                    "latest_json": str(
                        latest_json
                    ),
                    "latest_markdown": str(
                        latest_markdown
                    ),
                    "manifest": str(
                        manifest_path
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not result[
            "passed"
        ]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
