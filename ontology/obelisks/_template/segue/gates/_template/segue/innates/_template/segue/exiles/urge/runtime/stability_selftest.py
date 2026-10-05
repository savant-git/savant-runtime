from __future__ import annotations

from .convergence import (
    project as converge,
)
from .stability import (
    project as stabilize,
)


def main() -> None:
    convergence = converge(
        [
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
    )

    first = stabilize(
        convergence
    )

    second = stabilize(
        convergence
    )

    assert first[
        "digest"
    ] == second[
        "digest"
    ]

    assert first[
        "source_digest"
    ] == convergence[
        "digest"
    ]

    assert first[
        "anchor_id"
    ] == convergence[
        "anchor"
    ][
        "id"
    ]

    assert first[
        "authority_effect"
    ] == "none"

    assert first[
        "projection_only"
    ] is True

    assert (
        0.0
        <= first[
            "signals"
        ][
            "stability"
        ]
        <= 1.0
    )

    assert first[
        "boundaries"
    ][
        "changes_anchor"
    ] is False

    assert first[
        "boundaries"
    ][
        "declares_truth"
    ] is False

    print(
        "urge convergence stability: ok"
    )


if __name__ == "__main__":
    main()
