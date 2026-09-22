import sys
from datetime import datetime, timezone

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.bridge import (
    TemporalBridge,
)
from runtime.oid.constraint import (
    TemporalConstraint,
)
from runtime.oid.core import (
    ClockObservation,
    TemporalInterval,
    TemporalRecord,
)
from runtime.oid.frame import (
    establish_frame,
)
from runtime.oid.integrity import (
    inspect_frame,
    integrity_receipt,
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

    first = TemporalRecord(
        record_ref="event:a",
        frame_ref="oid:integrity-test",
        source_clock_ref="clock:a",
        logical_sequence=0,
        event_interval=TemporalInterval(),
        observation_time=now,
    )

    second = TemporalRecord(
        record_ref="event:b",
        frame_ref="oid:integrity-test",
        source_clock_ref="clock:b",
        logical_sequence=0,
        event_interval=TemporalInterval(),
        observation_time=now,
        predecessor_refs=(
            "oid-record:absent",
        ),
    )

    frame = establish_frame(
        "oid:integrity-test",
        (
            first,
            second,
        ),
    )

    constraint = TemporalConstraint(
        left_ref=first.id,
        right_ref="oid-record:missing",
        relation="before",
    )

    bridge = TemporalBridge(
        left_frame_ref=(
            "oid:integrity-test"
        ),
        left_record_ref=(
            "oid-record:bridge-missing"
        ),
        right_frame_ref="oid:other",
        right_record_ref=(
            "oid-record:other"
        ),
        relation="unknown",
    )

    clock = ClockObservation(
        source_clock_ref="clock:a",
        observed_offset_seconds=0.0,
        uncertainty_seconds=0.1,
        observation_ref=(
            "clock-observation:a"
        ),
    )

    findings = inspect_frame(
        frame,
        constraints=(constraint,),
        bridges=(bridge,),
    )

    codes = {
        finding.code
        for finding in findings
    }

    assert (
        "logical_sequence_collision"
        in codes
    )

    assert (
        "orphan_predecessor"
        in codes
    )

    assert (
        "constraint_endpoint_absent"
        in codes
    )

    assert (
        "bridge_endpoint_absent"
        in codes
    )

    receipt = integrity_receipt(
        frame,
        constraints=(constraint,),
        bridges=(bridge,),
        clock_observations=(clock,),
    )

    assert receipt["finding_count"] == 4

    assert (
        receipt[
            "logical_sequence_is_causal_fact"
        ]
        is False
    )

    assert (
        receipt[
            "integrity_is_external_truth"
        ]
        is False
    )

    assert (
        receipt[
            "automatic_reconciliation"
        ]
        is False
    )

    assert (
        receipt[
            "historical_evidence_mutated"
        ]
        is False
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

    assert (
        receipt["authoritative"]
        is False
    )

    assert (
        receipt["authority_effect"]
        == "none"
    )

    assert len(receipt["digest"]) == 64

    assert all(
        finding.projection()[
            "automatic_mutation"
        ]
        is False
        for finding in findings
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
