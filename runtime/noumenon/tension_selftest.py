import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.tension import (
    DevelopmentalTension,
    TensionResolution,
    apply_resolution,
    establish_tension,
    tension_competition,
    tension_debt,
    tension_projection,
)


def main() -> int:
    contradiction = (
        DevelopmentalTension(
            tension_ref=(
                "tension:value-behavior"
            ),
            kind="contradiction",
            pressure=0.9,
            persistence=0.9,
            uncertainty=0.1,
            resolvability=0.8,
            causal_refs=(
                "value:professed",
                "behavior:observed",
            ),
            evidence_refs=(
                "evidence:behavior",
            ),
        )
    )

    relational = (
        DevelopmentalTension(
            tension_ref=(
                "tension:relationship"
            ),
            kind="relational",
            pressure=0.5,
            persistence=0.6,
            uncertainty=0.2,
            resolvability=0.9,
            causal_refs=(
                "relationship:alpha",
            ),
        )
    )

    contradiction_state = (
        establish_tension(
            contradiction
        )
    )

    relational_state = (
        establish_tension(
            relational
        )
    )

    before = tension_debt(
        (
            contradiction_state,
            relational_state,
        )
    )

    assert before > 0.0

    ranked = tension_competition(
        (
            relational_state,
            contradiction_state,
        )
    )

    assert (
        ranked[0].origin.id
        == contradiction.id
    )

    resolution = TensionResolution(
        tension_ref=contradiction.id,
        resolution_ref=(
            "resolution:behavior-change"
        ),
        acknowledgment=1.0,
        action=0.9,
        consequence_change=0.8,
        evidence_support=0.9,
        causal_refs=(
            "experience:repair",
        ),
        evidence_refs=(
            "evidence:repair",
        ),
    )

    resolved_state = (
        apply_resolution(
            contradiction_state,
            resolution,
        )
    )

    assert (
        resolved_state.current_pressure
        < contradiction_state
        .current_pressure
    )

    assert (
        contradiction.id
        in resolved_state.causal_refs
    )

    assert (
        "resolution:behavior-change"
        in resolved_state.causal_refs
    )

    after = tension_debt(
        (
            resolved_state,
            relational_state,
        )
    )

    assert after < before

    projection = tension_projection(
        (
            resolved_state,
            relational_state,
        )
    )

    assert (
        projection[
            "resolution_erases_origin"
        ]
        is False
    )

    assert (
        projection[
            "unresolved_is_authority"
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
