from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from cognitive_capabilities import (
    canonical_list,
    provider_capabilities,
)


class ProviderState(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderHealth:
    provider_id: str
    state: ProviderState
    usable: bool
    capabilities: tuple[str, ...]
    latency_ms: float | None
    success_rate: float | None
    consecutive_failures: int
    last_success_at: float | None
    last_failure_at: float | None
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "state": self.state.value,
            "usable": self.usable,
            "capabilities": list(
                self.capabilities
            ),
            "latency_ms": self.latency_ms,
            "success_rate": self.success_rate,
            "consecutive_failures":
                self.consecutive_failures,
            "last_success_at":
                self.last_success_at,
            "last_failure_at":
                self.last_failure_at,
            "reason": self.reason,
        }


def _bounded(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        number = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


def _number(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def evaluate_provider_health(
    provider: Mapping[str, Any],
    *,
    now: float | None = None,
) -> ProviderHealth:
    timestamp = (
        float(now)
        if now is not None
        else time.time()
    )

    provider_id = str(
        provider.get("id")
        or provider.get(
            "provider_id"
        )
        or ""
    ).strip()

    if not provider_id:
        raise ValueError(
            "provider requires id"
        )

    configured = provider.get(
        "configured"
    )

    if configured is None:
        configured = provider.get(
            "available",
            True,
        )

    authenticated = provider.get(
        "authenticated"
    )

    if authenticated is None:
        authenticated = configured

    explicit_state = str(
        provider.get("state")
        or provider.get("health")
        or ""
    ).strip().lower()

    rate_limited = bool(
        provider.get(
            "rate_limited",
            False,
        )
    )

    consecutive_failures = int(
        provider.get(
            "consecutive_failures"
        )
        or 0
    )

    latency_ms = _number(
        provider.get(
            "latency_ms"
        )
    )

    success_rate = _bounded(
        provider.get(
            "success_rate"
        )
    )

    last_success_at = _number(
        provider.get(
            "last_success_at"
        )
    )

    last_failure_at = _number(
        provider.get(
            "last_failure_at"
        )
    )

    stale_success = False

    stale_after_seconds = _number(
        provider.get(
            "stale_after_seconds"
        )
    )

    if (
        stale_after_seconds is not None
        and last_success_at is not None
        and (
            timestamp
            - last_success_at
            > stale_after_seconds
        )
    ):
        stale_success = True

    if not configured:
        state = (
            ProviderState.UNAVAILABLE
        )
        usable = False
        reason = "not_configured"

    elif not authenticated:
        state = (
            ProviderState.UNAVAILABLE
        )
        usable = False
        reason = "not_authenticated"

    elif rate_limited:
        state = (
            ProviderState.RATE_LIMITED
        )
        usable = False
        reason = "rate_limited"

    elif explicit_state in {
        ProviderState.FAILED.value,
        ProviderState.UNAVAILABLE.value,
    }:
        state = ProviderState(
            explicit_state
        )
        usable = False
        reason = (
            f"explicit_{explicit_state}"
        )

    elif consecutive_failures >= 3:
        state = ProviderState.FAILED
        usable = False
        reason = (
            "consecutive_failure_threshold"
        )

    elif (
        explicit_state
        == ProviderState.DEGRADED.value
        or stale_success
        or (
            success_rate is not None
            and success_rate < 0.80
        )
        or consecutive_failures > 0
    ):
        state = ProviderState.DEGRADED
        usable = True
        reason = "degraded_but_usable"

    else:
        state = ProviderState.AVAILABLE
        usable = True
        reason = "healthy"

    return ProviderHealth(
        provider_id=provider_id,
        state=state,
        usable=usable,
        capabilities=tuple(
            sorted(
                provider_capabilities(
                    provider
                )
            )
        ),
        latency_ms=latency_ms,
        success_rate=success_rate,
        consecutive_failures=
            consecutive_failures,
        last_success_at=
            last_success_at,
        last_failure_at=
            last_failure_at,
        reason=reason,
    )


def health_rank(
    health: ProviderHealth,
) -> tuple:
    state_rank = {
        ProviderState.AVAILABLE: 0,
        ProviderState.DEGRADED: 1,
        ProviderState.UNKNOWN: 2,
        ProviderState.RATE_LIMITED: 3,
        ProviderState.UNAVAILABLE: 4,
        ProviderState.FAILED: 5,
    }

    success_penalty = (
        1.0
        - health.success_rate
        if health.success_rate
        is not None
        else 0.5
    )

    latency = (
        health.latency_ms
        if health.latency_ms
        is not None
        else float("inf")
    )

    return (
        state_rank[
            health.state
        ],
        success_penalty,
        health.consecutive_failures,
        latency,
        health.provider_id,
    )


def rank_providers_by_health(
    providers: Iterable[
        Mapping[str, Any]
    ],
) -> List[Dict[str, Any]]:
    evaluated: List[
        tuple[
            ProviderHealth,
            Dict[str, Any],
        ]
    ] = []

    for provider in providers:
        value = dict(
            provider
        )

        health = (
            evaluate_provider_health(
                value
            )
        )

        value[
            "health_evaluation"
        ] = health.as_dict()

        if health.usable:
            evaluated.append(
                (
                    health,
                    value,
                )
            )

    evaluated.sort(
        key=lambda item:
            health_rank(
                item[0]
            )
    )

    return [
        value
        for _,
        value in evaluated
    ]


def capability_healthy_providers(
    providers: Iterable[
        Mapping[str, Any]
    ],
    required_capabilities: Sequence[str],
) -> List[Dict[str, Any]]:
    required = set(
        canonical_list(
            required_capabilities
        )
    )

    output: List[
        Dict[str, Any]
    ] = []

    for provider in (
        rank_providers_by_health(
            providers
        )
    ):
        offered = set(
            provider_capabilities(
                provider
            )
        )

        if required.issubset(
            offered
        ):
            output.append(
                provider
            )

    return output
