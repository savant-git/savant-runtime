#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

LEXICON_ROOT = RUNTIME_ROOT.parent

BIN_ROOT = LEXICON_ROOT / "bin"

COMPILED_ROOT = RUNTIME_ROOT / "compiled"

ORCHESTRATION_ROOT = (
    RUNTIME_ROOT
    / "orchestration"
)

RUN_ROOT = (
    ORCHESTRATION_ROOT
    / "runs"
)

HEAD_PATH = (
    ORCHESTRATION_ROOT
    / "orchestration_head.json"
)

INDEX_PATH = (
    ORCHESTRATION_ROOT
    / "orchestration_index.json"
)

EVENT_LOG_PATH = (
    ORCHESTRATION_ROOT
    / "orchestration_events.jsonl"
)

RUNTIME_ADDRESS_INDEX_PATH = (
    COMPILED_ROOT
    / "runtime_address_index.json"
)

RUNTIME_AUDIT_REPORT_PATH = (
    COMPILED_ROOT
    / "runtime_audit_report.json"
)

TRANSACTION_HEAD_PATH = (
    RUNTIME_ROOT
    / "transactions"
    / "transaction_head.json"
)

CHECKPOINT_HEAD_PATH = (
    RUNTIME_ROOT
    / "checkpoints"
    / "refs"
    / "HEAD.json"
)


class RuntimeOrchestratorError(
    RuntimeError
):
    pass


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def file_digest(
    path: Path,
) -> str | None:
    if not path.is_file():
        return None

    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def load_json(
    path: Path,
    default: Any = None,
) -> Any:
    if not path.is_file():
        return default

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(
            handle
        )


def write_json_atomic(
    path: Path,
    payload: Any,
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
            json.dump(
                payload,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )

            handle.write(
                "\n"
            )

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


def append_jsonl(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            canonical_json(
                payload
            )
        )

        handle.write(
            "\n"
        )

        handle.flush()

        os.fsync(
            handle.fileno()
        )


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            try:
                payload = json.loads(
                    line
                )

            except json.JSONDecodeError as error:
                raise RuntimeOrchestratorError(
                    f"Invalid JSONL at "
                    f"{path}:{line_number}: "
                    f"{error}"
                ) from error

            if not isinstance(
                payload,
                dict,
            ):
                raise RuntimeOrchestratorError(
                    f"Invalid orchestration event "
                    f"at {path}:{line_number}"
                )

            records.append(
                payload
            )

    return records


class RuntimeOrchestrator:

    def __init__(
        self,
    ) -> None:
        for path in (
            ORCHESTRATION_ROOT,
            RUN_ROOT,
        ):
            path.mkdir(
                parents=True,
                exist_ok=True,
            )

    def controller(
        self,
        name: str,
    ) -> Path:
        return BIN_ROOT / name

    def execute(
        self,
        command: list[str],
    ) -> dict[str, Any]:
        started_at = utc_now()

        completed = subprocess.run(
            command,
            cwd=str(
                LEXICON_ROOT
            ),
            capture_output=True,
            text=True,
            check=False,
        )

        parsed_stdout = None

        if completed.stdout.strip():
            try:
                parsed_stdout = json.loads(
                    completed.stdout
                )

            except json.JSONDecodeError:
                parsed_stdout = None

        payload = {
            "command": command,
            "started_at": started_at,
            "finished_at": utc_now(),
            "returncode": completed.returncode,
            "passed": (
                completed.returncode == 0
            ),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "parsed_stdout": parsed_stdout,
            "stdout_digest": digest(
                completed.stdout
            ),
            "stderr_digest": digest(
                completed.stderr
            ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def step(
        self,
        name: str,
        controller: str,
        arguments: list[str],
        *,
        required: bool = True,
    ) -> dict[str, Any]:
        path = self.controller(
            controller
        )

        if not path.is_file():
            payload = {
                "name": name,
                "controller": controller,
                "controller_path": str(
                    path
                ),
                "required": required,
                "passed": (
                    not required
                ),
                "skipped": (
                    not required
                ),
                "reason": (
                    "controller_missing"
                ),
                "result": None,
            }

            payload[
                "digest"
            ] = digest(
                payload
            )

            return payload

        result = self.execute(
            [
                str(
                    path
                ),
                *arguments,
            ]
        )

        payload = {
            "name": name,
            "controller": controller,
            "controller_path": str(
                path
            ),
            "controller_sha256": file_digest(
                path
            ),
            "required": required,
            "passed": result[
                "passed"
            ],
            "skipped": False,
            "result": result,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def next_sequence(
        self,
    ) -> int:
        index = load_json(
            INDEX_PATH,
            default={},
        )

        if not isinstance(
            index,
            dict,
        ):
            return 1

        return int(
            index.get(
                "sequence",
                0,
            )
        ) + 1

    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        events = read_jsonl(
            EVENT_LOG_PATH
        )

        previous_digest = (
            events[
                -1
            ].get(
                "digest"
            )
            if events
            else None
        )

        event = {
            "event_id": (
                "runtime:orchestration:event:"
                f"{len(events) + 1:012d}"
            ),
            "sequence": len(
                events
            ) + 1,
            "run_id": run_id,
            "event_type": event_type,
            "timestamp": utc_now(),
            "previous_digest": previous_digest,
            "payload": payload,
        }

        event[
            "digest"
        ] = digest(
            event
        )

        append_jsonl(
            EVENT_LOG_PATH,
            event,
        )

        return event

    def update_index(
        self,
        run: dict[str, Any],
        run_path: Path,
    ) -> dict[str, Any]:
        existing = load_json(
            INDEX_PATH,
            default={},
        )

        if not isinstance(
            existing,
            dict,
        ):
            existing = {}

        records = existing.get(
            "records",
            {}
        )

        if not isinstance(
            records,
            dict,
        ):
            records = {}

        run_id = str(
            run[
                "run_id"
            ]
        )

        records[
            run_id
        ] = {
            "run_id": run_id,
            "sequence": run[
                "sequence"
            ],
            "mode": run[
                "mode"
            ],
            "passed": run[
                "passed"
            ],
            "started_at": run[
                "started_at"
            ],
            "finished_at": run[
                "finished_at"
            ],
            "run_path": str(
                run_path
            ),
            "digest": run[
                "digest"
            ],
        }

        ordered = {
            key: records[
                key
            ]
            for key in sorted(
                records,
                key=lambda current: (
                    int(
                        records[
                            current
                        ].get(
                            "sequence",
                            0,
                        )
                    ),
                    current,
                ),
            )
        }

        payload = {
            "index_id": (
                "runtime:orchestration:index"
            ),
            "sequence": max(
                (
                    int(
                        record.get(
                            "sequence",
                            0,
                        )
                    )
                    for record in ordered.values()
                ),
                default=0,
            ),
            "run_count": len(
                ordered
            ),
            "records": ordered,
            "updated_at": utc_now(),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        write_json_atomic(
            INDEX_PATH,
            payload,
        )

        return payload

    def persist_run(
        self,
        run: dict[str, Any],
    ) -> dict[str, Any]:
        run_path = (
            RUN_ROOT
            / f"{run['run_id']}.json"
        )

        write_json_atomic(
            run_path,
            run,
        )

        index = self.update_index(
            run,
            run_path,
        )

        head = {
            "head_id": (
                "runtime:orchestration:head"
            ),
            "run_id": run[
                "run_id"
            ],
            "sequence": run[
                "sequence"
            ],
            "mode": run[
                "mode"
            ],
            "passed": run[
                "passed"
            ],
            "run_path": str(
                run_path
            ),
            "run_digest": run[
                "digest"
            ],
            "updated_at": utc_now(),
        }

        head[
            "digest"
        ] = digest(
            head
        )

        write_json_atomic(
            HEAD_PATH,
            head,
        )

        return {
            "run_path": str(
                run_path
            ),
            "index": index,
            "head": head,
        }

    def execute_pipeline(
        self,
        *,
        mode: str,
        checkpoint_label: str | None,
        stop_on_failure: bool,
    ) -> dict[str, Any]:
        sequence = self.next_sequence()

        run_id = (
            "runtime-orchestration-"
            f"{sequence:012d}"
        )

        started_at = utc_now()

        steps = []

        plan = self.plan(
            mode
        )

        self.append_event(
            run_id,
            "begin",
            {
                "mode": mode,
                "plan": plan,
            },
        )

        for definition in plan:
            arguments = list(
                definition[
                    "arguments"
                ]
            )

            if (
                definition[
                    "name"
                ] == "checkpoint"
                and checkpoint_label
            ):
                arguments.extend(
                    [
                        "--label",
                        checkpoint_label,
                    ]
                )

            step = self.step(
                definition[
                    "name"
                ],
                definition[
                    "controller"
                ],
                arguments,
                required=definition.get(
                    "required",
                    True,
                ),
            )

            steps.append(
                step
            )

            self.append_event(
                run_id,
                "step",
                {
                    "name": step[
                        "name"
                    ],
                    "passed": step[
                        "passed"
                    ],
                    "required": step[
                        "required"
                    ],
                    "digest": step[
                        "digest"
                    ],
                },
            )

            if (
                stop_on_failure
                and step[
                    "required"
                ]
                and not step[
                    "passed"
                ]
            ):
                break

        failed_required = [
            step
            for step in steps
            if step[
                "required"
            ]
            and not step[
                "passed"
            ]
        ]

        run = {
            "run_id": run_id,
            "sequence": sequence,
            "mode": mode,
            "passed": (
                not failed_required
            ),
            "started_at": started_at,
            "finished_at": utc_now(),
            "stop_on_failure": (
                stop_on_failure
            ),
            "planned_step_count": len(
                plan
            ),
            "executed_step_count": len(
                steps
            ),
            "failed_required_count": len(
                failed_required
            ),
            "steps": steps,
            "artifacts": {
                "runtime_address_index": {
                    "path": str(
                        RUNTIME_ADDRESS_INDEX_PATH
                    ),
                    "exists": (
                        RUNTIME_ADDRESS_INDEX_PATH.is_file()
                    ),
                    "sha256": file_digest(
                        RUNTIME_ADDRESS_INDEX_PATH
                    ),
                },
                "runtime_audit_report": {
                    "path": str(
                        RUNTIME_AUDIT_REPORT_PATH
                    ),
                    "exists": (
                        RUNTIME_AUDIT_REPORT_PATH.is_file()
                    ),
                    "sha256": file_digest(
                        RUNTIME_AUDIT_REPORT_PATH
                    ),
                },
                "transaction_head": load_json(
                    TRANSACTION_HEAD_PATH,
                    default=None,
                ),
                "checkpoint_head": load_json(
                    CHECKPOINT_HEAD_PATH,
                    default=None,
                ),
            },
            "dependencies": {
                "plan": plan,
                "controllers": [
                    definition[
                        "controller"
                    ]
                    for definition in plan
                ],
            },
            "provenance": {
                "generator": str(
                    Path(
                        __file__
                    ).resolve()
                ),
                "runtime_root": str(
                    RUNTIME_ROOT
                ),
            },
            "lineage": {
                "derived_from": [
                    step[
                        "digest"
                    ]
                    for step in steps
                ]
            },
        }

        run[
            "digest"
        ] = digest(
            run
        )

        persistence = self.persist_run(
            run
        )

        event = self.append_event(
            run_id,
            "finish",
            {
                "passed": run[
                    "passed"
                ],
                "run_digest": run[
                    "digest"
                ],
                "run_path": persistence[
                    "run_path"
                ],
            },
        )

        return {
            "operation": "run",
            "passed": run[
                "passed"
            ],
            "run": run,
            "persistence": persistence,
            "event": event,
        }

    def plan(
        self,
        mode: str,
    ) -> list[dict[str, Any]]:
        plans = {
            "validate": [
                {
                    "name": "address-build",
                    "controller": (
                        "runtimeaddressctl"
                    ),
                    "arguments": [
                        "build"
                    ],
                    "required": True,
                },
                {
                    "name": "address-materialize",
                    "controller": (
                        "runtimeaddressctl"
                    ),
                    "arguments": [
                        "materialize"
                    ],
                    "required": True,
                },
                {
                    "name": "transaction-validate",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "run",
                        "validate",
                    ],
                    "required": True,
                },
                {
                    "name": "transaction-verify",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "verify"
                    ],
                    "required": True,
                },
                {
                    "name": "audit",
                    "controller": (
                        "runtimeauditctl"
                    ),
                    "arguments": [
                        "audit",
                        "--action",
                        "validate",
                    ],
                    "required": True,
                },
                {
                    "name": "audit-validate",
                    "controller": (
                        "runtimeauditvalidate"
                    ),
                    "arguments": [],
                    "required": True,
                },
            ],
            "compile": [
                {
                    "name": "transaction-compile",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "run",
                        "compile",
                    ],
                    "required": True,
                },
                {
                    "name": "address-build",
                    "controller": (
                        "runtimeaddressctl"
                    ),
                    "arguments": [
                        "build"
                    ],
                    "required": True,
                },
                {
                    "name": "address-materialize",
                    "controller": (
                        "runtimeaddressctl"
                    ),
                    "arguments": [
                        "materialize"
                    ],
                    "required": True,
                },
                {
                    "name": "audit",
                    "controller": (
                        "runtimeauditctl"
                    ),
                    "arguments": [
                        "audit",
                        "--action",
                        "validate",
                    ],
                    "required": True,
                },
                {
                    "name": "checkpoint",
                    "controller": (
                        "runtimecheckpointctl"
                    ),
                    "arguments": [
                        "create"
                    ],
                    "required": True,
                },
                {
                    "name": "checkpoint-verify",
                    "controller": (
                        "runtimecheckpointctl"
                    ),
                    "arguments": [
                        "verify",
                        "HEAD",
                    ],
                    "required": True,
                },
            ],
            "integrity": [
                {
                    "name": "transaction-integrity",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "run",
                        "integrity",
                    ],
                    "required": True,
                },
                {
                    "name": "transaction-verify",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "verify"
                    ],
                    "required": True,
                },
                {
                    "name": "checkpoint-verify-all",
                    "controller": (
                        "runtimecheckpointctl"
                    ),
                    "arguments": [
                        "verify-all"
                    ],
                    "required": True,
                },
                {
                    "name": "audit-verify",
                    "controller": (
                        "runtimeauditctl"
                    ),
                    "arguments": [
                        "verify"
                    ],
                    "required": True,
                },
                {
                    "name": "audit-validate",
                    "controller": (
                        "runtimeauditvalidate"
                    ),
                    "arguments": [],
                    "required": True,
                },
            ],
            "full": [
                {
                    "name": "address-build",
                    "controller": (
                        "runtimeaddressctl"
                    ),
                    "arguments": [
                        "build"
                    ],
                    "required": True,
                },
                {
                    "name": "address-materialize",
                    "controller": (
                        "runtimeaddressctl"
                    ),
                    "arguments": [
                        "materialize"
                    ],
                    "required": True,
                },
                {
                    "name": "transaction-validate",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "run",
                        "validate",
                    ],
                    "required": True,
                },
                {
                    "name": "transaction-compile",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "run",
                        "compile",
                    ],
                    "required": True,
                },
                {
                    "name": "transaction-integrity",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "run",
                        "integrity",
                    ],
                    "required": True,
                },
                {
                    "name": "transaction-verify",
                    "controller": (
                        "runtimetransactionctl"
                    ),
                    "arguments": [
                        "verify"
                    ],
                    "required": True,
                },
                {
                    "name": "audit",
                    "controller": (
                        "runtimeauditctl"
                    ),
                    "arguments": [
                        "audit",
                        "--action",
                        "validate",
                    ],
                    "required": True,
                },
                {
                    "name": "audit-validate",
                    "controller": (
                        "runtimeauditvalidate"
                    ),
                    "arguments": [],
                    "required": True,
                },
                {
                    "name": "checkpoint",
                    "controller": (
                        "runtimecheckpointctl"
                    ),
                    "arguments": [
                        "create"
                    ],
                    "required": True,
                },
                {
                    "name": "checkpoint-verify",
                    "controller": (
                        "runtimecheckpointctl"
                    ),
                    "arguments": [
                        "verify",
                        "HEAD",
                    ],
                    "required": True,
                },
            ],
        }

        if mode not in plans:
            raise RuntimeOrchestratorError(
                f"Unknown mode: {mode}"
            )

        return plans[
            mode
        ]

    def show_plan(
        self,
        mode: str,
    ) -> dict[str, Any]:
        plan = self.plan(
            mode
        )

        payload = {
            "operation": "plan",
            "passed": True,
            "mode": mode,
            "step_count": len(
                plan
            ),
            "steps": plan,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def status(
        self,
    ) -> dict[str, Any]:
        index = load_json(
            INDEX_PATH,
            default={},
        )

        head = load_json(
            HEAD_PATH,
            default={},
        )

        if not isinstance(
            index,
            dict,
        ):
            index = {}

        if not isinstance(
            head,
            dict,
        ):
            head = {}

        payload = {
            "operation": "status",
            "passed": True,
            "head": head,
            "index": index,
            "run_count": len(
                list(
                    RUN_ROOT.glob(
                        "*.json"
                    )
                )
            ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def verify(
        self,
    ) -> dict[str, Any]:
        issues = []

        events = read_jsonl(
            EVENT_LOG_PATH
        )

        previous_digest = None

        for expected_sequence, event in enumerate(
            events,
            start=1,
        ):
            if event.get(
                "sequence"
            ) != expected_sequence:
                issues.append(
                    {
                        "code": (
                            "event_sequence_mismatch"
                        ),
                        "expected": (
                            expected_sequence
                        ),
                        "actual": event.get(
                            "sequence"
                        ),
                    }
                )

            if event.get(
                "previous_digest"
            ) != previous_digest:
                issues.append(
                    {
                        "code": (
                            "event_previous_digest_mismatch"
                        ),
                        "sequence": (
                            expected_sequence
                        ),
                        "expected": (
                            previous_digest
                        ),
                        "actual": event.get(
                            "previous_digest"
                        ),
                    }
                )

            expected_digest = digest(
                {
                    key: value
                    for key, value
                    in event.items()
                    if key != "digest"
                }
            )

            if event.get(
                "digest"
            ) != expected_digest:
                issues.append(
                    {
                        "code": (
                            "event_digest_mismatch"
                        ),
                        "sequence": (
                            expected_sequence
                        ),
                    }
                )

            previous_digest = event.get(
                "digest"
            )

        for run_path in sorted(
            RUN_ROOT.glob(
                "*.json"
            )
        ):
            run = load_json(
                run_path,
                default=None,
            )

            if not isinstance(
                run,
                dict,
            ):
                issues.append(
                    {
                        "code": (
                            "run_invalid"
                        ),
                        "path": str(
                            run_path
                        ),
                    }
                )

                continue

            expected_digest = digest(
                {
                    key: value
                    for key, value
                    in run.items()
                    if key != "digest"
                }
            )

            if run.get(
                "digest"
            ) != expected_digest:
                issues.append(
                    {
                        "code": (
                            "run_digest_mismatch"
                        ),
                        "run_id": run.get(
                            "run_id"
                        ),
                    }
                )

        payload = {
            "operation": "verify",
            "passed": not issues,
            "event_count": len(
                events
            ),
            "run_count": len(
                list(
                    RUN_ROOT.glob(
                        "*.json"
                    )
                )
            ),
            "issue_count": len(
                issues
            ),
            "issues": issues,
            "head_event_digest": (
                previous_digest
            ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def print_result(
    payload: Any,
) -> None:
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    plan_parser = subparsers.add_parser(
        "plan"
    )

    plan_parser.add_argument(
        "mode",
        choices=[
            "validate",
            "compile",
            "integrity",
            "full",
        ],
    )

    run_parser = subparsers.add_parser(
        "run"
    )

    run_parser.add_argument(
        "mode",
        choices=[
            "validate",
            "compile",
            "integrity",
            "full",
        ],
    )

    run_parser.add_argument(
        "--checkpoint-label"
    )

    run_parser.add_argument(
        "--continue-on-failure",
        action="store_true",
    )

    subparsers.add_parser(
        "status"
    )

    subparsers.add_parser(
        "verify"
    )

    args = parser.parse_args()

    orchestrator = RuntimeOrchestrator()

    if args.command == "plan":
        result = orchestrator.show_plan(
            args.mode
        )

    elif args.command == "run":
        result = orchestrator.execute_pipeline(
            mode=args.mode,
            checkpoint_label=(
                args.checkpoint_label
            ),
            stop_on_failure=(
                not args.continue_on_failure
            ),
        )

    elif args.command == "status":
        result = orchestrator.status()

    elif args.command == "verify":
        result = orchestrator.verify()

    else:
        raise RuntimeOrchestratorError(
            args.command
        )

    print_result(
        result
    )

    return (
        0
        if result.get(
            "passed",
            True,
        )
        else 1
    )


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except RuntimeOrchestratorError as error:
        print_result(
            {
                "operation": "error",
                "passed": False,
                "error": type(
                    error
                ).__name__,
                "message": str(
                    error
                ),
            }
        )

        raise SystemExit(
            1
        )
