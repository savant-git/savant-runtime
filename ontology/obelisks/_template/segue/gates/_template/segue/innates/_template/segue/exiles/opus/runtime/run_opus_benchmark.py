#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping


RUNTIME_ROOT = Path(__file__).resolve().parent

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from environment import load_environment
from cognitive_benchmark_suite import benchmark_cases
from router import (
    execute_text_request,
    provider,
)


BASELINE_PROVIDER = "openai_text"

PROVEN_OPUS_PROVIDERS = (
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
EPSILON = 1e-9


def normalize(value: Any) -> str:
    return " ".join(
        str(value or "").strip().lower().split()
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
        value = result.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    synthesis = result.get("synthesis")

    if isinstance(synthesis, Mapping):
        for key in (
            "text",
            "selected_text",
            "synthesized_text",
            "output",
            "response",
        ):
            value = synthesis.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def expected_score(
    text: str,
    expected: Iterable[str],
) -> float:
    values = tuple(
        normalize(item)
        for item in expected
        if normalize(item)
    )

    if not values:
        return 1.0

    body = normalize(text)

    hits = sum(
        1
        for value in values
        if value in body
    )

    return hits / len(values)


def forbidden_score(
    text: str,
    forbidden: Iterable[str],
) -> float:
    values = tuple(
        normalize(item)
        for item in forbidden
        if normalize(item)
    )

    if not values:
        return 1.0

    body = normalize(text)

    violations = sum(
        1
        for value in values
        if value in body
    )

    return 1.0 - (
        violations / len(values)
    )


def exact_score(
    text: str,
    exact_output: Iterable[str],
) -> float:
    expected = tuple(
        str(item).strip()
        for item in exact_output
    )

    if not expected:
        return 1.0

    observed = tuple(
        line.strip()
        for line in str(text).strip().splitlines()
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
    if not ok or not text.strip():
        return {
            "expected_coverage": 0.0,
            "forbidden_claim_control": 0.0,
            "exact_constraint_satisfaction": 0.0,
            "execution_success": 0.0,
            "quality": 0.0,
        }

    expected_values = tuple(expected)
    forbidden_values = tuple(forbidden)
    exact_values = tuple(exact_output)

    expected_coverage = expected_score(
        text,
        expected_values,
    )

    forbidden_control = forbidden_score(
        text,
        forbidden_values,
    )

    exact_constraint = exact_score(
        text,
        exact_values,
    )

    execution_success = 1.0

    if exact_values:
        weights = {
            "expected_coverage": 0.15,
            "forbidden_claim_control": 0.15,
            "exact_constraint_satisfaction": 0.60,
            "execution_success": 0.10,
        }
    else:
        weights = {
            "expected_coverage": 0.45,
            "forbidden_claim_control": 0.35,
            "exact_constraint_satisfaction": 0.10,
            "execution_success": 0.10,
        }

    dimensions = {
        "expected_coverage": expected_coverage,
        "forbidden_claim_control": forbidden_control,
        "exact_constraint_satisfaction": exact_constraint,
        "execution_success": execution_success,
    }

    dimensions["quality"] = sum(
        dimensions[key] * weight
        for key, weight in weights.items()
    )

    return dimensions


def common_request(
    case: Any,
) -> Dict[str, Any]:
    return {
        "owner": "opus_benchmark",
        "prompt": case.prompt,
        "text": case.prompt,
        "system": (
            "Answer the task using only the supplied "
            "authority context. Distinguish established "
            "facts from inference. Do not invent missing "
            "authority."
        ),
        "authority_context": case.authority_context,
        "required_capabilities": [
            "text_inference",
        ],
    }


def baseline_request(
    case: Any,
) -> Dict[str, Any]:
    request = common_request(case)

    request.update(
        {
            "cognitive_orchestration": False,
            "benchmark_mode": "baseline",
        }
    )

    return request


def opus_request(
    case: Any,
) -> Dict[str, Any]:
    request = common_request(case)

    request.update(
        {
            "cognitive_orchestration": True,
            "available_providers": list(
                PROVEN_OPUS_PROVIDERS
            ),
            "benchmark_mode": "opus",
            "verification_required": True,
            "authority_sensitive": True,
        }
    )

    return request


def baseline_provider_data() -> Dict[str, Any]:
    data = dict(
        provider(BASELINE_PROVIDER)
    )

    data["id"] = BASELINE_PROVIDER

    return data


def execute_baseline(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    provider_data = baseline_provider_data()

    module = importlib.import_module(
        f"providers.{BASELINE_PROVIDER}"
    )

    available = getattr(
        module,
        "available",
        None,
    )

    if callable(available) and not available():
        raise RuntimeError(
            f"baseline provider unavailable: "
            f"{BASELINE_PROVIDER}"
        )

    infer = getattr(
        module,
        "infer",
        None,
    )

    if not callable(infer):
        raise RuntimeError(
            f"baseline provider has no infer(): "
            f"{BASELINE_PROVIDER}"
        )

    result = infer(
        request,
        provider_data,
    )

    if not isinstance(result, Mapping):
        raise RuntimeError(
            "baseline provider returned "
            "non-mapping result"
        )

    result = dict(result)

    result["lineage"] = {
        "owner": "opus_benchmark",
        "mode": "single_provider_control",
        "cognitive_orchestration": False,
        "provider": BASELINE_PROVIDER,
        "model": result.get("model"),
    }

    result["provider"] = (
        result.get("provider")
        or BASELINE_PROVIDER
    )

    result["provider_count"] = 1
    result["strategy"] = {
        "strategy": "single",
        "parallelism": 1,
        "require_adjudication": False,
        "require_counterpoint": False,
        "allow_refinement": False,
        "rationale": [
            "benchmark_control",
            "cognitive_orchestration_disabled",
        ],
    }

    return result


def execute_opus(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    result = execute_text_request(request)

    if not isinstance(result, Mapping):
        raise RuntimeError(
            "Opus returned non-mapping result"
        )

    return dict(result)


def run_request(
    request: Dict[str, Any],
    *,
    mode: str,
) -> Dict[str, Any]:
    started = time.perf_counter()

    try:
        if mode == "baseline":
            result = execute_baseline(request)
        elif mode == "opus":
            result = execute_opus(request)
        else:
            raise ValueError(
                f"unknown benchmark mode: {mode}"
            )

        text = output_text(result)

        ok = bool(
            result.get(
                "ok",
                bool(text),
            )
        ) and bool(text)

        error = (
            None
            if ok
            else result.get("error")
            or "execution produced no usable text"
        )

    except Exception as exc:
        result = {}
        text = ""
        ok = False
        error = (
            f"{type(exc).__name__}: {exc}"
        )

    latency_ms = (
        time.perf_counter() - started
    ) * 1000.0

    return {
        "ok": ok,
        "text": text,
        "provider": result.get("provider"),
        "model": result.get("model"),
        "lineage": result.get("lineage"),
        "synthesis": result.get("synthesis"),
        "strategy": result.get("strategy"),
        "provider_count": result.get(
            "provider_count"
        ),
        "healthy_provider_count": result.get(
            "healthy_provider_count"
        ),
        "latency_ms": round(
            latency_ms,
            3,
        ),
        "error": error,
    }


def mean(
    values: Iterable[float],
) -> float:
    items = list(values)

    if not items:
        return 0.0

    return statistics.fmean(items)


def confidence_interval(
    deltas: list[float],
) -> Dict[str, float | None]:
    if not deltas:
        return {
            "mean": 0.0,
            "standard_error": None,
            "ci95_low": None,
            "ci95_high": None,
        }

    observed = mean(deltas)

    if len(deltas) < 2:
        return {
            "mean": observed,
            "standard_error": None,
            "ci95_low": None,
            "ci95_high": None,
        }

    standard_error = (
        statistics.stdev(deltas)
        / math.sqrt(len(deltas))
    )

    margin = 1.96 * standard_error

    return {
        "mean": observed,
        "standard_error": standard_error,
        "ci95_low": observed - margin,
        "ci95_high": observed + margin,
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
                baseline_request(case),
                mode="baseline",
            )

            opus = run_request(
                opus_request(case),
                mode="opus",
            )

            baseline_score = score_output(
                text=baseline["text"],
                ok=baseline["ok"],
                expected=case.expected_constraints,
                forbidden=case.forbidden_claims,
                exact_output=case.exact_output,
            )

            opus_score = score_output(
                text=opus["text"],
                ok=opus["ok"],
                expected=case.expected_constraints,
                forbidden=case.forbidden_claims,
                exact_output=case.exact_output,
            )

            delta = (
                opus_score["quality"]
                - baseline_score["quality"]
            )

            observations.append(
                {
                    "repetition": repetition,
                    "case_id": case.case_id,
                    "category": case.category,
                    "weight": case.weight,
                    "baseline": baseline,
                    "opus": opus,
                    "baseline_score": baseline_score,
                    "opus_score": opus_score,
                    "quality_delta": delta,
                }
            )

    baseline_successes = sum(
        1
        for item in observations
        if item["baseline"]["ok"]
    )

    opus_successes = sum(
        1
        for item in observations
        if item["opus"]["ok"]
    )

    valid_pairs = [
        item
        for item in observations
        if (
            item["baseline"]["ok"]
            and item["opus"]["ok"]
        )
    ]

    execution_valid = (
        len(valid_pairs)
        == len(observations)
        and bool(valid_pairs)
    )

    baseline_quality = mean(
        item["baseline_score"]["quality"]
        for item in valid_pairs
    )

    opus_quality = mean(
        item["opus_score"]["quality"]
        for item in valid_pairs
    )

    absolute_gain = (
        opus_quality - baseline_quality
    )

    relative_gain = (
        absolute_gain / baseline_quality
        if (
            valid_pairs
            and baseline_quality > 0.0
        )
        else None
    )

    wins = sum(
        1
        for item in valid_pairs
        if item["quality_delta"] > EPSILON
    )

    ties = sum(
        1
        for item in valid_pairs
        if abs(
            item["quality_delta"]
        ) <= EPSILON
    )

    losses = sum(
        1
        for item in valid_pairs
        if item["quality_delta"] < -EPSILON
    )

    by_category: dict[
        str,
        list[Dict[str, Any]],
    ] = defaultdict(list)

    for item in valid_pairs:
        by_category[
            item["category"]
        ].append(item)

    categories: Dict[str, Any] = {}

    for category, items in sorted(
        by_category.items()
    ):
        baseline_category = mean(
            item["baseline_score"]["quality"]
            for item in items
        )

        opus_category = mean(
            item["opus_score"]["quality"]
            for item in items
        )

        categories[category] = {
            "baseline": baseline_category,
            "opus": opus_category,
            "absolute_gain": (
                opus_category
                - baseline_category
            ),
        }

    dimension_deltas: Dict[
        str,
        float | None,
    ] = {}

    for dimension in QUALITY_DIMENSIONS:
        if not valid_pairs:
            dimension_deltas[
                dimension
            ] = None
            continue

        baseline_dimension = mean(
            item["baseline_score"][dimension]
            for item in valid_pairs
        )

        opus_dimension = mean(
            item["opus_score"][dimension]
            for item in valid_pairs
        )

        dimension_deltas[dimension] = (
            opus_dimension
            - baseline_dimension
        )

    baseline_latency = mean(
        item["baseline"]["latency_ms"]
        for item in observations
        if item["baseline"]["ok"]
    )

    opus_latency = mean(
        item["opus"]["latency_ms"]
        for item in observations
        if item["opus"]["ok"]
    )

    deltas = [
        item["quality_delta"]
        for item in valid_pairs
    ]

    uncertainty = confidence_interval(
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
        < -EPSILON
    )

    unsupported_regression = (
        categories.get(
            "unsupported_claim_control",
            {},
        ).get(
            "absolute_gain",
            0.0,
        )
        < -EPSILON
    )

    material_improvement = bool(
        execution_valid
        and absolute_gain
        >= SIGNIFICANT_ABSOLUTE_GAIN
        and relative_gain is not None
        and relative_gain
        >= SIGNIFICANT_RELATIVE_GAIN
        and wins > losses
        and not authority_regression
        and not unsupported_regression
    )

    output = {
        "schema":
            "opus.cognitive_benchmark.v3",
        "experiment": {
            "baseline": (
                "direct single-provider openai_text "
                "inference with cognitive orchestration "
                "disabled"
            ),
            "opus": (
                "Opus cognitive orchestration over the "
                "proven provider set"
            ),
            "baseline_provider":
                BASELINE_PROVIDER,
            "opus_provider_set":
                list(
                    PROVEN_OPUS_PROVIDERS
                ),
            "case_count":
                len(cases),
            "repetitions":
                args.repetitions,
            "observation_count":
                len(observations),
            "valid_pair_count":
                len(valid_pairs),
            "baseline_success_count":
                baseline_successes,
            "opus_success_count":
                opus_successes,
            "execution_valid":
                execution_valid,
        },
        "quality": {
            "baseline": (
                baseline_quality
                if valid_pairs
                else None
            ),
            "opus": (
                opus_quality
                if valid_pairs
                else None
            ),
            "absolute_gain": (
                absolute_gain
                if valid_pairs
                else None
            ),
            "percentage_point_gain": (
                absolute_gain * 100.0
                if valid_pairs
                else None
            ),
            "relative_gain": relative_gain,
            "relative_gain_percent": (
                relative_gain * 100.0
                if relative_gain is not None
                else None
            ),
            "wins": wins,
            "ties": ties,
            "losses": losses,
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
                "all_pairs_must_execute":
                    True,
            },
        },
        "uncertainty":
            uncertainty,
        "latency": {
            "baseline_mean_ms": (
                baseline_latency
                if baseline_successes
                else None
            ),
            "opus_mean_ms": (
                opus_latency
                if opus_successes
                else None
            ),
            "multiplier": (
                opus_latency / baseline_latency
                if (
                    baseline_successes
                    and opus_successes
                    and baseline_latency > 0.0
                )
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

    if not execution_valid:
        return 3

    if (
        args.require_improvement
        and not material_improvement
    ):
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
