from __future__ import annotations

import json

from . import iterative_creative
from .iteration import policy


def _fake_opus(
    *,
    message: str,
    context: dict,
) -> dict:
    if (
        '"scores"' in message
        and "Evaluate the candidate"
        in message
    ):
        body = {
            "scores": {
                "objective_fidelity": 1.0,
                "constraint_fidelity": 1.0,
                "invariant_fidelity": 1.0,
                "conceptual_novelty": 0.99,
                "structural_coherence": 0.99,
                "non_cliche": 0.99,
                "usability": 0.99,
                "elegance": 0.99,
            },
            "findings": [],
            "evidence": [
                "selftest"
            ],
            "metadata": {
                "summary": (
                    "selftest evaluation"
                )
            },
        }

    else:
        body = {
            "candidates": [
                {
                    "payload": {
                        "concept": (
                            "selftest branch a"
                        )
                    },
                    "rationale": [
                        "selftest"
                    ],
                    "provenance": [
                        "selftest"
                    ],
                },
                {
                    "payload": {
                        "concept": (
                            "selftest branch b"
                        )
                    },
                    "rationale": [
                        "selftest"
                    ],
                    "provenance": [
                        "selftest"
                    ],
                },
            ]
        }

    return {
        "body": body,
        "provider": "selftest",
        "model": "selftest",
        "lineage": {
            "selftest": True
        },
        "usage": {},
    }


def run() -> dict:
    original = (
        iterative_creative._opus
    )

    iterative_creative._opus = (
        _fake_opus
    )

    try:
        first = (
            iterative_creative.project(
                objective=(
                    "produce a structurally "
                    "distinct concept"
                ),
                initial_payload={
                    "concept": (
                        "selftest seed"
                    )
                },
                constraints=(
                    "preserve usability",
                ),
                invariants=(
                    "preserve objective",
                ),
                cliches=(
                    "generic futurism",
                ),
                baselines=(
                    "baseline-a",
                ),
                context={
                    "mode": "selftest"
                },
                run_policy=policy(
                    max_cycles=1,
                    branch_factor=2,
                    min_improvement=0.0,
                    target_score=0.98,
                    patience=1,
                    max_candidates=4,
                    max_failures=1,
                    preserve_alternates=2,
                ),
            )
        )

        second = (
            iterative_creative.project(
                objective=(
                    "produce a structurally "
                    "distinct concept"
                ),
                initial_payload={
                    "concept": (
                        "selftest seed"
                    )
                },
                constraints=(
                    "preserve usability",
                ),
                invariants=(
                    "preserve objective",
                ),
                cliches=(
                    "generic futurism",
                ),
                baselines=(
                    "baseline-a",
                ),
                context={
                    "mode": "selftest"
                },
                run_policy=policy(
                    max_cycles=1,
                    branch_factor=2,
                    min_improvement=0.0,
                    target_score=0.98,
                    patience=1,
                    max_candidates=4,
                    max_failures=1,
                    preserve_alternates=2,
                ),
            )
        )

    finally:
        iterative_creative._opus = (
            original
        )

    first_copy = dict(
        first
    )

    second_copy = dict(
        second
    )

    first_iteration = dict(
        first_copy[
            "iteration"
        ]
    )

    second_iteration = dict(
        second_copy[
            "iteration"
        ]
    )

    first_body = dict(
        first_iteration[
            "iteration"
        ]
    )

    second_body = dict(
        second_iteration[
            "iteration"
        ]
    )

    first_body.pop(
        "duration_ns",
        None,
    )

    second_body.pop(
        "duration_ns",
        None,
    )

    first_body.pop(
        "digest",
        None,
    )

    second_body.pop(
        "digest",
        None,
    )

    first_iteration[
        "iteration"
    ] = first_body

    second_iteration[
        "iteration"
    ] = second_body

    first_iteration.pop(
        "digest",
        None,
    )

    second_iteration.pop(
        "digest",
        None,
    )

    first_copy[
        "iteration"
    ] = first_iteration

    second_copy[
        "iteration"
    ] = second_iteration

    first_copy.pop(
        "digest",
        None,
    )

    second_copy.pop(
        "digest",
        None,
    )

    if (
        first_copy
        != second_copy
    ):
        raise RuntimeError(
            "iterative creative projection "
            "is not deterministic apart "
            "from runtime duration"
        )

    body = first[
        "iteration"
    ][
        "iteration"
    ]

    if not body.get(
        "best"
    ):
        raise RuntimeError(
            "iteration produced no best "
            "candidate"
        )

    if (
        first[
            "boundaries"
        ][
            "owns_provider_routing"
        ]
    ):
        raise RuntimeError(
            "urge acquired provider routing"
        )

    if (
        first[
            "authority_effect"
        ]
        != "none"
    ):
        raise RuntimeError(
            "iteration created authority"
        )

    return {
        "schema": (
            iterative_creative.schema
        ),
        "owner": (
            iterative_creative.owner
        ),
        "ok": True,
        "iterative_revision": True,
        "branching": True,
        "criterion_pressure": True,
        "required_invariant_pressure": (
            True
        ),
        "provider_authority": False,
        "authority_effect": "none",
        "best_candidate": True,
        "deterministic_selection": True,
        "digest": first[
            "digest"
        ],
    }


if __name__ == "__main__":
    print(
        json.dumps(
            run(),
            indent=2,
            sort_keys=True,
        )
    )
