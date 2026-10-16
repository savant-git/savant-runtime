#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


SUBJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_ROOT = SUBJECT_ROOT / "contracts"

if str(CONTRACTS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(CONTRACTS_ROOT),
    )

from masterplan_contracts import (  # noqa: E402
    AuthorityState,
    FailureRecord,
    MasterplanRequest,
    MasterplanResult,
    ProvenanceEnvelope,
    SegueType,
    SelectionReason,
    TaskGraph,
    TaskKind,
    TaskProjection,
    TaskQuery,
    TaskRecord,
    TaskSelection,
    TaskSelectionCandidate,
    TaskStatus,
)


RUNTIME_ID = "prodigal.niche.masterplan.runtime"
RUNTIME_VERSION = "1.0.0"

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
    "captured_at",
    "occurred_at",
    "accepted_at",
}

NON_EXECUTABLE_STATUSES = {
    TaskStatus.UNKNOWN,
    TaskStatus.PROPOSED,
    TaskStatus.BLOCKED,
    TaskStatus.PAUSED,
    TaskStatus.COMPLETED,
    TaskStatus.REJECTED,
    TaskStatus.CANCELLED,
    TaskStatus.SUPERSEDED,
    TaskStatus.ARCHIVED,
}

EXECUTABLE_STATUSES = {
    TaskStatus.ACCEPTED,
    TaskStatus.READY,
    TaskStatus.ACTIVE,
    TaskStatus.REOPENED,
}

COMPLETION_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.ARCHIVED,
    TaskStatus.SUPERSEDED,
}

AUTHORITY_WEIGHT = {
    AuthorityState.AUTHORITATIVE: 100000,
    AuthorityState.ACCEPTED: 80000,
    AuthorityState.PROPOSED: 30000,
    AuthorityState.OBSERVED: 20000,
    AuthorityState.UNKNOWN: 10000,
    AuthorityState.SUPERSEDED: -50000,
    AuthorityState.REJECTED: -100000,
}

STATUS_WEIGHT = {
    TaskStatus.ACTIVE: 5000,
    TaskStatus.READY: 4000,
    TaskStatus.REOPENED: 3500,
    TaskStatus.ACCEPTED: 3000,
    TaskStatus.BLOCKED: -10000,
    TaskStatus.PAUSED: -12000,
    TaskStatus.PROPOSED: -15000,
    TaskStatus.UNKNOWN: -20000,
    TaskStatus.COMPLETED: -30000,
    TaskStatus.CANCELLED: -40000,
    TaskStatus.REJECTED: -50000,
    TaskStatus.SUPERSEDED: -60000,
    TaskStatus.ARCHIVED: -70000,
}

KIND_WEIGHT = {
    TaskKind.GATE: 900,
    TaskKind.DECISION: 850,
    TaskKind.AUDIT: 800,
    TaskKind.VERIFICATION: 750,
    TaskKind.MIGRATION: 700,
    TaskKind.TASK: 650,
    TaskKind.SUBTASK: 600,
    TaskKind.MICROSTEP: 550,
    TaskKind.ONUS: 500,
    TaskKind.CAPABILITY: 450,
    TaskKind.MILESTONE: 400,
    TaskKind.ATTESTATION: 350,
    TaskKind.PROGRAM: 300,
}

PRIORITY_BAND_WEIGHT = {
    "P0": 10000,
    "P1": 9000,
    "P2": 8000,
    "P2A": 7900,
    "P3": 7000,
    "P4": 6000,
    "P4A": 5900,
    "P5": 5000,
    "P6": 4000,
    "P7": 3000,
    "P8": 2000,
    "P9": 1000,
    "P10": 500,
}


def canonical_bytes(
    value: Any,
) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(
            mode="json",
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(
            mode="json",
        )

    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def graph_digest(
    graph: TaskGraph,
) -> str:
    return digest(
        deterministic_projection(
            graph
        )
    )


def provenance_for(
    request: MasterplanRequest,
    transformations: Iterable[str],
) -> ProvenanceEnvelope:
    return ProvenanceEnvelope(
        sources=request.provenance.sources,
        transformations=tuple(
            transformations
        ),
        generated_by=(
            f"{RUNTIME_ID}@{RUNTIME_VERSION}"
        ),
        generated_at=(
            request.provenance.generated_at
        ),
    )


def task_map(
    graph: TaskGraph,
) -> dict[str, TaskRecord]:
    return {
        record.id: record
        for record in graph.records
    }


def outgoing_segues(
    graph: TaskGraph,
    segue_type: SegueType | None = None,
) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = defaultdict(list)

    for segue in graph.segues:
        if (
            segue_type is not None
            and segue.type != segue_type
        ):
            continue

        result[segue.source].append(
            segue
        )

    return {
        key: sorted(
            value,
            key=lambda segue: (
                segue.type.value,
                segue.target,
                segue.id,
            ),
        )
        for key, value in sorted(
            result.items()
        )
    }


def incoming_segues(
    graph: TaskGraph,
    segue_type: SegueType | None = None,
) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = defaultdict(list)

    for segue in graph.segues:
        if (
            segue_type is not None
            and segue.type != segue_type
        ):
            continue

        result[segue.target].append(
            segue
        )

    return {
        key: sorted(
            value,
            key=lambda segue: (
                segue.type.value,
                segue.source,
                segue.id,
            ),
        )
        for key, value in sorted(
            result.items()
        )
    }


def dependency_ids(
    graph: TaskGraph,
    task_id: str,
) -> tuple[str, ...]:
    values = {
        segue.target
        for segue in graph.segues
        if (
            segue.source == task_id
            and segue.type
            == SegueType.DEPENDS_ON
        )
    }

    return tuple(
        sorted(values)
    )


def blocker_ids(
    graph: TaskGraph,
    task_id: str,
) -> tuple[str, ...]:
    values = {
        segue.source
        for segue in graph.segues
        if (
            segue.target == task_id
            and segue.type
            == SegueType.BLOCKS
        )
    }

    return tuple(
        sorted(values)
    )


def unresolved_dependencies(
    graph: TaskGraph,
    task_id: str,
) -> tuple[str, ...]:
    records = task_map(graph)

    unresolved: list[str] = []

    for dependency_id in dependency_ids(
        graph,
        task_id,
    ):
        dependency = records[
            dependency_id
        ]

        if dependency.status not in COMPLETION_STATUSES:
            unresolved.append(
                dependency_id
            )

    return tuple(
        sorted(unresolved)
    )


def unresolved_blockers(
    graph: TaskGraph,
    task_id: str,
) -> tuple[str, ...]:
    records = task_map(graph)

    unresolved: list[str] = []

    for blocker_id in blocker_ids(
        graph,
        task_id,
    ):
        blocker = records[
            blocker_id
        ]

        if blocker.status not in COMPLETION_STATUSES:
            unresolved.append(
                blocker_id
            )

    return tuple(
        sorted(unresolved)
    )


def task_executable(
    graph: TaskGraph,
    task: TaskRecord,
) -> bool:
    if task.status not in EXECUTABLE_STATUSES:
        return False

    if task.authority.state not in {
        AuthorityState.ACCEPTED,
        AuthorityState.AUTHORITATIVE,
    }:
        return False

    if unresolved_dependencies(
        graph,
        task.id,
    ):
        return False

    if unresolved_blockers(
        graph,
        task.id,
    ):
        return False

    return True


def priority_band_score(
    band: str,
) -> int:
    if band in PRIORITY_BAND_WEIGHT:
        return PRIORITY_BAND_WEIGHT[
            band
        ]

    prefix = ""

    for character in band:
        if character.isdigit():
            break

        prefix += character

    digits = "".join(
        character
        for character in band
        if character.isdigit()
    )

    if prefix == "P" and digits:
        return max(
            0,
            10000
            - int(digits) * 1000,
        )

    return 0


def downstream_blocking_impact(
    graph: TaskGraph,
    task_id: str,
) -> int:
    adjacency: dict[str, set[str]] = defaultdict(set)

    for segue in graph.segues:
        if segue.type in {
            SegueType.DEPENDS_ON,
            SegueType.BLOCKS,
        }:
            if segue.type == SegueType.DEPENDS_ON:
                adjacency[
                    segue.target
                ].add(
                    segue.source
                )

            else:
                adjacency[
                    segue.source
                ].add(
                    segue.target
                )

    visited: set[str] = set()
    queue: deque[str] = deque(
        sorted(
            adjacency.get(
                task_id,
                set(),
            )
        )
    )

    while queue:
        current = queue.popleft()

        if current in visited:
            continue

        visited.add(current)

        for child in sorted(
            adjacency.get(
                current,
                set(),
            )
        ):
            if child not in visited:
                queue.append(child)

    return len(visited)


def task_score(
    graph: TaskGraph,
    task: TaskRecord,
) -> int:
    executable = task_executable(
        graph,
        task,
    )

    score = 0

    score += AUTHORITY_WEIGHT[
        task.authority.state
    ]

    score += STATUS_WEIGHT[
        task.status
    ]

    score += priority_band_score(
        task.priority.band
    )

    score += KIND_WEIGHT[
        task.kind
    ]

    score += max(
        0,
        1000
        - task.priority.ordinal,
    )

    score += downstream_blocking_impact(
        graph,
        task.id,
    ) * 50

    score += task.authority.tier * 100

    if task.priority.authority_locked:
        score += 2000

    if executable:
        score += 50000

    return score


def selection_reasons(
    graph: TaskGraph,
    task: TaskRecord,
) -> tuple[SelectionReason, ...]:
    reasons: list[
        SelectionReason
    ] = []

    if task.authority.state in {
        AuthorityState.ACCEPTED,
        AuthorityState.AUTHORITATIVE,
    }:
        reasons.append(
            SelectionReason.AUTHORITY
        )

    reasons.append(
        SelectionReason.PRIORITY
    )

    if not unresolved_dependencies(
        graph,
        task.id,
    ):
        reasons.append(
            SelectionReason.DEPENDENCY
        )

    if downstream_blocking_impact(
        graph,
        task.id,
    ):
        reasons.append(
            SelectionReason.BLOCKING_IMPACT
        )

    return tuple(
        reasons
    )


def select_next(
    graph: TaskGraph,
    provenance: ProvenanceEnvelope,
) -> TaskSelection:
    candidates = [
        TaskSelectionCandidate(
            task_id=task.id,
            executable=task_executable(
                graph,
                task,
            ),
            score=task_score(
                graph,
                task,
            ),
            reasons=selection_reasons(
                graph,
                task,
            ),
            blocked_by=unresolved_blockers(
                graph,
                task.id,
            ),
            unmet_dependencies=(
                unresolved_dependencies(
                    graph,
                    task.id,
                )
            ),
        )
        for task in graph.records
    ]

    ordered = sorted(
        candidates,
        key=lambda candidate: (
            not candidate.executable,
            -candidate.score,
            candidate.task_id,
        ),
    )

    selected = next(
        (
            candidate.task_id
            for candidate in ordered
            if candidate.executable
        ),
        None,
    )

    graph_value_digest = graph_digest(
        graph
    )

    selection_body = {
        "selected_task_id": selected,
        "candidates": [
            candidate.model_dump(
                mode="json",
            )
            for candidate in ordered
        ],
        "graph_digest": (
            graph_value_digest
        ),
    }

    return TaskSelection(
        selected_task_id=selected,
        candidates=tuple(ordered),
        graph_digest=graph_value_digest,
        selection_digest=digest(
            selection_body
        ),
        provenance=provenance,
    )


def query_records(
    graph: TaskGraph,
    query: TaskQuery,
) -> tuple[TaskRecord, ...]:
    records: list[TaskRecord] = []

    for task in graph.records:
        if (
            query.include_statuses
            and task.status
            not in query.include_statuses
        ):
            continue

        if (
            query.exclude_statuses
            and task.status
            in query.exclude_statuses
        ):
            continue

        if (
            query.priority_bands
            and task.priority.band
            not in query.priority_bands
        ):
            continue

        if (
            query.task_kinds
            and task.kind
            not in query.task_kinds
        ):
            continue

        if (
            query.authority_states
            and task.authority.state
            not in query.authority_states
        ):
            continue

        executable = task_executable(
            graph,
            task,
        )

        if (
            query.executable_only
            and not executable
        ):
            continue

        if (
            not query.include_blocked
            and (
                task.status
                == TaskStatus.BLOCKED
                or unresolved_blockers(
                    graph,
                    task.id,
                )
            )
        ):
            continue

        records.append(task)

    ordered = sorted(
        records,
        key=lambda task: (
            -task_score(
                graph,
                task,
            ),
            task.id,
        ),
    )

    return tuple(
        ordered[
            : query.limit
        ]
    )


def dependency_cycle_paths(
    graph: TaskGraph,
) -> list[list[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)

    for segue in graph.segues:
        if segue.type == SegueType.DEPENDS_ON:
            adjacency[
                segue.source
            ].add(
                segue.target
            )

    state: dict[str, int] = defaultdict(int)
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(
        task_id: str,
    ) -> None:
        state[task_id] = 1
        stack.append(task_id)

        for dependency in sorted(
            adjacency.get(
                task_id,
                set(),
            )
        ):
            if state[dependency] == 0:
                visit(dependency)

            elif state[dependency] == 1:
                index = stack.index(
                    dependency
                )

                cycle = (
                    stack[index:]
                    + [dependency]
                )

                if cycle not in cycles:
                    cycles.append(cycle)

        stack.pop()
        state[task_id] = 2

    for task_id in sorted(
        task.id
        for task in graph.records
    ):
        if state[task_id] == 0:
            visit(task_id)

    return cycles


def audit_graph(
    graph: TaskGraph,
) -> dict[str, Any]:
    records = task_map(graph)

    orphan_tasks: list[str] = []
    invalid_completions: list[str] = []
    missing_evidence: list[
        dict[str, Any]
    ] = []
    unresolved_authority: list[str] = []
    dependency_cycles = dependency_cycle_paths(
        graph
    )

    connected: set[str] = set()

    for segue in graph.segues:
        connected.add(segue.source)
        connected.add(segue.target)

    for task in graph.records:
        if (
            task.id not in connected
            and task.kind
            not in {
                TaskKind.PROGRAM,
                TaskKind.CAPABILITY,
            }
        ):
            orphan_tasks.append(
                task.id
            )

        if (
            task.status
            == TaskStatus.COMPLETED
        ):
            related_attestations = [
                attestation
                for attestation
                in graph.attestations
                if (
                    attestation.task_id
                    == task.id
                    and attestation.passed
                )
            ]

            if not related_attestations:
                invalid_completions.append(
                    task.id
                )

        if task.authority.state in {
            AuthorityState.UNKNOWN,
            AuthorityState.OBSERVED,
            AuthorityState.PROPOSED,
        }:
            unresolved_authority.append(
                task.id
            )

        task_evidence = {
            evidence.id: evidence
            for evidence in graph.evidence
            if evidence.task_id == task.id
        }

        for requirement in (
            task.evidence_requirements
        ):
            if not requirement.required:
                continue

            matched = [
                evidence
                for evidence in (
                    task_evidence.values()
                )
                if evidence.kind
                == requirement.kind
            ]

            if not matched:
                missing_evidence.append(
                    {
                        "task_id": task.id,
                        "requirement_id": (
                            requirement.id
                        ),
                        "kind": (
                            requirement.kind
                        ),
                    }
                )

    duplicate_titles: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for task in graph.records:
        duplicate_titles[
            task.title.strip().lower()
        ].append(task.id)

    title_collisions = {
        title: sorted(ids)
        for title, ids
        in duplicate_titles.items()
        if len(ids) > 1
    }

    executable = [
        task.id
        for task in graph.records
        if task_executable(
            graph,
            task,
        )
    ]

    passed = not any(
        (
            invalid_completions,
            dependency_cycles,
        )
    )

    return {
        "passed": passed,
        "task_count": len(
            graph.records
        ),
        "segue_count": len(
            graph.segues
        ),
        "event_count": len(
            graph.events
        ),
        "decision_count": len(
            graph.decisions
        ),
        "evidence_count": len(
            graph.evidence
        ),
        "receipt_count": len(
            graph.receipts
        ),
        "attestation_count": len(
            graph.attestations
        ),
        "executable_tasks": sorted(
            executable
        ),
        "orphan_tasks": sorted(
            orphan_tasks
        ),
        "invalid_completions": sorted(
            invalid_completions
        ),
        "missing_evidence": sorted(
            missing_evidence,
            key=lambda value: (
                value["task_id"],
                value[
                    "requirement_id"
                ],
            ),
        ),
        "unresolved_authority": sorted(
            unresolved_authority
        ),
        "dependency_cycles": (
            dependency_cycles
        ),
        "title_collisions": (
            title_collisions
        ),
        "known_task_ids": sorted(
            records
        ),
    }


def roadmap_projection(
    graph: TaskGraph,
) -> dict[str, Any]:
    grouped: dict[
        str,
        list[TaskRecord],
    ] = defaultdict(list)

    for task in graph.records:
        grouped[
            task.priority.band
        ].append(task)

    bands: list[dict[str, Any]] = []

    for band in sorted(
        grouped,
        key=lambda value: (
            -priority_band_score(
                value
            ),
            value,
        ),
    ):
        tasks = sorted(
            grouped[band],
            key=lambda task: (
                task.priority.ordinal,
                task.id,
            ),
        )

        bands.append(
            {
                "band": band,
                "tasks": [
                    {
                        "id": task.id,
                        "kind": task.kind.value,
                        "title": task.title,
                        "status": (
                            task.status.value
                        ),
                        "authority": (
                            task.authority.state.value
                        ),
                        "ordinal": (
                            task.priority.ordinal
                        ),
                        "authority_locked": (
                            task.priority
                            .authority_locked
                        ),
                        "executable": (
                            task_executable(
                                graph,
                                task,
                            )
                        ),
                        "dependencies": (
                            dependency_ids(
                                graph,
                                task.id,
                            )
                        ),
                        "blockers": (
                            unresolved_blockers(
                                graph,
                                task.id,
                            )
                        ),
                        "outputs": (
                            task.outputs
                        ),
                        "acceptance": (
                            task.acceptance
                        ),
                    }
                    for task in tasks
                ],
            }
        )

    return {
        "graph_id": graph.graph_id,
        "bands": bands,
    }


def queue_projection(
    graph: TaskGraph,
) -> dict[str, Any]:
    provenance = ProvenanceEnvelope(
        generated_by=(
            f"{RUNTIME_ID}@{RUNTIME_VERSION}"
        ),
        generated_at=(
            "1970-01-01T00:00:00+00:00"
        ),
    )

    selection = select_next(
        graph,
        provenance,
    )

    return {
        "selected_task_id": (
            selection.selected_task_id
        ),
        "candidates": [
            candidate.model_dump(
                mode="json",
            )
            for candidate
            in selection.candidates
        ],
    }


def dependency_projection(
    graph: TaskGraph,
) -> dict[str, Any]:
    return {
        "nodes": [
            {
                "id": task.id,
                "title": task.title,
                "status": (
                    task.status.value
                ),
                "priority": (
                    task.priority.band
                ),
            }
            for task in sorted(
                graph.records,
                key=lambda task: (
                    task.id
                ),
            )
        ],
        "edges": [
            {
                "id": segue.id,
                "type": (
                    segue.type.value
                ),
                "source": (
                    segue.source
                ),
                "target": (
                    segue.target
                ),
            }
            for segue in sorted(
                graph.segues,
                key=lambda segue: (
                    segue.type.value,
                    segue.source,
                    segue.target,
                    segue.id,
                ),
            )
        ],
    }


def bottleneck_projection(
    graph: TaskGraph,
) -> dict[str, Any]:
    values = []

    for task in graph.records:
        impact = downstream_blocking_impact(
            graph,
            task.id,
        )

        unresolved = (
            unresolved_dependencies(
                graph,
                task.id,
            )
        )

        blockers = unresolved_blockers(
            graph,
            task.id,
        )

        values.append(
            {
                "task_id": task.id,
                "title": task.title,
                "blocking_impact": (
                    impact
                ),
                "unmet_dependencies": (
                    unresolved
                ),
                "blocked_by": blockers,
                "status": (
                    task.status.value
                ),
                "score": task_score(
                    graph,
                    task,
                ),
            }
        )

    return {
        "bottlenecks": sorted(
            values,
            key=lambda value: (
                -value[
                    "blocking_impact"
                ],
                -value["score"],
                value["task_id"],
            ),
        )
    }


def release_projection(
    graph: TaskGraph,
) -> dict[str, Any]:
    incomplete = [
        task
        for task in graph.records
        if task.status
        not in COMPLETION_STATUSES
    ]

    critical = [
        task
        for task in incomplete
        if task.priority.band
        in {
            "P0",
            "P1",
            "P2",
            "P2A",
        }
    ]

    return {
        "ready": not critical,
        "critical_incomplete_count": len(
            critical
        ),
        "critical_incomplete": [
            {
                "id": task.id,
                "title": task.title,
                "priority": (
                    task.priority.band
                ),
                "status": (
                    task.status.value
                ),
                "executable": (
                    task_executable(
                        graph,
                        task,
                    )
                ),
            }
            for task in sorted(
                critical,
                key=lambda task: (
                    -priority_band_score(
                        task.priority.band
                    ),
                    task.priority.ordinal,
                    task.id,
                ),
            )
        ],
    }


def agent_context_projection(
    graph: TaskGraph,
) -> dict[str, Any]:
    provenance = ProvenanceEnvelope(
        generated_by=(
            f"{RUNTIME_ID}@{RUNTIME_VERSION}"
        ),
        generated_at=(
            "1970-01-01T00:00:00+00:00"
        ),
    )

    selection = select_next(
        graph,
        provenance,
    )

    selected = (
        task_map(graph).get(
            selection.selected_task_id
        )
        if selection.selected_task_id
        else None
    )

    return {
        "governing_rule": (
            "Execute only the selected task and its "
            "explicitly required dependencies unless "
            "an accepted override decision exists."
        ),
        "selected_task": (
            selected.model_dump(
                mode="json",
            )
            if selected
            else None
        ),
        "selection": (
            selection.model_dump(
                mode="json",
            )
        ),
        "dependencies": (
            dependency_ids(
                graph,
                selected.id,
            )
            if selected
            else ()
        ),
        "blockers": (
            unresolved_blockers(
                graph,
                selected.id,
            )
            if selected
            else ()
        ),
        "audit": audit_graph(
            graph
        ),
    }


def build_projection_payload(
    graph: TaskGraph,
    projection: str,
) -> dict[str, Any]:
    if projection == "roadmap":
        return roadmap_projection(
            graph
        )

    if projection == "queue":
        return queue_projection(
            graph
        )

    if projection == "dependency_graph":
        return dependency_projection(
            graph
        )

    if projection == "bottlenecks":
        return bottleneck_projection(
            graph
        )

    if projection == "release":
        return release_projection(
            graph
        )

    if projection == "agent_context":
        return agent_context_projection(
            graph
        )

    if projection == "audit":
        return audit_graph(
            graph
        )

    raise ValueError(
        f"Unsupported projection: {projection}"
    )


def execute_request(
    request: MasterplanRequest,
) -> MasterplanResult:
    provenance = provenance_for(
        request,
        (
            "validate_contracts",
            "resolve_task_graph",
            f"execute_{request.operation}",
            "emit_deterministic_result",
        ),
    )

    graph_value_digest = graph_digest(
        request.graph
    )

    try:
        selection = None
        records: tuple[
            TaskRecord,
            ...
        ] = ()
        projection = None
        audit = None

        if request.operation == "validate":
            audit = audit_graph(
                request.graph
            )

            passed = bool(
                audit["passed"]
            )

        elif request.operation == "select_next":
            selection = select_next(
                request.graph,
                provenance,
            )

            passed = (
                selection.selected_task_id
                is not None
            )

        elif request.operation == "query":
            assert request.query is not None

            records = query_records(
                request.graph,
                request.query,
            )

            passed = True

        elif request.operation == "project":
            assert request.projection is not None

            payload = build_projection_payload(
                request.graph,
                request.projection,
            )

            projection_digest = digest(
                deterministic_projection(
                    payload
                )
            )

            projection = TaskProjection(
                operation=request.projection,
                graph_digest=(
                    graph_value_digest
                ),
                projection_digest=(
                    projection_digest
                ),
                payload=payload,
                provenance=provenance,
            )

            passed = True

        elif request.operation == "audit":
            audit = audit_graph(
                request.graph
            )

            passed = bool(
                audit["passed"]
            )

        else:
            raise ValueError(
                f"Unsupported operation: {request.operation}"
            )

        result_body = {
            "operation": request.operation,
            "passed": passed,
            "request_id": (
                request.request_id
            ),
            "graph_digest": (
                graph_value_digest
            ),
            "selection": (
                deterministic_projection(
                    selection
                )
                if selection
                else None
            ),
            "records": [
                deterministic_projection(
                    record
                )
                for record in records
            ],
            "projection": (
                deterministic_projection(
                    projection
                )
                if projection
                else None
            ),
            "audit": audit,
        }

        return MasterplanResult(
            operation=request.operation,
            passed=passed,
            request_id=request.request_id,
            graph_digest=(
                graph_value_digest
            ),
            result_digest=digest(
                result_body
            ),
            selection=selection,
            records=records,
            projection=projection,
            audit=audit,
            metrics={
                "task_count": len(
                    request.graph.records
                ),
                "segue_count": len(
                    request.graph.segues
                ),
                "event_count": len(
                    request.graph.events
                ),
                "decision_count": len(
                    request.graph.decisions
                ),
                "evidence_count": len(
                    request.graph.evidence
                ),
                "receipt_count": len(
                    request.graph.receipts
                ),
                "attestation_count": len(
                    request.graph.attestations
                ),
                "passed": passed,
            },
            provenance=provenance,
        )

    except Exception as exc:
        failure_body = {
            "request_id": (
                request.request_id
            ),
            "operation": (
                request.operation
            ),
            "exception_type": (
                type(exc).__name__
            ),
            "message": str(exc),
        }

        failure = FailureRecord(
            failure_id=(
                "masterplan-failure-"
                f"{digest(failure_body)[:20]}"
            ),
            code=(
                "prodigal.niche.masterplan."
                "runtime.failure"
            ),
            message=str(exc),
            stage=request.operation,
            recoverable=True,
            details={
                "exception_type": (
                    type(exc).__name__
                ),
            },
            provenance=provenance,
        )

        result_body = {
            "operation": request.operation,
            "passed": False,
            "request_id": (
                request.request_id
            ),
            "graph_digest": (
                graph_value_digest
            ),
            "failure": (
                deterministic_projection(
                    failure
                )
            ),
        }

        return MasterplanResult(
            operation=request.operation,
            passed=False,
            request_id=request.request_id,
            graph_digest=(
                graph_value_digest
            ),
            result_digest=digest(
                result_body
            ),
            failure=failure,
            metrics={
                "passed": False,
            },
            provenance=provenance,
        )


def load_request(
    path: Path | None,
) -> MasterplanRequest:
    if path is None:
        raw = sys.stdin.read()

    else:
        raw = path.read_text(
            encoding="utf-8",
        )

    return MasterplanRequest.model_validate_json(
        raw
    )


def write_result(
    result: MasterplanResult,
    path: Path | None,
) -> None:
    rendered = (
        json.dumps(
            result.model_dump(
                mode="json",
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    if path is None:
        print(
            rendered,
            end="",
        )

        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        rendered,
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Execute deterministic Masterplan task-graph operations."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser(
        "run"
    )

    run_parser.add_argument(
        "--input",
        type=Path,
    )

    run_parser.add_argument(
        "--output",
        type=Path,
    )

    schema_parser = subparsers.add_parser(
        "schema"
    )

    schema_parser.add_argument(
        "--output",
        type=Path,
    )

    arguments = parser.parse_args()

    if arguments.command == "run":
        request = load_request(
            arguments.input
        )

        result = execute_request(
            request
        )

        write_result(
            result,
            arguments.output,
        )

        return (
            0
            if result.passed
            else 1
        )

    if arguments.command == "schema":
        value = {
            "request": (
                MasterplanRequest
                .model_json_schema()
            ),
            "result": (
                MasterplanResult
                .model_json_schema()
            ),
            "graph": (
                TaskGraph
                .model_json_schema()
            ),
        }

        rendered = (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

        if arguments.output is None:
            print(
                rendered,
                end="",
            )

        else:
            arguments.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            arguments.output.write_text(
                rendered,
                encoding="utf-8",
            )

        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
