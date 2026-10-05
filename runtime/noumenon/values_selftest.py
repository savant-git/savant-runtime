import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.values import (
    add_value_evidence,
    empty_profile,
    professed_value,
    revealed_value,
    value_discrepancy,
    value_projection,
)


def main() -> int:
    profile = empty_profile(
        "noumenon:values-selftest"
    )

    profile = add_value_evidence(
        profile,
        value_ref="value:honesty",
        value_class="professed",
        strength=0.9,
        causal_refs=(
            "statement:honesty",
        ),
    )

    profile = add_value_evidence(
        profile,
        value_ref="value:honesty",
        value_class="observed",
        strength=0.4,
        causal_refs=(
            "experience:behavior-a",
        ),
        evidence_refs=(
            "evidence:behavior-a",
        ),
    )

    profile = add_value_evidence(
        profile,
        value_ref="value:honesty",
        value_class="observed",
        strength=0.6,
        causal_refs=(
            "experience:behavior-b",
        ),
        evidence_refs=(
            "evidence:behavior-b",
        ),
    )

    profile = add_value_evidence(
        profile,
        value_ref="value:honesty",
        value_class="aspirational",
        strength=1.0,
        causal_refs=(
            "commitment:honesty",
        ),
    )

    assert math.isclose(
        professed_value(
            profile,
            "value:honesty",
        ),
        0.9,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert math.isclose(
        revealed_value(
            profile,
            "value:honesty",
        ),
        0.5,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    discrepancy = (
        value_discrepancy(
            profile,
            "value:honesty",
        )
    )

    assert discrepancy is not None

    assert math.isclose(
        discrepancy,
        -0.4,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    projection = value_projection(
        profile,
        "value:honesty",
    )

    assert projection[
        "contradiction"
    ]

    assert math.isclose(
        projection["classes"][
            "observed"
        ],
        0.5,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert (
        projection[
            "authoritative"
        ]
        is False
    )

    assert len(
        profile.evidence
    ) == 4

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
