import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.catax.composition import (
    TransformChain,
    apply_chain,
    composition_projection,
)
from runtime.catax.core import (
    TemporalCoordinate,
)
from runtime.catax.transform import (
    TemporalTransform,
)


def main() -> int:
    coordinate = TemporalCoordinate(
        coordinate_ref="event:a",
        frame_ref="frame:test",
        phase=2.0,
        uncertainty=0.25,
    )

    translate = TemporalTransform(
        transform_ref="transform:translate",
        kind="translate",
        offset=3.0,
    )

    scale = TemporalTransform(
        transform_ref="transform:scale",
        kind="scale",
        factor=2.0,
        pivot=0.0,
    )

    reflect = TemporalTransform(
        transform_ref="transform:reflect",
        kind="reflect",
        pivot=6.0,
    )

    chain = TransformChain(
        chain_ref="chain:test",
        transforms=(
            translate,
            scale,
            reflect,
        ),
    )

    result = apply_chain(
        coordinate,
        chain,
    )

    assert result.source_phase == 2.0

    assert result.step_phases == (
        5.0,
        10.0,
        2.0,
    )

    assert result.projected_phase == 2.0

    assert result.uncertainty == 0.25

    receipt = result.projection()

    assert (
        receipt["source_mutated"]
        is False
    )

    assert (
        receipt[
            "intermediate_states_preserved"
        ]
        is True
    )

    assert (
        receipt[
            "external_chronology_claimed"
        ]
        is False
    )

    projection = composition_projection(
        (coordinate,),
        chain,
    )

    assert projection["source_count"] == 1
    assert projection["result_count"] == 1

    assert (
        projection[
            "composition_order_preserved"
        ]
        is True
    )

    assert (
        projection["source_mutated"]
        is False
    )

    assert (
        projection[
            "intermediate_states_preserved"
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

    repeated = composition_projection(
        (coordinate,),
        chain,
    )

    assert (
        repeated["digest"]
        == projection["digest"]
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
