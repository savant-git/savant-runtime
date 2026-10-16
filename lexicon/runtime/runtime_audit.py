#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

LEXICON_ROOT = RUNTIME_ROOT.parent

BIN_ROOT = LEXICON_ROOT / "bin"

COMPILED_ROOT = RUNTIME_ROOT / "compiled"

REGISTRY_PATH = (
    RUNTIME_ROOT
    / "runtime_registry.yaml"
)

ADDRESS_INDEX_PATH = (
    COMPILED_ROOT
    / "runtime_address_index.json"
)

AUDIT_LOG_PATH = (
    COMPILED_ROOT
    / "runtime_audit.jsonl"
)

AUDIT_STATE_PATH = (
    COMPILED_ROOT
    / "runtime_audit_state.json"
)

AUDIT_REPORT_PATH = (
    COMPILED_ROOT
    / "runtime_audit_report.json"
)

AUDIT_MANIFEST_PATH = (
    COMPILED_ROOT
    / "runtime_audit_manifest.json"
)

EXECUTION_ORDER = (
    "lexicon",
    "ontology",
    "kindred",
    "instance",
    "segue",
    "projection",
    "constitution",
)

ACTION_ORDER = (
    "validate",
    "compile",
    "integrity",
)


class RuntimeAuditError(
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

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(
                path.parent
            ),
        )
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

    line = canonical_json(
        payload
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            line
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
                raise RuntimeAuditError(
                    f"Invalid JSONL at "
                    f"{path}:{line_number}: "
                    f"{error}"
                ) from error

            if not isinstance(
                payload,
                dict,
            ):
                raise RuntimeAuditError(
                    f"Audit record must be an object "
                    f"at {path}:{line_number}"
                )

            records.append(
                payload
            )

    return records


def command_text(
    command: Iterable[str],
) -> str:
    return " ".join(
        str(
            part
        )
        for part in command
    )


def parse_json_output(
    stdout: str,
) -> Any:
    text = stdout.strip()

    if not text:
        return None

    try:
        return json.loads(
            text
        )

    except json.JSONDecodeError:
        return None


@dataclass(
    frozen=True
)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(
        self,
    ) -> bool:
        return self.returncode == 0

    def as_dict(
        self,
    ) -> dict[str, Any]:
        parsed = parse_json_output(
            self.stdout
        )

        return {
            "command": list(
                self.command
            ),
            "command_text": command_text(
                self.command
            ),
            "returncode": self.returncode,
            "passed": self.passed,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "parsed_stdout": parsed,
            "stdout_digest": digest(
                self.stdout
            ),
            "stderr_digest": digest(
                self.stderr
            ),
        }


class RuntimeAudit:

    def __init__(
        self,
    ) -> None:
        COMPILED_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

    def controller_path(
        self,
        subsystem: str,
    ) -> Path:
        return (
            BIN_ROOT
            / f"{subsystem}ctl"
        )

    def execute(
        self,
        command: list[str],
    ) -> CommandResult:
        completed = subprocess.run(
            command,
            cwd=str(
                LEXICON_ROOT
            ),
            capture_output=True,
            text=True,
            check=False,
        )

        return CommandResult(
            command=tuple(
                command
            ),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def controller_inventory(
        self,
    ) -> list[dict[str, Any]]:
        records = []

        for position, subsystem in enumerate(
            EXECUTION_ORDER
        ):
            controller = self.controller_path(
                subsystem
            )

            records.append(
                {
                    "subsystem": subsystem,
                    "position": position,
                    "path": str(
                        controller
                    ),
                    "exists": controller.is_file(),
                    "executable": (
                        controller.is_file()
                        and os.access(
                            controller,
                            os.X_OK,
                        )
                    ),
                    "sha256": file_digest(
                        controller
                    ),
                }
            )

        return records

    def source_inventory(
        self,
    ) -> list[dict[str, Any]]:
        records = []

        for path in sorted(
            LEXICON_ROOT.rglob(
                "*"
            )
        ):
            if not path.is_file():
                continue

            if "__pycache__" in path.parts:
                continue

            if path.suffix in {
                ".pyc",
                ".pyo",
            }:
                continue

            relative = path.relative_to(
                LEXICON_ROOT
            )

            records.append(
                {
                    "path": str(
                        path
                    ),
                    "relative_path": str(
                        relative
                    ),
                    "size": path.stat().st_size,
                    "sha256": file_digest(
                        path
                    ),
                    "executable": os.access(
                        path,
                        os.X_OK,
                    ),
                }
            )

        return records

    def preflight(
        self,
    ) -> dict[str, Any]:
        controllers = self.controller_inventory()

        missing = [
            record
            for record in controllers
            if not record[
                "exists"
            ]
        ]

        non_executable = [
            record
            for record in controllers
            if record[
                "exists"
            ]
            and not record[
                "executable"
            ]
        ]

        payload = {
            "operation": "preflight",
            "passed": (
                not missing
                and not non_executable
            ),
            "timestamp": utc_now(),
            "execution_order": list(
                EXECUTION_ORDER
            ),
            "controller_count": len(
                controllers
            ),
            "controllers": controllers,
            "missing": missing,
            "non_executable": non_executable,
            "registry": {
                "path": str(
                    REGISTRY_PATH
                ),
                "exists": REGISTRY_PATH.is_file(),
                "sha256": file_digest(
                    REGISTRY_PATH
                ),
            },
            "address_index": {
                "path": str(
                    ADDRESS_INDEX_PATH
                ),
                "exists": ADDRESS_INDEX_PATH.is_file(),
                "sha256": file_digest(
                    ADDRESS_INDEX_PATH
                ),
            },
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def run_action(
        self,
        subsystem: str,
        action: str,
    ) -> dict[str, Any]:
        if subsystem not in EXECUTION_ORDER:
            raise RuntimeAuditError(
                f"Unknown subsystem: {subsystem}"
            )

        if action not in ACTION_ORDER:
            raise RuntimeAuditError(
                f"Unknown action: {action}"
            )

        controller = self.controller_path(
            subsystem
        )

        started_at = utc_now()

        if not controller.is_file():
            result = {
                "subsystem": subsystem,
                "action": action,
                "started_at": started_at,
                "finished_at": utc_now(),
                "passed": False,
                "returncode": 127,
                "command": [
                    str(
                        controller
                    ),
                    action,
                ],
                "error": (
                    "controller_not_found"
                ),
                "controller": str(
                    controller
                ),
                "controller_sha256": None,
            }

            result[
                "digest"
            ] = digest(
                result
            )

            return result

        command = [
            str(
                controller
            ),
            action,
        ]

        command_result = self.execute(
            command
        )

        result = {
            "subsystem": subsystem,
            "action": action,
            "started_at": started_at,
            "finished_at": utc_now(),
            "controller": str(
                controller
            ),
            "controller_sha256": file_digest(
                controller
            ),
            **command_result.as_dict(),
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def execute_matrix(
        self,
        *,
        actions: tuple[str, ...] = ACTION_ORDER,
        stop_on_failure: bool = False,
    ) -> dict[str, Any]:
        started_at = utc_now()

        results = []

        halted = False

        for subsystem in EXECUTION_ORDER:
            for action in actions:
                result = self.run_action(
                    subsystem,
                    action,
                )

                results.append(
                    result
                )

                if (
                    stop_on_failure
                    and not result[
                        "passed"
                    ]
                ):
                    halted = True
                    break

            if halted:
                break

        failed = [
            result
            for result in results
            if not result[
                "passed"
            ]
        ]

        payload = {
            "operation": "execute_matrix",
            "passed": not failed,
            "started_at": started_at,
            "finished_at": utc_now(),
            "stop_on_failure": stop_on_failure,
            "halted": halted,
            "actions": list(
                actions
            ),
            "execution_order": list(
                EXECUTION_ORDER
            ),
            "result_count": len(
                results
            ),
            "failed_count": len(
                failed
            ),
            "passed_count": (
                len(
                    results
                )
                - len(
                    failed
                )
            ),
            "results": results,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def build_event(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        state = load_json(
            AUDIT_STATE_PATH,
            default={},
        )

        if not isinstance(
            state,
            dict,
        ):
            state = {}

        previous_digest = state.get(
            "head_digest"
        )

        sequence = int(
            state.get(
                "sequence",
                0,
            )
        ) + 1

        event = {
            "event_id": (
                "runtime:audit:event:"
                f"{sequence:012d}"
            ),
            "sequence": sequence,
            "timestamp": utc_now(),
            "operation": report.get(
                "operation"
            ),
            "passed": bool(
                report.get(
                    "passed"
                )
            ),
            "report_digest": report[
                "digest"
            ],
            "previous_digest": previous_digest,
            "provenance": {
                "generator": str(
                    Path(
                        __file__
                    ).resolve()
                ),
                "registry": str(
                    REGISTRY_PATH
                ),
                "runtime_root": str(
                    RUNTIME_ROOT
                ),
            },
            "lineage": {
                "derived_from": [
                    report[
                        "digest"
                    ]
                ],
                "follows": (
                    [
                        previous_digest
                    ]
                    if previous_digest
                    else []
                ),
            },
        }

        event[
            "digest"
        ] = digest(
            event
        )

        return event

    def persist_event(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        event = self.build_event(
            report
        )

        append_jsonl(
            AUDIT_LOG_PATH,
            event,
        )

        state = {
            "state_id": (
                "runtime:audit:state"
            ),
            "sequence": event[
                "sequence"
            ],
            "head_event_id": event[
                "event_id"
            ],
            "head_digest": event[
                "digest"
            ],
            "updated_at": event[
                "timestamp"
            ],
            "log_path": str(
                AUDIT_LOG_PATH
            ),
        }

        state[
            "digest"
        ] = digest(
            state
        )

        write_json_atomic(
            AUDIT_STATE_PATH,
            state,
        )

        return event

    def audit(
        self,
        *,
        actions: tuple[str, ...] = ACTION_ORDER,
        stop_on_failure: bool = False,
    ) -> dict[str, Any]:
        preflight = self.preflight()

        matrix = self.execute_matrix(
            actions=actions,
            stop_on_failure=stop_on_failure,
        )

        sources = self.source_inventory()

        report = {
            "report_id": (
                "runtime:audit:report"
            ),
            "operation": "audit",
            "passed": (
                preflight[
                    "passed"
                ]
                and matrix[
                    "passed"
                ]
            ),
            "timestamp": utc_now(),
            "preflight": preflight,
            "matrix": matrix,
            "source_inventory": {
                "count": len(
                    sources
                ),
                "digest": digest(
                    sources
                ),
                "records": sources,
            },
            "artifacts": {
                "registry": {
                    "path": str(
                        REGISTRY_PATH
                    ),
                    "sha256": file_digest(
                        REGISTRY_PATH
                    ),
                },
                "address_index": {
                    "path": str(
                        ADDRESS_INDEX_PATH
                    ),
                    "sha256": file_digest(
                        ADDRESS_INDEX_PATH
                    ),
                },
            },
            "dependencies": {
                "execution_order": list(
                    EXECUTION_ORDER
                ),
                "actions": list(
                    actions
                ),
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
                    preflight[
                        "digest"
                    ],
                    matrix[
                        "digest"
                    ],
                ]
            },
        }

        report[
            "digest"
        ] = digest(
            report
        )

        event = self.persist_event(
            report
        )

        report[
            "audit_event"
        ] = event

        report[
            "digest"
        ] = digest(
            {
                key: value
                for key, value
                in report.items()
                if key != "digest"
            }
        )

        write_json_atomic(
            AUDIT_REPORT_PATH,
            report,
        )

        manifest = {
            "manifest_id": (
                "runtime:audit:manifest"
            ),
            "timestamp": utc_now(),
            "passed": report[
                "passed"
            ],
            "files": {
                "report": {
                    "path": str(
                        AUDIT_REPORT_PATH
                    ),
                    "sha256": file_digest(
                        AUDIT_REPORT_PATH
                    ),
                },
                "log": {
                    "path": str(
                        AUDIT_LOG_PATH
                    ),
                    "sha256": file_digest(
                        AUDIT_LOG_PATH
                    ),
                },
                "state": {
                    "path": str(
                        AUDIT_STATE_PATH
                    ),
                    "sha256": file_digest(
                        AUDIT_STATE_PATH
                    ),
                },
            },
            "head_event_id": event[
                "event_id"
            ],
            "head_digest": event[
                "digest"
            ],
            "report_digest": report[
                "digest"
            ],
        }

        manifest[
            "digest"
        ] = digest(
            manifest
        )

        write_json_atomic(
            AUDIT_MANIFEST_PATH,
            manifest,
        )

        return report

    def verify_chain(
        self,
    ) -> dict[str, Any]:
        events = read_jsonl(
            AUDIT_LOG_PATH
        )

        issues = []

        previous_digest = None
        expected_sequence = 1

        for position, event in enumerate(
            events
        ):
            sequence = event.get(
                "sequence"
            )

            if sequence != expected_sequence:
                issues.append(
                    {
                        "code": (
                            "sequence_mismatch"
                        ),
                        "position": position,
                        "expected": (
                            expected_sequence
                        ),
                        "actual": sequence,
                    }
                )

            if event.get(
                "previous_digest"
            ) != previous_digest:
                issues.append(
                    {
                        "code": (
                            "previous_digest_mismatch"
                        ),
                        "position": position,
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
                        "position": position,
                        "event_id": event.get(
                            "event_id"
                        ),
                        "expected": (
                            expected_digest
                        ),
                        "actual": event.get(
                            "digest"
                        ),
                    }
                )

            previous_digest = event.get(
                "digest"
            )

            expected_sequence += 1

        state = load_json(
            AUDIT_STATE_PATH,
            default={},
        )

        if not isinstance(
            state,
            dict,
        ):
            state = {}

        if events:
            final_event = events[
                -1
            ]

            if state.get(
                "head_digest"
            ) != final_event.get(
                "digest"
            ):
                issues.append(
                    {
                        "code": (
                            "state_head_mismatch"
                        ),
                        "expected": final_event.get(
                            "digest"
                        ),
                        "actual": state.get(
                            "head_digest"
                        ),
                    }
                )

            if state.get(
                "sequence"
            ) != final_event.get(
                "sequence"
            ):
                issues.append(
                    {
                        "code": (
                            "state_sequence_mismatch"
                        ),
                        "expected": final_event.get(
                            "sequence"
                        ),
                        "actual": state.get(
                            "sequence"
                        ),
                    }
                )

        elif state:
            issues.append(
                {
                    "code": (
                        "state_without_log"
                    ),
                }
            )

        payload = {
            "operation": "verify_chain",
            "passed": not issues,
            "timestamp": utc_now(),
            "event_count": len(
                events
            ),
            "issue_count": len(
                issues
            ),
            "issues": issues,
            "head_digest": previous_digest,
            "state": state,
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
        state = load_json(
            AUDIT_STATE_PATH,
            default={},
        )

        report = load_json(
            AUDIT_REPORT_PATH,
            default={},
        )

        manifest = load_json(
            AUDIT_MANIFEST_PATH,
            default={},
        )

        events = read_jsonl(
            AUDIT_LOG_PATH
        )

        payload = {
            "operation": "status",
            "passed": True,
            "timestamp": utc_now(),
            "paths": {
                "log": str(
                    AUDIT_LOG_PATH
                ),
                "state": str(
                    AUDIT_STATE_PATH
                ),
                "report": str(
                    AUDIT_REPORT_PATH
                ),
                "manifest": str(
                    AUDIT_MANIFEST_PATH
                ),
            },
            "event_count": len(
                events
            ),
            "state": state,
            "latest_report": {
                "exists": bool(
                    report
                ),
                "passed": (
                    report.get(
                        "passed"
                    )
                    if isinstance(
                        report,
                        dict,
                    )
                    else None
                ),
                "digest": (
                    report.get(
                        "digest"
                    )
                    if isinstance(
                        report,
                        dict,
                    )
                    else None
                ),
            },
            "manifest": manifest,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def parse_actions(
    raw_actions: list[str] | None,
) -> tuple[str, ...]:
    if not raw_actions:
        return ACTION_ORDER

    actions = []

    for value in raw_actions:
        for action in value.split(
            ","
        ):
            normalized = action.strip()

            if not normalized:
                continue

            if normalized not in ACTION_ORDER:
                raise RuntimeAuditError(
                    f"Unknown action: {normalized}"
                )

            if normalized not in actions:
                actions.append(
                    normalized
                )

    if not actions:
        raise RuntimeAuditError(
            "No actions selected"
        )

    return tuple(
        actions
    )


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

    subparsers.add_parser(
        "preflight"
    )

    audit_parser = subparsers.add_parser(
        "audit"
    )

    audit_parser.add_argument(
        "--action",
        action="append",
        dest="actions",
    )

    audit_parser.add_argument(
        "--stop-on-failure",
        action="store_true",
    )

    matrix_parser = subparsers.add_parser(
        "matrix"
    )

    matrix_parser.add_argument(
        "--action",
        action="append",
        dest="actions",
    )

    matrix_parser.add_argument(
        "--stop-on-failure",
        action="store_true",
    )

    run_parser = subparsers.add_parser(
        "run"
    )

    run_parser.add_argument(
        "subsystem",
        choices=EXECUTION_ORDER,
    )

    run_parser.add_argument(
        "action",
        choices=ACTION_ORDER,
    )

    subparsers.add_parser(
        "verify"
    )

    subparsers.add_parser(
        "status"
    )

    args = parser.parse_args()

    audit = RuntimeAudit()

    if args.command == "preflight":
        result = audit.preflight()

    elif args.command == "audit":
        result = audit.audit(
            actions=parse_actions(
                args.actions
            ),
            stop_on_failure=(
                args.stop_on_failure
            ),
        )

    elif args.command == "matrix":
        result = audit.execute_matrix(
            actions=parse_actions(
                args.actions
            ),
            stop_on_failure=(
                args.stop_on_failure
            ),
        )

    elif args.command == "run":
        result = audit.run_action(
            args.subsystem,
            args.action,
        )

    elif args.command == "verify":
        result = audit.verify_chain()

    elif args.command == "status":
        result = audit.status()

    else:
        raise RuntimeAuditError(
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

    except RuntimeAuditError as error:
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
