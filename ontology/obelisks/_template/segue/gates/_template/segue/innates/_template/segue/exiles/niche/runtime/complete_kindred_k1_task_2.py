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
    "k1:task-2"
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
        "alliance_affinity.py"
    ),
]

receipts = [
    (
        "alliance and affinity are normalized as "
        "role-bearing Segue projections"
    ),
    (
        "alliance and affinity preserve stable identity, "
        "validity, provenance, qualifiers, and extensions"
    ),
    (
        "alliance and affinity do not introduce a second "
        "relationship authority graph"
    ),
    (
        "alliance and affinity propagation defaults to "
        "disabled rather than implying descent"
    ),
    (
        "alliance and affinity project through the existing "
        "FOUNDATION-008 lineage Segue representation"
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
                "Alliance and affinity primitives are "
                "normalized as typed role-bearing Segue "
                "projections over the existing lineage "
                "authority, preserving provenance and "
                "temporal qualification without creating "
                "duplicate relationship authority."
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
