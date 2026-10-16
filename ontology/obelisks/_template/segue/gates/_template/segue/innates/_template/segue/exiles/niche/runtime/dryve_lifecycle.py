#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from runtime.dryve.owner_binding import (
    DryveOwnerBinding,
    ExecutionLifecycleReceipt,
    ExecutionLifecycleRequest,
    bind_owners,
)


OWNER = "exile:niche"
MECHANICS_OWNER = "living:dryve"

SCHEMA = "savant://runtime/niche/dryve-lifecycle/1.0.0"


class NicheDryveLifecycleError(RuntimeError):
    pass


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


def normalize_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    return text or None


def normalize_sequence(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        item = normalize_identifier(
            value
        )

        return (
            (item,)
            if item
            else ()
        )

    if isinstance(
        value,
        Mapping,
    ):
        values = value.keys()
    else:
        try:
            values = iter(
                value
            )
        except TypeError:
            values = (
                value,
            )

    result = {
        normalized
        for normalized in (
            normalize_identifier(
                item
            )
            for item in values
        )
        if normalized
    }

    return tuple(
        sorted(
            result
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class NicheTaskExecution:
    task_id: str
    execution: ExecutionLifecycleRequest
    task_state: str | None
    priority: Any
    dependencies: tuple[str, ...]
    governance_owner: str = OWNER

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/niche/"
                "task-execution/1.0.0"
            ),
            "owner": OWNER,
            "mechanics_owner": (
                MECHANICS_OWNER
            ),
            "task_id": self.task_id,
            "task_state": (
                self.task_state
            ),
            "priority": self.priority,
            "dependencies": list(
                self.dependencies
            ),
            "execution": (
                self.execution
                .projection()
            ),
            "task_governance_owner": (
                self.governance_owner
            ),
            "task_transition_authorized_by_dryve": (
                False
            ),
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


class NicheDryveLifecycle:
    """
    Niche-owned task execution lifecycle adapter.

    Niche decides task identity, dependency governance, priority,
    scheduling, and task-state transitions.

    Dryve supplies reusable execution-lifecycle mechanics only.
    """

    def __init__(
        self,
        *,
        dryve: DryveOwnerBinding | None = None,
    ) -> None:
        self.dryve = (
            dryve
            if dryve is not None
            else bind_owners()
        )

    def prepare(
        self,
        *,
        task_id: str,
        operation: str,
        payload: Any,
        task_state: str | None = None,
        priority: Any = None,
        dependencies: Sequence[str] = (),
        lineage: Any = None,
        provenance: Any = None,
        metadata: Any = None,
    ) -> NicheTaskExecution:
        normalized_task_id = (
            normalize_identifier(
                task_id
            )
        )

        if not normalized_task_id:
            raise NicheDryveLifecycleError(
                "task_id is required"
            )

        normalized_dependencies = (
            normalize_sequence(
                dependencies
            )
        )

        request = (
            self.dryve
            .niche_request(
                execution_id=(
                    "execution:niche:"
                    f"{normalized_task_id}"
                ),
                operation=operation,
                payload=payload,
                dependencies=(
                    normalized_dependencies
                ),
                lineage=lineage,
                provenance=provenance,
                metadata={
                    "task_id": (
                        normalized_task_id
                    ),
                    "task_state": (
                        task_state
                    ),
                    "priority": priority,
                    "niche_metadata": (
                        metadata
                    ),
                },
            )
        )

        return NicheTaskExecution(
            task_id=normalized_task_id,
            execution=request,
            task_state=(
                normalize_identifier(
                    task_state
                )
            ),
            priority=priority,
            dependencies=(
                normalized_dependencies
            ),
        )

    def lifecycle_receipt(
        self,
        task: NicheTaskExecution,
        *,
        execution_state: str,
        attempt: int = 1,
        previous_execution_state: str | None = None,
        result: Any = None,
        error: Any = None,
    ) -> ExecutionLifecycleReceipt:
        return self.dryve.receipt(
            task.execution,
            state=execution_state,
            attempt=attempt,
            previous_state=(
                previous_execution_state
            ),
            result=result,
            error=error,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        dryve_status = (
            self.dryve.status()
        )

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "mechanics_owner": (
                MECHANICS_OWNER
            ),
            "task_discovery_owner": OWNER,
            "job_decomposition_owner": OWNER,
            "work_planning_owner": OWNER,
            "task_governance_owner": OWNER,
            "task_transition_owner": OWNER,
            "execution_lifecycle_mechanics": (
                MECHANICS_OWNER
            ),
            "dryve_binding": (
                dryve_status
            ),
            "dryve_may_govern_tasks": False,
            "dryve_may_schedule_tasks": False,
            "dryve_may_set_priority": False,
            "dryve_may_transition_tasks": False,
            "dryve_may_rewrite_dependencies": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def lifecycle(
) -> NicheDryveLifecycle:
    return NicheDryveLifecycle()


def main() -> int:
    runtime = lifecycle()

    task = runtime.prepare(
        task_id="task:test:dryve",
        operation="execute-task-work",
        payload={
            "work": "focused-check",
        },
        task_state="ready",
        priority="normal",
        dependencies=(
            "task:test:dependency",
        ),
        provenance={
            "source": (
                "focused-integration-check"
            ),
        },
    )

    receipt = (
        runtime.lifecycle_receipt(
            task,
            execution_state="ready",
        )
    )

    output = {
        "status": runtime.status(),
        "task": task.projection(),
        "receipt": (
            receipt.projection()
        ),
    }

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            output["status"][
                "task_governance_owner"
            ]
            == OWNER
            and output["status"][
                "execution_lifecycle_mechanics"
            ]
            == MECHANICS_OWNER
            and output["status"][
                "dryve_may_transition_tasks"
            ]
            is False
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
