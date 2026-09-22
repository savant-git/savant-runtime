import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.guard import (
    IdentityClaim,
    anti_manipulation_check,
    contradiction_preservation,
    evaluate_identity_claim,
)
from runtime.noumenon.identity import (
    DevelopmentalDebt,
    append_identity_layer,
    debt_pressure,
    empty_palimpsest,
    palimpsest_projection,
    resolve_debt,
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
        "identity-selftest"
    )

    palimpsest = empty_palimpsest(
        root.noumenon_id
    )

    palimpsest = append_identity_layer(
        palimpsest,
        state=root,
        causal_refs=(
            "origin:selftest",
        ),
    )

    transition = TransitionCandidate(
        predecessor=root,
        experience=Experience(
            id="experience:identity",
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
                    "experience:identity",
                ),
            ),
        ),
    )

    successor = transition.successor()

    palimpsest = append_identity_layer(
        palimpsest,
        state=successor,
        causal_refs=(
            "experience:identity",
        ),
    )

    assert len(
        palimpsest.layers
    ) == 2

    assert (
        palimpsest.layers[0].digest
        == palimpsest.layers[
            1
        ].supersedes_ref
    )

    debt = DevelopmentalDebt(
        kind="promise",
        ref="promise:selftest",
        causal_refs=(
            "experience:identity",
        ),
        pressure=0.4,
    )

    assert debt_pressure(
        (debt,)
    ) == 0.4

    resolved = resolve_debt(
        debt,
        resolution_refs=(
            "repair:selftest",
        ),
    )

    assert resolved.resolved

    assert debt_pressure(
        (resolved,)
    ) == 0.0

    projection = (
        palimpsest_projection(
            palimpsest,
            (debt,),
        )
    )

    assert (
        projection[
            "historical_identity_erased"
        ]
        is False
    )

    accepted_claim = IdentityClaim(
        dimension="trust",
        proposed_value=0.3,
        causal_refs=(
            "experience:identity",
        ),
        evidence_refs=(
            "evidence:selftest",
        ),
        authority_refs=(
            "authority:selftest",
        ),
        uncertainty=0.2,
    )

    accepted = (
        evaluate_identity_claim(
            successor,
            accepted_claim,
        )
    )

    assert accepted.accepted

    rejected_claim = IdentityClaim(
        dimension="trust",
        proposed_value=-0.9,
        causal_refs=(),
        uncertainty=0.9,
    )

    rejected = (
        evaluate_identity_claim(
            successor,
            rejected_claim,
        )
    )

    assert not rejected.accepted

    manipulation = (
        anti_manipulation_check(
            evidence_strength=0.5,
            praise_pressure=1.0,
            threat_pressure=1.0,
            intimacy_pressure=1.0,
            guilt_pressure=1.0,
        )
    )

    assert (
        manipulation[
            "social_pressure_authority"
        ]
        == 0.0
    )

    assert (
        manipulation[
            "social_pressure_evidence"
        ]
        == 0.0
    )

    contradiction = (
        contradiction_preservation(
            (
                accepted_claim,
                IdentityClaim(
                    dimension="trust",
                    proposed_value=-0.2,
                    causal_refs=(
                        "experience:other",
                    ),
                ),
            )
        )
    )

    assert len(
        contradiction[
            "contradictions"
        ]
    ) == 1

    assert (
        contradiction[
            "automatic_reconciliation"
        ]
        is False
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
