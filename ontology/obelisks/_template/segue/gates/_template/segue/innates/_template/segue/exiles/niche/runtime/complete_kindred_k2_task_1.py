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
    "k2:task-1"
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
        "kindred_engine.py"
    ),
]

receipts = [
    (
        "brother and sister are specific canonical "
        "Kindred role projections rather than a "
        "generic sibling identity"
    ),
    (
        "full brother full sister half brother and "
        "half sister are symmetrical sex-specific "
        "qualified projections"
    ),
    (
        "half qualification requires exactly one "
        "shared qualifying immediate ascendant"
    ),
    (
        "full qualification requires complete "
        "evidence that qualifying immediate "
        "ascendant sets are equal"
    ),
    (
        "incomplete evidence cannot silently promote "
        "a relationship to full qualification"
    ),
    (
        "full-half derivation emits a deterministic "
        "non-authoritative derivation certificate"
    ),
    (
        "derivation certificates expose exact shared "
        "ascendant provenance"
    ),
    (
        "derived lateral roles do not duplicate "
        "authoritative lineage Segues"
    ),
    (
        "existing Kindred engine lineage authority "
        "and deterministic inverse projections are "
        "preserved"
    ),
]

enhancements = [
    "full_lateral_qualification",
    "half_lateral_qualification",
    "evidence_gated_full_qualification",
    "unresolved_incomplete_full_evidence",
    "lateral_derivation_certificates",
    "shared_ascendant_provenance",
    "symmetric_sex_specific_lateral_roles",
    "deterministic_lateral_projection",
    "immutable_lateral_derivation",
    "no_duplicate_lateral_authority",
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
                "Kindred now derives brother and "
                "sister roles with evidence-gated "
                "full and half qualification while "
                "preserving direct Segue authority "
                "and refusing unsupported full "
                "qualification."
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
