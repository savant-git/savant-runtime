from __future__ import annotations

from .enterprise_request import (
    project as project_request,
)
from .execution_governance import (
    execute,
)


class test_internal_error(
    RuntimeError
):
    pass


def _request(
    *,
    attempts: int = 3,
) -> dict:
    return project_request(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "test",
                }
            ],
            "retry_policy": {
                "max_attempts":
                    attempts,
                "retry_on_provider_error":
                    True,
                "retry_on_timeout":
                    True,
            },
        }
    )


def main() -> int:
    internal_calls = 0

    def fail_internal(
        envelope,
    ):
        nonlocal internal_calls

        internal_calls += 1

        raise test_internal_error(
            "secret provider detail "
            "must not be projected"
        )

    try:
        execute(
            _request(),
            fail_internal,
        )
    except test_internal_error as exc:
        receipt = getattr(
            exc,
            "receipt",
            None,
        )

        failure = getattr(
            exc,
            "failure",
            None,
        )

        assert isinstance(
            receipt,
            dict,
        )

        assert isinstance(
            failure,
            dict,
        )

        assert (
            failure[
                "category"
            ]
            == "internal_execution"
        )

        assert (
            "secret provider detail"
            not in str(
                receipt
            )
        )

        assert (
            receipt[
                "authority_effect"
            ]
            == "none"
        )
    else:
        raise AssertionError(
            "internal failure was not raised"
        )

    assert internal_calls == 1

    timeout_calls = 0

    def fail_timeout(
        envelope,
    ):
        nonlocal timeout_calls

        timeout_calls += 1

        raise TimeoutError(
            "provider timeout detail"
        )

    try:
        execute(
            _request(
                attempts=2
            ),
            fail_timeout,
        )
    except TimeoutError as exc:
        receipt = getattr(
            exc,
            "receipt",
            None,
        )

        failure = getattr(
            exc,
            "failure",
            None,
        )

        assert isinstance(
            receipt,
            dict,
        )

        assert isinstance(
            failure,
            dict,
        )

        assert (
            failure[
                "category"
            ]
            == "provider_timeout"
        )

        assert (
            "provider timeout detail"
            not in str(
                receipt
            )
        )
    else:
        raise AssertionError(
            "timeout failure was not raised"
        )

    assert timeout_calls >= 1

    print(
        "opus execution failure integration: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
