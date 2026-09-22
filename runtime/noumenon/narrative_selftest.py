import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.narrative import (
    NarrativeClaim,
    autobiographical_compression,
    establish_narrative,
    narrative_drift,
    narrative_projection,
    revise_narrative,
)


def main() -> int:
    original = NarrativeClaim(
        claim_ref="claim:trust",
        narrative_class="rupture",
        statement=(
            "trust was damaged"
        ),
        confidence=0.9,
        causal_refs=(
            "experience:rupture",
        ),
        evidence_refs=(
            "evidence:rupture",
        ),
    )

    unresolved = NarrativeClaim(
        claim_ref="claim:uncertainty",
        narrative_class="uncertain",
        statement=(
            "the relationship remains "
            "unresolved"
        ),
        confidence=0.7,
        causal_refs=(
            "residue:relationship",
        ),
    )

    narrative = establish_narrative(
        "noumenon:test",
        (
            original,
            unresolved,
        ),
        causal_refs=(
            "state:initial",
        ),
    )

    repaired = NarrativeClaim(
        claim_ref="claim:repair",
        narrative_class="repair",
        statement=(
            "repair changed the current "
            "relationship"
        ),
        confidence=0.8,
        causal_refs=(
            "experience:repair",
        ),
    )

    retained = NarrativeClaim(
        claim_ref="claim:trust",
        narrative_class=(
            "reinterpretation"
        ),
        statement=(
            "trust was damaged and later "
            "partially repaired"
        ),
        confidence=0.9,
        causal_refs=(
            "experience:rupture",
            "experience:repair",
        ),
    )

    narrative = revise_narrative(
        narrative,
        (
            retained,
            repaired,
        ),
        causal_refs=(
            "meaning:revision",
        ),
    )

    assert (
        len(narrative.layers)
        == 2
    )

    assert (
        narrative.current
        .predecessor_ref
        == narrative.layers[0].id
    )

    drift = narrative_drift(
        narrative.layers[0],
        narrative.layers[1],
    )

    assert (
        "claim:trust"
        in drift.retained_claim_refs
    )

    assert (
        "claim:repair"
        in drift.added_claim_refs
    )

    assert (
        "claim:uncertainty"
        in drift.omitted_claim_refs
    )

    compression = (
        autobiographical_compression(
            narrative
        )
    )

    trust_claim = next(
        item
        for item
        in compression["claims"]
        if (
            item["claim_ref"]
            == "claim:trust"
        )
    )

    assert (
        trust_claim["appearances"]
        == 2
    )

    assert (
        compression[
            "compression_erased_history"
        ]
        is False
    )

    projection = (
        narrative_projection(
            narrative
        )
    )

    assert (
        projection[
            "self_description_is_causal_truth"
        ]
        is False
    )

    assert (
        projection[
            "contradictions_may_persist"
        ]
        is True
    )

    assert (
        projection[
            "reinterpretation_erases_history"
        ]
        is False
    )

    assert (
        projection[
            "history_erased"
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
