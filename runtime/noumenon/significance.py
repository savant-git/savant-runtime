from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/significance-propagation/1"


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def _signed(
    value: float,
) -> float:
    return max(
        -1.0,
        min(
            1.0,
            float(value),
        ),
    )


def _unit(
    value: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


@dataclass(frozen=True, slots=True)
class SignificanceNode:
    subject_ref: str
    significance: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_ref:
            raise ValueError(
                "subject_ref is required"
            )

        if not (
            -1.0
            <= float(self.significance)
            <= 1.0
        ):
            raise ValueError(
                "significance must be "
                "between -1 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_ref": self.subject_ref,
            "significance": float(
                self.significance
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-significance-node:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class SignificanceSegue:
    source_ref: str
    target_ref: str
    relation: str
    strength: float
    polarity: float = 1.0
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        if not self.target_ref:
            raise ValueError(
                "target_ref is required"
            )

        if not self.relation:
            raise ValueError(
                "relation is required"
            )

        if self.source_ref == self.target_ref:
            raise ValueError(
                "significance segue requires "
                "distinct endpoints"
            )

        if not (
            0.0
            <= float(self.strength)
            <= 1.0
        ):
            raise ValueError(
                "strength must be between "
                "0 and 1"
            )

        if not (
            -1.0
            <= float(self.polarity)
            <= 1.0
        ):
            raise ValueError(
                "polarity must be between "
                "-1 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "target_ref": self.target_ref,
            "relation": self.relation,
            "strength": float(
                self.strength
            ),
            "polarity": float(
                self.polarity
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-significance-segue:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class SignificancePropagation:
    source_ref: str
    target_ref: str
    segue_ref: str
    source_significance: float
    propagated_significance: float
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_ref:
            raise ValueError(
                "source_ref is required"
            )

        if not self.target_ref:
            raise ValueError(
                "target_ref is required"
            )

        if not self.segue_ref:
            raise ValueError(
                "segue_ref is required"
            )

        for value in (
            self.source_significance,
            self.propagated_significance,
        ):
            if not (
                -1.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "propagation values must "
                    "be between -1 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_ref": self.source_ref,
            "target_ref": self.target_ref,
            "segue_ref": self.segue_ref,
            "source_significance": float(
                self.source_significance
            ),
            "propagated_significance": (
                float(
                    self
                    .propagated_significance
                )
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


@dataclass(frozen=True, slots=True)
class SignificancePolicy:
    attenuation: float
    maximum_depth: int

    def __post_init__(self) -> None:
        if not (
            0.0
            <= float(self.attenuation)
            <= 1.0
        ):
            raise ValueError(
                "attenuation must be between "
                "0 and 1"
            )

        if self.maximum_depth < 0:
            raise ValueError(
                "maximum_depth cannot be "
                "negative"
            )


def propagate_once(
    source: SignificanceNode,
    segue: SignificanceSegue,
    *,
    policy: SignificancePolicy,
    depth: int = 1,
) -> SignificancePropagation:
    if (
        segue.source_ref
        != source.subject_ref
    ):
        raise ValueError(
            "segue source mismatch"
        )

    if depth < 1:
        raise ValueError(
            "depth must be at least 1"
        )

    if depth > policy.maximum_depth:
        propagated = 0.0
    else:
        attenuation = (
            float(policy.attenuation)
            ** depth
        )

        propagated = _signed(
            float(source.significance)
            * float(segue.strength)
            * float(segue.polarity)
            * attenuation
        )

    return SignificancePropagation(
        source_ref=source.subject_ref,
        target_ref=segue.target_ref,
        segue_ref=segue.id,
        source_significance=(
            source.significance
        ),
        propagated_significance=(
            propagated
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    source.id,
                    segue.id,
                    *source.causal_refs,
                    *segue.causal_refs,
                )
            )
        ),
    )


def propagate_field(
    nodes: Sequence[
        SignificanceNode
    ],
    segues: Sequence[
        SignificanceSegue
    ],
    *,
    policy: SignificancePolicy,
) -> Mapping[str, float]:
    node_by_subject = {
        node.subject_ref: node
        for node in nodes
    }

    if len(node_by_subject) != len(
        nodes
    ):
        raise ValueError(
            "duplicate significance subjects"
        )

    values = {
        node.subject_ref: float(
            node.significance
        )
        for node in nodes
    }

    frontier = dict(values)

    for depth in range(
        1,
        policy.maximum_depth + 1,
    ):
        next_frontier: dict[
            str,
            float,
        ] = {}

        for segue in sorted(
            segues,
            key=lambda item: (
                item.source_ref,
                item.target_ref,
                item.relation,
                item.id,
            ),
        ):
            if (
                segue.source_ref
                not in frontier
            ):
                continue

            source_value = frontier[
                segue.source_ref
            ]

            propagated = _signed(
                source_value
                * float(segue.strength)
                * float(segue.polarity)
                * float(
                    policy.attenuation
                )
            )

            if propagated == 0.0:
                continue

            previous = next_frontier.get(
                segue.target_ref,
                0.0,
            )

            next_frontier[
                segue.target_ref
            ] = _signed(
                previous
                + propagated
            )

        if not next_frontier:
            break

        for target_ref, value in (
            next_frontier.items()
        ):
            values[target_ref] = _signed(
                values.get(
                    target_ref,
                    0.0,
                )
                + value
            )

        frontier = next_frontier

    return {
        key: values[key]
        for key in sorted(values)
    }


def significance_gradient(
    field: Mapping[str, float],
) -> tuple[
    tuple[str, float],
    ...
]:
    return tuple(
        sorted(
            (
                (
                    subject_ref,
                    _signed(value),
                )
                for subject_ref, value
                in field.items()
            ),
            key=lambda item: (
                -abs(item[1]),
                item[0],
            ),
        )
    )


def significance_projection(
    nodes: Sequence[
        SignificanceNode
    ],
    segues: Sequence[
        SignificanceSegue
    ],
    *,
    policy: SignificancePolicy,
) -> Mapping[str, Any]:
    field = propagate_field(
        nodes,
        segues,
        policy=policy,
    )

    return {
        "schema": SCHEMA,
        "field": dict(field),
        "gradient": [
            {
                "subject_ref": (
                    subject_ref
                ),
                "significance": value,
            }
            for subject_ref, value
            in significance_gradient(
                field
            )
        ],
        "propagation_is_authority": False,
        "automatic_mutation": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
