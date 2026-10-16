#!/usr/bin/env python3
"""
Bind the latest modular execution packet to the current implementation.

This tool is read-only with respect to authoritative and implementation files.
It records target state, digests, preserved baselines, dependencies, dependents,
and blockers. It never authorizes or performs implementation mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Iterator


ROOT: Final[Path] = Path("/root/savant-runtime")

SYS_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
)

EXECUTION_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-execution"
)

BINDING_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-binding"
)

LATEST_EXECUTION: Final[Path] = (
    EXECUTION_ROOT
    / "latest.json"
)

ACCEPTED_DECISION_ROOT: Final[Path] = (
    ROOT
    / "authority_graph"
    / "accepted_decisions"
    / "modular_architecture"
)

TEXT_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".bash",
        ".cfg",
        ".conf",
        ".css",
        ".csv",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".jsonl",
        ".jsx",
        ".md",
        ".mjs",
        ".py",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)

EXCLUDED_DIRECTORIES: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "node_modules",
        "site-packages",
        "vendor",
        "venv",
    }
)

BINDING_STATES: Final[tuple[str, ...]] = (
    "bound",
    "blocked",
    "ready",
)

READINESS_GATES: Final[tuple[str, ...]] = (
    "accepted_decision_verified",
    "target_resolved",
    "target_exists",
    "target_read",
    "target_digest_recorded",
    "baseline_preserved",
    "dependencies_identified",
    "dependents_identified",
    "semantic_review_complete",
)

MAX_TEXT_BYTES: Final[int] = 4_000_000


class BindingError(RuntimeError):
    """Raised when execution binding cannot complete reliably."""


@dataclass(frozen=True, slots=True)
class ReferenceRecord:
    path: str
    relation: str
    evidence: str
    digest: str | None


@dataclass(frozen=True, slots=True)
class BoundUnit:
    id: str
    execution_unit_id: str
    decision_id: str
    candidate_id: str
    candidate_ordinal: int
    phase: str
    authorized_action: str
    source_path: str
    target_path: str | None
    target_exists: bool
    target_is_file: bool
    target_size: int | None
    compiled_before_digest: str | None
    actual_before_digest: str | None
    digest_matches: bool
    baseline_path: str | None
    baseline_digest: str | None
    dependencies: tuple[ReferenceRecord, ...]
    dependents: tuple[ReferenceRecord, ...]
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    blockers: tuple[str, ...]
    state: str
    mutation_authorized: bool
    implementation_authorized: bool


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def atomic_write_bytes(
    path: Path,
    value: bytes,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_name(f".{path.name}.tmp")

    temporary.write_bytes(value)
    temporary.chmod(mode)
    temporary.replace(path)


def atomic_write_json(
    path: Path,
    value: object,
) -> None:
    atomic_write_bytes(
        path,
        canonical_json_bytes(value),
    )


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BindingError(
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
        raise BindingError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise BindingError(
            f"JSON root must be an object: {path}"
        )

    return value


def resolve_units_path() -> Path:
    latest = load_json(LATEST_EXECUTION)

    raw_path = latest.get("units")

    if not isinstance(raw_path, str):
        raise BindingError(
            "latest execution packet lacks units path"
        )

    path = Path(raw_path)

    if not path.is_file():
        raise BindingError(
            f"execution units file missing: {path}"
        )

    return path


def normalize_target_path(
    raw_path: object,
) -> Path | None:
    if not isinstance(raw_path, str):
        return None

    if not raw_path.strip():
        return None

    path = Path(raw_path)

    if not path.is_absolute():
        path = ROOT / path

    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return None

    return resolved


def accepted_decision_path(
    decision_id: str,
) -> Path:
    return (
        ACCEPTED_DECISION_ROOT
        / f"{decision_id.replace(':', '__')}.json"
    )


def accepted_decision_verified(
    decision_id: str,
) -> bool:
    path = accepted_decision_path(decision_id)

    if not path.is_file():
        return False

    try:
        decision = load_json(path)
    except BindingError:
        return False

    return (
        decision.get("id") == decision_id
        and decision.get("state") == "accepted"
        and decision.get("immutable") is True
        and decision.get("mutation_authorized") is True
    )


def iter_text_files() -> Iterator[Path]:
    for raw_root, directories, file_names in os.walk(
        ROOT,
        topdown=True,
        followlinks=False,
    ):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in EXCLUDED_DIRECTORIES
        )

        current_root = Path(raw_root)

        for file_name in sorted(file_names):
            path = current_root / file_name

            if path.suffix.casefold() not in TEXT_SUFFIXES:
                continue

            try:
                if path.stat().st_size > MAX_TEXT_BYTES:
                    continue
            except OSError:
                continue

            yield path


def read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    if len(raw) > MAX_TEXT_BYTES:
        return None

    if b"\x00" in raw:
        return None

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def file_digest(path: Path) -> str | None:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError:
        return None


def dependency_tokens(target: Path) -> tuple[str, ...]:
    tokens = {
        str(target),
        target.relative_to(ROOT).as_posix(),
        target.name,
        target.stem,
    }

    return tuple(
        sorted(
            token
            for token in tokens
            if len(token) >= 3
        )
    )


def discover_dependents(
    target: Path,
    project_files: tuple[Path, ...],
) -> tuple[ReferenceRecord, ...]:
    tokens = dependency_tokens(target)
    records: list[ReferenceRecord] = []

    for path in project_files:
        if path == target:
            continue

        text = read_text(path)

        if text is None:
            continue

        matched = next(
            (
                token
                for token in tokens
                if token in text
            ),
            None,
        )

        if matched is None:
            continue

        records.append(
            ReferenceRecord(
                path=str(path),
                relation="dependent",
                evidence=f"references {matched!r}",
                digest=file_digest(path),
            )
        )

    return tuple(
        sorted(
            records,
            key=lambda record: record.path,
        )
    )


def discover_dependencies(
    target: Path,
    text: str,
) -> tuple[ReferenceRecord, ...]:
    records: list[ReferenceRecord] = []

    for path in iter_text_files():
        if path == target:
            continue

        relative = path.relative_to(ROOT).as_posix()

        matched = None

        for token in (
            str(path),
            relative,
        ):
            if token in text:
                matched = token
                break

        if matched is None:
            continue

        records.append(
            ReferenceRecord(
                path=str(path),
                relation="dependency",
                evidence=f"target references {matched!r}",
                digest=file_digest(path),
            )
        )

    return tuple(
        sorted(
            records,
            key=lambda record: record.path,
        )
    )


def binding_identity(
    execution_unit_id: str,
    target_path: str | None,
    digest_value: str | None,
) -> str:
    payload = "\x1f".join(
        (
            execution_unit_id,
            target_path or "",
            digest_value or "",
        )
    )

    return (
        "bound-execution-unit:"
        + sha256_text(payload)[:24]
    )


def baseline_path(
    run_root: Path,
    execution_unit_id: str,
    target: Path,
) -> Path:
    safe_identifier = execution_unit_id.replace(
        ":",
        "__",
    )

    suffix = target.suffix or ".bin"

    return (
        run_root
        / "baselines"
        / f"{safe_identifier}{suffix}"
    )


def bind_unit(
    unit: dict[str, Any],
    run_root: Path,
    project_files: tuple[Path, ...],
) -> BoundUnit:
    execution_unit_id = str(
        unit.get("id", "")
    )

    if not execution_unit_id:
        raise BindingError(
            "execution unit lacks stable id"
        )

    decision_id = str(
        unit.get("decision_id", "")
    )

    candidate_ordinal = unit.get(
        "candidate_ordinal"
    )

    if not isinstance(candidate_ordinal, int):
        raise BindingError(
            f"execution unit {execution_unit_id} "
            "lacks integer candidate ordinal"
        )

    target = normalize_target_path(
        unit.get("target_path")
        or unit.get("source_path")
    )

    decision_verified = accepted_decision_verified(
        decision_id
    )

    target_exists = bool(
        target is not None
        and target.exists()
    )

    target_is_file = bool(
        target is not None
        and target.is_file()
    )

    target_bytes: bytes | None = None
    target_text: str | None = None
    actual_digest: str | None = None
    target_size: int | None = None
    preserved_path: str | None = None
    preserved_digest: str | None = None

    if target_is_file and target is not None:
        try:
            target_bytes = target.read_bytes()
        except OSError:
            target_bytes = None

    if target_bytes is not None:
        target_size = len(target_bytes)
        actual_digest = sha256_bytes(target_bytes)

        if (
            len(target_bytes) <= MAX_TEXT_BYTES
            and b"\x00" not in target_bytes
        ):
            try:
                target_text = target_bytes.decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                target_text = None

        saved_baseline = baseline_path(
            run_root,
            execution_unit_id,
            target,
        )

        atomic_write_bytes(
            saved_baseline,
            target_bytes,
        )

        preserved_path = str(saved_baseline)
        preserved_digest = sha256_bytes(
            saved_baseline.read_bytes()
        )

    compiled_digest_value = unit.get(
        "expected_before_digest"
    )

    compiled_digest = (
        compiled_digest_value
        if isinstance(
            compiled_digest_value,
            str,
        )
        else None
    )

    digest_matches = bool(
        compiled_digest is not None
        and actual_digest is not None
        and compiled_digest == actual_digest
    )

    dependencies: tuple[
        ReferenceRecord,
        ...
    ] = ()

    dependents: tuple[
        ReferenceRecord,
        ...
    ] = ()

    if target is not None and target_text is not None:
        dependencies = discover_dependencies(
            target,
            target_text,
        )

        dependents = discover_dependents(
            target,
            project_files,
        )

    gate_results = {
        "accepted_decision_verified": (
            decision_verified
        ),
        "target_resolved": target is not None,
        "target_exists": target_exists,
        "target_read": target_bytes is not None,
        "target_digest_recorded": (
            actual_digest is not None
        ),
        "baseline_preserved": (
            preserved_digest is not None
            and preserved_digest == actual_digest
        ),
        "dependencies_identified": (
            target_text is not None
        ),
        "dependents_identified": (
            target_text is not None
        ),
        "semantic_review_complete": False,
    }

    passed_gates = tuple(
        gate
        for gate in READINESS_GATES
        if gate_results[gate]
    )

    failed_gates = tuple(
        gate
        for gate in READINESS_GATES
        if not gate_results[gate]
    )

    blockers: list[str] = []

    if not decision_verified:
        blockers.append(
            "accepted decision could not be verified"
        )

    if target is None:
        blockers.append(
            "target path is unresolved or outside runtime root"
        )

    if not target_exists:
        blockers.append(
            "target does not exist"
        )

    if target_exists and not target_is_file:
        blockers.append(
            "target is not a regular file"
        )

    if target_bytes is None:
        blockers.append(
            "target content could not be read"
        )

    if actual_digest is None:
        blockers.append(
            "current target digest is unavailable"
        )

    if (
        compiled_digest is not None
        and actual_digest is not None
        and not digest_matches
    ):
        blockers.append(
            "target changed after execution compilation"
        )

    if target_text is None:
        blockers.append(
            "target is not readable UTF-8 text"
        )

    blockers.extend(
        (
            "semantic review is incomplete",
            "replacement content is not compiled",
            "target-specific validation is not bound",
            "target-specific rollback is not bound",
        )
    )

    return BoundUnit(
        id=binding_identity(
            execution_unit_id,
            str(target)
            if target is not None
            else None,
            actual_digest,
        ),
        execution_unit_id=execution_unit_id,
        decision_id=decision_id,
        candidate_id=str(
            unit.get("candidate_id", "")
        ),
        candidate_ordinal=candidate_ordinal,
        phase=str(
            unit.get(
                "phase",
                "verification",
            )
        ),
        authorized_action=str(
            unit.get(
                "authorized_action",
                "",
            )
        ),
        source_path=str(
            unit.get("source_path", "")
        ),
        target_path=(
            str(target)
            if target is not None
            else None
        ),
        target_exists=target_exists,
        target_is_file=target_is_file,
        target_size=target_size,
        compiled_before_digest=compiled_digest,
        actual_before_digest=actual_digest,
        digest_matches=digest_matches,
        baseline_path=preserved_path,
        baseline_digest=preserved_digest,
        dependencies=dependencies,
        dependents=dependents,
        passed_gates=passed_gates,
        failed_gates=failed_gates,
        blockers=tuple(
            dict.fromkeys(blockers)
        ),
        state=(
            "ready"
            if not blockers
            else "blocked"
        ),
        mutation_authorized=(
            unit.get("mutation_authorized")
            is True
        ),
        implementation_authorized=False,
    )


def bind_execution() -> dict[str, Any]:
    units_path = resolve_units_path()
    units_bytes = units_path.read_bytes()

    document = json.loads(
        units_bytes.decode("utf-8")
    )

    units = document.get("units")

    if not isinstance(units, list):
        raise BindingError(
            "execution units must be an array"
        )

    run_timestamp = utc_timestamp()

    run_root = (
        BINDING_ROOT
        / run_timestamp
    )

    project_files = tuple(
        iter_text_files()
    )

    bound_units = tuple(
        bind_unit(
            unit,
            run_root,
            project_files,
        )
        for unit in units
        if isinstance(unit, dict)
    )

    identifiers = [
        unit.id
        for unit in bound_units
    ]

    if len(identifiers) != len(
        set(identifiers)
    ):
        raise BindingError(
            "bound unit identifiers are duplicated"
        )

    states = Counter(
        unit.state
        for unit in bound_units
    )

    dependency_count = sum(
        len(unit.dependencies)
        for unit in bound_units
    )

    dependent_count = sum(
        len(unit.dependents)
        for unit in bound_units
    )

    packet_id = (
        "binding-packet:"
        + sha256_text(
            "\x1f".join(
                (
                    str(units_path),
                    sha256_bytes(units_bytes),
                    run_timestamp,
                )
            )
        )[:24]
    )

    report_path = run_root / "report.json"
    bound_units_path = run_root / "units.json"
    references_path = run_root / "references.json"
    manifest_path = run_root / "manifest.json"
    latest_path = BINDING_ROOT / "latest.json"

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-binding-report/1.0.0"
        ),
        "operation": "bind_modular_execution",
        "id": packet_id,
        "timestamp": run_timestamp,
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "source_units": str(units_path),
        "source_units_digest": sha256_bytes(
            units_bytes
        ),
        "bound_unit_count": len(bound_units),
        "ready_count": states["ready"],
        "blocked_count": states["blocked"],
        "dependency_count": dependency_count,
        "dependent_count": dependent_count,
        "project_text_file_count": len(
            project_files
        ),
        "binding_states": list(
            BINDING_STATES
        ),
        "readiness_gates": list(
            READINESS_GATES
        ),
    }

    units_document = {
        "schema": (
            "savant://vault/dimensions/"
            "bound-modular-units/1.0.0"
        ),
        "packet_id": packet_id,
        "unit_count": len(bound_units),
        "units": [
            asdict(unit)
            for unit in bound_units
        ],
    }

    references_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-binding-references/1.0.0"
        ),
        "packet_id": packet_id,
        "references": [
            {
                "unit_id": unit.id,
                "target_path": unit.target_path,
                "dependencies": [
                    asdict(record)
                    for record in unit.dependencies
                ],
                "dependents": [
                    asdict(record)
                    for record in unit.dependents
                ],
            }
            for unit in bound_units
        ],
    }

    atomic_write_json(
        report_path,
        report,
    )

    atomic_write_json(
        bound_units_path,
        units_document,
    )

    atomic_write_json(
        references_path,
        references_document,
    )

    manifest_candidates = [
        report_path,
        bound_units_path,
        references_path,
    ]

    manifest_candidates.extend(
        Path(unit.baseline_path)
        for unit in bound_units
        if unit.baseline_path is not None
    )

    manifest_entries = []

    for path in manifest_candidates:
        if not path.is_file():
            raise BindingError(
                f"binding output missing: {path}"
            )

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
                "modular-binding-manifest/1.0.0"
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
            "units": str(bound_units_path),
            "references": str(references_path),
            "manifest": str(manifest_path),
            "bound_unit_count": len(bound_units),
            "ready_count": states["ready"],
            "blocked_count": states["blocked"],
            "authority_effect": "none",
            "implementation_mutation_performed": False,
        },
    )

    return {
        "operation": "bind_modular_execution",
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "packet_id": packet_id,
        "bound_unit_count": len(bound_units),
        "ready_count": states["ready"],
        "blocked_count": states["blocked"],
        "dependency_count": dependency_count,
        "dependent_count": dependent_count,
        "latest": str(latest_path),
    }


def verify_latest() -> dict[str, Any]:
    latest_path = (
        BINDING_ROOT
        / "latest.json"
    )

    latest = load_json(latest_path)

    raw_manifest = latest.get("manifest")

    if not isinstance(raw_manifest, str):
        raise BindingError(
            "latest binding packet lacks manifest path"
        )

    manifest = load_json(
        Path(raw_manifest)
    )

    entries = manifest.get("entries")

    if not isinstance(entries, list):
        raise BindingError(
            "binding manifest entries must be an array"
        )

    verified_entries = []

    for entry in entries:
        if not isinstance(entry, dict):
            raise BindingError(
                "manifest entry must be an object"
            )

        raw_path = entry.get("path")
        expected_digest = entry.get("sha256")

        if not isinstance(raw_path, str):
            raise BindingError(
                "manifest entry lacks path"
            )

        if not isinstance(expected_digest, str):
            raise BindingError(
                "manifest entry lacks digest"
            )

        path = Path(raw_path)

        if not path.is_file():
            raise BindingError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise BindingError(
                f"manifest digest mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(path),
                "sha256": actual_digest,
                "passed": True,
            }
        )

    raw_units = latest.get("units")

    if not isinstance(raw_units, str):
        raise BindingError(
            "latest binding packet lacks units path"
        )

    units_document = load_json(
        Path(raw_units)
    )

    units = units_document.get("units")

    if not isinstance(units, list):
        raise BindingError(
            "bound units must be an array"
        )

    unit_ids = []

    for unit in units:
        if not isinstance(unit, dict):
            raise BindingError(
                "bound unit must be an object"
            )

        unit_id = unit.get("id")

        if not isinstance(unit_id, str):
            raise BindingError(
                "bound unit lacks stable id"
            )

        unit_ids.append(unit_id)

        if (
            unit.get(
                "implementation_authorized"
            )
            is not False
        ):
            raise BindingError(
                "bound unit prematurely authorizes implementation: "
                f"{unit_id}"
            )

        state = unit.get("state")

        if state not in BINDING_STATES:
            raise BindingError(
                f"bound unit has invalid state: {unit_id}"
            )

    if len(unit_ids) != len(set(unit_ids)):
        raise BindingError(
            "bound unit identifiers are duplicated"
        )

    return {
        "operation": "verify_modular_binding",
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "packet_id": latest.get("packet_id"),
        "bound_unit_count": len(units),
        "manifest_entry_count": len(
            verified_entries
        ),
        "verified_entries": verified_entries,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bind or verify modular execution units."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "bind",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "bind":
            result = bind_execution()
        else:
            result = verify_latest()

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except BindingError as error:
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "passed": False,
                    "authority_effect": "none",
                    "implementation_mutation_performed": False,
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
