#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-adjudication/1.0.0"
)

OWNER = "exile:envoy"
VERIFICATION_OWNER = "exile:notary"


class TraitAdjudicationError(
    ValueError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def normalize_term(
    value: Any,
) -> str:
    return (
        str(
            value
            or ""
        )
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def normalize_score(
    value: Any,
) -> float:
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise TraitAdjudicationError(
            "score must be numeric"
        ) from exc

    if not (
        0.0
        <= result
        <= 1.0
    ):
        raise TraitAdjudicationError(
            "score must be between "
            "0 and 1"
        )

    return result


def normalize_measurements(
    values: Mapping[
        str,
        Any,
    ],
) -> tuple[
    tuple[
        str,
        float,
    ],
    ...,
]:
    if not isinstance(
        values,
        Mapping,
    ):
        raise TraitAdjudicationError(
            "measurements must be "
            "a mapping"
        )

    if not values:
        raise TraitAdjudicationError(
            "measurements must not "
            "be empty"
        )

    rows: list[
        tuple[
            str,
            float,
        ]
    ] = []

    for raw_name, raw_value in (
        values.items()
    ):
        name = normalize_term(
            raw_name
        )

        if not name:
            raise TraitAdjudicationError(
                "measurement name "
                "is required"
            )

        rows.append(
            (
                name,
                normalize_score(
                    raw_value
                ),
            )
        )

    rows.sort(
        key=lambda row: (
            row[0]
        )
    )

    if (
        len(
            rows
        )
        != len(
            {
                row[0]
                for row in rows
            }
        )
    ):
        raise TraitAdjudicationError(
            "duplicate measurement "
            "dimensions"
        )

    return tuple(
        rows
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AdjudicationCandidate:
    candidate_id: str
    trait_id: str
    measurements: tuple[
        tuple[
            str,
            float,
        ],
        ...,
    ]
    evidence_ids: tuple[str, ...]
    verified: bool
    evidence_admitted: bool
    lineage: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        candidate_id = str(
            self.candidate_id
            or ""
        ).strip()

        trait_id = normalize_term(
            self.trait_id
        )

        if not candidate_id:
            raise TraitAdjudicationError(
                "candidate_id is required"
            )

        if not trait_id:
            raise TraitAdjudicationError(
                "trait_id is required"
            )

        if not (
            self.verified
            and self.evidence_admitted
        ):
            raise TraitAdjudicationError(
                "candidate evidence must "
                "be verified and admitted "
                "before adjudication"
            )

        normalized_measurements = (
            normalize_measurements(
                dict(
                    self.measurements
                )
            )
        )

        evidence_ids = tuple(
            sorted(
                {
                    str(
                        value
                    ).strip()
                    for value
                    in self.evidence_ids
                    if str(
                        value
                    ).strip()
                }
            )
        )

        if not evidence_ids:
            raise TraitAdjudicationError(
                "candidate requires "
                "admitted evidence"
            )

        lineage = tuple(
            sorted(
                {
                    str(
                        value
                    ).strip()
                    for value
                    in self.lineage
                    if str(
                        value
                    ).strip()
                }
            )
        )

        object.__setattr__(
            self,
            "candidate_id",
            candidate_id,
        )

        object.__setattr__(
            self,
            "trait_id",
            trait_id,
        )

        object.__setattr__(
            self,
            "measurements",
            normalized_measurements,
        )

        object.__setattr__(
            self,
            "evidence_ids",
            evidence_ids,
        )

        object.__setattr__(
            self,
            "lineage",
            lineage,
        )

    def measurement_map(
        self,
    ) -> dict[str, float]:
        return dict(
            self.measurements
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "candidate_id": (
                self.candidate_id
            ),
            "trait_id": (
                self.trait_id
            ),
            "measurements": {
                name: value
                for name, value
                in self.measurements
            },
            "evidence_ids": list(
                self.evidence_ids
            ),
            "verified": True,
            "evidence_admitted": True,
            "lineage": list(
                self.lineage
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class AdjudicationPolicy:
    policy_id: str
    weights: tuple[
        tuple[
            str,
            float,
        ],
        ...,
    ]
    minimum_margin: float = 0.03
    minimum_dimensions: int = 1

    def __post_init__(
        self,
    ) -> None:
        policy_id = normalize_term(
            self.policy_id
        )

        if not policy_id:
            raise TraitAdjudicationError(
                "policy_id is required"
            )

        normalized_weights = (
            normalize_measurements(
                dict(
                    self.weights
                )
            )
        )

        try:
            minimum_margin = float(
                self.minimum_margin
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise TraitAdjudicationError(
                "minimum_margin must "
                "be numeric"
            ) from exc

        if minimum_margin < 0:
            raise TraitAdjudicationError(
                "minimum_margin must "
                "not be negative"
            )

        minimum_dimensions = int(
            self.minimum_dimensions
        )

        if minimum_dimensions < 1:
            raise TraitAdjudicationError(
                "minimum_dimensions "
                "must be positive"
            )

        object.__setattr__(
            self,
            "policy_id",
            policy_id,
        )

        object.__setattr__(
            self,
            "weights",
            normalized_weights,
        )

        object.__setattr__(
            self,
            "minimum_margin",
            minimum_margin,
        )

        object.__setattr__(
            self,
            "minimum_dimensions",
            minimum_dimensions,
        )

    def weight_map(
        self,
    ) -> dict[str, float]:
        return dict(
            self.weights
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "policy_id": (
                self.policy_id
            ),
            "weights": {
                name: value
                for name, value
                in self.weights
            },
            "minimum_margin": (
                self.minimum_margin
            ),
            "minimum_dimensions": (
                self.minimum_dimensions
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class CandidateScore:
    candidate_id: str
    trait_id: str
    score: float
    dimensions: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "candidate_id": (
                self.candidate_id
            ),
            "trait_id": (
                self.trait_id
            ),
            "score": self.score,
            "dimensions": list(
                self.dimensions
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class AdjudicationDecision:
    trait_id: str
    policy_id: str
    previous_champion_id: str | None
    winner_candidate_id: str | None
    decision: str
    margin: float
    scores: tuple[
        CandidateScore,
        ...,
    ]
    evidence_ids: tuple[str, ...]
    lineage: tuple[str, ...]

    @property
    def decision_id(
        self,
    ) -> str:
        return (
            "trait-decision:"
            + digest(
                self.projection(
                    include_digest=False
                )
            )[:32]
        )

    def projection(
        self,
        *,
        include_digest: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "decision_id": (
                self.decision_id
                if include_digest
                else None
            ),
            "trait_id": (
                self.trait_id
            ),
            "policy_id": (
                self.policy_id
            ),
            "previous_champion_id": (
                self.previous_champion_id
            ),
            "winner_candidate_id": (
                self.winner_candidate_id
            ),
            "decision": (
                self.decision
            ),
            "margin": (
                self.margin
            ),
            "scores": [
                score.projection()
                for score
                in self.scores
            ],
            "evidence_ids": list(
                self.evidence_ids
            ),
            "lineage": list(
                self.lineage
            ),
            "owner": OWNER,
            "verification_owner": (
                VERIFICATION_OWNER
            ),
            "baseline_mutation": False,
            "crown_mutation": False,
            "automatic_supersession": (
                False
            ),
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        if not include_digest:
            payload.pop(
                "decision_id",
                None,
            )

            return payload

        payload["digest"] = digest(
            {
                key: value
                for key, value
                in payload.items()
                if key != "digest"
            }
        )

        return payload


def score_candidate(
    candidate: AdjudicationCandidate,
    policy: AdjudicationPolicy,
) -> CandidateScore:
    measurements = (
        candidate.measurement_map()
    )

    weights = (
        policy.weight_map()
    )

    common = tuple(
        sorted(
            set(
                measurements
            ).intersection(
                weights
            )
        )
    )

    if (
        len(
            common
        )
        < policy.minimum_dimensions
    ):
        raise TraitAdjudicationError(
            "candidate lacks sufficient "
            "shared dimensions"
        )

    numerator = sum(
        measurements[
            dimension
        ]
        * weights[
            dimension
        ]
        for dimension in common
    )

    denominator = sum(
        weights[
            dimension
        ]
        for dimension in common
    )

    if denominator <= 0:
        raise TraitAdjudicationError(
            "policy weight denominator "
            "must be positive"
        )

    return CandidateScore(
        candidate_id=(
            candidate.candidate_id
        ),
        trait_id=(
            candidate.trait_id
        ),
        score=(
            numerator
            / denominator
        ),
        dimensions=common,
    )


def adjudicate(
    candidates: Sequence[
        AdjudicationCandidate
    ],
    policy: AdjudicationPolicy,
    *,
    previous_champion_id: (
        str
        | None
    ) = None,
) -> AdjudicationDecision:
    materialized = tuple(
        candidates
    )

    if len(
        materialized
    ) < 2:
        raise TraitAdjudicationError(
            "adjudication requires "
            "at least two candidates"
        )

    trait_ids = {
        candidate.trait_id
        for candidate
        in materialized
    }

    if len(
        trait_ids
    ) != 1:
        raise TraitAdjudicationError(
            "candidates span multiple traits"
        )

    candidate_ids = [
        candidate.candidate_id
        for candidate
        in materialized
    ]

    if (
        len(
            candidate_ids
        )
        != len(
            set(
                candidate_ids
            )
        )
    ):
        raise TraitAdjudicationError(
            "duplicate candidate identity"
        )

    scored = tuple(
        sorted(
            (
                score_candidate(
                    candidate,
                    policy,
                )
                for candidate
                in materialized
            ),
            key=lambda score: (
                -score.score,
                score.candidate_id,
            ),
        )
    )

    first = scored[0]
    second = scored[1]

    margin = (
        first.score
        - second.score
    )

    winner: str | None = None
    decision = "no_decision"

    if (
        margin
        >= policy.minimum_margin
    ):
        winner = (
            first.candidate_id
        )

        if (
            previous_champion_id
            is None
        ):
            decision = (
                "establish_champion"
            )

        elif (
            previous_champion_id
            == winner
        ):
            decision = (
                "retain_champion"
            )

        else:
            decision = (
                "challenge_wins"
            )

    evidence_ids = tuple(
        sorted(
            {
                evidence_id
                for candidate
                in materialized
                for evidence_id
                in candidate
                .evidence_ids
            }
        )
    )

    lineage = tuple(
        sorted(
            {
                lineage
                for candidate
                in materialized
                for lineage
                in candidate
                .lineage
            }
        )
    )

    return AdjudicationDecision(
        trait_id=next(
            iter(
                trait_ids
            )
        ),
        policy_id=(
            policy.policy_id
        ),
        previous_champion_id=(
            previous_champion_id
        ),
        winner_candidate_id=(
            winner
        ),
        decision=decision,
        margin=margin,
        scores=scored,
        evidence_ids=evidence_ids,
        lineage=lineage,
    )


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-adjudication-"
            "status/1.0.0"
        ),
        "owner": OWNER,
        "verification_owner": (
            VERIFICATION_OWNER
        ),
        "verified_evidence_required": (
            True
        ),
        "admitted_evidence_required": (
            True
        ),
        "deterministic_scoring": True,
        "explicit_no_decision": True,
        "minimum_margin_required": (
            True
        ),
        "tie_break_by_identity_only": (
            False
        ),
        "automatic_supersession": (
            False
        ),
        "immutable_decision_projection": (
            True
        ),
        "baseline_mutation": False,
        "crown_mutation": False,
        "persistent_history_local": (
            False
        ),
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def main() -> int:
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
