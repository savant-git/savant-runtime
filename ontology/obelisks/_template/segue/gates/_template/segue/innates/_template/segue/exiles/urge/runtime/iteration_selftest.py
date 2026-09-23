from __future__ import annotations

from .iteration import (
    assessment,
    criterion,
    engine,
    job,
    policy,
    proposal,
)


def _evaluate(
    payload,
    context,
):
    del context

    return assessment(
        scores={
            "distinctiveness": (
                payload[
                    "distinctiveness"
                ]
            ),
            "legibility": (
                payload[
                    "legibility"
                ]
            ),
            "scalability": (
                payload[
                    "scalability"
                ]
            ),
            "semantic_fit": (
                payload[
                    "semantic_fit"
                ]
            ),
        },
        findings=(
            "deterministic logo-design "
            "iteration fixture",
        ),
        evidence=(
            "selftest",
        ),
    )


def _revise(
    payload,
    pressure,
):
    del pressure

    values = (
        0.08,
        0.04,
        0.02,
    )

    result = []

    for index, delta in enumerate(
        values
    ):
        revised = {
            key: min(
                1.0,
                float(value)
                + delta,
            )
            for key, value in (
                payload.items()
            )
        }

        result.append(
            proposal(
                payload=revised,
                rationale=(
                    "increase weakest "
                    "design dimensions",
                ),
                provenance=(
                    f"selftest:branch:{index}",
                ),
            )
        )

    return result


def run() -> dict:
    work = job(
        id="job:urge:selftest:logo-design",
        objective=(
            "improve a logo candidate "
            "without changing the job "
            "contract"
        ),
        payload={
            "distinctiveness": 0.60,
            "legibility": 0.72,
            "scalability": 0.68,
            "semantic_fit": 0.64,
        },
        criteria=(
            criterion(
                id="distinctiveness",
                weight=1.2,
                target=0.84,
            ),
            criterion(
                id="legibility",
                weight=1.0,
                target=0.90,
                required=True,
            ),
            criterion(
                id="scalability",
                weight=1.0,
                target=0.88,
                required=True,
            ),
            criterion(
                id="semantic_fit",
                weight=1.1,
                target=0.86,
            ),
        ),
        constraints=(
            "preserve job identity",
            "do not create authority",
        ),
        provenance=(
            "urge:iteration:selftest",
        ),
    )

    run_policy = policy(
        max_cycles=8,
        branch_factor=3,
        min_improvement=0.001,
        target_score=0.88,
        patience=2,
        max_candidates=25,
        max_failures=2,
        preserve_alternates=3,
    )

    first = engine(
        evaluator=_evaluate,
        reviser=_revise,
        run_policy=run_policy,
    ).run(
        work
    )

    second = engine(
        evaluator=_evaluate,
        reviser=_revise,
        run_policy=run_policy,
    ).run(
        work
    )

    assert (
        first[
            "digest"
        ]
        == second[
            "digest"
        ]
    )

    assert (
        first[
            "best"
        ][
            "assessment"
        ][
            "score"
        ]
        > _evaluate(
            work.payload,
            {},
        ).scores[
            "distinctiveness"
        ]
    )

    assert (
        first[
            "best"
        ][
            "assessment"
        ][
            "required_met"
        ]
        is True
    )

    assert (
        first[
            "authority_effect"
        ]
        == "none"
    )

    assert (
        first[
            "boundaries"
        ][
            "executes_model"
        ]
        is False
    )

    return first


if __name__ == "__main__":
    result = run()

    print(
        result[
            "digest"
        ]
    )
