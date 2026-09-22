#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
from pathlib import Path


SUBJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = (
    Path("/root/savant-runtime")
    / "tools"
    / "niche"
    / "masterplan"
)

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(TOOLS_ROOT),
    )


from build_authoritative_task_graph import (  # noqa: E402
    assert_preserved_authority,
    deterministic_projection,
    digest,
    merge_current_work,
    proposed_segues,
    task_map,
)


def accepted_authority() -> dict:
    return {
        "state": "accepted",
        "authority_class": "project-owner-directed",
        "tier": 1,
        "source": "test",
        "accepted_by": "project-owner",
        "accepted_at": "2026-08-01T00:00:00+00:00",
        "confidence": 1.0,
    }


def proposed_authority() -> dict:
    return {
        "state": "proposed",
        "authority_class": "project-owner-directed",
        "tier": 2,
        "source": "test",
        "accepted_by": None,
        "accepted_at": None,
        "confidence": 1.0,
    }


def provenance() -> dict:
    return {
        "sources": [],
        "transformations": [],
        "generated_by": "test",
        "generated_at": "2026-08-01T00:00:00+00:00",
        "contract_version": "1.0.0",
    }


def task(
    task_id: str,
    *,
    status: str = "accepted",
    authority: dict | None = None,
    dependencies: list[str] | None = None,
) -> dict:
    return {
        "id": task_id,
        "kind": "task",
        "title": task_id,
        "description": "",
        "priority": {
            "band": "P0",
            "ordinal": 1,
            "authority_locked": False,
            "rationale": "test",
        },
        "status": status,
        "authority": (
            authority
            if authority is not None
            else accepted_authority()
        ),
        "purpose": "test",
        "scope": {
            "depends_on": dependencies or [],
        },
        "acceptance": [
            "test acceptance"
        ],
        "evidence_requirements": [],
        "outputs": [],
        "risks": [],
        "security": {},
        "lineage": {},
        "provenance": provenance(),
        "extensions": {},
    }


def graph() -> dict:
    return {
        "schema_version": "1.0.0",
        "graph_id": "savant.masterplan",
        "authority": {
            "state": "authoritative",
            "authority_class": "project-owner-directed",
            "tier": 0,
            "source": "test",
            "accepted_by": "project-owner",
            "accepted_at": "2026-08-01T00:00:00+00:00",
            "confidence": 1.0,
        },
        "records": [
            task(
                "SAV-P0-001",
                status="active",
            ),
        ],
        "segues": [],
        "events": [
            {
                "id": "event-001",
                "task_id": "SAV-P0-001",
                "event_type": "task.status.transition",
                "previous_state": "accepted",
                "next_state": "active",
                "authority": accepted_authority(),
                "occurred_at": "2026-08-01T00:00:00+00:00",
                "provenance": provenance(),
            }
        ],
        "decisions": [
            {
                "id": "decision-001",
                "subject": "SAV-P0-001",
                "decision": "accept_task",
                "authority": accepted_authority(),
                "rationale": "test",
                "occurred_at": "2026-08-01T00:00:00+00:00",
                "provenance": provenance(),
            }
        ],
        "evidence": [
            {
                "id": "evidence-001",
                "task_id": "SAV-P0-001",
                "kind": "test",
                "path": None,
                "sha256": None,
                "passed": True,
                "authority": accepted_authority(),
                "provenance": provenance(),
            }
        ],
        "receipts": [
            {
                "id": "receipt-001",
                "task_id": "SAV-P0-001",
                "operation": "test",
                "passed": True,
                "outputs": [],
                "evidence": [
                    "evidence-001"
                ],
                "occurred_at": "2026-08-01T00:00:00+00:00",
                "provenance": provenance(),
            }
        ],
        "attestations": [
            {
                "id": "attestation-001",
                "task_id": "SAV-P0-001",
                "passed": True,
                "criteria": [
                    {
                        "criterion": "test",
                        "passed": True,
                        "evidence": [
                            "evidence-001"
                        ],
                        "reason": "",
                    }
                ],
                "evidence": [
                    "evidence-001"
                ],
                "digest": "0" * 64,
                "occurred_at": "2026-08-01T00:00:00+00:00",
                "provenance": provenance(),
            }
        ],
    }


def test_authoritative_collections_are_preserved() -> None:
    before = graph()
    after = copy.deepcopy(before)

    result = assert_preserved_authority(
        before,
        after,
    )

    assert result["passed"] is True
    assert result["collection_losses"] == {}


def test_removing_event_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after["events"] = []

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Removing an event must fail preservation."
        )


def test_removing_decision_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after["decisions"] = []

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Removing a decision must fail preservation."
        )


def test_removing_evidence_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after["evidence"] = []

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Removing evidence must fail preservation."
        )


def test_removing_receipt_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after["receipts"] = []

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Removing a receipt must fail preservation."
        )


def test_removing_attestation_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after["attestations"] = []

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Removing an attestation must fail preservation."
        )


def test_changing_accepted_task_status_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after["records"][0]["status"] = "completed"

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Builder must not change accepted task status."
        )


def test_changing_accepted_task_priority_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after[
        "records"
    ][0][
        "priority"
    ][
        "ordinal"
    ] = 999

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Builder must not change accepted task priority."
        )


def test_changing_accepted_authority_is_rejected() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after[
        "records"
    ][0][
        "authority"
    ][
        "state"
    ] = "proposed"

    try:
        assert_preserved_authority(
            before,
            after,
        )

    except RuntimeError:
        pass

    else:
        raise AssertionError(
            "Builder must not demote accepted authority."
        )


def test_new_proposed_record_can_be_added() -> None:
    before = graph()
    after = copy.deepcopy(before)

    after["records"].append(
        task(
            "SAV-P2A-001",
            status="proposed",
            authority=proposed_authority(),
        )
    )

    result = assert_preserved_authority(
        before,
        after,
    )

    assert result["passed"] is True
    assert (
        "SAV-P2A-001"
        in task_map(after)
    )


def test_proposed_dependency_generates_one_segue() -> None:
    records = {
        "SAV-P0-001": task(
            "SAV-P0-001",
            status="completed",
        ),
        "SAV-P2A-001": task(
            "SAV-P2A-001",
            status="proposed",
            authority=proposed_authority(),
            dependencies=[
                "SAV-P0-001"
            ],
        ),
    }

    segues = proposed_segues(
        records
    )

    assert len(segues) == 1
    assert (
        segues[0]["source"]
        == "SAV-P2A-001"
    )
    assert (
        segues[0]["target"]
        == "SAV-P0-001"
    )
    assert (
        segues[0]["type"]
        == "depends_on"
    )


def test_equal_graphs_produce_equal_digests() -> None:
    first = graph()
    second = copy.deepcopy(
        first
    )

    assert digest(
        deterministic_projection(
            first
        )
    ) == digest(
        deterministic_projection(
            second
        )
    )


def test_task_map_rejects_duplicate_ids() -> None:
    value = graph()

    value["records"].append(
        copy.deepcopy(
            value["records"][0]
        )
    )

    try:
        task_map(value)

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Duplicate task identifiers must fail."
        )
