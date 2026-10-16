#!/usr/bin/env python3

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence

from cognitive_consensus import semantic_consensus
from cognitive_evidence import candidate, evidence_bundle
from cognitive_lineage import CognitiveLineage
from cognitive_strategy import (
    CognitiveStrategy,
    eligible_providers,
    plan_strategy,
)


ProviderExecutor = Callable[
    [Mapping[str, Any], Mapping[str, Any]],
    Mapping[str, Any],
]


@dataclass(frozen=True)
class ExecutionFailure:
    provider_id: str
    role: str
    error_type: str
    error: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":
                self.provider_id,
            "role":
                self.role,
            "error_type":
                self.error_type,
            "error":
                self.error,
        }


def _provider_id(
    provider_data: Mapping[str, Any],
) -> str:
    return str(
        provider_data.get("id")
        or provider_data.get(
            "provider_id"
        )
        or ""
    ).strip()


def _provider_model(
    provider_data: Mapping[str, Any],
) -> str | None:
    value = provider_data.get(
        "model"
    )

    if value is None:
        return None

    value = str(
        value
    ).strip()

    return value or None


def _provider_priority(
    provider_data: Mapping[str, Any],
) -> tuple:
    priority = provider_data.get(
        "priority",
        1000,
    )

    try:
        priority_value = int(
            priority
        )
    except (
        TypeError,
        ValueError,
    ):
        priority_value = 1000

    return (
        priority_value,
        _provider_id(
            provider_data
        ),
    )


def _default_executor(
    request: Mapping[str, Any],
    provider_data: Mapping[str, Any],
) -> Mapping[str, Any]:
    provider_id = _provider_id(
        provider_data
    )

    if not provider_id:
        raise RuntimeError(
            "provider missing id"
        )

    module_name = str(
        provider_data.get(
            "module"
        )
        or provider_id
    ).strip()

    if not module_name.startswith(
        "providers."
    ):
        module_name = (
            f"providers.{module_name}"
        )

    module = importlib.import_module(
        module_name
    )

    infer = getattr(
        module,
        "infer",
        None,
    )

    if not callable(infer):
        raise RuntimeError(
            f"{provider_id} has no infer()"
        )

    result = infer(
        dict(request),
        dict(provider_data),
    )

    if not isinstance(
        result,
        Mapping,
    ):
        raise RuntimeError(
            f"{provider_id} returned invalid result"
        )

    return result


def _role_request(
    request: Mapping[str, Any],
    *,
    role: str,
    prior_candidates: Sequence[
        Mapping[str, Any]
    ] | None = None,
) -> Dict[str, Any]:
    output = dict(
        request
    )

    output[
        "cognitive_role"
    ] = role

    if role == "critic":
        output[
            "cognitive_instruction"
        ] = (
            "Independently challenge the proposed reasoning. "
            "Identify contradictions, unsupported assumptions, "
            "missing constraints, counterexamples, and authority "
            "conflicts. Preserve uncertainty."
        )

    elif role == "adjudicator":
        output[
            "cognitive_instruction"
        ] = (
            "Compare the candidate answers. Resolve only disagreements "
            "that the supplied evidence supports. Preserve unresolved "
            "disagreement explicitly. Prefer authority compliance, "
            "factual support, constraint satisfaction, and completeness."
        )

    elif role == "specialist":
        output[
            "cognitive_instruction"
        ] = (
            "Solve the request independently with emphasis on the "
            "capabilities assigned to this provider. Do not imitate "
            "another candidate."
        )

    else:
        output[
            "cognitive_instruction"
        ] = (
            "Solve the request independently. Preserve uncertainty and "
            "do not invent unsupported facts."
        )

    if prior_candidates:
        output[
            "cognitive_candidates"
        ] = [
            {
                "provider_id":
                    value.get(
                        "provider_id"
                    ),
                "role":
                    value.get(
                        "role"
                    ),
                "text":
                    value.get(
                        "text"
                    ),
            }
            for value
            in prior_candidates
        ]

    return output


def _execute_one(
    request: Mapping[str, Any],
    provider_data: Mapping[str, Any],
    *,
    role: str,
    lineage: CognitiveLineage,
    executor: ProviderExecutor,
) -> tuple[
    Dict[str, Any] | None,
    ExecutionFailure | None,
]:
    provider_id = _provider_id(
        provider_data
    )

    model = _provider_model(
        provider_data
    )

    lineage.selected_provider(
        provider_id,
        model=model,
        strategy=str(
            request.get(
                "cognitive_strategy"
            )
            or "unspecified"
        ),
        role=role,
    )

    started = time.perf_counter()

    try:
        raw = executor(
            request,
            provider_data,
        )

        elapsed_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        text = str(
            raw.get("text")
            or ""
        ).strip()

        if not text:
            raise RuntimeError(
                "provider returned no text"
            )

        result = {
            "provider_id":
                provider_id,
            "model":
                raw.get(
                    "model"
                )
                or model,
            "role":
                role,
            "text":
                text,
            "latency_ms":
                round(
                    elapsed_ms,
                    3,
                ),
            "raw_metadata": {
                key: value
                for key, value
                in raw.items()
                if key not in {
                    "text",
                    "audio",
                    "authorization",
                    "api_key",
                    "token",
                    "secret",
                }
            },
        }

        lineage.provider_result(
            provider_id,
            model=result[
                "model"
            ],
            ok=True,
            latency_ms=result[
                "latency_ms"
            ],
            role=role,
        )

        return (
            result,
            None,
        )

    except Exception as exc:
        elapsed_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        lineage.provider_result(
            provider_id,
            model=model,
            ok=False,
            latency_ms=round(
                elapsed_ms,
                3,
            ),
            role=role,
            error_type=type(
                exc
            ).__name__,
        )

        return (
            None,
            ExecutionFailure(
                provider_id=provider_id,
                role=role,
                error_type=type(
                    exc
                ).__name__,
                error=str(
                    exc
                ),
            ),
        )


def execute_cognitive_request(
    request: Mapping[str, Any],
    providers: Iterable[
        Mapping[str, Any]
    ],
    *,
    executor: ProviderExecutor | None = None,
) -> Dict[str, Any]:
    lineage = CognitiveLineage(
        request_id=str(
            request.get(
                "request_id"
            )
            or ""
        ).strip()
        or CognitiveLineage().request_id
    )

    provider_values = [
        dict(value)
        for value in providers
        if isinstance(
            value,
            Mapping,
        )
    ]

    required = request.get(
        "required_capabilities"
    ) or (
        "text",
    )

    eligible = eligible_providers(
        provider_values,
        required,
    )

    eligible.sort(
        key=_provider_priority
    )

    eligible_ids = {
        _provider_id(
            value
        )
        for value in eligible
    }

    for provider_data in provider_values:
        provider_id = _provider_id(
            provider_data
        )

        lineage.considered_provider(
            provider_id,
            model=_provider_model(
                provider_data
            ),
            eligible=(
                provider_id
                in eligible_ids
            ),
            reason=(
                "capability_compatible"
                if provider_id
                in eligible_ids
                else "capability_or_availability_mismatch"
            ),
            capabilities=provider_data.get(
                "capabilities"
            )
            or (),
        )

    if not eligible:
        return {
            "ok": False,
            "error":
                "no capability-compatible Opus provider available",
            "lineage":
                lineage.as_dict(),
        }

    decision = plan_strategy(
        request,
        available_provider_count=len(
            eligible
        ),
        available_capabilities=required,
    )

    lineage.record(
        "strategy.selected",
        decision.as_dict(),
    )

    active_executor = (
        executor
        or _default_executor
    )

    strategy = decision.strategy

    if strategy in {
        CognitiveStrategy.SINGLE,
        CognitiveStrategy.FALLBACK,
        CognitiveStrategy.REFINEMENT,
    }:
        selected = eligible
    else:
        selected = eligible[
            :decision.parallelism
        ]

    results: List[
        Dict[str, Any]
    ] = []

    failures: List[
        ExecutionFailure
    ] = []

    if strategy in {
        CognitiveStrategy.SINGLE,
        CognitiveStrategy.FALLBACK,
        CognitiveStrategy.REFINEMENT,
    }:
        for provider_data in selected:
            role_request = _role_request(
                request,
                role="solver",
            )

            role_request[
                "cognitive_strategy"
            ] = strategy.value

            result, failure = _execute_one(
                role_request,
                provider_data,
                role="solver",
                lineage=lineage,
                executor=active_executor,
            )

            if result:
                results.append(
                    result
                )
                break

            if failure:
                failures.append(
                    failure
                )

    else:
        for index, provider_data in enumerate(
            selected
        ):
            if (
                strategy
                == CognitiveStrategy.ADVERSARIAL
                and index == 1
            ):
                role = "critic"
            elif (
                strategy
                == CognitiveStrategy.SPECIALIST
            ):
                role = "specialist"
            else:
                role = "solver"

            role_request = _role_request(
                request,
                role=role,
                prior_candidates=results,
            )

            role_request[
                "cognitive_strategy"
            ] = strategy.value

            result, failure = _execute_one(
                role_request,
                provider_data,
                role=role,
                lineage=lineage,
                executor=active_executor,
            )

            if result:
                results.append(
                    result
                )

            if failure:
                failures.append(
                    failure
                )

    if not results:
        return {
            "ok": False,
            "error":
                "all Opus cognitive provider executions failed",
            "strategy":
                decision.as_dict(),
            "failures": [
                failure.as_dict()
                for failure
                in failures
            ],
            "lineage":
                lineage.as_dict(),
        }

    consensus = semantic_consensus(
        results
    )

    lineage.record(
        "consensus.measured",
        consensus.as_dict(),
    )

    evidence_candidates = tuple(
        candidate(
            provider_id=value[
                "provider_id"
            ],
            model=value.get(
                "model"
            ),
            role=value.get(
                "role"
            )
            or "solver",
            text=value[
                "text"
            ],
            latency_ms=value.get(
                "latency_ms"
            ),
            metadata=value.get(
                "raw_metadata"
            )
            or {},
        )
        for value in results
    )

    evidence = evidence_bundle(
        request_id=lineage.request_id,
        strategy=strategy.value,
        candidates=evidence_candidates,
        agreements=consensus.agreements,
        disagreements=consensus.disagreements,
        unresolved=(
            consensus.disagreements
            if consensus.requires_adjudication
            else ()
        ),
    )

    if len(results) == 1:
        final = results[0]
        synthesis = "single_candidate"

    elif (
        consensus.agreements
        and not consensus.requires_adjudication
    ):
        final = max(
            results,
            key=lambda value: len(
                value.get(
                    "text"
                )
                or ""
            ),
        )
        synthesis = "converged_candidate"

    else:
        final = results[0]
        synthesis = (
            "adjudication_required"
        )

    lineage.record(
        "result.selected",
        {
            "provider":
                final.get(
                    "provider_id"
                ),
            "model":
                final.get(
                    "model"
                ),
            "synthesis":
                synthesis,
            "adjudication_required":
                consensus.requires_adjudication,
        },
    )

    return {
        "ok": True,
        "text": final[
            "text"
        ],
        "provider": final[
            "provider_id"
        ],
        "model": final.get(
            "model"
        ),
        "strategy":
            decision.as_dict(),
        "synthesis":
            synthesis,
        "candidates":
            results,
        "consensus":
            consensus.as_dict(),
        "evidence":
            evidence.as_dict(),
        "failures": [
            failure.as_dict()
            for failure
            in failures
        ],
        "lineage":
            lineage.as_dict(),
    }
