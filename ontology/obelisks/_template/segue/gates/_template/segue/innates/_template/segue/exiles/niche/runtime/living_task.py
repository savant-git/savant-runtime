#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from runtime.straub.datrix import StraubDatrix


OWNER = "exile:niche"
MECHANICS_OWNER = "living:dryve"

SCHEMA = "savant://runtime/niche/living-task/1.1.0"
TASK_SCHEMA = "savant://runtime/niche/task/1.0.0"
EVENT_SCHEMA = "savant://runtime/niche/task-event/1.0.0"
PROJECTION_SCHEMA = "savant://runtime/niche/task-graph/1.1.0"
MASTERPLAN_SCHEMA = "savant://runtime/niche/masterplan/1.0.0"
EXECUTION_SCHEMA = (
    "savant://runtime/niche/execution-intelligence/1.0.0"
)
DASHBOARD_SCHEMA = (
    "savant://runtime/niche/dashboard/1.0.0"
)

DEFAULT_ROOT = Path("/root/savant-runtime")
DEFAULT_DATRIX = (
    DEFAULT_ROOT
    / "runtime"
    / "niche"
    / "tasks.datrix"
)
DEFAULT_DB = DEFAULT_DATRIX

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

SATISFIED_STATES = frozenset(
    {
        "completed",
    }
)

EXECUTABLE_STATES = frozenset(
    {
        "accepted",
        "ready",
    }
)

IN_FLIGHT_STATES = frozenset(
    {
        "leased",
        "active",
    }
)

PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
    "deferred": 4,
}

PRIORITY_WEIGHT = {
    "critical": 500.0,
    "high": 300.0,
    "normal": 150.0,
    "low": 50.0,
    "deferred": 0.0,
}

STATUS_WEIGHT = {
    "proposed": 40.0,
    "accepted": 100.0,
    "ready": 220.0,
    "leased": 160.0,
    "active": 180.0,
    "blocked": -80.0,
    "deferred": -200.0,
    "completed": -500.0,
    "rejected": -600.0,
    "superseded": -600.0,
}

DEFAULT_EXECUTION_POLICY = {
    "retry_limit": 0,
    "retry_backoff_seconds": 30,
    "retry_backoff_multiplier": 2.0,
    "retry_backoff_max_seconds": 3600,
    "timeout_seconds": None,
    "lease_seconds": 900,
    "concurrency_pool": None,
    "concurrency_limit": None,
    "resource_claims": [],
    "trigger_rule": "all_dependencies_completed",
    "manual_approval_required": False,
    "approved": False,
    "not_before": None,
    "deadline": None,
    "sla_seconds": None,
    "idempotency_key": None,
    "cache_key": None,
    "cache_ttl_seconds": None,
    "checkpoint_reference": None,
    "resumable": False,
    "failure_class": None,
    "cancellation_requested": False,
    "attempt": 0,
    "last_attempt_at": None,
    "last_failure_at": None,
    "last_success_at": None,
    "lease_owner": None,
    "lease_acquired_at": None,
    "lease_expires_at": None,
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
    return datetime.now(
        timezone.utc
    ).isoformat()


def parse_datetime(
    value: Any,
) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = (
            text[:-1]
            + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            text
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def normalize_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def normalize_sequence(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        item = normalize_identifier(
            value
        )
        return (
            (item,)
            if item
            else ()
        )

    if isinstance(value, Mapping):
        values: Iterable[Any] = (
            value.keys()
        )
    else:
        try:
            values = iter(value)
        except TypeError:
            values = (value,)

    normalized = {
        item
        for item in (
            normalize_identifier(
                candidate
            )
            for candidate in values
        )
        if item
    }

    return tuple(
        sorted(normalized)
    )


def stable_task_id(
    *,
    owner: str,
    purpose: str,
    created_from: Sequence[str] = (),
    alias: str | None = None,
) -> str:
    if alias:
        normalized = (
            normalize_identifier(
                alias
            )
        )

        if not normalized:
            raise NicheTaskError(
                "invalid task alias"
            )

        return normalized

    identity = {
        "owner": owner,
        "purpose": purpose,
        "created_from": list(
            normalize_sequence(
                created_from
            )
        ),
    }

    return (
        "task:"
        + digest(identity)[:24]
    )


def execution_policy(
    extension_slots: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    result = dict(
        DEFAULT_EXECUTION_POLICY
    )

    raw = extension_slots.get(
        "niche.execution",
        {},
    )

    if isinstance(raw, Mapping):
        for key in result:
            if key in raw:
                result[key] = raw[key]

    return result


@dataclass(
    frozen=True,
    slots=True,
)
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

    def authoritative_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": TASK_SCHEMA,
            "task_id": self.task_id,
            "owner": self.owner,
            "jurisdiction": (
                self.jurisdiction
            ),
            "purpose": self.purpose,
            "status": self.status,
            "priority": self.priority,
            "authority_basis": list(
                self.authority_basis
            ),
            "provenance": dict(
                self.provenance
            ),
            "created_from": list(
                self.created_from
            ),
            "dependencies": list(
                self.dependencies
            ),
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
            "blockers": list(
                self.blockers
            ),
            "evidence_receipts": list(
                self.evidence_receipts
            ),
            "supersedes": list(
                self.supersedes
            ),
            "decomposition_children": list(
                self.decomposition_children
            ),
            "implementation_references": list(
                self.implementation_references
            ),
            "extension_slots": dict(
                self.extension_slots
            ),
            "created_at": (
                self.created_at
            ),
            "updated_at": (
                self.updated_at
            ),
            "authority_owner": OWNER,
            "authoritative": True,
        }


class LivingTaskEngine:
    TASK_REVISION_KIND = "niche.task.revision"
    TASK_EVENT_KIND = "niche.task.event"

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DATRIX,
    ) -> None:
        # db_path remains accepted as a compatibility argument for callers.
        self.db_path = Path(
            db_path
        ).resolve()
        self.datrix_path = self.db_path

        self.datrix_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _initialize(
        self,
    ) -> None:
        # Opening an absent datrix is intentionally idempotent. Do not
        # checkpoint an empty store merely by constructing the engine.
        StraubDatrix.open(
            self.datrix_path
        )

    def _open_datrix(
        self,
    ) -> StraubDatrix:
        return StraubDatrix.open(
            self.datrix_path
        )

    @staticmethod
    def _query_results(
        datrix: StraubDatrix,
        *,
        kinds: Sequence[str],
    ) -> tuple[dict[str, Any], ...]:
        projection = datrix.query().search(
            {
                "kinds": list(kinds),
                "include_invalid": False,
            }
        )
        return tuple(
            dict(record)
            for record in projection.get(
                "results",
                (),
            )
            if isinstance(
                record,
                Mapping,
            )
        )

    def _task_revision_records(
        self,
        datrix: StraubDatrix | None = None,
    ) -> tuple[dict[str, Any], ...]:
        active = (
            datrix
            if datrix is not None
            else self._open_datrix()
        )
        return self._query_results(
            active,
            kinds=(
                self.TASK_REVISION_KIND,
            ),
        )

    def _event_records(
        self,
        datrix: StraubDatrix | None = None,
    ) -> tuple[dict[str, Any], ...]:
        active = (
            datrix
            if datrix is not None
            else self._open_datrix()
        )
        return self._query_results(
            active,
            kinds=(
                self.TASK_EVENT_KIND,
            ),
        )

    @staticmethod
    def _record_payload(
        record: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = record.get(
            "payload",
            {},
        )
        if not isinstance(
            payload,
            Mapping,
        ):
            raise NicheTaskError(
                "invalid niche datrix record payload"
            )
        return dict(payload)

    def _latest_task_records(
        self,
        datrix: StraubDatrix | None = None,
    ) -> dict[str, dict[str, Any]]:
        latest: dict[
            str,
            dict[str, Any],
        ] = {}

        for record in self._task_revision_records(
            datrix
        ):
            payload = self._record_payload(
                record
            )
            task_id = normalize_identifier(
                payload.get(
                    "task_id"
                )
            )
            if not task_id:
                continue

            revision = int(
                payload.get(
                    "revision",
                    0,
                )
                or 0
            )
            current = latest.get(
                task_id
            )
            current_revision = (
                int(
                    self._record_payload(
                        current
                    ).get(
                        "revision",
                        0,
                    )
                    or 0
                )
                if current
                else -1
            )

            if (
                current is None
                or revision
                > current_revision
                or (
                    revision
                    == current_revision
                    and str(
                        record.get(
                            "id",
                            "",
                        )
                    )
                    > str(
                        current.get(
                            "id",
                            "",
                        )
                    )
                )
            ):
                latest[
                    task_id
                ] = record

        return latest

    def _task_from_record(
        self,
        record: Mapping[str, Any],
    ) -> Task:
        payload = self._record_payload(
            record
        )
        task = payload.get(
            "task",
            {},
        )
        if not isinstance(
            task,
            Mapping,
        ):
            raise NicheTaskError(
                "invalid niche task revision"
            )

        return Task(
            task_id=str(
                task["task_id"]
            ),
            owner=str(
                task["owner"]
            ),
            jurisdiction=str(
                task["jurisdiction"]
            ),
            purpose=str(
                task["purpose"]
            ),
            status=str(
                task["status"]
            ),
            priority=str(
                task["priority"]
            ),
            authority_basis=normalize_sequence(
                task.get(
                    "authority_basis"
                )
            ),
            provenance=dict(
                task.get(
                    "provenance"
                )
                or {}
            ),
            created_from=normalize_sequence(
                task.get(
                    "created_from"
                )
            ),
            dependencies=normalize_sequence(
                task.get(
                    "dependencies"
                )
            ),
            affected_instances=normalize_sequence(
                task.get(
                    "affected_instances"
                )
            ),
            compatibility_obligations=normalize_sequence(
                task.get(
                    "compatibility_obligations"
                )
            ),
            completion_condition=str(
                task.get(
                    "completion_condition",
                    "",
                )
            ),
            validation_budget=dict(
                task.get(
                    "validation_budget"
                )
                or {}
            ),
            blockers=normalize_sequence(
                task.get(
                    "blockers"
                )
            ),
            evidence_receipts=normalize_sequence(
                task.get(
                    "evidence_receipts"
                )
            ),
            supersedes=normalize_sequence(
                task.get(
                    "supersedes"
                )
            ),
            decomposition_children=normalize_sequence(
                task.get(
                    "decomposition_children"
                )
            ),
            implementation_references=normalize_sequence(
                task.get(
                    "implementation_references"
                )
            ),
            extension_slots=dict(
                task.get(
                    "extension_slots"
                )
                or {}
            ),
            created_at=str(
                task["created_at"]
            ),
            updated_at=str(
                task["updated_at"]
            ),
        )

    def _revision_number(
        self,
        task_id: str,
        datrix: StraubDatrix,
    ) -> int:
        record = self._latest_task_records(
            datrix
        ).get(
            task_id
        )
        if record is None:
            return 0
        return int(
            self._record_payload(
                record
            ).get(
                "revision",
                0,
            )
            or 0
        )

    def _history_from_datrix(
        self,
        datrix: StraubDatrix,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        events = []

        for record in self._event_records(
            datrix
        ):
            payload = self._record_payload(
                record
            )
            event = payload.get(
                "event",
                {},
            )
            if not isinstance(
                event,
                Mapping,
            ):
                continue
            value = dict(event)
            value[
                "sequence"
            ] = int(
                payload.get(
                    "sequence",
                    0,
                )
                or 0
            )
            value[
                "authoritative"
            ] = True
            events.append(
                value
            )

        events.sort(
            key=lambda value: (
                int(
                    value.get(
                        "sequence",
                        0,
                    )
                    or 0
                ),
                str(
                    value.get(
                        "event_id",
                        "",
                    )
                ),
            )
        )
        return tuple(events)

    def _next_event_sequence(
        self,
        datrix: StraubDatrix,
    ) -> int:
        history = self._history_from_datrix(
            datrix
        )
        return (
            int(
                history[-1][
                    "sequence"
                ]
            )
            + 1
            if history
            else 1
        )

    def _append_event(
        self,
        datrix: StraubDatrix,
        *,
        task_id: str,
        event_type: str,
        previous_state: str | None,
        new_state: str | None,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        history = self._history_from_datrix(
            datrix
        )
        previous_digest = (
            history[-1][
                "event_digest"
            ]
            if history
            else None
        )
        sequence = (
            int(
                history[-1][
                    "sequence"
                ]
            )
            + 1
            if history
            else 1
        )
        created_at = utc_now()

        event_body = {
            "schema": EVENT_SCHEMA,
            "task_id": task_id,
            "event_type": event_type,
            "previous_state": (
                previous_state
            ),
            "new_state": new_state,
            "payload": dict(payload),
            "created_at": created_at,
            "previous_event_digest": (
                previous_digest
            ),
            "owner": OWNER,
        }
        event_digest = digest(
            event_body
        )
        event_id = (
            "task-event:"
            + event_digest[:24]
        )
        event = {
            **event_body,
            "event_id": event_id,
            "event_digest": (
                event_digest
            ),
            "authoritative": True,
        }

        datrix.registry.substantiate(
            {
                "id": event_id,
                "kind": (
                    self.TASK_EVENT_KIND
                ),
                "status": "active",
                "authority": {
                    "owner": OWNER,
                    "authoritative": True,
                },
                "payload": {
                    "sequence": sequence,
                    "event": event,
                },
                "metadata": {
                    "profile": "workflow",
                    "logical_task_id": (
                        task_id
                    ),
                    "event_type": (
                        event_type
                    ),
                },
                "dependencies": [
                    task_id
                ],
                "relationships": [],
                "provenance": {
                    "owner": OWNER,
                    "source": "niche",
                },
                "lineage": {
                    "previous_event_digest": (
                        previous_digest
                    ),
                },
                "extensions": {
                    "niche_schema": (
                        EVENT_SCHEMA
                    ),
                },
            }
        )
        return event

    def _substantiate_task_revision(
        self,
        datrix: StraubDatrix,
        task: Task,
        *,
        event_digest: str,
    ) -> dict[str, Any]:
        revision = (
            self._revision_number(
                task.task_id,
                datrix,
            )
            + 1
        )
        task_projection = (
            task.authoritative_projection()
        )
        revision_identity = {
            "task_id": task.task_id,
            "revision": revision,
            "task": task_projection,
            "event_digest": event_digest,
        }
        revision_digest = digest(
            revision_identity
        )
        revision_id = (
            "niche-task-revision:"
            + revision_digest[:32]
        )

        return datrix.registry.substantiate(
            {
                "id": revision_id,
                "kind": (
                    self.TASK_REVISION_KIND
                ),
                "status": task.status,
                "authority": {
                    "owner": OWNER,
                    "authoritative": True,
                },
                "payload": {
                    "task_id": task.task_id,
                    "revision": revision,
                    "event_digest": (
                        event_digest
                    ),
                    "task": task_projection,
                },
                "metadata": {
                    "profile": "workflow",
                    "logical_task_id": (
                        task.task_id
                    ),
                    "revision": revision,
                },
                "dependencies": list(
                    task.dependencies
                ),
                "relationships": [],
                "provenance": dict(
                    task.provenance
                ),
                "lineage": {
                    "logical_task_id": (
                        task.task_id
                    ),
                    "revision": revision,
                    "event_digest": (
                        event_digest
                    ),
                },
                "extensions": {
                    "niche_schema": (
                        TASK_SCHEMA
                    ),
                },
            }
        )

    def _checkpoint_mutation(
        self,
        datrix: StraubDatrix,
        task: Task,
        *,
        event_type: str,
        previous_state: str | None,
        new_state: str | None,
        payload: Mapping[str, Any],
    ) -> Task:
        event = self._append_event(
            datrix,
            task_id=task.task_id,
            event_type=event_type,
            previous_state=previous_state,
            new_state=new_state,
            payload=payload,
        )
        self._substantiate_task_revision(
            datrix,
            task,
            event_digest=event[
                "event_digest"
            ],
        )
        datrix.checkpoint()
        return task

    @staticmethod
    def _task_replace(
        task: Task,
        **changes: Any,
    ) -> Task:
        values = {
            "task_id": task.task_id,
            "owner": task.owner,
            "jurisdiction": (
                task.jurisdiction
            ),
            "purpose": task.purpose,
            "status": task.status,
            "priority": task.priority,
            "authority_basis": (
                task.authority_basis
            ),
            "provenance": dict(
                task.provenance
            ),
            "created_from": (
                task.created_from
            ),
            "dependencies": (
                task.dependencies
            ),
            "affected_instances": (
                task.affected_instances
            ),
            "compatibility_obligations": (
                task.compatibility_obligations
            ),
            "completion_condition": (
                task.completion_condition
            ),
            "validation_budget": dict(
                task.validation_budget
            ),
            "blockers": task.blockers,
            "evidence_receipts": (
                task.evidence_receipts
            ),
            "supersedes": (
                task.supersedes
            ),
            "decomposition_children": (
                task.decomposition_children
            ),
            "implementation_references": (
                task.implementation_references
            ),
            "extension_slots": dict(
                task.extension_slots
            ),
            "created_at": (
                task.created_at
            ),
            "updated_at": (
                task.updated_at
            ),
        }
        values.update(
            changes
        )
        return Task(
            **values
        )

    def _graph_with_candidate(
        self,
        candidate: Task,
        *,
        creating: bool = False,
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        graph = self.dependency_map()
        if (
            creating
            and candidate.task_id
            in graph
        ):
            raise NicheTaskError(
                "task already exists: "
                + candidate.task_id
            )
        graph[
            candidate.task_id
        ] = tuple(
            candidate.dependencies
        )
        for dependency in (
            candidate.dependencies
        ):
            graph.setdefault(
                dependency,
                (),
            )
        return graph

    @staticmethod
    def _cycles_for_graph(
        graph: Mapping[
            str,
            Sequence[str],
        ],
    ) -> tuple[
        tuple[str, ...],
        ...,
    ]:
        state: dict[str, int] = {}
        stack: list[str] = []
        found: set[
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
                    found.add(
                        tuple(
                            stack[index:]
                            + [node]
                        )
                    )
                return

            state[node] = 1
            stack.append(
                node
            )
            for dependency in graph.get(
                node,
                (),
            ):
                visit(
                    dependency
                )
            stack.pop()
            state[node] = 2

        for node in sorted(
            graph
        ):
            visit(
                node
            )

        return tuple(
            sorted(found)
        )

    def get(
        self,
        task_id: str,
    ) -> Task:
        record = self._latest_task_records().get(
            task_id
        )
        if record is None:
            raise NicheTaskError(
                "unknown task: "
                + task_id
            )
        return self._task_from_record(
            record
        )

    def tasks(
        self,
    ) -> tuple[Task, ...]:
        latest = self._latest_task_records()
        return tuple(
            self._task_from_record(
                latest[task_id]
            )
            for task_id in sorted(
                latest
            )
        )

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
        purpose = str(
            purpose
        ).strip()
        owner = str(
            owner
        ).strip()
        jurisdiction = str(
            jurisdiction
        ).strip()
        completion_condition = str(
            completion_condition
        ).strip()

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
                "invalid task state: "
                + status
            )
        if priority not in PRIORITY_ORDER:
            raise NicheTaskError(
                "invalid priority: "
                + priority
            )

        normalized_dependencies = (
            normalize_sequence(
                dependencies
            )
        )
        resolved_id = stable_task_id(
            owner=owner,
            purpose=purpose,
            created_from=created_from,
            alias=task_id,
        )
        if (
            resolved_id
            in normalized_dependencies
        ):
            raise NicheTaskError(
                "task cannot depend on itself"
            )

        slots = dict(
            extension_slots or {}
        )
        if (
            "niche.execution"
            in slots
            and not isinstance(
                slots[
                    "niche.execution"
                ],
                Mapping,
            )
        ):
            raise NicheTaskError(
                "niche.execution extension "
                "must be a mapping"
            )

        now = utc_now()
        task = Task(
            task_id=resolved_id,
            owner=owner,
            jurisdiction=jurisdiction,
            purpose=purpose,
            status=status,
            priority=priority,
            authority_basis=authority,
            provenance=dict(
                provenance or {}
            ),
            created_from=normalize_sequence(
                created_from
            ),
            dependencies=(
                normalized_dependencies
            ),
            affected_instances=normalize_sequence(
                affected_instances
            ),
            compatibility_obligations=normalize_sequence(
                compatibility_obligations
            ),
            completion_condition=(
                completion_condition
            ),
            validation_budget=dict(
                validation_budget
                or {
                    "syntax_or_compile": True,
                    "focused_functional": 1,
                    "integration_or_startup": 1,
                }
            ),
            blockers=normalize_sequence(
                blockers
            ),
            evidence_receipts=normalize_sequence(
                evidence_receipts
            ),
            supersedes=normalize_sequence(
                supersedes
            ),
            decomposition_children=normalize_sequence(
                decomposition_children
            ),
            implementation_references=normalize_sequence(
                implementation_references
            ),
            extension_slots=slots,
            created_at=now,
            updated_at=now,
        )

        graph = self._graph_with_candidate(
            task,
            creating=True,
        )
        cycles = self._cycles_for_graph(
            graph
        )
        if cycles:
            raise NicheTaskError(
                "dependency cycle introduced: "
                + canonical_json(
                    cycles
                )
            )

        datrix = self._open_datrix()
        if (
            resolved_id
            in self._latest_task_records(
                datrix
            )
        ):
            raise NicheTaskError(
                "task already exists: "
                + resolved_id
            )

        self._checkpoint_mutation(
            datrix,
            task,
            event_type="created",
            previous_state=None,
            new_state=status,
            payload={
                "task_digest": digest(
                    task.authoritative_projection()
                ),
                "dependencies": list(
                    normalized_dependencies
                ),
            },
        )
        return self.get(
            resolved_id
        )

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
                "invalid task state: "
                + new_state
            )

        current = self.get(
            task_id
        )
        if (
            current.status
            in TERMINAL_STATES
        ):
            raise NicheTaskError(
                "terminal task state is immutable; "
                "supersede or create a regression task"
            )

        receipts = tuple(
            sorted(
                set(
                    current.evidence_receipts
                )
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

        unresolved = (
            self.unsatisfied_dependencies(
                task_id
            )
        )
        if (
            new_state
            in {
                "ready",
                "leased",
                "active",
                "completed",
            }
            and unresolved
        ):
            raise NicheTaskError(
                "task has unsatisfied dependencies: "
                + ", ".join(
                    unresolved
                )
            )

        intelligence = (
            self.execution_intelligence(
                current
            )
        )
        if (
            new_state
            in {
                "leased",
                "active",
                "completed",
            }
            and not intelligence[
                "eligible"
            ]
        ):
            reasons = intelligence[
                "ineligibility_reasons"
            ]
            if reasons:
                raise NicheTaskError(
                    "task is not execution eligible: "
                    + ", ".join(
                        reasons
                    )
                )

        updated = self._task_replace(
            current,
            status=new_state,
            evidence_receipts=receipts,
            updated_at=utc_now(),
        )
        datrix = self._open_datrix()
        self._checkpoint_mutation(
            datrix,
            updated,
            event_type="transition",
            previous_state=(
                current.status
            ),
            new_state=new_state,
            payload={
                "reason": reason,
                "evidence_receipts": list(
                    receipts
                ),
            },
        )
        return self.get(
            task_id
        )

    def update(
        self,
        task_id: str,
        **changes: Any,
    ) -> Task:
        current = self.get(
            task_id
        )
        if (
            current.status
            in TERMINAL_STATES
        ):
            raise NicheTaskError(
                "terminal task is immutable"
            )

        allowed = {
            "purpose",
            "priority",
            "completion_condition",
            "blockers",
            "affected_instances",
            "compatibility_obligations",
            "validation_budget",
            "implementation_references",
            "extension_slots",
            "dependencies",
        }
        unknown = (
            set(changes)
            - allowed
        )
        if unknown:
            raise NicheTaskError(
                "unsupported task update fields: "
                + ", ".join(
                    sorted(unknown)
                )
            )

        replacements: dict[
            str,
            Any,
        ] = {}
        payload: dict[
            str,
            Any,
        ] = {}

        if "purpose" in changes:
            purpose = str(
                changes["purpose"]
            ).strip()
            if not purpose:
                raise NicheTaskError(
                    "purpose is required"
                )
            replacements[
                "purpose"
            ] = purpose
            payload[
                "purpose"
            ] = purpose

        if "priority" in changes:
            priority = str(
                changes["priority"]
            )
            if (
                priority
                not in PRIORITY_ORDER
            ):
                raise NicheTaskError(
                    "invalid priority: "
                    + priority
                )
            replacements[
                "priority"
            ] = priority
            payload[
                "priority"
            ] = priority

        if (
            "completion_condition"
            in changes
        ):
            condition = str(
                changes[
                    "completion_condition"
                ]
            ).strip()
            if not condition:
                raise NicheTaskError(
                    "completion_condition "
                    "is required"
                )
            replacements[
                "completion_condition"
            ] = condition
            payload[
                "completion_condition"
            ] = condition

        for field in (
            "blockers",
            "affected_instances",
            "compatibility_obligations",
            "implementation_references",
        ):
            if field not in changes:
                continue
            value = normalize_sequence(
                changes[field]
            )
            replacements[
                field
            ] = value
            payload[
                field
            ] = list(
                value
            )

        if (
            "validation_budget"
            in changes
        ):
            value = changes[
                "validation_budget"
            ]
            if not isinstance(
                value,
                Mapping,
            ):
                raise NicheTaskError(
                    "validation_budget "
                    "must be a mapping"
                )
            replacements[
                "validation_budget"
            ] = dict(value)
            payload[
                "validation_budget"
            ] = dict(value)

        if (
            "extension_slots"
            in changes
        ):
            value = changes[
                "extension_slots"
            ]
            if not isinstance(
                value,
                Mapping,
            ):
                raise NicheTaskError(
                    "extension_slots "
                    "must be a mapping"
                )
            replacements[
                "extension_slots"
            ] = dict(value)
            payload[
                "extension_slots"
            ] = dict(value)

        if "dependencies" in changes:
            dependencies = normalize_sequence(
                changes[
                    "dependencies"
                ]
            )
            if task_id in dependencies:
                raise NicheTaskError(
                    "task cannot depend on itself"
                )
            replacements[
                "dependencies"
            ] = dependencies
            payload[
                "dependencies"
            ] = list(
                dependencies
            )

        if not replacements:
            return current

        replacements[
            "updated_at"
        ] = utc_now()
        updated = self._task_replace(
            current,
            **replacements,
        )
        graph = self._graph_with_candidate(
            updated
        )
        cycles = self._cycles_for_graph(
            graph
        )
        if cycles:
            raise NicheTaskError(
                "task graph contains a cycle "
                "after update: "
                + canonical_json(
                    cycles
                )
            )

        datrix = self._open_datrix()
        self._checkpoint_mutation(
            datrix,
            updated,
            event_type="updated",
            previous_state=(
                current.status
            ),
            new_state=(
                current.status
            ),
            payload=payload,
        )
        return self.get(
            task_id
        )

    def _write_extension_slots(
        self,
        task: Task,
        slots: Mapping[str, Any],
        *,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        updated = self._task_replace(
            task,
            extension_slots=dict(
                slots
            ),
            updated_at=utc_now(),
        )
        datrix = self._open_datrix()
        self._checkpoint_mutation(
            datrix,
            updated,
            event_type=event_type,
            previous_state=(
                task.status
            ),
            new_state=task.status,
            payload=payload,
        )

    def configure_execution(
        self,
        task_id: str,
        **policy_changes: Any,
    ) -> Task:
        task = self.get(
            task_id
        )
        if (
            task.status
            in TERMINAL_STATES
        ):
            raise NicheTaskError(
                "terminal task is immutable"
            )

        unknown = (
            set(policy_changes)
            - set(
                DEFAULT_EXECUTION_POLICY
            )
        )
        if unknown:
            raise NicheTaskError(
                "unknown execution policy fields: "
                + ", ".join(
                    sorted(unknown)
                )
            )

        policy = execution_policy(
            task.extension_slots
        )
        policy.update(
            policy_changes
        )

        retry_limit = int(
            policy[
                "retry_limit"
            ]
            or 0
        )
        if retry_limit < 0:
            raise NicheTaskError(
                "retry_limit cannot be negative"
            )

        lease_seconds = int(
            policy[
                "lease_seconds"
            ]
            or 0
        )
        if lease_seconds < 1:
            raise NicheTaskError(
                "lease_seconds must be positive"
            )

        multiplier = float(
            policy[
                "retry_backoff_multiplier"
            ]
            or 1.0
        )
        if multiplier < 1.0:
            raise NicheTaskError(
                "retry_backoff_multiplier "
                "must be at least 1"
            )

        slots = dict(
            task.extension_slots
        )
        slots[
            "niche.execution"
        ] = policy
        self._write_extension_slots(
            task,
            slots,
            event_type=(
                "execution-policy-updated"
            ),
            payload={
                "execution_policy": (
                    policy
                ),
            },
        )
        return self.get(
            task_id
        )

    def lease(
        self,
        task_id: str,
        *,
        lease_owner: str,
        lease_seconds: int | None = None,
        reason: str | None = None,
    ) -> Task:
        task = self.get(
            task_id
        )
        owner = str(
            lease_owner
        ).strip()
        if not owner:
            raise NicheTaskError(
                "lease_owner is required"
            )

        intelligence = (
            self.execution_intelligence(
                task
            )
        )
        if not intelligence[
            "eligible"
        ]:
            raise NicheTaskError(
                "task is not execution eligible: "
                + ", ".join(
                    intelligence[
                        "ineligibility_reasons"
                    ]
                )
            )

        policy = execution_policy(
            task.extension_slots
        )
        duration = int(
            lease_seconds
            if lease_seconds is not None
            else policy[
                "lease_seconds"
            ]
        )
        if duration < 1:
            raise NicheTaskError(
                "lease duration must be positive"
            )

        now = datetime.now(
            timezone.utc
        )
        expires = (
            now
            + timedelta(
                seconds=duration
            )
        )
        policy[
            "lease_owner"
        ] = owner
        policy[
            "lease_acquired_at"
        ] = now.isoformat()
        policy[
            "lease_expires_at"
        ] = expires.isoformat()
        policy[
            "attempt"
        ] = int(
            policy[
                "attempt"
            ]
            or 0
        ) + 1
        policy[
            "last_attempt_at"
        ] = now.isoformat()

        slots = dict(
            task.extension_slots
        )
        slots[
            "niche.execution"
        ] = policy
        updated = self._task_replace(
            task,
            status="leased",
            extension_slots=slots,
            updated_at=now.isoformat(),
        )
        datrix = self._open_datrix()
        self._checkpoint_mutation(
            datrix,
            updated,
            event_type="leased",
            previous_state=(
                task.status
            ),
            new_state="leased",
            payload={
                "lease_owner": owner,
                "lease_seconds": (
                    duration
                ),
                "lease_expires_at": (
                    expires.isoformat()
                ),
                "attempt": policy[
                    "attempt"
                ],
                "reason": reason,
            },
        )
        return self.get(
            task_id
        )

    def release(
        self,
        task_id: str,
        *,
        reason: str | None = None,
        new_state: str = "ready",
    ) -> Task:
        if (
            new_state
            not in {
                "accepted",
                "ready",
                "blocked",
                "deferred",
            }
        ):
            raise NicheTaskError(
                "invalid release state: "
                + new_state
            )

        task = self.get(
            task_id
        )
        policy = execution_policy(
            task.extension_slots
        )
        previous_owner = policy[
            "lease_owner"
        ]
        policy[
            "lease_owner"
        ] = None
        policy[
            "lease_acquired_at"
        ] = None
        policy[
            "lease_expires_at"
        ] = None

        slots = dict(
            task.extension_slots
        )
        slots[
            "niche.execution"
        ] = policy
        updated = self._task_replace(
            task,
            status=new_state,
            extension_slots=slots,
            updated_at=utc_now(),
        )
        datrix = self._open_datrix()
        self._checkpoint_mutation(
            datrix,
            updated,
            event_type="lease-released",
            previous_state=(
                task.status
            ),
            new_state=new_state,
            payload={
                "lease_owner": (
                    previous_owner
                ),
                "reason": reason,
            },
        )
        return self.get(
            task_id
        )

    def dependency_map(
        self,
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        result: dict[
            str,
            set[str],
        ] = {}

        for task in self.tasks():
            result.setdefault(
                task.task_id,
                set(),
            ).update(
                task.dependencies
            )
            for dependency in (
                task.dependencies
            ):
                result.setdefault(
                    dependency,
                    set(),
                )

        return {
            key: tuple(
                sorted(value)
            )
            for key, value
            in sorted(
                result.items()
            )
        }

    def reverse_dependencies(
        self,
    ) -> dict[
        str,
        tuple[str, ...],
    ]:
        reverse: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for (
            task_id,
            dependencies,
        ) in self.dependency_map().items():
            reverse.setdefault(
                task_id,
                set(),
            )

            for dependency in dependencies:
                reverse[
                    dependency
                ].add(
                    task_id
                )

        return {
            key: tuple(
                sorted(value)
            )
            for key, value
            in sorted(
                reverse.items()
            )
        }

    def transitive_dependencies(
        self,
        task_id: str,
    ) -> tuple[str, ...]:
        graph = (
            self.dependency_map()
        )

        seen: set[str] = set()

        pending = list(
            graph.get(
                task_id,
                (),
            )
        )

        while pending:
            current = (
                pending.pop()
            )

            if current in seen:
                continue

            seen.add(
                current
            )

            pending.extend(
                graph.get(
                    current,
                    (),
                )
            )

        return tuple(
            sorted(seen)
        )

    def transitive_dependents(
        self,
        task_id: str,
    ) -> tuple[str, ...]:
        graph = (
            self.reverse_dependencies()
        )

        seen: set[str] = set()

        pending = list(
            graph.get(
                task_id,
                (),
            )
        )

        while pending:
            current = (
                pending.pop()
            )

            if current in seen:
                continue

            seen.add(
                current
            )

            pending.extend(
                graph.get(
                    current,
                    (),
                )
            )

        return tuple(
            sorted(seen)
        )

    def unsatisfied_dependencies(
        self,
        task_id: str,
    ) -> tuple[str, ...]:
        task = self.get(
            task_id
        )

        unsatisfied: list[str] = []

        for dependency in (
            task.dependencies
        ):
            try:
                dependency_task = (
                    self.get(
                        dependency
                    )
                )
            except NicheTaskError:
                unsatisfied.append(
                    dependency
                )
                continue

            if (
                dependency_task.status
                not in SATISFIED_STATES
            ):
                unsatisfied.append(
                    dependency
                )

        return tuple(
            sorted(
                unsatisfied
            )
        )

    def cycles(
        self,
    ) -> tuple[
        tuple[str, ...],
        ...,
    ]:
        graph = (
            self.dependency_map()
        )

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
                    index = (
                        stack.index(
                            node
                        )
                    )

                    cycle = tuple(
                        stack[index:]
                        + [node]
                    )

                    cycles.add(
                        cycle
                    )

                return

            state[node] = 1

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

            state[node] = 2

        for node in sorted(
            graph
        ):
            visit(node)

        return tuple(
            sorted(cycles)
        )

    def topological_order(
        self,
    ) -> tuple[str, ...]:
        graph = (
            self.dependency_map()
        )

        reverse = (
            self.reverse_dependencies()
        )

        indegree = {
            task_id: len(
                dependencies
            )
            for (
                task_id,
                dependencies,
            ) in graph.items()
        }

        queue = [
            task_id
            for (
                task_id,
                count,
            ) in indegree.items()
            if count == 0
        ]

        queue.sort()

        ordered: list[str] = []

        while queue:
            node = queue.pop(0)

            ordered.append(
                node
            )

            for dependent in (
                reverse.get(
                    node,
                    (),
                )
            ):
                indegree[
                    dependent
                ] -= 1

                if (
                    indegree[
                        dependent
                    ]
                    == 0
                ):
                    queue.append(
                        dependent
                    )

                    queue.sort()

        if (
            len(ordered)
            != len(indegree)
        ):
            raise NicheTaskError(
                "task graph contains a cycle"
            )

        return tuple(
            ordered
        )

    def critical_path(
        self,
    ) -> tuple[str, ...]:
        graph = (
            self.dependency_map()
        )

        if not graph:
            return ()

        order = (
            self.topological_order()
        )

        distance: dict[
            str,
            int,
        ] = {}

        predecessor: dict[
            str,
            str | None,
        ] = {}

        for task_id in order:
            dependencies = (
                graph.get(
                    task_id,
                    (),
                )
            )

            if not dependencies:
                distance[
                    task_id
                ] = 1

                predecessor[
                    task_id
                ] = None

                continue

            parent = max(
                dependencies,
                key=lambda value: (
                    distance.get(
                        value,
                        0,
                    ),
                    value,
                ),
            )

            distance[
                task_id
            ] = (
                distance.get(
                    parent,
                    0,
                )
                + 1
            )

            predecessor[
                task_id
            ] = parent

        end = max(
            order,
            key=lambda value: (
                distance.get(
                    value,
                    0,
                ),
                value,
            ),
        )

        path: list[str] = []

        current: str | None = (
            end
        )

        while current is not None:
            path.append(
                current
            )

            current = (
                predecessor.get(
                    current
                )
            )

        path.reverse()

        return tuple(path)

    def retry_delay_seconds(
        self,
        task: Task,
    ) -> int:
        policy = execution_policy(
            task.extension_slots
        )

        attempt = max(
            1,
            int(
                policy[
                    "attempt"
                ]
                or 1
            ),
        )

        base = max(
            0,
            int(
                policy[
                    "retry_backoff_seconds"
                ]
                or 0
            ),
        )

        multiplier = max(
            1.0,
            float(
                policy[
                    "retry_backoff_multiplier"
                ]
                or 1.0
            ),
        )

        maximum = max(
            base,
            int(
                policy[
                    "retry_backoff_max_seconds"
                ]
                or base
            ),
        )

        delay = (
            base
            * math.pow(
                multiplier,
                max(
                    0,
                    attempt - 1,
                ),
            )
        )

        return int(
            min(
                delay,
                maximum,
            )
        )

    def execution_intelligence(
        self,
        task: Task | str,
    ) -> dict[str, Any]:
        if isinstance(
            task,
            str,
        ):
            task = self.get(
                task
            )

        now = datetime.now(
            timezone.utc
        )

        policy = execution_policy(
            task.extension_slots
        )

        unresolved = (
            self.unsatisfied_dependencies(
                task.task_id
            )
        )

        dependents = (
            self.reverse_dependencies().get(
                task.task_id,
                (),
            )
        )

        downstream = (
            self.transitive_dependents(
                task.task_id
            )
        )

        not_before = (
            parse_datetime(
                policy[
                    "not_before"
                ]
            )
        )

        deadline = (
            parse_datetime(
                policy[
                    "deadline"
                ]
            )
        )

        lease_expires = (
            parse_datetime(
                policy[
                    "lease_expires_at"
                ]
            )
        )

        last_failure = (
            parse_datetime(
                policy[
                    "last_failure_at"
                ]
            )
        )

        attempt = int(
            policy[
                "attempt"
            ]
            or 0
        )

        retry_limit = int(
            policy[
                "retry_limit"
            ]
            or 0
        )

        retry_remaining = max(
            0,
            retry_limit
            - max(
                0,
                attempt - 1,
            ),
        )

        retry_delay = (
            self.retry_delay_seconds(
                task
            )
        )

        retry_eligible_at = None

        if last_failure:
            retry_eligible_at = (
                last_failure
                + timedelta(
                    seconds=retry_delay
                )
            )

        stale_lease = bool(
            task.status == "leased"
            and lease_expires
            and lease_expires
            <= now
        )

        scheduled_wait = bool(
            not_before
            and not_before > now
        )

        retry_wait = bool(
            retry_eligible_at
            and retry_eligible_at
            > now
        )

        deadline_overdue = bool(
            deadline
            and deadline < now
            and task.status
            not in TERMINAL_STATES
        )

        deadline_seconds = (
            (
                deadline
                - now
            ).total_seconds()
            if deadline
            else None
        )

        approval_missing = bool(
            policy[
                "manual_approval_required"
            ]
            and not policy[
                "approved"
            ]
        )

        cancellation_requested = bool(
            policy[
                "cancellation_requested"
            ]
        )

        reasons: list[str] = []

        if (
            task.status
            in TERMINAL_STATES
        ):
            reasons.append(
                "terminal"
            )

        if task.blockers:
            reasons.append(
                "explicit-blocker"
            )

        if unresolved:
            reasons.append(
                "unsatisfied-dependency"
            )

        if approval_missing:
            reasons.append(
                "approval-required"
            )

        if scheduled_wait:
            reasons.append(
                "not-before"
            )

        if retry_wait:
            reasons.append(
                "retry-backoff"
            )

        if cancellation_requested:
            reasons.append(
                "cancellation-requested"
            )

        eligible = (
            task.status
            in EXECUTABLE_STATES
            and not reasons
        )

        age_seconds = 0.0

        created = (
            parse_datetime(
                task.created_at
            )
        )

        if created:
            age_seconds = max(
                0.0,
                (
                    now
                    - created
                ).total_seconds(),
            )

        age_days = (
            age_seconds
            / 86400.0
        )

        aging_bonus = min(
            120.0,
            age_days * 4.0,
        )

        fanout_bonus = min(
            150.0,
            len(
                downstream
            )
            * 5.0,
        )

        deadline_bonus = 0.0

        if (
            deadline_seconds
            is not None
        ):
            if (
                deadline_seconds
                <= 0
            ):
                deadline_bonus = (
                    180.0
                )
            elif (
                deadline_seconds
                <= 86400
            ):
                deadline_bonus = (
                    120.0
                )
            elif (
                deadline_seconds
                <= 604800
            ):
                deadline_bonus = (
                    60.0
                )

        blocker_penalty = (
            120.0
            if task.blockers
            else 0.0
        )

        dependency_penalty = (
            min(
                180.0,
                len(
                    unresolved
                )
                * 45.0,
            )
        )

        score = (
            PRIORITY_WEIGHT.get(
                task.priority,
                0.0,
            )
            + STATUS_WEIGHT.get(
                task.status,
                0.0,
            )
            + aging_bonus
            + fanout_bonus
            + deadline_bonus
            - blocker_penalty
            - dependency_penalty
        )

        if not eligible:
            score -= 250.0

        evidence_complete = bool(
            task.evidence_receipts
        )

        starvation_risk = bool(
            task.status
            in EXECUTABLE_STATES
            and age_days >= 7
            and task.priority
            not in {
                "critical",
                "high",
            }
        )

        dependency_risk = min(
            1.0,
            (
                len(unresolved)
                + len(
                    task.blockers
                )
            )
            / max(
                1,
                len(
                    task.dependencies
                )
                + len(
                    task.blockers
                ),
            ),
        )

        blast_radius = len(
            downstream
        )

        intervention_reasons: list[
            str
        ] = []

        if stale_lease:
            intervention_reasons.append(
                "stale-lease"
            )

        if deadline_overdue:
            intervention_reasons.append(
                "deadline-overdue"
            )

        if starvation_risk:
            intervention_reasons.append(
                "starvation-risk"
            )

        if approval_missing:
            intervention_reasons.append(
                "approval-required"
            )

        if (
            task.status == "blocked"
            and not task.blockers
            and not unresolved
        ):
            intervention_reasons.append(
                "blocked-without-visible-cause"
            )

        if (
            task.status
            == "completed"
            and not evidence_complete
        ):
            intervention_reasons.append(
                "completed-without-evidence"
            )

        return {
            "schema": (
                EXECUTION_SCHEMA
            ),
            "task_id": (
                task.task_id
            ),
            "eligible": eligible,
            "ineligibility_reasons": (
                sorted(
                    set(reasons)
                )
            ),
            "execution_policy": (
                policy
            ),
            "attempt": attempt,
            "retry_limit": (
                retry_limit
            ),
            "retry_remaining": (
                retry_remaining
            ),
            "retry_delay_seconds": (
                retry_delay
            ),
            "retry_eligible_at": (
                retry_eligible_at.isoformat()
                if retry_eligible_at
                else None
            ),
            "scheduled_wait": (
                scheduled_wait
            ),
            "not_before": (
                not_before.isoformat()
                if not_before
                else None
            ),
            "deadline": (
                deadline.isoformat()
                if deadline
                else None
            ),
            "deadline_seconds": (
                deadline_seconds
            ),
            "deadline_overdue": (
                deadline_overdue
            ),
            "stale_lease": (
                stale_lease
            ),
            "lease_owner": (
                policy[
                    "lease_owner"
                ]
            ),
            "lease_expires_at": (
                lease_expires.isoformat()
                if lease_expires
                else None
            ),
            "manual_approval_required": (
                bool(
                    policy[
                        "manual_approval_required"
                    ]
                )
            ),
            "approved": bool(
                policy[
                    "approved"
                ]
            ),
            "cancellation_requested": (
                cancellation_requested
            ),
            "resumable": bool(
                policy[
                    "resumable"
                ]
            ),
            "checkpoint_reference": (
                policy[
                    "checkpoint_reference"
                ]
            ),
            "idempotency_key": (
                policy[
                    "idempotency_key"
                ]
            ),
            "cache_key": (
                policy[
                    "cache_key"
                ]
            ),
            "cache_ttl_seconds": (
                policy[
                    "cache_ttl_seconds"
                ]
            ),
            "concurrency_pool": (
                policy[
                    "concurrency_pool"
                ]
            ),
            "concurrency_limit": (
                policy[
                    "concurrency_limit"
                ]
            ),
            "resource_claims": list(
                normalize_sequence(
                    policy[
                        "resource_claims"
                    ]
                )
            ),
            "failure_class": (
                policy[
                    "failure_class"
                ]
            ),
            "age_days": (
                round(
                    age_days,
                    4,
                )
            ),
            "aging_bonus": (
                round(
                    aging_bonus,
                    4,
                )
            ),
            "priority_score": (
                round(
                    score,
                    4,
                )
            ),
            "starvation_risk": (
                starvation_risk
            ),
            "dependency_risk": (
                round(
                    dependency_risk,
                    4,
                )
            ),
            "direct_fan_out": len(
                dependents
            ),
            "blast_radius": (
                blast_radius
            ),
            "downstream_dependents": (
                list(downstream)
            ),
            "evidence_complete": (
                evidence_complete
            ),
            "intervention_required": (
                bool(
                    intervention_reasons
                )
            ),
            "intervention_reasons": (
                intervention_reasons
            ),
            "authoritative": False,
            "authority_effect": (
                "none"
            ),
            "rebuildable": True,
        }

    def focus_score(
        self,
        task: Task | str,
    ) -> float:
        return float(
            self.execution_intelligence(
                task
            )[
                "priority_score"
            ]
        )

    def ready_tasks(
        self,
    ) -> tuple[Task, ...]:
        candidates: list[
            Task
        ] = []

        for task in self.tasks():
            intelligence = (
                self.execution_intelligence(
                    task
                )
            )

            if (
                intelligence[
                    "eligible"
                ]
            ):
                candidates.append(
                    task
                )

        candidates.sort(
            key=lambda task: (
                -self.focus_score(
                    task
                ),
                PRIORITY_ORDER.get(
                    task.priority,
                    99,
                ),
                task.created_at,
                task.task_id,
            )
        )

        return tuple(
            candidates
        )

    def newly_unblocked(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            task.task_id
            for task
            in self.ready_tasks()
            if (
                task.status
                == "accepted"
            )
        )

    def bottlenecks(
        self,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        reverse = (
            self.reverse_dependencies()
        )

        values = []

        for (
            task_id,
            dependents,
        ) in reverse.items():
            if not dependents:
                continue

            downstream = (
                self.transitive_dependents(
                    task_id
                )
            )

            values.append(
                {
                    "task_id": (
                        task_id
                    ),
                    "fan_out": len(
                        dependents
                    ),
                    "blast_radius": len(
                        downstream
                    ),
                    "dependents": list(
                        dependents
                    ),
                    "downstream_dependents": list(
                        downstream
                    ),
                }
            )

        values.sort(
            key=lambda value: (
                -value[
                    "blast_radius"
                ],
                -value[
                    "fan_out"
                ],
                value[
                    "task_id"
                ],
            )
        )

        return tuple(
            values
        )

    def intervention_queue(
        self,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        values: list[
            dict[str, Any]
        ] = []

        for task in self.tasks():
            intelligence = (
                self.execution_intelligence(
                    task
                )
            )

            if not intelligence[
                "intervention_required"
            ]:
                continue

            values.append(
                {
                    "task_id": (
                        task.task_id
                    ),
                    "purpose": (
                        task.purpose
                    ),
                    "status": (
                        task.status
                    ),
                    "priority": (
                        task.priority
                    ),
                    "reasons": (
                        intelligence[
                            "intervention_reasons"
                        ]
                    ),
                    "blast_radius": (
                        intelligence[
                            "blast_radius"
                        ]
                    ),
                    "priority_score": (
                        intelligence[
                            "priority_score"
                        ]
                    ),
                }
            )

        values.sort(
            key=lambda value: (
                -value[
                    "blast_radius"
                ],
                -value[
                    "priority_score"
                ],
                value[
                    "task_id"
                ],
            )
        )

        return tuple(
            values
        )

    def history(
        self,
        task_id: str | None = None,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        events = self._history_from_datrix(
            self._open_datrix()
        )
        if task_id is None:
            return events
        return tuple(
            event
            for event in events
            if event.get(
                "task_id"
            )
            == task_id
        )

    def validate_history_chain(
        self,
    ) -> tuple[str, ...]:
        errors: list[str] = []

        previous_digest = None

        for event in self.history():
            body = {
                "schema": EVENT_SCHEMA,
                "task_id": (
                    event[
                        "task_id"
                    ]
                ),
                "event_type": (
                    event[
                        "event_type"
                    ]
                ),
                "previous_state": (
                    event[
                        "previous_state"
                    ]
                ),
                "new_state": (
                    event[
                        "new_state"
                    ]
                ),
                "payload": (
                    event[
                        "payload"
                    ]
                ),
                "created_at": (
                    event[
                        "created_at"
                    ]
                ),
                "previous_event_digest": (
                    event[
                        "previous_event_digest"
                    ]
                ),
                "owner": OWNER,
            }

            expected = digest(
                body
            )

            if (
                event[
                    "previous_event_digest"
                ]
                != previous_digest
            ):
                errors.append(
                    "broken previous-event link: "
                    + event[
                        "event_id"
                    ]
                )

            if (
                event[
                    "event_digest"
                ]
                != expected
            ):
                errors.append(
                    "event digest mismatch: "
                    + event[
                        "event_id"
                    ]
                )

            previous_digest = (
                event[
                    "event_digest"
                ]
            )

        return tuple(
            errors
        )

    def project(
        self,
    ) -> dict[str, Any]:
        tasks = self.tasks()

        reverse = (
            self.reverse_dependencies()
        )

        cycles = (
            self.cycles()
        )

        projected_tasks = []

        for task in tasks:
            value = (
                task.authoritative_projection()
            )

            value[
                "dependents"
            ] = list(
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
                "transitive_dependents"
            ] = list(
                self.transitive_dependents(
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

            intelligence = (
                self.execution_intelligence(
                    task
                )
            )

            value[
                "ready"
            ] = intelligence[
                "eligible"
            ]

            value[
                "execution_intelligence"
            ] = intelligence

            value[
                "focus_score"
            ] = intelligence[
                "priority_score"
            ]

            value[
                "authoritative"
            ] = False

            value[
                "authority_effect"
            ] = "none"

            value[
                "rebuildable"
            ] = True

            projected_tasks.append(
                value
            )

        payload = {
            "schema": (
                PROJECTION_SCHEMA
            ),
            "owner": OWNER,
            "task_count": len(
                tasks
            ),
            "tasks": (
                projected_tasks
            ),
            "topological_order": (
                list(
                    self.topological_order()
                )
                if not cycles
                else []
            ),
            "critical_path": list(
                self.critical_path()
                if not cycles
                else ()
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
            "intervention_queue": list(
                self.intervention_queue()
            ),
            "history_chain_errors": list(
                self.validate_history_chain()
            ),
            "authoritative": False,
            "authority_effect": (
                "none"
            ),
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def dashboard(
        self,
    ) -> dict[str, Any]:
        tasks = self.tasks()

        ready = [
            task
            for task in tasks
            if self.execution_intelligence(
                task
            )[
                "eligible"
            ]
        ]

        ready.sort(
            key=lambda value: (
                -self.focus_score(
                    value
                ),
                value.task_id,
            )
        )

        blocked = []

        overdue = []

        stale_leases = []

        starvation = []

        for task in tasks:
            intelligence = (
                self.execution_intelligence(
                    task
                )
            )

            if (
                task.status
                == "blocked"
                or task.blockers
                or intelligence[
                    "ineligibility_reasons"
                ]
                and task.status
                in EXECUTABLE_STATES
            ):
                blocked.append(
                    task.task_id
                )

            if intelligence[
                "deadline_overdue"
            ]:
                overdue.append(
                    task.task_id
                )

            if intelligence[
                "stale_lease"
            ]:
                stale_leases.append(
                    task.task_id
                )

            if intelligence[
                "starvation_risk"
            ]:
                starvation.append(
                    task.task_id
                )

        recent = list(
            self.history()
        )[-25:]

        payload = {
            "schema": (
                DASHBOARD_SCHEMA
            ),
            "owner": OWNER,
            "task_authority_owner": (
                OWNER
            ),
            "task_count": len(
                tasks
            ),
            "ready_queue": [
                {
                    **task.authoritative_projection(),
                    "ready": True,
                    "focus_score": (
                        self.focus_score(
                            task
                        )
                    ),
                    "execution_intelligence": (
                        self.execution_intelligence(
                            task
                        )
                    ),
                    "authoritative": False,
                    "authority_effect": (
                        "none"
                    ),
                    "rebuildable": True,
                }
                for task in ready
            ],
            "blocked": sorted(
                set(blocked)
            ),
            "overdue": sorted(
                overdue
            ),
            "stale_leases": sorted(
                stale_leases
            ),
            "starvation_risk": sorted(
                starvation
            ),
            "critical_path": list(
                self.critical_path()
                if not self.cycles()
                else ()
            ),
            "bottlenecks": list(
                self.bottlenecks()
            ),
            "newly_unblocked": list(
                self.newly_unblocked()
            ),
            "intervention_queue": list(
                self.intervention_queue()
            ),
            "recent_updates": (
                recent
            ),
            "health": (
                self.health()
            ),
            "projection_only": True,
            "authoritative": False,
            "authority_effect": (
                "none"
            ),
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

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

        for task in graph[
            "tasks"
        ]:
            domain = task.get(
                "extension_slots",
                {},
            ).get(
                "masterplan_domain",
                "runtime",
            )

            if domain not in domains:
                domain = "runtime"

            domains[
                domain
            ].append(
                task[
                    "task_id"
                ]
            )

        payload = {
            "schema": (
                MASTERPLAN_SCHEMA
            ),
            "owner": OWNER,
            "domains": domains,
            "ready": [
                task.task_id
                for task
                in self.ready_tasks()
            ],
            "blocked": [
                task.task_id
                for task
                in self.tasks()
                if (
                    task.status
                    == "blocked"
                    or task.blockers
                    or self.unsatisfied_dependencies(
                        task.task_id
                    )
                )
            ],
            "completed": [
                task.task_id
                for task
                in self.tasks()
                if (
                    task.status
                    == "completed"
                )
            ],
            "critical_path": (
                graph[
                    "critical_path"
                ]
            ),
            "intervention_queue": (
                graph[
                    "intervention_queue"
                ]
            ),
            "task_graph_digest": (
                graph[
                    "digest"
                ]
            ),
            "authoritative": False,
            "authority_effect": (
                "none"
            ),
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        cycles = self.cycles()

        history_errors = (
            self.validate_history_chain()
        )

        tasks = self.tasks()

        stale_leases = []

        for task in tasks:
            intelligence = (
                self.execution_intelligence(
                    task
                )
            )

            if intelligence[
                "stale_lease"
            ]:
                stale_leases.append(
                    task.task_id
                )

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "mechanics_owner": (
                MECHANICS_OWNER
            ),
            "datrix": str(
                self.datrix_path
            ),
            "datrix_profile": (
                "workflow"
            ),
            "storage_backend": (
                "straub-datrix"
            ),
            "task_count": len(
                tasks
            ),
            "task_governance_owner": (
                OWNER
            ),
            "task_transition_owner": (
                OWNER
            ),
            "masterplan_projection_owner": (
                OWNER
            ),
            "dryve_may_govern_tasks": (
                False
            ),
            "dryve_may_transition_tasks": (
                False
            ),
            "direct_dependency_storage": (
                True
            ),
            "reverse_dependencies_derived": (
                True
            ),
            "transitive_dependencies_derived": (
                True
            ),
            "transitive_dependents_derived": (
                True
            ),
            "critical_path_derived": (
                True
            ),
            "execution_intelligence_derived": (
                True
            ),
            "priority_aging_derived": (
                True
            ),
            "blast_radius_derived": (
                True
            ),
            "dependency_risk_derived": (
                True
            ),
            "intervention_queue_derived": (
                True
            ),
            "retry_policy_supported": (
                True
            ),
            "retry_backoff_supported": (
                True
            ),
            "timeout_budget_supported": (
                True
            ),
            "execution_leases_supported": (
                True
            ),
            "stale_lease_detection": (
                True
            ),
            "concurrency_policy_supported": (
                True
            ),
            "resource_claims_supported": (
                True
            ),
            "trigger_rules_supported": (
                True
            ),
            "manual_approval_supported": (
                True
            ),
            "scheduled_eligibility_supported": (
                True
            ),
            "deadline_pressure_supported": (
                True
            ),
            "checkpoint_metadata_supported": (
                True
            ),
            "resumability_metadata_supported": (
                True
            ),
            "failure_classification_supported": (
                True
            ),
            "cancellation_metadata_supported": (
                True
            ),
            "idempotency_metadata_supported": (
                True
            ),
            "cache_metadata_supported": (
                True
            ),
            "starvation_detection": (
                True
            ),
            "evidence_completeness_projection": (
                True
            ),
            "immutable_history": (
                True
            ),
            "history_chain_valid": (
                not history_errors
            ),
            "cycle_free": (
                not cycles
            ),
            "cycles": [
                list(cycle)
                for cycle in cycles
            ],
            "history_errors": list(
                history_errors
            ),
            "stale_leases": (
                sorted(
                    stale_leases
                )
            ),
            "authoritative_task_store": (
                True
            ),
            "projection_authoritative": (
                False
            ),
        }

        payload[
            "healthy"
        ] = (
            payload[
                "history_chain_valid"
            ]
            and payload[
                "cycle_free"
            ]
        )

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def engine(
    db_path: str | Path = DEFAULT_DATRIX,
) -> LivingTaskEngine:
    return LivingTaskEngine(
        db_path
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Niche persistent living task engine"
        )
    )

    parser.add_argument(
        "--datrix",
        "--db",
        dest="datrix",
        default=str(
            DEFAULT_DATRIX
        ),
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    subparsers.add_parser(
        "health"
    )

    subparsers.add_parser(
        "list"
    )

    subparsers.add_parser(
        "ready"
    )

    subparsers.add_parser(
        "graph"
    )

    subparsers.add_parser(
        "dashboard"
    )

    subparsers.add_parser(
        "masterplan"
    )

    history_parser = (
        subparsers.add_parser(
            "history"
        )
    )

    history_parser.add_argument(
        "--task-id"
    )

    intelligence_parser = (
        subparsers.add_parser(
            "intelligence"
        )
    )

    intelligence_parser.add_argument(
        "task_id"
    )

    subparsers.add_parser(
        "interventions"
    )

    create_parser = (
        subparsers.add_parser(
            "create"
        )
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
        choices=tuple(
            PRIORITY_ORDER
        ),
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
        subparsers.add_parser(
            "transition"
        )
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

    lease_parser = (
        subparsers.add_parser(
            "lease"
        )
    )

    lease_parser.add_argument(
        "task_id"
    )

    lease_parser.add_argument(
        "--owner",
        required=True,
    )

    lease_parser.add_argument(
        "--seconds",
        type=int,
    )

    lease_parser.add_argument(
        "--reason",
    )

    release_parser = (
        subparsers.add_parser(
            "release"
        )
    )

    release_parser.add_argument(
        "task_id"
    )

    release_parser.add_argument(
        "--state",
        choices=(
            "accepted",
            "ready",
            "blocked",
            "deferred",
        ),
        default="ready",
    )

    release_parser.add_argument(
        "--reason",
    )

    execution_parser = (
        subparsers.add_parser(
            "execution"
        )
    )

    execution_parser.add_argument(
        "task_id"
    )

    execution_parser.add_argument(
        "--retry-limit",
        type=int,
    )

    execution_parser.add_argument(
        "--timeout-seconds",
        type=int,
    )

    execution_parser.add_argument(
        "--lease-seconds",
        type=int,
    )

    execution_parser.add_argument(
        "--not-before",
    )

    execution_parser.add_argument(
        "--deadline",
    )

    execution_parser.add_argument(
        "--approval-required",
        action="store_true",
    )

    execution_parser.add_argument(
        "--approve",
        action="store_true",
    )

    execution_parser.add_argument(
        "--resumable",
        action="store_true",
    )

    execution_parser.add_argument(
        "--checkpoint",
    )

    execution_parser.add_argument(
        "--idempotency-key",
    )

    execution_parser.add_argument(
        "--concurrency-pool",
    )

    return parser


def main() -> int:
    args = (
        build_parser()
        .parse_args()
    )

    runtime = engine(
        args.datrix
    )

    if (
        args.command
        == "health"
    ):
        output: Any = (
            runtime.health()
        )

    elif (
        args.command
        == "list"
    ):
        output = [
            task.authoritative_projection()
            for task
            in runtime.tasks()
        ]

    elif (
        args.command
        == "ready"
    ):
        output = [
            {
                **task.authoritative_projection(),
                "execution_intelligence": (
                    runtime.execution_intelligence(
                        task
                    )
                ),
            }
            for task
            in runtime.ready_tasks()
        ]

    elif (
        args.command
        == "graph"
    ):
        output = (
            runtime.project()
        )

    elif (
        args.command
        == "dashboard"
    ):
        output = (
            runtime.dashboard()
        )

    elif (
        args.command
        == "masterplan"
    ):
        output = (
            runtime.masterplan()
        )

    elif (
        args.command
        == "history"
    ):
        output = (
            runtime.history(
                args.task_id
            )
        )

    elif (
        args.command
        == "intelligence"
    ):
        output = (
            runtime.execution_intelligence(
                args.task_id
            )
        )

    elif (
        args.command
        == "interventions"
    ):
        output = (
            runtime.intervention_queue()
        )

    elif (
        args.command
        == "create"
    ):
        output = (
            runtime.create(
                task_id=(
                    args.task_id
                ),
                purpose=(
                    args.purpose
                ),
                owner=(
                    args.owner
                ),
                jurisdiction=(
                    args.jurisdiction
                ),
                authority_basis=(
                    args.authority
                ),
                completion_condition=(
                    args.completion
                ),
                dependencies=(
                    args.dependency
                ),
                affected_instances=(
                    args.affected_instance
                ),
                priority=(
                    args.priority
                ),
                status=(
                    args.status
                ),
                provenance={
                    "source": (
                        "niche-cli"
                    ),
                },
                extension_slots={
                    "masterplan_domain": (
                        args.domain
                    ),
                },
            )
            .authoritative_projection()
        )

    elif (
        args.command
        == "transition"
    ):
        output = (
            runtime.transition(
                args.task_id,
                args.state,
                evidence_receipts=(
                    args.receipt
                ),
                reason=(
                    args.reason
                ),
            )
            .authoritative_projection()
        )

    elif (
        args.command
        == "lease"
    ):
        output = (
            runtime.lease(
                args.task_id,
                lease_owner=(
                    args.owner
                ),
                lease_seconds=(
                    args.seconds
                ),
                reason=(
                    args.reason
                ),
            )
            .authoritative_projection()
        )

    elif (
        args.command
        == "release"
    ):
        output = (
            runtime.release(
                args.task_id,
                reason=(
                    args.reason
                ),
                new_state=(
                    args.state
                ),
            )
            .authoritative_projection()
        )

    elif (
        args.command
        == "execution"
    ):
        changes: dict[
            str,
            Any,
        ] = {}

        if (
            args.retry_limit
            is not None
        ):
            changes[
                "retry_limit"
            ] = (
                args.retry_limit
            )

        if (
            args.timeout_seconds
            is not None
        ):
            changes[
                "timeout_seconds"
            ] = (
                args.timeout_seconds
            )

        if (
            args.lease_seconds
            is not None
        ):
            changes[
                "lease_seconds"
            ] = (
                args.lease_seconds
            )

        if (
            args.not_before
            is not None
        ):
            changes[
                "not_before"
            ] = (
                args.not_before
            )

        if (
            args.deadline
            is not None
        ):
            changes[
                "deadline"
            ] = (
                args.deadline
            )

        if (
            args.approval_required
        ):
            changes[
                "manual_approval_required"
            ] = True

        if args.approve:
            changes[
                "approved"
            ] = True

        if args.resumable:
            changes[
                "resumable"
            ] = True

        if (
            args.checkpoint
            is not None
        ):
            changes[
                "checkpoint_reference"
            ] = (
                args.checkpoint
            )

        if (
            args.idempotency_key
            is not None
        ):
            changes[
                "idempotency_key"
            ] = (
                args.idempotency_key
            )

        if (
            args.concurrency_pool
            is not None
        ):
            changes[
                "concurrency_pool"
            ] = (
                args.concurrency_pool
            )

        output = (
            runtime.configure_execution(
                args.task_id,
                **changes,
            )
            .authoritative_projection()
        )

    else:
        raise NicheTaskError(
            "unsupported command: "
            + args.command
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
    raise SystemExit(
        main()
    )
