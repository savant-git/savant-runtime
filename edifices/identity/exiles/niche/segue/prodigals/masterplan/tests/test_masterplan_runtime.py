#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import given, strategies as st


SUBJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_ROOT = SUBJECT_ROOT / "contracts"
RUNTIME_ROOT = SUBJECT_ROOT / "runtime"

for path in (
    CONTRACTS_ROOT,
    RUNTIME_ROOT,
):
    if str(path) not in sys.path:
        sys.path.insert(
            0,
            str(path),
        )


from masterplan_contracts import (  # noqa: E402
    AuthorityEnvelope,
    AuthorityState,
    MasterplanRequest,
    PriorityRecord,
    ProvenanceEnvelope,
    SegueType,
    SourceReference,
    TaskGraph,
    TaskKind,
    TaskRecord,
    TaskSegue,
    TaskStatus,
)
from masterplan_runtime import (  # noqa: E402
    audit_graph,
    canonical_bytes,
    deterministic_projection,
    digest,
    execute_request,
    graph_digest,
    select_next,
    task_executable,
)


GENERATED_AT = "2026-08-01T00:00:00+00:00"


def authority(
    state: AuthorityState = AuthorityState.ACCEPTED,
    *,
    tier: int = 1,
) -> AuthorityEnvelope:
    return AuthorityEnvelope(
        state=state,
        authority_class="project-owner-directed",
        tier=tier,
        source="test",
        accepted_by=(
            "test-owner"
            if state
            in {
                AuthorityState.ACCEPTED,
                AuthorityState.AUTHORITATIVE,
            }
            else None
        ),
        accepted_at=(
            GENERATED_AT
            if state
            in {
                AuthorityState.ACCEPTED,
                AuthorityState.AUTHORITATIVE,
            }
            else None
        ),
        confidence=1.0,
    )


def provenance() -> ProvenanceEnvelope:
    return ProvenanceEnvelope(
        sources=(
            SourceReference(
                source_id="test-source",
                source_kind="test",
                authority_state=(
                    AuthorityState.ACCEPTED
                ),
            ),
        ),
        transformations=(),
        generated_by="test-suite",
        generated_at=GENERATED_AT,
    )


def task(
    task_id: str,
    *,
    title: str | None = None,
    band: str = "P0",
    ordinal: int = 1,
    status: TaskStatus = TaskStatus.ACCEPTED,
    state: AuthorityState = AuthorityState.ACCEPTED,
    kind: TaskKind = TaskKind.TASK,
    locked: bool = False,
) -> TaskRecord:
    return TaskRecord(
        id=task_id,
        kind=kind,
        title=title or task_id,
        description="",
        priority=PriorityRecord(
            band=band,
            ordinal=ordinal,
            authority_locked=locked,
            rationale="test",
        ),
        status=status,
        authority=authority(state),
        purpose="test",
        scope={},
        acceptance=(
            "test acceptance",
        ),
        evidence_requirements=(),
        outputs=(),
        risks=(),
        security={},
        lineage={},
        provenance=provenance(),
        extensions={},
    )


def segue(
    segue_id: str,
    source: str,
    target: str,
    segue_type: SegueType,
) -> TaskSegue:
    return TaskSegue(
        id=segue_id,
        type=segue_type,
        source=source,
        target=target,
        authority=authority(),
        provenance=provenance(),
        validity={},
        extensions={},
    )


def graph(
    records: tuple[TaskRecord, ...],
    segues: tuple[TaskSegue, ...] = (),
) -> TaskGraph:
    return TaskGraph(
        authority=authority(
            AuthorityState.AUTHORITATIVE,
            tier=0,
        ),
        records=records,
        segues=segues,
        events=(),
        decisions=(),
        evidence=(),
        receipts=(),
        attestations=(),
    )


def request(
    task_graph: TaskGraph,
    operation: str,
    *,
    projection: str | None = None,
) -> MasterplanRequest:
    return MasterplanRequest(
        request_id=f"test-{operation}",
        operation=operation,
        graph=task_graph,
        projection=projection,
        authority=authority(),
        provenance=provenance(),
    )


def test_highest_priority_executable_task_is_selected() -> None:
    value = graph(
        (
            task(
                "SAV-P1-001",
                band="P1",
                ordinal=1,
            ),
            task(
                "SAV-P0-001",
                band="P0",
                ordinal=1,
                locked=True,
            ),
        )
    )

    selection = select_next(
        value,
        provenance(),
    )

    assert (
        selection.selected_task_id
        == "SAV-P0-001"
    )


def test_unfinished_dependency_blocks_task() -> None:
    dependency = task(
        "SAV-P0-001",
        status=TaskStatus.ACTIVE,
    )

    dependent = task(
        "SAV-P0-002",
        ordinal=2,
    )

    value = graph(
        (
            dependency,
            dependent,
        ),
        (
            segue(
                "segue-SAV-P0-002-depends-SAV-P0-001",
                "SAV-P0-002",
                "SAV-P0-001",
                SegueType.DEPENDS_ON,
            ),
        ),
    )

    assert (
        task_executable(
            value,
            dependent,
        )
        is False
    )

    selection = select_next(
        value,
        provenance(),
    )

    assert (
        selection.selected_task_id
        == "SAV-P0-001"
    )


def test_completed_dependency_unblocks_task() -> None:
    dependency = task(
        "SAV-P0-001",
        status=TaskStatus.COMPLETED,
    )

    dependent = task(
        "SAV-P0-002",
        ordinal=2,
    )

    value = graph(
        (
            dependency,
            dependent,
        ),
        (
            segue(
                "segue-SAV-P0-002-depends-SAV-P0-001",
                "SAV-P0-002",
                "SAV-P0-001",
                SegueType.DEPENDS_ON,
            ),
        ),
    )

    assert (
        task_executable(
            value,
            dependent,
        )
        is True
    )


def test_proposed_task_is_not_executable() -> None:
    proposed = task(
        "SAV-P4A-001",
        band="P4A",
        state=AuthorityState.PROPOSED,
        status=TaskStatus.PROPOSED,
    )

    value = graph(
        (
            proposed,
        )
    )

    assert (
        task_executable(
            value,
            proposed,
        )
        is False
    )

    selection = select_next(
        value,
        provenance(),
    )

    assert (
        selection.selected_task_id
        is None
    )


def test_equal_graphs_produce_equal_selection_digests() -> None:
    value = graph(
        (
            task(
                "SAV-P0-001",
                locked=True,
            ),
            task(
                "SAV-P1-001",
                band="P1",
            ),
        )
    )

    first = select_next(
        value,
        provenance(),
    )

    second = select_next(
        value,
        provenance(),
    )

    assert (
        first.selection_digest
        == second.selection_digest
    )


def test_graph_digest_excludes_volatile_fields() -> None:
    first = provenance().model_dump(
        mode="json",
    )

    second = json.loads(
        json.dumps(first)
    )

    first[
        "generated_at"
    ] = "2026-01-01T00:00:00+00:00"

    second[
        "generated_at"
    ] = "2027-01-01T00:00:00+00:00"

    assert digest(
        deterministic_projection(first)
    ) == digest(
        deterministic_projection(second)
    )


def test_audit_detects_dependency_cycle() -> None:
    value = graph(
        (
            task("SAV-P0-001"),
            task("SAV-P0-002"),
        ),
        (
            segue(
                "segue-a-b",
                "SAV-P0-001",
                "SAV-P0-002",
                SegueType.DEPENDS_ON,
            ),
            segue(
                "segue-b-a",
                "SAV-P0-002",
                "SAV-P0-001",
                SegueType.DEPENDS_ON,
            ),
        ),
    )

    audit = audit_graph(value)

    assert audit["passed"] is False
    assert audit["dependency_cycles"]


def test_completed_task_without_attestation_fails_audit() -> None:
    value = graph(
        (
            task(
                "SAV-P0-001",
                status=TaskStatus.COMPLETED,
            ),
        )
    )

    audit = audit_graph(value)

    assert audit["passed"] is False
    assert (
        "SAV-P0-001"
        in audit["invalid_completions"]
    )


def test_agent_context_projects_selected_task() -> None:
    value = graph(
        (
            task(
                "SAV-P0-001",
                locked=True,
            ),
            task(
                "SAV-P2A-001",
                band="P2A",
            ),
        )
    )

    result = execute_request(
        request(
            value,
            "project",
            projection="agent_context",
        )
    )

    assert result.passed is True
    assert result.projection is not None
    assert (
        result.projection.payload[
            "selected_task"
        ][
            "id"
        ]
        == "SAV-P0-001"
    )


def test_equal_requests_produce_equal_result_digests() -> None:
    value = graph(
        (
            task(
                "SAV-P0-001",
                locked=True,
            ),
        )
    )

    operation = request(
        value,
        "select_next",
    )

    first = execute_request(
        operation
    )

    second = execute_request(
        operation
    )

    assert (
        first.result_digest
        == second.result_digest
    )


def test_canonical_bytes_are_stable() -> None:
    value = {
        "z": 1,
        "a": {
            "d": 4,
            "b": 2,
        },
    }

    first = canonical_bytes(value)

    second = canonical_bytes(
        json.loads(first)
    )

    assert first == second


@given(
    title=st.text(
        alphabet=st.characters(
            blacklist_categories=(
                "Cs",
            ),
        ),
        min_size=1,
        max_size=100,
    )
)
def test_task_title_does_not_change_selection_determinism(
    title: str,
) -> None:
    value = graph(
        (
            task(
                "SAV-P0-001",
                title=title,
                locked=True,
            ),
        )
    )

    first = select_next(
        value,
        provenance(),
    )

    second = select_next(
        value,
        provenance(),
    )

    assert (
        first.selection_digest
        == second.selection_digest
    )


def test_graph_digest_is_stable() -> None:
    value = graph(
        (
            task(
                "SAV-P0-001",
                locked=True,
            ),
        )
    )

    assert (
        graph_digest(value)
        == graph_digest(value)
    )
