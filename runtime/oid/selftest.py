import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.core import (
    ClockObservation,
    TemporalInterval,
    TemporalRecord,
    detect_conflicts,
    interval_relation,
    next_logical_sequence,
    relate,
    replay_order,
    temporal_receipt,
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
        frame_ref="oid:test",
        source_clock_ref="clock:a",
        logical_sequence=0,
        event_interval=TemporalInterval(
            start=base,
            end=base + timedelta(seconds=10),
        ),
        observation_time=(
            base + timedelta(seconds=20)
        ),
        original_timestamp=(
            "2026-09-11T00:00:00Z"
        ),
        provenance_refs=("source:a",),
        evidence_refs=("evidence:a",),
    )

    second = TemporalRecord(
        record_ref="event:b",
        frame_ref="oid:test",
        source_clock_ref="clock:b",
        logical_sequence=1,
        event_interval=TemporalInterval(
            start=base + timedelta(seconds=20),
            end=base + timedelta(seconds=30),
        ),
        observation_time=(
            base + timedelta(seconds=31)
        ),
        predecessor_refs=(first.id,),
        provenance_refs=("source:b",),
        evidence_refs=("evidence:b",),
    )

    assert (
        interval_relation(
            first.event_interval,
            second.event_interval,
        )
        == "before"
    )

    relation = relate(first, second)

    assert relation.relation == "before"
    assert relation.causal is True

    unknown_a = TemporalRecord(
        record_ref="event:c",
        frame_ref="oid:test",
        source_clock_ref="clock:c",
        logical_sequence=2,
        event_interval=TemporalInterval(),
        observation_time=(
            base + timedelta(seconds=40)
        ),
    )

    unknown_b = TemporalRecord(
        record_ref="event:d",
        frame_ref="oid:test",
        source_clock_ref="clock:d",
        logical_sequence=3,
        event_interval=TemporalInterval(),
        observation_time=(
            base + timedelta(seconds=41)
        ),
    )

    concurrent = relate(
        unknown_a,
        unknown_b,
    )

    assert (
        concurrent.relation
        == "concurrent"
    )

    assert concurrent.causal is False

    conflicting = TemporalRecord(
        record_ref="event:a",
        frame_ref="oid:test",
        source_clock_ref="clock:x",
        logical_sequence=4,
        event_interval=TemporalInterval(
            start=base + timedelta(hours=1),
            end=base + timedelta(
                hours=1,
                seconds=10,
            ),
        ),
        observation_time=(
            base + timedelta(hours=1)
        ),
        provenance_refs=("source:x",),
        evidence_refs=("evidence:x",),
    )

    conflicts = detect_conflicts(
        (
            first,
            conflicting,
        )
    )

    assert len(conflicts) == 1

    assert (
        conflicts[0]
        .projection()[
            "automatically_resolved"
        ]
        is False
    )

    records = (
        unknown_b,
        second,
        first,
        unknown_a,
    )

    ordered = replay_order(records)

    assert [
        item.logical_sequence
        for item in ordered
    ] == [0, 1, 2, 3]

    assert (
        next_logical_sequence(records)
        == 4
    )

    clock = ClockObservation(
        source_clock_ref="clock:b",
        observed_offset_seconds=1.25,
        uncertainty_seconds=0.5,
        observation_ref="observation:clock:b",
    )

    clock_projection = (
        clock.projection()
    )

    assert (
        clock_projection[
            "authority_effect"
        ]
        == "none"
    )

    receipt = temporal_receipt(
        (
            first,
            second,
            unknown_a,
            unknown_b,
            conflicting,
        )
    )

    assert (
        receipt[
            "replay_is_external_chronology"
        ]
        is False
    )

    assert (
        receipt[
            "concurrency_may_be_preserved"
        ]
        is True
    )

    assert (
        receipt[
            "unknown_may_be_preserved"
        ]
        is True
    )

    assert (
        receipt[
            "authority_transferred"
        ]
        is False
    )

    assert (
        receipt["model_independent"]
        is True
    )

    assert (
        receipt["provider_independent"]
        is True
    )

    assert receipt["authoritative"] is False

    assert (
        receipt["authority_effect"]
        == "none"
    )

    assert len(receipt["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
