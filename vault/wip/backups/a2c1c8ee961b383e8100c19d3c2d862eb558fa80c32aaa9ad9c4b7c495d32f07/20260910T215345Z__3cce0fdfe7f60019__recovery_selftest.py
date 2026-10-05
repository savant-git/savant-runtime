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


def successor(
    predecessor,
    *,
    experience_id: str,
    dimension: str,
    delta: float,
):
    return TransitionCandidate(
        predecessor=predecessor,
        experience=Experience(
            id=experience_id,
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
                dimension=dimension,
                delta=delta,
                causal_refs=(
                    experience_id,
                ),
            ),
        ),
    ).successor()


def main() -> int:
    root = empty_state(
        "recovery-selftest"
    )

    first = successor(
        root,
        experience_id="experience:first",
        dimension="trust",
        delta=0.2,
    )

    quorum = ContinuityQuorum(
        evidence=(
            ContinuityEvidence(
                kind="lineage",
                ref=root.state_digest,
                digest=root.state_digest,
            ),
            ContinuityEvidence(
                kind="autobiography",
                ref="autobiography:first",
                digest="autobiography:first",
            ),
            ContinuityEvidence(
                kind="relationships",
                ref="relationships:first",
                digest="relationships:first",
            ),
            ContinuityEvidence(
                kind="commitments",
                ref="commitments:first",
                digest="commitments:first",
            ),
            ContinuityEvidence(
                kind="significance_history",
                ref="significance:first",
                digest="significance:first",
            ),
            ContinuityEvidence(
                kind="identity_ancestry",
                ref=root.state_digest,
                digest=root.state_digest,
            ),
            ContinuityEvidence(
                kind="integrity_receipts",
                ref="receipt:first",
                digest="receipt:first",
            ),
        )
    )

    decision = evaluate_quorum(
        root,
        first,
        quorum,
    )

    assert (
        decision.status
        == "continuous"
    )

    assert (
        decision.candidate_id
        == first.noumenon_id
    )

    assert (
        decision.candidate_state_digest
        == first.state_digest
    )

    receipt = recovery_receipt(
        decision,
        evidence_refs=(
            "evidence:selftest",
        ),
    )

    assert (
        receipt[
            "candidate_state_digest"
        ]
        == first.state_digest
    )

    branch_a = successor(
        root,
        experience_id="experience:branch-a",
        dimension="trust",
        delta=0.4,
    )

    branch_b = successor(
        root,
        experience_id="experience:branch-b",
        dimension="trust",
        delta=-0.4,
    )

    assert (
        branch_a.noumenon_id
        == branch_b.noumenon_id
        == root.noumenon_id
    )

    assert (
        branch_a.state_digest
        != branch_b.state_digest
    )

    forks = fork_classification(
        (
            root,
            branch_a,
            branch_b,
        )
    )

    assert len(
        forks["forks"]
    ) == 1

    fork = forks["forks"][0]

    assert (
        fork[
            "predecessor_state_digest"
        ]
        == root.state_digest
    )

    assert (
        set(
            fork[
                "successor_state_digests"
            ]
        )
        == {
            branch_a.state_digest,
            branch_b.state_digest,
        }
    )

    explanation = SelfExplanation(
        state_digest=(
            first.state_digest
        ),
        claim=(
            "trust may have changed"
        ),
        confidence=0.6,
        evidence_refs=(
            "experience:first",
        ),
        alternatives=(
            "another cause may contribute",
        ),
    )

    explanation_projection = (
        explanation.projection()
    )

    assert (
        explanation_projection[
            "authoritative_causal_access"
        ]
        is False
    )

    introspection = (
        introspective_projection(
            first,
            explanations=(
                explanation,
            ),
        )
    )

    assert isinstance(
        introspection,
        dict,
    )

    possible = (
        PossibleSelf(
            kind="ideal",
            dimensions={
                "trust": 0.5,
            },
            evidence_refs=(
                "evidence:possible",
            ),
            confidence=0.5,
        ),
    )

    ecology = possible_self_ecology(
        first,
        possible,
    )

    assert isinstance(
        ecology,
        dict,
    )

    triptych = self_triptych(
        first,
        phenomenal_dimensions={
            "trust": 0.1,
        },
        historical_dimensions={
            "trust": 0.0,
        },
    )

    assert (
        triptych[
            "causal_self"
        ][
            "dimensions"
        ][
            "trust"
        ]
        == 0.2
    )

    profile = DynamicsProfile(
        dimensions={
            "trust": (
                DimensionDynamics()
            ),
        }
    )

    development = (
        developmental_projection(
            root,
            first,
            profile=profile,
        )
    )

    assert (
        development[
            "successor_state_digest"
        ]
        == first.state_digest
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
