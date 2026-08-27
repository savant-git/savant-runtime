#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-evaluation/1.0.0"
)

OWNER = "exile:envoy"
EXECUTION_OWNER = "exile:opus"
VERIFICATION_OWNER = "exile:notary"


class TraitEvaluationError(
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


def normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                term
                for value in values
                if (
                    term
                    := normalize_term(
                        value
                    )
                )
            }
        )
    )


def normalize_score(
    value: Any,
) -> float:
    try:
        score = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise TraitEvaluationError(
            "evaluation score "
            "must be numeric"
        ) from exc

    if not (
        0.0
        <= score
        <= 1.0
    ):
        raise TraitEvaluationError(
            "evaluation score "
            "must be between 0 and 1"
        )

    return score


def normalize_scores(
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
        raise TraitEvaluationError(
            "scores must be a mapping"
        )

    if not values:
        raise TraitEvaluationError(
            "scores must not be empty"
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
            raise TraitEvaluationError(
                "score dimension "
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
        raise TraitEvaluationError(
            "score dimensions "
            "must be unique"
        )

    return tuple(
        rows
    )


@dataclass(
    frozen=True,
    slots=True,
)
class BlindEvaluation:
    packet_id: str
    blind_id: str
    evaluator_id: str
    scores: tuple[
        tuple[
            str,
            float,
        ],
        ...,
    ]
    target_traits: tuple[str, ...] = ()
    notes: str = ""
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        packet_id = str(
            self.packet_id
            or ""
        ).strip()

        blind_id = str(
            self.blind_id
            or ""
        ).strip()

        evaluator_id = (
            normalize_term(
                self.evaluator_id
            )
        )

        if not packet_id:
            raise TraitEvaluationError(
                "packet_id is required"
            )

        if not blind_id:
            raise TraitEvaluationError(
                "blind_id is required"
            )

        if not evaluator_id:
            raise TraitEvaluationError(
                "evaluator_id is required"
            )

        normalized_scores = (
            normalize_scores(
                dict(
                    self.scores
                )
            )
        )

        object.__setattr__(
            self,
            "packet_id",
            packet_id,
        )

        object.__setattr__(
            self,
            "blind_id",
            blind_id,
        )

        object.__setattr__(
            self,
            "evaluator_id",
            evaluator_id,
        )

        object.__setattr__(
            self,
            "scores",
            normalized_scores,
        )

        object.__setattr__(
            self,
            "target_traits",
            normalize_terms(
                self.target_traits
            ),
        )

        object.__setattr__(
            self,
            "notes",
            str(
                self.notes
                or ""
            ).strip(),
        )

        object.__setattr__(
            self,
            "evidence_refs",
            normalize_terms(
                self.evidence_refs
            ),
        )

    @property
    def evaluation_id(
        self,
    ) -> str:
        return (
            "blind-evaluation:"
            + digest(
                self.projection()
            )[:32]
        )

    def score_map(
        self,
    ) -> dict[str, float]:
        return dict(
            self.scores
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "packet_id": (
                self.packet_id
            ),
            "blind_id": (
                self.blind_id
            ),
            "evaluator_id": (
                self.evaluator_id
            ),
            "scores": {
                name: value
                for name, value
                in self.scores
            },
            "target_traits": list(
                self.target_traits
            ),
            "notes": self.notes,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "provider_identity_exposed": (
                False
            ),
            "owner": OWNER,
            "verification_owner": (
                VERIFICATION_OWNER
            ),
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class EvaluationAggregate:
    blind_id: str
    evaluations: tuple[
        BlindEvaluation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        blind_id = str(
            self.blind_id
            or ""
        ).strip()

        if not blind_id:
            raise TraitEvaluationError(
                "blind_id is required"
            )

        if not self.evaluations:
            raise TraitEvaluationError(
                "aggregate requires "
                "evaluations"
            )

        for evaluation in (
            self.evaluations
        ):
            if (
                evaluation.blind_id
                != blind_id
            ):
                raise TraitEvaluationError(
                    "aggregate contains "
                    "multiple blind identities"
                )

        ordered = tuple(
            sorted(
                self.evaluations,
                key=lambda evaluation: (
                    evaluation
                    .evaluation_id
                ),
            )
        )

        object.__setattr__(
            self,
            "blind_id",
            blind_id,
        )

        object.__setattr__(
            self,
            "evaluations",
            ordered,
        )

    @property
    def aggregate_id(
        self,
    ) -> str:
        return (
            "evaluation-aggregate:"
            + digest(
                {
                    "blind_id": (
                        self.blind_id
                    ),
                    "evaluation_ids": [
                        evaluation
                        .evaluation_id
                        for evaluation
                        in self.evaluations
                    ],
                }
            )[:32]
        )

    def dimensions(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    dimension
                    for evaluation
                    in self.evaluations
                    for dimension
                    in evaluation
                    .score_map()
                }
            )
        )

    def measurements(
        self,
    ) -> dict[
        str,
        dict[str, float],
    ]:
        result: dict[
            str,
            dict[str, float],
        ] = {}

        for dimension in (
            self.dimensions()
        ):
            values = [
                evaluation
                .score_map()[
                    dimension
                ]
                for evaluation
                in self.evaluations
                if dimension
                in evaluation
                .score_map()
            ]

            if not values:
                continue

            result[
                dimension
            ] = {
                "mean": (
                    statistics.fmean(
                        values
                    )
                ),
                "minimum": min(
                    values
                ),
                "maximum": max(
                    values
                ),
                "count": float(
                    len(
                        values
                    )
                ),
                "population_stdev": (
                    statistics.pstdev(
                        values
                    )
                    if len(
                        values
                    ) > 1
                    else 0.0
                ),
            }

        return result

    def overall_mean(
        self,
    ) -> float:
        values = [
            value
            for evaluation
            in self.evaluations
            for value
            in evaluation
            .score_map()
            .values()
        ]

        if not values:
            raise TraitEvaluationError(
                "aggregate contains "
                "no scores"
            )

        return statistics.fmean(
            values
        )

    def target_traits(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    trait
                    for evaluation
                    in self.evaluations
                    for trait
                    in evaluation
                    .target_traits
                }
            )
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://envoy/"
                "orobouros-trait-evaluation-"
                "aggregate/1.0.0"
            ),
            "aggregate_id": (
                self.aggregate_id
            ),
            "blind_id": (
                self.blind_id
            ),
            "evaluation_ids": [
                evaluation
                .evaluation_id
                for evaluation
                in self.evaluations
            ],
            "evaluation_count": len(
                self.evaluations
            ),
            "target_traits": list(
                self.target_traits()
            ),
            "measurements": (
                self.measurements()
            ),
            "overall_mean": (
                self.overall_mean()
            ),
            "provider_identity_exposed": (
                False
            ),
            "owner": OWNER,
            "verification_owner": (
                VERIFICATION_OWNER
            ),
            "evidence_admitted": False,
            "champion_selected": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def aggregate_evaluations(
    evaluations: Sequence[
        BlindEvaluation
    ],
) -> tuple[
    EvaluationAggregate,
    ...,
]:
    grouped: dict[
        str,
        list[
            BlindEvaluation
        ],
    ] = {}

    for evaluation in evaluations:
        grouped.setdefault(
            evaluation.blind_id,
            [],
        ).append(
            evaluation
        )

    return tuple(
        EvaluationAggregate(
            blind_id=blind_id,
            evaluations=tuple(
                grouped[
                    blind_id
                ]
            ),
        )
        for blind_id
        in sorted(
            grouped
        )
    )


def trait_measurements(
    aggregate: EvaluationAggregate,
    trait_id: str,
) -> dict[str, Any]:
    trait = normalize_term(
        trait_id
    )

    if not trait:
        raise TraitEvaluationError(
            "trait_id is required"
        )

    if (
        aggregate.target_traits()
        and trait
        not in aggregate.target_traits()
    ):
        raise TraitEvaluationError(
            "trait not represented "
            "by aggregate"
        )

    measurements = (
        aggregate.measurements()
    )

    flattened = {
        (
            dimension
            + "_mean"
        ): values[
            "mean"
        ]
        for dimension, values
        in measurements.items()
    }

    flattened[
        "overall_mean"
    ] = aggregate.overall_mean()

    return {
        "trait_id": trait,
        "blind_id": (
            aggregate.blind_id
        ),
        "aggregate_id": (
            aggregate.aggregate_id
        ),
        "measurements": flattened,
        "evaluation_count": len(
            aggregate.evaluations
        ),
        "provider_identity_exposed": (
            False
        ),
        "owner": OWNER,
        "verification_owner": (
            VERIFICATION_OWNER
        ),
        "evidence_admitted": False,
        "champion_selected": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-evaluation-"
            "status/1.0.0"
        ),
        "owner": OWNER,
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "verification_owner": (
            VERIFICATION_OWNER
        ),
        "blind_results": True,
        "provider_neutral_measurements": (
            True
        ),
        "deterministic_aggregation": (
            True
        ),
        "repeated_trial_aggregation": (
            True
        ),
        "automatic_evidence_admission": (
            False
        ),
        "automatic_champion_selection": (
            False
        ),
        "baseline_mutation": False,
        "crown_mutation": False,
        "persistent_store": False,
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
