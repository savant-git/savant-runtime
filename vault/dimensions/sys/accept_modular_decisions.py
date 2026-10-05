#!/usr/bin/env python3
"""
Accept eligible modular decision proposals under the current user directive.

This tool does not modify implementation files.

It creates immutable accepted-decision records only when every proposal:

- remains in the proposed state
- has no unresolved blockers
- requests an eligible disposition
- declares decision authority
- preserves authority, history, lineage, provenance, and rollback
- exposes exactly nine review gates
- exposes exactly nine acceptance conditions
- exposes exactly nine rejection conditions
- exposes exactly nine rollback requirements

The current user directive authorizes the assistant to make further decisions
and implement the modular architecture to the ideal justified degree.

Accepted decisions remain immutable. Later changes must supersede them.
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

PROPOSAL_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-decisions"
)

ACCEPTED_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-accepted-decisions"
)

LATEST_PROPOSALS: Final[Path] = (
    PROPOSAL_ROOT
    / "latest.json"
)

ACCEPTED_DECISION_GRAPH: Final[Path] = (
    ROOT
    / "authority_graph"
    / "accepted_decisions"
    / "modular_architecture"
)

ELIGIBLE_DISPOSITIONS: Final[tuple[str, ...]] = (
    "approve",
    "supersede",
    "instance",
    "project",
)

REQUIRED_REVIEW_GATES: Final[tuple[str, ...]] = (
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

DECISION_EFFECTS: Final[tuple[str, ...]] = (
    "authority_preserved",
    "history_preserved",
    "lineage_preserved",
    "provenance_preserved",
    "dependencies_exposed",
    "rollback_required",
    "validation_required",
    "footprint_minimized",
    "implementation_authorized",
)


class AcceptanceError(RuntimeError):
    """Raised when a proposal cannot be accepted safely."""


@dataclass(frozen=True, slots=True)
class AcceptedDecision:
    id: str
    proposal_id: str
    packet_id: str
    classification_id: str
    candidate_id: str
    candidate_ordinal: int
    phase: str
    source_path: str
    source_finding_key: str
    disposition: str
    authorized_action: str
    authority: str
    authority_source: str
    state: str
    accepted_at: str
    immutable: bool
    mutation_authorized: bool
    rationale: str
    review_gates: tuple[str, ...]
    preservation_requirements: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    rollback_requirements: tuple[str, ...]
    effects: tuple[str, ...]
    supersedes: tuple[str, ...]
    superseded_by: tuple[str, ...]


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


def immutable_write(
    path: Path,
    value: object,
) -> None:
    if path.exists():
        existing = path.read_bytes()
        proposed = canonical_json_bytes(value)

        if existing != proposed:
            raise AcceptanceError(
                f"immutable decision already exists with different content: {path}"
            )

        return

    atomic_write(
        path,
        value,
    )


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AcceptanceError(
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
        raise AcceptanceError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise AcceptanceError(
            f"JSON root must be an object: {path}"
        )

    return value


def resolve_proposals_path() -> tuple[str, Path]:
    latest = load_json(
        LATEST_PROPOSALS
    )

    packet_id = latest.get(
        "packet_id"
    )

    raw_path = latest.get(
        "proposals"
    )

    if not isinstance(packet_id, str):
        raise AcceptanceError(
            "latest proposal packet lacks packet id"
        )

    if not isinstance(raw_path, str):
        raise AcceptanceError(
            "latest proposal packet lacks proposals path"
        )

    path = Path(raw_path)

    if not path.is_file():
        raise AcceptanceError(
            f"proposal file missing: {path}"
        )

    return packet_id, path


def require_string(
    value: object,
    field: str,
    proposal_id: str,
) -> str:
    if not isinstance(value, str):
        raise AcceptanceError(
            f"proposal {proposal_id} lacks string field {field}"
        )

    if not value.strip():
        raise AcceptanceError(
            f"proposal {proposal_id} has empty field {field}"
        )

    return value


def require_string_tuple(
    value: object,
    field: str,
    proposal_id: str,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise AcceptanceError(
            f"proposal {proposal_id} lacks array field {field}"
        )

    result = tuple(
        require_string(
            item,
            field,
            proposal_id,
        )
        for item in value
    )

    if len(result) != len(set(result)):
        raise AcceptanceError(
            f"proposal {proposal_id} contains duplicate {field}"
        )

    return result


def validate_proposal(
    proposal: dict[str, Any],
) -> None:
    proposal_id = require_string(
        proposal.get("id"),
        "id",
        "<unknown>",
    )

    state = require_string(
        proposal.get("state"),
        "state",
        proposal_id,
    )

    if state != "proposed":
        raise AcceptanceError(
            f"proposal {proposal_id} state is not proposed: {state}"
        )

    if proposal.get("mutation_authorized") is not False:
        raise AcceptanceError(
            f"proposal {proposal_id} prematurely authorizes mutation"
        )

    disposition = require_string(
        proposal.get("disposition"),
        "disposition",
        proposal_id,
    )

    if disposition not in ELIGIBLE_DISPOSITIONS:
        raise AcceptanceError(
            f"proposal {proposal_id} has ineligible disposition: {disposition}"
        )

    authority_required = require_string(
        proposal.get("authority_required"),
        "authority_required",
        proposal_id,
    )

    if authority_required != "decision":
        raise AcceptanceError(
            f"proposal {proposal_id} requires unsupported authority: "
            f"{authority_required}"
        )

    blockers = require_string_tuple(
        proposal.get("blockers"),
        "blockers",
        proposal_id,
    )

    if blockers:
        raise AcceptanceError(
            f"proposal {proposal_id} remains blocked: {list(blockers)!r}"
        )

    review_gates = require_string_tuple(
        proposal.get("review_gates"),
        "review_gates",
        proposal_id,
    )

    if review_gates != REQUIRED_REVIEW_GATES:
        raise AcceptanceError(
            f"proposal {proposal_id} review gates differ from authority"
        )

    acceptance_conditions = require_string_tuple(
        proposal.get("acceptance_conditions"),
        "acceptance_conditions",
        proposal_id,
    )

    rejection_conditions = require_string_tuple(
        proposal.get("rejection_conditions"),
        "rejection_conditions",
        proposal_id,
    )

    rollback_requirements = require_string_tuple(
        proposal.get("rollback_requirements"),
        "rollback_requirements",
        proposal_id,
    )

    if len(acceptance_conditions) != 9:
        raise AcceptanceError(
            f"proposal {proposal_id} requires exactly 9 acceptance conditions"
        )

    if len(rejection_conditions) != 9:
        raise AcceptanceError(
            f"proposal {proposal_id} requires exactly 9 rejection conditions"
        )

    if len(rollback_requirements) != 9:
        raise AcceptanceError(
            f"proposal {proposal_id} requires exactly 9 rollback requirements"
        )


def decision_identity(
    proposal_id: str,
    packet_id: str,
) -> str:
    return (
        "accepted-decision:"
        + sha256_text(
            "\x1f".join(
                (
                    proposal_id,
                    packet_id,
                    "current_user_directive",
                )
            )
        )[:24]
    )


def superseded_decisions(
    proposal: dict[str, Any],
) -> tuple[str, ...]:
    disposition = str(
        proposal.get(
            "disposition",
            "",
        )
    )

    source_finding_key = str(
        proposal.get(
            "source_finding_key",
            "",
        )
    )

    if (
        disposition == "supersede"
        and source_finding_key
    ):
        return (
            f"historical-implementation:{source_finding_key}",
        )

    return ()


def accept_proposal(
    proposal: dict[str, Any],
    *,
    packet_id: str,
    accepted_at: str,
) -> AcceptedDecision:
    validate_proposal(
        proposal
    )

    proposal_id = str(
        proposal["id"]
    )

    candidate_ordinal = proposal.get(
        "candidate_ordinal"
    )

    if not isinstance(
        candidate_ordinal,
        int,
    ):
        raise AcceptanceError(
            f"proposal {proposal_id} lacks integer candidate ordinal"
        )

    return AcceptedDecision(
        id=decision_identity(
            proposal_id,
            packet_id,
        ),
        proposal_id=proposal_id,
        packet_id=packet_id,
        classification_id=str(
            proposal["classification_id"]
        ),
        candidate_id=str(
            proposal["candidate_id"]
        ),
        candidate_ordinal=(
            candidate_ordinal
        ),
        phase=str(
            proposal["phase"]
        ),
        source_path=str(
            proposal["source_path"]
        ),
        source_finding_key=str(
            proposal["source_finding_key"]
        ),
        disposition=str(
            proposal["disposition"]
        ),
        authorized_action=str(
            proposal["proposed_action"]
        ),
        authority="decision",
        authority_source=(
            "current_user_directive:"
            "make_further_decisions_and_implement_ideal_degree"
        ),
        state="accepted",
        accepted_at=accepted_at,
        immutable=True,
        mutation_authorized=True,
        rationale=str(
            proposal["rationale"]
        ),
        review_gates=tuple(
            str(value)
            for value in proposal["review_gates"]
        ),
        preservation_requirements=tuple(
            str(value)
            for value in proposal[
                "preservation_requirements"
            ]
        ),
        validation_requirements=tuple(
            str(value)
            for value in proposal[
                "validation_requirements"
            ]
        ),
        rollback_requirements=tuple(
            str(value)
            for value in proposal[
                "rollback_requirements"
            ]
        ),
        effects=DECISION_EFFECTS,
        supersedes=superseded_decisions(
            proposal
        ),
        superseded_by=(),
    )


def write_authoritative_decision(
    decision: AcceptedDecision,
) -> Path:
    decision_path = (
        ACCEPTED_DECISION_GRAPH
        / f"{decision.id.replace(':', '__')}.json"
    )

    immutable_write(
        decision_path,
        {
            "schema": (
                "savant://authority-graph/"
                "accepted-modular-decision/1.0.0"
            ),
            **asdict(decision),
        },
    )

    return decision_path


def accept_decisions() -> dict[str, Any]:
    packet_id, proposals_path = (
        resolve_proposals_path()
    )

    proposals_bytes = (
        proposals_path.read_bytes()
    )

    proposals_document = json.loads(
        proposals_bytes.decode("utf-8")
    )

    proposals = proposals_document.get(
        "proposals"
    )

    if not isinstance(
        proposals,
        list,
    ):
        raise AcceptanceError(
            "proposals must be an array"
        )

    accepted_at = utc_timestamp()

    decisions = tuple(
        accept_proposal(
            proposal,
            packet_id=packet_id,
            accepted_at=accepted_at,
        )
        for proposal in proposals
        if isinstance(proposal, dict)
    )

    decision_ids = [
        decision.id
        for decision in decisions
    ]

    if len(decision_ids) != len(
        set(decision_ids)
    ):
        raise AcceptanceError(
            "accepted decision identifiers are duplicated"
        )

    authoritative_paths = tuple(
        write_authoritative_decision(
            decision
        )
        for decision in decisions
    )

    run_root = (
        ACCEPTED_ROOT
        / accepted_at
    )

    report_path = (
        run_root
        / "report.json"
    )

    decisions_path = (
        run_root
        / "decisions.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        ACCEPTED_ROOT
        / "latest.json"
    )

    disposition_counts = Counter(
        decision.disposition
        for decision in decisions
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "accepted-modular-decision-report/1.0.0"
        ),
        "operation": "accept_modular_decisions",
        "timestamp": accepted_at,
        "passed": True,
        "authority_effect": "accepted_decisions_created",
        "implementation_mutation_performed": False,
        "packet_id": packet_id,
        "proposal_file": str(
            proposals_path
        ),
        "proposal_digest": sha256_bytes(
            proposals_bytes
        ),
        "accepted_decision_count": len(
            decisions
        ),
        "disposition_counts": {
            disposition: disposition_counts[
                disposition
            ]
            for disposition in ELIGIBLE_DISPOSITIONS
        },
        "authoritative_paths": [
            str(path)
            for path in authoritative_paths
        ],
    }

    decisions_document = {
        "schema": (
            "savant://vault/dimensions/"
            "accepted-modular-decisions/1.0.0"
        ),
        "packet_id": packet_id,
        "accepted_at": accepted_at,
        "decision_count": len(
            decisions
        ),
        "decisions": [
            asdict(decision)
            for decision in decisions
        ],
    }

    atomic_write(
        report_path,
        report,
    )

    atomic_write(
        decisions_path,
        decisions_document,
    )

    manifest_entries = []

    for path in (
        report_path,
        decisions_path,
        *authoritative_paths,
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
                "accepted-modular-decision-manifest/1.0.0"
            ),
            "packet_id": packet_id,
            "entries": manifest_entries,
        },
    )

    atomic_write(
        latest_path,
        {
            "packet_id": packet_id,
            "timestamp": accepted_at,
            "report": str(report_path),
            "decisions": str(
                decisions_path
            ),
            "manifest": str(
                manifest_path
            ),
            "accepted_decision_count": len(
                decisions
            ),
            "authority_effect": (
                "accepted_decisions_created"
            ),
            "implementation_mutation_performed": False,
        },
    )

    return {
        "operation": "accept_modular_decisions",
        "passed": True,
        "packet_id": packet_id,
        "accepted_decision_count": len(
            decisions
        ),
        "authority_effect": (
            "accepted_decisions_created"
        ),
        "implementation_mutation_performed": False,
        "paths": {
            "report": str(report_path),
            "decisions": str(
                decisions_path
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
        ACCEPTED_ROOT
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
        raise AcceptanceError(
            "latest acceptance record lacks manifest path"
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
        raise AcceptanceError(
            "acceptance manifest entries must be an array"
        )

    verified_entries = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise AcceptanceError(
                "acceptance manifest entry must be an object"
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
            raise AcceptanceError(
                "manifest entry lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise AcceptanceError(
                "manifest entry lacks digest"
            )

        path = Path(
            raw_path
        )

        if not path.is_file():
            raise AcceptanceError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise AcceptanceError(
                f"manifest digest mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(path),
                "sha256": actual_digest,
                "passed": True,
            }
        )

    raw_decisions = latest.get(
        "decisions"
    )

    if not isinstance(
        raw_decisions,
        str,
    ):
        raise AcceptanceError(
            "latest acceptance record lacks decisions path"
        )

    decisions_document = load_json(
        Path(raw_decisions)
    )

    decisions = decisions_document.get(
        "decisions"
    )

    if not isinstance(
        decisions,
        list,
    ):
        raise AcceptanceError(
            "accepted decisions must be an array"
        )

    for decision in decisions:
        if not isinstance(
            decision,
            dict,
        ):
            raise AcceptanceError(
                "accepted decision must be an object"
            )

        if decision.get("state") != "accepted":
            raise AcceptanceError(
                "accepted decision has invalid state"
            )

        if decision.get("immutable") is not True:
            raise AcceptanceError(
                "accepted decision is not immutable"
            )

        if decision.get(
            "mutation_authorized"
        ) is not True:
            raise AcceptanceError(
                "accepted decision does not authorize mutation"
            )

        effects = decision.get(
            "effects"
        )

        if not isinstance(
            effects,
            list,
        ):
            raise AcceptanceError(
                "accepted decision lacks effects"
            )

        if tuple(effects) != DECISION_EFFECTS:
            raise AcceptanceError(
                "accepted decision effects differ from authority"
            )

    return {
        "operation": (
            "verify_accepted_modular_decisions"
        ),
        "passed": True,
        "packet_id": latest.get(
            "packet_id"
        ),
        "accepted_decision_count": len(
            decisions
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
            "Accept or verify eligible modular decision proposals."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "accept",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "accept":
            result = accept_decisions()
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

    except AcceptanceError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        arguments.operation
                    ),
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
