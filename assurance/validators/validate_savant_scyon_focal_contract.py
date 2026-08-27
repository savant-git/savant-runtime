#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_CONTRACT = Path(
    "/root/savant-runtime/canon/structure/"
    "SAVANT_SCYON_FOCAL_CONTRACT_v1.0.0.json"
)

EXPECTED_TIERS = [
    "trait",
    "quirk",
    "prodigal",
    "exile",
    "innate",
    "portal",
    "obelisk",
]

EXPECTED_ATOMIC_EXCLUSIONS = [
    "iota",
    "mote",
]

EXPECTED_DIMENSIONS = {
    "identity",
    "state",
    "situated_depth",
}

EXPECTED_EQUALIZER_CHANNELS = {
    "adaptivity",
    "automation",
    "authority_strictness",
    "causal_depth",
    "composition_depth",
    "confidence_threshold",
    "exploration",
    "metadata_influence",
    "projection_detail",
    "simulation_breadth",
    "temporal_depth",
    "validation_rigor",
}

EXPECTED_AUTOMATION_CLASSES = {
    "deterministic",
    "observational",
    "governed_operational",
    "authority_changing",
}


class ValidationError(Exception):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def require_dict(
    value: Any,
    name: str,
) -> dict[str, Any]:
    require(
        isinstance(value, dict),
        f"{name} must be an object",
    )

    return value


def require_list(
    value: Any,
    name: str,
) -> list[Any]:
    require(
        isinstance(value, list),
        f"{name} must be an array",
    )

    return value


def require_true(
    value: Any,
    name: str,
) -> None:
    require(
        value is True,
        f"{name} must be true",
    )


def require_false(
    value: Any,
    name: str,
) -> None:
    require(
        value is False,
        f"{name} must be false",
    )


def validate_identity_tiers(
    contract: dict[str, Any],
) -> None:
    tiers = require_dict(
        contract.get("identity_tiers"),
        "identity_tiers",
    )

    exclusions = require_list(
        tiers.get("atomic_exclusions"),
        "identity_tiers.atomic_exclusions",
    )

    scyon_bearing = require_list(
        tiers.get("scyon_bearing"),
        "identity_tiers.scyon_bearing",
    )

    require(
        exclusions == EXPECTED_ATOMIC_EXCLUSIONS,
        "atomic exclusions must be exactly iota, mote",
    )

    require(
        scyon_bearing == EXPECTED_TIERS,
        "Scyon-bearing tiers are incorrect",
    )

    rank = require_dict(
        tiers.get("complexity_rank"),
        "identity_tiers.complexity_rank",
    )

    require(
        list(rank.keys()) == EXPECTED_TIERS,
        "complexity rank keys must follow canonical tier order",
    )

    require(
        list(rank.values()) == list(range(1, 8)),
        "complexity ranks must be exactly 1 through 7",
    )


def validate_kernel(
    contract: dict[str, Any],
) -> None:
    kernel = require_dict(
        contract.get("kernel_law"),
        "kernel_law",
    )

    require_true(
        kernel.get("single_shared_kernel"),
        "kernel_law.single_shared_kernel",
    )

    require_true(
        kernel.get("canonical_substance_exists_once"),
        "kernel_law.canonical_substance_exists_once",
    )

    require_true(
        kernel.get("higher_tiers_reference_lower_tiers"),
        "kernel_law.higher_tiers_reference_lower_tiers",
    )

    require_true(
        kernel.get(
            "higher_tiers_must_not_absorb_lower_tier_authority"
        ),
        (
            "kernel_law."
            "higher_tiers_must_not_absorb_lower_tier_authority"
        ),
    )

    require_false(
        kernel.get(
            "independent_reimplementation_for_specialization"
        ),
        (
            "kernel_law."
            "independent_reimplementation_for_specialization"
        ),
    )

    require_false(
        kernel.get("focal_replaces_kernel"),
        "kernel_law.focal_replaces_kernel",
    )


def validate_dimensions(
    contract: dict[str, Any],
) -> None:
    dimensions = require_dict(
        contract.get("dimensions"),
        "dimensions",
    )

    require(
        set(dimensions.keys()) == EXPECTED_DIMENSIONS,
        "dimensions must be exactly identity, state, situated_depth",
    )

    situated = require_dict(
        dimensions.get("situated_depth"),
        "dimensions.situated_depth",
    )

    require_true(
        situated.get("native_operational_dimension"),
        "dimensions.situated_depth.native_operational_dimension",
    )

    coordinates = require_list(
        situated.get("coordinates"),
        "dimensions.situated_depth.coordinates",
    )

    require(
        len(coordinates) >= 12,
        "situated depth must expose substantial coordinate depth",
    )


def validate_focal(
    contract: dict[str, Any],
) -> None:
    focal = require_dict(
        contract.get("focal_contract"),
        "focal_contract",
    )

    require(
        focal.get("maximum_primary_focals_per_scyon") == 1,
        "one primary Focal maximum is required",
    )

    prohibited = set(
        require_list(
            focal.get("must_not"),
            "focal_contract.must_not",
        )
    )

    required_prohibitions = {
        "replace_kernel",
        "duplicate_kernel_substance",
        "create_independent_authority",
        "bypass_tier_limits",
        "bypass_authority",
        "erase_history",
        "erase_provenance",
        "mutate_other_scyons_directly",
        "absorb_constituent_scyons",
    }

    require(
        required_prohibitions.issubset(prohibited),
        "Focal prohibitions are incomplete",
    )


def validate_metadata(
    contract: dict[str, Any],
) -> None:
    metadata = require_dict(
        contract.get("metadata_contract"),
        "metadata_contract",
    )

    require_true(
        metadata.get("arbitrary_structured_metadata"),
        "metadata_contract.arbitrary_structured_metadata",
    )

    require_false(
        metadata.get("metadata_is_authority_by_default"),
        "metadata_contract.metadata_is_authority_by_default",
    )

    required_fields = set(
        require_list(
            metadata.get("required_fields"),
            "metadata_contract.required_fields",
        )
    )

    require(
        {
            "namespace",
            "key",
            "value",
            "value_type",
            "authority_state",
            "recorded_at",
            "provenance",
        }.issubset(required_fields),
        "metadata required fields are incomplete",
    )


def validate_equalizer(
    contract: dict[str, Any],
) -> None:
    equalizer = require_dict(
        contract.get("equalizer_contract"),
        "equalizer_contract",
    )

    value_range = require_dict(
        equalizer.get("range"),
        "equalizer_contract.range",
    )

    require(
        value_range.get("minimum") == 0.0,
        "equalizer minimum must be 0.0",
    )

    require(
        value_range.get("maximum") == 1.0,
        "equalizer maximum must be 1.0",
    )

    channels = set(
        require_list(
            equalizer.get("standard_channels"),
            "equalizer_contract.standard_channels",
        )
    )

    require(
        channels == EXPECTED_EQUALIZER_CHANNELS,
        "standard equalizer channels are incorrect",
    )

    require_true(
        equalizer.get("tier_ceiling_enforced"),
        "equalizer_contract.tier_ceiling_enforced",
    )


def validate_abilities(
    contract: dict[str, Any],
) -> None:
    ability = require_dict(
        contract.get("ability_contract"),
        "ability_contract",
    )

    for key in (
        "modular",
        "independently_registered",
        "tier_qualified",
        "focal_qualified",
        "authority_qualified",
        "metadata_conditionable",
        "resource_qualified",
        "dependency_qualified",
    ):
        require_true(
            ability.get(key),
            f"ability_contract.{key}",
        )

    catalog = require_list(
        ability.get("catalog"),
        "ability_contract.catalog",
    )

    require(
        len(catalog) >= 25,
        "ability catalog must contain at least 25 abilities",
    )

    require(
        len(catalog) == len(set(catalog)),
        "ability catalog contains duplicates",
    )


def validate_temporal(
    contract: dict[str, Any],
) -> None:
    temporal = require_dict(
        contract.get("temporal_contract"),
        "temporal_contract",
    )

    require(
        temporal.get("required_axes")
        == [
            "valid_time",
            "transaction_time",
        ],
        "required temporal axes are incorrect",
    )

    require_true(
        temporal.get("historical_state_reconstructable"),
        "temporal_contract.historical_state_reconstructable",
    )

    require_false(
        temporal.get("later_knowledge_rewrites_prior_knowledge"),
        (
            "temporal_contract."
            "later_knowledge_rewrites_prior_knowledge"
        ),
    )


def validate_events(
    contract: dict[str, Any],
) -> None:
    events = require_dict(
        contract.get("event_contract"),
        "event_contract",
    )

    require_true(
        events.get("append_only_by_default"),
        "event_contract.append_only_by_default",
    )

    require_true(
        events.get("immutable_authoritative_history"),
        "event_contract.immutable_authoritative_history",
    )

    require_true(
        events.get("hash_chain_supported"),
        "event_contract.hash_chain_supported",
    )

    require_true(
        events.get("replay_supported"),
        "event_contract.replay_supported",
    )


def validate_automation(
    contract: dict[str, Any],
) -> None:
    automation = require_dict(
        contract.get("automation_classes"),
        "automation_classes",
    )

    require(
        set(automation.keys()) == EXPECTED_AUTOMATION_CLASSES,
        "automation classes are incorrect",
    )

    authority_changing = require_dict(
        automation.get("authority_changing"),
        "automation_classes.authority_changing",
    )

    require_false(
        authority_changing.get("silent_automation"),
        (
            "automation_classes."
            "authority_changing.silent_automation"
        ),
    )

    require_true(
        authority_changing.get("requires_accepted_authority"),
        (
            "automation_classes."
            "authority_changing.requires_accepted_authority"
        ),
    )


def validate_simulation(
    contract: dict[str, Any],
) -> None:
    simulation = require_dict(
        contract.get("simulation_contract"),
        "simulation_contract",
    )

    require_true(
        simulation.get("branch_safe"),
        "simulation_contract.branch_safe",
    )

    require_false(
        simulation.get("branches_are_authority"),
        "simulation_contract.branches_are_authority",
    )

    require_true(
        simulation.get("baseline_preserved"),
        "simulation_contract.baseline_preserved",
    )

    require_true(
        simulation.get("promotion_requires_authority"),
        "simulation_contract.promotion_requires_authority",
    )


def validate_projection(
    contract: dict[str, Any],
) -> None:
    projection = require_dict(
        contract.get("projection_contract"),
        "projection_contract",
    )

    require_true(
        projection.get("derived"),
        "projection_contract.derived",
    )

    require_false(
        projection.get("authoritative"),
        "projection_contract.authoritative",
    )

    require_true(
        projection.get("traceable_to_sources"),
        "projection_contract.traceable_to_sources",
    )


def validate_tier_profiles(
    contract: dict[str, Any],
) -> None:
    profiles = require_dict(
        contract.get("tier_profiles"),
        "tier_profiles",
    )

    require(
        list(profiles.keys()) == EXPECTED_TIERS,
        "tier profile order or membership is incorrect",
    )

    portal = require_dict(
        profiles.get("portal"),
        "tier_profiles.portal",
    )

    require_false(
        portal.get("markdown_operational_dependency"),
        "tier_profiles.portal.markdown_operational_dependency",
    )


def validate_runtime_shards(
    contract: dict[str, Any],
) -> None:
    shards = require_dict(
        contract.get("runtime_shard_contract"),
        "runtime_shard_contract",
    )

    require(
        shards.get("semantics_status") == "deferred",
        "runtime shard semantics must remain deferred",
    )

    require_true(
        shards.get("canonical_instances_remain_authority"),
        (
            "runtime_shard_contract."
            "canonical_instances_remain_authority"
        ),
    )

    require_true(
        shards.get("shards_are_projections"),
        "runtime_shard_contract.shards_are_projections",
    )


def validate_mutation_boundary(
    contract: dict[str, Any],
) -> None:
    require_false(
        contract.get("mutation_authorized"),
        "mutation_authorized",
    )

    require_false(
        contract.get("physical_migration_authorized"),
        "physical_migration_authorized",
    )

    compatibility = require_dict(
        contract.get("compatibility_contract"),
        "compatibility_contract",
    )

    require_false(
        compatibility.get("blind_global_rename"),
        "compatibility_contract.blind_global_rename",
    )

    require_true(
        compatibility.get("extension_before_replacement"),
        "compatibility_contract.extension_before_replacement",
    )

    require_true(
        compatibility.get("migration_requires_inventory"),
        "compatibility_contract.migration_requires_inventory",
    )


def validate_invariants(
    contract: dict[str, Any],
) -> None:
    invariants = require_list(
        contract.get("invariants"),
        "invariants",
    )

    require(
        len(invariants) == len(set(invariants)),
        "invariants contain duplicates",
    )

    required = {
        "scyon_kernel_is_shared",
        "focal_is_specialization_not_replacement",
        "iota_and_mote_do_not_own_scyons",
        "tier_capacity_is_enforced",
        "metadata_is_not_automatically_authority",
        "equalizer_cannot_bypass_tier_capacity",
        "equalizer_cannot_bypass_authority",
        "simulation_branches_are_non_authoritative",
        "projections_are_non_authoritative",
        "history_is_preserved",
        "lineage_is_preserved",
        "provenance_is_preserved",
        "dependencies_are_traceable",
        "dependents_are_traceable",
        "physical_migration_is_not_authorized",
    }

    require(
        required.issubset(set(invariants)),
        "required Scyon/Focal invariants are incomplete",
    )


def validate(
    contract: dict[str, Any],
) -> None:
    require(
        contract.get("contract_id")
        == "savant.scyon-focal.contract",
        "invalid contract_id",
    )

    require(
        contract.get("version") == "1.0.0",
        "invalid contract version",
    )

    validate_identity_tiers(contract)
    validate_kernel(contract)
    validate_dimensions(contract)
    validate_focal(contract)
    validate_metadata(contract)
    validate_equalizer(contract)
    validate_abilities(contract)
    validate_temporal(contract)
    validate_events(contract)
    validate_automation(contract)
    validate_simulation(contract)
    validate_projection(contract)
    validate_tier_profiles(contract)
    validate_runtime_shards(contract)
    validate_mutation_boundary(contract)
    validate_invariants(contract)


def main() -> int:
    path = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else DEFAULT_CONTRACT
    )

    if not path.is_absolute():
        print(
            "ERROR: contract path must be absolute",
            file=sys.stderr,
        )
        return 1

    if not path.is_file():
        print(
            f"ERROR: contract not found: {path}",
            file=sys.stderr,
        )
        return 1

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            contract = json.load(handle)

        require_dict(
            contract,
            "contract",
        )

        validate(contract)

    except (
        json.JSONDecodeError,
        OSError,
        ValidationError,
    ) as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"CONTRACT: {path}")
    print("SCYON KERNEL: validated")
    print("FOCAL CONTRACT: validated")
    print("IDENTITY TIERS: 7 Scyon-bearing")
    print("ATOMIC EXCLUSIONS: iota, mote")
    print("DIMENSIONS: 3")
    print("METADATA: arbitrary structured")
    print("ABILITY MODULES: validated")
    print("EQUALIZER CHANNELS: 12")
    print("BITEMPORAL MODEL: validated")
    print("EVENT HISTORY: validated")
    print("AUTOMATION CLASSES: 4")
    print("SIMULATION SAFETY: validated")
    print("PROJECTION NON-AUTHORITY: validated")
    print("RUNTIME SHARD SEMANTICS: deferred")
    print("MUTATION AUTHORIZED: false")
    print("PHYSICAL MIGRATION AUTHORIZED: false")
    print("SAVANT SCYON/FOCAL CONTRACT: validated")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
