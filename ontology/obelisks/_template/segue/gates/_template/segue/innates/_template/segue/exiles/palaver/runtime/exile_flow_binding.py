from __future__ import annotations

from typing import Any, Mapping

from .provider_lifecycle import (
    authority_effect,
    execution_owner,
    lifecycle,
    owner,
    schema as lifecycle_schema,
)

from ...segue.exile_runtime.runtime.execution.exile_flow import (
    flow_contract,
    flow_envelope,
    prepare_exile,
)


schema = "savant://runtime/palaver/exile-flow-binding/1.0.0"

capability_register = "exile:palaver:provider-lifecycle-register"
capability_cancel = "exile:palaver:provider-lifecycle-cancel"
capability_complete = "exile:palaver:provider-lifecycle-complete"
capability_status = "exile:palaver:provider-lifecycle-status"


def contracts() -> tuple[flow_contract, ...]:
    return (
        flow_contract(
            capability=capability_register,
            source="exile:palaver",
            target="exile:palaver",
            accepted_schemas=(
                lifecycle_schema,
            ),
            emitted_schema=lifecycle_schema,
            idempotent=False,
            replayable=False,
        ),
        flow_contract(
            capability=capability_cancel,
            source="exile:palaver",
            target="exile:palaver",
            accepted_schemas=(
                lifecycle_schema,
            ),
            emitted_schema=lifecycle_schema,
            idempotent=False,
            replayable=False,
        ),
        flow_contract(
            capability=capability_complete,
            source="exile:palaver",
            target="exile:palaver",
            accepted_schemas=(
                lifecycle_schema,
            ),
            emitted_schema=lifecycle_schema,
            idempotent=False,
            replayable=False,
        ),
        flow_contract(
            capability=capability_status,
            source="exile:palaver",
            target="exile:palaver",
            accepted_schemas=(
                lifecycle_schema,
            ),
            emitted_schema=lifecycle_schema,
            idempotent=True,
            replayable=True,
        ),
    )


def _request_id(
    payload: Mapping[str, Any],
) -> str:
    request_id = str(
        payload.get(
            "request_id",
            "",
        )
    ).strip()

    if not request_id:
        raise ValueError(
            "request_id is required"
        )

    return request_id


def register_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    result = lifecycle.register(
        request_id=_request_id(
            payload
        ),
    )

    return {
        **result,
        "schema":
            lifecycle_schema,
    }


def cancel_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    result = lifecycle.cancel(
        request_id=_request_id(
            payload
        ),
    )

    return {
        **result,
        "schema":
            lifecycle_schema,
    }


def complete_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    result = lifecycle.complete(
        request_id=_request_id(
            payload
        ),
    )

    return {
        **result,
        "schema":
            lifecycle_schema,
    }


def status_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    del payload

    return lifecycle.status()


def handler_for(
    capability: str,
):
    handlers = {
        capability_register:
            register_handler,
        capability_cancel:
            cancel_handler,
        capability_complete:
            complete_handler,
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
            "unsupported palaver flow capability"
        ) from exc


def preparation() -> dict[str, Any]:
    return prepare_exile(
        exile=owner,
        capabilities=(
            capability_register,
            capability_cancel,
            capability_complete,
            capability_status,
        ),
        accepts=(
            lifecycle_schema,
        ),
        emits=(
            lifecycle_schema,
        ),
        extensions={
            "execution_owner":
                execution_owner,
            "authority_effect":
                authority_effect,
            "provider_lifecycle":
                lifecycle_schema,
        },
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "execution_owner":
            execution_owner,
        "authority_effect":
            authority_effect,
        "provider_lifecycle_schema":
            lifecycle_schema,
        "capabilities": [
            contract.capability
            for contract in contracts()
        ],
        "flow_owner":
            "exile:segue",
        "creates_authority":
            False,
        "changes_execution_owner":
            False,
    }


def selftest() -> dict[str, Any]:
    prepared = preparation()

    request_id = (
        "palaver-flow-binding-selftest"
    )

    registered = register_handler(
        {
            "request_id":
                request_id,
        }
    )

    completed = complete_handler(
        {
            "request_id":
                request_id,
        }
    )

    checks = {
        "owner_preserved":
            owner == "exile:palaver",
        "execution_owner_preserved":
            execution_owner
            == "exile:opus",
        "authority_effect_preserved":
            authority_effect
            == "none",
        "four_contracts":
            len(
                contracts()
            )
            == 4,
        "registered":
            bool(
                registered.get(
                    "registered"
                )
            ),
        "completed":
            bool(
                completed.get(
                    "completed"
                )
            ),
        "prepared_without_authority":
            not bool(
                prepared[
                    "boundaries"
                ][
                    "creates_authority"
                ]
            ),
        "extension_space_reserved":
            bool(
                prepared[
                    "boundaries"
                ][
                    "extension_space_reserved"
                ]
            ),
    }

    return {
        "schema":
            schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "status":
            status(),
    }


__all__ = [
    "capability_cancel",
    "capability_complete",
    "capability_register",
    "capability_status",
    "contracts",
    "handler_for",
    "preparation",
    "schema",
    "selftest",
    "status",
]


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
