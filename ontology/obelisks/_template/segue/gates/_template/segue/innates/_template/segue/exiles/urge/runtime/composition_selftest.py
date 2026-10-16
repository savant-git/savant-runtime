from __future__ import annotations

from .composition import project


def main() -> None:
    candidates = [
        {
            "id": "alpha",
            "text": (
                "semantic anchor "
                "stable meaning"
            ),
            "provenance": {
                "source": "a",
            },
        },
        {
            "id": "beta",
            "text": (
                "semantic anchor "
                "coherent meaning"
            ),
            "provenance": {
                "source": "b",
            },
        },
        {
            "id": "gamma",
            "text": (
                "semantic anchor "
                "stable context"
            ),
            "provenance": {
                "source": "c",
            },
        },
    ]

    first = project(
        candidates
    )

    second = project(
        candidates
    )

    assert first[
        "digest"
    ] == second[
        "digest"
    ]

    assert first[
        "authority_effect"
    ] == "none"

    assert first[
        "projection_only"
    ] is True

    assert first[
        "convergence"
    ][
        "digest"
    ] == first[
        "lineage"
    ][
        "convergence_digest"
    ]

    assert first[
        "stability"
    ][
        "digest"
    ] == first[
        "lineage"
    ][
        "stability_digest"
    ]

    assert first[
        "lineage"
    ][
        "anchor_id"
    ] == first[
        "convergence"
    ][
        "anchor"
    ][
        "id"
    ]

    assert first[
        "convergence"
    ][
        "anchor"
    ][
        "provenance"
    ] == {
        "source": "a",
    }

    assert first[
        "capabilities"
    ][
        "provenance_preservation"
    ] is True

    assert first[
        "boundaries"
    ][
        "creates_authority"
    ] is False

    print(
        "urge convergence composition: ok"
    )


if __name__ == "__main__":
    main()
