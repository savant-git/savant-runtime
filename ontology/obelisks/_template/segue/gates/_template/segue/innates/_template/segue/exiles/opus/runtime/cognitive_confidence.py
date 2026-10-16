#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping


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
class ConfidenceSignals:
    provider_agreement: float = 0.0
    validation_success: float = 0.0
    evidence_coverage: float = 0.0
    contradiction_resolution: float = 0.0
    authority_alignment: float = 0.0
    evaluator_agreement: float = 0.0
    completeness: float = 0.0
    capability_fit: float = 0.0
    fallback_penalty: float = 0.0
    unresolved_penalty: float = 0.0

    def normalized(self) -> "ConfidenceSignals":
        return ConfidenceSignals(
            provider_agreement=_bounded(
                self.provider_agreement
            ),
            validation_success=_bounded(
                self.validation_success
            ),
            evidence_coverage=_bounded(
                self.evidence_coverage
            ),
            contradiction_resolution=_bounded(
                self.contradiction_resolution
            ),
            authority_alignment=_bounded(
                self.authority_alignment
            ),
            evaluator_agreement=_bounded(
                self.evaluator_agreement
            ),
            completeness=_bounded(
                self.completeness
            ),
            capability_fit=_bounded(
                self.capability_fit
            ),
            fallback_penalty=_bounded(
                self.fallback_penalty
            ),
            unresolved_penalty=_bounded(
                self.unresolved_penalty
            ),
        )


@dataclass(frozen=True)
class ConfidenceResult:
    score: float
    level: str
    signals: ConfidenceSignals
    weights: Mapping[str, float]
    penalties: Mapping[str, float]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "signals": {
                "provider_agreement":
                    self.signals.provider_agreement,
                "validation_success":
                    self.signals.validation_success,
                "evidence_coverage":
                    self.signals.evidence_coverage,
                "contradiction_resolution":
                    self.signals.contradiction_resolution,
                "authority_alignment":
                    self.signals.authority_alignment,
                "evaluator_agreement":
                    self.signals.evaluator_agreement,
                "completeness":
                    self.signals.completeness,
                "capability_fit":
                    self.signals.capability_fit,
                "fallback_penalty":
                    self.signals.fallback_penalty,
                "unresolved_penalty":
                    self.signals.unresolved_penalty,
            },
            "weights": dict(self.weights),
            "penalties": dict(
                self.penalties
            ),
        }


DEFAULT_WEIGHTS = {
    "provider_agreement": 0.12,
    "validation_success": 0.18,
    "evidence_coverage": 0.14,
    "contradiction_resolution": 0.10,
    "authority_alignment": 0.16,
    "evaluator_agreement": 0.10,
    "completeness": 0.10,
    "capability_fit": 0.10,
}


def confidence(
    signals: ConfidenceSignals,
    *,
    weights: Mapping[str, float] | None = None,
) -> ConfidenceResult:
    normalized = signals.normalized()

    active_weights = dict(
        DEFAULT_WEIGHTS
    )

    if weights:
        for key, value in weights.items():
            if key not in active_weights:
                raise ValueError(
                    f"unsupported confidence weight: {key}"
                )

            active_weights[key] = max(
                0.0,
                float(value),
            )

    total_weight = sum(
        active_weights.values()
    )

    if total_weight <= 0.0:
        raise ValueError(
            "confidence weights must have positive total"
        )

    positive = {
        "provider_agreement":
            normalized.provider_agreement,
        "validation_success":
            normalized.validation_success,
        "evidence_coverage":
            normalized.evidence_coverage,
        "contradiction_resolution":
            normalized.contradiction_resolution,
        "authority_alignment":
            normalized.authority_alignment,
        "evaluator_agreement":
            normalized.evaluator_agreement,
        "completeness":
            normalized.completeness,
        "capability_fit":
            normalized.capability_fit,
    }

    weighted = sum(
        positive[key]
        * active_weights[key]
        for key in active_weights
    ) / total_weight

    penalties = {
        "fallback": (
            normalized.fallback_penalty
            * 0.08
        ),
        "unresolved": (
            normalized.unresolved_penalty
            * 0.18
        ),
    }

    score = _bounded(
        weighted
        - sum(
            penalties.values()
        )
    )

    if score >= 0.90:
        level = "very_high"
    elif score >= 0.75:
        level = "high"
    elif score >= 0.55:
        level = "moderate"
    elif score >= 0.35:
        level = "low"
    else:
        level = "very_low"

    return ConfidenceResult(
        score=round(
            score,
            6,
        ),
        level=level,
        signals=normalized,
        weights=active_weights,
        penalties=penalties,
    )
