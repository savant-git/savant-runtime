import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.inheritance import (
    MeaningSource,
    inherit_meaning,
    inherited_field,
    inheritance_projection,
)


def main() -> int:
    source = MeaningSource(
        source_ref="meaning:early-failure",
        dimensions={
            "risk": -0.8,
            "persistence": 0.7,
        },
        significance=0.9,
        confidence=0.9,
        causal_refs=(
            "experience:failure",
        ),
        evidence_refs=(
            "evidence:failure",
        ),
    )

    inherited = inherit_meaning(
        source,
        successor_ref=(
            "development:later-context"
        ),
        continuity=0.9,
        reinterpretation=0.2,
        causal_refs=(
            "state:later",
        ),
    )

    assert (
        inherited.inheritance_strength
        > 0.0
    )

    assert (
        inherited
        .inherited_dimensions["risk"]
        < 0.0
    )

    assert (
        inherited
        .inherited_dimensions[
            "persistence"
        ]
        > 0.0
    )

    revised = inherit_meaning(
        source,
        successor_ref=(
            "development:reinterpreted"
        ),
        continuity=0.9,
        reinterpretation=1.0,
        causal_refs=(
            "meaning:revision",
        ),
    )

    assert (
        abs(
            revised
            .inherited_dimensions["risk"]
        )
        < abs(
            inherited
            .inherited_dimensions["risk"]
        )
    )

    field = inherited_field(
        (
            inherited,
            revised,
        )
    )

    assert field["risk"] < 0.0
    assert field["persistence"] > 0.0

    projection = (
        inheritance_projection(
            (
                inherited,
                revised,
            )
        )
    )

    assert (
        projection[
            "meaning_can_be_revised"
        ]
        is True
    )

    assert (
        projection[
            "inheritance_is_identity"
        ]
        is False
    )

    assert (
        projection[
            "inheritance_is_authority"
        ]
        is False
    )

    assert (
        projection[
            "source_history_erased"
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
        projection["authoritative"]
        is False
    )

    assert (
        projection["authority_effect"]
        == "none"
    )

    assert source.id in (
        inherited.causal_refs
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
