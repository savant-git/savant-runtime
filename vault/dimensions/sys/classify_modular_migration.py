#!/usr/bin/env python3
"""
Classify modular-migration candidates without mutating Savant.

This stage converts raw migration candidates into governed dispositions:

- preserve
- investigate
- approve
- block
- reject
- supersede
- instance
- project
- verify

Classification remains evidence, not authority. Mutating dispositions require
a separately accepted decision before execution.
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

PLAN_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-migration"
)

CLASSIFICATION_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-classification"
)

LATEST_PLAN: Final[Path] = (
    PLAN_ROOT
    / "latest.json"
)

DISPOSITIONS: Final[tuple[str, ...]] = (
    "preserve",
    "investigate",
    "approve",
    "block",
    "reject",
    "supersede",
    "instance",
    "project",
    "verify",
)

EVIDENCE_STATES: Final[tuple[str, ...]] = (
    "absent",
    "weak",
    "partial",
    "adequate",
    "strong",
    "corroborated",
    "authoritative",
    "conflicted",
    "unknown",
)

REVIEW_AXES: Final[tuple[str, ...]] = (
    "authority",
    "necessity",
    "duplication",
    "compatibility",
    "lineage",
    "provenance",
    "reversibility",
    "dependencies",
    "footprint",
)


class ClassificationError(RuntimeError):
    """Raised when classification cannot complete reliably."""


@dataclass(frozen=True, slots=True)
class Classification:
    id: str
    candidate_id: str
    candidate_ordinal: int
    phase: str
    source_path: str
    source_finding_key: str
    proposed_action: str
    disposition: str
    evidence_state: str
    mutation_authorized: bool
    authority_required: str
    rationale: str
    review_axes: tuple[str, ...]
    preservation_requirements: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    blockers: tuple[str, ...]
    status: str


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
        raise ClassificationError(
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
        raise ClassificationError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise ClassificationError(
            f"JSON root must be an object: {path}"
        )

    return value


def resolve_plan_path() -> Path:
    latest = load_json(
        LATEST_PLAN
    )

    raw_plan = latest.get(
        "plan"
    )

    if not isinstance(raw_plan, str):
        raise ClassificationError(
            "latest migration plan lacks plan path"
        )

    plan_path = Path(
        raw_plan
    )

    if not plan_path.is_file():
        raise ClassificationError(
            f"migration plan missing: {plan_path}"
        )

    return plan_path


def candidate_disposition(
    candidate: dict[str, Any],
) -> str:
    action = str(
        candidate.get(
            "action_class",
            "",
        )
    ).casefold()

    status = str(
        candidate.get(
            "status",
            "",
        )
    ).casefold()

    severity = str(
        candidate.get(
            "severity",
            "",
        )
    ).casefold()

    source_key = str(
        candidate.get(
            "source_finding_key",
            "",
        )
    ).casefold()

    if status == "blocked":
        return "block"

    if action == "preserve":
        return "preserve"

    if action == "classify":
        return "investigate"

    if action == "refuse":
        return "block"

    if action == "supersede":
        return "supersede"

    if action == "instance":
        return "instance"

    if action == "project":
        return "project"

    if action == "verify":
        return "verify"

    if action in {
        "extend",
        "migrate",
    }:
        if severity == "error":
            return "investigate"

        return "approve"

    if "missing_required_authority" in source_key:
        return "block"

    return "investigate"


def candidate_evidence_state(
    candidate: dict[str, Any],
) -> str:
    status = str(
        candidate.get(
            "status",
            "",
        )
    ).casefold()

    severity = str(
        candidate.get(
            "severity",
            "",
        )
    ).casefold()

    rationale = str(
        candidate.get(
            "rationale",
            "",
        )
    ).strip()

    source_path = str(
        candidate.get(
            "source_path",
            "",
        )
    ).strip()

    if status == "blocked":
        return "conflicted"

    if not rationale:
        return "absent"

    if not source_path:
        return "weak"

    if severity == "error":
        return "strong"

    if severity == "warning":
        return "adequate"

    return "partial"


def classification_blockers(
    candidate: dict[str, Any],
    disposition: str,
    evidence_state: str,
) -> tuple[str, ...]:
    blockers: list[str] = []

    mutation_allowed = bool(
        candidate.get(
            "mutation_allowed",
            False,
        )
    )

    if disposition in {
        "approve",
        "supersede",
        "instance",
        "project",
    }:
        if not mutation_allowed:
            blockers.append(
                "candidate does not permit mutation"
            )

        blockers.append(
            "accepted mutation decision is not attached"
        )

    if evidence_state in {
        "absent",
        "weak",
        "conflicted",
        "unknown",
    }:
        blockers.append(
            f"evidence state is {evidence_state}"
        )

    if disposition == "investigate":
        blockers.append(
            "semantic classification remains unresolved"
        )

    if disposition == "block":
        blockers.append(
            "candidate is blocked by governing plan"
        )

    return tuple(
        dict.fromkeys(blockers)
    )


def classification_identity(
    candidate_id: str,
    disposition: str,
    evidence_state: str,
) -> str:
    payload = "\x1f".join(
        (
            candidate_id,
            disposition,
            evidence_state,
        )
    )

    return (
        "classification:"
        + sha256_text(payload)[:24]
    )


def classify_candidate(
    candidate: dict[str, Any],
) -> Classification:
    candidate_id = str(
        candidate.get(
            "id",
            "",
        )
    )

    if not candidate_id:
        raise ClassificationError(
            "migration candidate lacks stable id"
        )

    candidate_ordinal = candidate.get(
        "ordinal"
    )

    if not isinstance(
        candidate_ordinal,
        int,
    ):
        raise ClassificationError(
            f"candidate {candidate_id} lacks integer ordinal"
        )

    disposition = candidate_disposition(
        candidate
    )

    evidence_state = candidate_evidence_state(
        candidate
    )

    blockers = classification_blockers(
        candidate,
        disposition,
        evidence_state,
    )

    mutation_authorized = (
        bool(
            candidate.get(
                "mutation_allowed",
                False,
            )
        )
        and disposition
        in {
            "approve",
            "supersede",
            "instance",
            "project",
        }
        and not blockers
    )

    return Classification(
        id=classification_identity(
            candidate_id,
            disposition,
            evidence_state,
        ),
        candidate_id=candidate_id,
        candidate_ordinal=(
            candidate_ordinal
        ),
        phase=str(
            candidate.get(
                "phase",
                "verification",
            )
        ),
        source_path=str(
            candidate.get(
                "source_path",
                "",
            )
        ),
        source_finding_key=str(
            candidate.get(
                "source_finding_key",
                "",
            )
        ),
        proposed_action=str(
            candidate.get(
                "action_class",
                "",
            )
        ),
        disposition=disposition,
        evidence_state=evidence_state,
        mutation_authorized=(
            mutation_authorized
        ),
        authority_required=str(
            candidate.get(
                "authority_required",
                "decision",
            )
        ),
        rationale=str(
            candidate.get(
                "rationale",
                "",
            )
        ),
        review_axes=REVIEW_AXES,
        preservation_requirements=tuple(
            str(value)
            for value in candidate.get(
                "preservation_requirements",
                [],
            )
        ),
        validation_requirements=tuple(
            str(value)
            for value in candidate.get(
                "validation_requirements",
                [],
            )
        ),
        blockers=blockers,
        status=(
            "actionable"
            if mutation_authorized
            else "review_required"
        ),
    )


def classify_plan() -> dict[str, Any]:
    plan_path = resolve_plan_path()
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(
        plan_bytes.decode("utf-8")
    )

    candidates = plan.get(
        "candidates"
    )

    if not isinstance(
        candidates,
        list,
    ):
        raise ClassificationError(
            "migration plan candidates must be an array"
        )

    classifications = tuple(
        classify_candidate(candidate)
        for candidate in candidates
        if isinstance(candidate, dict)
    )

    expected_ordinals = list(
        range(
            1,
            len(classifications) + 1,
        )
    )

    actual_ordinals = [
        classification.candidate_ordinal
        for classification in classifications
    ]

    if actual_ordinals != expected_ordinals:
        raise ClassificationError(
            "candidate ordinals are not contiguous"
        )

    run_timestamp = utc_timestamp()

    classification_set_id = (
        "classification-set:"
        + sha256_text(
            "\x1f".join(
                (
                    str(plan_path),
                    sha256_bytes(plan_bytes),
                    run_timestamp,
                )
            )
        )[:24]
    )

    disposition_counts = Counter(
        classification.disposition
        for classification in classifications
    )

    evidence_counts = Counter(
        classification.evidence_state
        for classification in classifications
    )

    actionable_count = sum(
        classification.mutation_authorized
        for classification in classifications
    )

    blocked_count = sum(
        bool(classification.blockers)
        for classification in classifications
    )

    run_root = (
        CLASSIFICATION_ROOT
        / run_timestamp
    )

    report_path = (
        run_root
        / "report.json"
    )

    classifications_path = (
        run_root
        / "classifications.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        CLASSIFICATION_ROOT
        / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-classification-report/1.0.0"
        ),
        "operation": "classify_modular_migration",
        "id": classification_set_id,
        "timestamp": run_timestamp,
        "passed": True,
        "mutation_performed": False,
        "authority_effect": "none",
        "plan": str(plan_path),
        "plan_digest": sha256_bytes(
            plan_bytes
        ),
        "classification_count": len(
            classifications
        ),
        "actionable_count": actionable_count,
        "blocked_count": blocked_count,
        "disposition_counts": {
            disposition: disposition_counts[
                disposition
            ]
            for disposition in DISPOSITIONS
        },
        "evidence_counts": {
            evidence_state: evidence_counts[
                evidence_state
            ]
            for evidence_state in EVIDENCE_STATES
        },
        "review_axes": list(
            REVIEW_AXES
        ),
    }

    classification_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-classifications/1.0.0"
        ),
        "classification_set_id": (
            classification_set_id
        ),
        "classifications": [
            asdict(classification)
            for classification in classifications
        ],
    }

    atomic_write(
        report_path,
        report,
    )

    atomic_write(
        classifications_path,
        classification_document,
    )

    manifest_entries = []

    for path in (
        report_path,
        classifications_path,
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
                "modular-classification-manifest/1.0.0"
            ),
            "classification_set_id": (
                classification_set_id
            ),
            "entries": manifest_entries,
        },
    )

    atomic_write(
        latest_path,
        {
            "classification_set_id": (
                classification_set_id
            ),
            "timestamp": run_timestamp,
            "report": str(report_path),
            "classifications": str(
                classifications_path
            ),
            "manifest": str(
                manifest_path
            ),
            "classification_count": len(
                classifications
            ),
            "actionable_count": (
                actionable_count
            ),
            "blocked_count": blocked_count,
            "mutation_performed": False,
            "authority_effect": "none",
        },
    )

    return {
        "operation": "classify_modular_migration",
        "passed": True,
        "mutation_performed": False,
        "authority_effect": "none",
        "classification_set_id": (
            classification_set_id
        ),
        "classification_count": len(
            classifications
        ),
        "actionable_count": actionable_count,
        "blocked_count": blocked_count,
        "paths": {
            "report": str(report_path),
            "classifications": str(
                classifications_path
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
        CLASSIFICATION_ROOT
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
        raise ClassificationError(
            "latest classification lacks manifest path"
        )

    manifest_path = Path(
        raw_manifest
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
        raise ClassificationError(
            "classification manifest entries must be an array"
        )

    verified_entries = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise ClassificationError(
                "classification manifest entry must be an object"
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
            raise ClassificationError(
                "manifest entry lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise ClassificationError(
                "manifest entry lacks digest"
            )

        path = Path(
            raw_path
        )

        if not path.is_file():
            raise ClassificationError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise ClassificationError(
                f"manifest digest mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(path),
                "sha256": actual_digest,
                "passed": True,
            }
        )

    raw_classifications = latest.get(
        "classifications"
    )

    if not isinstance(
        raw_classifications,
        str,
    ):
        raise ClassificationError(
            "latest classification lacks classifications path"
        )

    classification_document = load_json(
        Path(raw_classifications)
    )

    classifications = (
        classification_document.get(
            "classifications"
        )
    )

    if not isinstance(
        classifications,
        list,
    ):
        raise ClassificationError(
            "classifications must be an array"
        )

    candidate_ids = [
        classification.get(
            "candidate_id"
        )
        for classification in classifications
        if isinstance(
            classification,
            dict,
        )
    ]

    if len(candidate_ids) != len(
        set(candidate_ids)
    ):
        raise ClassificationError(
            "candidate classifications are duplicated"
        )

    return {
        "operation": (
            "verify_modular_classification"
        ),
        "passed": True,
        "mutation_performed": False,
        "authority_effect": "none",
        "classification_set_id": (
            latest.get(
                "classification_set_id"
            )
        ),
        "classification_count": len(
            classifications
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
            "Classify or verify modular migration candidates."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "classify",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "classify":
            result = classify_plan()
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

    except ClassificationError as error:
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "passed": False,
                    "mutation_performed": False,
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
