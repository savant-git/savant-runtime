from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .image_renderer import binding as image_renderer_binding
from .renderer_slot import project as project_renderer
from .thrust_qualification import execute as execute_thrusts
from .visual_evaluator import evaluate_and_quantify


schema = (
    "savant://runtime/urge/"
    "praxis-execution/1.0.0"
)

owner = "exile:urge"
provider_owner = "exile:opus"


class praxis_execution_error(
    RuntimeError
):
    pass


def _canonical(
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
        raise praxis_execution_error(
            "praxis execution value must "
            "be canonical-json serializable"
        ) from exc


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical(
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
        candidates = (
            value.splitlines()
        )
    elif isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        (
            bytes,
            bytearray,
        ),
    ):
        candidates = value
    else:
        raise praxis_execution_error(
            "string collection must be "
            "text or sequence"
        )

    return tuple(
        str(
            item
        ).strip()
        for item in candidates
        if str(
            item
        ).strip()
    )


def _image(
    value: Any,
) -> str | None:
    if isinstance(
        value,
        str,
    ):
        source = value.strip()

        if (
            source.startswith(
                "data:image/"
            )
            or source.startswith(
                "https://"
            )
            or source.startswith(
                "http://"
            )
        ):
            return source

        return None

    if isinstance(
        value,
        Mapping,
    ):
        for key in (
            "image",
            "image_url",
            "source",
            "url",
            "rendered_image",
            "preview",
            "projection",
            "renderer",
        ):
            if key not in value:
                continue

            found = _image(
                value[
                    key
                ]
            )

            if found:
                return found

        for child in value.values():
            found = _image(
                child
            )

            if found:
                return found

        return None

    if isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        for child in value:
            found = _image(
                child
            )

            if found:
                return found

    return None


def _baseline_projection(
    baseline: Any,
) -> dict[str, Any] | None:
    source = _image(
        baseline
    )

    if not source:
        return None

    if isinstance(
        baseline,
        Mapping,
    ):
        name = str(
            baseline.get(
                "name"
            )
            or "baseline"
        ).strip()

        media_type = str(
            baseline.get(
                "media_type"
            )
            or ""
        ).strip()
    else:
        name = "baseline"
        media_type = ""

    result = {
        "source":
            source,
        "name":
            name,
        "media_type":
            media_type
            or (
                source[
                    5:
                    source.find(
                        ";"
                    )
                ]
                if source.startswith(
                    "data:image/"
                )
                and ";"
                in source
                else "image"
            ),
        "digest":
            _digest(
                source
            ),
    }

    return result


def _candidate_payload(
    *,
    request: Mapping[str, Any],
    objective: str,
    logo_name: str,
    constraints: Sequence[str],
    invariants: Sequence[str],
    cliches: Sequence[str],
) -> dict[str, Any]:
    rigor = int(
        request[
            "rigor"
        ]
    )

    next_thrust = int(
        request[
            "next_thrust"
        ]
    )

    target = float(
        request[
            "target_improvement_percent"
        ]
    )

    previous_rigors = (
        request.get(
            "previous_rigors"
        )
        or ()
    )

    rejected = [
        item
        for item
        in previous_rigors
        if not bool(
            item.get(
                "accepted"
            )
        )
    ]

    return {
        "kind":
            "logo-rigor",
        "logo_name":
            logo_name,
        "objective":
            objective,
        "rigor":
            rigor,
        "target_thrust":
            next_thrust,
        "target_improvement_percent":
            target,
        "constraints":
            list(
                constraints
            ),
        "invariants":
            list(
                invariants
            ),
        "avoid_cliches":
            list(
                cliches
            ),
        "improvement_directive": (
            "Create a materially stronger "
            "candidate than the supplied "
            "baseline. The candidate is only "
            "a raw rigor until independent "
            "evaluation qualifies it as a "
            "thrust. Seek visible improvement "
            "in the selected dimensions while "
            "preserving every invariant. "
            "Do not change merely for novelty."
        ),
        "retry_context": {
            "previous_rigors":
                len(
                    previous_rigors
                ),
            "rejected_rigors":
                len(
                    rejected
                ),
            "must_not_repeat_rejected_state":
                bool(
                    rejected
                ),
        },
    }


def execute(
    *,
    objective: str,
    logo_name: str = "",
    baseline: Any,
    requested_thrusts: int,
    target_improvement_percent: float,
    weights: Mapping[
        str,
        Any,
    ] | None = None,
    constraints: Any = None,
    invariants: Any = None,
    cliches: Any = None,
    rigor_budget: int | None = None,
    on_rigor=None,
) -> dict[str, Any]:
    normalized_objective = str(
        objective
        or ""
    ).strip()

    if not normalized_objective:
        raise praxis_execution_error(
            "objective is required"
        )

    normalized_logo_name = str(
        logo_name
        or ""
    ).strip()

    normalized_constraints = (
        _strings(
            constraints
        )
    )

    normalized_invariants = (
        _strings(
            invariants
        )
    )

    normalized_cliches = (
        _strings(
            cliches
        )
    )

    baseline_projection = (
        _baseline_projection(
            baseline
        )
    )

    if baseline_projection is None:
        seed_candidate = {
            "kind":
                "logo-seed",
            "logo_name":
                normalized_logo_name,
            "objective":
                normalized_objective,
            "constraints":
                list(
                    normalized_constraints
                ),
            "invariants":
                list(
                    normalized_invariants
                ),
            "avoid_cliches":
                list(
                    normalized_cliches
                ),
            "directive": (
                "Create the initial visual "
                "baseline for this praxis. "
                "This seed is not a thrust."
            ),
        }

        seed_projection = (
            project_renderer(
                candidate=seed_candidate,
                binding=(
                    image_renderer_binding(
                        baseline=None
                    )
                ),
                context={
                    "praxis_role":
                        "seed",
                    "objective":
                        normalized_objective,
                },
            )
        )

        seed_image = _image(
            seed_projection
        )

        if not seed_image:
            raise praxis_execution_error(
                "renderer did not produce "
                "a seed image"
            )

        baseline_projection = {
            "source":
                seed_image,
            "name":
                "generated-seed",
            "media_type":
                "image/png",
            "digest":
                _digest(
                    seed_image
                ),
            "renderer":
                seed_projection,
        }

    def candidate_factory(
        request: Mapping[
            str,
            Any,
        ],
    ) -> Mapping[str, Any]:
        current_baseline = (
            request[
                "baseline"
            ]
        )

        candidate = (
            _candidate_payload(
                request=request,
                objective=(
                    normalized_objective
                ),
                logo_name=(
                    normalized_logo_name
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
            )
        )

        projection = (
            project_renderer(
                candidate=candidate,
                binding=(
                    image_renderer_binding(
                        baseline={
                            "source":
                                current_baseline,
                            "name":
                                (
                                    "previous-thrust"
                                ),
                        }
                    )
                ),
                context={
                    "praxis_role":
                        "rigor",
                    "rigor":
                        request[
                            "rigor"
                        ],
                    "target_thrust":
                        request[
                            "next_thrust"
                        ],
                    "objective":
                        normalized_objective,
                    "target_improvement_percent":
                        request[
                            "target_improvement_percent"
                        ],
                    "weights":
                        request[
                            "weights"
                        ],
                },
            )
        )

        image = _image(
            projection
        )

        if not image:
            raise praxis_execution_error(
                "renderer did not produce "
                "a rigor image"
            )

        return {
            "schema":
                schema,
            "owner":
                owner,
            "kind":
                "rigor",
            "rigor":
                request[
                    "rigor"
                ],
            "target_thrust":
                request[
                    "next_thrust"
                ],
            "image":
                image,
            "candidate":
                candidate,
            "renderer":
                projection,
        }

    def evaluator(
        request: Mapping[
            str,
            Any,
        ],
    ) -> Mapping[str, Any]:
        return evaluate_and_quantify(
            baseline=request[
                "baseline"
            ],
            candidate=request[
                "candidate"
            ],
            objective=(
                normalized_objective
            ),
            target_improvement_percent=(
                request[
                    "target_improvement_percent"
                ]
            ),
            weights=(
                request[
                    "weights"
                ]
            ),
            constraints=(
                normalized_constraints
            ),
            invariants=(
                normalized_invariants
            ),
        )

    execution = execute_thrusts(
        baseline=(
            baseline_projection[
                "source"
            ]
        ),
        requested_thrusts=(
            requested_thrusts
        ),
        target_improvement_percent=(
            target_improvement_percent
        ),
        candidate_factory=(
            candidate_factory
        ),
        evaluator=evaluator,
        weights=weights,
        rigor_budget=rigor_budget,
        context={
            "objective":
                normalized_objective,
            "logo_name":
                normalized_logo_name,
            "constraints":
                list(
                    normalized_constraints
                ),
            "invariants":
                list(
                    normalized_invariants
                ),
            "avoid_cliches":
                list(
                    normalized_cliches
                ),
        },
        on_rigor=on_rigor,
    )

    result = {
        "schema":
            schema,
        "owner":
            owner,
        "provider_owner":
            provider_owner,
        "kind":
            "praxis",
        "objective":
            normalized_objective,
        "logo_name":
            normalized_logo_name,
        "initial_baseline":
            baseline_projection,
        "requested_thrusts":
            execution[
                "requested_thrusts"
            ],
        "completed_thrusts":
            execution[
                "completed_thrusts"
            ],
        "rigors_attempted":
            execution[
                "rigors_attempted"
            ],
        "rigor_budget":
            execution[
                "rigor_budget"
            ],
        "target_improvement_percent":
            execution[
                "target_improvement_percent"
            ],
        "state":
            execution[
                "state"
            ],
        "complete":
            execution[
                "complete"
            ],
        "stop_reason":
            execution[
                "stop_reason"
            ],
        "final_image":
            execution[
                "final_image"
            ],
        "thrusts":
            execution[
                "thrusts"
            ],
        "history":
            execution[
                "history"
            ],
        "weights":
            execution[
                "weights"
            ],
        "lineage":
            execution[
                "lineage"
            ],
        "boundaries": {
            "urge_owns_qualification":
                True,
            "opus_owns_provider_execution":
                True,
            "rejected_rigors_preserved":
                True,
            "thrust_is_accepted_rigor":
                True,
            "next_baseline_is_last_thrust":
                True,
            "model_improvement_is_objective_fact":
                False,
        },
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


__all__ = [
    "execute",
    "owner",
    "provider_owner",
    "praxis_execution_error",
    "schema",
]
