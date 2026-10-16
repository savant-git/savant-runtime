import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.transference import (
    RelationalPattern,
    aggregate_pressure,
    hypothesize_transference,
    transference_field,
    transference_projection,
)


def main() -> int:
    prior = RelationalPattern(
        relationship_ref=(
            "relationship:prior"
        ),
        dimensions={
            "trust": -0.8,
            "safety": -0.7,
            "predictability": -0.6,
        },
        significance=0.9,
        confidence=0.9,
        causal_refs=(
            "episode:prior-rupture",
        ),
    )

    similar = RelationalPattern(
        relationship_ref=(
            "relationship:current"
        ),
        dimensions={
            "trust": -0.6,
            "safety": -0.5,
            "predictability": -0.4,
        },
        significance=0.7,
        confidence=0.8,
        causal_refs=(
            "episode:current",
        ),
    )

    unrelated = RelationalPattern(
        relationship_ref=(
            "relationship:unrelated"
        ),
        dimensions={
            "admiration": 0.8,
        },
        significance=0.8,
        confidence=0.9,
        causal_refs=(
            "episode:unrelated",
        ),
    )

    hypothesis = (
        hypothesize_transference(
            prior,
            similar,
        )
    )

    assert hypothesis.similarity > 0.0
    assert hypothesis.activation > 0.0

    assert (
        hypothesis.pressure["trust"]
        < 0.0
    )

    no_overlap = (
        hypothesize_transference(
            unrelated,
            similar,
        )
    )

    assert no_overlap.similarity == 0.0
    assert no_overlap.activation == 0.0
    assert no_overlap.pressure == {}

    field = transference_field(
        similar,
        (
            unrelated,
            prior,
        ),
    )

    assert (
        field[0]
        .source_relationship_ref
        == "relationship:prior"
    )

    pressure = aggregate_pressure(
        field
    )

    assert pressure["trust"] < 0.0
    assert pressure["safety"] < 0.0

    projection = (
        transference_projection(
            similar,
            (
                prior,
                unrelated,
            ),
        )
    )

    assert (
        projection[
            "strongest_source_ref"
        ]
        == "relationship:prior"
    )

    assert (
        projection[
            "transference_is_hypothesis"
        ]
        is True
    )

    assert (
        projection[
            "transference_is_fact"
        ]
        is False
    )

    assert (
        projection[
            "transference_is_authority"
        ]
        is False
    )

    assert (
        projection[
            "automatic_relationship_mutation"
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

    assert prior.id in (
        hypothesis.causal_refs
    )

    assert similar.id in (
        hypothesis.causal_refs
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
