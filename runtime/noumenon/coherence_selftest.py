import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.coherence import (
    CoherenceClaim,
    coherence_field,
    coherence_projection,
    global_coherence,
)


def main() -> int:
    restraint = CoherenceClaim(
        claim_ref="claim:restraint",
        dimension="risk",
        position=-0.8,
        confidence=0.9,
        significance=0.9,
        causal_refs=(
            "experience:restraint",
        ),
    )

    curiosity = CoherenceClaim(
        claim_ref="claim:curiosity",
        dimension="risk",
        position=0.5,
        confidence=0.8,
        significance=0.8,
        causal_refs=(
            "experience:curiosity",
        ),
    )

    compassion = CoherenceClaim(
        claim_ref="claim:compassion",
        dimension="care",
        position=0.9,
        confidence=0.9,
        significance=1.0,
        causal_refs=(
            "experience:care-a",
        ),
    )

    loyalty = CoherenceClaim(
        claim_ref="claim:loyalty",
        dimension="care",
        position=0.8,
        confidence=0.8,
        significance=0.9,
        causal_refs=(
            "experience:care-b",
        ),
    )

    claims = (
        restraint,
        curiosity,
        compassion,
        loyalty,
    )

    field = coherence_field(
        claims
    )

    assert (
        field["risk"].contradiction
        > 0.0
    )

    assert (
        field["risk"].diversity
        > 0.0
    )

    assert (
        field["care"].coherence
        > field["risk"].coherence
    )

    assert (
        -1.0
        <= field["risk"].center
        <= 1.0
    )

    score = global_coherence(
        claims
    )

    assert 0.0 <= score <= 1.0

    projection = coherence_projection(
        claims
    )

    assert (
        projection[
            "contradictions_preserved"
        ]
        is True
    )

    assert (
        projection[
            "diversity_preserved"
        ]
        is True
    )

    assert (
        projection[
            "homogenization_required"
        ]
        is False
    )

    assert (
        projection[
            "coherence_is_authority"
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

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
