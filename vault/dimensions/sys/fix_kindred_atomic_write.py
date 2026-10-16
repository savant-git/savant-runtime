#!/usr/bin/env python3
"""
Compatibility guard for the retired Kindred/Kinship migration repair.

Historical purpose
------------------
This executable formerly patched ``atomic_write()`` inside
``kindred_migration.py`` so the old global Kinship -> Kindred migration could
mutate repository files safely.

That global migration is no longer authoritative.

Current authority
-----------------
Kindred
    Canonical relationship methodology and universal typed relationship
    system.

Kinship
    Active functional relationship-plane service/runtime.

Relationship
------------
    Kinship -> depends_on -> Kindred

Therefore:

- Kinship is not an alias of Kindred.
- Kinship is not superseded by Kindred.
- Kindred is not superseded by Kinship.
- A global textual Kinship -> Kindred rewrite is forbidden.
- This historical repair executable must never patch or restore the obsolete
  mutation implementation.

The filename remains only for compatibility with callers that may still invoke
it. Running it performs a non-mutating integrity check against the current
Kindred/Kinship auditor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Final, Sequence


SAVANT_ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

TARGET: Final[Path] = (
    SAVANT_ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "kindred_migration.py"
)

SELF: Final[Path] = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "fix_kindred_atomic_write.py"
)

REQUIRED_MARKERS: Final[tuple[str, ...]] = (
    "Kinship",
    "Kindred",
    "global_replacement_authorized",
)

FORBIDDEN_ACTIVE_MARKERS: Final[tuple[str, ...]] = (
    'source_lexeme": "kinship"',
    'destination_lexeme": "kindred"',
    '"source_lexeme": "kinship"',
    '"destination_lexeme": "kindred"',
    "def mutate_file(",
    "replace_content(",
)

OBSOLETE_PATCH_MARKERS: Final[tuple[str, ...]] = (
    "FUNCTION_PATTERN",
    "REPLACEMENT =",
    "Replace atomic_write() in kindred_migration.py",
)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def require_file(
    path: Path,
) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"required file missing: {path}"
        )


def compile_file(
    path: Path,
) -> None:
    py_compile.compile(
        str(path),
        doraise=True,
    )


def inspect_target() -> dict[str, object]:
    require_file(TARGET)

    source = TARGET.read_text(
        encoding="utf-8",
        errors="strict",
    )

    required = {
        marker: marker in source
        for marker in REQUIRED_MARKERS
    }

    forbidden = {
        marker: marker in source
        for marker in FORBIDDEN_ACTIVE_MARKERS
    }

    obsolete = {
        marker: marker in source
        for marker in OBSOLETE_PATCH_MARKERS
    }

    return {
        "path": str(TARGET),
        "sha256": sha256_file(
            TARGET
        ),
        "required_markers": required,
        "forbidden_active_markers": forbidden,
        "obsolete_patch_markers": obsolete,
        "required_markers_present": all(
            required.values()
        ),
        "forbidden_active_markers_absent": not any(
            forbidden.values()
        ),
        "obsolete_patch_markers_absent": not any(
            obsolete.values()
        ),
    }


def run_auditor_plan() -> dict[str, object]:
    process = subprocess.run(
        [
            sys.executable,
            str(TARGET),
            "plan",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()

    parsed: object | None = None

    if stdout:
        try:
            parsed = json.loads(
                stdout
            )
        except json.JSONDecodeError:
            parsed = None

    return {
        "command": [
            sys.executable,
            str(TARGET),
            "plan",
        ],
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "json": parsed,
        "passed": (
            process.returncode == 0
        ),
    }


def verify() -> dict[str, object]:
    compile_file(SELF)
    compile_file(TARGET)

    target = inspect_target()
    plan = run_auditor_plan()

    passed = bool(
        target[
            "required_markers_present"
        ]
        and target[
            "forbidden_active_markers_absent"
        ]
        and target[
            "obsolete_patch_markers_absent"
        ]
        and plan["passed"]
    )

    return {
        "schema": (
            "savant://vault/dimensions/"
            "kindred-kinship-repair-guard/1.0.0"
        ),
        "role": (
            "compatibility-guard"
        ),
        "mutation_authorized": False,
        "patch_authorized": False,
        "global_kinship_to_kindred_replacement_authorized": False,
        "kindred": {
            "status": "active",
            "role": (
                "relationship-methodology-system"
            ),
        },
        "kinship": {
            "status": "active",
            "role": (
                "functional-relationship-plane-service"
            ),
            "depends_on": "Kindred",
        },
        "target": target,
        "auditor_plan": plan,
        "passed": passed,
    }


def run_verify() -> int:
    result = verify()

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
        else 1
    )


def run_status() -> int:
    result = inspect_target()

    payload = {
        "schema": (
            "savant://vault/dimensions/"
            "kindred-kinship-repair-guard/"
            "status/1.0.0"
        ),
        "historical_patch_retired": True,
        "mutation_authorized": False,
        "patch_authorized": False,
        "target": result,
    }

    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compatibility guard for the "
            "retired Kinship-to-Kindred "
            "atomic-write repair utility."
        )
    )

    parser.add_argument(
        "operation",
        nargs="?",
        default="verify",
        choices=(
            "verify",
            "status",
        ),
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = build_parser().parse_args(
        argv
    )

    if args.operation == "verify":
        return run_verify()

    if args.operation == "status":
        return run_status()

    raise AssertionError(
        args.operation
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
