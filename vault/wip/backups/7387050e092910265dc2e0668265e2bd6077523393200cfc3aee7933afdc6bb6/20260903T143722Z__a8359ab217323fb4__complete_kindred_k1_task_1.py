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
    "k1:task-1"
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
        "/root/savant-runtime/authority_graph/policies/"
        "functional_lineage.json"
    ),
    (
        "/root/savant-runtime/authority_graph/schemas/"
        "lineage_segue.schema.json"
    ),
    (
        "/root/savant-runtime/runtime/lineage/"
        "model.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "kindred_registry.yaml"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "kindred.schema.yaml"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "kindred_engine.py"
    ),
]

receipts = [
    (
        "kindred parent-child authority is normalized "
        "to directed lineage segues"
    ),
    (
        "kindred_registry.yaml stores parent-child "
        "relationships as lineage_segues"
    ),
    (
        "kindred records no longer require authoritative "
        "parents or children arrays"
    ),
    (
        "kindred.schema.yaml declares lineage_segue as "
        "the authoritative parent-child primitive"
    ),
    (
        "legacy parents and children fields are explicitly "
        "compatibility projections"
    ),
    (
        "kindred_engine.py builds parent and child indexes "
        "from authoritative lineage segues"
    ),
    (
        "kindred_engine.py projects parents and children "
        "without duplicate inverse storage"
    ),
    (
        "kindred lineage remains governed by FOUNDATION-008"
    ),
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
                "Parent-child primitives are normalized "
                "onto the existing FOUNDATION-008 "
                "directed lineage Segue authority. "
                "Kindred parent and child views are now "
                "deterministic projections rather than "
                "duplicated authoritative storage."
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
