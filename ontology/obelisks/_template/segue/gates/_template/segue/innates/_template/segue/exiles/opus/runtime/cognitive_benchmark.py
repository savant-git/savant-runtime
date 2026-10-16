#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence


METRICS = (
    "authority_compliance",
    "constraint_satisfaction",
    "factual_compliance",
    "contradiction_control",
    "relationship_reasoning",
    "terminology_reconciliation",
    "completeness",
    "deterministic_structure",
    "validation_success",
    "unsupported_claim_control",
)


def _bounded(
    value: Any,
) -> float:
    try:
        number = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


def _hash(
    value: Any,
) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(
        raw
    ).hexdigest()


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    request: Mapping[str, Any]
    rubric: Mapping[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "case_id":
                self.case_id,
            "request":
                dict(
                    self.request
                ),
            "rubric":
                dict(
                    self.rubric
                ),
        }


@dataclass(frozen=True)
class BenchmarkScore:
    case_id: str
    mode: str
    metrics: Mapping[str, float]
    aggregate: float
    latency_ms: float
    provider_count: int
    output_hash: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "case_id":
                self.case_id,
            "mode":
                self.mode,
            "metrics":
                dict(
                    self.metrics
                ),
            "aggregate":
                self.aggregate,
            "latency_ms":
                self.latency_ms,
            "provider_count":
                self.provider_count,
            "output_hash":
                self.output_hash,
        }


def score(
    *,
    case_id: str,
    mode: str,
    evaluation: Mapping[str, Any],
    output: Mapping[str, Any],
    latency_ms: float,
) -> BenchmarkScore:
    metrics = {
        metric: _bounded(
            evaluation.get(
                metric,
                0.0,
            )
        )
        for metric in METRICS
    }

    aggregate = (
        sum(
            metrics.values()
        )
        / len(
            metrics
        )
    )

    candidates = output.get(
        "candidates"
    )

    if isinstance(
        candidates,
        Sequence,
    ) and not isinstance(
        candidates,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        provider_count = len(
            {
                str(
                    value.get(
                        "provider_id"
                    )
                    or value.get(
                        "provider"
                    )
                    or ""
                )
                for value in candidates
                if isinstance(
                    value,
                    Mapping,
                )
            }
            - {""}
        )
    else:
        provider_count = (
            1
            if output.get(
                "provider"
            )
            else 0
        )

    return BenchmarkScore(
        case_id=case_id,
        mode=mode,
        metrics=metrics,
        aggregate=round(
            aggregate,
            6,
        ),
        latency_ms=round(
            float(
                latency_ms
            ),
            3,
        ),
        provider_count=provider_count,
        output_hash=_hash(
            {
                "text":
                    output.get(
                        "text"
                    ),
                "provider":
                    output.get(
                        "provider"
                    ),
                "model":
                    output.get(
                        "model"
                    ),
            }
        ),
    )


def compare(
    baseline: Sequence[
        BenchmarkScore
    ],
    opus: Sequence[
        BenchmarkScore
    ],
) -> Dict[str, Any]:
    baseline_map = {
        value.case_id: value
        for value in baseline
    }

    opus_map = {
        value.case_id: value
        for value in opus
    }

    shared = sorted(
        set(
            baseline_map
        )
        & set(
            opus_map
        )
    )

    if not shared:
        raise ValueError(
            "benchmark comparison has no shared cases"
        )

    metric_deltas: Dict[
        str,
        List[float]
    ] = {
        metric: []
        for metric in METRICS
    }

    aggregate_deltas: List[
        float
    ] = []

    latency_deltas: List[
        float
    ] = []

    cases: List[
        Dict[str, Any]
    ] = []

    for case_id in shared:
        base = baseline_map[
            case_id
        ]
        enhanced = opus_map[
            case_id
        ]

        deltas = {
            metric: round(
                enhanced.metrics[
                    metric
                ]
                - base.metrics[
                    metric
                ],
                6,
            )
            for metric in METRICS
        }

        for metric, delta in deltas.items():
            metric_deltas[
                metric
            ].append(
                delta
            )

        aggregate_delta = (
            enhanced.aggregate
            - base.aggregate
        )

        latency_delta = (
            enhanced.latency_ms
            - base.latency_ms
        )

        aggregate_deltas.append(
            aggregate_delta
        )

        latency_deltas.append(
            latency_delta
        )

        cases.append(
            {
                "case_id":
                    case_id,
                "baseline":
                    base.as_dict(),
                "opus":
                    enhanced.as_dict(),
                "metric_deltas":
                    deltas,
                "aggregate_delta":
                    round(
                        aggregate_delta,
                        6,
                    ),
                "latency_delta_ms":
                    round(
                        latency_delta,
                        3,
                    ),
            }
        )

    metric_means = {
        metric: round(
            statistics.fmean(
                values
            ),
            6,
        )
        for metric, values
        in metric_deltas.items()
    }

    aggregate_mean = (
        statistics.fmean(
            aggregate_deltas
        )
    )

    improved_cases = sum(
        delta > 0
        for delta in aggregate_deltas
    )

    regressed_cases = sum(
        delta < 0
        for delta in aggregate_deltas
    )

    tied_cases = (
        len(shared)
        - improved_cases
        - regressed_cases
    )

    result = {
        "cases":
            cases,
        "case_count":
            len(shared),
        "metric_mean_deltas":
            metric_means,
        "aggregate_mean_delta":
            round(
                aggregate_mean,
                6,
            ),
        "mean_latency_delta_ms":
            round(
                statistics.fmean(
                    latency_deltas
                ),
                3,
            ),
        "improved_cases":
            improved_cases,
        "regressed_cases":
            regressed_cases,
        "tied_cases":
            tied_cases,
        "improvement_proven":
            (
                aggregate_mean > 0
                and improved_cases
                > regressed_cases
                and all(
                    value >= 0
                    for value
                    in metric_means.values()
                )
            ),
    }

    result[
        "comparison_hash"
    ] = _hash(
        result
    )

    return result


def run_case(
    case: BenchmarkCase,
    *,
    mode: str,
    executor: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    evaluator: Callable[
        [
            BenchmarkCase,
            Mapping[str, Any],
        ],
        Mapping[str, Any],
    ],
) -> BenchmarkScore:
    started = time.perf_counter()

    output = executor(
        dict(
            case.request
        )
    )

    latency_ms = (
        time.perf_counter()
        - started
    ) * 1000.0

    if not isinstance(
        output,
        Mapping,
    ):
        raise RuntimeError(
            "benchmark executor returned invalid output"
        )

    evaluation = evaluator(
        case,
        output,
    )

    if not isinstance(
        evaluation,
        Mapping,
    ):
        raise RuntimeError(
            "benchmark evaluator returned invalid evaluation"
        )

    return score(
        case_id=case.case_id,
        mode=mode,
        evaluation=evaluation,
        output=output,
        latency_ms=latency_ms,
    )


def run_benchmark(
    cases: Iterable[
        BenchmarkCase
    ],
    *,
    baseline_executor: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    opus_executor: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    evaluator: Callable[
        [
            BenchmarkCase,
            Mapping[str, Any],
        ],
        Mapping[str, Any],
    ],
) -> Dict[str, Any]:
    case_values = list(
        cases
    )

    if not case_values:
        raise ValueError(
            "benchmark requires at least one case"
        )

    baseline_scores = [
        run_case(
            case,
            mode="baseline",
            executor=baseline_executor,
            evaluator=evaluator,
        )
        for case in case_values
    ]

    opus_scores = [
        run_case(
            case,
            mode="opus",
            executor=opus_executor,
            evaluator=evaluator,
        )
        for case in case_values
    ]

    comparison = compare(
        baseline_scores,
        opus_scores,
    )

    return {
        "schema":
            "opus.cognitive_benchmark.v1",
        "baseline": [
            value.as_dict()
            for value
            in baseline_scores
        ],
        "opus": [
            value.as_dict()
            for value
            in opus_scores
        ],
        "comparison":
            comparison,
    }
