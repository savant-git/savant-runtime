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
    TemporalInterval,
    TemporalRecord,
)
from runtime.oid.projection import (
    deterministic_replay,
    temporal_snapshot,
    topological_layers,
)


def record(
    ref: str,
    sequence: int,
    base: datetime,
    predecessors: tuple[str, ...] = (),
) -> TemporalRecord:
    return TemporalRecord(
        record_ref=ref,
        frame_ref="oid:projection-test",
        source_clock_ref="clock:test",
        logical_sequence=sequence,
        event_interval=TemporalInterval(),
        observation_time=(
            base
            + timedelta(
                seconds=sequence
            )
        ),
        predecessor_refs=predecessors,
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

    first = record(
        "event:a",
        0,
        base,
    )

    second = record(
        "event:b",
        1,
        base,
        (first.id,),
    )

    concurrent = record(
        "event:c",
        2,
        base,
    )

    last = record(
        "event:d",
        3,
        base,
    )

    constraint = TemporalConstraint(
        left_ref=second.id,
        right_ref=last.id,
        relation="before",
    )

    records = (
        last,
        concurrent,
        second,
        first,
    )

    layers = topological_layers(
        records,
        (constraint,),
    )

    assert first.id in (
        layers[0].record_refs
    )

    assert concurrent.id in (
        layers[0].record_refs
    )

    assert second.id in (
        layers[1].record_refs
    )

    assert last.id in (
        layers[2].record_refs
    )

    ordered = deterministic_replay(
        records,
        (constraint,),
    )

    positions = {
        item.id: index
        for index, item
        in enumerate(ordered)
    }

    assert (
        positions[first.id]
        < positions[second.id]
    )

    assert (
        positions[second.id]
        < positions[last.id]
    )

    snapshot = temporal_snapshot(
        records,
        (constraint,),
    )

    assert snapshot["record_count"] == 4

    assert (
        snapshot[
            "single_present_projection"
        ]
        is True
    )

    assert (
        snapshot[
            "single_present_is_external_fact"
        ]
        is False
    )

    assert (
        snapshot[
            "replay_is_external_chronology"
        ]
        is False
    )

    assert (
        snapshot[
            "partial_order_preserved"
        ]
        is True
    )

    assert (
        snapshot[
            "concurrency_preserved"
        ]
        is True
    )

    assert (
        snapshot[
            "unknown_order_preserved"
        ]
        is True
    )

    assert (
        snapshot[
            "conflicts_preserved"
        ]
        is True
    )

    assert (
        snapshot[
            "authority_transferred"
        ]
        is False
    )

    assert (
        snapshot["authoritative"]
        is False
    )

    assert (
        snapshot["authority_effect"]
        == "none"
    )

    assert len(snapshot["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
