#!/usr/bin/env python3
"""
Correct the modular-pipeline audit return-code contract.

The conformance auditor uses:

- 0: audit completed with no blocking findings
- 1: audit completed and produced blocking findings
- 2: audit completed and produced governed non-success state

All three outcomes produce a valid audit report for the migration planner.
The pipeline must continue after them. Syntax failures, missing output, invalid
JSON, signals, and unexpected return codes remain fatal.

This migration changes only the audit Stage declaration in
run_modular_pipeline.py. It preserves the complete previous file and refuses
ambiguous or repeated mutation.
"""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

TARGET: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "run_modular_pipeline.py"
)

REPORT_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-pipeline-contract-migration"
)

OLD_BLOCK: Final[str] = """\
    Stage(
        ordinal=1,
        key="audit",
        script=SYS_ROOT / "audit_modular_conformance.py",
        operation="audit",
        output=REPORT_ROOT / "modular-conformance" / "latest.json",
        acceptable_return_codes=(0, 2),
    ),
"""

NEW_BLOCK: Final[str] = """\
    Stage(
        ordinal=1,
        key="audit",
        script=SYS_ROOT / "audit_modular_conformance.py",
        operation="audit",
        output=REPORT_ROOT / "modular-conformance" / "latest.json",
        acceptable_return_codes=(0, 1, 2),
    ),
"""


class MigrationError(RuntimeError):
    """Raised when the migration cannot be applied deterministically."""


def utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def canonical_json_bytes(
    value: object,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def atomic_write(
    path: Path,
    value: bytes,
    mode: int,
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

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                value
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        temporary.chmod(
            mode
        )

        temporary.replace(
            path
        )

        directory_descriptor = os.open(
            path.parent,
            os.O_DIRECTORY,
        )

        try:
            os.fsync(
                directory_descriptor
            )
        finally:
            os.close(
                directory_descriptor
            )

    except BaseException:
        temporary.unlink(
            missing_ok=True
        )
        raise


def validate_target(
    content: str,
) -> None:
    audit_marker = (
        'key="audit"'
    )

    old_count = content.count(
        OLD_BLOCK
    )

    new_count = content.count(
        NEW_BLOCK
    )

    marker_count = content.count(
        audit_marker
    )

    if marker_count != 1:
        raise MigrationError(
            "expected exactly one audit stage; "
            f"found {marker_count}"
        )

    if old_count == 1 and new_count == 0:
        return

    if old_count == 0 and new_count == 1:
        raise MigrationError(
            "migration is already applied"
        )

    raise MigrationError(
        "audit stage does not match the verified "
        "pre-migration or post-migration form"
    )


def validate_replacement(
    before: str,
    after: str,
) -> None:
    if before == after:
        raise MigrationError(
            "replacement produced no change"
        )

    if after.count(
        NEW_BLOCK
    ) != 1:
        raise MigrationError(
            "replacement does not contain exactly one "
            "corrected audit stage"
        )

    if OLD_BLOCK in after:
        raise MigrationError(
            "historical audit stage remains active"
        )

    restored = after.replace(
        NEW_BLOCK,
        OLD_BLOCK,
        1,
    )

    if restored != before:
        raise MigrationError(
            "replacement changed content outside "
            "the audit return-code contract"
        )


def compile_candidate(
    content: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="savant-pipeline-contract-"
    ) as raw_directory:
        candidate = (
            Path(
                raw_directory
            )
            / TARGET.name
        )

        candidate.write_text(
            content,
            encoding="utf-8",
        )

        try:
            py_compile.compile(
                str(
                    candidate
                ),
                doraise=True,
            )
        except py_compile.PyCompileError as error:
            raise MigrationError(
                "candidate syntax validation failed: "
                f"{error}"
            ) from error


def write_report(
    *,
    timestamp: str,
    before_digest: str,
    after_digest: str,
    baseline_path: Path,
) -> Path:
    report_directory = (
        REPORT_ROOT
        / timestamp
    )

    report_path = (
        report_directory
        / "report.json"
    )

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-pipeline-contract-migration/1.0.0"
        ),
        "operation": (
            "fix_modular_pipeline_audit_return"
        ),
        "passed": True,
        "target": str(
            TARGET
        ),
        "baseline": str(
            baseline_path
        ),
        "before_sha256": before_digest,
        "after_sha256": after_digest,
        "changed_fields": [
            (
                "STAGES[0]."
                "acceptable_return_codes"
            ),
        ],
        "previous_value": [
            0,
            2,
        ],
        "current_value": [
            0,
            1,
            2,
        ],
        "reason": (
            "Audit return code 1 represents a completed "
            "audit with blocking findings. The migration "
            "planner must receive those findings."
        ),
        "authority_effect": "none",
        "finding_suppression": False,
        "implementation_mutation_performed": True,
        "rollback": {
            "source": str(
                baseline_path
            ),
            "expected_restored_sha256": (
                before_digest
            ),
        },
        "timestamp": timestamp,
    }

    atomic_write(
        report_path,
        canonical_json_bytes(
            report
        ),
        0o644,
    )

    latest = {
        "operation": (
            "fix_modular_pipeline_audit_return"
        ),
        "passed": True,
        "report": str(
            report_path
        ),
        "target": str(
            TARGET
        ),
        "baseline": str(
            baseline_path
        ),
        "before_sha256": before_digest,
        "after_sha256": after_digest,
        "authority_effect": "none",
        "finding_suppression": False,
        "implementation_mutation_performed": True,
        "timestamp": timestamp,
    }

    atomic_write(
        latest_path,
        canonical_json_bytes(
            latest
        ),
        0o644,
    )

    return latest_path


def main() -> int:
    if not TARGET.is_file():
        raise MigrationError(
            f"target file missing: {TARGET}"
        )

    before_bytes = TARGET.read_bytes()

    try:
        before = before_bytes.decode(
            "utf-8"
        )
    except UnicodeDecodeError as error:
        raise MigrationError(
            f"target is not UTF-8: {TARGET}"
        ) from error

    validate_target(
        before
    )

    after = before.replace(
        OLD_BLOCK,
        NEW_BLOCK,
        1,
    )

    validate_replacement(
        before,
        after,
    )

    compile_candidate(
        after
    )

    timestamp = utc_timestamp()

    report_directory = (
        REPORT_ROOT
        / timestamp
    )

    baseline_path = (
        report_directory
        / "run_modular_pipeline.py.before"
    )

    atomic_write(
        baseline_path,
        before_bytes,
        TARGET.stat().st_mode
        & 0o777,
    )

    before_digest = sha256_bytes(
        before_bytes
    )

    if sha256_bytes(
        baseline_path.read_bytes()
    ) != before_digest:
        raise MigrationError(
            "baseline verification failed"
        )

    after_bytes = after.encode(
        "utf-8"
    )

    atomic_write(
        TARGET,
        after_bytes,
        TARGET.stat().st_mode
        & 0o777,
    )

    after_digest = sha256_bytes(
        TARGET.read_bytes()
    )

    if after_digest != sha256_bytes(
        after_bytes
    ):
        atomic_write(
            TARGET,
            before_bytes,
            TARGET.stat().st_mode
            & 0o777,
        )

        raise MigrationError(
            "post-write verification failed; "
            "target was restored"
        )

    try:
        py_compile.compile(
            str(
                TARGET
            ),
            doraise=True,
        )
    except py_compile.PyCompileError as error:
        atomic_write(
            TARGET,
            before_bytes,
            TARGET.stat().st_mode
            & 0o777,
        )

        raise MigrationError(
            "live syntax validation failed; "
            f"target was restored: {error}"
        ) from error

    latest_path = write_report(
        timestamp=timestamp,
        before_digest=before_digest,
        after_digest=after_digest,
        baseline_path=baseline_path,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "fix_modular_pipeline_audit_return"
                ),
                "passed": True,
                "target": str(
                    TARGET
                ),
                "before_sha256": before_digest,
                "after_sha256": after_digest,
                "accepted_audit_return_codes": [
                    0,
                    1,
                    2,
                ],
                "finding_suppression": False,
                "latest": str(
                    latest_path
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )
    except MigrationError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        "fix_modular_pipeline_audit_return"
                    ),
                    "passed": False,
                    "error": str(
                        error
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        raise SystemExit(
            1
        )
