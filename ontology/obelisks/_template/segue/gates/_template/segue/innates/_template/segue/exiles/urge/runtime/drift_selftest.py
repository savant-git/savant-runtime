from __future__ import annotations

from .composition import (
    project as compose,
)
from .drift import (
    project as project_drift,
)


def main() -> None:
    previous = compose(
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
        ]
    )

    current = compose(
        [
            {
                "id": "alpha",
                "text": (
                    "semantic anchor "
                    "stable context"
                ),
            },
            {
                "id": "gamma",
                "text": (
                    "semantic context "
                    "coherent focus"
                ),
            },
        ]
    )

    first = project_drift(
        previous,
        current,
    )

    second = project_drift(
        previous,
        current,
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
        "changed"
    ] is True

    assert (
        first[
            "semantic_drift"
        ] > 0.0
    )

    assert first[
        "lineage"
    ][
        "previous_digest"
    ] == previous[
        "digest"
    ]

    assert first[
        "lineage"
    ][
        "current_digest"
    ] == current[
        "digest"
    ]

    assert first[
        "boundaries"
    ][
        "declares_regression"
    ] is False

    assert first[
        "boundaries"
    ][
        "declares_truth"
    ] is False

    unchanged = project_drift(
        previous,
        previous,
    )

    assert unchanged[
        "semantic_drift"
    ] == 0.0

    assert unchanged[
        "changed"
    ] is False

    print(
        "urge convergence drift: ok"
    )


if __name__ == "__main__":
    main()
