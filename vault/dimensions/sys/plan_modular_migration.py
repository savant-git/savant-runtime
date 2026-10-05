#!/usr/bin/env python3
"""
Create a deterministic, read-only migration plan from the latest modular
conformance audit.

This tool does not modify project authority or implementation files.

It converts audit findings into ordered migration candidates while preserving:

- authority
- history
- compatibility
- lineage
- provenance
- reversibility
- dependency transparency
- evidence
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

AUDIT_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-conformance"
)

PLAN_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "modular-migration"
)

LATEST_AUDIT: Final[Path] = (
    AUDIT_ROOT
    / "latest.json"
)

AUTHORITY_ORDER: Final[tuple[str, ...]] = (
    "directive",
    "graph",
    "decision",
    "constitution",
    "implementation",
    "evidence",
    "projection",
    "history",
    "speculation",
)

MIGRATION_PHASES: Final[tuple[str, ...]] = (
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

ACTION_CLASSES: Final[tuple[str, ...]] = (
    "preserve",
    "classify",
    "extend",
    "project",
    "instance",
    "supersede",
    "migrate",
    "verify",
    "refuse",
)


class PlanningError(RuntimeError):
    """Raised when a migration plan cannot be produced reliably."""


@dataclass(frozen=True, slots=True)
class MigrationCandidate:
    id: str
    phase: str
    ordinal: int
    source_finding_key: str
    source_path: str
    severity: str
    action_class: str
    authority_required: str
    mutation_allowed: bool
    rationale: str
    prerequisite_ids: tuple[str, ...]
    dependency_paths: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    rollback_requirements: tuple[str, ...]
    preservation_requirements: tuple[str, ...]
    status: str


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    id: str
    timestamp: str
    status: str
    authority_effect: str
    mutation_performed: bool
    audit_report: str
    audit_digest: str
    candidate_count: int
    phases: tuple[str, ...]
    candidates: tuple[MigrationCandidate, ...]


def timestamp() -> str:
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


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PlanningError(
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
        raise PlanningError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise PlanningError(
            f"JSON root must be an object: {path}"
        )

    return value


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


def resolve_audit_report() -> Path:
    latest = load_json(
        LATEST_AUDIT
    )

    raw_report = latest.get(
        "report"
    )

    if not isinstance(raw_report, str):
        raise PlanningError(
            "latest audit pointer lacks report path"
        )

    report_path = Path(
        raw_report
    )

    if not report_path.is_file():
        raise PlanningError(
            f"audit report missing: {report_path}"
        )

    return report_path


def finding_phase(
    finding: dict[str, Any],
) -> str:
    key = str(
        finding.get("key", "")
    ).casefold()

    if "authority" in key:
        return "authority"

    if "mood" in key:
        return "moods"

    if "slot" in key:
        return "slots"

    if "duplicate" in key:
        return "duplication"

    if "projection" in key:
        return "projections"

    if "instance" in key:
        return "instances"

    if "lexicon" in key or "term" in key:
        return "lexicon"

    if "dependency" in key:
        return "dependencies"

    return "verification"


def action_for_finding(
    finding: dict[str, Any],
) -> str:
    key = str(
        finding.get("key", "")
    ).casefold()

    severity = str(
        finding.get("severity", "notice")
    ).casefold()

    if key == "missing_required_authority":
        return "refuse"

    if "canonical_mood_mismatch" in key:
        return "supersede"

    if "mood_fusion_count" in key:
        return "extend"

    if "missing_mood_fusions" in key:
        return "extend"

    if "slot_semantic" in key:
        return "supersede"

    if "duplicate" in key:
        return "classify"

    if severity == "error":
        return "refuse"

    return "classify"


def authority_for_action(
    action_class: str,
) -> str:
    mapping = {
        "preserve": "history",
        "classify": "evidence",
        "extend": "decision",
        "project": "implementation",
        "instance": "decision",
        "supersede": "decision",
        "migrate": "decision",
        "verify": "implementation",
        "refuse": "directive",
    }

    return mapping[action_class]


def mutation_allowed_for_action(
    action_class: str,
) -> bool:
    return action_class in {
        "extend",
        "project",
        "instance",
        "supersede",
        "migrate",
    }


def validation_for_phase(
    phase: str,
) -> tuple[str, ...]:
    common = (
        "syntax",
        "integrity",
        "lineage",
        "provenance",
        "replay",
        "recovery",
    )

    phase_specific = {
        "authority": (
            "authority_precedence",
            "accepted_decision",
            "history_preservation",
        ),
        "lexicon": (
            "lexeme_collision",
            "alias_preservation",
            "historical_term_preservation",
        ),
        "instances": (
            "stable_identity",
            "instance_contract",
            "dependency_manifest",
        ),
        "moods": (
            "nine_mood_cardinality",
            "thirty_six_fusions",
            "fusion_uniqueness",
        ),
        "slots": (
            "additive_semantics",
            "maximum_four_slots",
            "independent_removal",
        ),
        "projections": (
            "source_authority",
            "deterministic_regeneration",
            "projection_disposability",
        ),
        "duplication": (
            "authority_ownership",
            "content_equivalence",
            "compatibility_preservation",
        ),
        "dependencies": (
            "dependency_resolution",
            "dependent_impact",
            "execution_path",
        ),
        "verification": (
            "focused_tests",
            "integrated_verification",
            "report_integrity",
        ),
    }

    return common + phase_specific[phase]


def preservation_for_phase(
    phase: str,
) -> tuple[str, ...]:
    base = (
        "authority",
        "meaning",
        "history",
        "lineage",
        "provenance",
        "recoverability",
    )

    specific = {
        "authority": (
            "accepted_decisions",
            "constitutional_canon",
            "unresolved_conflicts",
        ),
        "lexicon": (
            "aliases",
            "deprecated_terms",
            "quotations",
        ),
        "instances": (
            "stable_identifiers",
            "external_references",
            "constituent_identity",
        ),
        "moods": (
            "source_mood_semantics",
            "fusion_lineage",
            "historical_names",
        ),
        "slots": (
            "occupant_identity",
            "occupant_authority",
            "independent_removability",
        ),
        "projections": (
            "authoritative_sources",
            "projection_targets",
            "generation_inputs",
        ),
        "duplication": (
            "compatibility_copies",
            "historical_evidence",
            "external_contracts",
        ),
        "dependencies": (
            "working_behavior",
            "execution_order",
            "consumer_contracts",
        ),
        "verification": (
            "test_evidence",
            "failure_evidence",
            "previous_verified_baseline",
        ),
    }

    return base + specific[phase]


def rollback_for_phase(
    phase: str,
) -> tuple[str, ...]:
    common = (
        "prechange_digest",
        "complete_previous_file",
        "reversal_command",
        "postrollback_verification",
    )

    phase_specific = {
        "authority": (
            "superseding_decision_reversal",
            "authority_graph_replay",
            "conflict_restoration",
        ),
        "lexicon": (
            "alias_restoration",
            "registry_restoration",
            "reference_reindex",
        ),
        "instances": (
            "instance_manifest_restoration",
            "reference_restoration",
            "dependency_replay",
        ),
        "moods": (
            "mood_registry_restoration",
            "fusion_registry_restoration",
            "historical_mapping_restoration",
        ),
        "slots": (
            "slot_registry_restoration",
            "occupant_detachment",
            "host_state_restoration",
        ),
        "projections": (
            "projection_removal",
            "source_replay",
            "target_cleanup",
        ),
        "duplication": (
            "copy_restoration",
            "ownership_restoration",
            "compatibility_replay",
        ),
        "dependencies": (
            "dependency_version_restoration",
            "consumer_revalidation",
            "execution_replay",
        ),
        "verification": (
            "report_restoration",
            "test_replay",
            "digest_revalidation",
        ),
    }

    return common + phase_specific[phase]


def prerequisite_ids_for_phase(
    phase: str,
    phase_candidates: dict[
        str,
        list[MigrationCandidate],
    ],
) -> tuple[str, ...]:
    phase_index = MIGRATION_PHASES.index(
        phase
    )

    prior_phases = MIGRATION_PHASES[
        :phase_index
    ]

    prerequisites: list[str] = []

    for prior_phase in prior_phases:
        prerequisites.extend(
            candidate.id
            for candidate in phase_candidates.get(
                prior_phase,
                []
            )
            if candidate.status
            != "informational"
        )

    return tuple(
        prerequisites
    )


def candidate_identity(
    *,
    phase: str,
    source_finding_key: str,
    source_path: str,
    action_class: str,
) -> str:
    payload = "\x1f".join(
        (
            phase,
            source_finding_key,
            source_path,
            action_class,
        )
    )

    return (
        "migration-candidate:"
        + sha256_text(payload)[:24]
    )


def build_candidates(
    findings: list[dict[str, Any]],
) -> tuple[MigrationCandidate, ...]:
    raw_candidates: list[
        tuple[
            str,
            dict[str, Any],
            str,
        ]
    ] = []

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        phase = finding_phase(
            finding
        )

        action_class = action_for_finding(
            finding
        )

        raw_candidates.append(
            (
                phase,
                finding,
                action_class,
            )
        )

    raw_candidates.sort(
        key=lambda item: (
            MIGRATION_PHASES.index(
                item[0]
            ),
            str(
                item[1].get(
                    "severity",
                    "notice",
                )
            ),
            str(
                item[1].get(
                    "path",
                    "",
                )
            ),
            str(
                item[1].get(
                    "key",
                    "",
                )
            ),
        )
    )

    provisional_by_phase: dict[
        str,
        list[MigrationCandidate],
    ] = {
        phase: []
        for phase in MIGRATION_PHASES
    }

    ordinal = 0

    for phase, finding, action_class in raw_candidates:
        ordinal += 1

        source_key = str(
            finding.get(
                "key",
                "unknown",
            )
        )

        source_path = str(
            finding.get(
                "path",
                "",
            )
        )

        candidate_id = candidate_identity(
            phase=phase,
            source_finding_key=source_key,
            source_path=source_path,
            action_class=action_class,
        )

        candidate = MigrationCandidate(
            id=candidate_id,
            phase=phase,
            ordinal=ordinal,
            source_finding_key=source_key,
            source_path=source_path,
            severity=str(
                finding.get(
                    "severity",
                    "notice",
                )
            ),
            action_class=action_class,
            authority_required=(
                authority_for_action(
                    action_class
                )
            ),
            mutation_allowed=(
                mutation_allowed_for_action(
                    action_class
                )
            ),
            rationale=str(
                finding.get(
                    "evidence",
                    "",
                )
            ),
            prerequisite_ids=(),
            dependency_paths=(),
            validation_requirements=(
                validation_for_phase(
                    phase
                )
            ),
            rollback_requirements=(
                rollback_for_phase(
                    phase
                )
            ),
            preservation_requirements=(
                preservation_for_phase(
                    phase
                )
            ),
            status=(
                "blocked"
                if action_class == "refuse"
                else "planned"
            ),
        )

        provisional_by_phase[
            phase
        ].append(candidate)

    finalized: list[MigrationCandidate] = []

    for phase in MIGRATION_PHASES:
        phase_candidates = (
            provisional_by_phase[
                phase
            ]
        )

        prerequisites = (
            prerequisite_ids_for_phase(
                phase,
                provisional_by_phase,
            )
        )

        for candidate in phase_candidates:
            finalized.append(
                MigrationCandidate(
                    id=candidate.id,
                    phase=candidate.phase,
                    ordinal=candidate.ordinal,
                    source_finding_key=(
                        candidate
                        .source_finding_key
                    ),
                    source_path=(
                        candidate.source_path
                    ),
                    severity=(
                        candidate.severity
                    ),
                    action_class=(
                        candidate.action_class
                    ),
                    authority_required=(
                        candidate
                        .authority_required
                    ),
                    mutation_allowed=(
                        candidate
                        .mutation_allowed
                    ),
                    rationale=(
                        candidate.rationale
                    ),
                    prerequisite_ids=(
                        prerequisites
                    ),
                    dependency_paths=(
                        candidate
                        .dependency_paths
                    ),
                    validation_requirements=(
                        candidate
                        .validation_requirements
                    ),
                    rollback_requirements=(
                        candidate
                        .rollback_requirements
                    ),
                    preservation_requirements=(
                        candidate
                        .preservation_requirements
                    ),
                    status=candidate.status,
                )
            )

    return tuple(
        finalized
    )


def extract_findings(
    audit_report: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = audit_report.get(
        "findings"
    )

    if isinstance(findings, list):
        return [
            finding
            for finding in findings
            if isinstance(finding, dict)
        ]

    latest = load_json(
        LATEST_AUDIT
    )

    findings_path_raw = latest.get(
        "findings"
    )

    if not isinstance(
        findings_path_raw,
        str,
    ):
        return []

    findings_document = load_json(
        Path(
            findings_path_raw
        )
    )

    external_findings = (
        findings_document.get(
            "findings"
        )
    )

    if not isinstance(
        external_findings,
        list,
    ):
        return []

    return [
        finding
        for finding in external_findings
        if isinstance(finding, dict)
    ]


def write_plan_bundle(
    plan: MigrationPlan,
) -> dict[str, str]:
    run_root = (
        PLAN_ROOT
        / plan.timestamp
    )

    plan_path = (
        run_root
        / "plan.json"
    )

    candidates_path = (
        run_root
        / "candidates.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        PLAN_ROOT
        / "latest.json"
    )

    plan_payload = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-migration-plan/1.0.0"
        ),
        **asdict(plan),
        "candidates": [
            asdict(candidate)
            for candidate in plan.candidates
        ],
    }

    candidates_payload = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-migration-candidates/1.0.0"
        ),
        "plan_id": plan.id,
        "candidate_count": (
            plan.candidate_count
        ),
        "candidates": [
            asdict(candidate)
            for candidate in plan.candidates
        ],
    }

    atomic_write(
        plan_path,
        plan_payload,
    )

    atomic_write(
        candidates_path,
        candidates_payload,
    )

    manifest_entries = []

    for path in (
        plan_path,
        candidates_path,
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
                "modular-migration-manifest/1.0.0"
            ),
            "plan_id": plan.id,
            "entries": manifest_entries,
        },
    )

    atomic_write(
        latest_path,
        {
            "plan_id": plan.id,
            "timestamp": plan.timestamp,
            "plan": str(plan_path),
            "candidates": str(
                candidates_path
            ),
            "manifest": str(
                manifest_path
            ),
            "candidate_count": (
                plan.candidate_count
            ),
            "status": plan.status,
            "mutation_performed": False,
            "authority_effect": "none",
        },
    )

    return {
        "plan": str(plan_path),
        "candidates": str(
            candidates_path
        ),
        "manifest": str(
            manifest_path
        ),
        "latest": str(
            latest_path
        ),
    }


def create_plan() -> dict[str, Any]:
    audit_report_path = (
        resolve_audit_report()
    )

    audit_bytes = (
        audit_report_path.read_bytes()
    )

    audit_report = json.loads(
        audit_bytes.decode("utf-8")
    )

    findings = extract_findings(
        audit_report
    )

    candidates = build_candidates(
        findings
    )

    run_timestamp = timestamp()

    plan_id = (
        "migration-plan:"
        + sha256_text(
            "\x1f".join(
                (
                    str(
                        audit_report_path
                    ),
                    sha256_bytes(
                        audit_bytes
                    ),
                    run_timestamp,
                )
            )
        )[:24]
    )

    blocked_count = sum(
        candidate.status == "blocked"
        for candidate in candidates
    )

    plan = MigrationPlan(
        id=plan_id,
        timestamp=run_timestamp,
        status=(
            "blocked"
            if blocked_count
            else "planned"
        ),
        authority_effect="none",
        mutation_performed=False,
        audit_report=str(
            audit_report_path
        ),
        audit_digest=sha256_bytes(
            audit_bytes
        ),
        candidate_count=len(
            candidates
        ),
        phases=MIGRATION_PHASES,
        candidates=candidates,
    )

    paths = write_plan_bundle(
        plan
    )

    action_counts = Counter(
        candidate.action_class
        for candidate in candidates
    )

    phase_counts = Counter(
        candidate.phase
        for candidate in candidates
    )

    return {
        "operation": (
            "plan_modular_migration"
        ),
        "passed": blocked_count == 0,
        "status": plan.status,
        "mutation_performed": False,
        "authority_effect": "none",
        "plan_id": plan.id,
        "candidate_count": (
            plan.candidate_count
        ),
        "blocked_count": blocked_count,
        "phase_counts": {
            phase: phase_counts[
                phase
            ]
            for phase in MIGRATION_PHASES
        },
        "action_counts": {
            action: action_counts[
                action
            ]
            for action in ACTION_CLASSES
        },
        "paths": paths,
    }


def verify_plan() -> dict[str, Any]:
    latest_path = (
        PLAN_ROOT
        / "latest.json"
    )

    latest = load_json(
        latest_path
    )

    manifest_raw = latest.get(
        "manifest"
    )

    if not isinstance(
        manifest_raw,
        str,
    ):
        raise PlanningError(
            "latest plan lacks manifest path"
        )

    manifest_path = Path(
        manifest_raw
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
        raise PlanningError(
            "plan manifest entries must be an array"
        )

    verified = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise PlanningError(
                "plan manifest entry must be an object"
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
            raise PlanningError(
                "manifest entry lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise PlanningError(
                "manifest entry lacks digest"
            )

        path = Path(
            raw_path
        )

        if not path.is_file():
            raise PlanningError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise PlanningError(
                f"manifest digest mismatch: {path}"
            )

        verified.append(
            {
                "path": str(path),
                "sha256": actual_digest,
                "passed": True,
            }
        )

    plan_raw = latest.get(
        "plan"
    )

    if not isinstance(
        plan_raw,
        str,
    ):
        raise PlanningError(
            "latest plan lacks plan path"
        )

    plan = load_json(
        Path(plan_raw)
    )

    candidates = plan.get(
        "candidates"
    )

    if not isinstance(
        candidates,
        list,
    ):
        raise PlanningError(
            "plan candidates must be an array"
        )

    ordinals = [
        candidate.get(
            "ordinal"
        )
        for candidate in candidates
        if isinstance(
            candidate,
            dict,
        )
    ]

    if ordinals != list(
        range(
            1,
            len(candidates) + 1,
        )
    ):
        raise PlanningError(
            "candidate ordinals are not contiguous"
        )

    return {
        "operation": (
            "verify_modular_migration_plan"
        ),
        "passed": True,
        "mutation_performed": False,
        "authority_effect": "none",
        "plan_id": latest.get(
            "plan_id"
        ),
        "candidate_count": len(
            candidates
        ),
        "manifest_entry_count": len(
            verified
        ),
        "verified_entries": verified,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or verify a deterministic "
            "modular-conformance migration plan."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "plan",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "plan":
            result = create_plan()
        else:
            result = verify_plan()

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0 if result["passed"] else 1

    except PlanningError as error:
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
