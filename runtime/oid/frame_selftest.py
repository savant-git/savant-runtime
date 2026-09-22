import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.core import (
    TemporalInterval,
    TemporalRecord,
)
from runtime.oid.frame import (
    advance_frame,
    establish_frame,
    frame_receipt,
    validate_transition,
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
            base + timedelta(seconds=11)
        ),
        evidence_refs=("evidence:a",),
    )

    genesis = establish_frame(
        "oid:test",
        (first,),
        causal_refs=("source:genesis",),
    )

    assert genesis.generation == 0
    assert genesis.predecessor_ref is None

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
        evidence_refs=("evidence:b",),
    )

    successor, transition = advance_frame(
        genesis,
        (
            first,
            second,
        ),
        causal_refs=("source:advance",),
    )

    assert successor.generation == 1

    assert (
        successor.predecessor_ref
        == genesis.id
    )

    assert validate_transition(
        genesis,
        successor,
        transition,
    )

    assert second.id in (
        transition.added_record_refs
    )

    assert first.id in (
        transition.retained_record_refs
    )

    assert (
        transition.removed_record_refs
        == ()
    )

    receipt = frame_receipt(
        successor
    )

    assert receipt["record_count"] == 2

    assert (
        receipt[
            "replay_is_external_chronology"
        ]
        is False
    )

    assert (
        receipt[
            "conflicts_are_automatically_resolved"
        ]
        is False
    )

    assert (
        receipt["authority_transferred"]
        is False
    )

    assert receipt["authoritative"] is False

    assert (
        receipt["authority_effect"]
        == "none"
    )

    projection = successor.projection()

    assert (
        projection["single_present_claimed"]
        is False
    )

    assert (
        projection["partial_order_preserved"]
        is True
    )

    assert (
        projection["conflicts_preserved"]
        is True
    )

    assert len(successor.digest) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
