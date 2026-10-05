import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.catax.core import (
    TemporalCoordinate,
    geometry_projection,
    relate,
)


def main() -> int:
    first = TemporalCoordinate(
        coordinate_ref="event:a",
        frame_ref="frame:a",
        sequence=1,
        uncertainty=0.1,
        provenance_refs=(
            "source:a",
        ),
    )

    second = TemporalCoordinate(
        coordinate_ref="event:b",
        frame_ref="frame:a",
        sequence=2,
        uncertainty=0.1,
        evidence_refs=(
            "evidence:b",
        ),
    )

    foreign = TemporalCoordinate(
        coordinate_ref="event:c",
        frame_ref="frame:b",
        sequence=0,
    )

    relation = relate(
        first,
        second,
    )

    assert relation.relation == "precedes"

    assert relation.distance == 1.0

    assert (
        relation.external_chronology_claimed
        if hasattr(
            relation,
            "external_chronology_claimed",
        )
        else False
    ) is False

    reverse = relate(
        second,
        first,
    )

    assert reverse.relation == "follows"

    cross_frame = relate(
        first,
        foreign,
    )

    assert (
        cross_frame.relation
        == "unknown"
    )

    projection = geometry_projection(
        (
            second,
            foreign,
            first,
        )
    )

    assert (
        projection[
            "coordinate_count"
        ]
        == 3
    )

    assert (
        projection[
            "relation_count"
        ]
        == 3
    )

    assert (
        projection[
            "cross_frame_order_inferred"
        ]
        is False
    )

    assert (
        projection[
            "unknowns_preserved"
        ]
        is True
    )

    assert (
        projection[
            "temporal_geometry_is_projection"
        ]
        is True
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

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
