import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.prospective import (
    PossibleSelf,
    build_ecology,
    prospective_dimension_pressure,
    prospective_projection,
)


def main() -> int:
    repair_self = PossibleSelf(
        possible_self_ref=(
            "possible-self:repair"
        ),
        dimensions={
            "trustworthiness": 0.9,
            "avoidance": -0.7,
        },
        plausibility=0.8,
        desirability=0.9,
        commitment=0.9,
        continuity=0.9,
        causal_refs=(
            "commitment:repair",
        ),
    )

    withdrawal_self = PossibleSelf(
        possible_self_ref=(
            "possible-self:withdrawal"
        ),
        dimensions={
            "trustworthiness": 0.1,
            "avoidance": 0.9,
        },
        plausibility=0.7,
        desirability=0.2,
        commitment=0.2,
        continuity=0.6,
        causal_refs=(
            "residue:wound",
        ),
    )

    ecology = build_ecology(
        (
            repair_self,
            withdrawal_self,
        )
    )

    assert (
        len(ecology.selves)
        == 2
    )

    pressures = {
        item.possible_self_ref:
        item.pressure
        for item in ecology.pressures
    }

    assert (
        pressures[repair_self.id]
        > pressures[
            withdrawal_self.id
        ]
    )

    dimensions = (
        prospective_dimension_pressure(
            ecology
        )
    )

    assert (
        dimensions[
            "trustworthiness"
        ]
        > 0.0
    )

    projection = (
        prospective_projection(
            (
                repair_self,
                withdrawal_self,
            )
        )
    )

    assert (
        projection[
            "dominant_possible_self_ref"
        ]
        == repair_self.id
    )

    assert (
        projection[
            "future_is_prediction"
        ]
        is False
    )

    assert (
        projection[
            "future_is_authority"
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
