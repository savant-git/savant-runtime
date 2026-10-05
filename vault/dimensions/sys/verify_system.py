#!/usr/bin/env python3
"""
Integrated verifier for the Savant dimensional archive subsystem.

This verifier checks:

- required implementation files
- Python syntax
- JSON syntax
- registry integrity
- focused unit tests
- dimensional runtime verification
- latest report integrity
- nine-dimensional directory structure
- absence of forbidden legacy paths
- generated-record count
- exclusion of sys from the dimension registry

It performs no mutation.
"""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Final, Sequence


SAVANT_ROOT: Final[Path] = Path("/root/savant-runtime")
DIMENSIONS_ROOT: Final[Path] = (
    SAVANT_ROOT / "vault" / "dimensions"
)
SYS_ROOT: Final[Path] = DIMENSIONS_ROOT / "sys"

REGISTRY_PATH: Final[Path] = (
    SYS_ROOT / "dimension_registry.json"
)
SCHEMA_PATH: Final[Path] = (
    SYS_ROOT
    / "schemas"
    / "dimensional-record.schema.json"
)
REPORT_PATH: Final[Path] = (
    SYS_ROOT / "reports" / "latest.json"
)

PYTHON_FILES: Final[tuple[Path, ...]] = (
    SYS_ROOT / "__init__.py",
    SYS_ROOT / "scaffold.py",
    SYS_ROOT / "dimensionsctl.py",
    SYS_ROOT / "lexeme_audit.py",
    SYS_ROOT / "report_check.py",
    SYS_ROOT / "verify_system.py",
    SYS_ROOT / "tests" / "test_scaffold.py",
)

REQUIRED_FILES: Final[tuple[Path, ...]] = (
    SYS_ROOT / "VERSION",
    SYS_ROOT / "__init__.py",
    SYS_ROOT / "README.md",
    REGISTRY_PATH,
    SCHEMA_PATH,
    SYS_ROOT / "scaffold.py",
    SYS_ROOT / "dimensionsctl.py",
    SYS_ROOT / "lexeme_audit.py",
    SYS_ROOT / "report_check.py",
    SYS_ROOT / "tests" / "test_scaffold.py",
)

DIMENSION_KEYS: Final[tuple[str, ...]] = (
    "canon",
    "context",
    "motive",
    "proof",
    "seed",
    "sense",
    "signal",
    "trajectory",
    "affinity",
)

GENERATED_DIMENSIONS: Final[tuple[str, ...]] = (
    "context",
    "motive",
    "proof",
    "seed",
    "sense",
    "signal",
    "trajectory",
    "affinity",
)

FORBIDDEN_PATHS: Final[tuple[Path, ...]] = (
    SAVANT_ROOT / "canon",
    SAVANT_ROOT / "context",
    SAVANT_ROOT / "motive",
    SAVANT_ROOT / "proof",
    SAVANT_ROOT / "seed",
    SAVANT_ROOT / "sense",
    SAVANT_ROOT / "signal",
    SAVANT_ROOT / "trajectory",
    SAVANT_ROOT / "affinity",
    SAVANT_ROOT / "dimensions",
)


class VerificationFailure(RuntimeError):
    """Raised when an integrated verification requirement fails."""


def load_json(path: Path) -> object:
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except FileNotFoundError as error:
        raise VerificationFailure(
            f"Required JSON file is missing: {path}"
        ) from error
    except json.JSONDecodeError as error:
        raise VerificationFailure(
            f"Invalid JSON in {path}: {error}"
        ) from error


def run_command(
    command: Sequence[str],
    description: str,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise VerificationFailure(
            "\n".join(
                [
                    f"{description} failed.",
                    f"Command: {' '.join(command)}",
                    f"Exit code: {result.returncode}",
                    "STDOUT:",
                    result.stdout.rstrip(),
                    "STDERR:",
                    result.stderr.rstrip(),
                ]
            )
        )

    return result


def verify_required_files() -> None:
    missing = [
        str(path)
        for path in REQUIRED_FILES
        if not path.is_file()
    ]

    if missing:
        raise VerificationFailure(
            "Missing required subsystem files:\n- "
            + "\n- ".join(missing)
        )


def verify_python_syntax() -> None:
    for path in PYTHON_FILES:
        if not path.is_file():
            raise VerificationFailure(
                f"Python file is missing: {path}"
            )

        try:
            py_compile.compile(
                str(path),
                doraise=True,
            )
        except py_compile.PyCompileError as error:
            raise VerificationFailure(
                f"Python syntax validation failed: {path}\n{error}"
            ) from error


def verify_json_syntax() -> None:
    load_json(REGISTRY_PATH)
    load_json(SCHEMA_PATH)


def verify_registry() -> dict[str, object]:
    value = load_json(REGISTRY_PATH)

    if not isinstance(value, dict):
        raise VerificationFailure(
            "Dimension registry must be a JSON object."
        )

    dimensions = value.get("dimensions")

    if not isinstance(dimensions, list):
        raise VerificationFailure(
            "Dimension registry lacks a dimensions array."
        )

    if len(dimensions) != 9:
        raise VerificationFailure(
            f"Expected 9 dimensions; found {len(dimensions)}."
        )

    keys: list[str] = []
    names: list[str] = []
    generated_count = 0

    for index, dimension in enumerate(
        dimensions,
        start=1,
    ):
        if not isinstance(dimension, dict):
            raise VerificationFailure(
                f"Dimension {index} is not an object."
            )

        key = dimension.get("key")
        name = dimension.get("name")
        ordinal = dimension.get("ordinal")
        generated = dimension.get("generated")

        if not isinstance(key, str):
            raise VerificationFailure(
                f"Dimension {index} has no valid key."
            )

        if not isinstance(name, str):
            raise VerificationFailure(
                f"Dimension {index} has no valid name."
            )

        if ordinal != index:
            raise VerificationFailure(
                f"Dimension {key} has ordinal {ordinal}; "
                f"expected {index}."
            )

        if generated is True:
            generated_count += 1

        keys.append(key)
        names.append(name)

    if tuple(keys) != DIMENSION_KEYS:
        raise VerificationFailure(
            "Dimension order mismatch.\n"
            f"Expected: {list(DIMENSION_KEYS)}\n"
            f"Actual: {keys}"
        )

    if len(set(keys)) != 9:
        raise VerificationFailure(
            "Dimension keys are not globally unique."
        )

    if len(set(names)) != 9:
        raise VerificationFailure(
            "Dimension names are not globally unique."
        )

    if "sys" in keys:
        raise VerificationFailure(
            "sys is incorrectly registered as a dimension."
        )

    if generated_count != 8:
        raise VerificationFailure(
            f"Expected 8 generated dimensions; found {generated_count}."
        )

    aliases = value.get(
        "legacy_compatibility_aliases"
    )

    if not isinstance(aliases, dict):
        raise VerificationFailure(
            "Registry lacks legacy compatibility aliases."
        )

    if aliases.get("kinship") != "kindred":
        raise VerificationFailure(
            "Registry must resolve kinship to kindred."
        )

    return value


def verify_directory_structure() -> None:
    if not DIMENSIONS_ROOT.is_dir():
        raise VerificationFailure(
            f"Dimensions root is missing: {DIMENSIONS_ROOT}"
        )

    if not SYS_ROOT.is_dir():
        raise VerificationFailure(
            f"System root is missing: {SYS_ROOT}"
        )

    for key in DIMENSION_KEYS:
        path = DIMENSIONS_ROOT / key

        if not path.is_dir():
            raise VerificationFailure(
                f"Dimension directory is missing: {path}"
            )

    for path in FORBIDDEN_PATHS:
        if path.exists() or path.is_symlink():
            raise VerificationFailure(
                f"Forbidden legacy path remains: {path}"
            )


def verify_unit_tests() -> None:
    run_command(
        (
            sys.executable,
            "-m",
            "unittest",
            "-v",
            str(
                SYS_ROOT
                / "tests"
                / "test_scaffold.py"
            ),
        ),
        "Focused unit tests",
    )


def verify_runtime() -> None:
    run_command(
        (
            sys.executable,
            str(SYS_ROOT / "dimensionsctl.py"),
            "verify",
        ),
        "Dimensional runtime verification",
    )


def verify_latest_report() -> dict[str, object]:
    report = load_json(REPORT_PATH)

    if not isinstance(report, dict):
        raise VerificationFailure(
            "Latest report must be a JSON object."
        )

    operation = report.get("operation")
    canon_count = report.get(
        "canon_object_count"
    )
    failure_count = report.get(
        "failure_count"
    )

    if operation != "verify":
        raise VerificationFailure(
            f"Latest report operation is {operation!r}; "
            "expected 'verify'."
        )

    if not isinstance(canon_count, int):
        raise VerificationFailure(
            "Latest report has no integer canon object count."
        )

    if canon_count <= 0:
        raise VerificationFailure(
            "Canon object count must be positive."
        )

    if failure_count != 0:
        raise VerificationFailure(
            f"Latest report contains {failure_count} failures:\n"
            + "\n".join(
                str(item)
                for item in report.get(
                    "failures",
                    [],
                )
            )
        )

    scaffold_action_counts = report.get(
        "scaffold_action_counts"
    )

    if not isinstance(
        scaffold_action_counts,
        dict,
    ):
        raise VerificationFailure(
            "Latest report lacks scaffold action counts."
        )

    expected = canon_count * 8
    unchanged = scaffold_action_counts.get(
        "unchanged",
        0,
    )

    if unchanged != expected:
        raise VerificationFailure(
            f"Expected {expected} unchanged records; "
            f"report contains {unchanged}."
        )

    return report


def count_generated_records() -> int:
    count = 0

    for key in GENERATED_DIMENSIONS:
        root = DIMENSIONS_ROOT / key

        for path in root.rglob(
            "*.dimension.json"
        ):
            if path.is_file() and not path.is_symlink():
                count += 1

    return count


def verify_generated_record_count(
    report: dict[str, object],
) -> None:
    canon_count = report[
        "canon_object_count"
    ]

    if not isinstance(canon_count, int):
        raise VerificationFailure(
            "Canon count is not an integer."
        )

    expected = canon_count * 8
    actual = count_generated_records()

    if actual != expected:
        raise VerificationFailure(
            f"Generated-record count mismatch: "
            f"expected={expected} actual={actual}"
        )


def verify_report_checker() -> None:
    run_command(
        (
            sys.executable,
            str(SYS_ROOT / "report_check.py"),
        ),
        "Standalone report checker",
    )


def main() -> int:
    checks: list[tuple[str, object]] = []

    try:
        verify_required_files()
        checks.append(
            ("required_files", True)
        )

        verify_python_syntax()
        checks.append(
            ("python_syntax", True)
        )

        verify_json_syntax()
        checks.append(
            ("json_syntax", True)
        )

        registry_value = verify_registry()
        checks.append(
            ("registry", True)
        )

        verify_directory_structure()
        checks.append(
            ("directory_structure", True)
        )

        verify_unit_tests()
        checks.append(
            ("unit_tests", True)
        )

        verify_runtime()
        checks.append(
            ("runtime_verify", True)
        )

        report = verify_latest_report()
        checks.append(
            ("latest_report", True)
        )

        verify_generated_record_count(
            report
        )
        checks.append(
            ("generated_record_count", True)
        )

        verify_report_checker()
        checks.append(
            ("report_checker", True)
        )

        result = {
            "operation": "verify_dimension_system",
            "passed": True,
            "dimensions_root": str(
                DIMENSIONS_ROOT
            ),
            "sys_root": str(SYS_ROOT),
            "dimension_count": len(
                registry_value["dimensions"]
            ),
            "canon_object_count": report[
                "canon_object_count"
            ],
            "generated_record_count": (
                count_generated_records()
            ),
            "checks": {
                name: value
                for name, value in checks
            },
        }

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except VerificationFailure as error:
        result = {
            "operation": "verify_dimension_system",
            "passed": False,
            "checks": {
                name: value
                for name, value in checks
            },
            "error": str(error),
        }

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
