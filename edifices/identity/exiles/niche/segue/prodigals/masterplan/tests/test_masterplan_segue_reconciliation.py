#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path("/root/savant-runtime")

TOOLS_ROOT = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
)

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(TOOLS_ROOT),
    )


from plan_duplicate_segue_reconciliation import (  # noqa: E402
    build_plan,
    semantic_digest,
)

from apply_duplicate_segue_reconciliation import (  # noqa: E402
    ReconciliationError,
    apply_reconciliation,
    validate_authorization,
)


def authority(
    state: str = "accepted",
) -> dict:
    return {
        "state": state,
        "authority_class": (
            "project-owner-directed"
        ),
        "tier": 1,
        "source": "test",
        "accepted_by": (
            "project-owner"
            if state in {
                "accepted",
                "authoritative",
            }
            else None
        ),
        "accepted_at": (
            "2026-08-02T00:00:00+00:00"
            if state in {
                "accepted",
                "authoritative",
            }
            else None
        ),
        "confidence": 1.0,
    }


def provenance() -> dict:
    return {
        "sources": [],
        "transformations": [],
        "generated_by": "test",
        "generated_at": (
            "2026-08-02T00:00:00+00:00"
        ),
        "contract_version": "1.0.0",
    }


def task(
    task_id: str,
) -> dict:
    return {
        "id": task_id,
        "kind": "task",
        "title": task_id,
        "description": "",
        "priority": {
            "band": "P4A",
            "ordinal": 1,
            "authority_locked": False,
            "rationale": "test",
        },
        "status": "active",
        "authority": authority(),
        "purpose": "test",
        "scope": {},
        "acceptance": [],
        "evidence_requirements": [],
        "outputs": [],
        "risks": [],
        "security": {},
        "lineage": {},
        "provenance": provenance(),
        "extensions": {},
    }


def segue(
    segue_id: str,
    *,
    state: str = "accepted",
    tier: int = 1,
) -> dict:
    value = {
        "id": segue_id,
        "type": "depends_on",
        "source": "SAV-P4A-002",
        "target": "SAV-P4A-001",
        "authority": authority(
            state
        ),
        "provenance": provenance(),
    }

    value[
        "authority"
    ][
        "tier"
    ] = tier

    return value


def graph() -> dict:
    return {
        "schema_version": "1.1.0",
        "graph_id": "savant.masterplan",
        "authority": authority(
            "authoritative"
        ),
        "records": [
            task(
                "SAV-P4A-001"
            ),
            task(
                "SAV-P4A-002"
            ),
        ],
        "segues": [
            segue(
                "segue-authoritative",
                state="authoritative",
                tier=0,
            ),
            segue(
                "segue-accepted",
                state="accepted",
                tier=1,
            ),
            segue(
                "segue-proposed",
                state="proposed",
                tier=2,
            ),
        ],
        "events": [],
        "decisions": [],
        "evidence": [],
        "receipts": [],
        "attestations": [],
    }


def decision(
    plan: dict,
) -> dict:
    return {
        "id": "decision-test",
        "subject": "SAV-P4A-001",
        "decision": (
            "approve_duplicate_"
            "segue_reconciliation"
        ),
        "authority": authority(
            "accepted"
        ),
        "rationale": "test",
        "occurred_at": (
            "2026-08-02T00:00:00+00:00"
        ),
        "provenance": provenance(),
        "extensions": {
            "payload": {
                "plan_semantic_digest": (
                    plan[
                        "semantic_digest"
                    ]
                ),
                "graph_semantic_digest": (
                    plan[
                        "graph"
                    ][
                        "semantic_digest"
                    ]
                ),
                "removal_ids": (
                    plan[
                        "proposed_removal_ids"
                    ]
                ),
                "removal_count": len(
                    plan[
                        "proposed_removal_ids"
                    ]
                ),
            }
        },
    }


def test_plan_retains_highest_authority_segue() -> None:
    value = graph()

    plan = build_plan(
        value
    )

    assert plan[
        "statistics"
    ][
        "duplicate_group_count"
    ] == 1

    assert plan[
        "statistics"
    ][
        "proposed_removal_count"
    ] == 2

    assert (
        "segue-authoritative"
        in plan[
            "retained_ids"
        ]
    )

    assert plan[
        "proposed_removal_ids"
    ] == [
        "segue-accepted",
        "segue-proposed",
    ]


def test_plan_is_deterministic() -> None:
    first = build_plan(
        graph()
    )

    second_graph = graph()

    second_graph[
        "segues"
    ] = list(
        reversed(
            second_graph[
                "segues"
            ]
        )
    )

    second = build_plan(
        second_graph
    )

    assert first[
        "semantic_digest"
    ] == second[
        "semantic_digest"
    ]


def test_reconciliation_removes_only_authorized_ids() -> None:
    value = graph()

    result = apply_reconciliation(
        value,
        [
            "segue-accepted",
            "segue-proposed",
        ],
    )

    identifiers = [
        record[
            "id"
        ]
        for record in result[
            "segues"
        ]
    ]

    assert identifiers == [
        "segue-authoritative"
    ]

    assert len(
        value[
            "segues"
        ]
    ) == 3


def test_reconciliation_rejects_missing_ids() -> None:
    with pytest.raises(
        ReconciliationError
    ):
        apply_reconciliation(
            graph(),
            [
                "segue-does-not-exist",
            ],
        )


def test_authorization_accepts_exact_current_plan() -> None:
    value = graph()

    plan = build_plan(
        value
    )

    accepted = decision(
        plan
    )

    removals = validate_authorization(
        value,
        plan,
        accepted,
    )

    assert removals == [
        "segue-accepted",
        "segue-proposed",
    ]


def test_authorization_rejects_stale_graph() -> None:
    value = graph()

    plan = build_plan(
        value
    )

    accepted = decision(
        plan
    )

    changed = copy.deepcopy(
        value
    )

    changed[
        "records"
    ][0][
        "title"
    ] = "Changed"

    with pytest.raises(
        ReconciliationError
    ):
        validate_authorization(
            changed,
            plan,
            accepted,
        )


def test_authorization_rejects_changed_removal_set() -> None:
    value = graph()

    plan = build_plan(
        value
    )

    accepted = decision(
        plan
    )

    accepted[
        "extensions"
    ][
        "payload"
    ][
        "removal_ids"
    ] = [
        "segue-proposed",
    ]

    with pytest.raises(
        ReconciliationError
    ):
        validate_authorization(
            value,
            plan,
            accepted,
        )


def test_semantic_digest_is_key_order_stable() -> None:
    first = {
        "b": 2,
        "a": 1,
    }

    second = {
        "a": 1,
        "b": 2,
    }

    assert semantic_digest(
        first
    ) == semantic_digest(
        second
    )
