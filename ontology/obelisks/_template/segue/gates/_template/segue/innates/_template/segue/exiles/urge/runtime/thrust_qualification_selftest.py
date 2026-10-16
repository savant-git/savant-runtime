from __future__ import annotations

import json

from .thrust_qualification import (
    execute,
)


baseline_image = (
    "data:image/png;base64,"
    "c2F2YW50LWJhc2VsaW5l"
)


def candidate_factory(
    request,
):
    rigor = int(
        request[
            "rigor"
        ]
    )

    return {
        "image": (
            "data:image/png;base64,"
            + (
                "c2F2YW50LXJpZ29yLQ=="
            )
            + str(
                rigor
            )
        ),
        "rigor":
            rigor,
    }


def evaluator(
    request,
):
    rigor = int(
        request[
            "rigor"
        ]
    )

    qualifies = (
        rigor % 2 == 0
    )

    improvement = (
        18.0
        if qualifies
        else 9.0
    )

    result = {
        "qualifies_as_thrust":
            qualifies,
        "verdict":
            (
                "thrust"
                if qualifies
                else (
                    "rigor-rejected-improvement"
                )
            ),
        "invariant_failures":
            [],
        "quantification": {
            "aggregate": {
                "conservative_improvement_percent":
                    improvement,
                "qualification_margin_percent":
                    improvement
                    - 15.0,
            },
        },
    }

    result[
        "digest"
    ] = (
        "evaluation-"
        + str(
            rigor
        )
    )

    return result


def main() -> int:
    events = []

    first = execute(
        baseline=baseline_image,
        requested_thrusts=3,
        target_improvement_percent=15,
        weights={
            "artistic_quality": 1,
            "sophistication": 1,
        },
        rigor_budget=8,
        candidate_factory=(
            candidate_factory
        ),
        evaluator=evaluator,
        on_rigor=events.append,
    )

    second = execute(
        baseline=baseline_image,
        requested_thrusts=3,
        target_improvement_percent=15,
        weights={
            "artistic_quality": 1,
            "sophistication": 1,
        },
        rigor_budget=8,
        candidate_factory=(
            candidate_factory
        ),
        evaluator=evaluator,
    )

    accepted_rigors = [
        item[
            "source_rigor"
        ]
        for item
        in first[
            "thrusts"
        ]
    ]

    rejected = [
        item
        for item
        in first[
            "history"
        ]
        if not item[
            "accepted"
        ]
    ]

    checks = {
        "deterministic":
            (
                first[
                    "digest"
                ]
                == second[
                    "digest"
                ]
            ),
        "complete":
            first[
                "complete"
            ],
        "three_thrusts":
            first[
                "completed_thrusts"
            ] == 3,
        "six_rigors":
            first[
                "rigors_attempted"
            ] == 6,
        "accepted_are_even":
            accepted_rigors
            == [
                2,
                4,
                6,
            ],
        "rejections_preserved":
            len(
                rejected
            ) == 3,
        "events_emitted":
            len(
                events
            ) == 6,
        "lineage_preserved":
            first[
                "lineage"
            ][
                "rejected_rigors_preserved"
            ],
        "thrust_becomes_baseline":
            first[
                "lineage"
            ][
                "next_baseline_is_last_thrust"
            ],
        "bounded":
            first[
                "rigors_attempted"
            ]
            <= first[
                "rigor_budget"
            ],
    }

    output = {
        "ok":
            all(
                checks.values()
            ),
        "schema":
            first[
                "schema"
            ],
        "state":
            first[
                "state"
            ],
        "requested_thrusts":
            first[
                "requested_thrusts"
            ],
        "completed_thrusts":
            first[
                "completed_thrusts"
            ],
        "rigors_attempted":
            first[
                "rigors_attempted"
            ],
        "accepted_rigors":
            accepted_rigors,
        "checks":
            checks,
    }

    print(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if output[
            "ok"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
