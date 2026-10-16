from __future__ import annotations

from .failure_taxonomy import (
    categories,
    failure_taxonomy_error,
    project,
)


def main() -> None:
    expected = {
        "deadline",
        "cancelled",
        "authentication",
        "authorization",
        "invalid_request",
        "capability_mismatch",
        "model_mismatch",
        "provider_unavailable",
        "provider_throttled",
        "provider_timeout",
        "provider_rejected",
        "provider_malformed_response",
        "transport_error",
        "internal_execution",
    }

    assert (
        set(
            categories()
        )
        == expected
    )

    throttled_a = project(
        "provider_throttled",
        code="provider_rate_limit",
        message="provider rate limited",
        provenance={
            "request_id": "request-1",
            "provider": "provider-a",
            "secret": "must-not-project",
        },
    )

    throttled_b = project(
        "provider_throttled",
        code="provider_rate_limit",
        message="provider rate limited",
        provenance={
            "request_id": "request-1",
            "provider": "provider-a",
            "secret": "must-not-project",
        },
    )

    assert (
        throttled_a[
            "digest"
        ]
        == throttled_b[
            "digest"
        ]
    )

    assert (
        throttled_a[
            "retryable"
        ]
        is True
    )

    assert (
        throttled_a[
            "http_status"
        ]
        == 429
    )

    assert (
        throttled_a[
            "public_type"
        ]
        == "rate_limit_error"
    )

    assert (
        "secret"
        not in throttled_a[
            "provenance"
        ]
    )

    invalid = project(
        "invalid_request"
    )

    assert (
        invalid[
            "retryable"
        ]
        is False
    )

    assert (
        invalid[
            "http_status"
        ]
        == 400
    )

    assert (
        invalid[
            "authority_effect"
        ]
        == "none"
    )

    failed = False

    try:
        project(
            "not-a-category"
        )

    except failure_taxonomy_error:
        failed = True

    assert failed

    print(
        "opus failure taxonomy: ok"
    )


if __name__ == "__main__":
    main()
