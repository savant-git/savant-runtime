from __future__ import annotations

import json
from typing import Any, Mapping

from . import praxis_execution


BASELINE = (
    "data:image/png;base64,"
    "c2F2YW50LWJhc2VsaW5l"
)


def fake_binding(
    *,
    baseline=None,
):
    return {
        "baseline":
            baseline,
    }


def fake_project_renderer(
    *,
    candidate: Mapping[
        str,
        Any,
    ],
    binding: Any,
    context: Mapping[
        str,
        Any,
    ] | None = None,
):
    role = str(
        (
            context
            or {}
        ).get(
            "praxis_role",
            "",
        )
    )

    if role == "seed":
        return {
            "state":
                "projected",
            "image":
                (
                    "data:image/png;base64,"
                    "c2F2YW50LXNlZWQ="
                ),
            "candidate":
                dict(
                    candidate
                ),
        }

    rigor = int(
        (
            context
            or {}
        ).get(
            "rigor",
            0,
        )
    )

    return {
        "state":
            "projected",
        "image": (
            "data:image/png;base64,"
            "c2F2YW50LXJpZ29yLQ=="
            + str(
                rigor
            )
        ),
        "candidate":
            dict(
                candidate
            ),
        "binding":
            binding,
    }


def fake_evaluate_and_quantify(
    *,
    baseline: Any,
    candidate: Any,
    objective: str,
    target_improvement_percent:
        float,
    weights=None,
    constraints=(),
    invariants=(),
):
    candidate_text = str(
        candidate
    )

    rigor = 0

    marker = (
        "c2F2YW50LXJpZ29yLQ=="
    )

    if marker in candidate_text:
        suffix = candidate_text.split(
            marker,
            1,
        )[
            1
        ]

        digits = "".join(
            character
            for character in suffix
            if character.isdigit()
        )

        if digits:
            rigor = int(
                digits
            )

    qualifies = (
        rigor % 2 == 0
        and rigor > 0
    )

    improvement = (
        18.0
        if qualifies
        else 8.0
    )

    return {
        "schema":
            (
                "savant://runtime/urge/"
                "visual-evaluator/fixture"
            ),
        "kind":
            (
                "thrust"
                if qualifies
                else "rigor"
            ),
        "verdict":
            (
                "thrust"
                if qualifies
                else (
                    "rigor-rejected-improvement"
                )
            ),
        "qualifies_as_thrust":
            qualifies,
        "invariant_failures":
            [],
        "quantification": {
            "aggregate": {
                "conservative_improvement_percent":
                    improvement,
                "qualification_margin_percent":
                    (
                        improvement
                        - float(
                            target_improvement_percent
                        )
                    ),
            },
        },
        "digest":
            (
                "fixture-evaluation-"
                + str(
                    rigor
                )
            ),
    }


def _run(
    *,
    baseline,
):
    events = []

    result = praxis_execution.execute(
        objective=(
            "evolve a distinctive "
            "savant logo"
        ),
        logo_name="savant",
        baseline=baseline,
        requested_thrusts=2,
        target_improvement_percent=15,
        weights={
            "artistic_quality":
                1,
            "sophistication":
                1,
        },
        constraints=[
            "remain usable as a logo",
        ],
        invariants=[
            "preserve the savant identity",
        ],
        cliches=[
            "generic ai sparkle",
        ],
        rigor_budget=6,
        on_rigor=events.append,
    )

    return (
        result,
        events,
    )


def main() -> int:
    original_binding = (
        praxis_execution
        .image_renderer_binding
    )

    original_project = (
        praxis_execution
        .project_renderer
    )

    original_evaluator = (
        praxis_execution
        .evaluate_and_quantify
    )

    try:
        praxis_execution.image_renderer_binding = (
            fake_binding
        )

        praxis_execution.project_renderer = (
            fake_project_renderer
        )

        praxis_execution.evaluate_and_quantify = (
            fake_evaluate_and_quantify
        )

        baseline_result, baseline_events = (
            _run(
                baseline=BASELINE
            )
        )

        scratch_result, scratch_events = (
            _run(
                baseline=None
            )
        )

    finally:
        praxis_execution.image_renderer_binding = (
            original_binding
        )

        praxis_execution.project_renderer = (
            original_project
        )

        praxis_execution.evaluate_and_quantify = (
            original_evaluator
        )

    baseline_accepted = [
        item[
            "source_rigor"
        ]
        for item
        in baseline_result[
            "thrusts"
        ]
    ]

    scratch_accepted = [
        item[
            "source_rigor"
        ]
        for item
        in scratch_result[
            "thrusts"
        ]
    ]

    baseline_rejected = [
        item
        for item
        in baseline_result[
            "history"
        ]
        if not item[
            "accepted"
        ]
    ]

    scratch_rejected = [
        item
        for item
        in scratch_result[
            "history"
        ]
        if not item[
            "accepted"
        ]
    ]

    checks = {
        "baseline_complete":
            baseline_result[
                "complete"
            ],
        "scratch_complete":
            scratch_result[
                "complete"
            ],
        "baseline_two_thrusts":
            baseline_result[
                "completed_thrusts"
            ] == 2,
        "scratch_two_thrusts":
            scratch_result[
                "completed_thrusts"
            ] == 2,
        "baseline_four_rigors":
            baseline_result[
                "rigors_attempted"
            ] == 4,
        "scratch_four_rigors":
            scratch_result[
                "rigors_attempted"
            ] == 4,
        "baseline_accepts_even_rigors":
            baseline_accepted
            == [
                2,
                4,
            ],
        "scratch_accepts_even_rigors":
            scratch_accepted
            == [
                2,
                4,
            ],
        "baseline_rejections_preserved":
            len(
                baseline_rejected
            ) == 2,
        "scratch_rejections_preserved":
            len(
                scratch_rejected
            ) == 2,
        "baseline_events_live":
            len(
                baseline_events
            ) == 4,
        "scratch_events_live":
            len(
                scratch_events
            ) == 4,
        "scratch_seed_created":
            (
                scratch_result[
                    "initial_baseline"
                ][
                    "name"
                ]
                == "generated-seed"
            ),
        "provided_baseline_preserved":
            (
                baseline_result[
                    "initial_baseline"
                ][
                    "source"
                ]
                == BASELINE
            ),
        "provider_boundary_preserved":
            (
                baseline_result[
                    "boundaries"
                ][
                    "opus_owns_provider_execution"
                ]
            ),
        "qualification_boundary_preserved":
            (
                baseline_result[
                    "boundaries"
                ][
                    "urge_owns_qualification"
                ]
            ),
        "rejected_rigors_not_baselines":
            (
                baseline_result[
                    "lineage"
                ][
                    "next_baseline_is_last_thrust"
                ]
            ),
        "model_judgment_not_objective_fact":
            (
                not baseline_result[
                    "boundaries"
                ][
                    "model_improvement_is_objective_fact"
                ]
            ),
    }

    output = {
        "ok":
            all(
                checks.values()
            ),
        "schema":
            baseline_result[
                "schema"
            ],
        "baseline": {
            "state":
                baseline_result[
                    "state"
                ],
            "rigors":
                baseline_result[
                    "rigors_attempted"
                ],
            "thrusts":
                baseline_result[
                    "completed_thrusts"
                ],
            "accepted_rigors":
                baseline_accepted,
        },
        "scratch": {
            "state":
                scratch_result[
                    "state"
                ],
            "rigors":
                scratch_result[
                    "rigors_attempted"
                ],
            "thrusts":
                scratch_result[
                    "completed_thrusts"
                ],
            "accepted_rigors":
                scratch_accepted,
            "seed":
                scratch_result[
                    "initial_baseline"
                ][
                    "name"
                ],
        },
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
