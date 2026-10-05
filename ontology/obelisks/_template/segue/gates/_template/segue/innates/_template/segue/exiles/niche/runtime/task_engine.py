#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from living_task import (
    NicheTaskError,
    PRIORITY_ORDER,
    TASK_STATES,
    canonical_json,
    digest,
    engine as living_engine,
    normalize_sequence,
    utc_now,
)


owner = "exile:niche"
authority_effect = "none"

schema = "savant://runtime/niche/task-engine/2.0.0"

default_root = Path(
    "/root/savant-runtime"
)

default_db = (
    default_root
    / "runtime/niche/tasks.sqlite3"
)

taskboard_slot = "niche.taskboard"


priority_weight = {
    "critical": 1000,
    "high": 700,
    "normal": 400,
    "low": 150,
    "deferred": 0,
}


editable_scalars = {
    "purpose":
        "purpose",

    "priority":
        "priority",

    "completion_condition":
        "completion_condition",
}


editable_json = {
    "affected_instances":
        "affected_instances_json",

    "compatibility_obligations":
        "compatibility_obligations_json",

    "validation_budget":
        "validation_budget_json",

    "blockers":
        "blockers_json",

    "implementation_references":
        "implementation_references_json",

    "decomposition_children":
        "decomposition_children_json",
}


class NicheTaskEngineError(
    RuntimeError
):
    pass


def parse_time(
    value: Any,
) -> datetime | None:
    if value in (
        None,
        "",
    ):
        return None

    if not isinstance(
        value,
        str,
    ):
        raise NicheTaskEngineError(
            (
                "timestamp must be an "
                "ISO-8601 string"
            )
        )

    text = value.strip()

    if text.endswith(
        "Z"
    ):
        text = (
            text[:-1]
            + "+00:00"
        )

    try:
        parsed = (
            datetime.fromisoformat(
                text
            )
        )

    except ValueError as exc:
        raise NicheTaskEngineError(
            (
                "invalid timestamp: "
                + str(
                    value
                )
            )
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=
                timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def json_clone(
    value: Any,
) -> Any:
    return json.loads(
        canonical_json(
            value
        )
    )


def normalize_labels(
    value: Any,
) -> list[str]:
    return list(
        normalize_sequence(
            value
        )
    )


def taskboard_meta(
    extension_slots: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    raw = extension_slots.get(
        taskboard_slot,
        {},
    )

    if isinstance(
        raw,
        Mapping,
    ):
        return dict(
            raw
        )

    return {}


def estimate_minutes(
    meta: Mapping[
        str,
        Any,
    ],
) -> int:
    raw = meta.get(
        "estimate_minutes",
        30,
    )

    try:
        value = int(
            raw
        )

    except (
        TypeError,
        ValueError,
    ):
        return 30

    return max(
        1,
        min(
            value,
            1000000,
        ),
    )


def cycle_paths(
    graph: Mapping[
        str,
        Sequence[str],
    ],
) -> tuple[
    tuple[str, ...],
    ...,
]:
    state: dict[
        str,
        int,
    ] = {}

    stack: list[str] = []

    cycles: set[
        tuple[str, ...]
    ] = set()

    def visit(
        node: str,
    ) -> None:
        marker = state.get(
            node,
            0,
        )

        if marker == 2:
            return

        if marker == 1:
            if node in stack:
                index = stack.index(
                    node
                )

                cycles.add(
                    tuple(
                        stack[index:]
                        + [
                            node
                        ]
                    )
                )

            return

        state[
            node
        ] = 1

        stack.append(
            node
        )

        for dependency in (
            graph.get(
                node,
                (),
            )
        ):
            visit(
                dependency
            )

        stack.pop()

        state[
            node
        ] = 2

    for node in sorted(
        graph
    ):
        visit(
            node
        )

    return tuple(
        sorted(
            cycles
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SearchResult:
    task_id: str
    rank: float


class NicheTaskEngine:
    def __init__(
        self,
        db_path: str
        | Path = default_db,
    ) -> None:
        self.runtime = (
            living_engine(
                db_path
            )
        )

        self.db_path = (
            self.runtime.db_path
        )

        self._initialize_projection_indexes()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        return (
            self.runtime._connect()
        )

    def _initialize_projection_indexes(
        self,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE VIRTUAL TABLE
                    IF NOT EXISTS task_search
                    USING fts5(
                        task_id UNINDEXED,
                        purpose,
                        owner,
                        jurisdiction,
                        labels,
                        notes
                    )
                    """
                )

        except sqlite3.OperationalError:
            pass

    def _rebuild_search_index(
        self,
    ) -> bool:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    DELETE FROM task_search
                    """
                )

                for task in (
                    self.runtime.tasks()
                ):
                    meta = taskboard_meta(
                        task.extension_slots
                    )

                    connection.execute(
                        """
                        INSERT INTO task_search (
                            task_id,
                            purpose,
                            owner,
                            jurisdiction,
                            labels,
                            notes
                        )
                        VALUES (
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        )
                        """,
                        (
                            task.task_id,
                            task.purpose,
                            task.owner,
                            task.jurisdiction,
                            " ".join(
                                normalize_labels(
                                    meta.get(
                                        "labels"
                                    )
                                )
                            ),
                            str(
                                meta.get(
                                    "notes",
                                    "",
                                )
                            ),
                        ),
                    )

            return True

        except sqlite3.OperationalError:
            return False

    def public_task(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        task = self.runtime.get(
            task_id
        )

        meta = taskboard_meta(
            task.extension_slots
        )

        unsatisfied = list(
            self.runtime
            .unsatisfied_dependencies(
                task_id
            )
        )

        dependents = list(
            self.runtime
            .reverse_dependencies()
            .get(
                task_id,
                (),
            )
        )

        due_at = (
            parse_time(
                meta.get(
                    "due_at"
                )
            )
            if meta.get(
                "due_at"
            )
            else None
        )

        now = datetime.now(
            timezone.utc
        )

        overdue = bool(
            due_at
            and due_at
            < now
            and task.status
            not in {
                "completed",
                "rejected",
                "superseded",
            }
        )

        ready = bool(
            task.status
            in {
                "accepted",
                "ready",
            }
            and not task.blockers
            and not unsatisfied
        )

        payload = (
            task.authoritative_projection()
        )

        payload.update(
            {
                "title":
                    str(
                        meta.get(
                            "title"
                        )
                        or task.purpose
                    ),

                "labels":
                    normalize_labels(
                        meta.get(
                            "labels"
                        )
                    ),

                "notes":
                    str(
                        meta.get(
                            "notes",
                            "",
                        )
                    ),

                "assignee":
                    meta.get(
                        "assignee"
                    ),

                "due_at":
                    meta.get(
                        "due_at"
                    ),

                "start_at":
                    meta.get(
                        "start_at"
                    ),

                "lease_until":
                    meta.get(
                        "lease_until"
                    ),

                "estimate_minutes":
                    estimate_minutes(
                        meta
                    ),

                "checklist":
                    json_clone(
                        meta.get(
                            "checklist",
                            [],
                        )
                    ),

                "ready":
                    ready,

                "overdue":
                    overdue,

                "unsatisfied_dependencies":
                    unsatisfied,

                "dependents":
                    dependents,

                "transitive_dependencies":
                    list(
                        self.runtime
                        .transitive_dependencies(
                            task_id
                        )
                    ),

                "fan_out":
                    len(
                        dependents
                    ),
            }
        )

        return payload

    def tasks(
        self,
        *,
        query: str
        | None = None,
        statuses: Sequence[str] = (),
        priorities: Sequence[str] = (),
        owner_filter: str
        | None = None,
        assignee: str
        | None = None,
        label: str
        | None = None,
        include_terminal: bool = True,
    ) -> list[
        dict[str, Any]
    ]:
        task_ids: set[str] | None = None

        q = (
            query
            or ""
        ).strip()

        if q:
            task_ids = {
                item.task_id
                for item
                in self.search(
                    q
                )
            }

        status_set = set(
            statuses
        )

        priority_set = set(
            priorities
        )

        terminal = {
            "completed",
            "rejected",
            "superseded",
        }

        result = []

        for task in (
            self.runtime.tasks()
        ):
            if (
                task_ids is not None
                and task.task_id
                not in task_ids
            ):
                continue

            if (
                status_set
                and task.status
                not in status_set
            ):
                continue

            if (
                priority_set
                and task.priority
                not in priority_set
            ):
                continue

            if (
                owner_filter
                and task.owner
                != owner_filter
            ):
                continue

            if (
                not include_terminal
                and task.status
                in terminal
            ):
                continue

            public = self.public_task(
                task.task_id
            )

            if (
                assignee
                and public.get(
                    "assignee"
                )
                != assignee
            ):
                continue

            if (
                label
                and label
                not in public.get(
                    "labels",
                    [],
                )
            ):
                continue

            result.append(
                public
            )

        result.sort(
            key=lambda value: (
                PRIORITY_ORDER.get(
                    value[
                        "priority"
                    ],
                    99,
                ),
                value[
                    "due_at"
                ]
                or "9999",
                value[
                    "created_at"
                ],
                value[
                    "task_id"
                ],
            )
        )

        return result

    def search(
        self,
        query: str,
        limit: int = 100,
    ) -> list[
        SearchResult
    ]:
        query = query.strip()

        if not query:
            return []

        if self._rebuild_search_index():
            try:
                with self._connect() as connection:
                    rows = connection.execute(
                        """
                        SELECT
                            task_id,
                            bm25(task_search)
                                AS rank
                        FROM task_search
                        WHERE task_search MATCH ?
                        ORDER BY
                            rank,
                            task_id
                        LIMIT ?
                        """,
                        (
                            query,
                            limit,
                        ),
                    ).fetchall()

                return [
                    SearchResult(
                        row[
                            "task_id"
                        ],
                        float(
                            row[
                                "rank"
                            ]
                        ),
                    )
                    for row in rows
                ]

            except sqlite3.OperationalError:
                pass

        needle = query.casefold()

        values = []

        for task in (
            self.runtime.tasks()
        ):
            meta = taskboard_meta(
                task.extension_slots
            )

            haystack = "\n".join(
                [
                    task.task_id,
                    task.purpose,
                    task.owner,
                    task.jurisdiction,
                    " ".join(
                        normalize_labels(
                            meta.get(
                                "labels"
                            )
                        )
                    ),
                    str(
                        meta.get(
                            "notes",
                            "",
                        )
                    ),
                ]
            ).casefold()

            if needle in haystack:
                values.append(
                    SearchResult(
                        task.task_id,
                        0.0,
                    )
                )

        return values[
            :limit
        ]

    def create(
        self,
        payload: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        purpose = str(
            payload.get(
                "purpose"
            )
            or payload.get(
                "title"
            )
            or ""
        ).strip()

        if not purpose:
            raise NicheTaskEngineError(
                "purpose is required"
            )

        requested_status = str(
            payload.get(
                "status"
            )
            or "proposed"
        )

        if requested_status not in {
            "proposed",
            "accepted",
            "blocked",
            "deferred",
        }:
            raise NicheTaskEngineError(
                (
                    "new tasks must begin as "
                    "proposed, accepted, blocked, "
                    "or deferred"
                )
            )

        taskboard = {
            "title":
                str(
                    payload.get(
                        "title"
                    )
                    or purpose
                ).strip(),

            "labels":
                normalize_labels(
                    payload.get(
                        "labels"
                    )
                ),

            "notes":
                str(
                    payload.get(
                        "notes"
                    )
                    or ""
                ),

            "assignee":
                payload.get(
                    "assignee"
                )
                or None,

            "due_at":
                payload.get(
                    "due_at"
                )
                or None,

            "start_at":
                payload.get(
                    "start_at"
                )
                or None,

            "estimate_minutes":
                max(
                    1,
                    int(
                        payload.get(
                            "estimate_minutes"
                        )
                        or 30
                    ),
                ),

            "checklist":
                json_clone(
                    payload.get(
                        "checklist"
                    )
                    or []
                ),
        }

        if taskboard[
            "due_at"
        ]:
            parse_time(
                taskboard[
                    "due_at"
                ]
            )

        if taskboard[
            "start_at"
        ]:
            parse_time(
                taskboard[
                    "start_at"
                ]
            )

        extension_slots = dict(
            payload.get(
                "extension_slots"
            )
            or {}
        )

        extension_slots[
            taskboard_slot
        ] = taskboard

        extension_slots.setdefault(
            "masterplan_domain",
            str(
                payload.get(
                    "masterplan_domain"
                )
                or "runtime"
            ),
        )

        task = self.runtime.create(
            task_id=
                payload.get(
                    "task_id"
                ),

            purpose=
                purpose,

            owner=
                str(
                    payload.get(
                        "owner"
                    )
                    or owner
                ),

            jurisdiction=
                str(
                    payload.get(
                        "jurisdiction"
                    )
                    or "savant-runtime"
                ),

            authority_basis=
                normalize_sequence(
                    payload.get(
                        "authority_basis"
                    )
                    or (
                        "current-user-directive",
                    )
                ),

            completion_condition=
                str(
                    payload.get(
                        "completion_condition"
                    )
                    or (
                        "Requested outcome is "
                        "implemented and focused "
                        "validation passes."
                    )
                ),

            status=
                requested_status,

            priority=
                str(
                    payload.get(
                        "priority"
                    )
                    or "normal"
                ),

            provenance=
                dict(
                    payload.get(
                        "provenance"
                    )
                    or {
                        "source":
                            "niche-taskboard"
                    }
                ),

            created_from=
                normalize_sequence(
                    payload.get(
                        "created_from"
                    )
                ),

            dependencies=
                normalize_sequence(
                    payload.get(
                        "dependencies"
                    )
                ),

            affected_instances=
                normalize_sequence(
                    payload.get(
                        "affected_instances"
                    )
                ),

            compatibility_obligations=
                normalize_sequence(
                    payload.get(
                        (
                            "compatibility_"
                            "obligations"
                        )
                    )
                ),

            validation_budget=
                dict(
                    payload.get(
                        "validation_budget"
                    )
                    or {}
                ),

            blockers=
                normalize_sequence(
                    payload.get(
                        "blockers"
                    )
                ),

            supersedes=
                normalize_sequence(
                    payload.get(
                        "supersedes"
                    )
                ),

            decomposition_children=
                normalize_sequence(
                    payload.get(
                        (
                            "decomposition_"
                            "children"
                        )
                    )
                ),

            implementation_references=
                normalize_sequence(
                    payload.get(
                        (
                            "implementation_"
                            "references"
                        )
                    )
                ),

            extension_slots=
                extension_slots,
        )

        return self.public_task(
            task.task_id
        )

    def amend(
        self,
        task_id: str,
        patch: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        current = self.runtime.get(
            task_id
        )

        before = (
            current
            .authoritative_projection()
        )

        updates: dict[
            str,
            Any,
        ] = {}

        for (
            field,
            column,
        ) in editable_scalars.items():
            if field not in patch:
                continue

            value = str(
                patch[
                    field
                ]
            ).strip()

            if (
                field == "priority"
                and value
                not in PRIORITY_ORDER
            ):
                raise NicheTaskEngineError(
                    (
                        "invalid priority: "
                        + value
                    )
                )

            if not value:
                raise NicheTaskEngineError(
                    (
                        field
                        + " cannot be empty"
                    )
                )

            updates[
                column
            ] = value

        for (
            field,
            column,
        ) in editable_json.items():
            if field not in patch:
                continue

            value = patch[
                field
            ]

            if (
                field
                == "validation_budget"
            ):
                if not isinstance(
                    value,
                    Mapping,
                ):
                    raise NicheTaskEngineError(
                        (
                            "validation_budget "
                            "must be an object"
                        )
                    )

                normalized: Any = dict(
                    value
                )

            else:
                normalized = (
                    normalize_sequence(
                        value
                    )
                )

            updates[
                column
            ] = canonical_json(
                normalized
            )

        extension_slots = dict(
            current.extension_slots
        )

        meta = taskboard_meta(
            extension_slots
        )

        meta_fields = {
            "title",
            "labels",
            "notes",
            "assignee",
            "due_at",
            "start_at",
            "estimate_minutes",
            "lease_until",
            "checklist",
        }

        meta_changed = False

        for field in meta_fields:
            if field not in patch:
                continue

            value = patch[
                field
            ]

            if field == "labels":
                value = normalize_labels(
                    value
                )

            elif (
                field
                == "estimate_minutes"
            ):
                value = max(
                    1,
                    int(
                        value
                        or 30
                    ),
                )

            elif field == "checklist":
                if not isinstance(
                    value,
                    list,
                ):
                    raise NicheTaskEngineError(
                        (
                            "checklist must "
                            "be an array"
                        )
                    )

                value = json_clone(
                    value
                )

            elif field in {
                "due_at",
                "start_at",
                "lease_until",
            }:
                value = (
                    value
                    or None
                )

                if value:
                    parse_time(
                        value
                    )

            elif field in {
                "title",
                "notes",
            }:
                value = str(
                    value
                    or ""
                )

            elif field == "assignee":
                value = (
                    str(
                        value
                    ).strip()
                    if value
                    else None
                )

            meta[
                field
            ] = value

            meta_changed = True

        if meta_changed:
            extension_slots[
                taskboard_slot
            ] = meta

            updates[
                "extension_slots_json"
            ] = canonical_json(
                extension_slots
            )

        dependencies = None

        if "dependencies" in patch:
            dependencies = (
                normalize_sequence(
                    patch.get(
                        "dependencies"
                    )
                )
            )

            if task_id in dependencies:
                raise NicheTaskEngineError(
                    (
                        "task cannot depend "
                        "on itself"
                    )
                )

            known = {
                task.task_id
                for task
                in self.runtime.tasks()
            }

            missing = sorted(
                set(
                    dependencies
                )
                - known
            )

            if missing:
                raise NicheTaskEngineError(
                    (
                        "unknown dependencies: "
                        + ", ".join(
                            missing
                        )
                    )
                )

            prospective = {
                key:
                    tuple(
                        value
                    )
                for (
                    key,
                    value,
                )
                in (
                    self.runtime
                    .dependency_map()
                    .items()
                )
            }

            prospective[
                task_id
            ] = tuple(
                dependencies
            )

            cycles = cycle_paths(
                prospective
            )

            if cycles:
                raise NicheTaskEngineError(
                    (
                        "dependency cycle "
                        "introduced: "
                        + canonical_json(
                            cycles
                        )
                    )
                )

        if (
            not updates
            and dependencies is None
        ):
            return self.public_task(
                task_id
            )

        updates[
            "updated_at"
        ] = utc_now()

        with self._connect() as connection:
            if updates:
                assignments = ", ".join(
                    (
                        column
                        + " = ?"
                    )
                    for column
                    in updates
                )

                values = (
                    list(
                        updates.values()
                    )
                    + [
                        task_id
                    ]
                )

                connection.execute(
                    (
                        "UPDATE tasks SET "
                        + assignments
                        + " WHERE task_id = ?"
                    ),
                    values,
                )

            if dependencies is not None:
                connection.execute(
                    """
                    DELETE FROM dependencies
                    WHERE task_id = ?
                    """,
                    (
                        task_id,
                    ),
                )

                for dependency in dependencies:
                    connection.execute(
                        """
                        INSERT INTO dependencies (
                            task_id,
                            dependency_id
                        )
                        VALUES (?, ?)
                        """,
                        (
                            task_id,
                            dependency,
                        ),
                    )

            row = connection.execute(
                """
                SELECT *
                FROM tasks
                WHERE task_id = ?
                """,
                (
                    task_id,
                ),
            ).fetchone()

            if row is None:
                raise NicheTaskEngineError(
                    (
                        "task disappeared "
                        "during amendment"
                    )
                )

            after_task = (
                self.runtime._row_to_task(
                    row,
                    (
                        dependencies
                        if dependencies
                        is not None
                        else current.dependencies
                    ),
                )
            )

            self.runtime._append_event(
                connection,
                task_id=
                    task_id,
                event_type=
                    "amended",
                previous_state=
                    current.status,
                new_state=
                    current.status,
                payload={
                    "before_digest":
                        digest(
                            before
                        ),

                    "after_digest":
                        digest(
                            after_task
                            .authoritative_projection()
                        ),

                    "changed_fields":
                        sorted(
                            set(
                                patch
                            )
                        ),
                },
            )

        return self.public_task(
            task_id
        )

    def transition(
        self,
        task_id: str,
        state: str,
        *,
        receipts: Sequence[str] = (),
        reason: str | None = None,
    ) -> dict[str, Any]:
        if state not in TASK_STATES:
            raise NicheTaskEngineError(
                (
                    "invalid task state: "
                    + state
                )
            )

        task = self.runtime.transition(
            task_id,
            state,
            evidence_receipts=
                receipts,
            reason=
                reason,
        )

        return self.public_task(
            task.task_id
        )

    def lease(
        self,
        task_id: str,
        *,
        assignee: str,
        minutes: int = 60,
    ) -> dict[str, Any]:
        assignee = assignee.strip()

        if not assignee:
            raise NicheTaskEngineError(
                "assignee is required"
            )

        minutes = max(
            1,
            min(
                int(
                    minutes
                ),
                10080,
            ),
        )

        current = self.public_task(
            task_id
        )

        if (
            current[
                "blockers"
            ]
            or current[
                (
                    "unsatisfied_"
                    "dependencies"
                )
            ]
        ):
            raise NicheTaskEngineError(
                (
                    "blocked task cannot "
                    "be leased"
                )
            )

        lease_until = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                minutes=
                    minutes
            )
        )

        self.amend(
            task_id,
            {
                "assignee":
                    assignee,

                "lease_until":
                    lease_until.isoformat(),
            },
        )

        return self.transition(
            task_id,
            "leased",
            reason=
                (
                    "leased to "
                    + assignee
                ),
        )

    def release(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        current = self.public_task(
            task_id
        )

        if (
            current[
                "status"
            ]
            != "leased"
        ):
            raise NicheTaskEngineError(
                "task is not leased"
            )

        self.amend(
            task_id,
            {
                "lease_until":
                    None,
            },
        )

        return self.transition(
            task_id,
            "ready",
            reason=
                "lease released",
        )

    def critical_path(
        self,
    ) -> dict[str, Any]:
        tasks = {
            task.task_id:
                task
            for task
            in self.runtime.tasks()
        }

        graph = (
            self.runtime
            .dependency_map()
        )

        cycles = (
            self.runtime.cycles()
        )

        if cycles:
            return {
                "available":
                    False,

                "cycles": [
                    list(
                        item
                    )
                    for item
                    in cycles
                ],

                "path":
                    [],
            }

        order = (
            self.runtime
            .topological_order()
        )

        best_cost: dict[
            str,
            int,
        ] = {}

        best_path: dict[
            str,
            list[str],
        ] = {}

        for task_id in order:
            task = tasks[
                task_id
            ]

            meta = taskboard_meta(
                task.extension_slots
            )

            duration = (
                0
                if task.status
                == "completed"
                else estimate_minutes(
                    meta
                )
            )

            dependencies = graph.get(
                task_id,
                (),
            )

            if dependencies:
                parent = max(
                    dependencies,
                    key=lambda value: (
                        best_cost.get(
                            value,
                            0,
                        ),
                        value,
                    ),
                )

                best_cost[
                    task_id
                ] = (
                    best_cost.get(
                        parent,
                        0,
                    )
                    + duration
                )

                best_path[
                    task_id
                ] = (
                    best_path.get(
                        parent,
                        [
                            parent
                        ],
                    )
                    + [
                        task_id
                    ]
                )

            else:
                best_cost[
                    task_id
                ] = duration

                best_path[
                    task_id
                ] = [
                    task_id
                ]

        if not best_cost:
            return {
                "available":
                    True,

                "minutes":
                    0,

                "path":
                    [],
            }

        end = max(
            best_cost,
            key=lambda value: (
                best_cost[
                    value
                ],
                value,
            ),
        )

        return {
            "available":
                True,

            "minutes":
                best_cost[
                    end
                ],

            "path":
                best_path[
                    end
                ],
        }

    def focus_score(
        self,
        task: Mapping[
            str,
            Any,
        ],
    ) -> int:
        score = priority_weight.get(
            str(
                task.get(
                    "priority"
                )
            ),
            0,
        )

        score += (
            int(
                task.get(
                    "fan_out",
                    0,
                )
            )
            * 25
        )

        if task.get(
            "overdue"
        ):
            score += 350

        due_at = (
            parse_time(
                task.get(
                    "due_at"
                )
            )
            if task.get(
                "due_at"
            )
            else None
        )

        if due_at:
            hours = (
                (
                    due_at
                    - datetime.now(
                        timezone.utc
                    )
                )
                .total_seconds()
                / 3600
            )

            if (
                0
                <= hours
                <= 24
            ):
                score += 180

            elif (
                24
                < hours
                <= 72
            ):
                score += 90

        return score

    def dashboard(
        self,
    ) -> dict[str, Any]:
        tasks = self.tasks()

        counts: dict[
            str,
            int,
        ] = defaultdict(
            int
        )

        for task in tasks:
            counts[
                str(
                    task[
                        "status"
                    ]
                )
            ] += 1

        denominator = len(
            [
                task
                for task
                in tasks
                if task[
                    "status"
                ]
                not in {
                    "rejected",
                    "superseded",
                }
            ]
        )

        completed = counts.get(
            "completed",
            0,
        )

        progress = (
            round(
                (
                    completed
                    / denominator
                )
                * 100,
                1,
            )
            if denominator
            else 0.0
        )

        ready = [
            task
            for task
            in tasks
            if task.get(
                "ready"
            )
        ]

        ready.sort(
            key=lambda value: (
                -self.focus_score(
                    value
                ),
                value[
                    "task_id"
                ],
            )
        )

        blocked = [
            task
            for task
            in tasks
            if (
                task[
                    "status"
                ]
                == "blocked"
                or task[
                    "blockers"
                ]
                or task[
                    (
                        "unsatisfied_"
                        "dependencies"
                    )
                ]
            )
        ]

        overdue = [
            task
            for task
            in tasks
            if task.get(
                "overdue"
            )
        ]

        workloads: dict[
            str,
            dict[
                str,
                int,
            ],
        ] = defaultdict(
            lambda:
                defaultdict(
                    int
                )
        )

        for task in tasks:
            assignee = (
                task.get(
                    "assignee"
                )
                or "unassigned"
            )

            workloads[
                str(
                    assignee
                )
            ][
                str(
                    task[
                        "status"
                    ]
                )
            ] += 1

        bottlenecks = list(
            self.runtime
            .bottlenecks()
        )[:20]

        recently_updated = sorted(
            tasks,
            key=lambda value:
                value[
                    "updated_at"
                ],
            reverse=True,
        )[:20]

        payload = {
            "schema":
                schema,

            "owner":
                owner,

            "authority_effect":
                authority_effect,

            "task_count":
                len(
                    tasks
                ),

            "counts":
                dict(
                    sorted(
                        counts.items()
                    )
                ),

            "progress_percent":
                progress,

            "ready_queue":
                ready[:50],

            "blocked":
                blocked[:50],

            "overdue":
                overdue[:50],

            "critical_path":
                self.critical_path(),

            "bottlenecks":
                bottlenecks,

            "workloads": {
                key:
                    dict(
                        sorted(
                            value.items()
                        )
                    )
                for (
                    key,
                    value,
                )
                in sorted(
                    workloads.items()
                )
            },

            "recently_updated":
                recently_updated,

            "health":
                self.runtime.health(),

            "newly_unblocked":
                list(
                    self.runtime
                    .newly_unblocked()
                ),

            "projection_only":
                True,

            "task_authority_owner":
                owner,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def state(
        self,
    ) -> dict[str, Any]:
        graph = (
            self.runtime.project()
        )

        dashboard = (
            self.dashboard()
        )

        return {
            "schema":
                (
                    "savant://runtime/niche/"
                    "taskboard-state/1.0.0"
                ),

            "owner":
                owner,

            "dashboard":
                dashboard,

            "tasks":
                self.tasks(),

            "graph": {
                "topological_order":
                    graph.get(
                        "topological_order",
                        [],
                    ),

                "cycles":
                    graph.get(
                        "cycles",
                        [],
                    ),

                "digest":
                    graph.get(
                        "digest"
                    ),
            },

            "history_tail":
                list(
                    self.runtime.history()
                )[-100:],

            "authority_effect":
                authority_effect,

            "projection_only":
                True,
        }

    def history(
        self,
        task_id: str
        | None = None,
    ) -> list[
        dict[str, Any]
    ]:
        return list(
            self.runtime.history(
                task_id
            )
        )

    def health(
        self,
    ) -> dict[str, Any]:
        payload = (
            self.runtime.health()
        )

        payload.update(
            {
                "task_engine_schema":
                    schema,

                "fts5_search":
                    self._rebuild_search_index(),

                "taskboard_ready":
                    True,

                "task_authority_owner":
                    owner,
            }
        )

        return payload


def engine(
    db_path: str
    | Path = default_db,
) -> NicheTaskEngine:
    return NicheTaskEngine(
        db_path
    )


__all__ = [
    "NicheTaskEngine",
    "NicheTaskEngineError",
    "engine",
]
