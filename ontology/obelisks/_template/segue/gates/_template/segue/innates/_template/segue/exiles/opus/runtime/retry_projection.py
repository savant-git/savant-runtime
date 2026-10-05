from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


schema = (
    "savant://runtime/opus/"
    "retry-projection/1.0.0"
)

owner = "exile:opus"


class retry_projection_error(
    ValueError
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


def _positive_attempt(
    value: Any,
) -> int:
    try:
        attempt = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise retry_projection_error(
            "attempt must be a positive integer"
        ) from exc

    if attempt < 1:
        raise retry_projection_error(
            "attempt must be a positive integer"
        )

    return attempt


def _max_attempts(
    value: Any,
) -> int:
    try:
        attempts = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise retry_projection_error(
            "max_attempts must be an integer"
        ) from exc

    if not 1 <= attempts <= 8:
        raise retry_projection_error(
            "max_attempts must be between 1 and 8"
        )

    return attempts


def _finite_nonnegative(
    value: Any,
    *,
    field: str,
) -> float:
    try:
        number = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise retry_projection_error(
            f"{field} must be a finite "
            "nonnegative number"
        ) from exc

    if (
        not math.isfinite(
            number
        )
        or number < 0.0
    ):
        raise retry_projection_error(
            f"{field} must be a finite "
            "nonnegative number"
        )

    return number


def _retry_after(
    failure: Mapping[str, Any],
) -> float:
    value = failure.get(
        "retry_after_seconds",
        0.0,
    )

    if value is None:
        return 0.0

    return _finite_nonnegative(
        value,
        field="retry_after_seconds",
    )


def project(
    failure: Mapping[str, Any],
    *,
    attempt: int,
    max_attempts: int,
    base_delay_seconds: float = 0.25,
    maximum_delay_seconds: float = 8.0,
) -> dict[str, Any]:
    if not isinstance(
        failure,
        Mapping,
    ):
        raise retry_projection_error(
            "failure must be an object"
        )

    attempt_value = (
        _positive_attempt(
            attempt
        )
    )

    max_attempts_value = (
        _max_attempts(
            max_attempts
        )
    )

    base_delay = (
        _finite_nonnegative(
            base_delay_seconds,
            field="base_delay_seconds",
        )
    )

    maximum_delay = (
        _finite_nonnegative(
            maximum_delay_seconds,
            field="maximum_delay_seconds",
        )
    )

    if base_delay > maximum_delay:
        raise retry_projection_error(
            "base_delay_seconds must not "
            "exceed maximum_delay_seconds"
        )

    retryable = bool(
        failure.get(
            "retryable",
            False,
        )
    )

    attempts_remaining = max(
        0,
        max_attempts_value
        - attempt_value,
    )

    eligible = bool(
        retryable
        and attempts_remaining > 0
    )

    exponential_delay = min(
        maximum_delay,
        base_delay
        * (
            2
            ** max(
                0,
                attempt_value - 1,
            )
        ),
    )

    retry_after = (
        _retry_after(
            failure
        )
    )

    delay_seconds = (
        max(
            exponential_delay,
            retry_after,
        )
        if eligible
        else 0.0
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "type": (
            "opus_retry_projection"
        ),
        "attempt": attempt_value,
        "max_attempts":
            max_attempts_value,
        "attempts_remaining":
            attempts_remaining,
        "failure_retryable":
            retryable,
        "eligible": eligible,
        "delay_seconds":
            delay_seconds,
        "base_delay_seconds":
            base_delay,
        "maximum_delay_seconds":
            maximum_delay,
        "retry_after_seconds":
            retry_after,
        "deterministic": True,
        "projection_only": True,
        "authority_effect": "none",
        "boundaries": {
            "sleeps": False,
            "executes_retry": False,
            "selects_provider": False,
            "selects_model": False,
            "owns_credentials": False,
            "mutates_registry": False,
            "creates_authority": False,
        },
        "lineage": {
            "failure_projection_digest":
                failure.get(
                    "projection_digest"
                ),
            "failure_category":
                failure.get(
                    "category"
                ),
            "failure_code":
                failure.get(
                    "code"
                ),
        },
    }

    projection[
        "projection_digest"
    ] = _digest(
        projection
    )

    return projection
