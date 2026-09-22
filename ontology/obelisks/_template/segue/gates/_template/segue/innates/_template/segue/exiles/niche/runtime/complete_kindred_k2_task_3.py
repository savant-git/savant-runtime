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
    "k2:task-3"
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
        "generational_calculus.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "collateral_calculus.py"
    ),
]

receipts = [
    (
        "Kindred derives specific aunt uncle niece "
        "and nephew roles without a generic canonical "
        "family-role identity"
    ),
    (
        "female and male collateral roles are "
        "symmetrical reciprocal projections"
    ),
    (
        "aunt and uncle derivation composes an "
        "existing qualified lateral relationship "
        "with authoritative descent evidence"
    ),
    (
        "niece and nephew are deterministic inverse "
        "projections of the same derivation"
    ),
    (
        "full half adoptive and step qualification "
        "can be preserved from the qualifying "
        "collateral relationship"
    ),
    (
        "great aunt great uncle great niece and "
        "great nephew roles generalize without "
        "a fixed generation ceiling"
    ),
    (
        "collateral and descent evidence identifiers "
        "remain exposed in the derivation certificate"
    ),
    (
        "derived collateral relationships remain "
        "non-authoritative projections"
    ),
    (
        "no derived collateral relationship is "
        "stored as duplicate lineage authority"
    ),
]

enhancements = [
    "aunt_projection",
    "uncle_projection",
    "niece_projection",
    "nephew_projection",
    "sex_specific_collateral_roles",
    "symmetric_inverse_collateral_roles",
    "great_aunt_projection",
    "great_uncle_projection",
    "great_niece_projection",
    "great_nephew_projection",
    "unbounded_collateral_generation_depth",
    "full_collateral_qualification",
    "half_collateral_qualification",
    "adoptive_collateral_qualification",
    "step_collateral_qualification",
    "collateral_evidence_certificate",
    "descent_evidence_certificate",
    "combined_evidence_provenance",
    "immutable_collateral_derivation",
    "non_authoritative_collateral_projection",
    "no_duplicate_collateral_authority",
    "explicit_generation_distance",
    "evidence_completeness_tracking",
    "specific_role_only_projection",
    "qualification_preservation",
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
                "Kindred now derives symmetrical "
                "aunt uncle niece and nephew roles "
                "from qualified lateral geometry plus "
                "authoritative descent evidence, with "
                "unbounded great-generation depth and "
                "exact derivation provenance."
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
                "enhancements": enhancements,
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
