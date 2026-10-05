from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Mapping

from .enterprise_request import expired


schema = (
    "savant://runtime/opus/"
    "execution-governance/1.0.0"
)

owner = "exile:opus"


class execution_governance_error(
    RuntimeError
):
    pass


class execution_deadline_error(
    TimeoutError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _retry_policy(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    value = envelope.get(
        "retry_policy"
    )

    if not isinstance(
        value,
        Mapping,
    ):
        return {
            "max_attempts": 1,
            "retry_on_provider_error": False,
            "retry_on_timeout": False,
        }

    attempts = value.get(
        "max_attempts",
        1,
    )

    try:
        attempts = int(
            attempts
        )

    except (
        TypeError,
        ValueError,
    ):
        attempts = 1

    attempts = max(
        1,
        min(
            attempts,
            8,
        ),
    )

    return {
        "max_attempts": attempts,
        "retry_on_provider_error": bool(
            value.get(
                "retry_on_provider_error",
                False,
            )
        ),
        "retry_on_timeout": bool(
            value.get(
                "retry_on_timeout",
                False,
            )
        ),
    }


def execution_identity(
    envelope: Mapping[str, Any],
) -> str:
    material = {
        "request_id": envelope.get(
            "request_id"
        ),
        "canonical_digest": (
            envelope.get(
                "canonical_digest"
            )
        ),
        "tenant_id": envelope.get(
            "tenant_id"
        ),
        "idempotency_key": (
            envelope.get(
                "idempotency_key"
            )
        ),
    }

    return (
        "opusexec_"
        + _digest(
            material
        )[
            :32
        ]
    )


def _receipt(
    *,
    envelope: Mapping[str, Any],
    execution_id: str,
    status: str,
    attempts: list[dict[str, Any]],
    result: Any = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    receipt = {
        "schema": schema,
        "owner": owner,
        "type": (
            "opus_execution_receipt"
        ),
        "execution_id": execution_id,
        "request_id": envelope.get(
            "request_id"
        ),
        "request_digest": envelope.get(
            "canonical_digest"
        ),
        "tenant_id": envelope.get(
            "tenant_id"
        ),
        "trace_id": envelope.get(
            "trace_id"
        ),
        "status": status,
        "attempt_count": len(
            attempts
        ),
        "attempts": attempts,
        "authority_effect": "none",
        "boundaries": {
            "selects_provider": False,
            "selects_model": False,
            "owns_credentials": False,
            "mutates_registry": False,
            "creates_authority": False,
            "canonical_execution": (
                "opus.runtime.router"
            ),
        },
    }

    if result is not None:
        receipt[
            "result_digest"
        ] = _digest(
            result
        )

    if error is not None:
        receipt[
            "error"
        ] = {
            "type": type(
                error
            ).__name__,
            "message": str(
                error
            ),
        }

    receipt[
        "receipt_digest"
    ] = _digest(
        receipt
    )

    return receipt


def execute(
    envelope: Mapping[str, Any],
    executor: Callable[
        [Mapping[str, Any]],
        Any,
    ],
    *,
    now_monotonic: Callable[
        [],
        float,
    ] = time.monotonic,
) -> tuple[
    Any,
    dict[str, Any],
]:
    if not isinstance(
        envelope,
        Mapping,
    ):
        raise execution_governance_error(
            "enterprise envelope "
            "must be an object"
        )

    if not callable(
        executor
    ):
        raise execution_governance_error(
            "executor must be callable"
        )

    execution_id = (
        execution_identity(
            envelope
        )
    )

    retry = _retry_policy(
        envelope
    )

    attempts = []
    last_error = None

    for attempt_number in range(
        1,
        retry[
            "max_attempts"
        ] + 1,
    ):
        started = now_monotonic()

        if expired(
            envelope,
            now_monotonic=started,
        ):
            error = (
                execution_deadline_error(
                    "opus request deadline "
                    "expired before execution"
                )
            )

            attempts.append(
                {
                    "attempt": (
                        attempt_number
                    ),
                    "status": (
                        "deadline_expired"
                    ),
                    "started_monotonic": (
                        started
                    ),
                    "finished_monotonic": (
                        started
                    ),
                    "duration_seconds": 0.0,
                    "error_type": type(
                        error
                    ).__name__,
                }
            )

            receipt = _receipt(
                envelope=envelope,
                execution_id=(
                    execution_id
                ),
                status="failed",
                attempts=attempts,
                error=error,
            )

            error.receipt = receipt

            raise error

        try:
            result = executor(
                envelope
            )

            finished = (
                now_monotonic()
            )

            attempts.append(
                {
                    "attempt": (
                        attempt_number
                    ),
                    "status": "succeeded",
                    "started_monotonic": (
                        started
                    ),
                    "finished_monotonic": (
                        finished
                    ),
                    "duration_seconds": (
                        max(
                            0.0,
                            finished
                            - started,
                        )
                    ),
                }
            )

            receipt = _receipt(
                envelope=envelope,
                execution_id=(
                    execution_id
                ),
                status="succeeded",
                attempts=attempts,
                result=result,
            )

            return (
                result,
                receipt,
            )

        except TimeoutError as exc:
            finished = (
                now_monotonic()
            )

            last_error = exc

            attempts.append(
                {
                    "attempt": (
                        attempt_number
                    ),
                    "status": "timeout",
                    "started_monotonic": (
                        started
                    ),
                    "finished_monotonic": (
                        finished
                    ),
                    "duration_seconds": (
                        max(
                            0.0,
                            finished
                            - started,
                        )
                    ),
                    "error_type": type(
                        exc
                    ).__name__,
                }
            )

            if not retry[
                "retry_on_timeout"
            ]:
                break

        except Exception as exc:
            finished = (
                now_monotonic()
            )

            last_error = exc

            attempts.append(
                {
                    "attempt": (
                        attempt_number
                    ),
                    "status": (
                        "provider_error"
                    ),
                    "started_monotonic": (
                        started
                    ),
                    "finished_monotonic": (
                        finished
                    ),
                    "duration_seconds": (
                        max(
                            0.0,
                            finished
                            - started,
                        )
                    ),
                    "error_type": type(
                        exc
                    ).__name__,
                }
            )

            if not retry[
                "retry_on_provider_error"
            ]:
                break

    if last_error is None:
        last_error = (
            execution_governance_error(
                "opus execution failed"
            )
        )

    receipt = _receipt(
        envelope=envelope,
        execution_id=execution_id,
        status="failed",
        attempts=attempts,
        error=last_error,
    )

    try:
        last_error.receipt = (
            receipt
        )
    except Exception:
        pass

    raise last_error
