from __future__ import annotations

from .convergence import project
from .convergence_policy import (
    convergence_policy_error,
    interpret,
    normalize,
)
from .stability import (
    project as project_stability,
)


def main() -> None:
    convergence = project(
        [
            {
                "id": "a",
                "text": (
                    "alpha beta gamma"
                ),
            },
            {
                "id": "b",
                "text": (
                    "alpha beta delta"
                ),
            },
            {
                "id": "c",
                "text": (
                    "alpha beta gamma"
                ),
            },
        ]
    )

    stability = project_stability(
        convergence
    )

    default_policy_a = normalize()
    default_policy_b = normalize()

    assert (
        default_policy_a[
            "digest"
        ]
        == default_policy_b[
            "digest"
        ]
    )

    assert (
        default_policy_a[
            "authority_effect"
        ]
        == "none"
    )

    assert (
        default_policy_a[
            "boundaries"
        ][
            "creates_authority"
        ]
        is False
    )

    custom_policy = {
        "stable": 0.6,
        "ambiguous": 0.8,
        "strongly_separated": 0.1,
    }

    result_a = interpret(
        stability,
        policy=custom_policy,
    )

    result_b = interpret(
        stability,
        policy=custom_policy,
    )

    assert (
        result_a[
            "digest"
        ]
        == result_b[
            "digest"
        ]
    )

    assert (
        result_a[
            "source_digest"
        ]
        == stability[
            "digest"
        ]
    )

    assert (
        result_a[
            "thresholds"
        ][
            "stable"
        ]
        == 0.6
    )

    assert (
        result_a[
            "authority_effect"
        ]
        == "none"
    )

    assert (
        result_a[
            "boundaries"
        ][
            "declares_truth"
        ]
        is False
    )

    failed = False

    try:
        normalize(
            {
                "unknown": 0.5,
            }
        )

    except convergence_policy_error:
        failed = True

    assert failed

    failed = False

    try:
        normalize(
            {
                "stable": 1.1,
            }
        )

    except convergence_policy_error:
        failed = True

    assert failed

    print(
        "urge convergence policy: ok"
    )


if __name__ == "__main__":
    main()
