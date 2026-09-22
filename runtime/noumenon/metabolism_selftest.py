import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.metabolism import (
    empty_history,
    metabolism_projection,
    revise_meaning,
    significance_delta,
)


def main() -> int:
    history = empty_history(
        "experience:metabolism"
    )

    history = revise_meaning(
        history,
        interpretation=(
            "initial interpretation"
        ),
        epistemic_class="interpreted",
        significance={
            "trust": -0.6,
            "curiosity": 0.2,
        },
        causal_refs=(
            "experience:metabolism",
        ),
        evidence_refs=(
            "evidence:initial",
        ),
    )

    first = history.current

    assert first is not None

    assert (
        first.predecessor_ref
        is None
    )

    first_id = first.id

    history = revise_meaning(
        history,
        interpretation=(
            "later interpretation"
        ),
        epistemic_class="inferred",
        significance={
            "trust": -0.2,
            "curiosity": 0.5,
        },
        causal_refs=(
            "experience:metabolism",
            first_id,
        ),
        evidence_refs=(
            "evidence:later",
        ),
    )

    second = history.current

    assert second is not None

    assert (
        second.predecessor_ref
        == first_id
    )

    assert (
        second.experience_ref
        == first.experience_ref
    )

    assert (
        second.id
        != first.id
    )

    delta = significance_delta(
        first,
        second,
    )

    assert round(
        delta["trust"],
        10,
    ) == 0.4

    assert round(
        delta["curiosity"],
        10,
    ) == 0.3

    projection = (
        metabolism_projection(
            history
        )
    )

    assert (
        projection[
            "experience_ref"
        ]
        == "experience:metabolism"
    )

    assert (
        projection[
            "revision_count"
        ]
        == 2
    )

    assert (
        projection[
            "event_mutated"
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
        history.revisions[0]
        == first
    )

    assert (
        history.revisions[0]
        .interpretation
        == "initial interpretation"
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
