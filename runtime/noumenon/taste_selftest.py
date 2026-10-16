import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.taste import (
    TasteEvidence,
    taste_drift,
    taste_profile,
    taste_projection,
)


def main() -> int:
    first = TasteEvidence(
        subject_ref="work:a",
        dimension="complexity",
        response=0.8,
        confidence=0.9,
        significance=0.8,
        causal_refs=(
            "experience:a",
        ),
    )

    second = TasteEvidence(
        subject_ref="work:b",
        dimension="complexity",
        response=0.6,
        confidence=0.8,
        significance=0.7,
        causal_refs=(
            "experience:b",
        ),
    )

    aversion = TasteEvidence(
        subject_ref="work:c",
        dimension="sentimentality",
        response=-0.9,
        confidence=0.9,
        significance=0.9,
        causal_refs=(
            "experience:c",
        ),
    )

    profile = taste_profile(
        (
            first,
            second,
            aversion,
        )
    )

    assert (
        profile["complexity"]
        .preference
        > 0.0
    )

    assert (
        profile["sentimentality"]
        .preference
        < 0.0
    )

    assert (
        profile["complexity"]
        .evidence_count
        == 2
    )

    changed = TasteEvidence(
        subject_ref="work:d",
        dimension="complexity",
        response=-0.8,
        confidence=1.0,
        significance=1.0,
        causal_refs=(
            "experience:d",
        ),
    )

    successor = taste_profile(
        (
            first,
            second,
            aversion,
            changed,
        )
    )

    drift = taste_drift(
        profile,
        successor,
    )

    assert (
        drift["complexity"]
        < 0.0
    )

    projection = taste_projection(
        (
            first,
            second,
            aversion,
        )
    )

    assert (
        projection[
            "taste_is_inferred"
        ]
        is True
    )

    assert (
        projection[
            "taste_is_authority"
        ]
        is False
    )

    assert (
        projection[
            "single_response_defines_taste"
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
