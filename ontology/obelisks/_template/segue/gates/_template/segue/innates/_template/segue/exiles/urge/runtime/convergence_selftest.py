from __future__ import annotations

from .convergence import project


def main() -> None:
    candidates = [
        {
            "id": "alpha",
            "text": (
                "semantic anchor "
                "stable meaning"
            ),
        },
        {
            "id": "beta",
            "text": (
                "semantic anchor "
                "coherent meaning"
            ),
        },
        {
            "id": "gamma",
            "text": (
                "semantic anchor "
                "stable context"
            ),
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
        "consensus"
    ][
        "universal_tokens"
    ] == [
        "anchor",
        "semantic",
    ]

    assert first[
        "anchor"
    ][
        "id"
    ] == "alpha"

    assert first[
        "historical_kernel"
    ][
        "quirk_execution"
    ] is True

    assert first[
        "boundaries"
    ][
        "declares_truth"
    ] is False

    assert first[
        "boundaries"
    ][
        "mutates_canon"
    ] is False

    assert len(
        first[
            "pairwise"
        ]
    ) == 3

    print(
        "urge convergence: ok"
    )


if __name__ == "__main__":
    main()
