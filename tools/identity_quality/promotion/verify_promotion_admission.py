#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

ADMISSION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "admissions"
)

VERIFICATION_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "admission-verifications"
)

PYTHON = (
    ROOT
    / "bin"
    / "identity-quality-python"
)

IDENTITY_QUALITY = (
    ROOT
    / "bin"
    / "identityqualityctl"
)

PROMOTION_QUEUE = (
    ROOT
    / "bin"
    / "identity-promotionctl"
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

EXPECTED_ROLES = {
    "contracts",
    "runtime",
    "tests",
    "controller",
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


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        value,
        encoding="utf-8",
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
    ).strip(
        "_"
    )


def latest_admission_paths() -> list[Path]:
    if not ADMISSION_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in ADMISSION_ROOT.glob(
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


def latest_admission_path() -> Path:
    paths = latest_admission_paths()

    if not paths:
        raise FileNotFoundError(
            "No promotion admission exists."
        )

    return paths[
        0
    ]


def resolve_admission_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_admission_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = (
            ROOT
            / path
        )

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(
            path
        )

    return path


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


def validate_admission(
    admission: dict[str, Any],
) -> None:
    subject = admission.get(
        "subject"
    )

    if not isinstance(
        subject,
        dict,
    ):
        raise ValueError(
            "Admission has no subject."
        )

    identifier = subject.get(
        "id"
    )

    if (
        not isinstance(
            identifier,
            str,
        )
        or not identifier.strip()
    ):
        raise ValueError(
            "Admission subject has no identifier."
        )

    files = admission.get(
        "files"
    )

    if (
        not isinstance(
            files,
            list,
        )
        or not files
    ):
        raise ValueError(
            "Admission has no files."
        )

    roles = {
        record.get(
            "role"
        )
        for record in files
        if isinstance(
            record,
            dict,
        )
    }

    missing_roles = (
        EXPECTED_ROLES
        - roles
    )

    if missing_roles:
        raise ValueError(
            "Admission lacks roles: "
            + ", ".join(
                sorted(
                    missing_roles
                )
            )
        )


def admitted_file_records(
    admission: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in admission[
        "files"
    ]:
        if not isinstance(
            record,
            dict,
        ):
            continue

        role = record.get(
            "role"
        )

        path = record.get(
            "path"
        )

        if (
            not isinstance(
                role,
                str,
            )
            or not isinstance(
                path,
                str,
            )
        ):
            continue

        result[
            role
        ] = record

    return result


def inspect_file(
    role: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    declared = record.get(
        "path"
    )

    if not isinstance(
        declared,
        str,
    ):
        return {
            "role": role,
            "passed": False,
            "code": (
                "verification.path_missing"
            ),
        }

    path = (
        ROOT
        / declared
    ).resolve()

    exists = path.is_file()

    current_sha256 = (
        sha256_path(
            path
        )
        if exists
        else None
    )

    details = record.get(
        "details"
    )

    expected_sha256 = None

    if isinstance(
        details,
        dict,
    ):
        expected_sha256 = (
            details.get(
                "expected_sha256"
            )
            or details.get(
                "after_sha256"
            )
        )

    state = record.get(
        "state"
    )

    applied = (
        state
        == "written"
    )

    passed = (
        exists
        and (
            expected_sha256
            is None
            or current_sha256
            == expected_sha256
        )
    )

    return {
        "role": role,
        "path": declared,
        "absolute_path": str(
            path
        ),
        "exists": exists,
        "state": state,
        "applied": applied,
        "expected_sha256": (
            expected_sha256
        ),
        "current_sha256": (
            current_sha256
        ),
        "passed": passed,
    }


def build_commands(
    records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    contracts_path = (
        ROOT
        / records[
            "contracts"
        ][
            "path"
        ]
    )

    runtime_path = (
        ROOT
        / records[
            "runtime"
        ][
            "path"
        ]
    )

    tests_path = (
        ROOT
        / records[
            "tests"
        ][
            "path"
        ]
    )

    controller_path = (
        ROOT
        / records[
            "controller"
        ][
            "path"
        ]
    )

    return [
        {
            "id": (
                "python.compile"
            ),
            "command": [
                str(
                    PYTHON
                ),
                "-m",
                "py_compile",
                str(
                    contracts_path
                ),
                str(
                    runtime_path
                ),
                str(
                    tests_path
                ),
                str(
                    controller_path
                ),
            ],
        },
        {
            "id": (
                "subject.tests"
            ),
            "command": [
                str(
                    PYTHON
                ),
                "-m",
                "pytest",
                "-q",
                str(
                    tests_path
                ),
            ],
        },
        {
            "id": (
                "subject.verify"
            ),
            "command": [
                str(
                    controller_path
                ),
                "verify",
            ],
        },
        {
            "id": (
                "identity.audit"
            ),
            "command": [
                str(
                    IDENTITY_QUALITY
                ),
                "audit",
            ],
        },
        {
            "id": (
                "identity.validation"
            ),
            "command": [
                str(
                    IDENTITY_QUALITY
                ),
                "validate",
            ],
        },
        {
            "id": (
                "promotion.queue"
            ),
            "command": [
                str(
                    PROMOTION_QUEUE
                ),
                "strict",
            ],
        },
    ]


def execute_commands(
    commands: list[dict[str, Any]],
    *,
    run_identity_checks: bool,
) -> list[dict[str, Any]]:
    results: list[
        dict[str, Any]
    ] = []

    for operation in commands:
        identifier = operation[
            "id"
        ]

        if (
            not run_identity_checks
            and identifier
            in {
                "identity.audit",
                "identity.validation",
                "promotion.queue",
            }
        ):
            results.append(
                {
                    "id": identifier,
                    "passed": True,
                    "state": (
                        "skipped"
                    ),
                    "reason": (
                        "Identity-wide checks disabled."
                    ),
                    "command": operation[
                        "command"
                    ],
                }
            )

            continue

        result = run_command(
            operation[
                "command"
            ]
        )

        result[
            "id"
        ] = identifier

        result[
            "state"
        ] = (
            "completed"
            if result[
                "passed"
            ]
            else "failed"
        )

        results.append(
            result
        )

        if not result[
            "passed"
        ]:
            break

    return results


def verify_admission(
    admission_path: Path,
    *,
    run_identity_checks: bool,
) -> dict[str, Any]:
    admission = load_json(
        admission_path
    )

    validate_admission(
        admission
    )

    records = admitted_file_records(
        admission
    )

    file_results = [
        inspect_file(
            role,
            records[
                role
            ],
        )
        for role in sorted(
            EXPECTED_ROLES
        )
    ]

    files_passed = all(
        record[
            "passed"
        ]
        for record in file_results
    )

    applied = all(
        record[
            "applied"
        ]
        for record in file_results
    )

    command_results: list[
        dict[str, Any]
    ] = []

    if files_passed and applied:
        commands = build_commands(
            records
        )

        command_results = execute_commands(
            commands,
            run_identity_checks=(
                run_identity_checks
            ),
        )

    commands_passed = (
        bool(
            command_results
        )
        and all(
            result[
                "passed"
            ]
            for result in command_results
        )
    )

    passed = all(
        (
            admission.get(
                "mode"
            )
            == "apply",
            admission.get(
                "passed"
            )
            is True,
            files_passed,
            applied,
            commands_passed,
        )
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-admission-verification/1.0.0"
        ),
        "operation": (
            "verify_promotion_admission"
        ),
        "generated_at": utc_now(),
        "admission": {
            "path": relative_path(
                admission_path
            ),
            "sha256": sha256_path(
                admission_path
            ),
            "digest": admission.get(
                "digest"
            ),
            "mode": admission.get(
                "mode"
            ),
            "passed": admission.get(
                "passed"
            ),
        },
        "subject": admission[
            "subject"
        ],
        "files": {
            "passed": files_passed,
            "applied": applied,
            "records": file_results,
        },
        "commands": {
            "passed": commands_passed,
            "identity_checks_enabled": (
                run_identity_checks
            ),
            "results": command_results,
        },
        "passed": passed,
        "statistics": {
            "file_count": len(
                file_results
            ),
            "file_passed_count": sum(
                record[
                    "passed"
                ]
                for record in file_results
            ),
            "command_count": len(
                command_results
            ),
            "command_passed_count": sum(
                result[
                    "passed"
                ]
                for result in command_results
            ),
            "command_failed_count": sum(
                not result[
                    "passed"
                ]
                for result in command_results
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

    return result


def markdown(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Promotion Admission Verification",
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
            f"- Passed: "
            f"**{result['passed']}**"
        ),
        (
            f"- Digest: "
            f"`{result['digest']}`"
        ),
        "",
        "## Files",
        "",
    ]

    for record in result[
        "files"
    ][
        "records"
    ]:
        lines.extend(
            [
                (
                    f"### `{record['role']}`"
                ),
                "",
                (
                    f"- Path: "
                    f"`{record['path']}`"
                ),
                (
                    f"- Applied: "
                    f"`{record['applied']}`"
                ),
                (
                    f"- Passed: "
                    f"**{record['passed']}**"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Commands",
            "",
        ]
    )

    for record in result[
        "commands"
    ][
        "results"
    ]:
        lines.extend(
            [
                (
                    f"### `{record['id']}`"
                ),
                "",
                (
                    f"- State: "
                    f"`{record['state']}`"
                ),
                (
                    f"- Passed: "
                    f"**{record['passed']}**"
                ),
                "",
            ]
        )

    return "\n".join(
        lines
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify an applied identity promotion "
            "content admission."
        )
    )

    parser.add_argument(
        "--admission",
        type=Path,
    )

    parser.add_argument(
        "--skip-identity-checks",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=(
            VERIFICATION_ROOT
        ),
    )

    arguments = parser.parse_args()

    try:
        admission_path = (
            resolve_admission_path(
                arguments.admission
            )
        )

        result = verify_admission(
            admission_path,
            run_identity_checks=(
                not arguments
                .skip_identity_checks
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "verify_promotion_admission"
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
            "admission-verification.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "admission-verification.md"
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

    write_json(
        json_path,
        result,
    )

    write_json(
        latest_json,
        result,
    )

    rendered = markdown(
        result
    )

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
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
        "passed": (
            result[
                "passed"
            ]
        ),
        "verification_digest": (
            result[
                "digest"
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

    write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "verify_promotion_admission"
                ),
                "passed": (
                    result[
                        "passed"
                    ]
                ),
                "subject": (
                    result[
                        "subject"
                    ]
                ),
                "digest": (
                    result[
                        "digest"
                    ]
                ),
                "statistics": (
                    result[
                        "statistics"
                    ]
                ),
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
