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
    "k3:task-1"
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
        "/root/savant-runtime/lexicon/kindred/"
        "role_calculus.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "adoption_step_guardian.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "descent_policy.py"
    ),
]

receipts = [
    (
        "Kindred descent semantics are explicitly "
        "policy scoped rather than inferred from "
        "family-role labels"
    ),
    (
        "biological adoptive foster and legal descent "
        "remain distinct policy semantics"
    ),
    (
        "guardianship is explicitly excluded from "
        "descent semantics"
    ),
    (
        "step relationships are explicitly excluded "
        "from direct descent semantics"
    ),
    (
        "biological descent contribution is not "
        "inferred from adoption foster or legal status"
    ),
    (
        "descent policy decisions require explicit "
        "evidence by default"
    ),
    (
        "lateral generational and cousin derivation "
        "eligibility are independently policy controlled"
    ),
    (
        "foster descent does not automatically create "
        "cousin relationships"
    ),
    (
        "descent policy decisions emit deterministic "
        "non-authoritative certificates"
    ),
    (
        "multiple descent policies can be evaluated "
        "across one composed path without duplicating "
        "underlying relationship authority"
    ),
    (
        "policy identities are deterministic immutable "
        "and authority bound"
    ),
]

enhancements = [
    "policy_scoped_descent_semantics",
    "biological_descent_isolation",
    "adoptive_descent_isolation",
    "foster_descent_isolation",
    "legal_descent_isolation",
    "explicit_evidence_gating",
    "purpose_specific_descent_eligibility",
    "lateral_derivation_policy",
    "generational_derivation_policy",
    "cousin_derivation_policy",
    "qualification_propagation_policy",
    "stable_policy_identity",
    "immutable_policy_instances",
    "deterministic_policy_decisions",
    "policy_decision_certificates",
    "non_authoritative_policy_projection",
    "multi_policy_path_validation",
    "social_descent_projection",
    "legal_descent_projection",
    "biological_descent_projection",
    "foster_cousin_exclusion",
    "authority_bound_policy",
    "provenance_ready_policy",
    "extension_ready_policy",
    "no_descent_semantic_conflation",
    "no_guardianship_descent_conflation",
    "no_step_descent_conflation",
    "no_duplicate_relationship_authority",
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
                "Kindred now applies explicit "
                "policy-scoped descent semantics for "
                "biological adoptive foster and legal "
                "relationships while keeping step and "
                "guardianship outside direct descent "
                "and preserving single Segue authority."
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
                "task":
                    current,
                "enhancements":
                    enhancements,
                "enhancement_count":
                    len(enhancements),
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
