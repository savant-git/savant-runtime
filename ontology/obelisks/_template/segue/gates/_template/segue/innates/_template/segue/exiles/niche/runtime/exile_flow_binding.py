from __future__ import annotations

from typing import Any, Mapping

from .dryve_lifecycle import (
    MECHANICS_OWNER,
    OWNER,
    SCHEMA as lifecycle_schema,
    lifecycle,
)

from ...segue.exile_runtime.runtime.execution.exile_flow import (
    flow_contract,
    prepare_exile,
)


schema = "savant://runtime/niche/exile-flow-binding/1.0.0"

owner = OWNER
mechanics_owner = MECHANICS_OWNER
authority_effect = "none"

capability_prepare = "exile:niche:task-execution-prepare"
capability_receipt = "exile:niche:task-execution-receipt"
capability_status = "exile:niche:dryve-lifecycle-status"


def contracts() -> tuple[flow_contract, ...]:
    return (
        flow_contract(
            capability=capability_prepare,
            source=owner,
            target=owner,
            accepted_schemas=(
                lifecycle_schema,
            ),
            emitted_schema=(
                "savant://runtime/niche/"
                "task-execution/1.0.0"
            ),
            idempotent=True,
            replayable=True,
        ),
        flow_contract(
            capability=capability_receipt,
            source=owner,
            target=owner,
            accepted_schemas=(
                "savant://runtime/niche/"
                "task-execution/1.0.0",
            ),
            emitted_schema=(
                "savant://runtime/dryve/"
                "execution-lifecycle-receipt/1.0.0"
            ),
            idempotent=True,
            replayable=True,
        ),
        flow_contract(
            capability=capability_status,
            source=owner,
            target=owner,
            accepted_schemas=(
                lifecycle_schema,
            ),
            emitted_schema=lifecycle_schema,
            idempotent=True,
            replayable=True,
        ),
    )


def prepare_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    runtime = lifecycle()

    task_id = str(
        payload.get(
            "task_id",
            "",
        )
    ).strip()

    operation = str(
        payload.get(
            "operation",
            "",
        )
    ).strip()

    if not task_id:
        raise ValueError(
            "task_id is required"
        )

    if not operation:
        raise ValueError(
            "operation is required"
        )

    task = runtime.prepare(
        task_id=task_id,
        operation=operation,
        payload=payload.get(
            "payload"
        ),
        task_state=payload.get(
            "task_state"
        ),
        priority=payload.get(
            "priority"
        ),
        dependencies=payload.get(
            "dependencies",
            (),
        ),
        lineage=payload.get(
            "lineage"
        ),
        provenance=payload.get(
            "provenance"
        ),
        metadata=payload.get(
            "metadata"
        ),
    )

    return task.projection()


def receipt_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    runtime = lifecycle()

    prepared = payload.get(
        "prepared"
    )

    if not isinstance(
        prepared,
        Mapping,
    ):
        raise ValueError(
            "prepared is required"
        )

    task_id = str(
        prepared.get(
            "task_id",
            "",
        )
    ).strip()

    execution = prepared.get(
        "execution"
    )

    if not isinstance(
        execution,
        Mapping,
    ):
        raise ValueError(
            "prepared.execution is required"
        )

    operation = str(
        execution.get(
            "operation",
            "",
        )
    ).strip()

    if not task_id:
        raise ValueError(
            "prepared.task_id is required"
        )

    if not operation:
        raise ValueError(
            "prepared execution operation is required"
        )

    task = runtime.prepare(
        task_id=task_id,
        operation=operation,
        payload=execution.get(
            "payload"
        ),
        task_state=prepared.get(
            "task_state"
        ),
        priority=prepared.get(
            "priority"
        ),
        dependencies=prepared.get(
            "dependencies",
            (),
        ),
        lineage=execution.get(
            "lineage"
        ),
        provenance=execution.get(
            "provenance"
        ),
        metadata=execution.get(
            "metadata"
        ),
    )

    receipt = runtime.lifecycle_receipt(
        task,
        execution_state=str(
            payload.get(
                "execution_state",
                "",
            )
        ).strip(),
        attempt=int(
            payload.get(
                "attempt",
                1,
            )
        ),
        previous_execution_state=(
            payload.get(
                "previous_execution_state"
            )
        ),
        result=payload.get(
            "result"
        ),
        error=payload.get(
            "error"
        ),
    )

    return receipt.projection()


def status_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    del payload

    return lifecycle().status()


def handler_for(
    capability: str,
):
    handlers = {
        capability_prepare:
            prepare_handler,
        capability_receipt:
            receipt_handler,
        capability_status:
            status_handler,
    }

    try:
        return handlers[
            str(
                capability
            ).strip().lower()
        ]
    except KeyError as exc:
        raise ValueError(
            "unsupported niche flow capability"
        ) from exc


def preparation() -> dict[str, Any]:
    return prepare_exile(
        exile=owner,
        capabilities=(
            capability_prepare,
            capability_receipt,
            capability_status,
        ),
        accepts=(
            lifecycle_schema,
        ),
        emits=(
            "savant://runtime/niche/"
            "task-execution/1.0.0",
            "savant://runtime/dryve/"
            "execution-lifecycle-receipt/1.0.0",
            lifecycle_schema,
        ),
        extensions={
            "mechanics_owner":
                mechanics_owner,
            "task_governance_owner":
                owner,
            "task_transition_owner":
                owner,
            "authority_effect":
                authority_effect,
            "lifecycle":
                lifecycle_schema,
        },
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "mechanics_owner":
            mechanics_owner,
        "authority_effect":
            authority_effect,
        "lifecycle_schema":
            lifecycle_schema,
        "capabilities": [
            contract.capability
            for contract in contracts()
        ],
        "flow_owner":
            "exile:segue",
        "task_governance_owner":
            owner,
        "task_transition_owner":
            owner,
        "changes_task_governance":
            False,
        "changes_task_transition_owner":
            False,
        "creates_authority":
            False,
    }


__all__ = [
    "capability_prepare",
    "capability_receipt",
    "capability_status",
    "contracts",
    "handler_for",
    "preparation",
    "schema",
    "status",
]
