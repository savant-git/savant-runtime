import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.affect import (
    AffectInfluence,
    AffectPolicy,
    cognition_modulation,
    empty_affect,
    update_affect,
    affect_projection,
)


def main() -> int:
    state = empty_affect()

    policy = AffectPolicy(
        persistence=0.6,
        influence_gain=0.7,
    )

    rupture = AffectInfluence(
        source_ref="experience:rupture",
        valence=-0.8,
        arousal=0.9,
        threat=0.8,
        safety=-0.7,
        attachment=0.6,
        curiosity=0.2,
        unresolved=0.9,
        strength=1.0,
        causal_refs=(
            "relationship:alpha",
        ),
    )

    state = update_affect(
        state,
        (rupture,),
        policy=policy,
    )

    assert state.valence < 0.0
    assert state.arousal > 0.0
    assert state.threat > 0.0
    assert state.safety == 0.0
    assert state.attachment > 0.0
    assert state.unresolved > 0.0

    assert (
        "experience:rupture"
        in state.causal_refs
    )

    modulation = (
        cognition_modulation(
            state
        )
    )

    assert (
        modulation[
            "threat_attention"
        ]
        > 0.0
    )

    assert (
        modulation[
            "defensive_pressure"
        ]
        > 0.0
    )

    repair = AffectInfluence(
        source_ref="experience:repair",
        valence=0.8,
        arousal=-0.3,
        threat=-0.7,
        safety=0.9,
        attachment=0.8,
        curiosity=0.5,
        unresolved=-0.8,
        strength=1.0,
        causal_refs=(
            "relationship:alpha",
        ),
    )

    repaired = update_affect(
        state,
        (repair,),
        policy=policy,
    )

    assert (
        repaired.safety
        > state.safety
    )

    assert (
        repaired.threat
        < state.threat
    )

    assert (
        repaired.unresolved
        < state.unresolved
    )

    assert (
        repaired.attachment
        > state.attachment
    )

    assert (
        "experience:rupture"
        in repaired.causal_refs
    )

    assert (
        "experience:repair"
        in repaired.causal_refs
    )

    projection = (
        affect_projection(
            repaired
        )
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

    assert math.isclose(
        projection[
            "state"
        ]["safety"],
        repaired.safety,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
