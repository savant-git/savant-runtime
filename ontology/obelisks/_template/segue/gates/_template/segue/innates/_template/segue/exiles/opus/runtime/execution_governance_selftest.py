from __future__ import annotations

from .enterprise_request import project
from .execution_governance import (
    execute,
    execution_deadline_error,
    execution_identity,
)


class clock:
    def __init__(
        self,
        value: float,
    ) -> None:
        self.value = value

    def __call__(
        self,
    ) -> float:
        current = self.value

        self.value += 1.0

        return current


def main() -> None:
    envelope = project(
        {
            "request_id": (
                "governance-test"
            ),
            "idempotency_key": (
                "governance-idempotency"
            ),
            "tenant_id": "tenant-a",
            "trace_id": "trace-a",
            "messages": [
                {
                    "role": "user",
                    "content": "hello",
                }
            ],
            "timeout_seconds": 30,
            "retry_policy": {
                "max_attempts": 3,
                "retry_on_provider_error": (
                    True
                ),
                "retry_on_timeout": True,
            },
        },
        now_monotonic=100.0,
    )

    identity_a = (
        execution_identity(
            envelope
        )
    )

    identity_b = (
        execution_identity(
            envelope
        )
    )

    assert identity_a == identity_b

    calls = {
        "count": 0,
    }

    def executor(
        request,
    ):
        calls[
            "count"
        ] += 1

        if calls[
            "count"
        ] == 1:
            raise RuntimeError(
                "transient"
            )

        return {
            "content": "ok",
            "request_id": request[
                "request_id"
            ],
        }

    result, receipt = execute(
        envelope,
        executor,
        now_monotonic=clock(
            101.0
        ),
    )

    assert result[
        "content"
    ] == "ok"

    assert receipt[
        "status"
    ] == "succeeded"

    assert receipt[
        "attempt_count"
    ] == 2

    assert receipt[
        "attempts"
    ][
        0
    ][
        "status"
    ] == "provider_error"

    assert receipt[
        "attempts"
    ][
        1
    ][
        "status"
    ] == "succeeded"

    assert receipt[
        "boundaries"
    ][
        "selects_provider"
    ] is False

    expired_envelope = project(
        {
            "request_id": (
                "expired-test"
            ),
            "messages": [
                {
                    "role": "user",
                    "content": "hello",
                }
            ],
            "timeout_seconds": 1,
        },
        now_monotonic=10.0,
    )

    failed = False

    try:
        execute(
            expired_envelope,
            lambda request: {
                "content": "never"
            },
            now_monotonic=clock(
                12.0
            ),
        )

    except execution_deadline_error as exc:
        failed = True

        assert exc.receipt[
            "status"
        ] == "failed"

        assert exc.receipt[
            "attempts"
        ][
            0
        ][
            "status"
        ] == (
            "deadline_expired"
        )

    assert failed

    print(
        "opus execution governance: ok"
    )


if __name__ == "__main__":
    main()
