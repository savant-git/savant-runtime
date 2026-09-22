import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.integration import (
    compare_integrations,
    integrate,
    integration_digest,
    integration_projection,
    mechanism_projection,
    mechanism_refs,
)


def main() -> int:
    significance = mechanism_projection(
        "significance",
        {
            "schema": (
                "savant://noumenon/"
                "significance-propagation/1"
            ),
            "subject_ref": "experience:a",
            "significance": 0.8,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        },
        causal_refs=(
            "experience:a",
        ),
    )

    affect = mechanism_projection(
        "affect",
        {
            "schema": (
                "savant://noumenon/affect/1"
            ),
            "valence": -0.2,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        },
        causal_refs=(
            "experience:a",
        ),
    )

    tension = mechanism_projection(
        "tension",
        {
            "schema": (
                "savant://noumenon/"
                "developmental-tension/1"
            ),
            "developmental_debt": 0.4,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        },
        causal_refs=(
            "experience:a",
        ),
    )

    first = integrate(
        "noumenon:test",
        1,
        (
            significance,
            affect,
            tension,
        ),
        causal_refs=(
            "state:1",
        ),
    )

    refs = mechanism_refs(first)

    assert refs["significance"] == (
        significance.id
    )

    assert refs["affect"] == affect.id
    assert refs["tension"] == tension.id

    first_digest = integration_digest(
        first
    )

    assert len(first_digest) == 64

    changed_affect = mechanism_projection(
        "affect",
        {
            "schema": (
                "savant://noumenon/affect/1"
            ),
            "valence": 0.3,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        },
        causal_refs=(
            "experience:b",
        ),
    )

    second = integrate(
        "noumenon:test",
        2,
        (
            significance,
            changed_affect,
            tension,
        ),
        causal_refs=(
            "state:2",
        ),
    )

    comparison = compare_integrations(
        first,
        second,
    )

    assert (
        comparison[
            "changed_mechanisms"
        ]
        == ["affect"]
    )

    assert (
        "significance"
        in comparison[
            "retained_mechanisms"
        ]
    )

    assert (
        "tension"
        in comparison[
            "retained_mechanisms"
        ]
    )

    projection = integration_projection(
        second
    )

    assert projection[
        "integration_owner"
    ] == "noumenon"

    assert (
        projection[
            "substance_owners_preserved"
        ]
        is True
    )

    assert (
        projection[
            "authority_transferred"
        ]
        is False
    )

    assert (
        projection[
            "contradictions_preserved"
        ]
        is True
    )

    assert (
        projection[
            "automatic_identity_mutation"
        ]
        is False
    )

    assert (
        projection[
            "model_is_noumenon"
        ]
        is False
    )

    assert (
        projection[
            "provider_is_noumenon"
        ]
        is False
    )

    assert (
        projection[
            "integration_absorbs_authority"
        ]
        is False
    )

    assert (
        projection[
            "experience_equals_identity"
        ]
        is False
    )

    assert (
        projection[
            "development_requires_causal_lineage"
        ]
        is True
    )

    assert (
        projection[
            "same_experience_can_diverge"
        ]
        is True
    )

    assert (
        projection[
            "persistent_individuality_preserved"
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

    assert significance.id in (
        second.causal_refs
    )

    assert changed_affect.id in (
        second.causal_refs
    )

    assert tension.id in (
        second.causal_refs
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
