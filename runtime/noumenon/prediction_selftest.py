import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.prediction import (
    Expectation,
    prediction_error,
    update_expectation,
)


def main() -> int:
    expectation = Expectation(
        subject_ref="relationship:alpha",
        dimensions={
            "reliability": 0.8,
            "safety": 0.7,
        },
        confidence=0.9,
        causal_refs=(
            "experience:history",
        ),
    )

    error = prediction_error(
        expectation,
        observed_ref=(
            "experience:unexpected"
        ),
        observed_dimensions={
            "reliability": -0.4,
            "safety": 0.1,
        },
    )

    assert math.isclose(
        error.errors["reliability"],
        -1.2,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert math.isclose(
        error.errors["safety"],
        -0.6,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert error.surprise > 0.0

    assert (
        error.curiosity_pressure
        > 0.0
    )

    assert (
        error.projection()[
            "authoritative"
        ]
        is False
    )

    updated = update_expectation(
        expectation,
        observed_dimensions={
            "reliability": -0.4,
            "safety": 0.1,
        },
        learning_rate=0.25,
        causal_refs=(
            "experience:unexpected",
        ),
        evidence_refs=(
            "evidence:unexpected",
        ),
    )

    assert math.isclose(
        updated.dimensions[
            "reliability"
        ],
        0.5,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert math.isclose(
        updated.dimensions["safety"],
        0.55,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert (
        expectation.id
        in updated.causal_refs
    )

    assert (
        "experience:unexpected"
        in updated.causal_refs
    )

    assert (
        expectation.dimensions[
            "reliability"
        ]
        == 0.8
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
