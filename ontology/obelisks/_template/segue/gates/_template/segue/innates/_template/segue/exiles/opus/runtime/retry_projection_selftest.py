from __future__ import annotations

from .retry_projection import (
    project,
    retry_projection_error,
)


def main() -> int:
    failure = {
        "category":
            "provider_timeout",
        "code":
            "provider_timeout",
        "retryable": True,
        "retry_after_seconds":
            1.0,
        "projection_digest":
            "failure-test-digest",
    }

    first = project(
        failure,
        attempt=1,
        max_attempts=3,
    )

    assert (
        first[
            "eligible"
        ]
        is True
    )

    assert (
        first[
            "attempts_remaining"
        ]
        == 2
    )

    assert (
        first[
            "delay_seconds"
        ]
        == 1.0
    )

    second = project(
        failure,
        attempt=2,
        max_attempts=3,
    )

    assert (
        second[
            "eligible"
        ]
        is True
    )

    terminal = project(
        failure,
        attempt=3,
        max_attempts=3,
    )

    assert (
        terminal[
            "eligible"
        ]
        is False
    )

    assert (
        terminal[
            "delay_seconds"
        ]
        == 0.0
    )

    nonretryable = project(
        {
            "category":
                "invalid_request",
            "code":
                "invalid_request",
            "retryable": False,
        },
        attempt=1,
        max_attempts=3,
    )

    assert (
        nonretryable[
            "eligible"
        ]
        is False
    )

    assert (
        nonretryable[
            "delay_seconds"
        ]
        == 0.0
    )

    repeat = project(
        failure,
        attempt=1,
        max_attempts=3,
    )

    assert (
        repeat[
            "projection_digest"
        ]
        == first[
            "projection_digest"
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
            "projection_only"
        ]
        is True
    )

    assert (
        first[
            "boundaries"
        ][
            "executes_retry"
        ]
        is False
    )

    assert (
        first[
            "boundaries"
        ][
            "sleeps"
        ]
        is False
    )

    invalid = False

    try:
        project(
            failure,
            attempt=0,
            max_attempts=3,
        )
    except retry_projection_error:
        invalid = True

    assert invalid

    print(
        "opus retry projection: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
