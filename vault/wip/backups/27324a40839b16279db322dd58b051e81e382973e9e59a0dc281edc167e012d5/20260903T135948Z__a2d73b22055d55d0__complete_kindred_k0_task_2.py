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


def main() -> int:
    task_engine = engine()

    task_engine.amend(
        task_id,
        {
            "implementation_references": [
                (
                    "/root/savant-runtime/canon/foundation/"
                    "008_FUNCTIONAL_LINEAGE_CANON.md"
                ),
                (
                    "/root/savant-runtime/authority_graph/"
                    "kinship/kinship_registry.json"
                ),
                (
                    "/root/savant-runtime/runtime/kinship"
                ),
                (
                    "/root/savant-runtime/tools/"
                    "run_functional_kinship_validation.sh"
                ),
            ],
        },
    )

    completed = task_engine.transition(
        task_id,
        "completed",
        receipts=[
            (
                "FOUNDATION-008 is active tier-0 "
                "constitutional canon"
            ),
            (
                "FOUNDATION-008 stores authoritative "
                "lineage once as a directed "
                "parent-to-child segue"
            ),
            (
                "FOUNDATION-008 requires parent and "
                "child views to be deterministic "
                "projections"
            ),
            (
                "FOUNDATION-008 requires legacy "
                "parent-child projection without "
                "duplicated authority"
            ),
            (
                "runtime/kinship implementation "
                "is present"
            ),
            (
                "bounded dependency inspection "
                "demonstrated no external operational "
                "runtime/kinship consumer"
            ),
            (
                "classification: preserve runtime/"
                "kinship as compatibility implementation "
                "pending semantic migration and "
                "reverse-dependency proof; do not "
                "recognize it as independent "
                "relationship authority"
            ),
        ],
        reason=(
            "Legacy kinship surfaces classified "
            "against active FOUNDATION-008. "
            "The constitutional authority is the "
            "directed lineage segue, not an independent "
            "duplicated kinship authority. Existing "
            "kinship surfaces remain preserved for "
            "compatibility until semantic migration "
            "and reverse-dependency proof."
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
                "completed": completed,
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
