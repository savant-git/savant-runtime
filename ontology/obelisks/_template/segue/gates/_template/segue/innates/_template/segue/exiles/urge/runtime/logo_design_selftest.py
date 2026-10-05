from __future__ import annotations

from .iteration import policy
from .job_adapter import execution_boundary
from .logo_design import create_job, run


_criteria = (
    "conceptual_fit",
    "distinctiveness",
    "legibility",
    "scalability",
    "silhouette_strength",
    "reproduction_resilience",
    "memorability",
    "system_extensibility",
)


def _evaluate(request):
    payload = request[
        "payload"
    ]

    return {
        "scores": {
            key: payload[key]
            for key in _criteria
        },
        "findings": [
            "deterministic logo fixture"
        ],
        "evidence": [
            "urge:logo-design:selftest"
        ],
        "metadata": {
            "fixture": True
        },
    }


def _revise(request):
    payload = request[
        "payload"
    ]

    pressure = request[
        "pressure"
    ]

    gaps = pressure.get(
        "gaps",
        ()
    )

    priority = [
        item["criterion"]
        for item in gaps
    ]

    result = []

    for branch, delta in enumerate(
        (
            0.075,
            0.050,
            0.025,
            0.0125,
        )
    ):
        revised = dict(
            payload
        )

        for index, key in enumerate(
            priority
        ):
            multiplier = max(
                0.35,
                1.0
                - (
                    index
                    * 0.10
                ),
            )

            revised[key] = min(
                1.0,
                float(
                    revised[key]
                )
                + (
                    delta
                    * multiplier
                ),
            )

        result.append(
            {
                "payload": revised,
                "rationale": [
                    "apply weighted revision "
                    "pressure to unresolved "
                    "design criteria"
                ],
                "provenance": [
                    (
                        "urge:logo-design:"
                        f"selftest:branch:{branch}"
                    )
                ],
                "metadata": {
                    "fixture": True,
                    "branch": branch,
                },
            }
        )

    return result


def run_selftest():
    initial = {
        "conceptual_fit": 0.61,
        "distinctiveness": 0.57,
        "legibility": 0.73,
        "scalability": 0.69,
        "silhouette_strength": 0.60,
        "reproduction_resilience": 0.66,
        "memorability": 0.58,
        "system_extensibility": 0.62,
    }

    work = create_job(
        job_id=(
            "job:urge:selftest:"
            "logo-design"
        ),
        objective=(
            "evolve the candidate into a "
            "stronger logo while preserving "
            "the brief and constraints"
        ),
        initial_candidate=initial,
        brief={
            "name": "savant",
            "category": (
                "design-development-branding"
            ),
            "case": "lowercase",
        },
        constraints=(
            "preserve lowercase identity",
            "preserve brief",
            "preserve job lineage",
        ),
        provenance=(
            "urge:logo-design:selftest",
        ),
    )

    boundary = execution_boundary(
        evaluate=_evaluate,
        revise=_revise,
        identity=(
            "selftest:deterministic:"
            "logo-design"
        ),
    )

    first = run(
        work=work,
        boundary=boundary,
        run_policy=policy(
            max_cycles=10,
            branch_factor=4,
            min_improvement=0.001,
            target_score=0.88,
            patience=3,
            max_candidates=41,
            max_failures=2,
            preserve_alternates=4,
        ),
    )

    second = run(
        work=work,
        boundary=boundary,
        run_policy=policy(
            max_cycles=10,
            branch_factor=4,
            min_improvement=0.001,
            target_score=0.88,
            patience=3,
            max_candidates=41,
            max_failures=2,
            preserve_alternates=4,
        ),
    )

    assert (
        first["digest"]
        == second["digest"]
    )

    best = first[
        "best_candidate"
    ][
        "assessment"
    ]

    assert (
        best["score"]
        > 0.632
    )

    assert (
        best["required_met"]
        is True
    )

    assert (
        first[
            "boundaries"
        ][
            "executes_model"
        ]
        is False
    )

    assert (
        first[
            "authority_effect"
        ]
        == "none"
    )

    return first


if __name__ == "__main__":
    result = run_selftest()

    print(
        result[
            "digest"
        ]
    )
