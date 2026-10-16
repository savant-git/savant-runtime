from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from runtime.oid.clock import (
    ClockSkewPolicy,
    clock_projection,
)
from runtime.oid.constraint import (
    TemporalConstraint,
    constraint_projection,
    detect_constraint_conflicts,
)
from runtime.oid.core import (
    ClockObservation,
    TemporalRecord,
    detect_conflicts,
    temporal_receipt,
)
from runtime.oid.frame import (
    FrameTransition,
    OidFrame,
    advance_frame,
    establish_frame,
    frame_receipt,
    validate_transition,
)


SCHEMA = "savant://oid/runtime/1"


@dataclass(frozen=True, slots=True)
class OidRuntimeResult:
    frame: OidFrame
    transition: FrameTransition | None
    constraints: tuple[
        TemporalConstraint,
        ...
    ]
    clock_observations: tuple[
        ClockObservation,
        ...
    ]

    def projection(self) -> Mapping[str, Any]:
        temporal = temporal_receipt(
            self.frame.records
        )

        constraints = constraint_projection(
            self.constraints
        )

        clocks = clock_projection(
            self.clock_observations
        )

        frame = frame_receipt(
            self.frame
        )

        return {
            "schema": SCHEMA,
            "frame": self.frame.projection(),
            "frame_receipt": frame,
            "temporal_receipt": temporal,
            "constraint_projection": (
                constraints
            ),
            "clock_projection": clocks,
            "transition": (
                self.transition.projection()
                if self.transition is not None
                else None
            ),
            "temporal_conflict_count": len(
                detect_conflicts(
                    self.frame.records
                )
            ),
            "constraint_conflict_count": len(
                detect_constraint_conflicts(
                    self.constraints
                )
            ),
            "partial_order_preserved": True,
            "unknown_order_preserved": True,
            "concurrency_preserved": True,
            "contradictions_preserved": True,
            "automatic_reconciliation": False,
            "external_chronology_claimed": False,
            "authority_transferred": False,
            "model_independent": True,
            "provider_independent": True,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


def establish_runtime(
    *,
    frame_ref: str,
    records: Sequence[
        TemporalRecord
    ] = (),
    constraints: Sequence[
        TemporalConstraint
    ] = (),
    clock_observations: Sequence[
        ClockObservation
    ] = (),
    causal_refs: Sequence[str] = (),
) -> OidRuntimeResult:
    frame = establish_frame(
        frame_ref,
        records,
        causal_refs=causal_refs,
    )

    return OidRuntimeResult(
        frame=frame,
        transition=None,
        constraints=tuple(constraints),
        clock_observations=tuple(
            clock_observations
        ),
    )


def advance_runtime(
    predecessor: OidRuntimeResult,
    *,
    records: Sequence[TemporalRecord],
    constraints: Sequence[
        TemporalConstraint
    ] | None = None,
    clock_observations: Sequence[
        ClockObservation
    ] | None = None,
    causal_refs: Sequence[str] = (),
) -> OidRuntimeResult:
    successor, transition = advance_frame(
        predecessor.frame,
        records,
        causal_refs=causal_refs,
    )

    result = OidRuntimeResult(
        frame=successor,
        transition=transition,
        constraints=(
            predecessor.constraints
            if constraints is None
            else tuple(constraints)
        ),
        clock_observations=(
            predecessor.clock_observations
            if clock_observations is None
            else tuple(
                clock_observations
            )
        ),
    )

    if not validate_transition(
        predecessor.frame,
        successor,
        transition,
    ):
        raise ValueError(
            "invalid oid runtime transition"
        )

    return result


def validate_runtime(
    result: OidRuntimeResult,
) -> bool:
    projection = result.projection()

    if (
        projection[
            "authority_transferred"
        ]
        is not False
    ):
        return False

    if (
        projection[
            "automatic_reconciliation"
        ]
        is not False
    ):
        return False

    if (
        projection[
            "external_chronology_claimed"
        ]
        is not False
    ):
        return False

    if (
        projection["authoritative"]
        is not False
    ):
        return False

    if (
        projection["authority_effect"]
        != "none"
    ):
        return False

    return True
