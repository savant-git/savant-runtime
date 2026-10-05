#!/usr/bin/env python3
"""
Perform deterministic semantic review of the latest modular binding packet.

This stage remains read-only with respect to authoritative and implementation
files.

It evaluates whether each bound unit has enough verified evidence to proceed
toward replacement compilation. It never creates replacement content, never
authorizes implementation, and never mutates the target.
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

BINDING_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-binding"
)

REVIEW_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-review"
)

LATEST_BINDING: Final[Path] = (
    BINDING_ROOT
    / "latest.json"
)

SUPPORTED_ACTIONS: Final[tuple[str, ...]] = (
    "extend",
    "instance",
    "migrate",
    "project",
    "supersede",
    "verify",
    "preserve",
    "classify",
    "refuse",
)

REVIEW_STATES: Final[tuple[str, ...]] = (
    "reviewed",
    "blocked",
    "ready",
)

SEMANTIC_AXES: Final[tuple[str, ...]] = (
    "authority",
    "identity",
    "meaning",
    "compatibility",
    "dependencies",
    "lineage",
    "provenance",
    "reversibility",
    "footprint",
)

KNOWN_FINDING_RULES: Final[dict[str, str]] = {
    "canonical_mood_mismatch": (
        "Replace only active historical mood terminology with the "
        "accepted canonical moods while preserving unrelated Segue "
        "elements, historical evidence, aliases, and compatibility."
    ),
    "mood_fusion_count": (
        "Complete the canonical unordered two-mood fusion registry "
        "without self-fusions, directional duplicates, or third moods."
    ),
    "missing_mood_fusions": (
        "Create missing two-mood fusion records only after ability "
        "uniqueness and lexicon collision validation."
    ),
    "invalid_mood_registry": (
        "Restore the complete canonical mood registry structure."
    ),
    "invalid_slot_semantics": (
        "Restore additive slot semantics without capability fusion."
    ),
    "duplicate_content_candidate": (
        "Classify ownership and authority before replacing duplicate "
        "content with instances or deterministic projections."
    ),
    "missing_required_authority": (
        "Refuse implementation until the required authority exists."
    ),
}

REQUIRED_READY_GATES: Final[tuple[str, ...]] = (
    "bound_unit_verified",
    "target_verified",
    "baseline_verified",
    "digest_verified",
    "action_supported",
    "semantic_rule_resolved",
    "dependencies_reviewed",
    "dependents_reviewed",
    "authority_preserved",
)


class ReviewError(RuntimeError):
    """Raised when semantic review cannot complete reliably."""


@dataclass(frozen=True, slots=True)
class SemanticReview:
    id: str
    bound_unit_id: str
    execution_unit_id: str
    decision_id: str
    candidate_id: str
    candidate_ordinal: int
    phase: str
    target_path: str | None
    source_finding_key: str
    authorized_action: str
    semantic_rule: str | None
    semantic_axes: tuple[str, ...]
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    dependencies: tuple[str, ...]
    dependents: tuple[str, ...]
    blockers: tuple[str, ...]
    state: str
    semantic_review_complete: bool
    replacement_content_compiled: bool
    implementation_authorized: bool


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
        raise ReviewError(
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
        raise ReviewError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise ReviewError(
            f"JSON root must be an object: {path}"
        )

    return value


def resolve_bound_units_path() -> Path:
    latest = load_json(
        LATEST_BINDING
    )

    raw_path = latest.get(
        "units"
    )

    if not isinstance(raw_path, str):
        raise ReviewError(
            "latest binding packet lacks units path"
        )

    path = Path(raw_path)

    if not path.is_file():
        raise ReviewError(
            f"bound units file missing: {path}"
        )

    return path


def file_digest(path: Path) -> str | None:
    try:
        return sha256_bytes(
            path.read_bytes()
        )
    except OSError:
        return None


def semantic_rule_for(
    finding_key: str,
) -> str | None:
    if finding_key in KNOWN_FINDING_RULES:
        return KNOWN_FINDING_RULES[
            finding_key
        ]

    for known_key, rule in (
        KNOWN_FINDING_RULES.items()
    ):
        if known_key in finding_key:
            return rule

    return None


def review_identity(
    bound_unit_id: str,
    target_path: str | None,
    source_finding_key: str,
) -> str:
    payload = "\x1f".join(
        (
            bound_unit_id,
            target_path or "",
            source_finding_key,
        )
    )

    return (
        "semantic-review:"
        + sha256_text(payload)[:24]
    )


def string_paths(
    value: object,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()

    paths: list[str] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        raw_path = item.get(
            "path"
        )

        if isinstance(raw_path, str):
            paths.append(raw_path)

    return tuple(
        sorted(
            dict.fromkeys(paths)
        )
    )


def review_bound_unit(
    unit: dict[str, Any],
) -> SemanticReview:
    bound_unit_id = str(
        unit.get("id", "")
    )

    if not bound_unit_id:
        raise ReviewError(
            "bound unit lacks stable id"
        )

    candidate_ordinal = unit.get(
        "candidate_ordinal"
    )

    if not isinstance(
        candidate_ordinal,
        int,
    ):
        raise ReviewError(
            f"bound unit {bound_unit_id} "
            "lacks integer candidate ordinal"
        )

    target_path_value = unit.get(
        "target_path"
    )

    target_path = (
        target_path_value
        if isinstance(
            target_path_value,
            str,
        )
        else None
    )

    target = (
        Path(target_path)
        if target_path is not None
        else None
    )

    source_finding_key = str(
        unit.get(
            "source_finding_key",
            "",
        )
    )

    authorized_action = str(
        unit.get(
            "authorized_action",
            "",
        )
    )

    semantic_rule = semantic_rule_for(
        source_finding_key
    )

    dependencies = string_paths(
        unit.get("dependencies")
    )

    dependents = string_paths(
        unit.get("dependents")
    )

    actual_digest = unit.get(
        "actual_before_digest"
    )

    baseline_digest = unit.get(
        "baseline_digest"
    )

    baseline_path_value = unit.get(
        "baseline_path"
    )

    baseline_path = (
        Path(baseline_path_value)
        if isinstance(
            baseline_path_value,
            str,
        )
        else None
    )

    live_digest = (
        file_digest(target)
        if target is not None
        and target.is_file()
        else None
    )

    preserved_digest = (
        file_digest(baseline_path)
        if baseline_path is not None
        and baseline_path.is_file()
        else None
    )

    gate_results = {
        "bound_unit_verified": (
            unit.get("state")
            in REVIEW_STATES
            or unit.get("state")
            == "blocked"
        ),
        "target_verified": (
            target is not None
            and target.is_file()
        ),
        "baseline_verified": (
            baseline_path is not None
            and baseline_path.is_file()
            and isinstance(
                baseline_digest,
                str,
            )
            and preserved_digest
            == baseline_digest
        ),
        "digest_verified": (
            isinstance(
                actual_digest,
                str,
            )
            and live_digest
            == actual_digest
        ),
        "action_supported": (
            authorized_action
            in SUPPORTED_ACTIONS
        ),
        "semantic_rule_resolved": (
            semantic_rule is not None
        ),
        "dependencies_reviewed": (
            isinstance(
                unit.get("dependencies"),
                list,
            )
        ),
        "dependents_reviewed": (
            isinstance(
                unit.get("dependents"),
                list,
            )
        ),
        "authority_preserved": (
            unit.get(
                "mutation_authorized"
            )
            is True
            and unit.get(
                "implementation_authorized"
            )
            is False
        ),
    }

    passed_gates = tuple(
        gate
        for gate in REQUIRED_READY_GATES
        if gate_results[gate]
    )

    failed_gates = tuple(
        gate
        for gate in REQUIRED_READY_GATES
        if not gate_results[gate]
    )

    blockers: list[str] = []

    existing_blockers = unit.get(
        "blockers"
    )

    if isinstance(
        existing_blockers,
        list,
    ):
        blockers.extend(
            str(blocker)
            for blocker in existing_blockers
            if str(blocker)
            not in {
                "semantic review is incomplete",
                "replacement content is not compiled",
                "target-specific validation is not bound",
                "target-specific rollback is not bound",
            }
        )

    if not gate_results[
        "target_verified"
    ]:
        blockers.append(
            "target could not be verified"
        )

    if not gate_results[
        "baseline_verified"
    ]:
        blockers.append(
            "preserved baseline could not be verified"
        )

    if not gate_results[
        "digest_verified"
    ]:
        blockers.append(
            "live target differs from bound digest"
        )

    if not gate_results[
        "action_supported"
    ]:
        blockers.append(
            "authorized action is unsupported"
        )

    if not gate_results[
        "semantic_rule_resolved"
    ]:
        blockers.append(
            "semantic review rule is unresolved"
        )

    if not gate_results[
        "authority_preserved"
    ]:
        blockers.append(
            "authority boundary could not be verified"
        )

    semantic_complete = (
        not blockers
        and not failed_gates
    )

    if semantic_complete:
        blockers.extend(
            (
                "replacement content is not compiled",
                "target-specific validation is not bound",
                "target-specific rollback is not bound",
            )
        )

    state = (
        "reviewed"
        if semantic_complete
        else "blocked"
    )

    return SemanticReview(
        id=review_identity(
            bound_unit_id,
            target_path,
            source_finding_key,
        ),
        bound_unit_id=bound_unit_id,
        execution_unit_id=str(
            unit.get(
                "execution_unit_id",
                "",
            )
        ),
        decision_id=str(
            unit.get(
                "decision_id",
                "",
            )
        ),
        candidate_id=str(
            unit.get(
                "candidate_id",
                "",
            )
        ),
        candidate_ordinal=(
            candidate_ordinal
        ),
        phase=str(
            unit.get(
                "phase",
                "verification",
            )
        ),
        target_path=target_path,
        source_finding_key=(
            source_finding_key
        ),
        authorized_action=(
            authorized_action
        ),
        semantic_rule=semantic_rule,
        semantic_axes=SEMANTIC_AXES,
        passed_gates=passed_gates,
        failed_gates=failed_gates,
        dependencies=dependencies,
        dependents=dependents,
        blockers=tuple(
            dict.fromkeys(blockers)
        ),
        state=state,
        semantic_review_complete=(
            semantic_complete
        ),
        replacement_content_compiled=False,
        implementation_authorized=False,
    )


def review_binding() -> dict[str, Any]:
    units_path = resolve_bound_units_path()
    units_bytes = units_path.read_bytes()

    document = json.loads(
        units_bytes.decode("utf-8")
    )

    units = document.get(
        "units"
    )

    if not isinstance(units, list):
        raise ReviewError(
            "bound units must be an array"
        )

    reviews = tuple(
        review_bound_unit(unit)
        for unit in units
        if isinstance(unit, dict)
    )

    review_ids = [
        review.id
        for review in reviews
    ]

    if len(review_ids) != len(
        set(review_ids)
    ):
        raise ReviewError(
            "semantic review identifiers are duplicated"
        )

    ordinals = [
        review.candidate_ordinal
        for review in reviews
    ]

    if ordinals != sorted(ordinals):
        raise ReviewError(
            "semantic reviews are not in candidate order"
        )

    run_timestamp = utc_timestamp()

    packet_id = (
        "review-packet:"
        + sha256_text(
            "\x1f".join(
                (
                    str(units_path),
                    sha256_bytes(
                        units_bytes
                    ),
                    run_timestamp,
                )
            )
        )[:24]
    )

    state_counts = Counter(
        review.state
        for review in reviews
    )

    complete_count = sum(
        review.semantic_review_complete
        for review in reviews
    )

    run_root = (
        REVIEW_ROOT
        / run_timestamp
    )

    report_path = (
        run_root
        / "report.json"
    )

    reviews_path = (
        run_root
        / "reviews.json"
    )

    manifest_path = (
        run_root
        / "manifest.json"
    )

    latest_path = (
        REVIEW_ROOT
        / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-semantic-review-report/1.0.0"
        ),
        "operation": "review_modular_binding",
        "id": packet_id,
        "timestamp": run_timestamp,
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "source_units": str(
            units_path
        ),
        "source_units_digest": sha256_bytes(
            units_bytes
        ),
        "review_count": len(
            reviews
        ),
        "semantic_complete_count": (
            complete_count
        ),
        "reviewed_count": state_counts[
            "reviewed"
        ],
        "ready_count": state_counts[
            "ready"
        ],
        "blocked_count": state_counts[
            "blocked"
        ],
        "semantic_axes": list(
            SEMANTIC_AXES
        ),
        "required_ready_gates": list(
            REQUIRED_READY_GATES
        ),
        "supported_actions": list(
            SUPPORTED_ACTIONS
        ),
    }

    reviews_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-semantic-reviews/1.0.0"
        ),
        "packet_id": packet_id,
        "review_count": len(
            reviews
        ),
        "reviews": [
            asdict(review)
            for review in reviews
        ],
    }

    atomic_write_json(
        report_path,
        report,
    )

    atomic_write_json(
        reviews_path,
        reviews_document,
    )

    manifest_entries = []

    for path in (
        report_path,
        reviews_path,
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
                "modular-semantic-review-manifest/1.0.0"
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
            "report": str(
                report_path
            ),
            "reviews": str(
                reviews_path
            ),
            "manifest": str(
                manifest_path
            ),
            "review_count": len(
                reviews
            ),
            "semantic_complete_count": (
                complete_count
            ),
            "blocked_count": state_counts[
                "blocked"
            ],
            "authority_effect": "none",
            "implementation_mutation_performed": False,
        },
    )

    return {
        "operation": (
            "review_modular_binding"
        ),
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "packet_id": packet_id,
        "review_count": len(
            reviews
        ),
        "semantic_complete_count": (
            complete_count
        ),
        "blocked_count": state_counts[
            "blocked"
        ],
        "latest": str(
            latest_path
        ),
    }


def verify_latest() -> dict[str, Any]:
    latest_path = (
        REVIEW_ROOT
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
        raise ReviewError(
            "latest review packet lacks manifest path"
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
        raise ReviewError(
            "review manifest entries must be an array"
        )

    verified_entries = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise ReviewError(
                "review manifest entry must be an object"
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
            raise ReviewError(
                "manifest entry lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise ReviewError(
                "manifest entry lacks digest"
            )

        path = Path(raw_path)

        if not path.is_file():
            raise ReviewError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise ReviewError(
                f"manifest digest mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(path),
                "sha256": actual_digest,
                "passed": True,
            }
        )

    raw_reviews = latest.get(
        "reviews"
    )

    if not isinstance(
        raw_reviews,
        str,
    ):
        raise ReviewError(
            "latest review packet lacks reviews path"
        )

    reviews_document = load_json(
        Path(raw_reviews)
    )

    reviews = reviews_document.get(
        "reviews"
    )

    if not isinstance(
        reviews,
        list,
    ):
        raise ReviewError(
            "semantic reviews must be an array"
        )

    review_ids: list[str] = []

    for review in reviews:
        if not isinstance(
            review,
            dict,
        ):
            raise ReviewError(
                "semantic review must be an object"
            )

        review_id = review.get(
            "id"
        )

        if not isinstance(
            review_id,
            str,
        ):
            raise ReviewError(
                "semantic review lacks stable id"
            )

        review_ids.append(
            review_id
        )

        state = review.get(
            "state"
        )

        if state not in REVIEW_STATES:
            raise ReviewError(
                f"semantic review has invalid state: {review_id}"
            )

        if review.get(
            "replacement_content_compiled"
        ) is not False:
            raise ReviewError(
                "semantic review falsely claims replacement compilation: "
                f"{review_id}"
            )

        if review.get(
            "implementation_authorized"
        ) is not False:
            raise ReviewError(
                "semantic review prematurely authorizes implementation: "
                f"{review_id}"
            )

        axes = review.get(
            "semantic_axes"
        )

        if tuple(
            axes
            if isinstance(
                axes,
                list,
            )
            else ()
        ) != SEMANTIC_AXES:
            raise ReviewError(
                f"semantic axes differ from authority: {review_id}"
            )

    if len(review_ids) != len(
        set(review_ids)
    ):
        raise ReviewError(
            "semantic review identifiers are duplicated"
        )

    return {
        "operation": (
            "verify_modular_review"
        ),
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "packet_id": latest.get(
            "packet_id"
        ),
        "review_count": len(
            reviews
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
            "Review or verify modular binding semantics."
        )
    )

    parser.add_argument(
        "operation",
        choices=(
            "review",
            "verify",
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.operation == "review":
            result = review_binding()
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

    except ReviewError as error:
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
