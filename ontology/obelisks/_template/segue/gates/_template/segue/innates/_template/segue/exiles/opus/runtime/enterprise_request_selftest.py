from __future__ import annotations

from .enterprise_request import (
    enterprise_request_error,
    expired,
    project,
    replay_projection,
)


def main() -> None:
    request = {
        "request_id": "test-request-1",
        "idempotency_key": (
            "test-idempotency-1"
        ),
        "owner": "opus_api",
        "request_origin": (
            "external_client"
        ),
        "client_key_id": "key-1",
        "client_owner": "client-1",
        "tenant_id": "tenant-1",
        "trace_id": "trace-1",
        "priority": "high",
        "privacy": "confidential",
        "cache_mode": "read_write",
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": "hello",
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "test",
                    "parameters": {
                        "type": "object",
                    },
                },
            }
        ],
        "required_capabilities": [
            "tools",
            "text",
            "text",
        ],
        "required_layers": [
            "reasoning",
        ],
        "requested_model": "opus:auto",
        "timeout_seconds": 30,
        "retry_policy": {
            "max_attempts": 3,
            "retry_on_provider_error": True,
            "retry_on_timeout": True,
        },
        "budget": {
            "max_input_tokens": 1000,
            "max_output_tokens": 500,
            "max_cost": 1.25,
        },
        "metadata": {
            "purpose": "selftest",
        },
    }

    first = project(
        request,
        now_monotonic=100.0,
    )

    second = project(
        request,
        now_monotonic=200.0,
    )

    assert first[
        "canonical_digest"
    ] == second[
        "canonical_digest"
    ]

    assert first[
        "deadline_monotonic"
    ] == 130.0

    assert second[
        "deadline_monotonic"
    ] == 230.0

    assert first[
        "required_capabilities"
    ] == [
        "text",
        "tools",
    ]

    assert first[
        "priority"
    ] == "high"

    assert first[
        "privacy"
    ] == "confidential"

    assert first[
        "retry_policy"
    ][
        "max_attempts"
    ] == 3

    assert first[
        "budget"
    ][
        "max_output_tokens"
    ] == 500

    assert first[
        "boundaries"
    ][
        "selects_provider"
    ] is False

    assert expired(
        first,
        now_monotonic=129.0,
    ) is False

    assert expired(
        first,
        now_monotonic=130.0,
    ) is True

    replay = replay_projection(
        first
    )

    assert replay[
        "canonical_digest"
    ] == first[
        "canonical_digest"
    ]

    assert replay[
        "rebuildable"
    ] is True

    failed = False

    try:
        project(
            {
                "messages": [],
            }
        )

    except enterprise_request_error:
        failed = True

    assert failed

    failed = False

    try:
        project(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "hello",
                    }
                ],
                "timeout_seconds": 1000,
            }
        )

    except enterprise_request_error:
        failed = True

    assert failed

    print(
        "opus enterprise request: ok"
    )


if __name__ == "__main__":
    main()
