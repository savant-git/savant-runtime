from __future__ import annotations

from typing import Any, Mapping

from .api_key_registry import authenticate
from .router import execute_text_request


SCHEMA = (
    "savant://runtime/opus/"
    "api/request/1.0.0"
)

OWNER = "exile:opus"

TEXT_ROUTE = "text_inference_route"
TEXT_SCOPE = "text:infer"


class ApiAuthenticationError(
    PermissionError
):
    pass


class ApiRequestError(
    ValueError
):
    pass


def _string(
    value: Any,
) -> str:
    return str(
        value
        if value is not None
        else ""
    ).strip()


def _strings(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        values = [
            value
        ]

    elif isinstance(
        value,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        values = list(
            value
        )

    else:
        raise ApiRequestError(
            "expected string collection"
        )

    return sorted(
        {
            _string(item)
            for item in values
            if _string(
                item
            )
        }
    )


def _messages(
    value: Any,
) -> list[dict[str, str]]:
    if not isinstance(
        value,
        list,
    ):
        raise ApiRequestError(
            "messages must be a list"
        )

    normalized = []

    for message in value:
        if not isinstance(
            message,
            Mapping,
        ):
            raise ApiRequestError(
                "message must be an object"
            )

        role = _string(
            message.get(
                "role"
            )
        )

        content = _string(
            message.get(
                "content"
            )
        )

        if not role:
            raise ApiRequestError(
                "message role is required"
            )

        if not content:
            raise ApiRequestError(
                "message content is required"
            )

        normalized.append(
            {
                "role": role,
                "content": content,
            }
        )

    if not normalized:
        raise ApiRequestError(
            "at least one message "
            "is required"
        )

    return normalized


def normalize_text_request(
    payload: Mapping[str, Any],
    *,
    client: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise ApiRequestError(
            "request payload must "
            "be an object"
        )

    messages = _messages(
        payload.get(
            "messages"
        )
    )

    required_capabilities = (
        _strings(
            payload.get(
                "required_capabilities"
            )
        )
    )

    required_layers = _strings(
        payload.get(
            "required_layers"
        )
    )

    request = {
        "owner": "opus_api",
        "request_origin": (
            "external_client"
        ),
        "client_key_id": client.get(
            "key_id"
        ),
        "client_owner": client.get(
            "client_owner"
        ),
        "messages": messages,
        "required_capabilities": (
            required_capabilities
        ),
        "required_layers": (
            required_layers
        ),
    }

    model = _string(
        payload.get(
            "model"
        )
    )

    if model:
        request[
            "requested_model"
        ] = model

    for field in (
        "temperature",
        "max_tokens",
        "top_p",
        "stop",
        "tools",
        "tool_choice",
        "response_format",
    ):
        if field in payload:
            request[
                field
            ] = payload[
                field
            ]

    return request


def execute_authenticated_text(
    *,
    secret: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    client = authenticate(
        secret,
        required_scope=TEXT_SCOPE,
        required_route=TEXT_ROUTE,
    )

    if not client:
        raise ApiAuthenticationError(
            "invalid or unauthorized "
            "opus api key"
        )

    request = normalize_text_request(
        payload,
        client=client,
    )

    result = execute_text_request(
        request
    )

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "opus text execution "
            "returned non-object result"
        )

    response = dict(
        result
    )

    api_lineage = {
        "schema": SCHEMA,
        "owner": OWNER,
        "client_key_id": client.get(
            "key_id"
        ),
        "client_owner": client.get(
            "client_owner"
        ),
        "route": TEXT_ROUTE,
        "canonical_execution": (
            "opus.runtime.router."
            "execute_text_request"
        ),
        "authority_effect": "none",
    }

    existing_lineage = response.get(
        "lineage"
    )

    if isinstance(
        existing_lineage,
        dict,
    ):
        response[
            "lineage"
        ] = {
            **existing_lineage,
            "api": api_lineage,
        }

    else:
        response[
            "lineage"
        ] = {
            "api": api_lineage,
        }

    return response
