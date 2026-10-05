#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


runtime = Path(
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/segue/"
    "exiles/niche/runtime"
)

sys.path.insert(
    0,
    str(runtime),
)

from task_engine import engine


task_id = (
    "completion:kindred-reconciliation:"
    "k1:task-3"
)

terminal_states = {
    "completed",
    "rejected",
    "superseded",
}

implementation_references = [
    (
        "/root/savant-runtime/canon/foundation/"
        "008_FUNCTIONAL_LINEAGE_CANON.md"
    ),
    (
        "/root/savant-runtime/runtime/lineage/"
        "model.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "role_calculus.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "adoption_step_guardian.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "alliance_affinity.py"
    ),
]

receipts = [
    (
        "Kindred canonical family roles are now "
        "specific and sex-qualified rather than "
        "generic family nouns"
    ),
    (
        "female and male role projections are "
        "symmetrical across ascent descent lateral "
        "collateral affinity alliance and guardianship"
    ),
    (
        "cousin terminology is explicitly projected "
        "as female cousin or male cousin"
    ),
    (
        "cousin degree and removal are deterministic "
        "and unbounded"
    ),
    (
        "adoption profiles distinguish adoptive mother "
        "adoptive father adoptive daughter and "
        "adoptive son"
    ),
    (
        "step profiles distinguish stepmother "
        "stepfather stepdaughter and stepson"
    ),
    (
        "guardianship distinguishes female guardian "
        "male guardian female ward and male ward"
    ),
    (
        "foster and legal qualifications remain "
        "separate from descent semantics"
    ),
    (
        "neutral geometry remains computational while "
        "generic family-role identities are not "
        "canonical"
    ),
    (
        "derived roles do not create a second "
        "relationship authority graph"
    ),
    (
        "role profiles are immutable deterministic "
        "reusable instances"
    ),
    (
        "great-generation terminology is generated "
        "without a fixed depth ceiling"
    ),
    (
        "relationship qualification composes without "
        "duplicating underlying authoritative Segues"
    ),
    (
        "at least twenty advanced Kindred enhancements "
        "are represented by the role calculus"
    ),
]

implementation_enhancements = [
    "specific_gendered_canonical_roles",
    "symmetric_reciprocal_roles",
    "neutral_internal_geometry",
    "direct_edge_first_semantics",
    "deterministic_role_projection",
    "stable_role_identity",
    "unbounded_ancestral_depth",
    "unbounded_descendant_depth",
    "unbounded_cousin_degree",
    "unbounded_cousin_removal",
    "female_cousin_projection",
    "male_cousin_projection",
    "full_lateral_qualification",
    "half_lateral_qualification",
    "adoptive_role_qualification",
    "step_role_qualification",
    "foster_role_qualification",
    "legal_role_qualification",
    "gender_specific_guardianship",
    "gender_specific_affinity",
    "gender_specific_alliance",
    "temporal_alliance_compatibility",
    "inverse_role_projection",
    "multi_generation_role_projection",
    "great_generation_projection",
    "qualification_composition",
    "immutable_role_profiles",
    "cached_deterministic_projection",
    "bounded_validation",
    "relationship_axis_separation",
    "descent_affinity_separation",
    "guardianship_descent_separation",
    "no_duplicate_relationship_authority",
    "no_derived_relationship_storage_requirement",
    "policy_ready_role_profiles",
    "provenance_ready_role_identity",
]


def main() -> int:
    task_engine = engine()

    current = task_engine.public_task(
        task_id
    )

    if current["status"] not in terminal_states:
        task_engine.amend(
            task_id,
            {
                "implementation_references":
                    implementation_references,
            },
        )

        current = task_engine.transition(
            task_id,
            "completed",
            receipts=receipts,
            reason=(
                "Adoption step and guardian profiles "
                "are normalized into a symmetric "
                "specific-role Kindred calculus. "
                "Canonical human-facing roles now use "
                "sex-specific family terminology while "
                "neutral geometry remains beneath the "
                "projection layer. Derived roles remain "
                "non-authoritative projections over "
                "existing Segue authority."
            ),
        )

    dashboard = task_engine.dashboard()

    ready = dashboard.get(
        "ready_queue",
        [],
    )

    print(
        json.dumps(
            {
                "task": current,
                "enhancements":
                    implementation_enhancements,
                "enhancement_count":
                    len(
                        implementation_enhancements
                    ),
                "next": (
                    ready[0]
                    if ready
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
