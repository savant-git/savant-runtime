#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/envoy/"
    "orobouros-shadow-evolution/1.0.0"
)

owner = "exile:envoy"
persona_id = "orobouros"

evidence_source_owner = "palaver"
verification_owner = "notary"
mutation_owner = "coda"
provider_owner = "opus"

authority_effect = "none"


class orobouros_shadow_evolution_error(
    RuntimeError
):
    pass


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


def _tokens(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    return tuple(
        sorted(
            {
                str(
                    item
                )
                .strip()
                .lower()
                for item in values
                if str(
                    item
                    or ""
                ).strip()
            }
        )
    )


def _finite(
    value: Any,
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

    return numeric


def _operational_score(
    observation: Mapping[
        str,
        Any,
    ],
) -> float:
    success = bool(
        observation.get(
            "success",
            False,
        )
    )

    cancelled = bool(
        observation.get(
            "cancelled",
            False,
        )
    )

    retry_count = max(
        0,
        int(
            observation.get(
                "retry_count",
                0,
            )
            or 0
        ),
    )

    failover_count = max(
        0,
        int(
            observation.get(
                "provider_failover_count",
                0,
            )
            or 0
        ),
    )

    latency = _finite(
        observation.get(
            "latency_ms"
        )
    )

    score = (
        1.0
        if success
        else 0.0
    )

    if cancelled:
        score -= 0.20

    score -= min(
        0.20,
        retry_count
        * 0.04,
    )

    score -= min(
        0.15,
        failover_count
        * 0.05,
    )

    if (
        latency is not None
        and latency > 0
    ):
        if latency > 60_000:
            score -= 0.15
        elif latency > 30_000:
            score -= 0.10
        elif latency > 10_000:
            score -= 0.05

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


def _admitted_dimensions(
    evidence: Mapping[
        str,
        Any,
    ],
) -> list[
    dict[
        str,
        Any,
    ]
]:
    semantic = _mapping(
        evidence.get(
            "semantic"
        )
    )

    evaluations = semantic.get(
        "external_evaluations"
    )

    if not isinstance(
        evaluations,
        list,
    ):
        return []

    admitted: list[
        dict[
            str,
            Any,
        ]
    ] = []

    for raw in evaluations:
        evaluation = _mapping(
            raw
        )

        if not evaluation.get(
            "admitted",
            False,
        ):
            continue

        if not str(
            evaluation.get(
                "admission_ref",
                "",
            )
        ).strip():
            continue

        admitted.append(
            evaluation
        )

    return admitted


def _quality_score(
    evidence: Mapping[
        str,
        Any,
    ],
) -> float | None:
    evaluations = (
        _admitted_dimensions(
            evidence
        )
    )

    values: list[
        float
    ] = []

    for evaluation in evaluations:
        dimensions = _mapping(
            evaluation.get(
                "dimensions"
            )
        )

        for key in (
            "correctness",
            "reliability",
            "authority_compliance",
            "uncertainty_calibration",
            "contextual_suitability",
        ):
            numeric = _finite(
                dimensions.get(
                    key
                )
            )

            if numeric is None:
                continue

            values.append(
                max(
                    0.0,
                    min(
                        1.0,
                        numeric,
                    ),
                )
            )

    if not values:
        return None

    return sum(
        values
    ) / len(
        values
    )


def _evidence_summary(
    evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[str, Any]:
    records: list[
        dict[
            str,
            Any,
        ]
    ] = []

    operational: list[
        float
    ] = []

    quality: list[
        float
    ] = []

    for raw in evidence:
        item = _mapping(
            raw
        )

        if not item:
            continue

        if (
            item.get(
                "owner"
            )
            != evidence_source_owner
        ):
            continue

        if item.get(
            "authority_effect"
        ) != "none":
            continue

        semantic = _mapping(
            item.get(
                "semantic"
            )
        )

        observation = _mapping(
            semantic.get(
                "operational_observation"
            )
        )

        records.append(
            item
        )

        operational.append(
            _operational_score(
                observation
            )
        )

        quality_value = (
            _quality_score(
                item
            )
        )

        if quality_value is not None:
            quality.append(
                quality_value
            )

    return {
        "sample_count":
            len(
                records
            ),
        "quality_sample_count":
            len(
                quality
            ),
        "operational_score":
            (
                sum(
                    operational
                )
                / len(
                    operational
                )
                if operational
                else None
            ),
        "quality_score":
            (
                sum(
                    quality
                )
                / len(
                    quality
                )
                if quality
                else None
            ),
        "evidence_digests":
            sorted(
                {
                    str(
                        item.get(
                            "evidence_digest",
                            "",
                        )
                    )
                    for item in records
                    if str(
                        item.get(
                            "evidence_digest",
                            "",
                        )
                    )
                }
            ),
    }


def evaluate_shadow(
    *,
    accepted_receipt: Mapping[
        str,
        Any,
    ],
    challenger_receipt: Mapping[
        str,
        Any,
    ],
    accepted_evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ] = (),
    challenger_evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ] = (),
    minimum_samples: int = 5,
    minimum_quality_samples: int = 0,
    required_margin: float = 0.02,
    regression_tolerance: float = 0.01,
) -> dict[str, Any]:
    accepted = _mapping(
        accepted_receipt
    )

    challenger = _mapping(
        challenger_receipt
    )

    if not accepted:
        raise (
            orobouros_shadow_evolution_error(
                "accepted composition receipt "
                "is required"
            )
        )

    if not challenger:
        raise (
            orobouros_shadow_evolution_error(
                "challenger composition receipt "
                "is required"
            )
        )

    accepted_traits = _tokens(
        accepted.get(
            "active_traits",
            (),
        )
    )

    challenger_traits = _tokens(
        challenger.get(
            "active_traits",
            (),
        )
    )

    accepted_summary = (
        _evidence_summary(
            accepted_evidence
        )
    )

    challenger_summary = (
        _evidence_summary(
            challenger_evidence
        )
    )

    minimum_samples = max(
        1,
        int(
            minimum_samples
        ),
    )

    minimum_quality_samples = max(
        0,
        int(
            minimum_quality_samples
        ),
    )

    required_margin = max(
        0.0,
        float(
            required_margin
        ),
    )

    regression_tolerance = max(
        0.0,
        float(
            regression_tolerance
        ),
    )

    blockers: list[str] = []

    if (
        challenger_summary[
            "sample_count"
        ]
        < minimum_samples
    ):
        blockers.append(
            "insufficient_challenger_samples"
        )

    if (
        challenger_summary[
            "quality_sample_count"
        ]
        < minimum_quality_samples
    ):
        blockers.append(
            "insufficient_admitted_quality_samples"
        )

    accepted_operational = (
        accepted_summary[
            "operational_score"
        ]
    )

    challenger_operational = (
        challenger_summary[
            "operational_score"
        ]
    )

    operational_delta = None

    if (
        accepted_operational
        is not None
        and challenger_operational
        is not None
    ):
        operational_delta = (
            challenger_operational
            - accepted_operational
        )

        if (
            operational_delta
            < -regression_tolerance
        ):
            blockers.append(
                "operational_regression"
            )

    accepted_quality = (
        accepted_summary[
            "quality_score"
        ]
    )

    challenger_quality = (
        challenger_summary[
            "quality_score"
        ]
    )

    quality_delta = None

    if (
        accepted_quality
        is not None
        and challenger_quality
        is not None
    ):
        quality_delta = (
            challenger_quality
            - accepted_quality
        )

        if (
            quality_delta
            < -regression_tolerance
        ):
            blockers.append(
                "quality_regression"
            )

    evidence_margin_met = False

    comparable_deltas = [
        value
        for value in (
            operational_delta,
            quality_delta,
        )
        if value is not None
    ]

    if comparable_deltas:
        evidence_margin_met = (
            sum(
                comparable_deltas
            )
            / len(
                comparable_deltas
            )
            >= required_margin
        )

    if not comparable_deltas:
        blockers.append(
            "no_comparable_evidence"
        )
    elif not evidence_margin_met:
        blockers.append(
            "required_margin_not_met"
        )

    semantic = {
        "persona_id":
            persona_id,
        "accepted":
            {
                "composition_digest":
                    str(
                        accepted.get(
                            "composition_digest",
                            "",
                        )
                    ),
                "active_traits":
                    list(
                        accepted_traits
                    ),
            },
        "challenger":
            {
                "composition_digest":
                    str(
                        challenger.get(
                            "composition_digest",
                            "",
                        )
                    ),
                "active_traits":
                    list(
                        challenger_traits
                    ),
            },
        "accepted_evidence":
            accepted_summary,
        "challenger_evidence":
            challenger_summary,
        "policy":
            {
                "minimum_samples":
                    minimum_samples,
                "minimum_quality_samples":
                    minimum_quality_samples,
                "required_margin":
                    required_margin,
                "regression_tolerance":
                    regression_tolerance,
            },
        "comparison":
            {
                "operational_delta":
                    operational_delta,
                "quality_delta":
                    quality_delta,
                "evidence_margin_met":
                    evidence_margin_met,
            },
        "blockers":
            sorted(
                set(
                    blockers
                )
            ),
    }

    shadow_digest = (
        _digest(
            semantic
        )
    )

    recommendation = (
        "eligible_for_authoritative_review"
        if not blockers
        else "hold"
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "shadow_id":
            (
                "oroshadow_"
                + shadow_digest[
                    :32
                ]
            ),
        "shadow_digest":
            shadow_digest,
        "semantic":
            semantic,
        "recommendation":
            recommendation,
        "promotion_executed":
            False,
        "accepted_composition_mutated":
            False,
        "baseline_mutated":
            False,
        "crown_mutated":
            False,
        "requires_authoritative_review":
            (
                recommendation
                == "eligible_for_authoritative_review"
            ),
        "verification_owner":
            verification_owner,
        "mutation_owner":
            mutation_owner,
        "provider_owner":
            provider_owner,
        "evidence_is_authority":
            False,
        "shadow_only":
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
                "shadow_digest",
                "",
            )
        )
        == str(
            right.get(
                "shadow_digest",
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
        "persona_id":
            persona_id,
        "mode":
            "shadow-only",
        "evidence_source_owner":
            evidence_source_owner,
        "verification_owner":
            verification_owner,
        "mutation_owner":
            mutation_owner,
        "provider_owner":
            provider_owner,
        "promotion_executed":
            False,
        "accepted_composition_mutated":
            False,
        "baseline_mutated":
            False,
        "crown_mutated":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    accepted_receipt = {
        "composition_digest":
            "accepted-composition",
        "active_traits":
            [
                "analytical_rigor",
                "uncertainty_calibration",
            ],
    }

    challenger_receipt = {
        "composition_digest":
            "challenger-composition",
        "active_traits":
            [
                "analytical_rigor",
                "uncertainty_calibration",
                "planning",
            ],
    }

    def evidence(
        suffix: str,
        success: bool,
    ) -> dict[str, Any]:
        semantic = {
            "operational_observation":
                {
                    "success":
                        success,
                    "cancelled":
                        False,
                    "latency_ms":
                        100.0,
                    "cost":
                        0.01,
                    "retry_count":
                        0,
                    "tool_count":
                        0,
                    "provider_failover_count":
                        0,
                },
            "external_evaluations":
                [],
        }

        return {
            "owner":
                "palaver",
            "authority_effect":
                "none",
            "evidence_digest":
                "evidence-"
                + suffix,
            "semantic":
                semantic,
        }

    accepted_evidence = [
        evidence(
            f"a-{index}",
            True,
        )
        for index in range(
            5
        )
    ]

    challenger_evidence = [
        evidence(
            f"c-{index}",
            True,
        )
        for index in range(
            5
        )
    ]

    first = evaluate_shadow(
        accepted_receipt=
            accepted_receipt,
        challenger_receipt=
            challenger_receipt,
        accepted_evidence=
            accepted_evidence,
        challenger_evidence=
            challenger_evidence,
        minimum_samples=
            5,
        required_margin=
            0.0,
    )

    second = evaluate_shadow(
        accepted_receipt=
            accepted_receipt,
        challenger_receipt=
            challenger_receipt,
        accepted_evidence=
            accepted_evidence,
        challenger_evidence=
            challenger_evidence,
        minimum_samples=
            5,
        required_margin=
            0.0,
    )

    if not replay_equivalent(
        first,
        second,
    ):
        raise (
            orobouros_shadow_evolution_error(
                "deterministic shadow replay failed"
            )
        )

    if first[
        "promotion_executed"
    ]:
        raise (
            orobouros_shadow_evolution_error(
                "shadow evaluation mutated persona"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "shadow_digest":
            first[
                "shadow_digest"
            ],
        "recommendation":
            first[
                "recommendation"
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
