from __future__ import annotations

from .idempotency import (
    equivalent,
    project,
)


def main() -> None:
    request = {
        "tenant_id": "tenant-a",
        "client_key_id": "key-a",
        "request_origin": (
            "external_client"
        ),
        "requested_model": "opus:auto",
        "messages": [
            {
                "role": "user",
                "content": "hello",
            }
        ],
        "required_capabilities": [
            "text",
        ],
        "max_tokens": 128,
    }

    first = project(
        request
    )

    second = project(
        dict(request)
    )

    assert first[
        "identity"
    ] == second[
        "identity"
    ]

    assert first[
        "request_digest"
    ] == second[
        "request_digest"
    ]

    assert first[
        "mode"
    ] == "derived"

    assert first[
        "authority_effect"
    ] == "none"

    assert first[
        "boundaries"
    ][
        "claims_exactly_once"
    ] is False

    assert equivalent(
        request,
        dict(request),
    )

    changed = {
        **request,
        "max_tokens": 256,
    }

    assert not equivalent(
        request,
        changed,
    )

    explicit_a = {
        **request,
        "idempotency_key": (
            "operation-123"
        ),
    }

    explicit_b = {
        **changed,
        "idempotency_key": (
            "operation-123"
        ),
    }

    assert project(
        explicit_a
    )[
        "identity"
    ] == project(
        explicit_b
    )[
        "identity"
    ]

    assert project(
        explicit_a
    )[
        "request_digest"
    ] != project(
        explicit_b
    )[
        "request_digest"
    ]

    print(
        "opus idempotency projection: ok"
    )


if __name__ == "__main__":
    main()
