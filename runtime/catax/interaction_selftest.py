import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.interaction import (
    CataxInteraction,
    classify_interaction,
    compare_interactions,
    interaction_projection,
)


def main() -> int:
    first = TemporalCoordinate(
        coordinate_ref="event:a",
        frame_ref="frame:test",
        sequence=1,
        phase=1.0,
        uncertainty=0.1,
    )

    second = TemporalCoordinate(
        coordinate_ref="event:b",
        frame_ref="frame:test",
        sequence=2,
        phase=2.0,
        uncertainty=0.1,
    )

    concurrent = TemporalCoordinate(
        coordinate_ref="event:c",
        frame_ref="frame:test",
        sequence=1,
        phase=1.0,
        uncertainty=0.1,
    )

    foreign = TemporalCoordinate(
        coordinate_ref="event:d",
        frame_ref="frame:foreign",
        sequence=0,
    )

    aligned = classify_interaction(
        first,
        second,
    )

    assert (
        aligned.interaction
        == "aligned"
    )

    assert (
        aligned.geometry_relation
        == "precedes"
    )

    coincident = classify_interaction(
        first,
        concurrent,
    )

    assert (
        coincident.interaction
        == "coincident"
    )

    cross_frame = classify_interaction(
        first,
        foreign,
    )

    assert (
        cross_frame.interaction
        == "cross_frame"
    )

    assert (
        cross_frame.geometry_relation
        == "unknown"
    )

    contradictory = CataxInteraction(
        left_ref=aligned.left_ref,
        right_ref=aligned.right_ref,
        interaction="uncertain",
        geometry_relation="unknown",
        magnitude=None,
        uncertainty=0.5,
    )

    conflict = compare_interactions(
        aligned,
        contradictory,
    )

    assert (
        conflict.interaction
        == "opposed"
    )

    assert (
        conflict.geometry_relation
        == "diverges"
    )

    projection = interaction_projection(
        (
            first,
            second,
            concurrent,
            foreign,
        )
    )

    assert (
        projection["coordinate_count"]
        == 4
    )

    assert (
        projection["interaction_count"]
        == 6
    )

    assert (
        projection[
            "cross_frame_order_inferred"
        ]
        is False
    )

    assert (
        projection[
            "contradictions_preserved"
        ]
        is True
    )

    assert (
        projection["unknowns_preserved"]
        is True
    )

    assert (
        projection["source_mutated"]
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
            "external_chronology_claimed"
        ]
        is False
    )

    assert (
        projection["authority_transferred"]
        is False
    )

    assert (
        projection["model_independent"]
        is True
    )

    assert (
        projection["provider_independent"]
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

    assert len(projection["digest"]) == 64

    repeated = interaction_projection(
        (
            first,
            second,
            concurrent,
            foreign,
        )
    )

    assert (
        repeated["digest"]
        == projection["digest"]
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
