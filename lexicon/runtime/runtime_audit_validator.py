#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

COMPILED_ROOT = (
    RUNTIME_ROOT
    / "compiled"
)

REPORT_PATH = (
    COMPILED_ROOT
    / "runtime_audit_report.json"
)

MANIFEST_PATH = (
    COMPILED_ROOT
    / "runtime_audit_manifest.json"
)

STATE_PATH = (
    COMPILED_ROOT
    / "runtime_audit_state.json"
)

LOG_PATH = (
    COMPILED_ROOT
    / "runtime_audit.jsonl"
)


class RuntimeAuditValidationError(
    RuntimeError
):
    pass


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
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            str(path)
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(
            handle
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeAuditValidationError(
            f"Expected object root: {path}"
        )

    return payload


def read_events(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    events = []

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
                raise RuntimeAuditValidationError(
                    f"Invalid JSONL at "
                    f"{path}:{line_number}: "
                    f"{error}"
                ) from error

            if not isinstance(
                payload,
                dict,
            ):
                raise RuntimeAuditValidationError(
                    f"Invalid event at "
                    f"{path}:{line_number}"
                )

            events.append(
                payload
            )

    return events


def validate_digest(
    payload: dict[str, Any],
) -> bool:
    expected = digest(
        {
            key: value
            for key, value
            in payload.items()
            if key != "digest"
        }
    )

    return payload.get(
        "digest"
    ) == expected


def validate() -> dict[str, Any]:
    issues = []

    required_files = (
        REPORT_PATH,
        MANIFEST_PATH,
        STATE_PATH,
        LOG_PATH,
    )

    for path in required_files:
        if not path.is_file():
            issues.append(
                {
                    "code": "missing_file",
                    "path": str(
                        path
                    ),
                }
            )

    if issues:
        result = {
            "operation": "validate",
            "passed": False,
            "issue_count": len(
                issues
            ),
            "issues": issues,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    report = load_json(
        REPORT_PATH
    )

    manifest = load_json(
        MANIFEST_PATH
    )

    state = load_json(
        STATE_PATH
    )

    events = read_events(
        LOG_PATH
    )

    if not validate_digest(
        report
    ):
        issues.append(
            {
                "code": (
                    "report_digest_mismatch"
                ),
                "path": str(
                    REPORT_PATH
                ),
            }
        )

    if not validate_digest(
        manifest
    ):
        issues.append(
            {
                "code": (
                    "manifest_digest_mismatch"
                ),
                "path": str(
                    MANIFEST_PATH
                ),
            }
        )

    if not validate_digest(
        state
    ):
        issues.append(
            {
                "code": (
                    "state_digest_mismatch"
                ),
                "path": str(
                    STATE_PATH
                ),
            }
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
                    "sequence": event.get(
                        "sequence"
                    ),
                    "expected": previous_digest,
                    "actual": event.get(
                        "previous_digest"
                    ),
                }
            )

        if not validate_digest(
            event
        ):
            issues.append(
                {
                    "code": (
                        "event_digest_mismatch"
                    ),
                    "sequence": event.get(
                        "sequence"
                    ),
                }
            )

        previous_digest = event.get(
            "digest"
        )

    if events:
        head = events[
            -1
        ]

        if state.get(
            "head_digest"
        ) != head.get(
            "digest"
        ):
            issues.append(
                {
                    "code": (
                        "state_head_digest_mismatch"
                    ),
                    "expected": head.get(
                        "digest"
                    ),
                    "actual": state.get(
                        "head_digest"
                    ),
                }
            )

        if state.get(
            "sequence"
        ) != head.get(
            "sequence"
        ):
            issues.append(
                {
                    "code": (
                        "state_sequence_mismatch"
                    ),
                    "expected": head.get(
                        "sequence"
                    ),
                    "actual": state.get(
                        "sequence"
                    ),
                }
            )

    report_file = manifest.get(
        "files",
        {}
    ).get(
        "report",
        {}
    )

    log_file = manifest.get(
        "files",
        {}
    ).get(
        "log",
        {}
    )

    state_file = manifest.get(
        "files",
        {}
    ).get(
        "state",
        {}
    )

    expected_file_digests = (
        (
            REPORT_PATH,
            report_file.get(
                "sha256"
            ),
        ),
        (
            LOG_PATH,
            log_file.get(
                "sha256"
            ),
        ),
        (
            STATE_PATH,
            state_file.get(
                "sha256"
            ),
        ),
    )

    for path, expected_sha256 in (
        expected_file_digests
    ):
        actual_sha256 = file_digest(
            path
        )

        if actual_sha256 != expected_sha256:
            issues.append(
                {
                    "code": (
                        "manifest_file_digest_mismatch"
                    ),
                    "path": str(
                        path
                    ),
                    "expected": (
                        expected_sha256
                    ),
                    "actual": actual_sha256,
                }
            )

    result = {
        "operation": "validate",
        "passed": not issues,
        "issue_count": len(
            issues
        ),
        "event_count": len(
            events
        ),
        "head_digest": previous_digest,
        "report_passed": report.get(
            "passed"
        ),
        "issues": issues,
    }

    result[
        "digest"
    ] = digest(
        result
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        nargs="?",
        default="validate",
        choices=[
            "validate"
        ],
    )

    parser.parse_args()

    result = validate()

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )

    return (
        0
        if result[
            "passed"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
