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
    "k0:task-2"
)

terminal_states = {
    "completed",
    "rejected",
    "superseded",
}


def main() -> int:
    task_engine = engine()

    current = task_engine.public_task(
        task_id
    )

    if current["status"] not in terminal_states:
        task_engine.amend(
            task_id,
            {
                "implementation_references": [
                    (
                        "/root/savant-runtime/canon/"
                        "foundation/"
                        "008_FUNCTIONAL_LINEAGE_CANON.md"
                    ),
                    (
                        "/root/savant-runtime/"
                        "authority_graph/kindred/"
                        "kindred_registry.json"
                    ),
                    (
                        "/root/savant-runtime/"
                        "runtime/kindred"
                    ),
                    (
                        "/root/savant-runtime/tools/"
                        "run_functional_kindred_"
                        "validation.sh"
                    ),
                ],
            },
        )

        current = task_engine.transition(
            task_id,
            "completed",
            receipts=[
                (
                    "FOUNDATION-008 is active "
                    "tier-0 constitutional canon"
                ),
                (
                    "FOUNDATION-008 stores "
                    "authoritative lineage once "
                    "as a directed parent-to-child "
                    "segue"
                ),
                (
                    "FOUNDATION-008 requires "
                    "parent and child views to be "
                    "deterministic projections"
                ),
                (
                    "FOUNDATION-008 requires "
                    "legacy parent-child projection "
                    "without duplicated authority"
                ),
                (
                    "runtime/kindred implementation "
                    "is present"
                ),
                (
                    "bounded dependency inspection "
                    "demonstrated no external "
                    "operational runtime/kindred "
                    "consumer"
                ),
                (
                    "classification: preserve "
                    "runtime/kindred as compatibility "
                    "implementation pending semantic "
                    "migration and reverse-dependency "
                    "proof; do not recognize it as "
                    "independent relationship "
                    "authority"
                ),
            ],
            reason=(
                "Legacy kindred surfaces classified "
                "against active FOUNDATION-008. "
                "The constitutional authority is "
                "the directed lineage segue, not an "
                "independent duplicated kindred "
                "authority. Existing kindred "
                "surfaces remain preserved for "
                "compatibility until semantic "
                "migration and reverse-dependency "
                "proof."
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
