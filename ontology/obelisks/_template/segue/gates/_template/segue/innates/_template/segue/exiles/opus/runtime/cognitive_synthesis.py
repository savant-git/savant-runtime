#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

from cognitive_consensus import (
    ConsensusResult,
    semantic_consensus,
)


@dataclass(frozen=True)
class SynthesisResult:
    text: str
    source_candidate_id: str | None
    source_provider_id: str | None
    mode: str
    agreements: tuple[str, ...]
    disagreements: tuple[str, ...]
    unresolved: tuple[str, ...]
    requires_adjudication: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_candidate_id":
                self.source_candidate_id,
            "source_provider_id":
                self.source_provider_id,
            "mode": self.mode,
            "agreements": list(
                self.agreements
            ),
            "disagreements": list(
                self.disagreements
            ),
            "unresolved": list(
                self.unresolved
            ),
            "requires_adjudication":
                self.requires_adjudication,
        }


def _candidate_id(
    candidate: Mapping[str, Any],
) -> str:
    return str(
        candidate.get("candidate_id")
        or ""
    ).strip()


def _provider_id(
    candidate: Mapping[str, Any],
) -> str:
    return str(
        candidate.get("provider_id")
        or candidate.get("provider")
        or ""
    ).strip()


def _text(
    candidate: Mapping[str, Any],
) -> str:
    return str(
        candidate.get("text")
        or ""
    ).strip()


def _candidate_quality(
    candidate: Mapping[str, Any],
) -> tuple:
    evaluation = candidate.get(
        "evaluation"
    )

    if not isinstance(evaluation, Mapping):
        evaluation = {}

    dimensions = (
        "authority_compliance",
        "constraint_satisfaction",
        "evidence_support",
        "factual_consistency",
        "relationship_reasoning",
        "terminology_consistency",
        "completeness",
        "validation_success",
    )

    scores: List[float] = []

    for dimension in dimensions:
        try:
            score = float(
                evaluation.get(
                    dimension,
                    0.0,
                )
            )
        except (TypeError, ValueError):
            score = 0.0

        scores.append(
            max(
                0.0,
                min(1.0, score),
            )
        )

    average = (
        sum(scores) / len(scores)
        if scores
        else 0.0
    )

    unsupported = evaluation.get(
        "unsupported_claim_rate",
        0.0,
    )

    contradictions = evaluation.get(
        "contradiction_rate",
        0.0,
    )

    try:
        unsupported_value = float(
            unsupported
        )
    except (TypeError, ValueError):
        unsupported_value = 0.0

    try:
        contradiction_value = float(
            contradictions
        )
    except (TypeError, ValueError):
        contradiction_value = 0.0

    adjusted = (
        average
        - max(
            0.0,
            unsupported_value,
        ) * 0.20
        - max(
            0.0,
            contradiction_value,
        ) * 0.20
    )

    return (
        adjusted,
        len(_text(candidate)),
        _candidate_id(candidate),
    )


def synthesize(
    candidates: Sequence[
        Mapping[str, Any]
    ],
    *,
    adjudicated_candidate_id: str | None = None,
) -> SynthesisResult:
    usable = [
        dict(candidate)
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and _text(candidate)
    ]

    if not usable:
        raise ValueError(
            "synthesis requires at least one candidate"
        )

    consensus = semantic_consensus(
        usable
    )

    if adjudicated_candidate_id:
        for candidate in usable:
            if (
                _candidate_id(candidate)
                == adjudicated_candidate_id
            ):
                return SynthesisResult(
                    text=_text(candidate),
                    source_candidate_id=
                        _candidate_id(
                            candidate
                        )
                        or None,
                    source_provider_id=
                        _provider_id(
                            candidate
                        )
                        or None,
                    mode="adjudicated",
                    agreements=
                        consensus.agreements,
                    disagreements=
                        consensus.disagreements,
                    unresolved=(),
                    requires_adjudication=False,
                )

    if len(usable) == 1:
        candidate = usable[0]

        return SynthesisResult(
            text=_text(candidate),
            source_candidate_id=(
                _candidate_id(candidate)
                or None
            ),
            source_provider_id=(
                _provider_id(candidate)
                or None
            ),
            mode="single",
            agreements=
                consensus.agreements,
            disagreements=
                consensus.disagreements,
            unresolved=(),
            requires_adjudication=False,
        )

    ranked = sorted(
        usable,
        key=_candidate_quality,
        reverse=True,
    )

    selected = ranked[0]

    unresolved = (
        consensus.disagreements
        if consensus.requires_adjudication
        else ()
    )

    return SynthesisResult(
        text=_text(selected),
        source_candidate_id=(
            _candidate_id(selected)
            or None
        ),
        source_provider_id=(
            _provider_id(selected)
            or None
        ),
        mode=(
            "best_supported_candidate"
            if not unresolved
            else "provisional_candidate"
        ),
        agreements=consensus.agreements,
        disagreements=
            consensus.disagreements,
        unresolved=tuple(unresolved),
        requires_adjudication=bool(
            unresolved
        ),
    )
