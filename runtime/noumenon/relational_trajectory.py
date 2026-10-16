from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/relational-trajectory/1"

DIMENSIONS = (
    "familiarity",
    "trust",
    "affection",
    "respect",
    "admiration",
    "dependence",
    "vulnerability",
    "safety",
    "predictability",
    "reciprocity",
    "intimacy",
    "grievance",
    "unresolvedness",
    "indebtedness",
    "loyalty",
    "rivalry",
    "authority_asymmetry",
    "power_asymmetry",
    "expectation",
    "boundary_state",
)


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


@dataclass(frozen=True, slots=True)
class RelationshipState:
    subject_ref: str
    object_ref: str
    dimensions: Mapping[str, float]
    sequence: int
    predecessor_ref: str | None = None
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    repair_refs: tuple[str, ...] = ()
    shared_history_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_ref:
            raise ValueError(
                "subject_ref is required"
            )

        if not self.object_ref:
            raise ValueError(
                "object_ref is required"
            )

        if self.subject_ref == self.object_ref:
            raise ValueError(
                "relationship endpoints "
                "must be distinct"
            )

        if self.sequence < 0:
            raise ValueError(
                "sequence cannot be negative"
            )

        if (
            self.sequence > 0
            and not self.predecessor_ref
        ):
            raise ValueError(
                "non-genesis relationship "
                "state requires predecessor"
            )

        unknown = (
            set(self.dimensions)
            - set(DIMENSIONS)
        )

        if unknown:
            raise ValueError(
                "unsupported relationship "
                "dimensions: "
                + ", ".join(
                    sorted(unknown)
                )
            )

        for value in (
            self.dimensions.values()
        ):
            if not (
                -1.0
                <= float(value)
                <= 1.0
            ):
                raise ValueError(
                    "relationship dimensions "
                    "must be between -1 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_ref": self.subject_ref,
            "object_ref": self.object_ref,
            "dimensions": {
                key: float(value)
                for key, value
                in sorted(
                    self.dimensions.items()
                )
            },
            "sequence": self.sequence,
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "repair_refs": list(
                self.repair_refs
            ),
            "shared_history_refs": list(
                self.shared_history_refs
            ),
            "directional": True,
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
            "noumenon-relationship-state:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class RelationshipTransition:
    predecessor_ref: str
    successor_ref: str
    deltas: Mapping[str, float]
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.predecessor_ref:
            raise ValueError(
                "predecessor_ref is required"
            )

        if not self.successor_ref:
            raise ValueError(
                "successor_ref is required"
            )

        for value in self.deltas.values():
            if not (
                -2.0
                <= float(value)
                <= 2.0
            ):
                raise ValueError(
                    "relationship delta must "
                    "be between -2 and 2"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "successor_ref": (
                self.successor_ref
            ),
            "deltas": {
                key: float(value)
                for key, value
                in sorted(
                    self.deltas.items()
                )
            },
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
class RelationshipTrajectory:
    subject_ref: str
    object_ref: str
    states: tuple[
        RelationshipState,
        ...
    ]

    def __post_init__(self) -> None:
        if not self.states:
            raise ValueError(
                "trajectory requires states"
            )

        previous: RelationshipState | None = (
            None
        )

        for state in self.states:
            if (
                state.subject_ref
                != self.subject_ref
                or state.object_ref
                != self.object_ref
            ):
                raise ValueError(
                    "trajectory endpoint "
                    "mismatch"
                )

            if previous is None:
                if state.sequence != 0:
                    raise ValueError(
                        "trajectory must begin "
                        "at sequence zero"
                    )
            else:
                if (
                    state.sequence
                    != previous.sequence + 1
                ):
                    raise ValueError(
                        "relationship sequence "
                        "discontinuity"
                    )

                if (
                    state.predecessor_ref
                    != previous.id
                ):
                    raise ValueError(
                        "relationship lineage "
                        "discontinuity"
                    )

            previous = state

    @property
    def current(
        self,
    ) -> RelationshipState:
        return self.states[-1]

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject_ref": self.subject_ref,
            "object_ref": self.object_ref,
            "states": [
                state.projection()
                for state in self.states
            ],
            "current_ref": (
                self.current.id
            ),
            "directional": True,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


def establish_relationship(
    subject_ref: str,
    object_ref: str,
    *,
    dimensions: Mapping[
        str,
        float,
    ] | None = None,
    causal_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    shared_history_refs: Sequence[
        str
    ] = (),
) -> RelationshipTrajectory:
    state = RelationshipState(
        subject_ref=subject_ref,
        object_ref=object_ref,
        dimensions=dict(
            dimensions or {}
        ),
        sequence=0,
        causal_refs=tuple(
            dict.fromkeys(
                causal_refs
            )
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                evidence_refs
            )
        ),
        shared_history_refs=tuple(
            dict.fromkeys(
                shared_history_refs
            )
        ),
    )

    return RelationshipTrajectory(
        subject_ref=subject_ref,
        object_ref=object_ref,
        states=(state,),
    )


def transition_relationship(
    trajectory: RelationshipTrajectory,
    *,
    deltas: Mapping[str, float],
    causal_refs: Sequence[str],
    evidence_refs: Sequence[str] = (),
    repair_refs: Sequence[str] = (),
    shared_history_refs: Sequence[
        str
    ] = (),
) -> tuple[
    RelationshipTrajectory,
    RelationshipTransition,
]:
    if not causal_refs:
        raise ValueError(
            "relationship transition "
            "requires causal refs"
        )

    unknown = (
        set(deltas)
        - set(DIMENSIONS)
    )

    if unknown:
        raise ValueError(
            "unsupported relationship "
            "dimensions: "
            + ", ".join(
                sorted(unknown)
            )
        )

    predecessor = trajectory.current

    dimensions = dict(
        predecessor.dimensions
    )

    for dimension, delta in (
        deltas.items()
    ):
        dimensions[dimension] = _signed(
            dimensions.get(
                dimension,
                0.0,
            )
            + float(delta)
        )

    successor = RelationshipState(
        subject_ref=(
            trajectory.subject_ref
        ),
        object_ref=(
            trajectory.object_ref
        ),
        dimensions=dimensions,
        sequence=(
            predecessor.sequence + 1
        ),
        predecessor_ref=predecessor.id,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *predecessor.causal_refs,
                    *causal_refs,
                )
            )
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    *predecessor
                    .evidence_refs,
                    *evidence_refs,
                )
            )
        ),
        repair_refs=tuple(
            dict.fromkeys(
                (
                    *predecessor.repair_refs,
                    *repair_refs,
                )
            )
        ),
        shared_history_refs=tuple(
            dict.fromkeys(
                (
                    *predecessor
                    .shared_history_refs,
                    *shared_history_refs,
                )
            )
        ),
    )

    transition = (
        RelationshipTransition(
            predecessor_ref=(
                predecessor.id
            ),
            successor_ref=(
                successor.id
            ),
            deltas={
                key: (
                    float(
                        successor
                        .dimensions.get(
                            key,
                            0.0,
                        )
                    )
                    - float(
                        predecessor
                        .dimensions.get(
                            key,
                            0.0,
                        )
                    )
                )
                for key in sorted(
                    deltas
                )
            },
            causal_refs=tuple(
                dict.fromkeys(
                    causal_refs
                )
            ),
        )
    )

    updated = RelationshipTrajectory(
        subject_ref=(
            trajectory.subject_ref
        ),
        object_ref=(
            trajectory.object_ref
        ),
        states=(
            *trajectory.states,
            successor,
        ),
    )

    return updated, transition


def relationship_velocity(
    trajectory: RelationshipTrajectory,
) -> Mapping[str, float]:
    if len(trajectory.states) < 2:
        return {}

    previous = trajectory.states[-2]
    current = trajectory.states[-1]

    dimensions = (
        set(previous.dimensions)
        | set(current.dimensions)
    )

    return {
        dimension: (
            float(
                current.dimensions.get(
                    dimension,
                    0.0,
                )
            )
            - float(
                previous.dimensions.get(
                    dimension,
                    0.0,
                )
            )
        )
        for dimension
        in sorted(dimensions)
    }


def relationship_projection(
    trajectory: RelationshipTrajectory,
) -> Mapping[str, Any]:
    return {
        **trajectory.projection(),
        "velocity": dict(
            relationship_velocity(
                trajectory
            )
        ),
        "forgiveness_erases_evidence": (
            False
        ),
        "repair_restores_trust_automatically": (
            False
        ),
        "reciprocity_implied": False,
    }
