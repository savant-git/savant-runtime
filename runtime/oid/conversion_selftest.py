import sys
from datetime import datetime, timezone

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.clock import ClockEstimate
from runtime.oid.conversion import (
    conversion_receipt,
    convert_interval,
    convert_timestamp,
)
from runtime.oid.core import TemporalInterval


def main() -> int:
    source = datetime(
        2026,
        9,
        10,
        21,
        0,
        tzinfo=timezone.utc,
    )

    estimate = ClockEstimate(
        source_clock_ref="clock:test",
        offset_seconds=2.0,
        uncertainty_seconds=0.25,
        observation_refs=(
            "observation:a",
            "observation:b",
        ),
        outlier_refs=(),
        sample_count=2,
    )

    converted = convert_timestamp(
        source,
        source_clock_ref="clock:test",
        original_timestamp=(
            "2026-09-10T21:00:00+00:00"
        ),
        clock_estimate=estimate,
    )

    assert (
        converted.normalized_utc
        == source
    )

    assert (
        converted.projected_utc
        < converted.normalized_utc
    )

    assert (
        converted.clock_offset_seconds
        == 2.0
    )

    assert (
        converted.uncertainty_seconds
        == 0.25
    )

    assert converted.correction_applied is True

    projection = converted.projection()

    assert (
        projection[
            "original_timestamp_preserved"
        ]
        is True
    )

    assert (
        projection[
            "projection_is_external_fact"
        ]
        is False
    )

    assert (
        projection[
            "source_evidence_mutated"
        ]
        is False
    )

    interval = TemporalInterval(
        start=source,
        end=source,
        uncertainty_seconds=0.5,
    )

    converted_interval = convert_interval(
        interval,
        source_clock_ref="clock:test",
        clock_estimate=estimate,
    )

    assert (
        converted_interval
        .projected_interval
        .uncertainty_seconds
        == 0.75
    )

    assert (
        converted_interval
        .projected_interval
        .start
        < interval.start
    )

    receipt = conversion_receipt(
        converted,
        converted_interval,
    )

    assert (
        receipt[
            "original_representation_preserved"
        ]
        is True
    )

    assert (
        receipt["utc_normalization"]
        is True
    )

    assert (
        receipt[
            "uncertainty_preserved"
        ]
        is True
    )

    assert (
        receipt[
            "clock_correction_is_projection"
        ]
        is True
    )

    assert (
        receipt[
            "destructive_conversion"
        ]
        is False
    )

    assert (
        receipt[
            "external_chronology_claimed"
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
        receipt["authoritative"]
        is False
    )

    assert (
        receipt["authority_effect"]
        == "none"
    )

    assert len(receipt["digest"]) == 64

    unchanged = convert_timestamp(
        source,
        source_clock_ref="clock:raw",
        original_timestamp="raw",
    )

    assert (
        unchanged.projected_utc
        == unchanged.normalized_utc
    )

    assert (
        unchanged.correction_applied
        is False
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
