from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Mapping

from .enterprise_request import expired
from .execution_failure_adapter import (
    project_deadline,
    project_internal_execution,
    project_timeout,
)
from .retry_projection import (
    project as project_retry,
)


schema = (
    "savant://runtime/opus/"
    "execution-governance/1.1.0"
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
            "retry_on_provider_error":
                False,
            "retry_on_timeout":
                False,
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
        "request_id":
            envelope.get(
                "request_id"
            ),
        "canonical_digest":
            envelope.get(
                "canonical_digest"
            ),
        "tenant_id":
            envelope.get(
                "tenant_id"
            ),
        "idempotency_key":
            envelope.get(
                "idempotency_key"
            ),
    }

    return (
        "opusexec_"
        + _digest(
            material
        )[:32]
    )


def _failure_provenance(
    envelope: Mapping[str, Any],
    *,
    execution_id: str,
    attempt: int,
) -> dict[str, Any]:
    return {
        "request_id":
            envelope.get(
                "request_id"
            ),
        "trace_id":
            envelope.get(
                "trace_id"
            ),
        "tenant_id":
            envelope.get(
                "tenant_id"
            ),
        "execution_id":
            execution_id,
        "attempt":
            attempt,
    }


def _receipt(
    *,
    envelope: Mapping[str, Any],
    execution_id: str,
    status: str,
    attempts: list[
        dict[str, Any]
    ],
    result: Any = None,
    error: BaseException | None = None,
    failure: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    receipt = {
        "schema": schema,
        "owner": owner,
        "type":
            "opus_execution_receipt",
        "execution_id":
            execution_id,
        "request_id":
            envelope.get(
                "request_id"
            ),
        "request_digest":
            envelope.get(
                "canonical_digest"
            ),
        "tenant_id":
            envelope.get(
                "tenant_id"
            ),
        "trace_id":
            envelope.get(
                "trace_id"
            ),
        "status":
            status,
        "attempt_count":
            len(
                attempts
            ),
        "attempts":
            attempts,
        "authority_effect":
            "none",
        "boundaries": {
            "selects_provider": False,
            "selects_model": False,
            "owns_credentials": False,
            "mutates_registry": False,
            "creates_authority": False,
            "canonical_execution":
                "opus.runtime.router",
        },
    }

    if result is not None:
        receipt[
            "result_digest"
        ] = _digest(
            result
        )

    if failure is not None:
        receipt[
            "failure"
        ] = dict(
            failure
        )

    elif error is not None:
        receipt[
            "error"
        ] = {
            "type":
                type(
                    error
                ).__name__,
        }

    receipt[
        "receipt_digest"
    ] = _digest(
        receipt
    )

    return receipt


def _attempt_record(
    *,
    attempt_number: int,
    status: str,
    started: float,
    finished: float,
    error: BaseException | None = None,
    failure: Mapping[
        str,
        Any,
    ] | None = None,
    retry: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    record = {
        "attempt":
            attempt_number,
        "status":
            status,
        "started_monotonic":
            started,
        "finished_monotonic":
            finished,
        "duration_seconds":
            max(
                0.0,
                finished
                - started,
            ),
    }

    if error is not None:
        record[
            "error_type"
        ] = type(
            error
        ).__name__

    if failure is not None:
        record[
            "failure"
        ] = dict(
            failure
        )

    if retry is not None:
        record[
            "retry"
        ] = dict(
            retry
        )

    return record


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

    policy = _retry_policy(
        envelope
    )

    attempts: list[
        dict[str, Any]
    ] = []

    last_error: BaseException | None = (
        None
    )

    last_failure: dict[
        str,
        Any,
    ] | None = None

    for attempt_number in range(
        1,
        policy[
            "max_attempts"
        ] + 1,
    ):
        started = (
            now_monotonic()
        )

        provenance = (
            _failure_provenance(
                envelope,
                execution_id=
                    execution_id,
                attempt=
                    attempt_number,
            )
        )

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

            failure = project_deadline(
                error,
                **provenance,
            )

            retry = project_retry(
                failure,
                attempt=
                    attempt_number,
                max_attempts=
                    policy[
                        "max_attempts"
                    ],
            )

            attempts.append(
                _attempt_record(
                    attempt_number=
                        attempt_number,
                    status=
                        "deadline_expired",
                    started=
                        started,
                    finished=
                        started,
                    error=
                        error,
                    failure=
                        failure,
                    retry=
                        retry,
                )
            )

            receipt = _receipt(
                envelope=
                    envelope,
                execution_id=
                    execution_id,
                status=
                    "failed",
                attempts=
                    attempts,
                error=
                    error,
                failure=
                    failure,
            )

            error.receipt = (
                receipt
            )

            error.failure = (
                failure
            )

            raise error

        try:
            result = executor(
                envelope
            )

            finished = (
                now_monotonic()
            )

            attempts.append(
                _attempt_record(
                    attempt_number=
                        attempt_number,
                    status=
                        "succeeded",
                    started=
                        started,
                    finished=
                        finished,
                )
            )

            receipt = _receipt(
                envelope=
                    envelope,
                execution_id=
                    execution_id,
                status=
                    "succeeded",
                attempts=
                    attempts,
                result=
                    result,
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

            failure = project_timeout(
                exc,
                **provenance,
            )

            retry = project_retry(
                failure,
                attempt=
                    attempt_number,
                max_attempts=
                    policy[
                        "max_attempts"
                    ],
            )

            compatibility_allows = (
                policy[
                    "retry_on_timeout"
                ]
            )

            eligible = bool(
                retry.get(
                    "eligible",
                    False,
                )
                and compatibility_allows
            )

            retry = dict(
                retry
            )

            retry[
                "compatibility_policy_allows"
            ] = compatibility_allows

            retry[
                "execute_retry"
            ] = eligible

            last_failure = (
                failure
            )

            attempts.append(
                _attempt_record(
                    attempt_number=
                        attempt_number,
                    status=
                        "timeout",
                    started=
                        started,
                    finished=
                        finished,
                    error=
                        exc,
                    failure=
                        failure,
                    retry=
                        retry,
                )
            )

            if not eligible:
                break

        except Exception as exc:
            finished = (
                now_monotonic()
            )

            last_error = exc

            failure = (
                project_internal_execution(
                    exc,
                    **provenance,
                )
            )

            retry = project_retry(
                failure,
                attempt=
                    attempt_number,
                max_attempts=
                    policy[
                        "max_attempts"
                    ],
            )

            compatibility_allows = (
                policy[
                    "retry_on_provider_error"
                ]
            )

            eligible = bool(
                retry.get(
                    "eligible",
                    False,
                )
                and compatibility_allows
            )

            retry = dict(
                retry
            )

            retry[
                "compatibility_policy_allows"
            ] = compatibility_allows

            retry[
                "execute_retry"
            ] = eligible

            last_failure = (
                failure
            )

            attempts.append(
                _attempt_record(
                    attempt_number=
                        attempt_number,
                    status=
                        "internal_execution",
                    started=
                        started,
                    finished=
                        finished,
                    error=
                        exc,
                    failure=
                        failure,
                    retry=
                        retry,
                )
            )

            if not eligible:
                break

    if last_error is None:
        last_error = (
            execution_governance_error(
                "opus execution failed"
            )
        )

    receipt = _receipt(
        envelope=
            envelope,
        execution_id=
            execution_id,
        status=
            "failed",
        attempts=
            attempts,
        error=
            last_error,
        failure=
            last_failure,
    )

    try:
        last_error.receipt = (
            receipt
        )

        last_error.failure = (
            last_failure
        )
    except Exception:
        pass

    raise last_error
