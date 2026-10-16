#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


def _bounded(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True)
class MarginalValueDecision:
    continue_execution: bool
    expected_information_gain: float
    expected_quality_gain: float
    normalized_cost: float
    normalized_latency: float
    utility: float
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "continue_execution":
                self.continue_execution,
            "expected_information_gain":
                self.expected_information_gain,
            "expected_quality_gain":
                self.expected_quality_gain,
            "normalized_cost":
                self.normalized_cost,
            "normalized_latency":
                self.normalized_latency,
            "utility":
                self.utility,
            "reason":
                self.reason,
        }


def marginal_value(
    *,
    current_confidence: float,
    provider_diversity: float,
    unresolved_fraction: float,
    expected_cost: float = 0.0,
    expected_latency: float = 0.0,
    task_value: float = 0.5,
    minimum_utility: float = 0.08,
) -> MarginalValueDecision:
    confidence = _bounded(
        current_confidence
    )
    diversity = _bounded(
        provider_diversity
    )
    unresolved = _bounded(
        unresolved_fraction
    )
    cost = _bounded(
        expected_cost
    )
    latency = _bounded(
        expected_latency
    )
    value = _bounded(
        task_value
    )

    information_gain = _bounded(
        (
            (1.0 - confidence) * 0.45
            + diversity * 0.25
            + unresolved * 0.30
        )
    )

    quality_gain = _bounded(
        information_gain
        * (
            0.55
            + value * 0.45
        )
    )

    burden = (
        cost * 0.55
        + latency * 0.45
    )

    utility = (
        quality_gain
        - burden
    )

    if unresolved >= 0.50:
        reason = "substantial_unresolved_evidence"
    elif confidence < 0.55:
        reason = "insufficient_current_confidence"
    elif diversity >= 0.60:
        reason = "independent_provider_information_available"
    elif burden >= quality_gain:
        reason = "expected_burden_exceeds_gain"
    else:
        reason = "marginal_quality_assessment"

    return MarginalValueDecision(
        continue_execution=(
            utility
            >= float(
                minimum_utility
            )
        ),
        expected_information_gain=round(
            information_gain,
            6,
        ),
        expected_quality_gain=round(
            quality_gain,
            6,
        ),
        normalized_cost=round(
            cost,
            6,
        ),
        normalized_latency=round(
            latency,
            6,
        ),
        utility=round(
            utility,
            6,
        ),
        reason=reason,
    )
