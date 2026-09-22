from __future__ import annotations

from typing import Any, Mapping


schema = (
    "savant://runtime/opus/"
    "idempotency-guard/1.0.0"
)

owner = "exile:opus"


class idempotency_conflict_error(
    ValueError
):
    pass


def compare(
    existing: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        existing,
        Mapping,
    ):
        raise idempotency_conflict_error(
            "existing projection "
            "must be an object"
        )

    if not isinstance(
        incoming,
        Mapping,
    ):
        raise idempotency_conflict_error(
            "incoming projection "
            "must be an object"
        )

    existing_identity = (
        existing.get(
            "identity"
        )
    )

    incoming_identity = (
        incoming.get(
            "identity"
        )
    )

    same_identity = (
        existing_identity
        == incoming_identity
    )

    same_request = (
        existing.get(
            "request_digest"
        )
        == incoming.get(
            "request_digest"
        )
    )

    conflict = (
        same_identity
        and not same_request
    )

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "projection_only": True,
        "same_identity": same_identity,
        "same_request": same_request,
        "conflict": conflict,
        "identity": (
            incoming_identity
        ),
        "existing_request_digest": (
            existing.get(
                "request_digest"
            )
        ),
        "incoming_request_digest": (
            incoming.get(
                "request_digest"
            )
        ),
        "boundaries": {
            "stores_result": False,
            "mutates_state": False,
            "executes_request": False,
            "claims_exactly_once": False,
            "creates_authority": False,
        },
    }


def require_compatible(
    existing: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> dict[str, Any]:
    projection = compare(
        existing,
        incoming,
    )

    if projection[
        "conflict"
    ]:
        raise idempotency_conflict_error(
            "idempotency identity "
            "was reused for different "
            "request substance"
        )

    return projection
