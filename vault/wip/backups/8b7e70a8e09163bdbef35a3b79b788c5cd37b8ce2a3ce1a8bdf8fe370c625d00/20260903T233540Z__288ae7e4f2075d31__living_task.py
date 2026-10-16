#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


OWNER = "exile:niche"
MECHANICS_OWNER = "living:dryve"

SCHEMA = "savant://runtime/niche/living-task/1.0.0"
TASK_SCHEMA = "savant://runtime/niche/task/1.0.0"
EVENT_SCHEMA = "savant://runtime/niche/task-event/1.0.0"
PROJECTION_SCHEMA = "savant://runtime/niche/task-graph/1.0.0"
MASTERPLAN_SCHEMA = "savant://runtime/niche/masterplan/1.0.0"

DEFAULT_ROOT = Path("/root/savant-runtime")
DEFAULT_DB = DEFAULT_ROOT / "runtime" / "niche" / "tasks.sqlite3"

TASK_STATES = (
    "proposed",
    "accepted",
    "ready",
    "leased",
    "active",
    "blocked",
    "deferred",
    "completed",
    "rejected",
    "superseded",
)

TERMINAL_STATES = frozenset(
    {
        "completed",
        "rejected",
        "superseded",
    }
)

SATISFIED_STATES = frozenset({"completed"})

PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
    "deferred": 4,
}


class NicheTaskError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_identifier(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def normalize_sequence(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        item = normalize_identifier(value)
        return (item,) if item else ()

    if isinstance(value, Mapping):
        values: Iterable[Any] = value.keys()
    else:
        try:
            values = iter(value)
        except TypeError:
            values = (value,)

    normalized = {
        item
        for item in (
            normalize_identifier(candidate)
            for candidate in values
        )
        if item
    }

    return tuple(sorted(normalized))


def stable_task_id(
    *,
    owner: str,
    purpose: str,
    created_from: Sequence[str] = (),
    alias: str | None = None,
) -> str:
    if alias:
        normalized = normalize_identifier(alias)
        if not normalized:
            raise NicheTaskError("invalid task alias")
        return normalized

    identity = {
        "owner": owner,
        "purpose": purpose,
        "created_from": list(
            normalize_sequence(created_from)
        ),
    }

    return "task:" + digest(identity)[:24]


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    owner: str
    jurisdiction: str
    purpose: str
    status: str
    priority: str
    authority_basis: tuple[str, ...]
    provenance: Mapping[str, Any]
    created_from: tuple[str, ...]
    dependencies: tuple[str, ...]
    affected_instances: tuple[str, ...]
    compatibility_obligations: tuple[str, ...]
    completion_condition: str
    validation_budget: Mapping[str, Any]
    blockers: tuple[str, ...]
    evidence_receipts: tuple[str, ...]
    supersedes: tuple[str, ...]
    decomposition_children: tuple[str, ...]
    implementation_references: tuple[str, ...]
    extension_slots: Mapping[str, Any]
    created_at: str
    updated_at: str

    def authoritative_projection(self) -> dict[str, Any]:
        return {
            "schema": TASK_SCHEMA,
            "task_id": self.task_id,
            "owner": self.owner,
            "jurisdiction": self.jurisdiction,
            "purpose": self.purpose,
            "status": self.status,
            "priority": self.priority,
            "authority_basis": list(self.authority_basis),
            "provenance": dict(self.provenance),
            "created_from": list(self.created_from),
            "dependencies": list(self.dependencies),
            "affected_instances": list(
                self.affected_instances
            ),
            "compatibility_obligations": list(
                self.compatibility_obligations
            ),
            "completion_condition": (
                self.completion_condition
            ),
            "validation_budget": dict(
                self.validation_budget
            ),
            "blockers": list(self.blockers),
            "evidence_receipts": list(
                self.evidence_receipts
            ),
            "supersedes": list(self.supersedes),
            "decomposition_children": list(
                self.decomposition_children
            ),
            "implementation_references": list(
                self.implementation_references
            ),
            "extension_slots": dict(
                self.extension_slots
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "authority_owner": OWNER,
            "authoritative": True,
        }


class LivingTaskEngine:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB,
    ) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.db_path)
        )
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    authority_basis_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    created_from_json TEXT NOT NULL,
                    affected_instances_json TEXT NOT NULL,
                    compatibility_obligations_json TEXT NOT NULL,
                    completion_condition TEXT NOT NULL,
                    validation_budget_json TEXT NOT NULL,
                    blockers_json TEXT NOT NULL,
                    evidence_receipts_json TEXT NOT NULL,
                    supersedes_json TEXT NOT NULL,
                    decomposition_children_json TEXT NOT NULL,
                    implementation_references_json TEXT NOT NULL,
                    extension_slots_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dependencies (
                    task_id TEXT NOT NULL,
                    dependency_id TEXT NOT NULL,
                    PRIMARY KEY (
                        task_id,
                        dependency_id
                    ),
                    FOREIGN KEY(task_id)
                        REFERENCES tasks(task_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    previous_state TEXT,
                    new_state TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    previous_event_digest TEXT,
                    event_digest TEXT UNIQUE NOT NULL,
                    FOREIGN KEY(task_id)
                        REFERENCES tasks(task_id)
                );

                CREATE INDEX IF NOT EXISTS
                    idx_tasks_status
                ON tasks(status);

                CREATE INDEX IF NOT EXISTS
                    idx_tasks_priority
                ON tasks(priority);

                CREATE INDEX IF NOT EXISTS
                    idx_dependencies_dependency
                ON dependencies(dependency_id);

                CREATE INDEX IF NOT EXISTS
                    idx_events_task
                ON events(task_id, sequence);
                """
            )

    @staticmethod
    def _loads(value: str) -> Any:
        return json.loads(value)

    def _row_to_task(
        self,
        row: sqlite3.Row,
        dependencies: Sequence[str],
    ) -> Task:
        return Task(
            task_id=row["task_id"],
            owner=row["owner"],
            jurisdiction=row["jurisdiction"],
            purpose=row["purpose"],
            status=row["status"],
            priority=row["priority"],
            authority_basis=tuple(
                self._loads(
                    row["authority_basis_json"]
                )
            ),
            provenance=self._loads(
                row["provenance_json"]
            ),
            created_from=tuple(
                self._loads(
                    row["created_from_json"]
                )
            ),
            dependencies=tuple(
                sorted(dependencies)
            ),
            affected_instances=tuple(
                self._loads(
                    row["affected_instances_json"]
                )
            ),
            compatibility_obligations=tuple(
                self._loads(
                    row[
                        "compatibility_obligations_json"
                    ]
                )
            ),
            completion_condition=(
                row["completion_condition"]
            ),
            validation_budget=self._loads(
                row["validation_budget_json"]
            ),
            blockers=tuple(
                self._loads(row["blockers_json"])
            ),
            evidence_receipts=tuple(
                self._loads(
                    row["evidence_receipts_json"]
                )
            ),
            supersedes=tuple(
                self._loads(row["supersedes_json"])
            ),
            decomposition_children=tuple(
                self._loads(
                    row[
                        "decomposition_children_json"
                    ]
                )
            ),
            implementation_references=tuple(
                self._loads(
                    row[
                        "implementation_references_json"
                    ]
                )
            ),
            extension_slots=self._loads(
                row["extension_slots_json"]
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get(
        self,
        task_id: str,
    ) -> Task:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()

            if row is None:
                raise NicheTaskError(
                    f"unknown task: {task_id}"
                )

            dependencies = [
                item["dependency_id"]
                for item in connection.execute(
                    """
                    SELECT dependency_id
                    FROM dependencies
                    WHERE task_id = ?
                    ORDER BY dependency_id
                    """,
                    (task_id,),
                )
            ]

        return self._row_to_task(
            row,
            dependencies,
        )

    def tasks(self) -> tuple[Task, ...]:
        with self._connect() as connection:
            ids = [
                row["task_id"]
                for row in connection.execute(
                    """
                    SELECT task_id
                    FROM tasks
                    ORDER BY task_id
                    """
                )
            ]

        return tuple(
            self.get(task_id)
            for task_id in ids
        )

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        task_id: str,
        event_type: str,
        previous_state: str | None,
        new_state: str | None,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        previous = connection.execute(
            """
            SELECT event_digest
            FROM events
            ORDER BY sequence DESC
            LIMIT 1
            """
        ).fetchone()

        previous_digest = (
            previous["event_digest"]
            if previous
            else None
        )

        created_at = utc_now()

        event_body = {
            "schema": EVENT_SCHEMA,
            "task_id": task_id,
            "event_type": event_type,
            "previous_state": previous_state,
            "new_state": new_state,
            "payload": dict(payload),
            "created_at": created_at,
            "previous_event_digest": (
                previous_digest
            ),
            "owner": OWNER,
        }

        event_digest = digest(event_body)
        event_id = (
            "task-event:"
            + event_digest[:24]
        )

        connection.execute(
            """
            INSERT INTO events (
                event_id,
                task_id,
                event_type,
                previous_state,
                new_state,
                payload_json,
                created_at,
                previous_event_digest,
                event_digest
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                task_id,
                event_type,
                previous_state,
                new_state,
                canonical_json(payload),
                created_at,
                previous_digest,
                event_digest,
            ),
        )

        return {
            **event_body,
            "event_id": event_id,
            "event_digest": event_digest,
            "authoritative": True,
        }

    def create(
        self,
        *,
        purpose: str,
        owner: str,
        jurisdiction: str,
        authority_basis: Sequence[str],
        completion_condition: str,
        task_id: str | None = None,
        status: str = "proposed",
        priority: str = "normal",
        provenance: Mapping[str, Any] | None = None,
        created_from: Sequence[str] = (),
        dependencies: Sequence[str] = (),
        affected_instances: Sequence[str] = (),
        compatibility_obligations: Sequence[str] = (),
        validation_budget: Mapping[str, Any] | None = None,
        blockers: Sequence[str] = (),
        evidence_receipts: Sequence[str] = (),
        supersedes: Sequence[str] = (),
        decomposition_children: Sequence[str] = (),
        implementation_references: Sequence[str] = (),
        extension_slots: Mapping[str, Any] | None = None,
    ) -> Task:
        purpose = str(purpose).strip()
        owner = str(owner).strip()
        jurisdiction = str(jurisdiction).strip()
        completion_condition = (
            str(completion_condition).strip()
        )

        if not purpose:
            raise NicheTaskError(
                "purpose is required"
            )

        if not owner:
            raise NicheTaskError(
                "owner is required"
            )

        if not jurisdiction:
            raise NicheTaskError(
                "jurisdiction is required"
            )

        authority = normalize_sequence(
            authority_basis
        )

        if not authority:
            raise NicheTaskError(
                "authority_basis is required"
            )

        if not completion_condition:
            raise NicheTaskError(
                "completion_condition is required"
            )

        if status not in TASK_STATES:
            raise NicheTaskError(
                f"invalid task state: {status}"
            )

        if priority not in PRIORITY_ORDER:
            raise NicheTaskError(
                f"invalid priority: {priority}"
            )

        normalized_dependencies = (
            normalize_sequence(dependencies)
        )

        resolved_id = stable_task_id(
            owner=owner,
            purpose=purpose,
            created_from=created_from,
            alias=task_id,
        )

        if resolved_id in normalized_dependencies:
            raise NicheTaskError(
                "task cannot depend on itself"
            )

        now = utc_now()

        values = {
            "task_id": resolved_id,
            "owner": owner,
            "jurisdiction": jurisdiction,
            "purpose": purpose,
            "status": status,
            "priority": priority,
            "authority_basis_json": canonical_json(
                authority
            ),
            "provenance_json": canonical_json(
                provenance or {}
            ),
            "created_from_json": canonical_json(
                normalize_sequence(created_from)
            ),
            "affected_instances_json": canonical_json(
                normalize_sequence(
                    affected_instances
                )
            ),
            "compatibility_obligations_json": canonical_json(
                normalize_sequence(
                    compatibility_obligations
                )
            ),
            "completion_condition": (
                completion_condition
            ),
            "validation_budget_json": canonical_json(
                validation_budget
                or {
                    "syntax_or_compile": True,
                    "focused_functional": 1,
                    "integration_or_startup": 1,
                }
            ),
            "blockers_json": canonical_json(
                normalize_sequence(blockers)
            ),
            "evidence_receipts_json": canonical_json(
                normalize_sequence(
                    evidence_receipts
                )
            ),
            "supersedes_json": canonical_json(
                normalize_sequence(supersedes)
            ),
            "decomposition_children_json": canonical_json(
                normalize_sequence(
                    decomposition_children
                )
            ),
            "implementation_references_json": canonical_json(
                normalize_sequence(
                    implementation_references
                )
            ),
            "extension_slots_json": canonical_json(
                extension_slots or {}
            ),
            "created_at": now,
            "updated_at": now,
        }

        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT task_id
                FROM tasks
                WHERE task_id = ?
                """,
                (resolved_id,),
            ).fetchone()

            if existing:
                raise NicheTaskError(
                    f"task already exists: {resolved_id}"
                )

            connection.execute(
                """
                INSERT INTO tasks (
                    task_id,
                    owner,
                    jurisdiction,
                    purpose,
                    status,
                    priority,
                    authority_basis_json,
                    provenance_json,
                    created_from_json,
                    affected_instances_json,
                    compatibility_obligations_json,
                    completion_condition,
                    validation_budget_json,
                    blockers_json,
                    evidence_receipts_json,
                    supersedes_json,
                    decomposition_children_json,
                    implementation_references_json,
                    extension_slots_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    :task_id,
                    :owner,
                    :jurisdiction,
                    :purpose,
                    :status,
                    :priority,
                    :authority_basis_json,
                    :provenance_json,
                    :created_from_json,
                    :affected_instances_json,
                    :compatibility_obligations_json,
                    :completion_condition,
                    :validation_budget_json,
                    :blockers_json,
                    :evidence_receipts_json,
                    :supersedes_json,
                    :decomposition_children_json,
                    :implementation_references_json,
                    :extension_slots_json,
                    :created_at,
                    :updated_at
                )
                """,
                values,
            )

            for dependency in normalized_dependencies:
                connection.execute(
                    """
                    INSERT INTO dependencies (
                        task_id,
                        dependency_id
                    )
                    VALUES (?, ?)
                    """,
                    (
                        resolved_id,
                        dependency,
                    ),
                )

            self._append_event(
                connection,
                task_id=resolved_id,
                event_type="created",
                previous_state=None,
                new_state=status,
                payload={
                    "task_digest": digest(values),
                    "dependencies": list(
                        normalized_dependencies
                    ),
                },
            )

        cycles = self.cycles()

        if cycles:
            with self._connect() as connection:
                connection.execute(
                    """
                    DELETE FROM tasks
                    WHERE task_id = ?
                    """,
                    (resolved_id,),
                )

            raise NicheTaskError(
                "dependency cycle introduced: "
                + canonical_json(cycles)
            )

        return self.get(resolved_id)

    def transition(
        self,
        task_id: str,
        new_state: str,
        *,
        evidence_receipts: Sequence[str] = (),
        reason: str | None = None,
    ) -> Task:
        if new_state not in TASK_STATES:
            raise NicheTaskError(
                f"invalid task state: {new_state}"
            )

        current = self.get(task_id)

        if current.status in TERMINAL_STATES:
            raise NicheTaskError(
                "terminal task state is immutable; "
                "supersede or create a regression task"
            )

        receipts = tuple(
            sorted(
                set(current.evidence_receipts)
                | set(
                    normalize_sequence(
                        evidence_receipts
                    )
                )
            )
        )

        if (
            new_state == "completed"
            and not receipts
        ):
            raise NicheTaskError(
                "completion requires at least one "
                "evidence/receipt reference"
            )

        unresolved = self.unsatisfied_dependencies(
            task_id
        )

        if (
            new_state
            in {"ready", "leased", "active", "completed"}
            and unresolved
        ):
            raise NicheTaskError(
                "task has unsatisfied dependencies: "
                + ", ".join(unresolved)
            )

        now = utc_now()

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = ?,
                    evidence_receipts_json = ?,
                    updated_at = ?
                WHERE task_id = ?
                """,
                (
                    new_state,
                    canonical_json(receipts),
                    now,
                    task_id,
                ),
            )

            self._append_event(
                connection,
                task_id=task_id,
                event_type="transition",
                previous_state=current.status,
                new_state=new_state,
                payload={
                    "reason": reason,
                    "evidence_receipts": list(
                        receipts
                    ),
                },
            )

        return self.get(task_id)

    def dependency_map(
        self,
    ) -> dict[str, tuple[str, ...]]:
        tasks = {
            task.task_id
            for task in self.tasks()
        }

        result: dict[str, set[str]] = {
            task_id: set()
            for task_id in tasks
        }

        with self._connect() as connection:
            for row in connection.execute(
                """
                SELECT task_id, dependency_id
                FROM dependencies
                ORDER BY task_id, dependency_id
                """
            ):
                result.setdefault(
                    row["task_id"],
                    set(),
                ).add(row["dependency_id"])

                result.setdefault(
                    row["dependency_id"],
                    set(),
                )

        return {
            key: tuple(sorted(value))
            for key, value in sorted(
                result.items()
            )
        }

    def reverse_dependencies(
        self,
    ) -> dict[str, tuple[str, ...]]:
        reverse: dict[str, set[str]] = (
            defaultdict(set)
        )

        for task_id, dependencies in (
            self.dependency_map().items()
        ):
            reverse.setdefault(task_id, set())

            for dependency in dependencies:
                reverse[dependency].add(task_id)

        return {
            key: tuple(sorted(value))
            for key, value in sorted(
                reverse.items()
            )
        }

    def transitive_dependencies(
        self,
        task_id: str,
    ) -> tuple[str, ...]:
        graph = self.dependency_map()
        seen: set[str] = set()
        pending = list(
            graph.get(task_id, ())
        )

        while pending:
            current = pending.pop()

            if current in seen:
                continue

            seen.add(current)
            pending.extend(
                graph.get(current, ())
            )

        return tuple(sorted(seen))

    def unsatisfied_dependencies(
        self,
        task_id: str,
    ) -> tuple[str, ...]:
        task = self.get(task_id)
        unsatisfied: list[str] = []

        for dependency in task.dependencies:
            try:
                dependency_task = self.get(
                    dependency
                )
            except NicheTaskError:
                unsatisfied.append(dependency)
                continue

            if (
                dependency_task.status
                not in SATISFIED_STATES
            ):
                unsatisfied.append(dependency)

        return tuple(sorted(unsatisfied))

    def cycles(
        self,
    ) -> tuple[tuple[str, ...], ...]:
        graph = self.dependency_map()
        state: dict[str, int] = {}
        stack: list[str] = []
        cycles: set[tuple[str, ...]] = set()

        def visit(node: str) -> None:
            marker = state.get(node, 0)

            if marker == 2:
                return

            if marker == 1:
                if node in stack:
                    index = stack.index(node)
                    cycle = tuple(
                        stack[index:] + [node]
                    )
                    cycles.add(cycle)
                return

            state[node] = 1
            stack.append(node)

            for dependency in graph.get(
                node,
                (),
            ):
                visit(dependency)

            stack.pop()
            state[node] = 2

        for node in sorted(graph):
            visit(node)

        return tuple(sorted(cycles))

    def topological_order(
        self,
    ) -> tuple[str, ...]:
        graph = self.dependency_map()
        reverse = self.reverse_dependencies()

        indegree = {
            task_id: len(dependencies)
            for task_id, dependencies
            in graph.items()
        }

        queue = [
            task_id
            for task_id, count
            in indegree.items()
            if count == 0
        ]

        queue.sort()
        ordered: list[str] = []

        while queue:
            node = queue.pop(0)
            ordered.append(node)

            for dependent in reverse.get(
                node,
                (),
            ):
                indegree[dependent] -= 1

                if indegree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort()

        if len(ordered) != len(indegree):
            raise NicheTaskError(
                "task graph contains a cycle"
            )

        return tuple(ordered)

    def ready_tasks(
        self,
    ) -> tuple[Task, ...]:
        candidates: list[Task] = []

        for task in self.tasks():
            if task.status not in {
                "accepted",
                "ready",
            }:
                continue

            if task.blockers:
                continue

            if self.unsatisfied_dependencies(
                task.task_id
            ):
                continue

            candidates.append(task)

        candidates.sort(
            key=lambda task: (
                PRIORITY_ORDER.get(
                    task.priority,
                    99,
                ),
                task.created_at,
                task.task_id,
            )
        )

        return tuple(candidates)

    def newly_unblocked(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            task.task_id
            for task in self.ready_tasks()
            if task.status == "accepted"
        )

    def bottlenecks(
        self,
    ) -> tuple[dict[str, Any], ...]:
        reverse = self.reverse_dependencies()
        values = []

        for task_id, dependents in reverse.items():
            if not dependents:
                continue

            values.append(
                {
                    "task_id": task_id,
                    "fan_out": len(dependents),
                    "dependents": list(
                        dependents
                    ),
                }
            )

        values.sort(
            key=lambda value: (
                -value["fan_out"],
                value["task_id"],
            )
        )

        return tuple(values)

    def history(
        self,
        task_id: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            if task_id is None:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM events
                    ORDER BY sequence
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM events
                    WHERE task_id = ?
                    ORDER BY sequence
                    """,
                    (task_id,),
                ).fetchall()

        return tuple(
            {
                "sequence": row["sequence"],
                "event_id": row["event_id"],
                "task_id": row["task_id"],
                "event_type": row["event_type"],
                "previous_state": (
                    row["previous_state"]
                ),
                "new_state": row["new_state"],
                "payload": self._loads(
                    row["payload_json"]
                ),
                "created_at": row["created_at"],
                "previous_event_digest": (
                    row["previous_event_digest"]
                ),
                "event_digest": (
                    row["event_digest"]
                ),
                "authoritative": True,
            }
            for row in rows
        )

    def validate_history_chain(
        self,
    ) -> tuple[str, ...]:
        errors: list[str] = []
        previous_digest = None

        for event in self.history():
            body = {
                "schema": EVENT_SCHEMA,
                "task_id": event["task_id"],
                "event_type": (
                    event["event_type"]
                ),
                "previous_state": (
                    event["previous_state"]
                ),
                "new_state": (
                    event["new_state"]
                ),
                "payload": event["payload"],
                "created_at": (
                    event["created_at"]
                ),
                "previous_event_digest": (
                    event[
                        "previous_event_digest"
                    ]
                ),
                "owner": OWNER,
            }

            expected = digest(body)

            if (
                event["previous_event_digest"]
                != previous_digest
            ):
                errors.append(
                    "broken previous-event link: "
                    + event["event_id"]
                )

            if event["event_digest"] != expected:
                errors.append(
                    "event digest mismatch: "
                    + event["event_id"]
                )

            previous_digest = (
                event["event_digest"]
            )

        return tuple(errors)

    def project(
        self,
    ) -> dict[str, Any]:
        tasks = self.tasks()
        reverse = self.reverse_dependencies()
        cycles = self.cycles()

        projected_tasks = []

        for task in tasks:
            value = task.authoritative_projection()

            value["dependents"] = list(
                reverse.get(
                    task.task_id,
                    (),
                )
            )

            value[
                "transitive_dependencies"
            ] = list(
                self.transitive_dependencies(
                    task.task_id
                )
            )

            value[
                "unsatisfied_dependencies"
            ] = list(
                self.unsatisfied_dependencies(
                    task.task_id
                )
            )

            value["ready"] = (
                task.status
                in {"accepted", "ready"}
                and not task.blockers
                and not value[
                    "unsatisfied_dependencies"
                ]
            )

            value["authoritative"] = False
            value["authority_effect"] = "none"
            value["rebuildable"] = True

            projected_tasks.append(value)

        payload = {
            "schema": PROJECTION_SCHEMA,
            "owner": OWNER,
            "task_count": len(tasks),
            "tasks": projected_tasks,
            "topological_order": (
                list(self.topological_order())
                if not cycles
                else []
            ),
            "cycles": [
                list(cycle)
                for cycle in cycles
            ],
            "newly_unblocked": list(
                self.newly_unblocked()
            ),
            "bottlenecks": list(
                self.bottlenecks()
            ),
            "history_chain_errors": list(
                self.validate_history_chain()
            ),
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)

        return payload

    def masterplan(
        self,
    ) -> dict[str, Any]:
        graph = self.project()

        domains = {
            domain: []
            for domain in (
                "authority",
                "canon",
                "ontology",
                "rubrics",
                "context",
                "runtime",
                "vault",
                "assurance",
                "evolution",
            )
        }

        for task in graph["tasks"]:
            domain = task.get(
                "extension_slots",
                {},
            ).get(
                "masterplan_domain",
                "runtime",
            )

            if domain not in domains:
                domain = "runtime"

            domains[domain].append(
                task["task_id"]
            )

        payload = {
            "schema": MASTERPLAN_SCHEMA,
            "owner": OWNER,
            "domains": domains,
            "ready": [
                task.task_id
                for task in self.ready_tasks()
            ],
            "blocked": [
                task.task_id
                for task in self.tasks()
                if (
                    task.status == "blocked"
                    or task.blockers
                    or self.unsatisfied_dependencies(
                        task.task_id
                    )
                )
            ],
            "completed": [
                task.task_id
                for task in self.tasks()
                if task.status == "completed"
            ],
            "task_graph_digest": (
                graph["digest"]
            ),
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)

        return payload

    def health(self) -> dict[str, Any]:
        cycles = self.cycles()
        history_errors = (
            self.validate_history_chain()
        )

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "mechanics_owner": (
                MECHANICS_OWNER
            ),
            "database": str(self.db_path),
            "task_count": len(self.tasks()),
            "task_governance_owner": OWNER,
            "task_transition_owner": OWNER,
            "masterplan_projection_owner": OWNER,
            "dryve_may_govern_tasks": False,
            "dryve_may_transition_tasks": False,
            "direct_dependency_storage": True,
            "reverse_dependencies_derived": True,
            "transitive_dependencies_derived": True,
            "immutable_history": True,
            "history_chain_valid": (
                not history_errors
            ),
            "cycle_free": not cycles,
            "cycles": [
                list(cycle)
                for cycle in cycles
            ],
            "history_errors": list(
                history_errors
            ),
            "authoritative_task_store": True,
            "projection_authoritative": False,
        }

        payload["healthy"] = (
            payload["history_chain_valid"]
            and payload["cycle_free"]
        )

        payload["digest"] = digest(payload)

        return payload


def engine(
    db_path: str | Path = DEFAULT_DB,
) -> LivingTaskEngine:
    return LivingTaskEngine(db_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Niche persistent living task engine"
        )
    )

    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser("health")
    subparsers.add_parser("list")
    subparsers.add_parser("ready")
    subparsers.add_parser("graph")
    subparsers.add_parser("masterplan")
    subparsers.add_parser("history")

    create_parser = subparsers.add_parser(
        "create"
    )
    create_parser.add_argument(
        "--id",
        dest="task_id",
    )
    create_parser.add_argument(
        "--purpose",
        required=True,
    )
    create_parser.add_argument(
        "--owner",
        required=True,
    )
    create_parser.add_argument(
        "--jurisdiction",
        required=True,
    )
    create_parser.add_argument(
        "--authority",
        action="append",
        required=True,
    )
    create_parser.add_argument(
        "--completion",
        required=True,
    )
    create_parser.add_argument(
        "--dependency",
        action="append",
        default=[],
    )
    create_parser.add_argument(
        "--affected-instance",
        action="append",
        default=[],
    )
    create_parser.add_argument(
        "--priority",
        choices=tuple(PRIORITY_ORDER),
        default="normal",
    )
    create_parser.add_argument(
        "--status",
        choices=TASK_STATES,
        default="proposed",
    )
    create_parser.add_argument(
        "--domain",
        choices=(
            "authority",
            "canon",
            "ontology",
            "rubrics",
            "context",
            "runtime",
            "vault",
            "assurance",
            "evolution",
        ),
        default="runtime",
    )

    transition_parser = (
        subparsers.add_parser("transition")
    )
    transition_parser.add_argument(
        "task_id"
    )
    transition_parser.add_argument(
        "state",
        choices=TASK_STATES,
    )
    transition_parser.add_argument(
        "--receipt",
        action="append",
        default=[],
    )
    transition_parser.add_argument(
        "--reason",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime = engine(args.db)

    if args.command == "health":
        output: Any = runtime.health()

    elif args.command == "list":
        output = [
            task.authoritative_projection()
            for task in runtime.tasks()
        ]

    elif args.command == "ready":
        output = [
            task.authoritative_projection()
            for task in runtime.ready_tasks()
        ]

    elif args.command == "graph":
        output = runtime.project()

    elif args.command == "masterplan":
        output = runtime.masterplan()

    elif args.command == "history":
        output = runtime.history()

    elif args.command == "create":
        output = runtime.create(
            task_id=args.task_id,
            purpose=args.purpose,
            owner=args.owner,
            jurisdiction=args.jurisdiction,
            authority_basis=args.authority,
            completion_condition=(
                args.completion
            ),
            dependencies=args.dependency,
            affected_instances=(
                args.affected_instance
            ),
            priority=args.priority,
            status=args.status,
            provenance={
                "source": "niche-cli",
            },
            extension_slots={
                "masterplan_domain": (
                    args.domain
                ),
            },
        ).authoritative_projection()

    elif args.command == "transition":
        output = runtime.transition(
            args.task_id,
            args.state,
            evidence_receipts=args.receipt,
            reason=args.reason,
        ).authoritative_projection()

    else:
        raise NicheTaskError(
            f"unsupported command: {args.command}"
        )

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
