#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

ROADMAP_PATH = (
    ROOT
    / "docs"
    / "SAVANT_MASTER_TASKS.md"
)

AGENT_CONTEXT_PATH = (
    ROOT
    / "runtime"
    / "masterplan"
    / "gate"
    / "agent-context.json"
)

LEASE_PATH = (
    ROOT
    / "runtime"
    / "masterplan"
    / "gate"
    / "active-lease.json"
)

EVENT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "events"
)

DECISION_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "decisions"
)

EVIDENCE_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "evidence"
)

RECEIPT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "receipts"
)

ATTESTATION_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "attestations"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "integrity"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}

COMPLETION_STATES = {
    "completed",
    "archived",
    "superseded",
}

EXECUTABLE_STATES = {
    "accepted",
    "ready",
    "active",
    "reopened",
}

ACCEPTED_AUTHORITY_STATES = {
    "accepted",
    "authoritative",
}

COLLECTIONS = {
    "events": EVENT_ROOT,
    "decisions": DECISION_ROOT,
    "evidence": EVIDENCE_ROOT,
    "receipts": RECEIPT_ROOT,
    "attestations": ATTESTATION_ROOT,
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(
    value: Any,
) -> bytes:
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


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def task_map(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = graph.get(
        "records"
    )

    if not isinstance(records, list):
        raise ValueError(
            "Task graph records are invalid."
        )

    result: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise ValueError(
                "Task graph contains an invalid record."
            )

        identifier = record.get(
            "id"
        )

        if not isinstance(identifier, str):
            raise ValueError(
                "Task record identifier is missing."
            )

        if identifier in result:
            raise ValueError(
                f"Duplicate task record: {identifier}"
            )

        result[identifier] = record

    return result


def collection_map(
    graph: dict[str, Any],
    name: str,
) -> dict[str, dict[str, Any]]:
    values = graph.get(
        name,
        [],
    )

    if not isinstance(values, list):
        raise ValueError(
            f"Task graph {name} collection is invalid."
        )

    result: dict[str, dict[str, Any]] = {}

    for value in values:
        if not isinstance(value, dict):
            raise ValueError(
                f"Task graph {name} contains an invalid record."
            )

        identifier = value.get(
            "id"
        )

        if not isinstance(identifier, str):
            raise ValueError(
                f"Task graph {name} record has no identifier."
            )

        if identifier in result:
            raise ValueError(
                f"Duplicate {name} record: {identifier}"
            )

        result[identifier] = value

    return result


def external_collection_map(
    root: Path,
) -> dict[str, dict[str, Any]]:
    if not root.is_dir():
        return {}

    result: dict[str, dict[str, Any]] = {}

    for path in sorted(
        root.glob("*.json"),
        key=lambda candidate: candidate.name,
    ):
        if not path.is_file():
            continue

        value = load_json(path)

        identifier = value.get(
            "id"
        )

        if not isinstance(identifier, str):
            raise ValueError(
                f"External record has no identifier: {path}"
            )

        if identifier in result:
            raise ValueError(
                f"Duplicate external record: {identifier}"
            )

        result[identifier] = value

    return result


def compare_collection(
    graph: dict[str, Any],
    name: str,
    root: Path,
) -> dict[str, Any]:
    internal = collection_map(
        graph,
        name,
    )

    external = external_collection_map(
        root
    )

    missing_external = sorted(
        set(internal)
        - set(external)
    )

    missing_internal = sorted(
        set(external)
        - set(internal)
    )

    mismatched: list[
        dict[str, Any]
    ] = []

    for identifier in sorted(
        set(internal)
        & set(external)
    ):
        internal_digest = digest(
            deterministic_projection(
                internal[identifier]
            )
        )

        external_digest = digest(
            deterministic_projection(
                external[identifier]
            )
        )

        if internal_digest != external_digest:
            mismatched.append(
                {
                    "id": identifier,
                    "internal_digest": (
                        internal_digest
                    ),
                    "external_digest": (
                        external_digest
                    ),
                }
            )

    return {
        "passed": not any(
            (
                missing_external,
                missing_internal,
                mismatched,
            )
        ),
        "graph_count": len(internal),
        "external_count": len(external),
        "missing_external": (
            missing_external
        ),
        "missing_internal": (
            missing_internal
        ),
        "mismatched": mismatched,
        "root": relative_path(
            root
        ),
    }


def dependency_graph(
    graph: dict[str, Any],
) -> dict[str, set[str]]:
    adjacency: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for segue in graph.get(
        "segues",
        [],
    ):
        if not isinstance(segue, dict):
            continue

        if segue.get("type") != "depends_on":
            continue

        source = segue.get("source")
        target = segue.get("target")

        if (
            isinstance(source, str)
            and isinstance(target, str)
        ):
            adjacency[source].add(target)

    return adjacency


def dependency_cycles(
    graph: dict[str, Any],
) -> list[list[str]]:
    adjacency = dependency_graph(
        graph
    )

    state: dict[
        str,
        int,
    ] = defaultdict(int)

    stack: list[str] = []
    cycles: list[
        list[str]
    ] = []

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
                    cycles.append(
                        cycle
                    )

        stack.pop()
        state[task_id] = 2

    for task_id in sorted(
        task_map(graph)
    ):
        if state[task_id] == 0:
            visit(task_id)

    return cycles


def unresolved_dependencies(
    graph: dict[str, Any],
    task_id: str,
) -> list[str]:
    records = task_map(
        graph
    )

    adjacency = dependency_graph(
        graph
    )

    unresolved: list[str] = []

    for dependency in sorted(
        adjacency.get(
            task_id,
            set(),
        )
    ):
        record = records.get(
            dependency
        )

        if (
            record is None
            or record.get(
                "status"
            )
            not in COMPLETION_STATES
        ):
            unresolved.append(
                dependency
            )

    return unresolved


def passing_attestation_exists(
    graph: dict[str, Any],
    task_id: str,
) -> bool:
    attestations = graph.get(
        "attestations",
        [],
    )

    if not isinstance(
        attestations,
        list,
    ):
        return False

    return any(
        isinstance(attestation, dict)
        and attestation.get(
            "task_id"
        )
        == task_id
        and attestation.get(
            "passed"
        )
        is True
        for attestation in attestations
    )


def audit_tasks(
    graph: dict[str, Any],
) -> dict[str, Any]:
    records = task_map(
        graph
    )

    invalid_completion: list[str] = []
    invalid_active: list[
        dict[str, Any]
    ] = []
    unresolved_authority: list[str] = []
    output_issues: list[
        dict[str, Any]
    ] = []
    duplicate_titles: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for task_id, record in sorted(
        records.items()
    ):
        status = record.get(
            "status"
        )

        authority = record.get(
            "authority"
        )

        authority_state = (
            authority.get(
                "state"
            )
            if isinstance(
                authority,
                dict,
            )
            else None
        )

        if status == "completed":
            if not passing_attestation_exists(
                graph,
                task_id,
            ):
                invalid_completion.append(
                    task_id
                )

        if status in EXECUTABLE_STATES:
            unmet = unresolved_dependencies(
                graph,
                task_id,
            )

            if unmet:
                invalid_active.append(
                    {
                        "task_id": task_id,
                        "status": status,
                        "unresolved_dependencies": (
                            unmet
                        ),
                    }
                )

        if authority_state not in (
            ACCEPTED_AUTHORITY_STATES
            | {
                "proposed",
                "observed",
                "unknown",
                "rejected",
                "superseded",
            }
        ):
            unresolved_authority.append(
                task_id
            )

        outputs = record.get(
            "outputs",
            [],
        )

        if not isinstance(outputs, list):
            output_issues.append(
                {
                    "task_id": task_id,
                    "code": (
                        "task.outputs_invalid"
                    ),
                }
            )

        duplicate_titles[
            str(
                record.get(
                    "title",
                    "",
                )
            ).strip().lower()
        ].append(task_id)

    title_collisions = {
        title: sorted(
            identifiers
        )
        for title, identifiers
        in sorted(
            duplicate_titles.items()
        )
        if (
            title
            and len(
                identifiers
            )
            > 1
        )
    }

    return {
        "passed": not any(
            (
                invalid_completion,
                invalid_active,
                unresolved_authority,
                output_issues,
            )
        ),
        "invalid_completion": (
            invalid_completion
        ),
        "invalid_active": (
            invalid_active
        ),
        "unresolved_authority": (
            unresolved_authority
        ),
        "output_issues": output_issues,
        "title_collisions": (
            title_collisions
        ),
    }


def audit_references(
    graph: dict[str, Any],
) -> dict[str, Any]:
    tasks = task_map(
        graph
    )

    issues: list[
        dict[str, Any]
    ] = []

    for segue in graph.get(
        "segues",
        [],
    ):
        if not isinstance(segue, dict):
            issues.append(
                {
                    "collection": "segues",
                    "code": (
                        "reference.invalid_record"
                    ),
                }
            )

            continue

        source = segue.get(
            "source"
        )

        target = segue.get(
            "target"
        )

        if source not in tasks:
            issues.append(
                {
                    "collection": "segues",
                    "record_id": segue.get(
                        "id"
                    ),
                    "code": (
                        "reference.unknown_source"
                    ),
                    "value": source,
                }
            )

        if target not in tasks:
            issues.append(
                {
                    "collection": "segues",
                    "record_id": segue.get(
                        "id"
                    ),
                    "code": (
                        "reference.unknown_target"
                    ),
                    "value": target,
                }
            )

    for collection_name in (
        "events",
        "evidence",
        "receipts",
        "attestations",
    ):
        for record in graph.get(
            collection_name,
            [],
        ):
            if not isinstance(record, dict):
                continue

            task_id = record.get(
                "task_id"
            )

            if task_id not in tasks:
                issues.append(
                    {
                        "collection": (
                            collection_name
                        ),
                        "record_id": record.get(
                            "id"
                        ),
                        "code": (
                            "reference.unknown_task"
                        ),
                        "value": task_id,
                    }
                )

    for decision in graph.get(
        "decisions",
        [],
    ):
        if not isinstance(
            decision,
            dict,
        ):
            continue

        subject = decision.get(
            "subject"
        )

        if subject not in tasks:
            issues.append(
                {
                    "collection": "decisions",
                    "record_id": decision.get(
                        "id"
                    ),
                    "code": (
                        "reference.unknown_subject"
                    ),
                    "value": subject,
                }
            )

    return {
        "passed": not issues,
        "issues": issues,
    }


def audit_roadmap(
    graph: dict[str, Any],
) -> dict[str, Any]:
    if not ROADMAP_PATH.is_file():
        return {
            "passed": False,
            "exists": False,
            "path": relative_path(
                ROADMAP_PATH
            ),
            "issues": [
                {
                    "code": (
                        "roadmap.missing"
                    ),
                }
            ],
        }

    text = ROADMAP_PATH.read_text(
        encoding="utf-8",
    )

    graph_value_digest = digest(
        deterministic_projection(
            graph
        )
    )

    marker = (
        "Deterministic graph digest: "
        f"`{graph_value_digest}`"
    )

    missing_task_ids = [
        task_id
        for task_id in sorted(
            task_map(graph)
        )
        if task_id not in text
    ]

    issues: list[
        dict[str, Any]
    ] = []

    if marker not in text:
        issues.append(
            {
                "code": (
                    "roadmap.digest_mismatch"
                ),
                "expected_marker": marker,
            }
        )

    if missing_task_ids:
        issues.append(
            {
                "code": (
                    "roadmap.tasks_missing"
                ),
                "task_ids": (
                    missing_task_ids
                ),
            }
        )

    return {
        "passed": not issues,
        "exists": True,
        "path": relative_path(
            ROADMAP_PATH
        ),
        "sha256": sha256_path(
            ROADMAP_PATH
        ),
        "issues": issues,
    }


def parse_datetime(
    value: Any,
) -> dt.datetime | None:
    if not isinstance(value, str):
        return None

    try:
        parsed = dt.datetime.fromisoformat(
            value
        )

    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=dt.timezone.utc
        )

    return parsed


def audit_gate(
    graph: dict[str, Any],
) -> dict[str, Any]:
    graph_value_digest = digest(
        deterministic_projection(
            graph
        )
    )

    context_result: dict[
        str,
        Any,
    ]

    if not AGENT_CONTEXT_PATH.is_file():
        context_result = {
            "passed": False,
            "exists": False,
            "issues": [
                {
                    "code": (
                        "gate.context_missing"
                    ),
                }
            ],
        }

    else:
        context = load_json(
            AGENT_CONTEXT_PATH
        )

        issues = []

        context_graph_digest = (
            context.get(
                "graph",
                {}
            ).get(
                "digest"
            )
            if isinstance(
                context.get(
                    "graph"
                ),
                dict,
            )
            else None
        )

        if (
            context_graph_digest
            != graph_value_digest
        ):
            issues.append(
                {
                    "code": (
                        "gate.context_stale"
                    ),
                    "expected": (
                        graph_value_digest
                    ),
                    "actual": (
                        context_graph_digest
                    ),
                }
            )

        context_result = {
            "passed": not issues,
            "exists": True,
            "path": relative_path(
                AGENT_CONTEXT_PATH
            ),
            "issues": issues,
        }

    lease_result: dict[
        str,
        Any,
    ]

    if not LEASE_PATH.is_file():
        lease_result = {
            "passed": True,
            "exists": False,
            "active": False,
            "issues": [],
        }

    else:
        lease = load_json(
            LEASE_PATH
        )

        issues = []

        expires_at = parse_datetime(
            lease.get(
                "expires_at"
            )
        )

        if (
            expires_at is None
            or expires_at
            <= dt.datetime.now(
                dt.timezone.utc
            )
        ):
            issues.append(
                {
                    "code": (
                        "gate.lease_expired"
                    ),
                }
            )

        if (
            lease.get(
                "graph_digest"
            )
            != graph_value_digest
        ):
            issues.append(
                {
                    "code": (
                        "gate.lease_graph_mismatch"
                    ),
                }
            )

        if lease.get(
            "passed"
        ) is not True:
            issues.append(
                {
                    "code": (
                        "gate.lease_not_admitted"
                    ),
                }
            )

        lease_result = {
            "passed": not issues,
            "exists": True,
            "active": not issues,
            "path": relative_path(
                LEASE_PATH
            ),
            "lease_id": lease.get(
                "lease_id"
            ),
            "issues": issues,
        }

    return {
        "passed": (
            context_result[
                "passed"
            ]
            and lease_result[
                "passed"
            ]
        ),
        "context": context_result,
        "lease": lease_result,
    }


def build_integrity_report(
    graph: dict[str, Any],
) -> dict[str, Any]:
    collections = {
        name: compare_collection(
            graph,
            name,
            root,
        )
        for name, root
        in COLLECTIONS.items()
    }

    cycles = dependency_cycles(
        graph
    )

    task_audit = audit_tasks(
        graph
    )

    reference_audit = audit_references(
        graph
    )

    roadmap_audit = audit_roadmap(
        graph
    )

    gate_audit = audit_gate(
        graph
    )

    passed = all(
        (
            not cycles,
            task_audit[
                "passed"
            ],
            reference_audit[
                "passed"
            ],
            roadmap_audit[
                "passed"
            ],
            gate_audit[
                "passed"
            ],
            all(
                result[
                    "passed"
                ]
                for result
                in collections.values()
            ),
        )
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "integrity-audit/1.0.0"
        ),
        "operation": (
            "audit_masterplan_integrity"
        ),
        "generated_at": utc_now(),
        "passed": passed,
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "digest": digest(
                deterministic_projection(
                    graph
                )
            ),
            "task_count": len(
                task_map(
                    graph
                )
            ),
            "segue_count": len(
                graph.get(
                    "segues",
                    [],
                )
            ),
        },
        "dependency_cycles": cycles,
        "tasks": task_audit,
        "references": (
            reference_audit
        ),
        "collections": collections,
        "roadmap": roadmap_audit,
        "gate": gate_audit,
        "statistics": {
            "collection_count": len(
                collections
            ),
            "collection_passed_count": sum(
                value[
                    "passed"
                ]
                for value
                in collections.values()
            ),
            "dependency_cycle_count": len(
                cycles
            ),
            "invalid_completion_count": len(
                task_audit[
                    "invalid_completion"
                ]
            ),
            "invalid_active_count": len(
                task_audit[
                    "invalid_active"
                ]
            ),
            "reference_issue_count": len(
                reference_audit[
                    "issues"
                ]
            ),
            "roadmap_issue_count": len(
                roadmap_audit[
                    "issues"
                ]
            ),
            "gate_issue_count": (
                len(
                    gate_audit[
                        "context"
                    ][
                        "issues"
                    ]
                )
                + len(
                    gate_audit[
                        "lease"
                    ][
                        "issues"
                    ]
                )
            ),
        },
    }

    result["digest"] = digest(
        deterministic_projection(
            result
        )
    )

    return result


def render_markdown(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Masterplan Integrity Audit",
        "",
        (
            f"- Generated: "
            f"`{result['generated_at']}`"
        ),
        (
            f"- Passed: "
            f"**{result['passed']}**"
        ),
        (
            f"- Graph digest: "
            f"`{result['graph']['digest']}`"
        ),
        (
            f"- Tasks: "
            f"**{result['graph']['task_count']}**"
        ),
        (
            f"- Segues: "
            f"**{result['graph']['segue_count']}**"
        ),
        "",
        "## Checks",
        "",
        (
            f"- Dependency cycles: "
            f"**{len(result['dependency_cycles'])}**"
        ),
        (
            f"- Task integrity: "
            f"**{result['tasks']['passed']}**"
        ),
        (
            f"- Reference integrity: "
            f"**{result['references']['passed']}**"
        ),
        (
            f"- Roadmap integrity: "
            f"**{result['roadmap']['passed']}**"
        ),
        (
            f"- Gate integrity: "
            f"**{result['gate']['passed']}**"
        ),
        "",
        "## Collections",
        "",
    ]

    for name, value in sorted(
        result[
            "collections"
        ].items()
    ):
        lines.append(
            (
                f"- `{name}`: "
                f"**{value['passed']}** "
                f"({value['graph_count']} graph / "
                f"{value['external_count']} external)"
            )
        )

    lines.extend(
        [
            "",
            (
                f"- Audit digest: "
                f"`{result['digest']}`"
            ),
            "",
        ]
    )

    return "\n".join(
        lines
    )


def persist_report(
    result: dict[str, Any],
) -> dict[str, str]:
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        REPORT_ROOT
        / f"{run_id}__integrity.json"
    )

    markdown_path = (
        REPORT_ROOT
        / f"{run_id}__integrity.md"
    )

    latest_json = (
        REPORT_ROOT
        / "latest.json"
    )

    latest_markdown = (
        REPORT_ROOT
        / "latest.md"
    )

    atomic_write_json(
        json_path,
        result,
    )

    atomic_write_json(
        latest_json,
        result,
    )

    rendered = render_markdown(
        result
    )

    atomic_write_text(
        markdown_path,
        rendered,
    )

    atomic_write_text(
        latest_markdown,
        rendered,
    )

    return {
        "json": str(
            json_path
        ),
        "markdown": str(
            markdown_path
        ),
        "latest_json": str(
            latest_json
        ),
        "latest_markdown": str(
            latest_markdown
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Masterplan authority, immutable records, "
            "dependencies, projections, gate state, and completion integrity."
        )
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        if not GRAPH_PATH.is_file():
            raise FileNotFoundError(
                GRAPH_PATH
            )

        graph = load_json(
            GRAPH_PATH
        )

        result = build_integrity_report(
            graph
        )

        reports = persist_report(
            result
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "audit_masterplan_integrity"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            {
                **result,
                "reports": reports,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not result[
            "passed"
        ]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
