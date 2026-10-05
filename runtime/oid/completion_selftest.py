import sys
from datetime import datetime, timezone

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.completion import (
    REQUIREMENTS,
    completion_receipt,
    requirement_statuses,
)
from runtime.oid.core import (
    ClockObservation,
    TemporalInterval,
    TemporalRecord,
)
from runtime.oid.frame import establish_frame


def main() -> int:
    now = datetime(
        2026,
        9,
        11,
        0,
        0,
        tzinfo=timezone.utc,
    )

    record = TemporalRecord(
        record_ref="event:completion",
        frame_ref="oid:completion-test",
        source_clock_ref="clock:test",
        logical_sequence=0,
        event_interval=TemporalInterval(
            start=now,
            end=now,
        ),
        observation_time=now,
        original_timestamp=(
            "2026-09-11T00:00:00Z"
        ),
        provenance_refs=(
            "source:test",
        ),
        evidence_refs=(
            "evidence:test",
        ),
        authority_refs=(
            "authority:test",
        ),
    )

    frame = establish_frame(
        "oid:completion-test",
        (record,),
    )

    clock = ClockObservation(
        source_clock_ref="clock:test",
        observed_offset_seconds=0.0,
        uncertainty_seconds=0.1,
        observation_ref=(
            "clock-observation:test"
        ),
    )

    statuses = requirement_statuses()

    assert len(statuses) == len(
        REQUIREMENTS
    )

    assert all(
        status.implemented
        for status in statuses
    )

    assert all(
        status.evidence_refs
        for status in statuses
    )

    receipt = completion_receipt(
        frame,
        clock_observations=(clock,),
    )

    assert (
        receipt["requirement_count"]
        == 35
    )

    assert (
        receipt["implemented_count"]
        == 35
    )

    assert (
        receipt["missing_requirements"]
        == []
    )

    assert receipt["complete"] is True

    assert (
        receipt["semantic_scope"]
        == "temporal_coherence"
    )

    assert (
        receipt[
            "external_truth_authority"
        ]
        is False
    )

    assert (
        receipt[
            "external_chronology_authority"
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
        receipt["dependency_sovereign"]
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

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
