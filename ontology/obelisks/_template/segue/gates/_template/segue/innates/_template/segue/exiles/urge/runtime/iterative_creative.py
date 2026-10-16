from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from ...opus.runtime.resilient_text import (
    execute_text_request_resilient,
)
from .iteration import (
    criterion,
    job,
    policy,
)
from .iteration_composition import (
    project as project_iteration,
)
from .job_adapter import (
    adapter,
    execution_boundary,
)


schema = (
    "savant://runtime/urge/"
    "iterative-creative/1.0.0"
)

owner = "exile:urge"
opus_owner = "exile:opus"
underscore_owner = "exile:underscore"

default_criteria = (
    (
        "objective_fidelity",
        1.0,
        0.985,
        True,
    ),
    (
        "constraint_fidelity",
        1.0,
        0.985,
        True,
    ),
    (
        "invariant_fidelity",
        1.0,
        0.995,
        True,
    ),
    (
        "conceptual_novelty",
        0.95,
        0.95,
        False,
    ),
    (
        "structural_coherence",
        1.0,
        0.97,
        False,
    ),
    (
        "non_cliche",
        0.9,
        0.95,
        False,
    ),
    (
        "usability",
        0.9,
        0.94,
        False,
    ),
    (
        "elegance",
        0.8,
        0.92,
        False,
    ),
)


class iterative_creative_error(
    RuntimeError
):
    pass


def _canonical_json(
    value: Any,
) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise iterative_creative_error(
            "value must be canonical-json "
            "serializable"
        ) from exc


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


def _strings(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        value = (
            value,
        )

    if (
        isinstance(
            value,
            bytes,
        )
        or not isinstance(
            value,
            Sequence,
        )
    ):
        raise iterative_creative_error(
            "expected a sequence"
        )

    result: list[str] = []
    seen: set[str] = set()

    for item in value:
        text = str(
            item
        ).strip()

        if (
            text
            and text not in seen
        ):
            seen.add(
                text
            )
            result.append(
                text
            )

    return tuple(
        result
    )


def _mapping(
    value: Any,
    *,
    field: str,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise iterative_creative_error(
            f"{field} must be a mapping"
        )

    return dict(
        value
    )


def _json_object(
    value: Any,
) -> dict[str, Any]:
    text = str(
        value
    ).strip()

    if text.startswith(
        "```"
    ):
        lines = text.splitlines()

        if lines:
            lines = lines[
                1:
            ]

        if (
            lines
            and lines[-1].strip()
            == "```"
        ):
            lines = lines[
                :-1
            ]

        text = "\n".join(
            lines
        ).strip()

        if text.lower().startswith(
            "json\n"
        ):
            text = text[
                5:
            ].strip()

    try:
        parsed = json.loads(
            text
        )
    except json.JSONDecodeError as exc:
        raise iterative_creative_error(
            "opus response was not valid json"
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise iterative_creative_error(
            "opus response must be a json object"
        )

    return parsed


def _opus(
    *,
    message: str,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    result = execute_text_request_resilient(
        {
            "owner": owner,
            "message": message,
            "system": (
                "you are executing one bounded "
                "operation for savant urge. "
                "urge owns iteration and revision "
                "pressure. opus owns provider and "
                "model execution. preserve all "
                "binding constraints and invariants. "
                "do not expose hidden chain-of-thought. "
                "return strict json only."
            ),
            "context": _canonical_json(
                context
            ),
        }
    )

    if not isinstance(
        result,
        Mapping,
    ):
        raise iterative_creative_error(
            "opus returned an invalid result"
        )

    text = str(
        result.get(
            "text",
            "",
        )
    ).strip()

    if not text:
        raise iterative_creative_error(
            "opus returned no text"
        )

    return {
        "body": _json_object(
            text
        ),
        "provider": result.get(
            "provider"
        ),
        "model": result.get(
            "model"
        ),
        "lineage": result.get(
            "lineage",
            {},
        ),
        "usage": result.get(
            "usage",
            {},
        ),
    }


def _criterion_objects(
) -> tuple[criterion, ...]:
    return tuple(
        criterion(
            id=criterion_id,
            weight=weight,
            target=target,
            required=required,
        )
        for (
            criterion_id,
            weight,
            target,
            required,
        )
        in default_criteria
    )


def _evaluation_prompt(
    *,
    objective: str,
    criteria: Sequence[
        Mapping[str, Any]
    ],
    constraints: Sequence[str],
    invariants: Sequence[str],
    cliches: Sequence[str],
    baselines: Sequence[str],
    payload: Any,
) -> str:
    return (
        "Evaluate the candidate against the "
        "objective and every supplied criterion.\n\n"
        "Do not reward verbosity, complexity, "
        "fashionability, or superficial novelty.\n"
        "Novelty must come from mechanism or "
        "structure.\n"
        "Binding constraints and invariants must "
        "not be traded away for novelty.\n"
        "Known cliches and baselines are negative "
        "references, not ingredients.\n\n"
        f"objective:\n{objective}\n\n"
        "criteria:\n"
        f"{_canonical_json(criteria)}\n\n"
        "constraints:\n"
        f"{_canonical_json(list(constraints))}\n\n"
        "invariants:\n"
        f"{_canonical_json(list(invariants))}\n\n"
        "known cliches:\n"
        f"{_canonical_json(list(cliches))}\n\n"
        "baselines to avoid imitating:\n"
        f"{_canonical_json(list(baselines))}\n\n"
        "candidate:\n"
        f"{_canonical_json(payload)}\n\n"
        "Return exactly one JSON object with:\n"
        "{"
        "\"scores\":{"
        "\"criterion_id\":0.0"
        "},"
        "\"findings\":[\"\"],"
        "\"evidence\":[\"\"],"
        "\"metadata\":{"
        "\"summary\":\"\""
        "}"
        "}\n"
        "Every criterion id must appear exactly "
        "once in scores. Scores must be numbers "
        "from 0 through 1."
    )


def _revision_prompt(
    *,
    objective: str,
    constraints: Sequence[str],
    invariants: Sequence[str],
    cliches: Sequence[str],
    baselines: Sequence[str],
    payload: Any,
    pressure: Mapping[str, Any],
    branch_factor: int,
) -> str:
    return (
        "Revise the candidate under Urge revision "
        "pressure.\n\n"
        f"Produce exactly {branch_factor} materially "
        "different revision branches.\n"
        "Each branch must improve the candidate "
        "rather than merely restyle or paraphrase "
        "it.\n"
        "Preserve successful substance unless a "
        "specific pressure requires changing it.\n"
        "Respond directly to weak criteria and "
        "findings.\n"
        "Explore structurally different solutions "
        "when the current mechanism is limiting "
        "improvement.\n"
        "Do not converge all branches onto one "
        "cosmetic variation.\n"
        "Do not imitate the negative baselines.\n"
        "Do not violate constraints or invariants.\n"
        "Do not add features merely to appear more "
        "advanced.\n\n"
        f"objective:\n{objective}\n\n"
        "constraints:\n"
        f"{_canonical_json(list(constraints))}\n\n"
        "invariants:\n"
        f"{_canonical_json(list(invariants))}\n\n"
        "known cliches:\n"
        f"{_canonical_json(list(cliches))}\n\n"
        "baselines to avoid imitating:\n"
        f"{_canonical_json(list(baselines))}\n\n"
        "current candidate:\n"
        f"{_canonical_json(payload)}\n\n"
        "revision pressure:\n"
        f"{_canonical_json(dict(pressure))}\n\n"
        "Return exactly:\n"
        "{"
        "\"candidates\":["
        "{"
        "\"payload\":{},"
        "\"rationale\":[\"\"],"
        "\"provenance\":[\"urge:revision\"]"
        "}"
        "]"
        "}\n"
        "The payload may be any canonical JSON "
        "structure appropriate to the objective."
    )


def _boundary(
    *,
    objective: str,
    criteria: Sequence[
        Mapping[str, Any]
    ],
    constraints: tuple[str, ...],
    invariants: tuple[str, ...],
    cliches: tuple[str, ...],
    baselines: tuple[str, ...],
    branch_factor: int,
) -> execution_boundary:
    def evaluate(
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        payload = request.get(
            "payload"
        )

        result = _opus(
            message=_evaluation_prompt(
                objective=objective,
                criteria=criteria,
                constraints=constraints,
                invariants=invariants,
                cliches=cliches,
                baselines=baselines,
                payload=payload,
            ),
            context={
                "operation": "evaluate",
                "request_digest": (
                    request.get(
                        "digest"
                    )
                ),
                "owner": owner,
                "provider_owner": (
                    opus_owner
                ),
                "discrimination_owner": (
                    underscore_owner
                ),
            },
        )

        body = result[
            "body"
        ]

        scores = body.get(
            "scores"
        )

        if not isinstance(
            scores,
            Mapping,
        ):
            raise iterative_creative_error(
                "evaluation requires scores"
            )

        expected_ids = {
            str(
                item[
                    "id"
                ]
            )
            for item in criteria
        }

        actual_ids = {
            str(
                key
            )
            for key in scores
        }

        if (
            expected_ids
            != actual_ids
        ):
            raise iterative_creative_error(
                "evaluation scores must match "
                "all criteria exactly"
            )

        return {
            "scores": dict(
                scores
            ),
            "findings": _strings(
                body.get(
                    "findings"
                )
            ),
            "evidence": _strings(
                body.get(
                    "evidence"
                )
            ),
            "metadata": {
                **_mapping(
                    body.get(
                        "metadata"
                    ),
                    field="metadata",
                ),
                "provider": result[
                    "provider"
                ],
                "model": result[
                    "model"
                ],
                "opus_lineage": result[
                    "lineage"
                ],
            },
        }

    def revise(
        request: Mapping[str, Any],
    ) -> Sequence[
        Mapping[str, Any]
    ]:
        pressure = request.get(
            "pressure",
            {},
        )

        if not isinstance(
            pressure,
            Mapping,
        ):
            raise iterative_creative_error(
                "revision pressure must "
                "be a mapping"
            )

        result = _opus(
            message=_revision_prompt(
                objective=objective,
                constraints=constraints,
                invariants=invariants,
                cliches=cliches,
                baselines=baselines,
                payload=request.get(
                    "payload"
                ),
                pressure=pressure,
                branch_factor=(
                    branch_factor
                ),
            ),
            context={
                "operation": "revise",
                "request_digest": (
                    request.get(
                        "digest"
                    )
                ),
                "owner": owner,
                "provider_owner": (
                    opus_owner
                ),
                "discrimination_owner": (
                    underscore_owner
                ),
            },
        )

        body = result[
            "body"
        ]

        candidates = body.get(
            "candidates"
        )

        if (
            isinstance(
                candidates,
                (str, bytes),
            )
            or not isinstance(
                candidates,
                Sequence,
            )
        ):
            raise iterative_creative_error(
                "revision requires "
                "candidate sequence"
            )

        if len(
            candidates
        ) != branch_factor:
            raise iterative_creative_error(
                "revision returned the wrong "
                "branch count"
            )

        output = []

        for index, item in enumerate(
            candidates
        ):
            if not isinstance(
                item,
                Mapping,
            ):
                raise iterative_creative_error(
                    "revision candidate must "
                    "be a mapping"
                )

            if "payload" not in item:
                raise iterative_creative_error(
                    "revision candidate requires "
                    "payload"
                )

            output.append(
                {
                    "payload": item[
                        "payload"
                    ],
                    "rationale": _strings(
                        item.get(
                            "rationale"
                        )
                    ),
                    "provenance": (
                        *(
                            _strings(
                                item.get(
                                    "provenance"
                                )
                            )
                        ),
                        (
                            "opus:"
                            f"{result['provider']}:"
                            f"{result['model']}"
                        ),
                    ),
                    "metadata": {
                        "branch_index": index,
                        "provider": result[
                            "provider"
                        ],
                        "model": result[
                            "model"
                        ],
                        "opus_lineage": result[
                            "lineage"
                        ],
                    },
                }
            )

        return tuple(
            output
        )

    return execution_boundary(
        evaluate=evaluate,
        revise=revise,
        identity=(
            "urge:iterative-creative:"
            "opus-boundary"
        ),
    )


def project(
    *,
    objective: str,
    initial_payload: Any,
    constraints: Sequence[str] = (),
    invariants: Sequence[str] = (),
    cliches: Sequence[str] = (),
    baselines: Sequence[str] = (),
    context: Mapping[
        str,
        Any,
    ] | None = None,
    run_policy: policy | None = None,
    convergence_policy: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    normalized_objective = str(
        objective
    ).strip()

    if not normalized_objective:
        raise iterative_creative_error(
            "objective is required"
        )

    normalized_constraints = _strings(
        constraints
    )

    normalized_invariants = _strings(
        invariants
    )

    normalized_cliches = _strings(
        cliches
    )

    normalized_baselines = _strings(
        baselines
    )

    normalized_context = _mapping(
        context,
        field="context",
    )

    active_policy = (
        run_policy
        or policy()
    )

    criteria = (
        _criterion_objects()
    )

    criteria_projection = [
        {
            "id": item.id,
            "weight": item.weight,
            "target": item.target,
            "required": item.required,
        }
        for item in criteria
    ]

    seed_identity = {
        "objective": (
            normalized_objective
        ),
        "initial_payload": (
            initial_payload
        ),
        "criteria": (
            criteria_projection
        ),
        "constraints": list(
            normalized_constraints
        ),
        "invariants": list(
            normalized_invariants
        ),
        "cliches": list(
            normalized_cliches
        ),
        "baselines": list(
            normalized_baselines
        ),
        "context": (
            normalized_context
        ),
    }

    work = job(
        id=(
            "urge:creative:"
            f"{_digest(seed_identity)[:24]}"
        ),
        objective=(
            normalized_objective
        ),
        payload=(
            initial_payload
        ),
        criteria=criteria,
        constraints=(
            normalized_constraints
        ),
        provenance=(
            "urge:iterative-creative",
        ),
        metadata={
            "cliches": list(
                normalized_cliches
            ),
            "baselines": list(
                normalized_baselines
            ),
            "context": (
                normalized_context
            ),
        },
    )

    boundary = _boundary(
        objective=(
            normalized_objective
        ),
        criteria=(
            criteria_projection
        ),
        constraints=(
            normalized_constraints
        ),
        invariants=(
            normalized_invariants
        ),
        cliches=(
            normalized_cliches
        ),
        baselines=(
            normalized_baselines
        ),
        branch_factor=(
            active_policy.branch_factor
        ),
    )

    execution = adapter(
        boundary
    )

    iteration = project_iteration(
        work,
        evaluator=(
            execution.evaluator
        ),
        reviser=(
            execution.reviser
        ),
        run_policy=(
            active_policy
        ),
        convergence_policy=(
            convergence_policy
        ),
        initial_payload=(
            initial_payload
        ),
    )

    projection = {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "projection_only": True,
        "objective": (
            normalized_objective
        ),
        "seed_digest": _digest(
            seed_identity
        ),
        "iteration": iteration,
        "ownership": {
            "iteration": owner,
            "provider_orchestration": (
                opus_owner
            ),
            "structural_discrimination": (
                underscore_owner
            ),
        },
        "capabilities": {
            "iterative_revision": True,
            "branching": True,
            "criterion_pressure": True,
            "required_invariant_pressure": (
                True
            ),
            "candidate_deduplication": True,
            "bounded_execution": True,
            "failure_isolation": True,
            "alternate_preservation": True,
            "convergence_projection": True,
            "lineage_preservation": True,
            "provider_lineage": True,
            "deterministic_selection": True,
            "replay_from_recorded_outputs": (
                True
            ),
        },
        "boundaries": {
            "creates_authority": False,
            "mutates_canon": False,
            "mutates_source": False,
            "owns_provider_routing": False,
            "owns_model_selection": False,
            "owns_underscore": False,
            "exposes_hidden_chain_of_thought": (
                False
            ),
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection


__all__ = [
    "default_criteria",
    "iterative_creative_error",
    "project",
    "schema",
]
