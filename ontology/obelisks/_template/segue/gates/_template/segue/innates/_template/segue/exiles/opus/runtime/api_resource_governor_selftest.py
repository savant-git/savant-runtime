from __future__ import annotations

from .api_resource_governor import (
    api_resource_error,
    evaluate,
    resource_policy,
)


def main() -> None:
    payload = {
        "model": "opus:auto",
        "messages": [
            {
                "role": "user",
                "content": "hello",
            }
        ],
        "metadata": {
            "purpose": "selftest",
        },
        "max_tokens": 128,
    }

    first = evaluate(
        payload
    )

    second = evaluate(
        payload
    )

    assert first[
        "digest"
    ] == second[
        "digest"
    ]

    assert first[
        "accepted"
    ] is True

    assert first[
        "authority_effect"
    ] == "none"

    assert first[
        "metrics"
    ][
        "body_bytes"
    ] > 0

    assert first[
        "boundaries"
    ][
        "selects_provider"
    ] is False

    failed = False

    try:
        evaluate(
            payload,
            body_bytes=100,
            policy=resource_policy(
                max_body_bytes=10,
            ),
        )

    except api_resource_error:
        failed = True

    assert failed

    failed = False

    try:
        evaluate(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "hello",
                    }
                ],
                "max_tokens": 100,
            },
            policy=resource_policy(
                max_output_tokens=10,
            ),
        )

    except api_resource_error:
        failed = True

    assert failed

    print(
        "opus api resource governor: ok"
    )


if __name__ == "__main__":
    main()
