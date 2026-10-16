#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )

from environment import load_environment
from cognitive_benchmark_suite import benchmark_cases
from cognitive_router_bridge import execute


PROVEN_PROVIDERS = (
    "catalog_text",
    "openai_text",
    "anthropic_text",
)

QUALITY_DIMENSIONS = (
    "expected_coverage",
    "forbidden_claim_control",
    "exact_constraint_satisfaction",
    "execution_success",
)

SIGNIFICANT_ABSOLUTE_GAIN = 0.05
SIGNIFICANT_RELATIVE_GAIN = 0.10


def normalize(
    value: Any,
) -> str:
    return " ".join(
        str(
            value
            or ""
        ).strip().lower().split()
    )


def output_text(
    result: Mapping[str, Any],
) -> str:
    for key in (
        "text",
        "output",
        "response",
        "content",
    ):
        value = result.get(
            key
        )

        if isinstance(
            value,
            str,
        ) and value.strip():
            return value.strip()

    return ""


def expected_score(
    text: str,
    expected: Iterable[str],
) -> float:
    values = tuple(
        normalize(
            item
        )
        for item in expected
        if normalize(
            item
        )
    )

    if not values:
        return 1.0

    body = normalize(
        text
    )

    hits = sum(
        1
        for value in values
        if value in body
    )

    return hits / len(
        values
    )


def forbidden_score(
    text: str,
    forbidden: Iterable[str],
) -> float:
    values = tuple(
        normalize(
            item
        )
        for item in forbidden
        if normalize(
            item
        )
    )

    if not values:
        return 1.0

    body = normalize(
        text
    )

    violations = sum(
        1
        for value in values
        if value in body
    )

    return 1.0 - (
        violations
        / len(
            values
        )
    )


def exact_score(
    text: str,
    exact_output: Iterable[str],
) -> float:
    expected = tuple(
        str(
            item
        ).strip()
        for item in exact_output
    )

    if not expected:
        return 1.0

    observed = tuple(
        line.strip()
        for line in str(
            text
        ).strip().splitlines()
    )

    return (
        1.0
        if observed == expected
        else 0.0
    )


def score_output(
    *,
    text: str,
    ok: bool,
    expected: Iterable[str],
    forbidden: Iterable[str],
    exact_output: Iterable[str],
) -> Dict[str, float]:
    expected_coverage = (
        expected_score(
            text,
            expected,
        )
    )

    forbidden_control = (
        forbidden_score(
            text,
            forbidden,
        )
    )

    exact_constraint = (
        exact_score(
            text,
            exact_output,
        )
    )

    execution_success = (
        1.0
        if ok and bool(
            text.strip()
        )
        else 0.0
    )

    exact_required = bool(
        tuple(
            exact_output
        )
    )

    if exact_required:
        weights = {
            "expected_coverage":
                0.15,
            "forbidden_claim_control":
                0.15,
            "exact_constraint_satisfaction":
                0.60,
            "execution_success":
                0.10,
        }

    else:
        weights = {
            "expected_coverage":
                0.45,
            "forbidden_claim_control":
                0.35,
            "exact_constraint_satisfaction":
                0.10,
            "execution_success":
                0.10,
        }

    dimensions = {
        "expected_coverage":
            expected_coverage,
        "forbidden_claim_control":
            forbidden_control,
        "exact_constraint_satisfaction":
            exact_constraint,
        "execution_success":
            execution_success,
    }

    dimensions[
        "quality"
    ] = sum(
        dimensions[
            key
        ]
        * weight
        for key, weight
        in weights.items()
    )

    return dimensions


def baseline_request(
    case: Any,
) -> Dict[str, Any]:
    return {
        "owner":
            "opus_benchmark",
        "prompt":
            case.prompt,
        "text":
            case.prompt,
        "system": (
            "Answer the task using only the supplied "
            "authority context. Distinguish established "
            "facts from inference. Do not invent missing "
            "authority."
        ),
        "authority_context":
            case.authority_context,
        "required_capabilities": [
            "text_inference",
        ],
        "cognitive_orchestration":
            False,
        "preferred_provider":
            "openai_text",
        "benchmark_mode":
            "baseline",
    }


def opus_request(
    case: Any,
) -> Dict[str, Any]:
    return {
        "owner":
            "opus_benchmark",
        "prompt":
            case.prompt,
        "text":
            case.prompt,
        "system": (
            "Answer the task using only the supplied "
            "authority context. Distinguish established "
            "facts from inference. Do not invent missing "
            "authority. Preserve authority precedence, "
            "lineage, provenance, terminology succession, "
            "and explicit uncertainty."
        ),
        "authority_context":
            case.authority_context,
        "required_capabilities": [
            "text_inference",
        ],
        "cognitive_orchestration":
            True,
        "available_providers":
            list(
                PROVEN_PROVIDERS
            ),
        "benchmark_mode":
            "opus",
        "verification_required":
            True,
        "authority_sensitive":
            True,
    }


def run_request(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    started = time.perf_counter()

    try:
        result = execute(
            request
        )

        if not isinstance(
            result,
            Mapping,
        ):
            raise RuntimeError(
                "benchmark execution returned non-mapping result"
            )

        result = dict(
            result
        )

        ok = bool(
            result.get(
                "ok",
                bool(
                    output_text(
                        result
                    )
                ),
            )
        )

        error = None

    except Exception as exc:
        result = {}
        ok = False
        error = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    latency_ms = (
        time.perf_counter()
        - started
    ) * 1000.0

    return {
        "ok":
            ok,
        "text":
            output_text(
                result
            ),
        "provider":
            result.get(
                "provider"
            ),
        "model":
            result.get(
                "model"
            ),
        "lineage":
            result.get(
                "lineage"
            ),
        "synthesis":
            result.get(
                "synthesis"
            ),
        "strategy":
            result.get(
                "strategy"
            ),
        "provider_count":
            result.get(
                "provider_count"
            ),
        "healthy_provider_count":
            result.get(
                "healthy_provider_count"
            ),
        "latency_ms":
            round(
                latency_ms,
                3,
            ),
        "error":
            error
            or result.get(
                "error"
            ),
    }


def mean(
    values: Iterable[float],
) -> float:
    items = list(
        values
    )

    if not items:
        return 0.0

    return statistics.fmean(
        items
    )


def bootstrap_ci(
    deltas: list[float],
) -> Dict[str, float | None]:
    if len(
        deltas
    ) < 2:
        return {
            "mean":
                mean(
                    deltas
                ),
            "standard_error":
                None,
            "ci95_low":
                None,
            "ci95_high":
                None,
        }

    observed = mean(
        deltas
    )

    standard_error = (
        statistics.stdev(
            deltas
        )
        / math.sqrt(
            len(
                deltas
            )
        )
    )

    margin = (
        1.96
        * standard_error
    )

    return {
        "mean":
            observed,
        "standard_error":
            standard_error,
        "ci95_low":
            observed
            - margin,
        "ci95_high":
            observed
            + margin,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--require-improvement",
        action="store_true",
    )

    args = parser.parse_args()

    if args.repetitions < 1:
        raise SystemExit(
            "--repetitions must be >= 1"
        )

    load_environment()

    cases = benchmark_cases()

    observations: list[
        Dict[str, Any]
    ] = []

    for repetition in range(
        1,
        args.repetitions + 1,
    ):
        for case in cases:
            baseline = run_request(
                baseline_request(
                    case
                )
            )

            opus = run_request(
                opus_request(
                    case
                )
            )

            baseline_score = score_output(
                text=baseline[
                    "text"
                ],
                ok=baseline[
                    "ok"
                ],
                expected=case.expected_constraints,
                forbidden=case.forbidden_claims,
                exact_output=case.exact_output,
            )

            opus_score = score_output(
                text=opus[
                    "text"
                ],
                ok=opus[
                    "ok"
                ],
                expected=case.expected_constraints,
                forbidden=case.forbidden_claims,
                exact_output=case.exact_output,
            )

            delta = (
                opus_score[
                    "quality"
                ]
                - baseline_score[
                    "quality"
                ]
            )

            observations.append(
                {
                    "repetition":
                        repetition,
                    "case_id":
                        case.case_id,
                    "category":
                        case.category,
                    "weight":
                        case.weight,
                    "baseline":
                        baseline,
                    "opus":
                        opus,
                    "baseline_score":
                        baseline_score,
                    "opus_score":
                        opus_score,
                    "quality_delta":
                        delta,
                }
            )

    baseline_quality = mean(
        item[
            "baseline_score"
        ][
            "quality"
        ]
        for item in observations
    )

    opus_quality = mean(
        item[
            "opus_score"
        ][
            "quality"
        ]
        for item in observations
    )

    absolute_gain = (
        opus_quality
        - baseline_quality
    )

    relative_gain = (
        absolute_gain
        / baseline_quality
        if baseline_quality > 0.0
        else None
    )

    wins = sum(
        1
        for item in observations
        if item[
            "quality_delta"
        ] > 1e-9
    )

    ties = sum(
        1
        for item in observations
        if abs(
            item[
                "quality_delta"
            ]
        ) <= 1e-9
    )

    losses = sum(
        1
        for item in observations
        if item[
            "quality_delta"
        ] < -1e-9
    )

    by_category: dict[
        str,
        list[
            Dict[str, Any]
        ],
    ] = defaultdict(
        list
    )

    for item in observations:
        by_category[
            item[
                "category"
            ]
        ].append(
            item
        )

    categories: Dict[
        str,
        Any,
    ] = {}

    for category, items in sorted(
        by_category.items()
    ):
        baseline_category = mean(
            item[
                "baseline_score"
            ][
                "quality"
            ]
            for item in items
        )

        opus_category = mean(
            item[
                "opus_score"
            ][
                "quality"
            ]
            for item in items
        )

        categories[
            category
        ] = {
            "baseline":
                baseline_category,
            "opus":
                opus_category,
            "absolute_gain":
                opus_category
                - baseline_category,
        }

    dimension_deltas: Dict[
        str,
        float,
    ] = {}

    for dimension in QUALITY_DIMENSIONS:
        baseline_dimension = mean(
            item[
                "baseline_score"
            ][
                dimension
            ]
            for item in observations
        )

        opus_dimension = mean(
            item[
                "opus_score"
            ][
                dimension
            ]
            for item in observations
        )

        dimension_deltas[
            dimension
        ] = (
            opus_dimension
            - baseline_dimension
        )

    baseline_latency = mean(
        item[
            "baseline"
        ][
            "latency_ms"
        ]
        for item in observations
    )

    opus_latency = mean(
        item[
            "opus"
        ][
            "latency_ms"
        ]
        for item in observations
    )

    deltas = [
        item[
            "quality_delta"
        ]
        for item in observations
    ]

    uncertainty = bootstrap_ci(
        deltas
    )

    authority_regression = (
        categories.get(
            "authority_compliance",
            {},
        ).get(
            "absolute_gain",
            0.0,
        )
        < -1e-9
    )

    unsupported_regression = (
        categories.get(
            "unsupported_claim_control",
            {},
        ).get(
            "absolute_gain",
            0.0,
        )
        < -1e-9
    )

    material_improvement = bool(
        absolute_gain
        >= SIGNIFICANT_ABSOLUTE_GAIN
        and (
            relative_gain is not None
            and relative_gain
            >= SIGNIFICANT_RELATIVE_GAIN
        )
        and wins > losses
        and not authority_regression
        and not unsupported_regression
    )

    output = {
        "schema":
            "opus.cognitive_benchmark.v2",
        "experiment": {
            "baseline":
                "single-provider AI without cognitive orchestration",
            "opus":
                (
                    "Opus cognitive orchestration using only "
                    "catalog_text, openai_text, anthropic_text"
                ),
            "providers":
                list(
                    PROVEN_PROVIDERS
                ),
            "case_count":
                len(
                    cases
                ),
            "repetitions":
                args.repetitions,
            "observation_count":
                len(
                    observations
                ),
        },
        "quality": {
            "baseline":
                baseline_quality,
            "opus":
                opus_quality,
            "absolute_gain":
                absolute_gain,
            "percentage_point_gain":
                absolute_gain
                * 100.0,
            "relative_gain":
                relative_gain,
            "relative_gain_percent":
                (
                    relative_gain
                    * 100.0
                    if relative_gain
                    is not None
                    else None
                ),
            "wins":
                wins,
            "ties":
                ties,
            "losses":
                losses,
            "material_improvement":
                material_improvement,
            "thresholds": {
                "minimum_absolute_gain":
                    SIGNIFICANT_ABSOLUTE_GAIN,
                "minimum_relative_gain":
                    SIGNIFICANT_RELATIVE_GAIN,
                "wins_must_exceed_losses":
                    True,
                "authority_regression_allowed":
                    False,
                "unsupported_claim_regression_allowed":
                    False,
            },
        },
        "uncertainty":
            uncertainty,
        "latency": {
            "baseline_mean_ms":
                baseline_latency,
            "opus_mean_ms":
                opus_latency,
            "multiplier":
                (
                    opus_latency
                    / baseline_latency
                    if baseline_latency > 0
                    else None
                ),
        },
        "dimension_deltas":
            dimension_deltas,
        "category_results":
            categories,
        "observations":
            observations,
    }

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        args.require_improvement
        and not material_improvement
    ):
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
