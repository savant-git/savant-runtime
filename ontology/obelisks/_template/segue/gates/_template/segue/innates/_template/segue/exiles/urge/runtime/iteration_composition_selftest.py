from __future__ import annotations

from .iteration import (
    assessment,
    criterion,
    job,
    policy,
    proposal,
)
from .iteration_composition import (
    project,
)


def _evaluate(
    payload,
    context,
):
    del context

    return assessment(
        scores={
            "clarity": payload[
                "clarity"
            ],
            "distinctiveness": payload[
                "distinctiveness"
            ],
            "scalability": payload[
                "scalability"
            ],
        },
        findings=(
            "fixture assessment",
        ),
        evidence=(
            "selftest",
        ),
    )


def _revise(
    payload,
    pressure,
):
    gaps = pressure.get(
        "gaps",
        (),
    )

    primary = (
        gaps[0][
            "criterion"
        ]
        if gaps
        else "clarity"
    )

    proposals = []

    for index, delta in enumerate(
        (
            0.07,
            0.04,
            0.02,
        )
    ):
        revised = dict(
            payload
        )

        revised[
            primary
        ] = min(
            1.0,
            revised[
                primary
            ]
            + delta,
        )

        for key in revised:
            if key != primary:
                revised[
                    key
                ] = min(
                    1.0,
                    revised[
                        key
                    ]
                    + (
                        delta
                        / 2.0
                    ),
                )

        proposals.append(
            proposal(
                payload=revised,
                rationale=(
                    f"apply pressure to "
                    f"{primary}",
                ),
                provenance=(
                    f"selftest:branch:{index}",
                ),
            )
        )

    return proposals


def run() -> dict:
    work = job(
        id=(
            "job:urge:selftest:"
            "composition"
        ),
        objective=(
            "improve a design candidate"
        ),
        payload={
            "clarity": 0.62,
            "distinctiveness": 0.58,
            "scalability": 0.70,
        },
        criteria=(
            criterion(
                id="clarity",
                weight=1.0,
                target=0.82,
            ),
            criterion(
                id="distinctiveness",
                weight=1.2,
                target=0.82,
            ),
            criterion(
                id="scalability",
                weight=1.0,
                target=0.82,
            ),
        ),
        provenance=(
            "urge:composition:selftest",
        ),
    )

    result = project(
        work,
        evaluator=_evaluate,
        reviser=_revise,
        run_policy=policy(
            max_cycles=8,
            branch_factor=3,
            min_improvement=0.001,
            target_score=0.80,
            patience=3,
            max_candidates=25,
            max_failures=2,
            preserve_alternates=3,
        ),
    )

    assert (
        result[
            "authority_effect"
        ]
        == "none"
    )

    assert result[
        "iteration"
    ][
        "best"
    ][
        "assessment"
    ][
        "score"
    ] >= 0.80

    assert (
        result[
            "lineage"
        ][
            "iteration_digest"
        ]
        == result[
            "iteration"
        ][
            "digest"
        ]
    )

    assert (
        result[
            "boundaries"
        ][
            "creates_authority"
        ]
        is False
    )

    return result


if __name__ == "__main__":
    result = run()

    print(
        result[
            "digest"
        ]
    )
