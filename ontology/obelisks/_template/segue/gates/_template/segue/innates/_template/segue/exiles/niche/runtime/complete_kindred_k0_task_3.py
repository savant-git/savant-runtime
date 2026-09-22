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
    "k0:task-3"
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
        "/root/savant-runtime/authority_graph/policies/"
        "lineage_authority_projection.json"
    ),
    (
        "/root/savant-runtime/authority_graph/schemas/"
        "lineage_segue.schema.json"
    ),
    (
        "/root/savant-runtime/runtime/lineage/model.py"
    ),
]


receipts = [
    (
        "FOUNDATION-008 declares authoritative lineage "
        "is stored once as a directed parent-to-child segue"
    ),
    (
        "policy.functional_lineage declares lineage_segue "
        "the authoritative primitive"
    ),
    (
        "policy.functional_lineage declares parent and "
        "child lists projections and forbids duplicate "
        "inverse storage"
    ),
    (
        "lineage_segue.schema.json requires kind segue, "
        "type lineage, parent, child, and role"
    ),
    (
        "runtime/lineage/model.py implements stable "
        "lineage binding identity"
    ),
    (
        "runtime/lineage/model.py implements parent, child, "
        "functional role, continuation, inheritance, "
        "propagation, authority, validity, provenance, "
        "and extension surfaces"
    ),
    (
        "direct Segue relationship authority is confirmed "
        "by constitutional canon, active policy, schema, "
        "and verified runtime implementation"
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
                "Direct Segue relationship authority is "
                "confirmed. FOUNDATION-008 defines the "
                "directed lineage segue as authoritative; "
                "active policy, schema, and runtime model "
                "implement that primitive while keeping "
                "inverse parent and child views derivative."
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
