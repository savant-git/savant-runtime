from __future__ import annotations

from .failure_projection import (
    failure_projection_error,
    project,
    public_error,
)


def main() -> None:
    provenance = {
        "request_id": "request-1",
        "trace_id": "trace-1",
        "provider": "provider-a",
        "model": "model-a",
        "attempt": 2,
        "authorization": (
            "must-not-project"
        ),
        "api_key": (
            "must-not-project"
        ),
    }

    first = project(
        "provider_throttled",
        code="rate_limit",
        message="provider throttled",
        retry_after_seconds=2.5,
        provenance=provenance,
    )

    second = project(
        "provider_throttled",
        code="rate_limit",
        message="provider throttled",
        retry_after_seconds=2.5,
        provenance=provenance,
    )

    assert (
        first[
            "digest"
        ]
        == second[
            "digest"
        ]
    )

    assert (
        first[
            "authority_effect"
        ]
        == "none"
    )

    assert (
        first[
            "retryable"
        ]
        is True
    )

    assert (
        first[
            "terminal"
        ]
        is False
    )

    assert (
        first[
            "http_status"
        ]
        == 429
    )

    assert (
        first[
            "retry_after_seconds"
        ]
        == 2.5
    )

    assert (
        "authorization"
        not in first[
            "provenance"
        ]
    )

    assert (
        "api_key"
        not in first[
            "provenance"
        ]
    )

    assert (
        first[
            "boundaries"
        ][
            "executes_provider"
        ]
        is False
    )

    body = public_error(
        first
    )

    assert (
        body[
            "error"
        ][
            "type"
        ]
        == "rate_limit_error"
    )

    assert (
        body[
            "error"
        ][
            "code"
        ]
        == "rate_limit"
    )

    terminal = project(
        "invalid_request"
    )

    assert (
        terminal[
            "terminal"
        ]
        is True
    )

    failed = False

    try:
        project(
            "provider_timeout",
            retry_after_seconds=-1,
        )

    except failure_projection_error:
        failed = True

    assert failed

    print(
        "opus failure projection: ok"
    )


if __name__ == "__main__":
    main()
