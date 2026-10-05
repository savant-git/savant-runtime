import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.transform import (
    TemporalTransform,
    apply_transform,
    transform_geometry,
    transform_projection,
)


def main() -> int:
    first = TemporalCoordinate(
        coordinate_ref="event:a",
        frame_ref="frame:test",
        phase=2.0,
        uncertainty=0.1,
    )

    second = TemporalCoordinate(
        coordinate_ref="event:b",
        frame_ref="frame:test",
        phase=5.0,
        uncertainty=0.1,
    )

    translate = TemporalTransform(
        transform_ref="transform:translate",
        kind="translate",
        offset=10.0,
    )

    projected = apply_transform(
        first,
        translate,
    )

    assert projected.source_phase == 2.0
    assert projected.projected_phase == 12.0

    scale = TemporalTransform(
        transform_ref="transform:scale",
        kind="scale",
        factor=2.0,
        pivot=0.0,
    )

    scaled = apply_transform(
        second,
        scale,
    )

    assert scaled.projected_phase == 10.0

    reflect = TemporalTransform(
        transform_ref="transform:reflect",
        kind="reflect",
        pivot=4.0,
    )

    reflected = apply_transform(
        first,
        reflect,
    )

    assert reflected.projected_phase == 6.0

    relation = transform_geometry(
        first,
        second,
        translate,
    )

    assert relation.relation == "precedes"
    assert relation.distance == 3.0

    reflected_relation = (
        transform_geometry(
            first,
            second,
            reflect,
        )
    )

    assert (
        reflected_relation.relation
        == "follows"
    )

    projection = transform_projection(
        (first, second),
        translate,
    )

    assert projection["source_count"] == 2
    assert projection["projection_count"] == 2

    assert (
        projection["source_mutated"]
        is False
    )

    assert (
        projection["order_fabricated"]
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

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
