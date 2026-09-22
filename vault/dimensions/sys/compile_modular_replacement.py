#!/usr/bin/env python3
"""
Compile complete replacement artifacts from the latest modular semantic review.

This stage does not mutate implementation or authority.

It reads the current verified target, applies only registered deterministic
transformations, writes the complete proposed replacement into the report
vault, records before and after digests, and preserves the complete baseline.

Unsupported, ambiguous, stale, non-JSON, or semantically blocked targets remain
blocked.

Supported deterministic transformations:

1. Canonical modular mood migration.
2. Canonical additive attachment-slot normalization.
3. Canonical project-instruction terminology migration.

Every output is a complete replacement file. No append fragments are produced.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
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

REVIEW_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-review"
)

REPLACEMENT_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-replacement"
)

LATEST_REVIEW: Final[Path] = (
    REVIEW_ROOT
    / "latest.json"
)

MOODS_REGISTRY: Final[Path] = (
    ROOT
    / "authority_graph"
    / "registries"
    / "modular_moods.json"
)

SLOTS_REGISTRY: Final[Path] = (
    ROOT
    / "authority_graph"
    / "registries"
    / "attachment_slots.json"
)

PROJECT_INSTRUCTIONS: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "canon"
    / "PROJECT_INSTRUCTIONS.md"
)

CANONICAL_MOODS: Final[tuple[str, ...]] = (
    "anima",
    "weld",
    "kiln",
    "graft",
    "aria",
    "mantle",
    "fulcrum",
    "echelon",
    "ascent",
)

HISTORICAL_MOOD_MAP: Final[dict[str, str]] = {
    "instantiation": "anima",
    "composition": "weld",
    "projection": "kiln",
    "attachment": "graft",
    "parameterization": "aria",
    "masking": "mantle",
    "segue": "fulcrum",
    "interlock": "fulcrum",
    "layering": "echelon",
    "emergence": "ascent",
}

CANONICAL_ABILITIES: Final[dict[str, str]] = {
    "anima": "stable_identity",
    "weld": "structural_composition",
    "kiln": "deterministic_manifestation",
    "graft": "reversible_capability_addition",
    "aria": "controlled_variation",
    "mantle": "intelligent_structural_possibility",
    "fulcrum": "governed_operational_leverage",
    "echelon": "ordered_influence",
    "ascent": "higher_order_derivation",
}

CANONICAL_GOVERNS: Final[dict[str, str]] = {
    "anima": "identity, addressability, lifecycle, lineage, and provenance",
    "weld": "constituent-preserving structural composition",
    "kiln": "disposable deterministic manifestation from authority",
    "graft": "independent reversible capability addition",
    "aria": "bounded variation without authority replacement",
    "mantle": "typed structure, constraints, slots, and conditional possibility",
    "fulcrum": "mediated influence through explicit relationships",
    "echelon": "precedence, inheritance, stacking, override, and fallthrough",
    "ascent": "reproducible higher-order behavior from lower interactions",
}

REPLACEMENT_STATES: Final[tuple[str, ...]] = (
    "compiled",
    "blocked",
    "ready",
)

TRANSFORMATION_KEYS: Final[tuple[str, ...]] = (
    "canonical_moods",
    "additive_slots",
    "project_instructions",
)

VALIDATION_AXES: Final[tuple[str, ...]] = (
    "syntax",
    "schema",
    "authority",
    "identity",
    "lineage",
    "provenance",
    "dependencies",
    "replay",
    "rollback",
)


class ReplacementError(RuntimeError):
    """Raised when replacement compilation cannot proceed safely."""


@dataclass(frozen=True, slots=True)
class ReplacementUnit:
    id: str
    review_id: str
    decision_id: str
    candidate_id: str
    candidate_ordinal: int
    source_finding_key: str
    target_path: str | None
    transformation: str | None
    state: str
    before_digest: str | None
    after_digest: str | None
    baseline_path: str | None
    replacement_path: str | None
    changed: bool
    mutation_performed: bool
    implementation_authorized: bool
    semantic_review_complete: bool
    validation_axes: tuple[str, ...]
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
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def atomic_write_bytes(
    path: Path,
    value: bytes,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.tmp"
    )

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
        raise ReplacementError(
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
        raise ReplacementError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise ReplacementError(
            f"JSON root must be an object: {path}"
        )

    return value


def resolve_reviews_path() -> Path:
    latest = load_json(
        LATEST_REVIEW
    )

    raw_path = latest.get(
        "reviews"
    )

    if not isinstance(raw_path, str):
        raise ReplacementError(
            "latest review packet lacks reviews path"
        )

    path = Path(raw_path)

    if not path.is_file():
        raise ReplacementError(
            f"semantic reviews file missing: {path}"
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
        resolved = path.resolve(
            strict=False
        )
        resolved.relative_to(
            ROOT.resolve()
        )
    except (
        OSError,
        ValueError,
    ):
        return None

    return resolved


def replacement_identity(
    review_id: str,
    target_path: str | None,
    transformation: str | None,
) -> str:
    payload = "\x1f".join(
        (
            review_id,
            target_path or "",
            transformation or "",
        )
    )

    return (
        "replacement-unit:"
        + sha256_text(payload)[:24]
    )


def select_transformation(
    target: Path | None,
    finding_key: str,
) -> str | None:
    if target is None:
        return None

    if target == MOODS_REGISTRY:
        return "canonical_moods"

    if target == SLOTS_REGISTRY:
        return "additive_slots"

    if target == PROJECT_INSTRUCTIONS:
        return "project_instructions"

    if (
        "mood" in finding_key.casefold()
        and target.suffix.casefold() == ".json"
    ):
        return "canonical_moods"

    if (
        "slot" in finding_key.casefold()
        and target.suffix.casefold() == ".json"
    ):
        return "additive_slots"

    return None


def canonical_pair(
    first: str,
    second: str,
) -> tuple[str, str]:
    first_index = CANONICAL_MOODS.index(
        first
    )

    second_index = CANONICAL_MOODS.index(
        second
    )

    if first_index < second_index:
        return first, second

    return second, first


def map_mood_key(value: object) -> object:
    if not isinstance(value, str):
        return value

    normalized = value.casefold()

    return HISTORICAL_MOOD_MAP.get(
        normalized,
        normalized,
    )


def migrate_mood_list(
    value: object,
) -> object:
    if not isinstance(value, list):
        return value

    migrated = [
        map_mood_key(item)
        for item in value
    ]

    return migrated


def migrate_mood_registry(
    source: dict[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(source)

    result["id"] = result.get(
        "id",
        "registry:modular_moods",
    )

    result["kind"] = result.get(
        "kind",
        "registry",
    )

    result["version"] = "3.0.0"
    result["status"] = "accepted"

    authority = result.get(
        "authority"
    )

    if not isinstance(authority, dict):
        authority = {}

    authority["state"] = "accepted"
    authority["source"] = (
        "current_user_directive"
    )

    result["authority"] = authority

    result["terminology"] = {
        "canonical_singular": "modular mood",
        "canonical_plural": "modular moods",
        "compact": "mood",
        "historical_terms": [
            "modular method",
            "modular methods",
            "method",
        ],
    }

    result["cardinality"] = {
        "moods": 9,
        "distinct_pair_fusions": 36,
        "maximum_moods_per_fusion": 2,
    }

    result["fusion_policy"] = {
        "commutative": True,
        "directional": False,
        "self_fusion_allowed": False,
        "three_mood_fusion_allowed": False,
        "fusion_creates_new_ability": True,
        "fusion_creates_new_mood": False,
        "fusion_creates_authority": False,
    }

    result["moods"] = [
        {
            "ordinal": ordinal,
            "key": mood,
            "ability": CANONICAL_ABILITIES[
                mood
            ],
            "governs": CANONICAL_GOVERNS[
                mood
            ],
        }
        for ordinal, mood in enumerate(
            CANONICAL_MOODS,
            start=1,
        )
    ]

    existing_fusions = result.get(
        "fusions"
    )

    migrated_fusions: list[
        dict[str, Any]
    ] = []

    fusion_by_pair: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}

    if isinstance(
        existing_fusions,
        list,
    ):
        for fusion in existing_fusions:
            if not isinstance(
                fusion,
                dict,
            ):
                continue

            raw_moods = fusion.get(
                "moods"
            )

            if not isinstance(
                raw_moods,
                list,
            ):
                continue

            if len(raw_moods) != 2:
                continue

            first = map_mood_key(
                raw_moods[0]
            )

            second = map_mood_key(
                raw_moods[1]
            )

            if not isinstance(
                first,
                str,
            ):
                continue

            if not isinstance(
                second,
                str,
            ):
                continue

            if first not in CANONICAL_MOODS:
                continue

            if second not in CANONICAL_MOODS:
                continue

            if first == second:
                continue

            pair = canonical_pair(
                first,
                second,
            )

            migrated = copy.deepcopy(
                fusion
            )

            migrated["moods"] = list(
                pair
            )

            migrated["id"] = (
                f"fusion:{pair[0]}:{pair[1]}"
            )

            fusion_by_pair.setdefault(
                pair,
                migrated,
            )

    ordinal = 0

    for first_index, first in enumerate(
        CANONICAL_MOODS
    ):
        for second in CANONICAL_MOODS[
            first_index + 1:
        ]:
            ordinal += 1

            pair = (
                first,
                second,
            )

            fusion = fusion_by_pair.get(
                pair
            )

            if fusion is None:
                fusion = {
                    "id": (
                        f"fusion:{first}:{second}"
                    ),
                    "moods": [
                        first,
                        second,
                    ],
                    "name": None,
                    "ability": None,
                    "status": (
                        "definition_required"
                    ),
                    "authority": (
                        "unaccepted"
                    ),
                }

            fusion["ordinal"] = ordinal

            migrated_fusions.append(
                fusion
            )

    result["fusions"] = (
        migrated_fusions
    )

    result["validation"] = {
        "required_mood_count": 9,
        "required_fusion_count": 36,
        "unordered_pairs_required": True,
        "directional_duplicates_forbidden": True,
        "self_fusions_forbidden": True,
        "three_mood_fusions_forbidden": True,
        "unique_fusion_names_required": True,
        "unique_fusion_abilities_required": True,
        "lineage_required": True,
        "provenance_required": True,
        "replay_required": True,
    }

    return result


def migrate_slot_registry(
    source: dict[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(source)

    result["id"] = result.get(
        "id",
        "registry:attachment_slots",
    )

    result["kind"] = result.get(
        "kind",
        "registry",
    )

    result["version"] = "3.0.0"
    result["status"] = "accepted"

    authority = result.get(
        "authority"
    )

    if not isinstance(authority, dict):
        authority = {}

    authority["state"] = "accepted"
    authority["source"] = (
        "current_user_directive"
    )

    result["authority"] = authority

    result["primitive"] = {
        "key": "slot",
        "type": (
            "structural_attachment_locus"
        ),
        "definition": (
            "A governed location that adds an "
            "independently attributable capability "
            "without fusion."
        ),
    }

    result["semantics"] = {
        "additive": True,
        "fusion": False,
        "maximum_concurrent_primary_slots": 4,
        "occupant_identity_preserved": True,
        "occupant_authority_preserved": True,
        "occupant_removability_preserved": True,
        "new_mood_created": False,
        "new_fusion_ability_created": False,
    }

    result["result_formula"] = {
        "expression": (
            "host + capability_1 + capability_2 "
            "+ capability_3 + capability_4"
        ),
        "interaction": "typed_segues",
        "independent_attribution_required": True,
        "independent_removal_required": True,
    }

    result["capacity"] = {
        "minimum_non_atomic": 1,
        "maximum_non_atomic": 4,
        "atomic_default": 0,
        "derivation": "extension_pressure",
    }

    result["extension_pressure"] = {
        "factor_count": 9,
        "factor_score_minimum": 0,
        "factor_score_maximum": 4,
        "raw_minimum": 0,
        "raw_maximum": 36,
        "factors": [
            {
                "ordinal": 1,
                "key": "reuse_range",
            },
            {
                "ordinal": 2,
                "key": "consumer_diversity",
            },
            {
                "ordinal": 3,
                "key": "dependency_centrality",
            },
            {
                "ordinal": 4,
                "key": (
                    "expected_capability_growth"
                ),
            },
            {
                "ordinal": 5,
                "key": "governance_complexity",
            },
            {
                "ordinal": 6,
                "key": "integration_diversity",
            },
            {
                "ordinal": 7,
                "key": "output_diversity",
            },
            {
                "ordinal": 8,
                "key": "longevity",
            },
            {
                "ordinal": 9,
                "key": (
                    "compatibility_responsibility"
                ),
            },
        ],
        "bands": [
            {
                "slot_count": 1,
                "minimum": 0,
                "maximum": 9,
                "role": "focused_endpoint",
            },
            {
                "slot_count": 2,
                "minimum": 10,
                "maximum": 18,
                "role": "reusable_specialist",
            },
            {
                "slot_count": 3,
                "minimum": 19,
                "maximum": 27,
                "role": "extensible_composite",
            },
            {
                "slot_count": 4,
                "minimum": 28,
                "maximum": 36,
                "role": "infrastructural_hub",
            },
        ],
    }

    result["primary_roles"] = [
        {
            "ordinal": 1,
            "key": "capability",
            "definition": (
                "Adds independent operational capability."
            ),
        },
        {
            "ordinal": 2,
            "key": "governance",
            "definition": (
                "Adds policies, permissions, constraints, "
                "criteria, or lifecycle control."
            ),
        },
        {
            "ordinal": 3,
            "key": "mediation",
            "definition": (
                "Adds Segues, adapters, translators, "
                "routers, observers, synchronization, "
                "conflict handling, or recovery."
            ),
        },
        {
            "ordinal": 4,
            "key": "manifestation",
            "definition": (
                "Adds Kilns, renderers, exporters, "
                "serializers, reports, interfaces, or "
                "target adapters."
            ),
        },
    ]

    result["occupancy_modes"] = [
        {
            "ordinal": 1,
            "key": "singular",
            "definition": (
                "Zero or one independent occupant."
            ),
        },
        {
            "ordinal": 2,
            "key": "ordered",
            "definition": (
                "Zero or more independent occupants "
                "resolved by explicit precedence."
            ),
        },
        {
            "ordinal": 3,
            "key": "collective",
            "definition": (
                "Zero or more independent occupants "
                "coordinated through typed Segues "
                "without capability fusion."
            ),
        },
    ]

    result["prohibitions"] = [
        "slot_capability_fusion",
        "slot_generated_mood",
        "slot_generated_fusion_ability",
        "occupant_identity_absorption",
        "occupant_authority_transfer",
        "hidden_cross_slot_coupling",
        "untraceable_capability_contribution",
        "irreversible_occupancy",
        "more_than_four_primary_slots",
    ]

    result["validation"] = {
        "additive_semantics_required": True,
        "fusion_forbidden": True,
        "maximum_primary_slots": 4,
        "cross_slot_segues_required": True,
        "authority_transfer_forbidden": True,
        "stable_occupant_identity_required": True,
        "independent_attribution_required": True,
        "independent_removal_required": True,
        "lineage_required": True,
        "provenance_required": True,
        "recovery_path_required": True,
    }

    return result


def migrate_project_instructions(
    source: str,
) -> str:
    replacements = (
        (
            r"\bInstantiation\b",
            "Anima",
        ),
        (
            r"\bComposition\b",
            "Weld",
        ),
        (
            r"\bProjection\b",
            "Kiln",
        ),
        (
            r"\bAttachment\b",
            "Graft",
        ),
        (
            r"\bParameterization\b",
            "Aria",
        ),
        (
            r"\bMasking\b",
            "Mantle",
        ),
        (
            r"\bLayering\b",
            "Echelon",
        ),
        (
            r"\bEmergence\b",
            "Ascent",
        ),
    )

    result = source

    for pattern, replacement in replacements:
        result = re.sub(
            pattern,
            replacement,
            result,
        )

    return result


def compile_transformation(
    target: Path,
    transformation: str,
    source_bytes: bytes,
) -> bytes:
    if transformation == "canonical_moods":
        try:
            source = json.loads(
                source_bytes.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ReplacementError(
                f"mood target is not valid UTF-8 JSON: {target}: {error}"
            ) from error

        if not isinstance(source, dict):
            raise ReplacementError(
                f"mood target root must be an object: {target}"
            )

        return canonical_json_bytes(
            migrate_mood_registry(
                source
            )
        )

    if transformation == "additive_slots":
        try:
            source = json.loads(
                source_bytes.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ReplacementError(
                f"slot target is not valid UTF-8 JSON: {target}: {error}"
            ) from error

        if not isinstance(source, dict):
            raise ReplacementError(
                f"slot target root must be an object: {target}"
            )

        return canonical_json_bytes(
            migrate_slot_registry(
                source
            )
        )

    if transformation == "project_instructions":
        try:
            source_text = source_bytes.decode(
                "utf-8"
            )
        except UnicodeDecodeError as error:
            raise ReplacementError(
                f"instruction target is not UTF-8 text: {target}"
            ) from error

        return migrate_project_instructions(
            source_text
        ).encode("utf-8")

    raise ReplacementError(
        f"unsupported transformation: {transformation}"
    )


def safe_name(
    identifier: str,
    suffix: str,
) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "__",
        identifier,
    )

    return f"{normalized}{suffix}"


def compile_review(
    review: dict[str, Any],
    run_root: Path,
) -> ReplacementUnit:
    review_id = str(
        review.get(
            "id",
            "",
        )
    )

    if not review_id:
        raise ReplacementError(
            "semantic review lacks stable id"
        )

    candidate_ordinal = review.get(
        "candidate_ordinal"
    )

    if not isinstance(
        candidate_ordinal,
        int,
    ):
        raise ReplacementError(
            f"review {review_id} lacks integer candidate ordinal"
        )

    target = normalize_target_path(
        review.get(
            "target_path"
        )
    )

    finding_key = str(
        review.get(
            "source_finding_key",
            "",
        )
    )

    transformation = select_transformation(
        target,
        finding_key,
    )

    blockers: list[str] = []

    if review.get(
        "semantic_review_complete"
    ) is not True:
        blockers.append(
            "semantic review is not complete"
        )

    if target is None:
        blockers.append(
            "target path is unresolved"
        )
    elif not target.is_file():
        blockers.append(
            "target does not exist as a regular file"
        )

    if transformation is None:
        blockers.append(
            "no deterministic transformation is registered"
        )

    before_digest: str | None = None
    after_digest: str | None = None
    baseline_path: str | None = None
    replacement_path: str | None = None
    changed = False

    if not blockers:
        assert target is not None
        assert transformation is not None

        source_bytes = target.read_bytes()

        before_digest = sha256_bytes(
            source_bytes
        )

        replacement_bytes = (
            compile_transformation(
                target,
                transformation,
                source_bytes,
            )
        )

        after_digest = sha256_bytes(
            replacement_bytes
        )

        changed = (
            before_digest != after_digest
        )

        suffix = target.suffix or ".bin"

        baseline = (
            run_root
            / "baselines"
            / safe_name(
                review_id,
                suffix,
            )
        )

        replacement = (
            run_root
            / "replacements"
            / safe_name(
                review_id,
                suffix,
            )
        )

        atomic_write_bytes(
            baseline,
            source_bytes,
        )

        atomic_write_bytes(
            replacement,
            replacement_bytes,
        )

        baseline_path = str(
            baseline
        )

        replacement_path = str(
            replacement
        )

        if sha256_bytes(
            baseline.read_bytes()
        ) != before_digest:
            blockers.append(
                "baseline digest verification failed"
            )

        if sha256_bytes(
            replacement.read_bytes()
        ) != after_digest:
            blockers.append(
                "replacement digest verification failed"
            )

        if not changed:
            blockers.append(
                "replacement produces no content change"
            )

    state = (
        "ready"
        if not blockers
        else "blocked"
    )

    return ReplacementUnit(
        id=replacement_identity(
            review_id,
            str(target)
            if target is not None
            else None,
            transformation,
        ),
        review_id=review_id,
        decision_id=str(
            review.get(
                "decision_id",
                "",
            )
        ),
        candidate_id=str(
            review.get(
                "candidate_id",
                "",
            )
        ),
        candidate_ordinal=(
            candidate_ordinal
        ),
        source_finding_key=(
            finding_key
        ),
        target_path=(
            str(target)
            if target is not None
            else None
        ),
        transformation=(
            transformation
        ),
        state=state,
        before_digest=(
            before_digest
        ),
        after_digest=after_digest,
        baseline_path=baseline_path,
        replacement_path=(
            replacement_path
        ),
        changed=changed,
        mutation_performed=False,
        implementation_authorized=False,
        semantic_review_complete=(
            review.get(
                "semantic_review_complete"
            )
            is True
        ),
        validation_axes=(
            VALIDATION_AXES
        ),
        blockers=tuple(
            dict.fromkeys(
                blockers
            )
        ),
    )


def compile_replacements() -> dict[str, Any]:
    reviews_path = resolve_reviews_path()
    reviews_bytes = reviews_path.read_bytes()

    document = json.loads(
        reviews_bytes.decode("utf-8")
    )

    reviews = document.get(
        "reviews"
    )

    if not isinstance(
        reviews,
        list,
    ):
        raise ReplacementError(
            "semantic reviews must be an array"
        )

    run_timestamp = utc_timestamp()

    run_root = (
        REPLACEMENT_ROOT
        / run_timestamp
    )

    units = tuple(
        compile_review(
            review,
            run_root,
        )
        for review in reviews
        if isinstance(
            review,
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
        raise ReplacementError(
            "replacement unit identifiers are duplicated"
        )

    ordinals = [
        unit.candidate_ordinal
        for unit in units
    ]

    if ordinals != sorted(
        ordinals
    ):
        raise ReplacementError(
            "replacement units are not in candidate order"
        )

    state_counts = Counter(
        unit.state
        for unit in units
    )

    transformation_counts = Counter(
        unit.transformation
        for unit in units
        if unit.transformation
        is not None
    )

    packet_id = (
        "replacement-packet:"
        + sha256_text(
            "\x1f".join(
                (
                    str(
                        reviews_path
                    ),
                    sha256_bytes(
                        reviews_bytes
                    ),
                    run_timestamp,
                )
            )
        )[:24]
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
        REPLACEMENT_ROOT
        / "latest.json"
    )

    report = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-replacement-report/1.0.0"
        ),
        "operation": (
            "compile_modular_replacement"
        ),
        "id": packet_id,
        "timestamp": run_timestamp,
        "passed": (
            state_counts["blocked"] == 0
        ),
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "implementation_authorized": False,
        "source_reviews": str(
            reviews_path
        ),
        "source_reviews_digest": (
            sha256_bytes(
                reviews_bytes
            )
        ),
        "replacement_count": len(
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
        "changed_count": sum(
            unit.changed
            for unit in units
        ),
        "transformation_counts": {
            key: transformation_counts[
                key
            ]
            for key in TRANSFORMATION_KEYS
        },
        "validation_axes": list(
            VALIDATION_AXES
        ),
        "replacement_states": list(
            REPLACEMENT_STATES
        ),
    }

    units_document = {
        "schema": (
            "savant://vault/dimensions/"
            "modular-replacement-units/1.0.0"
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

    atomic_write_json(
        report_path,
        report,
    )

    atomic_write_json(
        units_path,
        units_document,
    )

    manifest_candidates = [
        report_path,
        units_path,
    ]

    for unit in units:
        if unit.baseline_path:
            manifest_candidates.append(
                Path(
                    unit.baseline_path
                )
            )

        if unit.replacement_path:
            manifest_candidates.append(
                Path(
                    unit.replacement_path
                )
            )

    manifest_entries = []

    for path in manifest_candidates:
        if not path.is_file():
            raise ReplacementError(
                f"replacement output missing: {path}"
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
                "modular-replacement-manifest/1.0.0"
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
            "units": str(
                units_path
            ),
            "manifest": str(
                manifest_path
            ),
            "replacement_count": len(
                units
            ),
            "ready_count": state_counts[
                "ready"
            ],
            "blocked_count": state_counts[
                "blocked"
            ],
            "passed": report["passed"],
            "authority_effect": "none",
            "implementation_mutation_performed": False,
            "implementation_authorized": False,
        },
    )

    return {
        "operation": (
            "compile_modular_replacement"
        ),
        "passed": report["passed"],
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "implementation_authorized": False,
        "packet_id": packet_id,
        "replacement_count": len(
            units
        ),
        "ready_count": state_counts[
            "ready"
        ],
        "blocked_count": state_counts[
            "blocked"
        ],
        "latest": str(
            latest_path
        ),
    }


def verify_latest() -> dict[str, Any]:
    latest_path = (
        REPLACEMENT_ROOT
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
        raise ReplacementError(
            "latest replacement packet lacks manifest path"
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
        raise ReplacementError(
            "replacement manifest entries must be an array"
        )

    verified_entries = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            raise ReplacementError(
                "manifest entry must be an object"
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
            raise ReplacementError(
                "manifest entry lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise ReplacementError(
                "manifest entry lacks digest"
            )

        path = Path(raw_path)

        if not path.is_file():
            raise ReplacementError(
                f"manifest file missing: {path}"
            )

        actual_digest = sha256_bytes(
            path.read_bytes()
        )

        if actual_digest != expected_digest:
            raise ReplacementError(
                f"manifest digest mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(path),
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
        raise ReplacementError(
            "latest replacement packet lacks units path"
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
        raise ReplacementError(
            "replacement units must be an array"
        )

    unit_ids: list[str] = []

    for unit in units:
        if not isinstance(
            unit,
            dict,
        ):
            raise ReplacementError(
                "replacement unit must be an object"
            )

        unit_id = unit.get(
            "id"
        )

        if not isinstance(
            unit_id,
            str,
        ):
            raise ReplacementError(
                "replacement unit lacks stable id"
            )

        unit_ids.append(
            unit_id
        )

        if unit.get(
            "mutation_performed"
        ) is not False:
            raise ReplacementError(
                "replacement compilation mutated implementation"
            )

        if unit.get(
            "implementation_authorized"
        ) is not False:
            raise ReplacementError(
                "replacement compilation prematurely authorized implementation"
            )

        state = unit.get(
            "state"
        )

        if state not in REPLACEMENT_STATES:
            raise ReplacementError(
                f"replacement unit has invalid state: {unit_id}"
            )

        axes = unit.get(
            "validation_axes"
        )

        if tuple(
            axes
            if isinstance(
                axes,
                list,
            )
            else ()
        ) != VALIDATION_AXES:
            raise ReplacementError(
                f"replacement validation axes differ from authority: {unit_id}"
            )

    if len(unit_ids) != len(
        set(unit_ids)
    ):
        raise ReplacementError(
            "replacement unit identifiers are duplicated"
        )

    return {
        "operation": (
            "verify_modular_replacement"
        ),
        "passed": True,
        "authority_effect": "none",
        "implementation_mutation_performed": False,
        "implementation_authorized": False,
        "packet_id": latest.get(
            "packet_id"
        ),
        "replacement_count": len(
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
            "Compile or verify complete modular replacement artifacts."
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
            result = compile_replacements()
        else:
            result = verify_latest()

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
            else 2
        )

    except ReplacementError as error:
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "passed": False,
                    "authority_effect": "none",
                    "implementation_mutation_performed": False,
                    "implementation_authorized": False,
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
