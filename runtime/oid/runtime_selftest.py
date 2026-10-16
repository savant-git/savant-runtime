import sys
from datetime import (
    datetime,
    timedelta,
    timezone,
)

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.constraint import (
    TemporalConstraint,
)
from runtime.oid.core import (
    ClockObservation,
    TemporalInterval,
    TemporalRecord,
)
from runtime.oid.runtime import (
    advance_runtime,
    establish_runtime,
    validate_runtime,
)


def main() -> int:
    base = datetime(
        2026,
        9,
        11,
        0,
        0,
        tzinfo=timezone.utc,
    )

    first = TemporalRecord(
        record_ref="event:a",
        frame_ref="oid:runtime-test",
        source_clock_ref="clock:a",
        logical_sequence=0,
        event_interval=TemporalInterval(
            start=base,
            end=base + timedelta(
                seconds=1
            ),
        ),
        observation_time=(
            base + timedelta(
                seconds=2
            )
        ),
        evidence_refs=(
            "evidence:a",
        ),
    )

    clock_a = ClockObservation(
        source_clock_ref="clock:a",
        observed_offset_seconds=0.1,
        uncertainty_seconds=0.05,
        observation_ref=(
            "clock-observation:a"
        ),
    )

    genesis = establish_runtime(
        frame_ref="oid:runtime-test",
        records=(first,),
        clock_observations=(clock_a,),
        causal_refs=(
            "source:genesis",
        ),
    )

    assert validate_runtime(
        genesis
    )

    assert genesis.frame.generation == 0

    second = TemporalRecord(
        record_ref="event:b",
        frame_ref="oid:runtime-test",
        source_clock_ref="clock:b",
        logical_sequence=1,
        event_interval=TemporalInterval(
            start=base + timedelta(
                seconds=3
            ),
            end=base + timedelta(
                seconds=4
            ),
        ),
        observation_time=(
            base + timedelta(
                seconds=5
            )
        ),
        predecessor_refs=(
            first.id,
        ),
        evidence_refs=(
            "evidence:b",
        ),
    )

    constraint = TemporalConstraint(
        left_ref=first.id,
        right_ref=second.id,
        relation="before",
        evidence_refs=(
            "evidence:order",
        ),
    )

    clock_b = ClockObservation(
        source_clock_ref="clock:b",
        observed_offset_seconds=-0.2,
        uncertainty_seconds=0.1,
        observation_ref=(
            "clock-observation:b"
        ),
    )

    successor = advance_runtime(
        genesis,
        records=(
            first,
            second,
        ),
        constraints=(
            constraint,
        ),
        clock_observations=(
            clock_a,
            clock_b,
        ),
        causal_refs=(
            "source:advance",
        ),
    )

    assert validate_runtime(
        successor
    )

    assert (
        successor.frame.generation
        == 1
    )

    assert (
        successor.frame.predecessor_ref
        == genesis.frame.id
    )

    assert successor.transition is not None

    projection = successor.projection()

    assert (
        projection[
            "temporal_conflict_count"
        ]
        == 0
    )

    assert (
        projection[
            "constraint_conflict_count"
        ]
        == 0
    )

    assert (
        projection[
            "partial_order_preserved"
        ]
        is True
    )

    assert (
        projection[
            "unknown_order_preserved"
        ]
        is True
    )

    assert (
        projection[
            "concurrency_preserved"
        ]
        is True
    )

    assert (
        projection[
            "contradictions_preserved"
        ]
        is True
    )

    assert (
        projection[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        projection[
            "external_chronology_claimed"
        ]
        is False
    )

    assert (
        projection[
            "authority_transferred"
        ]
        is False
    )

    assert (
        projection[
            "model_independent"
        ]
        is True
    )

    assert (
        projection[
            "provider_independent"
        ]
        is True
    )

    assert (
        projection["authoritative"]
        is False
    )

    assert (
        projection["authority_effect"]
        == "none"
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
