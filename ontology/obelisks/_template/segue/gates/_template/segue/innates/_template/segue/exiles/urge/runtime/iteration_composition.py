from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .composition import (
    project as project_convergence_composition,
)
from .convergence_policy import (
    interpret as interpret_convergence,
)
from .iteration import (
    engine,
    job,
    policy,
)


schema = (
    "savant://runtime/urge/"
    "iteration-composition/1.0.0"
)

owner = "exile:urge"


class iteration_composition_error(
    ValueError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _candidate_projection(
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    assessment = candidate.get(
        "assessment",
        {},
    )

    scores = assessment.get(
        "scores",
        {},
    )

    if not isinstance(
        scores,
        Mapping,
    ):
        scores = {}

    score_tokens = [
        f"{key}:{float(value):.12f}"
        for key, value in sorted(
            scores.items()
        )
    ]

    findings = assessment.get(
        "findings",
        (),
    )

    if (
        isinstance(
            findings,
            (str, bytes),
        )
        or not isinstance(
            findings,
            Sequence,
        )
    ):
        findings = ()

    rationale = candidate.get(
        "rationale",
        (),
    )

    if (
        isinstance(
            rationale,
            (str, bytes),
        )
        or not isinstance(
            rationale,
            Sequence,
        )
    ):
        rationale = ()

    semantic_tokens = [
        *score_tokens,
        *(
            str(value)
            for value in findings
        ),
        *(
            str(value)
            for value in rationale
        ),
    ]

    return {
        "id": str(
            candidate.get(
                "digest",
                candidate.get(
                    "payload_digest",
                    "",
                ),
            )
        ),
        "text": " ".join(
            semantic_tokens
        ),
        "payload_digest": candidate.get(
            "payload_digest"
        ),
        "candidate_digest": candidate.get(
            "digest"
        ),
        "score": assessment.get(
            "score"
        ),
        "required_met": assessment.get(
            "required_met"
        ),
    }


def project(
    work: job,
    *,
    evaluator: Any,
    reviser: Any,
    run_policy: policy | None = None,
    convergence_policy: Mapping[
        str,
        Any,
    ]
    | None = None,
    initial_payload: Any | None = None,
) -> dict[str, Any]:
    if not isinstance(
        work,
        job,
    ):
        raise iteration_composition_error(
            "work must be a job"
        )

    iteration = engine(
        evaluator=evaluator,
        reviser=reviser,
        run_policy=run_policy,
    ).run(
        work,
        initial_payload=initial_payload,
    )

    candidates = [
        _candidate_projection(
            candidate
        )
        for candidate in [
            iteration[
                "best"
            ],
            *iteration[
                "alternates"
            ],
        ]
    ]

    convergence = None
    interpretation = None

    if len(candidates) >= 2:
        convergence = (
            project_convergence_composition(
                candidates
            )
        )

        interpretation = (
            interpret_convergence(
                convergence[
                    "stability"
                ],
                policy=convergence_policy,
            )
        )

    projection = {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "projection_only": True,
        "deterministic_selection": True,
        "iteration": iteration,
        "convergence": convergence,
        "convergence_interpretation": (
            interpretation
        ),
        "lineage": {
            "job_digest": iteration[
                "job"
            ][
                "digest"
            ],
            "iteration_digest": iteration[
                "digest"
            ],
            "convergence_digest": (
                None
                if convergence is None
                else convergence[
                    "digest"
                ]
            ),
            "interpretation_digest": (
                None
                if interpretation is None
                else interpretation[
                    "digest"
                ]
            ),
        },
        "capabilities": {
            "iteration": True,
            "improvement_cycles": True,
            "revision_pressure": True,
            "branching": True,
            "candidate_deduplication": True,
            "criterion_pressure": True,
            "required_criterion_gating": True,
            "bounded_execution": True,
            "failure_isolation": True,
            "lineage_projection": True,
            "provenance_preservation": True,
            "convergence_projection": (
                convergence is not None
            ),
            "stability_projection": (
                convergence is not None
            ),
            "deterministic_selection": True,
            "deterministic_replay": True,
        },
        "boundaries": {
            "declares_truth": False,
            "verifies_fact": False,
            "admits_evidence": False,
            "mutates_canon": False,
            "mutates_source": False,
            "creates_authority": False,
            "selects_provider": False,
            "executes_model": False,
        },
    }

    digestable = dict(
        projection
    )

    digestable[
        "iteration"
    ] = dict(
        projection[
            "iteration"
        ]
    )

    digestable[
        "iteration"
    ][
        "metrics"
    ] = dict(
        projection[
            "iteration"
        ][
            "metrics"
        ]
    )

    digestable[
        "iteration"
    ][
        "metrics"
    ].pop(
        "duration_ns",
        None,
    )

    projection[
        "digest"
    ] = _digest(
        digestable
    )

    return projection
