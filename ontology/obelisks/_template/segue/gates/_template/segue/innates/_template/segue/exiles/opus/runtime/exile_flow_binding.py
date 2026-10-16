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


schema = "savant://runtime/opus/exile-flow-binding/1.0.0"

owner = OWNER
mechanics_owner = MECHANICS_OWNER
authority_effect = "none"

capability_prepare = "exile:opus:provider-execution-prepare"
capability_receipt = "exile:opus:provider-execution-receipt"
capability_status = "exile:opus:dryve-lifecycle-status"


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
                "savant://runtime/opus/"
                "provider-execution/1.0.0"
            ),
            idempotent=True,
            replayable=True,
        ),
        flow_contract(
            capability=capability_receipt,
            source=owner,
            target=owner,
            accepted_schemas=(
                "savant://runtime/opus/"
                "provider-execution/1.0.0",
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

    execution_id = str(
        payload.get(
            "execution_id",
            "",
        )
    ).strip()

    operation = str(
        payload.get(
            "operation",
            "",
        )
    ).strip()

    if not execution_id:
        raise ValueError(
            "execution_id is required"
        )

    if not operation:
        raise ValueError(
            "operation is required"
        )

    execution = runtime.prepare(
        execution_id=execution_id,
        operation=operation,
        payload=payload.get(
            "payload"
        ),
        provider_route=payload.get(
            "provider_route"
        ),
        model_route=payload.get(
            "model_route"
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
        retry_policy=payload.get(
            "retry_policy"
        ),
        timeout_policy=payload.get(
            "timeout_policy"
        ),
        metadata=payload.get(
            "metadata"
        ),
    )

    return execution.projection()


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

    execution_id = str(
        prepared.get(
            "execution_id",
            "",
        )
    ).strip()

    execution_projection = prepared.get(
        "execution"
    )

    if not isinstance(
        execution_projection,
        Mapping,
    ):
        raise ValueError(
            "prepared.execution is required"
        )

    operation = str(
        execution_projection.get(
            "operation",
            "",
        )
    ).strip()

    if not execution_id:
        raise ValueError(
            "prepared.execution_id is required"
        )

    if not operation:
        raise ValueError(
            "prepared execution operation is required"
        )

    execution = runtime.prepare(
        execution_id=execution_id,
        operation=operation,
        payload=execution_projection.get(
            "payload"
        ),
        provider_route=prepared.get(
            "provider_route"
        ),
        model_route=prepared.get(
            "model_route"
        ),
        dependencies=prepared.get(
            "dependencies",
            (),
        ),
        lineage=execution_projection.get(
            "lineage"
        ),
        provenance=execution_projection.get(
            "provenance"
        ),
        retry_policy=execution_projection.get(
            "retry_policy"
        ),
        timeout_policy=execution_projection.get(
            "timeout_policy"
        ),
        metadata=execution_projection.get(
            "metadata"
        ),
    )

    receipt = runtime.lifecycle_receipt(
        execution,
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
            "unsupported opus flow capability"
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
            "savant://runtime/opus/"
            "provider-execution/1.0.0",
            "savant://runtime/dryve/"
            "execution-lifecycle-receipt/1.0.0",
            lifecycle_schema,
        ),
        extensions={
            "mechanics_owner":
                mechanics_owner,
            "provider_execution_owner":
                owner,
            "provider_routing_owner":
                owner,
            "model_selection_owner":
                owner,
            "provider_credentials_owner":
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
        "provider_execution_owner":
            owner,
        "provider_routing_owner":
            owner,
        "model_selection_owner":
            owner,
        "provider_credentials_owner":
            owner,
        "changes_provider_ownership":
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
