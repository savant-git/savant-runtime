#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Sequence


class CognitiveStrategy(str, Enum):
    SINGLE = "single"
    FALLBACK = "fallback"
    PARALLEL = "parallel"
    SPECIALIST = "specialist"
    ADVERSARIAL = "adversarial"
    CONSENSUS = "consensus"
    REFINEMENT = "refinement"


@dataclass(frozen=True)
class StrategyDecision:
    strategy: CognitiveStrategy
    required_capabilities: tuple[str, ...]
    parallelism: int
    require_adjudication: bool
    require_counterpoint: bool
    allow_refinement: bool
    rationale: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "required_capabilities": list(self.required_capabilities),
            "parallelism": self.parallelism,
            "require_adjudication": self.require_adjudication,
            "require_counterpoint": self.require_counterpoint,
            "allow_refinement": self.allow_refinement,
            "rationale": list(self.rationale),
        }


def _normalized_capabilities(
    capabilities: Iterable[str] | None,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip().lower()
                for value in capabilities or ()
                if str(value).strip()
            }
        )
    )


def _bool(
    request: Mapping[str, Any],
    key: str,
    default: bool = False,
) -> bool:
    value = request.get(key, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    return bool(value)


def _complexity_score(
    request: Mapping[str, Any],
) -> int:
    score = 0

    message = str(
        request.get("message")
        or request.get("text")
        or request.get("prompt")
        or ""
    )

    context = str(
        request.get("context")
        or ""
    )

    if len(message) >= 1200:
        score += 1

    if len(message) >= 4000:
        score += 1

    if len(context) >= 4000:
        score += 1

    if len(context) >= 16000:
        score += 1

    if _bool(request, "authority_sensitive"):
        score += 2

    if _bool(request, "requires_verification"):
        score += 2

    if _bool(request, "requires_relationship_reasoning"):
        score += 1

    if _bool(request, "requires_historical_reconciliation"):
        score += 1

    if _bool(request, "high_value"):
        score += 1

    return score


def plan_strategy(
    request: Mapping[str, Any],
    *,
    available_provider_count: int,
    available_capabilities: Sequence[str] | None = None,
) -> StrategyDecision:
    capabilities = _normalized_capabilities(
        request.get("required_capabilities")
        or available_capabilities
        or ("text",)
    )

    requested = str(
        request.get("cognitive_strategy")
        or ""
    ).strip().lower()

    valid = {
        strategy.value: strategy
        for strategy in CognitiveStrategy
    }

    if requested:
        if requested not in valid:
            raise ValueError(
                f"unsupported cognitive strategy: {requested}"
            )

        strategy = valid[requested]

        return StrategyDecision(
            strategy=strategy,
            required_capabilities=capabilities,
            parallelism=max(
                1,
                min(
                    int(
                        request.get("parallelism")
                        or available_provider_count
                        or 1
                    ),
                    max(1, available_provider_count),
                ),
            ),
            require_adjudication=(
                strategy
                in {
                    CognitiveStrategy.CONSENSUS,
                    CognitiveStrategy.ADVERSARIAL,
                    CognitiveStrategy.SPECIALIST,
                }
            ),
            require_counterpoint=(
                strategy == CognitiveStrategy.ADVERSARIAL
            ),
            allow_refinement=(
                strategy == CognitiveStrategy.REFINEMENT
                or _bool(request, "allow_refinement")
            ),
            rationale=("explicit_request",),
        )

    provider_count = max(
        0,
        int(available_provider_count),
    )

    complexity = _complexity_score(request)
    rationale: List[str] = []

    if provider_count <= 1:
        rationale.append("single_usable_provider")

        return StrategyDecision(
            strategy=CognitiveStrategy.SINGLE,
            required_capabilities=capabilities,
            parallelism=1,
            require_adjudication=False,
            require_counterpoint=False,
            allow_refinement=(
                complexity >= 4
                and _bool(
                    request,
                    "allow_refinement",
                    True,
                )
            ),
            rationale=tuple(rationale),
        )

    if _bool(request, "requires_verification"):
        rationale.append("verification_requested")
        strategy = CognitiveStrategy.ADVERSARIAL

    elif _bool(request, "requires_historical_reconciliation"):
        rationale.append("historical_reconciliation")
        strategy = CognitiveStrategy.CONSENSUS

    elif _bool(request, "requires_relationship_reasoning"):
        rationale.append("relationship_reasoning")
        strategy = CognitiveStrategy.SPECIALIST

    elif _bool(request, "authority_sensitive"):
        rationale.append("authority_sensitive")
        strategy = CognitiveStrategy.ADVERSARIAL

    elif complexity >= 5:
        rationale.append("high_complexity")
        strategy = CognitiveStrategy.CONSENSUS

    elif complexity >= 3:
        rationale.append("moderate_complexity")
        strategy = CognitiveStrategy.PARALLEL

    else:
        rationale.append("ordinary_request")
        strategy = CognitiveStrategy.SINGLE

    parallelism = 1

    if strategy in {
        CognitiveStrategy.PARALLEL,
        CognitiveStrategy.SPECIALIST,
        CognitiveStrategy.ADVERSARIAL,
        CognitiveStrategy.CONSENSUS,
    }:
        parallelism = min(
            provider_count,
            3,
        )

    return StrategyDecision(
        strategy=strategy,
        required_capabilities=capabilities,
        parallelism=max(1, parallelism),
        require_adjudication=(
            strategy
            in {
                CognitiveStrategy.SPECIALIST,
                CognitiveStrategy.ADVERSARIAL,
                CognitiveStrategy.CONSENSUS,
            }
        ),
        require_counterpoint=(
            strategy == CognitiveStrategy.ADVERSARIAL
        ),
        allow_refinement=(
            complexity >= 4
            and _bool(
                request,
                "allow_refinement",
                True,
            )
        ),
        rationale=tuple(rationale),
    )


def capability_compatible(
    provider_data: Mapping[str, Any],
    required_capabilities: Iterable[str],
) -> bool:
    required = set(
        _normalized_capabilities(
            required_capabilities
        )
    )

    if not required:
        return True

    offered = set(
        _normalized_capabilities(
            provider_data.get("capabilities")
            or ()
        )
    )

    return required.issubset(offered)


def eligible_providers(
    providers: Iterable[Mapping[str, Any]],
    required_capabilities: Iterable[str],
) -> List[Dict[str, Any]]:
    eligible: List[Dict[str, Any]] = []

    for provider_data in providers:
        if not provider_data:
            continue

        if provider_data.get("available") is False:
            continue

        if capability_compatible(
            provider_data,
            required_capabilities,
        ):
            eligible.append(
                dict(provider_data)
            )

    return eligible
