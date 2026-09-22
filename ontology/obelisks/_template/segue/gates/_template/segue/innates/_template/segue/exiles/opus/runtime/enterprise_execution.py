from __future__ import annotations

from typing import Any, Mapping

from .enterprise_request import (
    project as project_request,
)
from .execution_governance import (
    execute as governed_execute,
)
from .router import (
    execute_text_request,
)


schema = (
    "savant://runtime/opus/"
    "enterprise-execution/1.0.0"
)

owner = "exile:opus"


class enterprise_execution_error(
    RuntimeError
):
    pass


def _canonical_request(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    request = {
        "owner": (
            envelope.get(
                "provenance",
                {},
            ).get(
                "request_owner"
            )
            or "opus"
        ),
        "request_origin": (
            envelope.get(
                "provenance",
                {},
            ).get(
                "request_origin"
            )
            or "internal"
        ),
        "messages": list(
            envelope.get(
                "messages"
            )
            or []
        ),
        "requested_model": (
            envelope.get(
                "requested_model"
            )
        ),
        "required_capabilities": list(
            envelope.get(
                "required_capabilities"
            )
            or []
        ),
        "required_layers": list(
            envelope.get(
                "required_layers"
            )
            or []
        ),
        "tools": list(
            envelope.get(
                "tools"
            )
            or []
        ),
        "tool_choice": envelope.get(
            "tool_choice"
        ),
        "request_id": envelope.get(
            "request_id"
        ),
        "trace_id": envelope.get(
            "trace_id"
        ),
        "tenant_id": envelope.get(
            "tenant_id"
        ),
        "idempotency_key": (
            envelope.get(
                "idempotency_key"
            )
        ),
        "priority": envelope.get(
            "priority"
        ),
        "privacy": envelope.get(
            "privacy"
        ),
        "budget": dict(
            envelope.get(
                "budget"
            )
            or {}
        ),
        "metadata": dict(
            envelope.get(
                "metadata"
            )
            or {}
        ),
    }

    provenance = envelope.get(
        "provenance"
    )

    if isinstance(
        provenance,
        Mapping,
    ):
        client_key_id = (
            provenance.get(
                "client_key_id"
            )
        )

        client_owner = (
            provenance.get(
                "client_owner"
            )
        )

        if client_key_id:
            request[
                "client_key_id"
            ] = client_key_id

        if client_owner:
            request[
                "client_owner"
            ] = client_owner

    return request


def execute_envelope(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    def executor(
        governed_envelope,
    ):
        return execute_text_request(
            _canonical_request(
                governed_envelope
            )
        )

    result, receipt = (
        governed_execute(
            envelope,
            executor,
        )
    )

    return {
        "schema": schema,
        "owner": owner,
        "result": result,
        "execution_receipt": receipt,
        "authority_effect": "none",
        "lineage": {
            "request_digest": (
                envelope.get(
                    "canonical_digest"
                )
            ),
            "execution_id": (
                receipt.get(
                    "execution_id"
                )
            ),
            "canonical_executor": (
                "opus.runtime.router."
                "execute_text_request"
            ),
        },
    }


def execute(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    envelope = project_request(
        request
    )

    return execute_envelope(
        envelope
    )
