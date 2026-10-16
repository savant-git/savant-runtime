#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    provider_id: str
    total: float
    dimensions: Mapping[str, float]
    penalties: Mapping[str, float]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "provider_id": self.provider_id,
            "total": self.total,
            "dimensions": dict(
                self.dimensions
            ),
            "penalties": dict(
                self.penalties
            ),
        }


@dataclass(frozen=True)
class Adjudication:
    selected_candidate_id: str | None
    ranking: tuple[CandidateScore, ...]
    unresolved: tuple[str, ...]
    requires_refinement: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "selected_candidate_id":
                self.selected_candidate_id,
            "ranking": [
                score.as_dict()
                for score in self.ranking
            ],
            "unresolved": list(
                self.unresolved
            ),
            "requires_refinement":
                self.requires_refinement,
        }


DEFAULT_WEIGHTS = {
    "authority_compliance": 0.18,
    "constraint_satisfaction": 0.16,
    "evidence_support": 0.15,
    "factual_consistency": 0.15,
    "relationship_reasoning": 0.10,
    "terminology_consistency": 0.08,
    "completeness": 0.10,
    "validation_success": 0.08,
}


def _bounded(
    value: Any,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


def score_candidate(
    candidate: Mapping[str, Any],
    *,
    weights: Mapping[str, float] | None = None,
) -> CandidateScore:
    active_weights = dict(
        DEFAULT_WEIGHTS
    )

    if weights:
        for key, value in weights.items():
            if key not in active_weights:
                raise ValueError(
                    f"unsupported adjudication dimension: {key}"
                )

            active_weights[key] = max(
                0.0,
                float(value),
            )

    evaluations = candidate.get(
        "evaluation"
    )

    if not isinstance(
        evaluations,
        Mapping,
    ):
        evaluations = {}

    dimensions = {
        key: _bounded(
            evaluations.get(
                key,
                0.0,
            )
        )
        for key in active_weights
    }

    weight_total = sum(
        active_weights.values()
    )

    if weight_total <= 0.0:
        raise ValueError(
            "adjudication weights require positive total"
        )

    positive = sum(
        dimensions[key]
        * active_weights[key]
        for key in active_weights
    ) / weight_total

    unsupported_claim_rate = _bounded(
        evaluations.get(
            "unsupported_claim_rate",
            0.0,
        )
    )

    contradiction_rate = _bounded(
        evaluations.get(
            "contradiction_rate",
            0.0,
        )
    )

    authority_violation_rate = _bounded(
        evaluations.get(
            "authority_violation_rate",
            0.0,
        )
    )

    penalties = {
        "unsupported_claims":
            unsupported_claim_rate * 0.22,
        "contradictions":
            contradiction_rate * 0.22,
        "authority_violations":
            authority_violation_rate * 0.30,
    }

    total = max(
        0.0,
        min(
            1.0,
            positive
            - sum(
                penalties.values()
            ),
        ),
    )

    return CandidateScore(
        candidate_id=str(
            candidate.get(
                "candidate_id"
            )
            or ""
        ),
        provider_id=str(
            candidate.get(
                "provider_id"
            )
            or ""
        ),
        total=round(
            total,
            6,
        ),
        dimensions=dimensions,
        penalties=penalties,
    )


def adjudicate(
    candidates: Sequence[Mapping[str, Any]],
    *,
    unresolved: Iterable[str] | None = None,
    minimum_score: float = 0.65,
    minimum_margin: float = 0.04,
) -> Adjudication:
    scores: List[CandidateScore] = [
        score_candidate(candidate)
        for candidate in candidates
    ]

    scores.sort(
        key=lambda item: (
            -item.total,
            item.candidate_id,
            item.provider_id,
        )
    )

    unresolved_values = tuple(
        sorted(
            {
                str(value).strip()
                for value in unresolved or ()
                if str(value).strip()
            }
        )
    )

    if not scores:
        return Adjudication(
            selected_candidate_id=None,
            ranking=(),
            unresolved=unresolved_values,
            requires_refinement=True,
        )

    best = scores[0]

    margin = (
        best.total
        - scores[1].total
        if len(scores) > 1
        else best.total
    )

    requires_refinement = (
        best.total < float(
            minimum_score
        )
        or (
            len(scores) > 1
            and margin < float(
                minimum_margin
            )
        )
        or bool(
            unresolved_values
        )
    )

    return Adjudication(
        selected_candidate_id=(
            best.candidate_id
        ),
        ranking=tuple(scores),
        unresolved=unresolved_values,
        requires_refinement=requires_refinement,
    )
