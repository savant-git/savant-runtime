import sys

sys.path.insert(0, "/root/savant-runtime")

from runtime.noumenon.cognition import (
    opus_request,
    underscore_request,
)
from runtime.noumenon.dynamics import (
    DimensionDynamics,
    DormantDisposition,
    DynamicsProfile,
    IdentityAttractor,
    IdentityRepulsor,
    activate_dormant,
    developmental_conservation_check,
    dormant_pressure,
    homeostatic_pressure,
)
from runtime.noumenon.relationship import (
    RelationshipProjection,
    consequence_candidate,
)
from runtime.noumenon.state import (
    NoumenonState,
    empty_state,
)


def main() -> int:
    state = empty_state(
        "advanced-selftest"
    )

    state = NoumenonState(
        noumenon_id=state.noumenon_id,
        predecessor_id=None,
        succession_status="unknown",
        generation=0,
        dimensions={
            "trust": 0.2,
            "curiosity": 0.4,
        },
    )

    profile = DynamicsProfile(
        dimensions={
            "trust": DimensionDynamics(
                inertia=0.7,
                plasticity=0.4,
                elasticity=0.6,
                bandwidth=0.5,
                threshold=0.1,
            )
        },
        attractors=(
            IdentityAttractor(
                dimension="curiosity",
                center=0.7,
                strength=0.5,
                evidence_refs=(
                    "evidence:curiosity",
                ),
            ),
        ),
        repulsors=(
            IdentityRepulsor(
                dimension="trust",
                center=-0.8,
                strength=0.4,
                evidence_refs=(
                    "evidence:trust",
                ),
            ),
        ),
        dormant=(
            DormantDisposition(
                dimension="trust",
                value=-0.2,
                activation_refs=(
                    "context:threat",
                ),
                evidence_refs=(
                    "evidence:dormant",
                ),
            ),
        ),
    )

    pressure = homeostatic_pressure(
        state,
        profile,
    )

    assert "curiosity" in pressure
    assert "trust" in pressure

    activated = activate_dormant(
        profile,
        context_refs=(
            "context:threat",
        ),
    )

    assert activated[0].active

    dormant = dormant_pressure(
        activated
    )

    assert dormant["trust"] == -0.2

    conservation = (
        developmental_conservation_check(
            proposed_deltas={
                "trust": 0.2,
            },
            causal_refs=(
                "experience:selftest",
            ),
            significance={
                "personal": 0.8,
            },
        )
    )

    assert conservation["accepted"]

    rejected_conservation = (
        developmental_conservation_check(
            proposed_deltas={
                "trust": 0.8,
            },
            causal_refs=(),
            significance={
                "personal": 0.1,
            },
        )
    )

    assert not rejected_conservation[
        "accepted"
    ]

    relationship = RelationshipProjection(
        subject_id="self:a",
        object_id="self:b",
        dimensions={
            "trust": 0.4,
            "respect": 0.6,
            "grievance": 0.2,
        },
        shared_history_refs=(
            "episode:shared",
        ),
        evidence_refs=(
            "evidence:relationship",
        ),
    )

    relationship_candidate = (
        consequence_candidate(
            relationship,
            deltas={
                "trust": -0.1,
                "grievance": 0.1,
            },
            causal_refs=(
                "experience:relationship",
            ),
        )
    )

    assert (
        relationship_candidate[
            "subject_id"
        ]
        == "self:a"
    )

    assert (
        relationship_candidate[
            "object_id"
        ]
        == "self:b"
    )

    reflection = opus_request(
        state,
        "reflect",
        subject_refs=(
            "experience:selftest",
        ),
        evidence_refs=(
            "evidence:selftest",
        ),
        constraints={
            "preserve_uncertainty": True,
        },
    )

    assert reflection.target == "opus"
    assert (
        reflection.contract
        == "noumenon.reflect"
    )

    divergence = underscore_request(
        state,
        problem_ref=(
            "problem:self-understanding"
        ),
        candidate_refs=(
            "candidate:one",
            "candidate:two",
        ),
        evidence_refs=(
            "evidence:selftest",
        ),
    )

    assert (
        divergence.target
        == "underscore"
    )

    assert (
        divergence.payload[
            "requirements"
        ][
            "novelty_is_authority"
        ]
        is False
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
