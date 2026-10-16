#!/usr/bin/env python3
"""
Prepare immutable decision proposals from the latest modular classification.

This tool does not accept decisions, mutate authority, or modify implementation
files. It produces deterministic proposal packets for review.

Only classifications whose disposition requires mutation are proposed.
Blocked, investigative, preservation-only, and verification-only records remain
preserved as evidence but do not become mutation proposals.
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

CLASSIFICATION_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-classification"
)

DECISION_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-decisions"
)

LATEST_CLASSIFICATION: Final[Path] = (
    CLASSIFICATION_ROOT
    / "latest.json"
)

PROPOSABLE_DISPOSITIONS: Final[tuple[str, ...]] = (
    "approve",
    "supersede",
    "instance",
    "project",
)

NONPROPOSABLE_DISPOSITIONS: Final[tuple[str, ...]] = (
    "preserve",
    "investigate",
    "block",
    "reject",
    "verify",
)

DECISION_STATES: Final[tuple[str, ...]] = (
    "proposed",
    "accepted",
    "rejected",
)

REVIEW_GATES: Final[tuple[str, ...]] = (
    "authority",
    "necessity",
    "compatibility",
    "dependencies",
    "lineage",
    "provenance",
    "reversibility",
    "validation",
    "footprint",
)


class DecisionPreparationError(RuntimeError):
    """Raised when immutable decision proposals cannot be prepared safely."""


@dataclass(frozen=True, slots=True)
class DecisionProposal:
    id: str
    classification_id: str
    candidate_id: str
    candidate_ordinal: int
    phase: str
    source_path: str
    source_finding_key: str
    disposition: str
    proposed_action: str
    authority_required: str
    state: str
    mutation_authorized: bool
    rationale: str
    review_gates: tuple[str, ...]
    preservation_requirements: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    blockers: tuple[str, ...]
    acceptance_conditions: tuple[str, ...]
    rejection_conditions: tuple[str, ...]
    rollback_requirements: tuple[str, ...]


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
        raise DecisionPreparationError(
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
        raise DecisionPreparationError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise DecisionPreparationError(
            f"JSON root must be an object: {path}"
        )

    return value


def resolve_classifications_path() -> Path:
    latest = load_json(
        LATEST_CLASSIFICATION
    )

    raw_path = latest.get(
        "classifications"
    )

    if not isinstance(raw_path, str):
        raise DecisionPreparationError(
            "latest classification lacks classifications path"
        )

    path = Path(raw_path)

    if not path.is_file():
        raise DecisionPreparationError(
            f"classifications file missing: {path}"
        )

    return path


def proposal_identity(
    classification_id: str,
    disposition: str,
    proposed_action: str,
) -> str:
    payload = "\x1f".join(
        (
            classification_id,
            disposition,
            proposed_action,
        )
    )

    return (
        "decision-proposal:"
        + sha256_text(payload)[:24]
    )


def acceptance_conditions(
    classification: dict[str, Any],
) -> tuple[str, ...]:
    return (
        "required authority explicitly accepts the proposal",
        "source implementation is re-read before mutation",
        "affected dependencies and dependents are identified",
        "preservation requirements are satisfied",
        "validation requirements are executable",
        "rollback is complete and independently verifiable",
        "the change reduces or justifies authoritative footprint",
        "no unresolved authority conflict remains",
        "lexicon and cardinality rules are satisfied",
    )


def rejection_conditions(
    classification: dict[str, Any],
) -> tuple[str, ...]:
    return (
        "equivalent reusable authority already exists",
        "the proposal duplicates authoritative substance",
        "working behavior cannot be preserved",
        "lineage or provenance would be lost",
        "rollback cannot be proven",
        "dependency impact remains unknown",
        "compatibility damage lacks authority",
        "the proposal increases footprint without proportional capability",
        "required evidence is absent or conflicted",
    )


def rollback_requirements(
    classification: dict[str, Any],
) -> tuple[str, ...]:
    return (
        "record complete prechange file digests",
        "preserve complete previous files",
        "record dependency and dependent manifests",
        "record authority and decision references",
        "provide deterministic reversal commands",
        "replay focused validation after reversal",
        "verify restored lineage and provenance",
        "verify restored integrated behavior",
        "retain immutable rollback receipts",
    )


def classification_is_proposable(
    classification: dict[str, Any],
) -> bool:
    disposition = str(
        classification.get(
            "disposition",
            "",
        )
    ).casefold()

    return disposition in PROPOSABLE_DISPOSITIONS


def prepare_proposal(
    classification: dict[str, Any],
) -> DecisionProposal:
    classification_id = str(
        classification.get(
            "id",
            "",
        )
    )

    if not classification_id:
        raise DecisionPreparationError(
            "classification lacks stable id"
        )

    candidate_id = str(
        classification.get(
            "candidate_id",
            "",
        )
    )

    if not candidate_id:
        raise DecisionPreparationError(
            f"classification {classification_id} lacks candidate id"
        )

    ordinal = classification.get(
        "candidate_ordinal"
    )

    if not isinstance(ordinal, int):
        raise DecisionPreparationError(
            f"classification {classification_id} lacks integer ordinal"
        )

    disposition = str(
        classification.get(
            "disposition",
            "",
        )
    ).casefold()

    proposed_action = str(
        classification.get(
            "proposed_action",
            "",
        )
    ).casefold()

    original_blockers = tuple(
        str(value)
        for value in classification.get(
            "blockers",
            [],
        )
    )

    decision_blockers = tuple(
        blocker
        for blocker in original_blockers
        if blocker
        != "accepted mutation decision is not attached"
    )

    return DecisionProposal(
        id=proposal_identity(
            classification_id,
            disposition,
            proposed_action,
        ),
        classification_id=classification_id,
        candidate_id=candidate_id,
        candidate_ordinal=ordinal,
        phase=str(
            classification.get(
                "phase",
                "verification",
            )
        ),
        source_path=str(
            classification.get(
                "source_path",
                "",
            )
        ),
        source_finding_key=str(
            classification.get(
                "source_finding_key",
                "",
            )
        ),
        disposition=disposition,
        proposed_action=proposed_action,
        authority_required=str(
            classification.get(
                "authority_required",
                "decision",
            )
        ),
        state="proposed",
        mutation_authorized=False,
        rationale=str(
            classification.get(
                "rationale",
                "",
            )
        ),
        review_gates=REVIEW_GATES,
        preservation_requirements=tuple(
            str(value)
            for value in classification.get(
                "preservation_requirements",
                [],
            )
        ),
        validation_requirements=tuple(
            str(value)
            for value in classification.get(
                "validation_requirements",
                [],
            )
        ),
        blockers=decision_blockers,
        acceptance_conditions=(
            acceptance_conditions(
                classification
            )
        ),
        rejection_conditions=(
            rejection_conditions(
                classification
            )
        ),
        rollback_requirements=(
            rollback_requirements(
                classification
            )
        ),
    )


def prepare_decisions() -> dict[str, Any]:
    classifications_path = (
        resolve_classifications_path()
    )

    classifications_bytes = (
        classifications_path.read_bytes()
    )

    document = json.loads(
        classifications_bytes.decode("utf-8")
    )

    classifications = document.get(
        "classifications"
    )

    if not isinstance(
        classifications,
        list,
    ):
        raise DecisionPreparationError(
            "classifications must be an array"
        )

    proposal_source = [
        classification
        for classification in classifications
        if isinstance(
            classification,
            dict,
        )
        and classification_is_proposable(
            classification
        )
    ]

    proposals = tuple(
        prepare_proposal(
            classification
        )
        for classification in proposal_source
    )

    proposal_ids = [
        proposal.id
        for proposal in proposals
    ]

    if len(proposal_ids) != len(
        set(proposal_ids)
    ):
        raise DecisionPreparationError(
            "decision proposal identifiers are duplicated"
        )

    run_timestamp = utc_timestamp()

    packet_id = (
        "decision-packet:"
        + sha256_text(
            "\x1f".join(
                (
                    str(
                        classifications_path
                    ),
                    sha256_bytes(
                        classifications_bytes
                    ),
                    run_timestamp,
                )
            )
        )[:24]
    )

    disposition_counts = Counter(
        proposal.disposition
        for proposal in proposals
    )

    blocked_count = sum(
        bool(proposal.blockers)
        for proposal in proposals
    )

    run_root = (
        DECISION_ROOT
        / run_timestamp
    )

    report_path = (
        run_root
        / "report.json"
    )

    proposals_path = (
        run_root
        / "proposals.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        DECISION_ROOT
        / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-decision-report/1.0.0"
        ),
        "operation": "prepare_modular_decisions",
        "id": packet_id,
        "timestamp": run_timestamp,
        "passed": True,
        "mutation_performed": False,
        "authority_effect": "none",
        "classifications": str(
            classifications_path
        ),
        "classifications_digest": (
            sha256_bytes(
                classifications_bytes
            )
        ),
        "proposal_count": len(
            proposals
        ),
        "blocked_proposal_count": (
            blocked_count
        ),
        "disposition_counts": {
            disposition: (
                disposition_counts[
                    disposition
                ]
            )
            for disposition in (
                PROPOSABLE_DISPOSITIONS
            )
        },
        "review_gates": list(
            REVIEW_GATES
        ),
        "decision_states": list(
            DECISION_STATES
        ),
    }

    proposals_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-decision-proposals/1.0.0"
        ),
        "packet_id": packet_id,
        "proposal_count": len(
            proposals
        ),
        "proposals": [
            asdict(proposal)
            for proposal in proposals
        ],
    }

    atomic_write(
        report_path,
        report,
    )

    atomic_write(
        proposals_path,
        proposals_document,
    )

    manifest_entries = []

    for path in (
        report_path,
        proposals_path,
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
                "modular-decision-manifest/1.0.0"
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
            "report": str(report_path),
            "proposals": str(
                proposals_path
            ),
            "manifest": str(
                manifest_path
            ),
            "proposal_count": len(
                proposals
            ),
            "blocked_proposal_count": (
                blocked_count
            ),
            "mutation_performed": False,
            "authority_effect": "none",
        },
    )

    return {
        "operation": (
            "prepare_modular_decisions"
        ),
        "passed": True,
        "mutation_performed": False,
        "authority_effect": "none",
        "packet_id": packet_id,
        "proposal_count": len(
            proposals
        ),
        "blocked_proposal_count": (
            blocked_count
        ),
        "paths": {
            "report": str(report_path),
            "proposals": str(
                proposals_path
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
        DECISION_ROOT
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
        raise DecisionPreparationError(
            "latest decision packet lacks manifest path"
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
        raise DecisionPreparationError(
            "decision manifest entries must be an array"
        )

    verified_entries = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise DecisionPreparationError(
                "decision manifest entry must be an object"
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
            raise DecisionPreparationError(
                "manifest entry lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise DecisionPreparationError(
                "manifest entry lacks digest"
            )

        path = Path(raw_path)

        if not path.is_file():
            raise DecisionPreparationError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise DecisionPreparationError(
                f"manifest digest mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(path),
                "sha256": actual_digest,
                "passed": True,
            }
        )

    raw_proposals = latest.get(
        "proposals"
    )

    if not isinstance(
        raw_proposals,
        str,
    ):
        raise DecisionPreparationError(
            "latest packet lacks proposals path"
        )

    proposals_document = load_json(
        Path(raw_proposals)
    )

    proposals = proposals_document.get(
        "proposals"
    )

    if not isinstance(
        proposals,
        list,
    ):
        raise DecisionPreparationError(
            "proposals must be an array"
        )

    proposal_ids = [
        proposal.get(
            "id"
        )
        for proposal in proposals
        if isinstance(
            proposal,
            dict,
        )
    ]

    if len(proposal_ids) != len(
        set(proposal_ids)
    ):
        raise DecisionPreparationError(
            "proposal identifiers are duplicated"
        )

    for proposal in proposals:
        if not isinstance(
            proposal,
            dict,
        ):
            raise DecisionPreparationError(
                "proposal must be an object"
            )

        if proposal.get(
            "state"
        ) != "proposed":
            raise DecisionPreparationError(
                "prepared proposals must remain proposed"
            )

        if proposal.get(
            "mutation_authorized"
        ) is not False:
            raise DecisionPreparationError(
                "prepared proposals cannot authorize mutation"
            )

    return {
        "operation": (
            "verify_modular_decisions"
        ),
        "passed": True,
        "mutation_performed": False,
        "authority_effect": "none",
        "packet_id": latest.get(
            "packet_id"
        ),
        "proposal_count": len(
            proposals
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
            "Prepare or verify immutable modular decision proposals."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "prepare",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "prepare":
            result = prepare_decisions()
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

    except DecisionPreparationError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        arguments.operation
                    ),
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
