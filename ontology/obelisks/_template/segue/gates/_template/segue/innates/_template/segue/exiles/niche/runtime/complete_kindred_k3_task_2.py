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
    "k3:task-2"
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
        "descent_policy.py"
    ),
    (
        "/root/savant-runtime/lexicon/kindred/"
        "propagation_policy.py"
    ),
]

receipts = [
    (
        "Kindred descent eligibility and payload "
        "propagation are separate policy decisions"
    ),
    (
        "a descent relationship does not itself "
        "authorize propagation"
    ),
    (
        "propagation permission does not itself "
        "establish descent"
    ),
    (
        "qualification characteristic capability "
        "state and metadata propagation are evaluated "
        "as distinct payload classes"
    ),
    (
        "state and metadata propagation are blocked "
        "by default"
    ),
    (
        "conditional payload propagation requires "
        "explicit permission and evidence"
    ),
    (
        "propagation can reference a descent-policy "
        "decision without modifying descent authority"
    ),
    (
        "propagation decisions remain deterministic "
        "non-authoritative certificates"
    ),
    (
        "underlying authoritative relationship Segues "
        "remain stored once"
    ),
    (
        "transitive propagation is independently "
        "controllable and disabled by default"
    ),
]

enhancements = [
    "descent_propagation_separation",
    "independent_propagation_policy",
    "qualification_payload_isolation",
    "characteristic_payload_isolation",
    "capability_payload_isolation",
    "state_payload_isolation",
    "metadata_payload_isolation",
    "default_state_propagation_block",
    "default_metadata_propagation_block",
    "explicit_propagation_evidence",
    "explicit_propagation_permission",
    "descent_eligibility_gate",
    "descent_policy_reference_only",
    "no_descent_implies_propagation",
    "no_propagation_implies_descent",
    "non_authoritative_decision_certificate",
    "immutable_propagation_policy",
    "stable_propagation_policy_identity",
    "source_provenance_preservation",
    "transitive_propagation_control",
    "payload_specific_policy",
    "deterministic_propagation_decision",
    "safe_default_blocking",
    "extension_ready_propagation",
    "authority_bound_propagation",
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
                "Kindred now treats descent and "
                "payload propagation as independent "
                "policy domains. Descent may gate "
                "propagation but never implicitly "
                "causes it, preserving authority and "
                "preventing accidental inheritance."
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
