from __future__ import annotations

from .workbench_projection import (
    project,
)


def main() -> int:
    iteration = {
        "iteration": {
            "best": {
                "candidate_id": (
                    "candidate:best"
                ),
                "assessment": {
                    "gaps": [
                        {
                            "criterion": (
                                "distinctiveness"
                            ),
                            "pressure": 0.12,
                        }
                    ],
                },
            },
            "alternates": [
                {
                    "candidate_id": (
                        "candidate:alternate"
                    )
                }
            ],
            "lineage": [
                {
                    "cycle": 1,
                    "parent": (
                        "candidate:initial"
                    ),
                    "child": (
                        "candidate:best"
                    ),
                }
            ],
            "metrics": {
                "cycles": 1,
            },
            "stop_reason": (
                "target_reached"
            ),
        }
    }

    creative = {
        "first_frontier": [
            {
                "candidate_id": (
                    "creative:first"
                )
            }
        ],
        "frontier": [
            {
                "candidate_id": (
                    "creative:final"
                )
            }
        ],
        "final_discrimination": {
            "ranked_candidates": []
        },
        "lineage": [
            {
                "stage": "divergence",
                "lens": (
                    "primitive-recomposition"
                ),
                "provider": "provider:test",
                "model": "model:test",
                "opus_lineage": {
                    "owner": (
                        "exile:opus"
                    )
                },
            }
        ],
    }

    logo = {
        "name": "savant",
        "brief_digest": (
            "brief:test"
        ),
        "stress_tests": [
            "monochrome",
            "micro-scale",
        ],
        "renderer_integration": {
            "state": "reserved",
            "renderer": (
                "savant-svg-renderer"
            ),
        },
    }

    first = project(
        iteration=iteration,
        creative=creative,
        logo=logo,
    )

    second = project(
        iteration=iteration,
        creative=creative,
        logo=logo,
    )

    assert (
        first["digest"]
        == second["digest"]
    )

    assert (
        first["status"][
            "renderer"
        ]
        == "reserved"
    )

    assert (
        first["ownership"][
            "provider_orchestration"
        ]
        == "exile:opus"
    )

    assert (
        first["ownership"][
            "structural_discrimination"
        ]
        == "exile:underscore"
    )

    assert (
        first["creative_frontier"][
            "final"
        ][0][
            "candidate_id"
        ]
        == "creative:final"
    )

    assert (
        first["candidate_stage"][
            "best"
        ][
            "candidate_id"
        ]
        == "candidate:best"
    )

    print(
        first["digest"]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
