from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Sequence

from cognitive_benchmark_suite import cases


ExecutionFunction = Callable[
    [Dict[str, Any]],
    Dict[str, Any],
]


METRICS = (
    "authority_compliance",
    "constraint_satisfaction",
    "contradiction_control",
    "relationship_reasoning",
    "terminology_reconciliation",
    "completeness",
    "validation_success",
    "unsupported_claim_control",
)


@dataclass(frozen=True)
class RunObservation:
    case_id: str
    mode: str
    ok: bool
    text: str
    latency_ms: float
    provider: str | None
    model: str | None
    lineage: Mapping[str, Any]
    error: str | None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "mode": self.mode,
            "ok": self.ok,
            "text": self.text,
            "latency_ms": self.latency_ms,
            "provider": self.provider,
            "model": self.model,
            "lineage": dict(
                self.lineage
            ),
            "error": self.error,
        }


def _request(
    benchmark_case: Mapping[str, Any],
    *,
    cognitive: bool,
) -> Dict[str, Any]:
    return {
        "owner": "opus_benchmark",
        "text": benchmark_case["prompt"],
        "system": benchmark_case["system"],
        "required_capabilities": list(
            benchmark_case.get(
                "required_capabilities"
            )
            or ["text"]
        ),
        "authority_sensitive": bool(
            benchmark_case.get(
                "authority_sensitive"
            )
        ),
        "requires_verification": bool(
            benchmark_case.get(
                "requires_verification"
            )
        ),
        "requires_relationship_reasoning": bool(
            benchmark_case.get(
                "requires_relationship_reasoning"
            )
        ),
        "requires_historical_reconciliation": bool(
            benchmark_case.get(
                "requires_historical_reconciliation"
            )
        ),
        "cognitive_orchestration": cognitive,
        "benchmark_case_id":
            benchmark_case["case_id"],
    }


def _run(
    execute: ExecutionFunction,
    benchmark_case: Mapping[str, Any],
    *,
    mode: str,
    cognitive: bool,
) -> RunObservation:
    started = time.perf_counter()

    try:
        result = execute(
            _request(
                benchmark_case,
                cognitive=cognitive,
            )
        )

        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        lineage = result.get(
            "lineage"
        )

        if not isinstance(
            lineage,
            Mapping,
        ):
            lineage = {}

        return RunObservation(
            case_id=str(
                benchmark_case[
                    "case_id"
                ]
            ),
            mode=mode,
            ok=bool(
                result.get(
                    "ok",
                    True,
                )
            ),
            text=str(
                result.get(
                    "text"
                )
                or ""
            ).strip(),
            latency_ms=latency_ms,
            provider=(
                str(
                    result.get(
                        "provider"
                    )
                )
                if result.get(
                    "provider"
                )
                else None
            ),
            model=(
                str(
                    result.get(
                        "model"
                    )
                )
                if result.get(
                    "model"
                )
                else None
            ),
            lineage=dict(
                lineage
            ),
            error=None,
        )

    except Exception as exc:
        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        return RunObservation(
            case_id=str(
                benchmark_case[
                    "case_id"
                ]
            ),
            mode=mode,
            ok=False,
            text="",
            latency_ms=latency_ms,
            provider=None,
            model=None,
            lineage={},
            error=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def run_pair(
    execute: ExecutionFunction,
    benchmark_case: Mapping[str, Any],
) -> Dict[str, Any]:
    baseline = _run(
        execute,
        benchmark_case,
        mode="basic",
        cognitive=False,
    )

    opus = _run(
        execute,
        benchmark_case,
        mode="opus",
        cognitive=True,
    )

    return {
        "case_id":
            benchmark_case["case_id"],
        "category":
            benchmark_case["category"],
        "expected_constraints":
            list(
                benchmark_case.get(
                    "expected_constraints"
                )
                or ()
            ),
        "forbidden_claims":
            list(
                benchmark_case.get(
                    "forbidden_claims"
                )
                or ()
            ),
        "basic": baseline.as_dict(),
        "opus": opus.as_dict(),
    }


def run_suite(
    execute: ExecutionFunction,
) -> Dict[str, Any]:
    results = [
        run_pair(
            execute,
            benchmark_case,
        )
        for benchmark_case in cases()
    ]

    return {
        "schema":
            "opus.cognitive.benchmark.raw.v1",
        "metrics": list(
            METRICS
        ),
        "case_count":
            len(results),
        "results":
            results,
    }


def dumps(
    result: Mapping[str, Any],
) -> str:
    return json.dumps(
        result,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    )
