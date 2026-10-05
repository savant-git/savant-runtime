#!/usr/bin/env python3
"""
Restore the historical TERMINAL_READY_STATES compatibility name.

The current implementation renamed TERMINAL_READY_STATES to READY_STATES while
the existing verified test and possible external dependents still reference the
historical public name.

This migration extends the implementation with an immutable compatibility alias.
It does not duplicate state data or alter behavior.
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
    / "tools"
    / "niche"
    / "masterplan"
    / "inspect_masterplan_opus_binding_state.py"
)

REPORT_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-status-compatibility"
)

ANCHOR: Final[str] = '''\
STATE_FIELDS: Final[
    dict[str, tuple[str, ...]]
] = {
'''

COMPATIBILITY_BLOCK: Final[str] = '''\
# Historical public name retained as a compatibility projection.
# READY_STATES remains the single substantiated state mapping.
TERMINAL_READY_STATES: Final[
    dict[str, tuple[str, ...]]
] = READY_STATES


'''

EXPECTED_ALIAS: Final[str] = (
    "TERMINAL_READY_STATES"
    ": Final["
)


class RepairError(RuntimeError):
    """Raised when compatibility repair cannot proceed safely."""


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


def pretty_json_bytes(
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
    content: bytes,
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
                content
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


def validate_baseline(
    content: str,
) -> None:
    if "READY_STATES: Final[" not in content:
        raise RepairError(
            "current implementation lacks READY_STATES"
        )

    if EXPECTED_ALIAS in content:
        raise RepairError(
            "compatibility alias is already present"
        )

    if content.count(
        ANCHOR
    ) != 1:
        raise RepairError(
            "expected exactly one STATE_FIELDS anchor"
        )

    if "inspector = load_module()" in content:
        raise RepairError(
            "implementation still contains recursive test-loader code"
        )

    first_line = content.splitlines()[0]

    if first_line != "#!/usr/bin/env python3":
        raise RepairError(
            f"invalid implementation shebang: {first_line!r}"
        )


def build_candidate(
    content: str,
) -> str:
    candidate = content.replace(
        ANCHOR,
        COMPATIBILITY_BLOCK
        + ANCHOR,
        1,
    )

    if candidate == content:
        raise RepairError(
            "compatibility insertion produced no change"
        )

    if candidate.count(
        EXPECTED_ALIAS
    ) != 1:
        raise RepairError(
            "candidate lacks exactly one compatibility alias"
        )

    restored = candidate.replace(
        COMPATIBILITY_BLOCK,
        "",
        1,
    )

    if restored != content:
        raise RepairError(
            "candidate changes content outside compatibility block"
        )

    return candidate


def compile_candidate(
    content: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="savant-opus-status-compatibility-"
    ) as raw_directory:
        candidate_path = (
            Path(
                raw_directory
            )
            / TARGET.name
        )

        candidate_path.write_text(
            content,
            encoding="utf-8",
        )

        try:
            py_compile.compile(
                str(
                    candidate_path
                ),
                doraise=True,
            )
        except py_compile.PyCompileError as error:
            raise RepairError(
                f"candidate syntax validation failed: {error}"
            ) from error


def write_receipt(
    *,
    before_digest: str,
    after_digest: str,
    baseline_path: Path,
) -> Path:
    timestamp = utc_timestamp()

    run_root = (
        REPORT_ROOT
        / timestamp
    )

    receipt_path = (
        run_root
        / "receipt.json"
    )

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    receipt = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-status-compatibility-repair/1.0.0"
        ),
        "operation": (
            "repair_masterplan_opus_status_compatibility"
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
        "compatibility_alias": (
            "TERMINAL_READY_STATES"
        ),
        "canonical_primitive": (
            "READY_STATES"
        ),
        "duplicate_state_storage": False,
        "authority_effect": "none",
        "implementation_mutation_performed": True,
        "timestamp": timestamp,
    }

    atomic_write(
        receipt_path,
        pretty_json_bytes(
            receipt
        ),
        0o644,
    )

    latest = {
        "operation": receipt[
            "operation"
        ],
        "passed": True,
        "receipt": str(
            receipt_path
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
        "implementation_mutation_performed": True,
        "timestamp": timestamp,
    }

    atomic_write(
        latest_path,
        pretty_json_bytes(
            latest
        ),
        0o644,
    )

    return latest_path


def main() -> int:
    if not TARGET.is_file():
        raise RepairError(
            f"target missing: {TARGET}"
        )

    before_bytes = TARGET.read_bytes()

    try:
        before = before_bytes.decode(
            "utf-8"
        )
    except UnicodeDecodeError as error:
        raise RepairError(
            "target is not valid UTF-8"
        ) from error

    validate_baseline(
        before
    )

    candidate = build_candidate(
        before
    )

    compile_candidate(
        candidate
    )

    timestamp = utc_timestamp()

    baseline_path = (
        REPORT_ROOT
        / timestamp
        / (
            TARGET.name
            + ".before"
        )
    )

    target_mode = (
        TARGET.stat().st_mode
        & 0o777
    )

    atomic_write(
        baseline_path,
        before_bytes,
        target_mode,
    )

    before_digest = sha256_bytes(
        before_bytes
    )

    if sha256_bytes(
        baseline_path.read_bytes()
    ) != before_digest:
        raise RepairError(
            "baseline preservation failed"
        )

    candidate_bytes = candidate.encode(
        "utf-8"
    )

    atomic_write(
        TARGET,
        candidate_bytes,
        target_mode,
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
            target_mode,
        )

        raise RepairError(
            "live syntax validation failed; "
            f"baseline restored: {error}"
        ) from error

    after_digest = sha256_bytes(
        TARGET.read_bytes()
    )

    if after_digest != sha256_bytes(
        candidate_bytes
    ):
        atomic_write(
            TARGET,
            before_bytes,
            target_mode,
        )

        raise RepairError(
            "post-write digest mismatch; baseline restored"
        )

    latest_path = write_receipt(
        before_digest=before_digest,
        after_digest=after_digest,
        baseline_path=baseline_path,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "repair_masterplan_opus_status_compatibility"
                ),
                "passed": True,
                "target": str(
                    TARGET
                ),
                "canonical_primitive": (
                    "READY_STATES"
                ),
                "compatibility_alias": (
                    "TERMINAL_READY_STATES"
                ),
                "duplicate_state_storage": False,
                "before_sha256": before_digest,
                "after_sha256": after_digest,
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
    except RepairError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        "repair_masterplan_opus_status_compatibility"
                    ),
                    "passed": False,
                    "authority_effect": "none",
                    "implementation_mutation_performed": False,
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
