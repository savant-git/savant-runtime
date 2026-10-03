#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest


ROOT = Path("/root/savant-runtime")

POLICY_ROOT = (
    ROOT
    / "edifices"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
    / "policies"
)

if str(POLICY_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(POLICY_ROOT),
    )


from masterplan_policy_runtime import (  # noqa: E402
    PolicyValidationError,
    build_registry,
    build_task_facts,
    default_policies,
    evaluate_operation,
    evaluate_policy,
    semantic_digest,
    validate_policy,
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
            "2026-08-01T00:00:00+00:00"
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
            "2026-08-01T00:00:00+00:00"
        ),
        "contract_version": "1.0.0",
    }


def task(
    task_id: str,
    *,
    status: str = "active",
    authority_state: str = "accepted",
) -> dict:
    return {
        "id": task_id,
        "kind": "task",
        "title": task_id,
        "description": "",
        "priority": {
            "band": "P4A",
            "ordinal": 24,
            "authority_locked": False,
            "rationale": "test",
        },
        "status": status,
        "authority": authority(
            authority_state
        ),
        "purpose": "test",
        "scope": {},
        "acceptance": [
            "test"
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
        "schema_version": "1.1.0",
        "graph_id": "savant.masterplan",
        "authority": authority(
            "authoritative"
        ),
        "records": [
            task(
                "SAV-P4A-024"
            ),
            task(
                "SAV-P4A-023",
                status="completed",
            ),
        ],
        "segues": [
            {
                "id": "segue-test",
                "type": "depends_on",
                "source": "SAV-P4A-024",
                "target": "SAV-P4A-023",
                "authority": authority(),
                "provenance": provenance(),
            }
        ],
        "events": [],
        "decisions": [],
        "evidence": [
            {
                "id": "evidence-test",
                "task_id": "SAV-P4A-024",
                "kind": "unit-test",
                "passed": True,
                "authority": authority(),
                "provenance": provenance(),
            }
        ],
        "receipts": [],
        "attestations": [
            {
                "id": "attestation-test",
                "task_id": "SAV-P4A-024",
                "passed": True,
                "criteria": [],
                "evidence": [
                    "evidence-test"
                ],
                "digest": "0" * 64,
                "occurred_at": (
                    "2026-08-01T00:00:00+00:00"
                ),
                "authority": authority(),
                "provenance": provenance(),
            }
        ],
    }


def policy_by_id(
    policy_id: str,
) -> dict:
    return next(
        policy
        for policy in default_policies()
        if policy["id"] == policy_id
    )


def test_default_policies_validate() -> None:
    for policy in default_policies():
        result = validate_policy(
            policy
        )

        assert result[
            "passed"
        ] is True


def test_invalid_policy_kind_fails() -> None:
    policy = copy.deepcopy(
        default_policies()[0]
    )

    policy["kind"] = "imaginary"

    with pytest.raises(
        PolicyValidationError
    ):
        validate_policy(
            policy
        )


def test_accepted_authority_policy_passes() -> None:
    policy = policy_by_id(
        "policy.masterplan."
        "task-authority-required"
    )

    facts = {
        "task": {
            "authority_state": "accepted",
        }
    }

    decision = evaluate_policy(
        policy,
        facts,
    )

    assert decision.passed is True


def test_proposed_authority_policy_fails() -> None:
    policy = policy_by_id(
        "policy.masterplan."
        "task-authority-required"
    )

    facts = {
        "task": {
            "authority_state": "proposed",
        }
    }

    decision = evaluate_policy(
        policy,
        facts,
    )

    assert decision.passed is False


def test_deny_policy_rejects_terminal_task() -> None:
    policy = policy_by_id(
        "policy.masterplan."
        "terminal-task-mutation-denied"
    )

    facts = {
        "task": {
            "status": "completed",
        }
    }

    decision = evaluate_policy(
        policy,
        facts,
    )

    assert decision.passed is False


def test_deny_policy_allows_active_task() -> None:
    policy = policy_by_id(
        "policy.masterplan."
        "terminal-task-mutation-denied"
    )

    facts = {
        "task": {
            "status": "active",
        }
    }

    decision = evaluate_policy(
        policy,
        facts,
    )

    assert decision.passed is True


def test_task_facts_detect_ready_dependencies() -> None:
    facts = build_task_facts(
        graph(),
        "SAV-P4A-024",
        "task.complete",
    )

    assert facts[
        "task"
    ][
        "dependency_ready"
    ] is True

    assert facts[
        "task"
    ][
        "passing_evidence_count"
    ] == 1

    assert facts[
        "task"
    ][
        "has_passing_attestation"
    ] is True


def test_task_facts_detect_blocked_dependency() -> None:
    value = graph()

    value[
        "records"
    ][1][
        "status"
    ] = "active"

    facts = build_task_facts(
        value,
        "SAV-P4A-024",
        "task.execute",
    )

    assert facts[
        "task"
    ][
        "dependency_ready"
    ] is False

    assert facts[
        "task"
    ][
        "unresolved_dependencies"
    ] == [
        "SAV-P4A-023"
    ]


def test_completion_operation_passes() -> None:
    value = graph()

    facts = build_task_facts(
        value,
        "SAV-P4A-024",
        "task.complete",
    )

    result = evaluate_operation(
        default_policies(),
        facts,
        "task.complete",
    )

    assert result[
        "passed"
    ] is True


def test_completion_without_evidence_fails() -> None:
    value = graph()

    value["evidence"] = []

    facts = build_task_facts(
        value,
        "SAV-P4A-024",
        "task.complete",
    )

    result = evaluate_operation(
        default_policies(),
        facts,
        "task.complete",
    )

    assert result[
        "passed"
    ] is False

    failed_codes = {
        decision["code"]
        for decision in result[
            "decisions"
        ]
        if not decision["passed"]
    }

    assert (
        "masterplan.policy."
        "completion_evidence_missing"
        in failed_codes
    )


def test_registry_is_deterministic() -> None:
    policies = default_policies()

    first = build_registry(
        policies
    )

    second = build_registry(
        reversed(policies)
    )

    assert first[
        "semantic_digest"
    ] == second[
        "semantic_digest"
    ]


def test_equal_facts_have_equal_digest() -> None:
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
