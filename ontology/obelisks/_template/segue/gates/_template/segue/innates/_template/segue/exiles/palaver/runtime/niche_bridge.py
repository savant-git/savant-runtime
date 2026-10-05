from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


root = Path(
    "/root/savant-runtime"
).resolve()

current_work_path = (
    root
    / "edifices"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
    / "authority"
    / "current_work.json"
)

masterplan_graph = (
    root
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

owner = "exile:niche"

specialization = "masterplan"

selected_task_schema = (
    "savant://niche/"
    "selected-task/1.1.0"
)


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        return {}

    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise RuntimeError(
            "expected JSON object: "
            + str(
                path
            )
        )

    return value


def load_current_work() -> dict[str, Any]:
    return load_json_object(
        current_work_path
    )


def load_graph() -> dict[str, Any]:
    if not masterplan_graph.is_file():
        return {
            "schema": None,
            "tasks": [],
            "source": str(
                masterplan_graph
            ),
            "available": False,
        }

    return load_json_object(
        masterplan_graph
    )


def task_rows(
    graph: dict[str, Any],
) -> list[dict[str, Any]]:
    for key in (
        "tasks",
        "nodes",
        "work",
        "items",
    ):
        value = graph.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            return [
                row
                for row in value
                if isinstance(
                    row,
                    dict,
                )
            ]

    nested = graph.get(
        "graph"
    )

    if isinstance(
        nested,
        dict,
    ):
        return task_rows(
            nested
        )

    return []


def task_id(
    row: Mapping[str, Any],
) -> str:
    return str(
        row.get("id")
        or row.get("task_id")
        or ""
    )


def task_status(
    row: Mapping[str, Any],
) -> str:
    return str(
        row.get("status")
        or row.get("state")
        or "unknown"
    ).strip().lower()


def task_title(
    row: Mapping[str, Any],
) -> str:
    return str(
        row.get("title")
        or row.get("purpose")
        or row.get("name")
        or task_id(
            row
        )
    )


def dependency_ids(
    row: Mapping[str, Any],
) -> list[str]:
    raw = (
        row.get("depends_on")
        or row.get("dependencies")
        or row.get("requires")
        or []
    )

    if not isinstance(
        raw,
        list,
    ):
        return []

    result: list[str] = []

    for item in raw:
        if isinstance(
            item,
            str,
        ):
            result.append(
                item
            )

        elif isinstance(
            item,
            Mapping,
        ):
            value = (
                item.get("id")
                or item.get("task_id")
                or item.get("target")
            )

            if value:
                result.append(
                    str(
                        value
                    )
                )

    return result


def blocker_values(
    row: Mapping[str, Any],
) -> list[str]:
    raw = (
        row.get("blockers")
        or row.get("blocked_by")
        or []
    )

    if isinstance(
        raw,
        str,
    ):
        return [
            raw
        ]

    if not isinstance(
        raw,
        list,
    ):
        return []

    result: list[str] = []

    for item in raw:
        if isinstance(
            item,
            str,
        ):
            result.append(
                item
            )

        elif isinstance(
            item,
            Mapping,
        ):
            result.append(
                str(
                    item.get("id")
                    or item.get("reason")
                    or item.get("message")
                    or item
                )
            )

    return result


def completed_ids(
    rows: list[dict[str, Any]],
) -> set[str]:
    completed_states = {
        "accepted",
        "closed",
        "complete",
        "completed",
        "done",
    }

    return {
        task_id(
            row
        )
        for row in rows
        if (
            task_id(
                row
            )
            and task_status(
                row
            )
            in completed_states
        )
    }


def priority_value(
    row: Mapping[str, Any],
) -> float:
    raw = row.get(
        "priority",
        row.get(
            "effective_priority",
            0,
        ),
    )

    try:
        return float(
            raw
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        text = str(
            raw
            or ""
        ).strip().lower()

        symbolic = {
            "critical": 1000.0,
            "highest": 1000.0,
            "p0": 1000.0,
            "p1": 900.0,
            "high": 900.0,
            "p2": 800.0,
            "p2a": 775.0,
            "medium": 500.0,
            "normal": 500.0,
            "p3": 400.0,
            "p4": 300.0,
            "p4a": 275.0,
            "low": 100.0,
        }

        return symbolic.get(
            text,
            0.0,
        )


def executable_frontier(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    completed = completed_ids(
        rows
    )

    excluded_states = {
        "accepted",
        "cancelled",
        "canceled",
        "closed",
        "complete",
        "completed",
        "done",
        "rejected",
        "superseded",
    }

    frontier: list[
        dict[str, Any]
    ] = []

    for row in rows:
        identity = task_id(
            row
        )

        if not identity:
            continue

        if (
            task_status(
                row
            )
            in excluded_states
        ):
            continue

        blockers = blocker_values(
            row
        )

        if blockers:
            continue

        dependencies = dependency_ids(
            row
        )

        if any(
            dependency
            not in completed
            for dependency
            in dependencies
        ):
            continue

        frontier.append(
            row
        )

    frontier.sort(
        key=lambda row: (
            -priority_value(
                row
            ),
            task_id(
                row
            ),
        )
    )

    return frontier


def active_governing_task() -> dict[str, Any] | None:
    current_work = (
        load_current_work()
    )

    task = current_work.get(
        "active_governing_task"
    )

    if not isinstance(
        task,
        dict,
    ):
        return None

    if not task_id(
        task
    ):
        return None

    return dict(
        task
    )


def current_work_authority() -> dict[str, Any]:
    current_work = (
        load_current_work()
    )

    value = current_work.get(
        "authority"
    )

    if isinstance(
        value,
        dict,
    ):
        return dict(
            value
        )

    return {}


def normalized_task(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    result = dict(
        row
    )

    identity = task_id(
        row
    )

    result[
        "task_id"
    ] = identity

    result.setdefault(
        "id",
        identity,
    )

    result[
        "title"
    ] = task_title(
        row
    )

    result[
        "status"
    ] = task_status(
        row
    )

    result[
        "dependencies"
    ] = dependency_ids(
        row
    )

    result[
        "blockers"
    ] = blocker_values(
        row
    )

    return result


def select_current_governing_task(
) -> dict[str, Any] | None:
    task = active_governing_task()

    if task is None:
        return None

    normalized = normalized_task(
        task
    )

    authority = (
        current_work_authority()
    )

    selection = {
        "strategy": (
            "explicit-active-governing-task"
        ),
        "action": (
            "continue_active"
        ),
        "priority": (
            normalized.get(
                "priority"
            )
        ),
        "priority_value": (
            priority_value(
                normalized
            )
        ),
        "authority_locked": bool(
            normalized.get(
                "authority_locked",
                False,
            )
        ),
        "dependencies_satisfied": True,
        "dependency_status": {},
        "blockers": (
            normalized.get(
                "blockers",
                [],
            )
        ),
    }

    projection = {
        "schema": (
            selected_task_schema
        ),
        "owner": owner,
        "specialization": (
            specialization
        ),
        "source": str(
            current_work_path.relative_to(
                root
            )
        ),
        "source_kind": (
            "niche-current-work"
        ),
        "source_authority": (
            authority
        ),
        "task": normalized,
        "selection": selection,
        "authoritative": (
            False
        ),
        "authority_effect": (
            "none"
        ),
        "mutation": False,
    }

    projection[
        "digest"
    ] = digest(
        {
            "owner": owner,
            "source": (
                projection[
                    "source"
                ]
            ),
            "source_authority": (
                authority
            ),
            "task": (
                normalized
            ),
            "selection": (
                selection
            ),
        }
    )

    return projection


def select_graph_task(
) -> dict[str, Any] | None:
    graph = load_graph()

    rows = task_rows(
        graph
    )

    frontier = executable_frontier(
        rows
    )

    if not frontier:
        return None

    selected = frontier[
        0
    ]

    task = normalized_task(
        selected
    )

    completed = completed_ids(
        rows
    )

    dependencies = dependency_ids(
        selected
    )

    by_id = {
        task_id(
            row
        ): row
        for row in rows
        if task_id(
            row
        )
    }

    dependency_status: dict[
        str,
        str
    ] = {}

    for dependency in dependencies:
        dependency_status[
            dependency
        ] = (
            task_status(
                by_id[
                    dependency
                ]
            )
            if dependency
            in by_id
            else "unknown"
        )

    selection = {
        "strategy": (
            "legacy-executable-frontier"
        ),
        "action": (
            "continue_active"
            if task_status(
                selected
            )
            in {
                "active",
                "in_progress",
                "in-progress",
                "working",
            }
            else "start_actionable"
        ),
        "priority": (
            selected.get(
                "priority",
                selected.get(
                    "effective_priority"
                ),
            )
        ),
        "priority_value": (
            priority_value(
                selected
            )
        ),
        "dependencies_satisfied": all(
            dependency
            in completed
            for dependency
            in dependencies
        ),
        "dependency_status": (
            dependency_status
        ),
        "blockers": (
            blocker_values(
                selected
            )
        ),
        "frontier_count": len(
            frontier
        ),
    }

    projection = {
        "schema": (
            selected_task_schema
        ),
        "owner": owner,
        "specialization": (
            specialization
        ),
        "source": str(
            masterplan_graph.relative_to(
                root
            )
        ),
        "source_kind": (
            "legacy-masterplan-graph"
        ),
        "task": task,
        "selection": selection,
        "authoritative": False,
        "authority_effect": "none",
        "mutation": False,
    }

    projection[
        "digest"
    ] = digest(
        projection
    )

    return projection


def select_next_task(
) -> dict[str, Any] | None:
    current = (
        select_current_governing_task()
    )

    if current is not None:
        return current

    return select_graph_task()


def project_task_context(
    limit: int = 9,
) -> dict[str, Any]:
    current = (
        select_current_governing_task()
    )

    graph = load_graph()

    rows = task_rows(
        graph
    )

    frontier = executable_frontier(
        rows
    )

    projected_frontier: list[
        dict[str, Any]
    ] = []

    if current is not None:
        task = current[
            "task"
        ]

        projected_frontier.append(
            {
                "id": (
                    task[
                        "task_id"
                    ]
                ),
                "title": (
                    task[
                        "title"
                    ]
                ),
                "status": (
                    task[
                        "status"
                    ]
                ),
                "priority": (
                    task.get(
                        "priority"
                    )
                ),
                "dependencies": (
                    task.get(
                        "dependencies",
                        [],
                    )
                ),
                "selection_strategy": (
                    current[
                        "selection"
                    ][
                        "strategy"
                    ]
                ),
            }
        )

    for row in frontier:
        identity = task_id(
            row
        )

        if any(
            existing[
                "id"
            ]
            == identity
            for existing
            in projected_frontier
        ):
            continue

        projected_frontier.append(
            {
                "id": identity,
                "title": (
                    task_title(
                        row
                    )
                ),
                "status": (
                    task_status(
                        row
                    )
                ),
                "priority": (
                    row.get(
                        "priority",
                        row.get(
                            "effective_priority"
                        ),
                    )
                ),
                "dependencies": (
                    dependency_ids(
                        row
                    )
                ),
                "selection_strategy": (
                    "legacy-executable-frontier"
                ),
            }
        )

    projected_frontier = (
        projected_frontier[
            :max(
                0,
                int(
                    limit
                ),
            )
        ]
    )

    return {
        "owner": "niche",
        "specialization": (
            specialization
        ),
        "source": (
            str(
                current_work_path.relative_to(
                    root
                )
            )
            if current is not None
            else str(
                masterplan_graph.relative_to(
                    root
                )
            )
        ),
        "available": (
            current is not None
            or masterplan_graph.is_file()
        ),
        "current_work_available": (
            current_work_path.is_file()
        ),
        "legacy_graph_available": (
            masterplan_graph.is_file()
        ),
        "legacy_graph_task_count": len(
            rows
        ),
        "frontier_count": len(
            projected_frontier
        ),
        "frontier": (
            projected_frontier
        ),
        "authority_effect": "none",
    }


def prompt_block(
    limit: int = 9,
) -> str:
    projection = (
        project_task_context(
            limit=limit
        )
    )

    if not projection[
        "available"
    ]:
        return ""

    lines = [
        "NICHE TASK CONTEXT",
        (
            "Source: "
            + str(
                projection[
                    "source"
                ]
            )
        ),
        (
            "This is a non-mutating "
            "projection of Niche task "
            "governance."
        ),
        (
            "Executable frontier: "
            + str(
                projection[
                    "frontier_count"
                ]
            )
        ),
    ]

    frontier = projection[
        "frontier"
    ]

    if not frontier:
        lines.append(
            "Frontier: none projected."
        )

        return "\n".join(
            lines
        )

    lines.append(
        "Frontier:"
    )

    for row in frontier:
        line = (
            "- "
            + str(
                row[
                    "id"
                ]
            )
            + ": "
            + str(
                row[
                    "title"
                ]
            )
            + " ["
            + str(
                row[
                    "status"
                ]
            )
            + "]"
        )

        if (
            row.get(
                "priority"
            )
            is not None
        ):
            line += (
                " priority="
                + str(
                    row[
                        "priority"
                    ]
                )
            )

        lines.append(
            line
        )

    return "\n".join(
        lines
    )


def integration_status() -> dict[str, Any]:
    selected = (
        select_next_task()
    )

    return {
        "owner": "palaver",
        "delegates_task_governance_to": (
            "niche"
        ),
        "specialization": (
            specialization
        ),
        "source": (
            selected.get(
                "source"
            )
            if selected
            else None
        ),
        "available": (
            selected is not None
        ),
        "selected_task_id": (
            selected.get(
                "task",
                {}
            ).get(
                "task_id"
            )
            if selected
            else None
        ),
        "mutation": False,
        "authority_effect": "none",
    }


def task_system_instruction(
    task_projection: Mapping[
        str,
        Any,
    ],
) -> str:
    task = task_projection.get(
        "task"
    )

    if not isinstance(
        task,
        Mapping,
    ):
        raise RuntimeError(
            "Niche task projection "
            "has no task"
        )

    identity = str(
        task.get(
            "task_id"
        )
        or task.get(
            "id"
        )
        or ""
    )

    if not identity:
        raise RuntimeError(
            "Niche task projection "
            "has no task identity"
        )

    return (
        "NICHE SELECTED TASK\n"
        "Niche selected this task from "
        "its current task-governance state.\n"
        "Task ownership remains with Niche.\n"
        "Do not substitute another task.\n"
        "Do not invent authority, dependencies, "
        "blockers, completion evidence, or "
        "task transitions.\n"
        "The source authority state must be "
        "preserved exactly as supplied.\n"
        "Focus only on the selected task.\n\n"
        + canonical_json(
            task_projection
        )
    )


def task_context(
    task_projection: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    if not isinstance(
        task_projection,
        Mapping,
    ):
        raise RuntimeError(
            "Niche task projection "
            "must be an object"
        )

    result = dict(
        task_projection
    )

    result[
        "schema"
    ] = selected_task_schema

    result[
        "owner"
    ] = owner

    result[
        "authority_effect"
    ] = "none"

    result[
        "mutation"
    ] = False

    return result
