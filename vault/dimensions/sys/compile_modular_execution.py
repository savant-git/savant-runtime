#!/usr/bin/env python3
"""
Compile accepted modular decisions into deterministic execution packets.

This stage does not modify implementation files.

It converts immutable accepted decisions into executable migration units that
record exact preconditions, target paths, dependency discovery requirements,
backup requirements, validation requirements, rollback requirements, and
completion evidence.

An execution unit remains blocked until its current target implementation has
been read and its exact expected digest has been recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final


ROOT: Final[Path] = Path("/root/savant-runtime")

ACCEPTED_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-accepted-decisions"
)

EXECUTION_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-execution"
)

LATEST_ACCEPTED: Final[Path] = (
    ACCEPTED_ROOT
    / "latest.json"
)

EXECUTION_STATES: Final[tuple[str, ...]] = (
    "compiled",
    "blocked",
    "ready",
)

EXECUTION_PHASES: Final[tuple[str, ...]] = (
    "authority",
    "lexicon",
    "instances",
    "moods",
    "slots",
    "projections",
    "duplication",
    "dependencies",
    "verification",
)

REQUIRED_PREFLIGHTS: Final[tuple[str, ...]] = (
    "target_exists_or_creation_is_authorized",
    "current_target_content_read",
    "current_target_digest_recorded",
    "dependencies_identified",
    "dependents_identified",
    "authority_confirmed",
    "compatibility_requirements_recorded",
    "rollback_material_prepared",
    "validation_commands_defined",
)

REQUIRED_EVIDENCE: Final[tuple[str, ...]] = (
    "before_digest",
    "after_digest",
    "syntax_result",
    "focused_test_result",
    "integrated_verification_result",
    "dependency_result",
    "lineage_result",
    "provenance_result",
    "rollback_result",
)


class CompilationError(RuntimeError):
    """Raised when accepted decisions cannot be compiled safely."""


@dataclass(frozen=True, slots=True)
class ExecutionUnit:
    id: str
    decision_id: str
    proposal_id: str
    candidate_id: str
    candidate_ordinal: int
    phase: str
    source_path: str
    source_finding_key: str
    authorized_action: str
    authority: str
    state: str
    mutation_authorized: bool
    implementation_authorized: bool
    target_path: str | None
    expected_before_digest: str | None
    expected_after_digest: str | None
    dependency_paths: tuple[str, ...]
    dependent_paths: tuple[str, ...]
    preflight_requirements: tuple[str, ...]
    preservation_requirements: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    rollback_requirements: tuple[str, ...]
    completion_evidence: tuple[str, ...]
    blockers: tuple[str, ...]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(
        value.encode("utf-8")
    )


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


def atomic_write(
    path: Path,
    value: object,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.tmp"
    )

    temporary.write_bytes(
        canonical_json_bytes(value)
    )

    temporary.chmod(0o644)
    temporary.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CompilationError(
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
        raise CompilationError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise CompilationError(
            f"JSON root must be an object: {path}"
        )

    return value


def resolve_decisions_path() -> Path:
    latest = load_json(
        LATEST_ACCEPTED
    )

    raw_path = latest.get(
        "decisions"
    )

    if not isinstance(raw_path, str):
        raise CompilationError(
            "latest accepted-decision record lacks decisions path"
        )

    path = Path(raw_path)

    if not path.is_file():
        raise CompilationError(
            f"accepted decisions file missing: {path}"
        )

    return path


def normalize_phase(value: object) -> str:
    phase = str(value)

    if phase not in EXECUTION_PHASES:
        return "verification"

    return phase


def resolve_target_path(
    decision: dict[str, Any],
) -> str | None:
    raw_source_path = decision.get(
        "source_path"
    )

    if not isinstance(raw_source_path, str):
        return None

    if not raw_source_path.strip():
        return None

    path = Path(
        raw_source_path
    )

    if not path.is_absolute():
        path = ROOT / path

    try:
        path.relative_to(ROOT)
    except ValueError:
        return None

    return str(path)


def target_digest(
    target_path: str | None,
) -> str | None:
    if target_path is None:
        return None

    path = Path(
        target_path
    )

    if not path.is_file():
        return None

    return sha256_bytes(
        path.read_bytes()
    )


def execution_identity(
    decision_id: str,
    target_path: str | None,
    authorized_action: str,
) -> str:
    payload = "\x1f".join(
        (
            decision_id,
            target_path or "",
            authorized_action,
        )
    )

    return (
        "execution-unit:"
        + sha256_text(payload)[:24]
    )


def determine_blockers(
    *,
    decision: dict[str, Any],
    target_path: str | None,
    before_digest: str | None,
) -> tuple[str, ...]:
    blockers: list[str] = []

    if decision.get(
        "state"
    ) != "accepted":
        blockers.append(
            "decision state is not accepted"
        )

    if decision.get(
        "immutable"
    ) is not True:
        blockers.append(
            "decision is not immutable"
        )

    if decision.get(
        "mutation_authorized"
    ) is not True:
        blockers.append(
            "decision does not authorize mutation"
        )

    if target_path is None:
        blockers.append(
            "target path is unresolved"
        )
    elif before_digest is None:
        blockers.append(
            "target does not exist or current target digest is unavailable"
        )

    blockers.append(
        "current implementation has not been semantically reviewed"
    )

    blockers.append(
        "dependencies and dependents have not been resolved"
    )

    blockers.append(
        "complete replacement content has not been compiled"
    )

    blockers.append(
        "focused validation has not been bound to the target"
    )

    blockers.append(
        "integrated verification has not been bound to the target"
    )

    return tuple(
        dict.fromkeys(blockers)
    )


def compile_decision(
    decision: dict[str, Any],
) -> ExecutionUnit:
    decision_id = str(
        decision.get(
            "id",
            "",
        )
    )

    if not decision_id:
        raise CompilationError(
            "accepted decision lacks stable id"
        )

    candidate_ordinal = decision.get(
        "candidate_ordinal"
    )

    if not isinstance(
        candidate_ordinal,
        int,
    ):
        raise CompilationError(
            f"decision {decision_id} lacks integer candidate ordinal"
        )

    target_path = resolve_target_path(
        decision
    )

    before_digest = target_digest(
        target_path
    )

    blockers = determine_blockers(
        decision=decision,
        target_path=target_path,
        before_digest=before_digest,
    )

    authorized_action = str(
        decision.get(
            "authorized_action",
            "",
        )
    )

    return ExecutionUnit(
        id=execution_identity(
            decision_id,
            target_path,
            authorized_action,
        ),
        decision_id=decision_id,
        proposal_id=str(
            decision.get(
                "proposal_id",
                "",
            )
        ),
        candidate_id=str(
            decision.get(
                "candidate_id",
                "",
            )
        ),
        candidate_ordinal=(
            candidate_ordinal
        ),
        phase=normalize_phase(
            decision.get(
                "phase"
            )
        ),
        source_path=str(
            decision.get(
                "source_path",
                "",
            )
        ),
        source_finding_key=str(
            decision.get(
                "source_finding_key",
                "",
            )
        ),
        authorized_action=(
            authorized_action
        ),
        authority=str(
            decision.get(
                "authority",
                "",
            )
        ),
        state=(
            "blocked"
            if blockers
            else "ready"
        ),
        mutation_authorized=(
            decision.get(
                "mutation_authorized"
            )
            is True
        ),
        implementation_authorized=(
            False
        ),
        target_path=target_path,
        expected_before_digest=(
            before_digest
        ),
        expected_after_digest=None,
        dependency_paths=(),
        dependent_paths=(),
        preflight_requirements=(
            REQUIRED_PREFLIGHTS
        ),
        preservation_requirements=tuple(
            str(value)
            for value in decision.get(
                "preservation_requirements",
                [],
            )
        ),
        validation_requirements=tuple(
            str(value)
            for value in decision.get(
                "validation_requirements",
                [],
            )
        ),
        rollback_requirements=tuple(
            str(value)
            for value in decision.get(
                "rollback_requirements",
                [],
            )
        ),
        completion_evidence=(
            REQUIRED_EVIDENCE
        ),
        blockers=blockers,
    )


def compile_execution() -> dict[str, Any]:
    decisions_path = (
        resolve_decisions_path()
    )

    decisions_bytes = (
        decisions_path.read_bytes()
    )

    document = json.loads(
        decisions_bytes.decode("utf-8")
    )

    decisions = document.get(
        "decisions"
    )

    if not isinstance(
        decisions,
        list,
    ):
        raise CompilationError(
            "accepted decisions must be an array"
        )

    units = tuple(
        compile_decision(
            decision
        )
        for decision in decisions
        if isinstance(
            decision,
            dict,
        )
    )

    unit_ids = [
        unit.id
        for unit in units
    ]

    if len(unit_ids) != len(
        set(unit_ids)
    ):
        raise CompilationError(
            "execution unit identifiers are duplicated"
        )

    run_timestamp = utc_timestamp()

    packet_id = (
        "execution-packet:"
        + sha256_text(
            "\x1f".join(
                (
                    str(
                        decisions_path
                    ),
                    sha256_bytes(
                        decisions_bytes
                    ),
                    run_timestamp,
                )
            )
        )[:24]
    )

    state_counts = Counter(
        unit.state
        for unit in units
    )

    phase_counts = Counter(
        unit.phase
        for unit in units
    )

    run_root = (
        EXECUTION_ROOT
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
        EXECUTION_ROOT
        / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-execution-report/1.0.0"
        ),
        "operation": "compile_modular_execution",
        "id": packet_id,
        "timestamp": run_timestamp,
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "decisions": str(
            decisions_path
        ),
        "decisions_digest": sha256_bytes(
            decisions_bytes
        ),
        "unit_count": len(
            units
        ),
        "ready_count": state_counts[
            "ready"
        ],
        "blocked_count": state_counts[
            "blocked"
        ],
        "compiled_count": state_counts[
            "compiled"
        ],
        "phase_counts": {
            phase: phase_counts[
                phase
            ]
            for phase in EXECUTION_PHASES
        },
        "execution_states": list(
            EXECUTION_STATES
        ),
        "required_preflights": list(
            REQUIRED_PREFLIGHTS
        ),
        "required_completion_evidence": list(
            REQUIRED_EVIDENCE
        ),
    }

    units_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-execution-units/1.0.0"
        ),
        "packet_id": packet_id,
        "unit_count": len(
            units
        ),
        "units": [
            asdict(unit)
            for unit in units
        ],
    }

    atomic_write(
        report_path,
        report,
    )

    atomic_write(
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

    atomic_write(
        manifest_path,
        {
            "schema": (
                "savant://vault/dimensions/"
                "modular-execution-manifest/1.0.0"
            ),
            "packet_id": packet_id,
            "entries": manifest_entries,
        },
    )

    atomic_write(
        latest_path,
        {
            "packet_id": packet_id,
            "timestamp": run_timestamp,
            "report": str(
                report_path
            ),
            "units": str(
                units_path
            ),
            "manifest": str(
                manifest_path
            ),
            "unit_count": len(
                units
            ),
            "ready_count": state_counts[
                "ready"
            ],
            "blocked_count": state_counts[
                "blocked"
            ],
            "authority_effect": "none",
            "implementation_mutation_performed": False,
        },
    )

    return {
        "operation": (
            "compile_modular_execution"
        ),
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "packet_id": packet_id,
        "unit_count": len(
            units
        ),
        "ready_count": state_counts[
            "ready"
        ],
        "blocked_count": state_counts[
            "blocked"
        ],
        "paths": {
            "report": str(
                report_path
            ),
            "units": str(
                units_path
            ),
            "manifest": str(
                manifest_path
            ),
            "latest": str(
                latest_path
            ),
        },
    }


def verify_latest() -> dict[str, Any]:
    latest_path = (
        EXECUTION_ROOT
        / "latest.json"
    )

    latest = load_json(
        latest_path
    )

    raw_manifest = latest.get(
        "manifest"
    )

    if not isinstance(
        raw_manifest,
        str,
    ):
        raise CompilationError(
            "latest execution packet lacks manifest path"
        )

    manifest = load_json(
        Path(raw_manifest)
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise CompilationError(
            "execution manifest entries must be an array"
        )

    verified_entries = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise CompilationError(
                "execution manifest entry must be an object"
            )

        raw_path = entry.get(
            "path"
        )

        expected_digest = entry.get(
            "sha256"
        )

        if not isinstance(
            raw_path,
            str,
        ):
            raise CompilationError(
                "manifest entry lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise CompilationError(
                "manifest entry lacks digest"
            )

        path = Path(
            raw_path
        )

        if not path.is_file():
            raise CompilationError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise CompilationError(
                f"manifest digest mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(
                    path
                ),
                "sha256": actual_digest,
                "passed": True,
            }
        )

    raw_units = latest.get(
        "units"
    )

    if not isinstance(
        raw_units,
        str,
    ):
        raise CompilationError(
            "latest execution packet lacks units path"
        )

    units_document = load_json(
        Path(raw_units)
    )

    units = units_document.get(
        "units"
    )

    if not isinstance(
        units,
        list,
    ):
        raise CompilationError(
            "execution units must be an array"
        )

    unit_ids = []

    for unit in units:
        if not isinstance(
            unit,
            dict,
        ):
            raise CompilationError(
                "execution unit must be an object"
            )

        unit_id = unit.get(
            "id"
        )

        if not isinstance(
            unit_id,
            str,
        ):
            raise CompilationError(
                "execution unit lacks stable id"
            )

        unit_ids.append(
            unit_id
        )

        if unit.get(
            "implementation_authorized"
        ) is not False:
            raise CompilationError(
                f"execution unit prematurely authorizes implementation: {unit_id}"
            )

        state = unit.get(
            "state"
        )

        if state not in EXECUTION_STATES:
            raise CompilationError(
                f"execution unit has invalid state: {unit_id}"
            )

        preflights = unit.get(
            "preflight_requirements"
        )

        if tuple(
            preflights
            if isinstance(
                preflights,
                list,
            )
            else ()
        ) != REQUIRED_PREFLIGHTS:
            raise CompilationError(
                f"execution unit preflights differ from authority: {unit_id}"
            )

        evidence = unit.get(
            "completion_evidence"
        )

        if tuple(
            evidence
            if isinstance(
                evidence,
                list,
            )
            else ()
        ) != REQUIRED_EVIDENCE:
            raise CompilationError(
                f"execution unit evidence differs from authority: {unit_id}"
            )

    if len(unit_ids) != len(
        set(unit_ids)
    ):
        raise CompilationError(
            "execution unit identifiers are duplicated"
        )

    return {
        "operation": (
            "verify_modular_execution"
        ),
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "packet_id": latest.get(
            "packet_id"
        ),
        "unit_count": len(
            units
        ),
        "manifest_entry_count": len(
            verified_entries
        ),
        "verified_entries": (
            verified_entries
        ),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile or verify modular execution packets."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "compile",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "compile":
            result = compile_execution()
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

    except CompilationError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        arguments.operation
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
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
