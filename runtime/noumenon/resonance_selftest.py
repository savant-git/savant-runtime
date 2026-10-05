import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.resonance import (
    ResonanceSource,
    resonate,
    resonance_field,
    resonance_projection,
)


def main() -> int:
    focal = ResonanceSource(
        source_ref="experience:current",
        dimensions={
            "trust": -0.8,
            "safety": -0.6,
        },
        significance=0.9,
        recency=1.0,
        unresolved=0.8,
        relational=1.0,
        causal_refs=(
            "relationship:alpha",
        ),
    )

    similar = ResonanceSource(
        source_ref="experience:historical-a",
        dimensions={
            "trust": -0.9,
            "safety": -0.5,
        },
        significance=0.8,
        recency=0.4,
        unresolved=0.7,
        relational=1.0,
        causal_refs=(
            "relationship:beta",
        ),
    )

    opposed = ResonanceSource(
        source_ref="experience:historical-b",
        dimensions={
            "trust": 0.9,
            "safety": 0.7,
        },
        significance=0.8,
        recency=0.8,
        unresolved=0.2,
        relational=0.8,
    )

    unrelated = ResonanceSource(
        source_ref="experience:historical-c",
        dimensions={
            "curiosity": 0.9,
        },
        significance=0.9,
        recency=0.9,
    )

    aligned = resonate(
        focal,
        similar,
    )

    contrary = resonate(
        focal,
        opposed,
    )

    none = resonate(
        focal,
        unrelated,
    )

    assert (
        aligned.directional_alignment
        == 1.0
    )

    assert (
        contrary.directional_alignment
        == 0.0
    )

    assert (
        aligned
        .developmental_resonance
        > contrary
        .developmental_resonance
    )

    assert (
        none.developmental_resonance
        == 0.0
    )

    assert (
        none.shared_dimensions
        == ()
    )

    field = resonance_field(
        focal,
        (
            opposed,
            unrelated,
            similar,
        ),
    )

    assert (
        field[0].source_b_ref
        == similar.id
    )

    projection = (
        resonance_projection(
            focal,
            (
                opposed,
                unrelated,
                similar,
            ),
        )
    )

    assert (
        projection[
            "strongest_ref"
        ]
        == similar.id
    )

    assert (
        projection[
            "authoritative"
        ]
        is False
    )

    assert (
        projection[
            "authority_effect"
        ]
        == "none"
    )

    assert focal.id in (
        aligned.causal_refs
    )

    assert similar.id in (
        aligned.causal_refs
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
