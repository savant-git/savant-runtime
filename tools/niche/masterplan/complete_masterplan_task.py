#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

MASTERPLAN_ATTEST = (
    ROOT
    / "bin"
    / "masterplan-attest"
)

MASTERPLAN_TRANSITION = (
    ROOT
    / "bin"
    / "masterplan-transition"
)

MASTERPLAN_PROJECT = (
    ROOT
    / "bin"
    / "masterplan-project"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "completion"
)

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
    "occurred_at",
    "accepted_at",
    "captured_at",
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
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            value
        )
    ).hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return {
            key: deterministic_projection(
                child
            )
            for key, child in sorted(
                value.items(),
                key=lambda item: item[
                    0
                ],
            )
            if key
            not in VOLATILE_FIELDS
        }

    if isinstance(
        value,
        list,
    ):
        return [
            deterministic_projection(
                child
            )
            for child in value
        ]

    if isinstance(
        value,
        tuple,
    ):
        return tuple(
            deterministic_projection(
                child
            )
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

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
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


def run_command(
    command: list[str],
) -> dict[str, Any]:
    started_at = utc_now()

    completed = subprocess.run(
        command,
        cwd=str(
            ROOT
        ),
        check=False,
        capture_output=True,
        text=True,
    )

    return {
        "command": command,
        "started_at": started_at,
        "finished_at": utc_now(),
        "returncode": (
            completed.returncode
        ),
        "passed": (
            completed.returncode
            == 0
        ),
        "stdout": (
            completed.stdout
        ),
        "stderr": (
            completed.stderr
        ),
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


def task_record(
    graph: dict[str, Any],
    task_id: str,
) -> dict[str, Any]:
    records = graph.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise ValueError(
            "Task graph records are invalid."
        )

    for record in records:
        if (
            isinstance(
                record,
                dict,
            )
            and record.get(
                "id"
            )
            == task_id
        ):
            return record

    raise KeyError(
        f"Unknown task: {task_id}"
    )


def passing_attestation(
    graph: dict[str, Any],
    task_id: str,
) -> dict[str, Any] | None:
    attestations = graph.get(
        "attestations",
        [],
    )

    if not isinstance(
        attestations,
        list,
    ):
        raise ValueError(
            "Task graph attestations are invalid."
        )

    matches = [
        record
        for record in attestations
        if (
            isinstance(
                record,
                dict,
            )
            and record.get(
                "task_id"
            )
            == task_id
            and record.get(
                "passed"
            )
            is True
        )
    ]

    if not matches:
        return None

    return sorted(
        matches,
        key=lambda record: (
            str(
                record.get(
                    "occurred_at",
                    "",
                )
            ),
            str(
                record.get(
                    "id",
                    "",
                )
            ),
        ),
    )[
        -1
    ]


def plan_completion(
    task_id: str,
    actor: str,
    rationale: str,
    notes: str,
) -> dict[str, Any]:
    graph = load_json(
        GRAPH_PATH
    )

    task = task_record(
        graph,
        task_id,
    )

    attestation = passing_attestation(
        graph,
        task_id,
    )

    return {
        "schema": (
            "savant://niche/masterplan/"
            "task-completion-plan/1.0.0"
        ),
        "operation": (
            "plan_masterplan_completion"
        ),
        "generated_at": utc_now(),
        "passed": (
            task.get(
                "status"
            )
            == "active"
        ),
        "task": {
            "id": task_id,
            "title": task.get(
                "title"
            ),
            "status": task.get(
                "status"
            ),
            "authority": task.get(
                "authority"
            ),
        },
        "actor": actor,
        "rationale": rationale,
        "notes": notes,
        "existing_passing_attestation": (
            attestation
        ),
        "steps": [
            {
                "id": "attest",
                "required": (
                    attestation
                    is None
                ),
                "command": [
                    str(
                        MASTERPLAN_ATTEST
                    ),
                    "apply-strict",
                    task_id,
                    "--actor",
                    actor,
                    "--notes",
                    notes,
                ],
            },
            {
                "id": "transition",
                "required": True,
                "command": [
                    str(
                        MASTERPLAN_TRANSITION
                    ),
                    "apply-strict",
                    task_id,
                    "completed",
                    "--actor",
                    actor,
                    "--rationale",
                    rationale,
                ],
            },
            {
                "id": "project",
                "required": True,
                "command": [
                    str(
                        MASTERPLAN_PROJECT
                    ),
                    "strict",
                ],
            },
        ],
    }


def apply_completion(
    task_id: str,
    actor: str,
    rationale: str,
    notes: str,
) -> dict[str, Any]:
    graph_before = load_json(
        GRAPH_PATH
    )

    task_before = task_record(
        graph_before,
        task_id,
    )

    if task_before.get(
        "status"
    ) != "active":
        raise ValueError(
            (
                "Task must be active before completion: "
                f"{task_id} is "
                f"{task_before.get('status')}"
            )
        )

    operations: list[
        dict[str, Any]
    ] = []

    existing_attestation = (
        passing_attestation(
            graph_before,
            task_id,
        )
    )

    if existing_attestation is None:
        attestation_result = run_command(
            [
                str(
                    MASTERPLAN_ATTEST
                ),
                "apply-strict",
                task_id,
                "--actor",
                actor,
                "--notes",
                notes,
            ]
        )

        attestation_result[
            "id"
        ] = "attest"

        operations.append(
            attestation_result
        )

        if not attestation_result[
            "passed"
        ]:
            return completion_result(
                task_id=task_id,
                actor=actor,
                rationale=rationale,
                notes=notes,
                graph_before=graph_before,
                operations=operations,
                passed=False,
            )

    transition_result = run_command(
        [
            str(
                MASTERPLAN_TRANSITION
            ),
            "apply-strict",
            task_id,
            "completed",
            "--actor",
            actor,
            "--rationale",
            rationale,
        ]
    )

    transition_result[
        "id"
    ] = "transition"

    operations.append(
        transition_result
    )

    if not transition_result[
        "passed"
    ]:
        return completion_result(
            task_id=task_id,
            actor=actor,
            rationale=rationale,
            notes=notes,
            graph_before=graph_before,
            operations=operations,
            passed=False,
        )

    project_result = run_command(
        [
            str(
                MASTERPLAN_PROJECT
            ),
            "strict",
        ]
    )

    project_result[
        "id"
    ] = "project"

    operations.append(
        project_result
    )

    graph_after = load_json(
        GRAPH_PATH
    )

    task_after = task_record(
        graph_after,
        task_id,
    )

    passed = all(
        (
            all(
                operation[
                    "passed"
                ]
                for operation in operations
            ),
            task_after.get(
                "status"
            )
            == "completed",
            passing_attestation(
                graph_after,
                task_id,
            )
            is not None,
        )
    )

    return completion_result(
        task_id=task_id,
        actor=actor,
        rationale=rationale,
        notes=notes,
        graph_before=graph_before,
        operations=operations,
        passed=passed,
        graph_after=graph_after,
    )


def completion_result(
    *,
    task_id: str,
    actor: str,
    rationale: str,
    notes: str,
    graph_before: dict[str, Any],
    operations: list[dict[str, Any]],
    passed: bool,
    graph_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if graph_after is None:
        graph_after = load_json(
            GRAPH_PATH
        )

    before_task = task_record(
        graph_before,
        task_id,
    )

    after_task = task_record(
        graph_after,
        task_id,
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "task-completion/1.0.0"
        ),
        "operation": (
            "complete_masterplan_task"
        ),
        "generated_at": utc_now(),
        "passed": passed,
        "task": {
            "id": task_id,
            "title": after_task.get(
                "title"
            ),
            "before_status": before_task.get(
                "status"
            ),
            "after_status": after_task.get(
                "status"
            ),
        },
        "actor": actor,
        "rationale": rationale,
        "notes": notes,
        "attestation": passing_attestation(
            graph_after,
            task_id,
        ),
        "operations": operations,
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "digest_before": digest(
                deterministic_projection(
                    graph_before
                )
            ),
            "digest_after": digest(
                deterministic_projection(
                    graph_after
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

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = (
        f"{timestamp()}__"
        f"{task_id}"
    )

    write_json(
        REPORT_ROOT
        / f"{run_id}__completion.json",
        result,
    )

    write_json(
        REPORT_ROOT
        / "latest.json",
        result,
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Attest and complete an active Masterplan task "
            "through the authoritative transition pipeline."
        )
    )

    parser.add_argument(
        "task_id",
    )

    parser.add_argument(
        "--actor",
        required=True,
    )

    parser.add_argument(
        "--rationale",
        required=True,
    )

    parser.add_argument(
        "--notes",
        default="",
    )

    parser.add_argument(
        "--plan",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        if not GRAPH_PATH.is_file():
            raise FileNotFoundError(
                GRAPH_PATH
            )

        if arguments.plan:
            result = plan_completion(
                arguments.task_id,
                arguments.actor,
                arguments.rationale,
                arguments.notes,
            )

        else:
            result = apply_completion(
                arguments.task_id,
                arguments.actor,
                arguments.rationale,
                arguments.notes,
            )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "complete_masterplan_task"
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
