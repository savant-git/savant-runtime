import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.clock import (
    ClockSkewPolicy,
    clock_field,
    clock_projection,
    estimate_clock,
)
from runtime.oid.core import ClockObservation


def observation(
    ref: str,
    offset: float,
    uncertainty: float = 0.05,
) -> ClockObservation:
    return ClockObservation(
        source_clock_ref="clock:test",
        observed_offset_seconds=offset,
        uncertainty_seconds=uncertainty,
        observation_ref=ref,
    )


def main() -> int:
    observations = (
        observation("clock-observation:a", 1.00),
        observation("clock-observation:b", 1.05),
        observation("clock-observation:c", 0.95),
        observation(
            "clock-observation:outlier",
            50.0,
        ),
    )

    estimate = estimate_clock(
        observations,
        policy=ClockSkewPolicy(
            outlier_multiplier=3.0,
            minimum_tolerance_seconds=0.01,
        ),
    )

    assert (
        estimate.source_clock_ref
        == "clock:test"
    )

    assert (
        abs(
            estimate.offset_seconds
            - 1.0
        )
        < 0.1
    )

    assert (
        "clock-observation:outlier"
        in estimate.outlier_refs
    )

    assert (
        "clock-observation:a"
        in estimate.observation_refs
    )

    assert estimate.sample_count == 4

    projection = estimate.projection()

    assert (
        projection[
            "clock_correction_is_fact"
        ]
        is False
    )

    assert (
        projection[
            "source_timestamp_mutated"
        ]
        is False
    )

    assert (
        projection["authoritative"]
        is False
    )

    second_clock = ClockObservation(
        source_clock_ref="clock:second",
        observed_offset_seconds=-2.0,
        uncertainty_seconds=0.2,
        observation_ref="clock-observation:d",
    )

    field = clock_field(
        (
            *observations,
            second_clock,
        )
    )

    assert set(field) == {
        "clock:test",
        "clock:second",
    }

    complete = clock_projection(
        (
            *observations,
            second_clock,
        )
    )

    assert complete["clock_count"] == 2

    assert (
        complete[
            "observations_are_immutable"
        ]
        is True
    )

    assert (
        complete[
            "outliers_are_preserved"
        ]
        is True
    )

    assert (
        complete[
            "correction_is_projection_only"
        ]
        is True
    )

    assert (
        complete[
            "clock_estimate_is_authority"
        ]
        is False
    )

    assert (
        complete[
            "authority_transferred"
        ]
        is False
    )

    assert (
        complete["authoritative"]
        is False
    )

    assert (
        complete["authority_effect"]
        == "none"
    )

    assert len(complete["digest"]) == 64

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
