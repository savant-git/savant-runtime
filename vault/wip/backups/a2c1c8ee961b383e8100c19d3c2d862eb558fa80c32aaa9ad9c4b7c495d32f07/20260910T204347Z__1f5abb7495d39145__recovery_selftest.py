import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.development import (
    PossibleSelf,
    SelfExplanation,
)
from runtime.noumenon.dynamics import (
    DimensionDynamics,
    DynamicsProfile,
)
from runtime.noumenon.projection import (
    developmental_projection,
    introspective_projection,
    possible_self_ecology,
    self_triptych,
)
from runtime.noumenon.recovery import (
    ContinuityEvidence,
    ContinuityQuorum,
    evaluate_quorum,
    fork_classification,
    recovery_receipt,
)
from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    Significance,
    TransitionCandidate,
    empty_state,
)


def main() -> int:
    root = empty_state(
        "recovery-selftest"
    )

    transition = TransitionCandidate(
        predecessor=root,
        experience=Experience(
            id="experience:one",
            observed=True,
            owned=True,
        ),
        significance=Significance(
            dimensions={
                "personal": 0.8,
            }
        ),
        consequences=(
            DevelopmentalConsequence(
                dimension="trust",
                delta=0.2,
                causal_refs=(
                    "experience:one",
                ),
            ),
        ),
    )

    successor = transition.successor()

    quorum = ContinuityQuorum(
        lineage=(
            ContinuityEvidence(
                kind="lineage",
                ref="lineage:one",
            ),
        ),
        autobiography=(
            ContinuityEvidence(
                kind="autobiography",
                ref="episode:one",
            ),
        ),
        relationships=(
            ContinuityEvidence(
                kind="relationship",
                ref="relationship:one",
            ),
        ),
        significance_history=(
            ContinuityEvidence(
                kind="significance",
                ref="significance:one",
            ),
        ),
        identity_ancestry=(
            ContinuityEvidence(
                kind="identity",
                ref=root.noumenon_id,
            ),
        ),
        integrity_receipts=(
            ContinuityEvidence(
                kind="receipt",
                ref="receipt:one",
            ),
        ),
    )

    decision = evaluate_quorum(
        quorum,
        predecessor=root,
        candidate=successor,
    )

    assert (
        decision.status
        == "continuous"
    )

    assert decision.score > 0.0

    receipt = recovery_receipt(
        decision,
        authority_refs=(
            "authority:selftest",
        ),
        evidence_refs=(
            "evidence:selftest",
        ),
    )

    assert receipt[
        "integrity_digest"
    ]

    alternate = TransitionCandidate(
        predecessor=root,
        experience=Experience(
            id="experience:two",
            observed=True,
            owned=True,
        ),
        significance=Significance(
            dimensions={
                "personal": 0.7,
            }
        ),
        consequences=(
            DevelopmentalConsequence(
                dimension="trust",
                delta=-0.2,
                causal_refs=(
                    "experience:two",
                ),
            ),
        ),
    ).successor()

    forks = fork_classification(
        (
            successor,
            alternate,
        )
    )

    assert len(
        forks["forks"]
    ) == 1

    assert (
        forks["forks"][0][
            "status"
        ]
        == "branched"
    )

    explanation = SelfExplanation(
        state_digest=(
            successor.state_digest
        ),
        claim=(
            "trust may have changed"
        ),
        confidence=0.5,
        evidence_refs=(
            "experience:one",
        ),
        alternatives=(
            "another cause may contribute",
        ),
    )

    introspection = (
        introspective_projection(
            successor,
            (explanation,),
        )
    )

    assert (
        introspection[
            "self_knowledge_is_fallible"
        ]
        is True
    )

    ecology = possible_self_ecology(
        successor,
        (
            PossibleSelf(
                kind="ideal",
                dimensions={
                    "trust": 0.5,
                },
                confidence=0.4,
            ),
            PossibleSelf(
                kind="feared",
                dimensions={
                    "trust": -0.8,
                },
                confidence=0.2,
            ),
        ),
    )

    assert len(
        ecology["possible_selves"]
    ) == 2

    triptych = self_triptych(
        successor,
        claimed_dimensions={
            "trust": 0.1,
        },
        explanation_refs=(
            explanation.id,
        ),
        confidence={
            "trust": 0.5,
        },
        evidence_refs=(
            "experience:one",
        ),
    )

    assert (
        triptych["phenomenal"][
            "dimensions"
        ]["trust"]
        == 0.1
    )

    assert (
        triptych["causal"][
            "dimensions"
        ]["trust"]
        == 0.2
    )

    profile = DynamicsProfile(
        dimensions={
            "trust": (
                DimensionDynamics(
                    inertia=0.5,
                    plasticity=0.5,
                    elasticity=0.5,
                    bandwidth=0.5,
                    threshold=0.1,
                )
            )
        }
    )

    projection = (
        developmental_projection(
            successor,
            profile,
            unresolved_refs=(
                "question:selftest",
            ),
        )
    )

    assert (
        projection["state"][
            "noumenon_id"
        ]
        == successor.noumenon_id
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
