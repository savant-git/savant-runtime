from __future__ import annotations

import json

from .improvement_quantification import (
    adaptive_rigor_budget,
    quantify,
    ui_projection,
)


def _judge(
    judge_id: str,
    baseline_offset: float,
    candidate_offset: float,
) -> dict:
    dimensions = (
        "artistic_quality",
        "sophistication",
        "concept_novelty",
        "distinctiveness",
        "brief_alignment",
        "composition",
        "visual_coherence",
        "legibility",
        "scalability",
        "reproduction",
        "memorability",
    )

    return {
        "id":
            judge_id,
        "provider":
            "selftest",
        "model":
            "deterministic-fixture",
        "confidence":
            0.9,
        "scores": {
            dimension: {
                "baseline":
                    60
                    + baseline_offset,
                "candidate":
                    84
                    + candidate_offset,
            }
            for dimension
            in dimensions
        },
    }


def main() -> int:
    weights = {
        "artistic_quality": 1,
        "sophistication": 1,
        "concept_novelty": 1,
        "distinctiveness": 1,
        "brief_alignment": 1,
        "composition": 1,
        "visual_coherence": 1,
        "legibility": 1,
        "scalability": 1,
        "reproduction": 1,
        "memorability": 1,
    }

    judges = [
        _judge(
            "judge-a",
            0,
            0,
        ),
        _judge(
            "judge-b",
            1,
            -1,
        ),
        _judge(
            "judge-c",
            -1,
            1,
        ),
    ]

    first = quantify(
        target_improvement_percent=15,
        judges=judges,
        weights=weights,
    )

    second = quantify(
        target_improvement_percent=15,
        judges=judges,
        weights=weights,
    )

    ui = ui_projection()

    checks = {
        "deterministic":
            first == second,
        "qualifies":
            first[
                "qualifies_as_thrust"
            ],
        "kind_is_thrust":
            first[
                "kind"
            ] == "thrust",
        "target_is_15":
            first[
                "target_improvement_percent"
            ] == 15.0,
        "dimensions_present":
            len(
                first[
                    "dimensions"
                ]
            ) == len(
                weights
            ),
        "no_hard_gate_failure":
            not first[
                "hard_gate_failures"
            ],
        "ui_uses_rigor":
            ui[
                "terminology"
            ][
                "raw_attempt"
            ] == "rigor",
        "ui_uses_thrust":
            ui[
                "terminology"
            ][
                "accepted_iteration"
            ] == "thrust",
        "ui_uses_praxi":
            ui[
                "terminology"
            ][
                "sessions"
            ] == "praxi",
        "budget_bounded":
            (
                1
                <= adaptive_rigor_budget(
                    requested_thrusts=8,
                    target_improvement_percent=15,
                )
                <= 2000
            ),
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
        "verdict":
            first[
                "verdict"
            ],
        "improvement_percent":
            first[
                "aggregate"
            ][
                "conservative_improvement_percent"
            ],
        "qualification_margin":
            first[
                "aggregate"
            ][
                "qualification_margin_percent"
            ],
        "rigor_budget":
            adaptive_rigor_budget(
                requested_thrusts=8,
                target_improvement_percent=15,
            ),
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
