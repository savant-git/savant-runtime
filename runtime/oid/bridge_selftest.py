import sys
from datetime import datetime, timezone

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.bridge import (
    TemporalBridge,
    bridge_constraint,
    bridge_projection,
    detect_bridge_conflicts,
    validate_bridge_records,
)
from runtime.oid.core import (
    TemporalInterval,
    TemporalRecord,
)


def main() -> int:
    now = datetime(
        2026,
        9,
        11,
        0,
        0,
        tzinfo=timezone.utc,
    )

    left = TemporalRecord(
        record_ref="event:left",
        frame_ref="oid:left",
        source_clock_ref="clock:left",
        logical_sequence=0,
        event_interval=TemporalInterval(),
        observation_time=now,
    )

    right = TemporalRecord(
        record_ref="event:right",
        frame_ref="oid:right",
        source_clock_ref="clock:right",
        logical_sequence=0,
        event_interval=TemporalInterval(),
        observation_time=now,
    )

    bridge = TemporalBridge(
        left_frame_ref="oid:left",
        left_record_ref=left.id,
        right_frame_ref="oid:right",
        right_record_ref=right.id,
        relation="before",
        evidence_refs=(
            "evidence:bridge",
        ),
        provenance_refs=(
            "source:bridge",
        ),
    )

    assert validate_bridge_records(
        bridge,
        (left, right),
    )

    constraint = bridge_constraint(
        bridge
    )

    assert constraint is not None

    assert (
        constraint.left_ref
        == left.id
    )

    assert (
        constraint.right_ref
        == right.id
    )

    assert (
        constraint.relation
        == "before"
    )

    reverse = TemporalBridge(
        left_frame_ref="oid:left",
        left_record_ref=left.id,
        right_frame_ref="oid:right",
        right_record_ref=right.id,
        relation="after",
        evidence_refs=(
            "evidence:reverse",
        ),
    )

    conflicts = detect_bridge_conflicts(
        (
            bridge,
            reverse,
        )
    )

    assert len(conflicts) == 1

    assert (
        conflicts[0].reason
        == "incompatible_cross_frame_relations"
    )

    projection = bridge_projection(
        (bridge,)
    )

    assert projection["bridge_count"] == 1

    assert (
        projection[
            "cross_frame_order_requires_bridge"
        ]
        is True
    )

    assert (
        projection[
            "implicit_cross_frame_order"
        ]
        is False
    )

    assert (
        projection[
            "automatic_reconciliation"
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
        projection["authoritative"]
        is False
    )

    assert (
        projection["authority_effect"]
        == "none"
    )

    assert len(projection["digest"]) == 64

    try:
        TemporalBridge(
            left_frame_ref="oid:left",
            left_record_ref=left.id,
            right_frame_ref="oid:left",
            right_record_ref=left.id,
            relation="equal",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "same-frame bridge accepted"
        )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
