import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.affect import (
    AffectInfluence,
    empty_affect,
    update_affect,
)
from runtime.noumenon.coherence import (
    CoherenceClaim,
    coherence_projection,
)
from runtime.noumenon.integration import (
    mechanism_projection,
)
from runtime.noumenon.integration_runtime import (
    advance_integration,
    establish_integration,
    runtime_projection,
    validate_transition,
)
from runtime.noumenon.path_dependence import (
    PathEvent,
    path_projection,
)
from runtime.noumenon.prediction import (
    Expectation,
    prediction_error,
)
from runtime.noumenon.salience import (
    SalienceSignal,
    score_salience,
)
from runtime.noumenon.significance import (
    SignificanceNode,
    SignificancePolicy,
    SignificanceSegue,
    significance_projection,
)
from runtime.noumenon.taste import (
    TasteEvidence,
    taste_projection,
)
from runtime.noumenon.tension import (
    DevelopmentalTension,
    establish_tension,
    tension_projection,
)
from runtime.noumenon.transference import (
    RelationalPattern,
    transference_projection,
)


def main() -> int:
    significance_source = SignificanceNode(
        subject_ref="experience:a",
        significance=0.8,
        causal_refs=(
            "experience:a",
        ),
    )

    significance_target = SignificanceNode(
        subject_ref="meaning:a",
        significance=0.0,
        causal_refs=(
            "experience:a",
        ),
    )

    segue = SignificanceSegue(
        source_ref=(
            significance_source.id
        ),
        target_ref=(
            significance_target.id
        ),
        relation="evokes",
        strength=0.8,
        polarity=1.0,
        causal_refs=(
            "experience:a",
        ),
    )

    significance = significance_projection(
        (
            significance_source,
            significance_target,
        ),
        (
            segue,
        ),
        policy=SignificancePolicy(
            attenuation=0.8,
            maximum_depth=2,
        ),
    )

    affect = update_affect(
        empty_affect(),
        (
            AffectInfluence(
                source_ref="experience:a",
                valence=-0.5,
                arousal=0.6,
                threat=0.4,
                safety=-0.2,
                curiosity=0.3,
                unresolved=0.5,
                attachment=0.0,
                strength=0.8,
                causal_refs=(
                    "experience:a",
                ),
            ),
        ),
    )

    expectation = Expectation(
        subject_ref="event:b",
        dimensions={
            "trust": 0.8,
        },
        confidence=0.9,
        causal_refs=(
            "experience:prior",
        ),
    )

    error = prediction_error(
        expectation,
        observed_ref="event:b",
        observed={
            "trust": -0.4,
        },
        unresolved_dimensions=(
            "trust",
        ),
    )

    salience_signal = SalienceSignal(
        subject_ref="event:b",
        significance=0.8,
        surprise=error.surprise,
        curiosity=(
            error.curiosity_pressure
        ),
        commitment=0.2,
        residue=0.4,
        relational=0.8,
        unresolved=0.7,
        causal_refs=(
            error.id,
        ),
    )

    salience = score_salience(
        salience_signal
    )

    tension_state = establish_tension(
        DevelopmentalTension(
            tension_ref="tension:trust",
            kind="relational",
            pressure=0.8,
            persistence=0.9,
            uncertainty=0.2,
            resolvability=0.7,
            causal_refs=(
                error.id,
            ),
        )
    )

    taste = taste_projection(
        (
            TasteEvidence(
                subject_ref="artifact:a",
                dimension="complexity",
                response=0.7,
                confidence=0.9,
                significance=0.8,
                causal_refs=(
                    "experience:taste-a",
                ),
            ),
            TasteEvidence(
                subject_ref="artifact:b",
                dimension="complexity",
                response=0.8,
                confidence=0.8,
                significance=0.7,
                causal_refs=(
                    "experience:taste-b",
                ),
            ),
        )
    )

    prior_relationship = (
        RelationalPattern(
            relationship_ref=(
                "relationship:prior"
            ),
            dimensions={
                "trust": -0.8,
                "safety": -0.7,
            },
            significance=0.9,
            confidence=0.9,
            causal_refs=(
                "experience:prior-rupture",
            ),
        )
    )

    current_relationship = (
        RelationalPattern(
            relationship_ref=(
                "relationship:current"
            ),
            dimensions={
                "trust": -0.5,
                "safety": -0.4,
            },
            significance=0.7,
            confidence=0.8,
            causal_refs=(
                "experience:current",
            ),
        )
    )

    transference = (
        transference_projection(
            current_relationship,
            (
                prior_relationship,
            ),
        )
    )

    path = path_projection(
        (
            PathEvent(
                event_ref="event:trust",
                dimensions={
                    "trust": 0.8,
                },
                significance=0.9,
                persistence=0.8,
                sequence=0,
                causal_refs=(
                    "experience:trust",
                ),
            ),
            PathEvent(
                event_ref="event:rupture",
                dimensions={
                    "trust": -0.7,
                },
                significance=0.9,
                persistence=0.9,
                sequence=1,
                causal_refs=(
                    "experience:rupture",
                ),
            ),
        ),
        hysteresis_retention=0.8,
    )

    coherence = coherence_projection(
        (
            CoherenceClaim(
                claim_ref="claim:a",
                dimension="trust",
                position=-0.7,
                confidence=0.9,
                significance=0.8,
                causal_refs=(
                    "experience:rupture",
                ),
            ),
            CoherenceClaim(
                claim_ref="claim:b",
                dimension="trust",
                position=0.4,
                confidence=0.7,
                significance=0.6,
                causal_refs=(
                    "experience:repair",
                ),
            ),
        )
    )

    generation_zero = (
        establish_integration(
            noumenon_id=(
                "noumenon:completion-test"
            ),
            generation=0,
            mechanisms=(
                mechanism_projection(
                    "significance",
                    significance,
                    causal_refs=(
                        significance_source.id,
                    ),
                ),
                mechanism_projection(
                    "affect",
                    affect.projection(),
                    causal_refs=(
                        "experience:a",
                    ),
                ),
                mechanism_projection(
                    "prediction",
                    error.projection(),
                    causal_refs=(
                        expectation.id,
                    ),
                ),
                mechanism_projection(
                    "salience",
                    salience.projection(),
                    causal_refs=(
                        salience_signal.id,
                    ),
                ),
                mechanism_projection(
                    "tension",
                    tension_projection(
                        (tension_state,)
                    ),
                    causal_refs=(
                        tension_state
                        .origin.id,
                    ),
                ),
            ),
            causal_refs=(
                "state:0",
            ),
        )
    )

    generation_one = (
        advance_integration(
            generation_zero.integration,
            generation=1,
            mechanisms=(
                mechanism_projection(
                    "significance",
                    significance,
                    causal_refs=(
                        significance_source.id,
                    ),
                ),
                mechanism_projection(
                    "affect",
                    affect.projection(),
                    causal_refs=(
                        "experience:a",
                    ),
                ),
                mechanism_projection(
                    "prediction",
                    error.projection(),
                    causal_refs=(
                        expectation.id,
                    ),
                ),
                mechanism_projection(
                    "salience",
                    salience.projection(),
                    causal_refs=(
                        salience_signal.id,
                    ),
                ),
                mechanism_projection(
                    "tension",
                    tension_projection(
                        (tension_state,)
                    ),
                    causal_refs=(
                        tension_state
                        .origin.id,
                    ),
                ),
                mechanism_projection(
                    "taste",
                    taste,
                    causal_refs=(
                        "experience:taste-a",
                        "experience:taste-b",
                    ),
                ),
                mechanism_projection(
                    "transference",
                    transference,
                    causal_refs=(
                        prior_relationship.id,
                        current_relationship.id,
                    ),
                ),
                mechanism_projection(
                    "path_dependence",
                    path,
                    causal_refs=(
                        "experience:trust",
                        "experience:rupture",
                    ),
                ),
                mechanism_projection(
                    "coherence",
                    coherence,
                    causal_refs=(
                        "experience:rupture",
                        "experience:repair",
                    ),
                ),
            ),
            causal_refs=(
                "state:1",
                "experience:a",
                "event:b",
            ),
        )
    )

    assert validate_transition(
        generation_zero.integration,
        generation_one,
    )

    projection = runtime_projection(
        generation_one
    )

    assert (
        projection[
            "persistent_identity"
        ]
        == "noumenon:completion-test"
    )

    assert projection["generation"] == 1

    assert (
        projection[
            "mechanism_count"
        ]
        == 9
    )

    assert (
        projection[
            "lineage_preserved"
        ]
        is True
    )

    assert (
        projection[
            "mechanisms_remain_derived"
        ]
        is True
    )

    assert (
        projection[
            "authority_remains_external"
        ]
        is True
    )

    assert (
        projection[
            "model_independent"
        ]
        is True
    )

    assert (
        projection[
            "provider_independent"
        ]
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

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
