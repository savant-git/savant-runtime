#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/palaver/"
    "conversation-outcome-evidence/1.0.0"
)

owner = "exile:palaver"
evidence_consumer = "envoy"
execution_owner = "opus"
verification_owner = "notary"

authority_effect = "none"


class conversation_outcome_evidence_error(
    RuntimeError
):
    pass


def _text(
    value: Any,
    *,
    maximum: int = 512,
) -> str:
    normalized = str(
        value
        or ""
    ).strip()

    return normalized[
        :maximum
    ]


def _identifier(
    value: Any,
) -> str:
    normalized = _text(
        value,
        maximum=256,
    )

    if not normalized:
        raise (
            conversation_outcome_evidence_error(
                "identifier is required"
            )
        )

    return normalized


def _bounded_float(
    value: Any,
    *,
    minimum: float,
    maximum: float,
) -> float | None:
    if value is None:
        return None

    try:
        numeric = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(
        numeric
    ):
        return None

    return max(
        minimum,
        min(
            maximum,
            numeric,
        ),
    )


def _nonnegative_int(
    value: Any,
) -> int:
    try:
        numeric = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0

    return max(
        0,
        numeric,
    )


def _tokens(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    normalized = {
        str(
            value
        )
        .strip()
        .lower()
        for value in values
        if str(
            value
            or ""
        ).strip()
    }

    return tuple(
        sorted(
            normalized
        )
    )


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        return {}

    return {
        str(
            key
        ):
            item
        for key, item
        in value.items()
    }


def _canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(
            value
        )
    ).hexdigest()


@dataclass(
    frozen=True
)
class operational_observation:
    success: bool
    cancelled: bool
    latency_ms: float | None
    cost: float | None
    retry_count: int
    tool_count: int
    provider_failover_count: int

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "success":
                self.success,
            "cancelled":
                self.cancelled,
            "latency_ms":
                self.latency_ms,
            "cost":
                self.cost,
            "retry_count":
                self.retry_count,
            "tool_count":
                self.tool_count,
            "provider_failover_count":
                self.provider_failover_count,
        }


def project(
    *,
    session_id: str,
    request_id: str,
    message_digest: str,
    response_digest: str,
    persona_composition_digest: str,
    active_traits: Iterable[Any] = (),
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    provider_id: str | None = None,
    model_id: str | None = None,
    success: bool = True,
    cancelled: bool = False,
    latency_ms: float | None = None,
    cost: float | None = None,
    retry_count: int = 0,
    tool_count: int = 0,
    provider_failover_count: int = 0,
    external_evaluations: Iterable[
        Mapping[
            str,
            Any,
        ]
    ] = (),
    metadata: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    session = _identifier(
        session_id
    )

    request = _identifier(
        request_id
    )

    message = _identifier(
        message_digest
    )

    response = _identifier(
        response_digest
    )

    composition = _identifier(
        persona_composition_digest
    )

    observation = (
        operational_observation(
            success=bool(
                success
            ),
            cancelled=bool(
                cancelled
            ),
            latency_ms=
                _bounded_float(
                    latency_ms,
                    minimum=0.0,
                    maximum=86_400_000.0,
                ),
            cost=
                _bounded_float(
                    cost,
                    minimum=0.0,
                    maximum=1_000_000.0,
                ),
            retry_count=
                _nonnegative_int(
                    retry_count
                ),
            tool_count=
                _nonnegative_int(
                    tool_count
                ),
            provider_failover_count=
                _nonnegative_int(
                    provider_failover_count
                ),
        )
    )

    evaluations: list[
        dict[
            str,
            Any,
        ]
    ] = []

    for raw in external_evaluations:
        value = _mapping(
            raw
        )

        if not value:
            continue

        evaluations.append(
            {
                "evaluator_owner":
                    _text(
                        value.get(
                            "evaluator_owner"
                        ),
                        maximum=128,
                    ),
                "evaluation_type":
                    _text(
                        value.get(
                            "evaluation_type"
                        ),
                        maximum=128,
                    ),
                "evidence_ref":
                    _text(
                        value.get(
                            "evidence_ref"
                        ),
                        maximum=512,
                    ),
                "admission_ref":
                    _text(
                        value.get(
                            "admission_ref"
                        ),
                        maximum=512,
                    ),
                "admitted":
                    bool(
                        value.get(
                            "admitted",
                            False,
                        )
                    ),
                "dimensions":
                    _mapping(
                        value.get(
                            "dimensions"
                        )
                    ),
            }
        )

    evaluations.sort(
        key=lambda item: (
            item[
                "evaluator_owner"
            ],
            item[
                "evaluation_type"
            ],
            item[
                "evidence_ref"
            ],
            item[
                "admission_ref"
            ],
        )
    )

    semantic = {
        "session_id":
            session,
        "request_id":
            request,
        "message_digest":
            message,
        "response_digest":
            response,
        "persona_composition_digest":
            composition,
        "active_traits":
            list(
                _tokens(
                    active_traits
                )
            ),
        "domains":
            list(
                _tokens(
                    domains
                )
            ),
        "signals":
            list(
                _tokens(
                    signals
                )
            ),
        "provider":
            {
                "provider_id":
                    _text(
                        provider_id,
                        maximum=128,
                    ),
                "model_id":
                    _text(
                        model_id,
                        maximum=256,
                    ),
            },
        "operational_observation":
            observation.projection(),
        "external_evaluations":
            evaluations,
        "metadata":
            _mapping(
                metadata
            ),
    }

    evidence_digest = (
        _digest(
            semantic
        )
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "evidence_consumer":
            evidence_consumer,
        "execution_owner":
            execution_owner,
        "verification_owner":
            verification_owner,
        "evidence_id":
            (
                "paloe_"
                + evidence_digest[
                    :32
                ]
            ),
        "evidence_digest":
            evidence_digest,
        "semantic":
            semantic,
        "authoritative":
            False,
        "evaluation_is_authority":
            False,
        "promotion_permission":
            False,
        "mutation_permission":
            False,
        "projection_only":
            True,
        "authority_effect":
            authority_effect,
    }


def replay_equivalent(
    left: Mapping[
        str,
        Any,
    ],
    right: Mapping[
        str,
        Any,
    ],
) -> bool:
    return (
        str(
            left.get(
                "evidence_digest",
                "",
            )
        )
        == str(
            right.get(
                "evidence_digest",
                "",
            )
        )
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "evidence_consumer":
            evidence_consumer,
        "execution_owner":
            execution_owner,
        "verification_owner":
            verification_owner,
        "deterministic":
            True,
        "projection_only":
            True,
        "promotion_permission":
            False,
        "mutation_permission":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    parameters = {
        "session_id":
            "session-test",
        "request_id":
            "request-test",
        "message_digest":
            "message-digest",
        "response_digest":
            "response-digest",
        "persona_composition_digest":
            "composition-digest",
        "active_traits":
            [
                "analytical_rigor",
                "uncertainty_calibration",
            ],
        "domains":
            [
                "engineering",
            ],
        "signals":
            [
                "implementation",
            ],
        "provider_id":
            "provider-test",
        "model_id":
            "model-test",
        "success":
            True,
        "latency_ms":
            125.5,
        "cost":
            0.02,
    }

    first = project(
        **parameters
    )

    second = project(
        **parameters
    )

    if not replay_equivalent(
        first,
        second,
    ):
        raise (
            conversation_outcome_evidence_error(
                "deterministic replay failed"
            )
        )

    if first[
        "promotion_permission"
    ]:
        raise (
            conversation_outcome_evidence_error(
                "evidence gained promotion authority"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "evidence_digest":
            first[
                "evidence_digest"
            ],
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
