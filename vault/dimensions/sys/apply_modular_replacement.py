#!/usr/bin/env python3
"""
Apply verified modular replacement artifacts transactionally.

This tool mutates implementation files only when every replacement unit:

- is marked ready
- has a complete replacement artifact
- has a complete baseline artifact
- matches the current live target digest
- matches its recorded baseline digest
- has a distinct replacement digest
- remains within /root/savant-runtime
- passes replacement syntax validation
- can be rolled back atomically

The operation is all-or-nothing. Any preflight failure prevents every mutation.
Any write or validation failure rolls back every changed target.

Accepted authority and historical reports are never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


ROOT: Final[Path] = Path("/root/savant-runtime").resolve()

SYS_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
)

REPLACEMENT_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-replacement"
)

APPLICATION_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-application"
)

LATEST_REPLACEMENT: Final[Path] = (
    REPLACEMENT_ROOT
    / "latest.json"
)

APPLICATION_STATES: Final[tuple[str, ...]] = (
    "planned",
    "applied",
    "rolled_back",
)

VALIDATION_KINDS: Final[tuple[str, ...]] = (
    "json",
    "python",
    "shell",
)

SUPPORTED_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".json",
        ".md",
        ".py",
        ".sh",
        ".txt",
        ".yaml",
        ".yml",
        ".toml",
    }
)


class ApplicationError(RuntimeError):
    """Raised when transactional replacement cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class ApplicationUnit:
    id: str
    replacement_unit_id: str
    target_path: str
    baseline_path: str
    replacement_path: str
    before_digest: str
    replacement_digest: str
    after_digest: str | None
    validation_kind: str | None
    preflight_passed: bool
    applied: bool
    rolled_back: bool
    blockers: tuple[str, ...]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def atomic_write_bytes(
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
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        temporary.chmod(mode)
        temporary.replace(path)

        directory_descriptor = os.open(
            path.parent,
            os.O_DIRECTORY,
        )

        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    except BaseException:
        temporary.unlink(
            missing_ok=True
        )
        raise


def atomic_write_json(
    path: Path,
    value: object,
) -> None:
    atomic_write_bytes(
        path,
        canonical_json_bytes(value),
        0o644,
    )


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ApplicationError(
            f"required JSON file missing: {path}"
        )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise ApplicationError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise ApplicationError(
            f"JSON root must be an object: {path}"
        )

    return value


def confined_path(
    raw_path: object,
    field: str,
) -> Path:
    if not isinstance(raw_path, str):
        raise ApplicationError(
            f"{field} must be an absolute path"
        )

    path = Path(raw_path)

    if not path.is_absolute():
        raise ApplicationError(
            f"{field} is not absolute: {path}"
        )

    resolved = path.resolve(
        strict=False
    )

    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise ApplicationError(
            f"{field} escapes runtime root: {resolved}"
        ) from error

    return resolved


def resolve_units_path() -> Path:
    latest = load_json(
        LATEST_REPLACEMENT
    )

    if latest.get(
        "implementation_mutation_performed"
    ) is not False:
        raise ApplicationError(
            "replacement packet reports prior implementation mutation"
        )

    if latest.get(
        "implementation_authorized"
    ) is not False:
        raise ApplicationError(
            "replacement compiler improperly authorized implementation"
        )

    raw_units = latest.get(
        "units"
    )

    if not isinstance(raw_units, str):
        raise ApplicationError(
            "latest replacement packet lacks units path"
        )

    units_path = confined_path(
        raw_units,
        "replacement units path",
    )

    if not units_path.is_file():
        raise ApplicationError(
            f"replacement units file missing: {units_path}"
        )

    return units_path


def validation_kind(
    path: Path,
) -> str | None:
    suffix = path.suffix.casefold()

    if suffix == ".json":
        return "json"

    if suffix == ".py":
        return "python"

    if suffix == ".sh":
        return "shell"

    return None


def validate_json_bytes(
    path: Path,
    value: bytes,
) -> None:
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ApplicationError(
            f"replacement is not UTF-8 JSON: {path}"
        ) from error

    try:
        json.loads(decoded)
    except json.JSONDecodeError as error:
        raise ApplicationError(
            f"replacement is invalid JSON: {path}: {error}"
        ) from error


def validate_python_bytes(
    path: Path,
    value: bytes,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="savant-python-validation-"
    ) as raw_directory:
        temporary = (
            Path(raw_directory)
            / path.name
        )

        temporary.write_bytes(value)

        try:
            py_compile.compile(
                str(temporary),
                doraise=True,
            )
        except py_compile.PyCompileError as error:
            raise ApplicationError(
                f"replacement Python syntax failed: {path}: {error}"
            ) from error


def validate_shell_bytes(
    path: Path,
    value: bytes,
) -> None:
    import subprocess

    with tempfile.TemporaryDirectory(
        prefix="savant-shell-validation-"
    ) as raw_directory:
        temporary = (
            Path(raw_directory)
            / path.name
        )

        temporary.write_bytes(value)
        temporary.chmod(0o755)

        process = subprocess.run(
            [
                "/usr/bin/bash",
                "-n",
                str(temporary),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            raise ApplicationError(
                "replacement shell syntax failed: "
                f"{path}: {process.stderr.strip()}"
            )


def validate_replacement_bytes(
    path: Path,
    value: bytes,
) -> str | None:
    kind = validation_kind(path)

    if kind == "json":
        validate_json_bytes(
            path,
            value,
        )

    elif kind == "python":
        validate_python_bytes(
            path,
            value,
        )

    elif kind == "shell":
        validate_shell_bytes(
            path,
            value,
        )

    return kind


def prepare_unit(
    raw_unit: dict[str, Any],
) -> ApplicationUnit:
    replacement_unit_id = raw_unit.get(
        "id"
    )

    if not isinstance(
        replacement_unit_id,
        str,
    ):
        raise ApplicationError(
            "replacement unit lacks stable id"
        )

    target = confined_path(
        raw_unit.get(
            "target_path"
        ),
        "target path",
    )

    baseline = confined_path(
        raw_unit.get(
            "baseline_path"
        ),
        "baseline path",
    )

    replacement = confined_path(
        raw_unit.get(
            "replacement_path"
        ),
        "replacement path",
    )

    blockers: list[str] = []

    if raw_unit.get(
        "state"
    ) != "ready":
        blockers.append(
            "replacement unit is not ready"
        )

    if raw_unit.get(
        "changed"
    ) is not True:
        blockers.append(
            "replacement unit records no content change"
        )

    if raw_unit.get(
        "mutation_performed"
    ) is not False:
        blockers.append(
            "replacement unit already records mutation"
        )

    if raw_unit.get(
        "implementation_authorized"
    ) is not False:
        blockers.append(
            "replacement unit improperly authorizes implementation"
        )

    if target.suffix.casefold() not in SUPPORTED_SUFFIXES:
        blockers.append(
            f"unsupported target suffix: {target.suffix}"
        )

    for required_path, label in (
        (
            target,
            "target",
        ),
        (
            baseline,
            "baseline",
        ),
        (
            replacement,
            "replacement",
        ),
    ):
        if not required_path.is_file():
            blockers.append(
                f"{label} file is missing: {required_path}"
            )

    before_digest = raw_unit.get(
        "before_digest"
    )

    replacement_digest = raw_unit.get(
        "after_digest"
    )

    if not isinstance(
        before_digest,
        str,
    ):
        blockers.append(
            "before digest is missing"
        )
        before_digest = ""

    if not isinstance(
        replacement_digest,
        str,
    ):
        blockers.append(
            "replacement digest is missing"
        )
        replacement_digest = ""

    if target.is_file():
        live_digest = sha256_bytes(
            target.read_bytes()
        )

        if live_digest != before_digest:
            blockers.append(
                "live target digest differs from replacement baseline"
            )

    if baseline.is_file():
        actual_baseline_digest = (
            sha256_bytes(
                baseline.read_bytes()
            )
        )

        if actual_baseline_digest != before_digest:
            blockers.append(
                "preserved baseline digest differs from recorded baseline"
            )

    replacement_bytes: bytes | None = None

    if replacement.is_file():
        replacement_bytes = (
            replacement.read_bytes()
        )

        actual_replacement_digest = (
            sha256_bytes(
                replacement_bytes
            )
        )

        if (
            actual_replacement_digest
            != replacement_digest
        ):
            blockers.append(
                "replacement artifact digest differs from recorded digest"
            )

        if before_digest == replacement_digest:
            blockers.append(
                "replacement digest equals baseline digest"
            )

    detected_validation_kind: str | None = None

    if (
        not blockers
        and replacement_bytes is not None
    ):
        detected_validation_kind = (
            validate_replacement_bytes(
                target,
                replacement_bytes,
            )
        )

    application_id = (
        "application-unit:"
        + sha256_bytes(
            "\x1f".join(
                (
                    replacement_unit_id,
                    str(target),
                    before_digest,
                    replacement_digest,
                )
            ).encode("utf-8")
        )[:24]
    )

    return ApplicationUnit(
        id=application_id,
        replacement_unit_id=(
            replacement_unit_id
        ),
        target_path=str(target),
        baseline_path=str(baseline),
        replacement_path=str(
            replacement
        ),
        before_digest=before_digest,
        replacement_digest=(
            replacement_digest
        ),
        after_digest=None,
        validation_kind=(
            detected_validation_kind
        ),
        preflight_passed=not blockers,
        applied=False,
        rolled_back=False,
        blockers=tuple(
            dict.fromkeys(blockers)
        ),
    )


def rollback_units(
    units: tuple[ApplicationUnit, ...],
) -> tuple[ApplicationUnit, ...]:
    results: list[ApplicationUnit] = []

    for unit in reversed(units):
        target = Path(
            unit.target_path
        )

        baseline = Path(
            unit.baseline_path
        )

        if not baseline.is_file():
            raise ApplicationError(
                f"rollback baseline missing: {baseline}"
            )

        mode = (
            target.stat().st_mode
            & 0o777
            if target.exists()
            else 0o644
        )

        baseline_bytes = (
            baseline.read_bytes()
        )

        atomic_write_bytes(
            target,
            baseline_bytes,
            mode,
        )

        restored_digest = (
            sha256_bytes(
                target.read_bytes()
            )
        )

        if (
            restored_digest
            != unit.before_digest
        ):
            raise ApplicationError(
                f"rollback digest mismatch: {target}"
            )

        results.append(
            ApplicationUnit(
                id=unit.id,
                replacement_unit_id=(
                    unit
                    .replacement_unit_id
                ),
                target_path=(
                    unit.target_path
                ),
                baseline_path=(
                    unit.baseline_path
                ),
                replacement_path=(
                    unit.replacement_path
                ),
                before_digest=(
                    unit.before_digest
                ),
                replacement_digest=(
                    unit
                    .replacement_digest
                ),
                after_digest=(
                    restored_digest
                ),
                validation_kind=(
                    unit.validation_kind
                ),
                preflight_passed=(
                    unit.preflight_passed
                ),
                applied=False,
                rolled_back=True,
                blockers=(),
            )
        )

    return tuple(
        reversed(results)
    )


def apply_units(
    units: tuple[ApplicationUnit, ...],
) -> tuple[ApplicationUnit, ...]:
    applied: list[ApplicationUnit] = []

    try:
        for unit in units:
            target = Path(
                unit.target_path
            )

            replacement = Path(
                unit.replacement_path
            )

            current_digest = (
                sha256_bytes(
                    target.read_bytes()
                )
            )

            if (
                current_digest
                != unit.before_digest
            ):
                raise ApplicationError(
                    f"target changed during application: {target}"
                )

            replacement_bytes = (
                replacement.read_bytes()
            )

            validate_replacement_bytes(
                target,
                replacement_bytes,
            )

            mode = (
                target.stat().st_mode
                & 0o777
            )

            atomic_write_bytes(
                target,
                replacement_bytes,
                mode,
            )

            after_digest = (
                sha256_bytes(
                    target.read_bytes()
                )
            )

            if (
                after_digest
                != unit.replacement_digest
            ):
                raise ApplicationError(
                    f"post-write digest mismatch: {target}"
                )

            validate_replacement_bytes(
                target,
                target.read_bytes(),
            )

            applied.append(
                ApplicationUnit(
                    id=unit.id,
                    replacement_unit_id=(
                        unit
                        .replacement_unit_id
                    ),
                    target_path=(
                        unit.target_path
                    ),
                    baseline_path=(
                        unit.baseline_path
                    ),
                    replacement_path=(
                        unit.replacement_path
                    ),
                    before_digest=(
                        unit.before_digest
                    ),
                    replacement_digest=(
                        unit
                        .replacement_digest
                    ),
                    after_digest=(
                        after_digest
                    ),
                    validation_kind=(
                        unit.validation_kind
                    ),
                    preflight_passed=True,
                    applied=True,
                    rolled_back=False,
                    blockers=(),
                )
            )

        return tuple(applied)

    except BaseException as original_error:
        rollback_candidates = tuple(
            applied
        )

        if rollback_candidates:
            rollback_units(
                rollback_candidates
            )

        raise ApplicationError(
            "application failed and changed targets were rolled back: "
            f"{original_error}"
        ) from original_error


def write_report(
    *,
    operation: str,
    state: str,
    units: tuple[ApplicationUnit, ...],
    replacement_units_path: Path,
) -> dict[str, Any]:
    run_timestamp = utc_timestamp()

    packet_id = (
        "application-packet:"
        + sha256_bytes(
            "\x1f".join(
                (
                    operation,
                    state,
                    str(
                        replacement_units_path
                    ),
                    run_timestamp,
                )
            ).encode("utf-8")
        )[:24]
    )

    run_root = (
        APPLICATION_ROOT
        / run_timestamp
    )

    report_path = (
        run_root
        / "report.json"
    )

    units_path = (
        run_root
        / "units.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        APPLICATION_ROOT
        / "latest.json"
    )

    applied_count = sum(
        unit.applied
        for unit in units
    )

    rolled_back_count = sum(
        unit.rolled_back
        for unit in units
    )

    blocked_count = sum(
        bool(unit.blockers)
        for unit in units
    )

    passed = (
        blocked_count == 0
        and (
            operation == "plan"
            or applied_count
            == len(units)
            or rolled_back_count
            == len(units)
        )
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-application-report/1.0.0"
        ),
        "operation": operation,
        "id": packet_id,
        "timestamp": run_timestamp,
        "passed": passed,
        "state": state,
        "authority_effect": "none",
        "implementation_mutation_performed": (
            applied_count > 0
        ),
        "source_units": str(
            replacement_units_path
        ),
        "unit_count": len(units),
        "applied_count": applied_count,
        "rolled_back_count": (
            rolled_back_count
        ),
        "blocked_count": blocked_count,
        "application_states": list(
            APPLICATION_STATES
        ),
        "validation_kinds": list(
            VALIDATION_KINDS
        ),
    }

    units_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-application-units/1.0.0"
        ),
        "packet_id": packet_id,
        "units": [
            asdict(unit)
            for unit in units
        ],
    }

    atomic_write_json(
        report_path,
        report,
    )

    atomic_write_json(
        units_path,
        units_document,
    )

    manifest_entries = []

    for path in (
        report_path,
        units_path,
    ):
        manifest_entries.append(
            {
                "path": str(path),
                "sha256": sha256_bytes(
                    path.read_bytes()
                ),
                "size": path.stat().st_size,
            }
        )

    atomic_write_json(
        manifest_path,
        {
            "schema": (
                "savant://vault/dimensions/"
                "modular-application-manifest/1.0.0"
            ),
            "packet_id": packet_id,
            "entries": manifest_entries,
        },
    )

    atomic_write_json(
        latest_path,
        {
            "packet_id": packet_id,
            "timestamp": run_timestamp,
            "report": str(report_path),
            "units": str(units_path),
            "manifest": str(
                manifest_path
            ),
            "state": state,
            "passed": passed,
            "unit_count": len(units),
            "applied_count": applied_count,
            "rolled_back_count": (
                rolled_back_count
            ),
            "blocked_count": blocked_count,
            "authority_effect": "none",
            "implementation_mutation_performed": (
                applied_count > 0
            ),
        },
    )

    return {
        "operation": operation,
        "passed": passed,
        "state": state,
        "packet_id": packet_id,
        "unit_count": len(units),
        "applied_count": applied_count,
        "rolled_back_count": (
            rolled_back_count
        ),
        "blocked_count": blocked_count,
        "latest": str(latest_path),
    }


def load_application_units() -> tuple[
    Path,
    tuple[ApplicationUnit, ...],
]:
    units_path = resolve_units_path()
    document = load_json(
        units_path
    )

    raw_units = document.get(
        "units"
    )

    if not isinstance(
        raw_units,
        list,
    ):
        raise ApplicationError(
            "replacement units must be an array"
        )

    units = tuple(
        prepare_unit(raw_unit)
        for raw_unit in raw_units
        if isinstance(
            raw_unit,
            dict,
        )
    )

    if len(units) != len(
        raw_units
    ):
        raise ApplicationError(
            "replacement units contain non-object records"
        )

    identifiers = [
        unit.id
        for unit in units
    ]

    if len(identifiers) != len(
        set(identifiers)
    ):
        raise ApplicationError(
            "application unit identifiers are duplicated"
        )

    return units_path, units


def run_plan() -> dict[str, Any]:
    units_path, units = (
        load_application_units()
    )

    return write_report(
        operation="plan",
        state="planned",
        units=units,
        replacement_units_path=(
            units_path
        ),
    )


def run_apply() -> dict[str, Any]:
    units_path, units = (
        load_application_units()
    )

    blocked = tuple(
        unit
        for unit in units
        if unit.blockers
    )

    if blocked:
        result = write_report(
            operation="apply",
            state="planned",
            units=units,
            replacement_units_path=(
                units_path
            ),
        )

        raise ApplicationError(
            "application preflight failed; "
            f"{len(blocked)} unit(s) remain blocked; "
            f"report={result['latest']}"
        )

    applied = apply_units(
        units
    )

    return write_report(
        operation="apply",
        state="applied",
        units=applied,
        replacement_units_path=(
            units_path
        ),
    )


def run_rollback() -> dict[str, Any]:
    latest = load_json(
        APPLICATION_ROOT
        / "latest.json"
    )

    if latest.get(
        "state"
    ) != "applied":
        raise ApplicationError(
            "latest application is not in applied state"
        )

    raw_units_path = latest.get(
        "units"
    )

    if not isinstance(
        raw_units_path,
        str,
    ):
        raise ApplicationError(
            "latest application lacks units path"
        )

    units_document = load_json(
        confined_path(
            raw_units_path,
            "application units path",
        )
    )

    raw_units = units_document.get(
        "units"
    )

    if not isinstance(
        raw_units,
        list,
    ):
        raise ApplicationError(
            "application units must be an array"
        )

    units = tuple(
        ApplicationUnit(
            id=str(unit["id"]),
            replacement_unit_id=str(
                unit[
                    "replacement_unit_id"
                ]
            ),
            target_path=str(
                unit["target_path"]
            ),
            baseline_path=str(
                unit["baseline_path"]
            ),
            replacement_path=str(
                unit["replacement_path"]
            ),
            before_digest=str(
                unit["before_digest"]
            ),
            replacement_digest=str(
                unit[
                    "replacement_digest"
                ]
            ),
            after_digest=(
                str(
                    unit[
                        "after_digest"
                    ]
                )
                if unit.get(
                    "after_digest"
                )
                is not None
                else None
            ),
            validation_kind=(
                str(
                    unit[
                        "validation_kind"
                    ]
                )
                if unit.get(
                    "validation_kind"
                )
                is not None
                else None
            ),
            preflight_passed=bool(
                unit[
                    "preflight_passed"
                ]
            ),
            applied=bool(
                unit["applied"]
            ),
            rolled_back=bool(
                unit["rolled_back"]
            ),
            blockers=tuple(
                str(value)
                for value in unit.get(
                    "blockers",
                    [],
                )
            ),
        )
        for unit in raw_units
        if isinstance(unit, dict)
    )

    for unit in units:
        target = confined_path(
            unit.target_path,
            "rollback target",
        )

        if (
            sha256_bytes(
                target.read_bytes()
            )
            != unit.replacement_digest
        ):
            raise ApplicationError(
                f"rollback target changed after application: {target}"
            )

    rolled_back = rollback_units(
        units
    )

    return write_report(
        operation="rollback",
        state="rolled_back",
        units=rolled_back,
        replacement_units_path=(
            confined_path(
                raw_units_path,
                "application units path",
            )
        ),
    )


def run_verify() -> dict[str, Any]:
    latest_path = (
        APPLICATION_ROOT
        / "latest.json"
    )

    latest = load_json(
        latest_path
    )

    manifest_path = confined_path(
        latest.get(
            "manifest"
        ),
        "application manifest",
    )

    manifest = load_json(
        manifest_path
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise ApplicationError(
            "application manifest entries must be an array"
        )

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise ApplicationError(
                "application manifest entry must be an object"
            )

        path = confined_path(
            entry.get(
                "path"
            ),
            "manifest entry path",
        )

        expected_digest = entry.get(
            "sha256"
        )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise ApplicationError(
                "manifest entry lacks digest"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise ApplicationError(
                f"manifest digest mismatch: {path}"
            )

    units_path = confined_path(
        latest.get(
            "units"
        ),
        "application units",
    )

    units_document = load_json(
        units_path
    )

    units = units_document.get(
        "units"
    )

    if not isinstance(
        units,
        list,
    ):
        raise ApplicationError(
            "application units must be an array"
        )

    state = latest.get(
        "state"
    )

    for unit in units:
        if not isinstance(
            unit,
            dict,
        ):
            raise ApplicationError(
                "application unit must be an object"
            )

        target = confined_path(
            unit.get(
                "target_path"
            ),
            "verified target",
        )

        expected_digest = (
            unit.get(
                "replacement_digest"
            )
            if state == "applied"
            else unit.get(
                "before_digest"
            )
        )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise ApplicationError(
                "application unit lacks expected live digest"
            )

        actual_digest = sha256_bytes(
            target.read_bytes()
        )

        if actual_digest != expected_digest:
            raise ApplicationError(
                f"live target digest mismatch: {target}"
            )

        validate_replacement_bytes(
            target,
            target.read_bytes(),
        )

    return {
        "operation": "verify",
        "passed": True,
        "state": state,
        "packet_id": latest.get(
            "packet_id"
        ),
        "unit_count": len(units),
        "manifest_entry_count": len(
            entries
        ),
        "authority_effect": "none",
        "implementation_mutation_performed": (
            state == "applied"
        ),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, apply, rollback, or verify modular replacements."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "plan",
            "apply",
            "rollback",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "plan":
            result = run_plan()

        elif arguments.operation == "apply":
            result = run_apply()

        elif arguments.operation == "rollback":
            result = run_rollback()

        else:
            result = run_verify()

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return (
            0
            if result["passed"]
            else 2
        )

    except ApplicationError as error:
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "passed": False,
                    "authority_effect": "none",
                    "error": str(error),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
