#!/usr/bin/env python3
"""
Summarize and verify the complete Savant modular-migration pipeline.

This tool is read-only with respect to project authority and implementation.

It resolves the latest report from every completed pipeline stage, verifies
referenced files and manifests where available, identifies the first exact
blocker, and emits one deterministic status report.

It never:

- mutates implementation
- accepts new authority
- changes accepted decisions
- compiles replacement content
- authorizes implementation
- conceals missing stages
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

SYS_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
)

REPORT_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
)

SUMMARY_ROOT: Final[Path] = (
    REPORT_ROOT
    / "modular-pipeline-summary"
)

PIPELINE_STAGES: Final[tuple[tuple[str, str], ...]] = (
    (
        "audit",
        "modular-conformance",
    ),
    (
        "plan",
        "modular-migration",
    ),
    (
        "classification",
        "modular-classification",
    ),
    (
        "proposal",
        "modular-decisions",
    ),
    (
        "acceptance",
        "modular-accepted-decisions",
    ),
    (
        "execution",
        "modular-execution",
    ),
    (
        "binding",
        "modular-binding",
    ),
    (
        "review",
        "modular-review",
    ),
    (
        "replacement",
        "modular-replacement",
    ),
)

STAGE_STATES: Final[tuple[str, ...]] = (
    "missing",
    "invalid",
    "blocked",
    "partial",
    "ready",
    "passed",
    "complete",
    "unknown",
    "superseded",
)

REQUIRED_SUMMARY_AXES: Final[tuple[str, ...]] = (
    "authority",
    "identity",
    "moods",
    "slots",
    "dependencies",
    "lineage",
    "provenance",
    "recovery",
    "footprint",
)


class PipelineError(RuntimeError):
    """Raised when pipeline state cannot be summarized reliably."""


@dataclass(frozen=True, slots=True)
class StageStatus:
    ordinal: int
    key: str
    directory: str
    latest_path: str
    latest_exists: bool
    latest_valid: bool
    manifest_path: str | None
    manifest_exists: bool
    manifest_valid: bool
    report_path: str | None
    report_exists: bool
    passed: bool | None
    state: str
    item_count: int | None
    ready_count: int | None
    blocked_count: int | None
    failure_count: int | None
    authority_effect: str | None
    implementation_mutation_performed: bool | None
    blockers: tuple[str, ...]
    digest: str | None


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def atomic_write_json(
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
        raise PipelineError(
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
        raise PipelineError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise PipelineError(
            f"JSON root must be an object: {path}"
        )

    return value


def optional_json(
    path: Path,
) -> dict[str, Any] | None:
    try:
        return load_json(path)
    except PipelineError:
        return None


def optional_path(
    document: dict[str, Any],
    key: str,
) -> Path | None:
    value = document.get(key)

    if not isinstance(value, str):
        return None

    if not value.strip():
        return None

    return Path(value)


def integer_from_keys(
    documents: tuple[dict[str, Any], ...],
    keys: tuple[str, ...],
) -> int | None:
    for document in documents:
        for key in keys:
            value = document.get(key)

            if isinstance(value, int):
                return value

            summary = document.get("summary")

            if isinstance(summary, dict):
                nested = summary.get(key)

                if isinstance(nested, int):
                    return nested

    return None


def boolean_from_keys(
    documents: tuple[dict[str, Any], ...],
    keys: tuple[str, ...],
) -> bool | None:
    for document in documents:
        for key in keys:
            value = document.get(key)

            if isinstance(value, bool):
                return value

    return None


def string_from_keys(
    documents: tuple[dict[str, Any], ...],
    keys: tuple[str, ...],
) -> str | None:
    for document in documents:
        for key in keys:
            value = document.get(key)

            if isinstance(value, str):
                return value

    return None


def verify_manifest(
    manifest_path: Path | None,
) -> tuple[bool, tuple[str, ...]]:
    if manifest_path is None:
        return False, (
            "manifest path is absent",
        )

    if not manifest_path.is_file():
        return False, (
            f"manifest does not exist: {manifest_path}",
        )

    manifest = optional_json(
        manifest_path
    )

    if manifest is None:
        return False, (
            f"manifest is invalid JSON: {manifest_path}",
        )

    entries = manifest.get("entries")

    if not isinstance(entries, list):
        return False, (
            "manifest entries are not an array",
        )

    blockers: list[str] = []

    for ordinal, entry in enumerate(
        entries,
        start=1,
    ):
        if not isinstance(entry, dict):
            blockers.append(
                f"manifest entry {ordinal} is not an object"
            )
            continue

        raw_path = entry.get("path")
        expected_digest = entry.get("sha256")

        if not isinstance(raw_path, str):
            blockers.append(
                f"manifest entry {ordinal} lacks path"
            )
            continue

        if not isinstance(expected_digest, str):
            blockers.append(
                f"manifest entry {ordinal} lacks digest"
            )
            continue

        path = Path(raw_path)

        if not path.is_file():
            blockers.append(
                f"manifest file is missing: {path}"
            )
            continue

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            blockers.append(
                f"manifest digest mismatch: {path}"
            )

    return not blockers, tuple(blockers)


def derive_stage_state(
    *,
    latest_exists: bool,
    latest_valid: bool,
    manifest_valid: bool,
    passed: bool | None,
    ready_count: int | None,
    blocked_count: int | None,
    failure_count: int | None,
    replacement_stage: bool,
) -> str:
    if not latest_exists:
        return "missing"

    if not latest_valid:
        return "invalid"

    if failure_count is not None and failure_count > 0:
        return "blocked"

    if blocked_count is not None and blocked_count > 0:
        return "blocked"

    if passed is False:
        return "blocked"

    if not manifest_valid:
        return "partial"

    if replacement_stage and passed is True:
        return "complete"

    if ready_count is not None and ready_count > 0:
        return "ready"

    if passed is True:
        return "passed"

    return "unknown"


def inspect_stage(
    ordinal: int,
    key: str,
    directory_name: str,
) -> StageStatus:
    directory = REPORT_ROOT / directory_name
    latest_path = directory / "latest.json"

    latest_exists = latest_path.is_file()
    latest = optional_json(latest_path)

    if latest is None:
        blockers = (
            (
                f"latest report is missing: {latest_path}"
            )
            if not latest_exists
            else (
                f"latest report is invalid JSON: {latest_path}"
            )
        )

        return StageStatus(
            ordinal=ordinal,
            key=key,
            directory=str(directory),
            latest_path=str(latest_path),
            latest_exists=latest_exists,
            latest_valid=False,
            manifest_path=None,
            manifest_exists=False,
            manifest_valid=False,
            report_path=None,
            report_exists=False,
            passed=None,
            state=(
                "missing"
                if not latest_exists
                else "invalid"
            ),
            item_count=None,
            ready_count=None,
            blocked_count=None,
            failure_count=None,
            authority_effect=None,
            implementation_mutation_performed=None,
            blockers=blockers,
            digest=None,
        )

    manifest_path = optional_path(
        latest,
        "manifest",
    )

    report_path = optional_path(
        latest,
        "report",
    )

    report = (
        optional_json(report_path)
        if report_path is not None
        else None
    )

    documents = tuple(
        document
        for document in (
            latest,
            report,
        )
        if isinstance(document, dict)
    )

    manifest_valid, manifest_blockers = (
        verify_manifest(
            manifest_path
        )
    )

    passed = boolean_from_keys(
        documents,
        (
            "passed",
            "audit_passed",
        ),
    )

    item_count = integer_from_keys(
        documents,
        (
            "item_count",
            "finding_count",
            "candidate_count",
            "classification_count",
            "proposal_count",
            "accepted_decision_count",
            "unit_count",
            "bound_unit_count",
            "review_count",
            "replacement_count",
        ),
    )

    ready_count = integer_from_keys(
        documents,
        (
            "ready_count",
            "actionable_count",
            "semantic_complete_count",
        ),
    )

    blocked_count = integer_from_keys(
        documents,
        (
            "blocked_count",
            "blocked_proposal_count",
        ),
    )

    failure_count = integer_from_keys(
        documents,
        (
            "failure_count",
            "error_count",
        ),
    )

    authority_effect = string_from_keys(
        documents,
        (
            "authority_effect",
        ),
    )

    implementation_mutation_performed = (
        boolean_from_keys(
            documents,
            (
                "implementation_mutation_performed",
                "mutation_performed",
            ),
        )
    )

    blockers: list[str] = list(
        manifest_blockers
    )

    if report_path is None:
        blockers.append(
            "report path is absent"
        )
    elif not report_path.is_file():
        blockers.append(
            f"report does not exist: {report_path}"
        )
    elif report is None:
        blockers.append(
            f"report is invalid JSON: {report_path}"
        )

    if failure_count is not None and failure_count > 0:
        blockers.append(
            f"failure count is {failure_count}"
        )

    if blocked_count is not None and blocked_count > 0:
        blockers.append(
            f"blocked count is {blocked_count}"
        )

    if passed is False:
        blockers.append(
            "stage reports passed=false"
        )

    state = derive_stage_state(
        latest_exists=True,
        latest_valid=True,
        manifest_valid=manifest_valid,
        passed=passed,
        ready_count=ready_count,
        blocked_count=blocked_count,
        failure_count=failure_count,
        replacement_stage=(
            key == "replacement"
        ),
    )

    return StageStatus(
        ordinal=ordinal,
        key=key,
        directory=str(directory),
        latest_path=str(latest_path),
        latest_exists=True,
        latest_valid=True,
        manifest_path=(
            str(manifest_path)
            if manifest_path is not None
            else None
        ),
        manifest_exists=bool(
            manifest_path is not None
            and manifest_path.is_file()
        ),
        manifest_valid=manifest_valid,
        report_path=(
            str(report_path)
            if report_path is not None
            else None
        ),
        report_exists=bool(
            report_path is not None
            and report_path.is_file()
        ),
        passed=passed,
        state=state,
        item_count=item_count,
        ready_count=ready_count,
        blocked_count=blocked_count,
        failure_count=failure_count,
        authority_effect=authority_effect,
        implementation_mutation_performed=(
            implementation_mutation_performed
        ),
        blockers=tuple(
            dict.fromkeys(blockers)
        ),
        digest=sha256_bytes(
            latest_path.read_bytes()
        ),
    )


def determine_pipeline_blockers(
    stages: tuple[StageStatus, ...],
) -> tuple[str, ...]:
    blockers: list[str] = []

    for stage in stages:
        if stage.state in {
            "missing",
            "invalid",
            "blocked",
            "partial",
            "unknown",
        }:
            blockers.append(
                f"{stage.key}: {stage.state}"
            )

            blockers.extend(
                f"{stage.key}: {blocker}"
                for blocker in stage.blockers
            )

    return tuple(
        dict.fromkeys(blockers)
    )


def determine_first_blocker(
    stages: tuple[StageStatus, ...],
) -> str | None:
    for stage in stages:
        if stage.state in {
            "missing",
            "invalid",
            "blocked",
            "partial",
            "unknown",
        }:
            if stage.blockers:
                return (
                    f"{stage.key}: "
                    f"{stage.blockers[0]}"
                )

            return (
                f"{stage.key}: "
                f"stage state is {stage.state}"
            )

    return None


def summarize_pipeline() -> dict[str, Any]:
    run_timestamp = utc_timestamp()

    stages = tuple(
        inspect_stage(
            ordinal,
            key,
            directory_name,
        )
        for ordinal, (
            key,
            directory_name,
        ) in enumerate(
            PIPELINE_STAGES,
            start=1,
        )
    )

    stage_counts = Counter(
        stage.state
        for stage in stages
    )

    blockers = determine_pipeline_blockers(
        stages
    )

    first_blocker = determine_first_blocker(
        stages
    )

    replacement_stage = stages[-1]

    complete = (
        not blockers
        and replacement_stage.state
        == "complete"
    )

    implementation_mutation_count = sum(
        stage.implementation_mutation_performed
        is True
        for stage in stages
    )

    packet_id = (
        "pipeline-summary:"
        + sha256_bytes(
            "\x1f".join(
                (
                    run_timestamp,
                    *(
                        stage.digest or ""
                        for stage in stages
                    ),
                )
            ).encode("utf-8")
        )[:24]
    )

    run_root = (
        SUMMARY_ROOT
        / run_timestamp
    )

    report_path = (
        run_root
        / "report.json"
    )

    stages_path = (
        run_root
        / "stages.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        SUMMARY_ROOT
        / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-pipeline-summary/1.0.0"
        ),
        "operation": (
            "summarize_modular_pipeline"
        ),
        "id": packet_id,
        "timestamp": run_timestamp,
        "passed": complete,
        "pipeline_complete": complete,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "observed_implementation_mutation_stage_count": (
            implementation_mutation_count
        ),
        "stage_count": len(stages),
        "stage_state_counts": {
            state: stage_counts[state]
            for state in STAGE_STATES
        },
        "first_blocker": first_blocker,
        "blocker_count": len(blockers),
        "summary_axes": list(
            REQUIRED_SUMMARY_AXES
        ),
    }

    stages_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-pipeline-stages/1.0.0"
        ),
        "packet_id": packet_id,
        "stage_count": len(stages),
        "stages": [
            asdict(stage)
            for stage in stages
        ],
        "blockers": list(blockers),
    }

    atomic_write_json(
        report_path,
        report,
    )

    atomic_write_json(
        stages_path,
        stages_document,
    )

    manifest_entries = []

    for path in (
        report_path,
        stages_path,
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
                "modular-pipeline-summary-manifest/1.0.0"
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
            "stages": str(stages_path),
            "manifest": str(manifest_path),
            "stage_count": len(stages),
            "pipeline_complete": complete,
            "first_blocker": first_blocker,
            "blocker_count": len(blockers),
            "authority_effect": "none",
            "implementation_mutation_performed": False,
        },
    )

    return {
        "operation": (
            "summarize_modular_pipeline"
        ),
        "passed": complete,
        "pipeline_complete": complete,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "packet_id": packet_id,
        "stage_count": len(stages),
        "first_blocker": first_blocker,
        "blocker_count": len(blockers),
        "latest": str(latest_path),
    }


def verify_latest() -> dict[str, Any]:
    latest_path = (
        SUMMARY_ROOT
        / "latest.json"
    )

    latest = load_json(
        latest_path
    )

    manifest_path = optional_path(
        latest,
        "manifest",
    )

    manifest_valid, blockers = (
        verify_manifest(
            manifest_path
        )
    )

    if not manifest_valid:
        raise PipelineError(
            "; ".join(blockers)
        )

    stages_path = optional_path(
        latest,
        "stages",
    )

    if stages_path is None:
        raise PipelineError(
            "latest summary lacks stages path"
        )

    stages_document = load_json(
        stages_path
    )

    stages = stages_document.get(
        "stages"
    )

    if not isinstance(stages, list):
        raise PipelineError(
            "pipeline stages must be an array"
        )

    if len(stages) != 9:
        raise PipelineError(
            f"expected 9 pipeline stages; "
            f"found {len(stages)}"
        )

    ordinals = [
        stage.get("ordinal")
        for stage in stages
        if isinstance(stage, dict)
    ]

    if ordinals != list(range(1, 10)):
        raise PipelineError(
            "pipeline stage ordinals are invalid"
        )

    keys = [
        stage.get("key")
        for stage in stages
        if isinstance(stage, dict)
    ]

    expected_keys = [
        key
        for key, _ in PIPELINE_STAGES
    ]

    if keys != expected_keys:
        raise PipelineError(
            "pipeline stage order differs from authority"
        )

    for stage in stages:
        if not isinstance(stage, dict):
            raise PipelineError(
                "pipeline stage must be an object"
            )

        state = stage.get("state")

        if state not in STAGE_STATES:
            raise PipelineError(
                f"invalid pipeline stage state: {state}"
            )

    return {
        "operation": (
            "verify_modular_pipeline_summary"
        ),
        "passed": True,
        "packet_id": latest.get(
            "packet_id"
        ),
        "stage_count": len(stages),
        "pipeline_complete": latest.get(
            "pipeline_complete"
        ),
        "first_blocker": latest.get(
            "first_blocker"
        ),
        "blocker_count": latest.get(
            "blocker_count"
        ),
        "authority_effect": "none",
        "implementation_mutation_performed": False,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize or verify the Savant "
            "modular-migration pipeline."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "summarize",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "summarize":
            result = summarize_pipeline()
        else:
            result = verify_latest()

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        if arguments.operation == "verify":
            return 0

        return (
            0
            if result["pipeline_complete"]
            else 2
        )

    except PipelineError as error:
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "passed": False,
                    "pipeline_complete": False,
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
