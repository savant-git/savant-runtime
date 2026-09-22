import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.path_dependence import (
    PathEvent,
    compare_paths,
    derive_path_state,
    path_projection,
    transformative_thresholds,
)


def main() -> int:
    trust = PathEvent(
        event_ref="event:trust",
        dimensions={
            "trust": 0.9,
        },
        significance=1.0,
        persistence=0.9,
        sequence=0,
        causal_refs=(
            "experience:trust",
        ),
    )

    rupture = PathEvent(
        event_ref="event:rupture",
        dimensions={
            "trust": -0.9,
        },
        significance=1.0,
        persistence=0.9,
        sequence=1,
        causal_refs=(
            "experience:rupture",
        ),
    )

    path_a = derive_path_state(
        (
            trust,
            rupture,
        ),
        hysteresis_retention=0.8,
    )

    rupture_first = PathEvent(
        event_ref="event:rupture-first",
        dimensions={
            "trust": -0.9,
        },
        significance=1.0,
        persistence=0.9,
        sequence=0,
        causal_refs=(
            "experience:rupture",
        ),
    )

    trust_second = PathEvent(
        event_ref="event:trust-second",
        dimensions={
            "trust": 0.9,
        },
        significance=1.0,
        persistence=0.9,
        sequence=1,
        causal_refs=(
            "experience:trust",
        ),
    )

    path_b = derive_path_state(
        (
            rupture_first,
            trust_second,
        ),
        hysteresis_retention=0.8,
    )

    difference = compare_paths(
        path_a,
        path_b,
    )

    assert (
        difference["trust"]
        != 0.0
    )

    genesis = derive_path_state(
        (trust,),
        hysteresis_retention=0.8,
    )

    crossed = transformative_thresholds(
        genesis,
        path_a,
        threshold=0.5,
    )

    assert "trust" in crossed

    assert (
        path_a.hysteresis["trust"]
        != 0.0
    )

    assert trust.id in (
        path_a.causal_refs
    )

    assert rupture.id in (
        path_a.causal_refs
    )

    projection = path_projection(
        (
            trust,
            rupture,
        ),
        hysteresis_retention=0.8,
    )

    assert (
        projection[
            "path_order_matters"
        ]
        is True
    )

    assert (
        projection[
            "hysteresis_preserved"
        ]
        is True
    )

    assert (
        projection[
            "history_is_authority"
        ]
        is False
    )

    assert (
        projection[
            "automatic_identity_mutation"
        ]
        is False
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

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
