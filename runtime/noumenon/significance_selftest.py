import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.significance import (
    SignificanceNode,
    SignificancePolicy,
    SignificanceSegue,
    propagate_field,
    propagate_once,
    significance_gradient,
    significance_projection,
)


def main() -> int:
    experience = SignificanceNode(
        subject_ref="experience:rupture",
        significance=1.0,
        causal_refs=(
            "event:rupture",
        ),
    )

    relationship = SignificanceNode(
        subject_ref="relationship:alpha",
        significance=0.0,
    )

    trust = SignificanceNode(
        subject_ref="dimension:trust",
        significance=0.0,
    )

    first = SignificanceSegue(
        source_ref=(
            "experience:rupture"
        ),
        target_ref=(
            "relationship:alpha"
        ),
        relation="affects",
        strength=0.8,
        polarity=-1.0,
    )

    second = SignificanceSegue(
        source_ref=(
            "relationship:alpha"
        ),
        target_ref="dimension:trust",
        relation="conditions",
        strength=0.5,
        polarity=1.0,
    )

    policy = SignificancePolicy(
        attenuation=0.5,
        maximum_depth=2,
    )

    direct = propagate_once(
        experience,
        first,
        policy=policy,
    )

    assert math.isclose(
        direct.propagated_significance,
        -0.4,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    field = propagate_field(
        (
            experience,
            relationship,
            trust,
        ),
        (
            first,
            second,
        ),
        policy=policy,
    )

    assert math.isclose(
        field[
            "experience:rupture"
        ],
        1.0,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert math.isclose(
        field[
            "relationship:alpha"
        ],
        -0.4,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert math.isclose(
        field[
            "dimension:trust"
        ],
        -0.1,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    gradient = significance_gradient(
        field
    )

    assert (
        gradient[0][0]
        == "experience:rupture"
    )

    projection = (
        significance_projection(
            (
                experience,
                relationship,
                trust,
            ),
            (
                first,
                second,
            ),
            policy=policy,
        )
    )

    assert (
        projection[
            "propagation_is_authority"
        ]
        is False
    )

    assert (
        projection[
            "automatic_mutation"
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

    assert experience.id in (
        direct.causal_refs
    )

    assert first.id in (
        direct.causal_refs
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
