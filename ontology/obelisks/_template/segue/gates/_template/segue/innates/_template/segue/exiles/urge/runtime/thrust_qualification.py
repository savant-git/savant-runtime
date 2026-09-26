from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .improvement_quantification import (
    adaptive_rigor_budget,
    normalize_target,
    normalize_weights,
)


schema = (
    "savant://runtime/urge/"
    "thrust-qualification/1.0.0"
)

owner = "exile:urge"

minimum_thrusts = 1
maximum_thrusts = 250


class thrust_qualification_error(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class praxis_pressure:
    requested_thrusts: int
    target_improvement_percent: float
    weights: Mapping[str, float]
    rigor_budget: int


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
        raise thrust_qualification_error(
            "thrust qualification value must "
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


def _positive_integer(
    value: Any,
    *,
    field: str,
    maximum: int,
) -> int:
    if isinstance(
        value,
        bool,
    ):
        raise thrust_qualification_error(
            field
            + " must be an integer"
        )

    try:
        parsed = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise thrust_qualification_error(
            field
            + " must be an integer"
        ) from exc

    if (
        parsed < 1
        or parsed > maximum
    ):
        raise thrust_qualification_error(
            field
            + " must be between 1 and "
            + str(
                maximum
            )
        )

    return parsed


def normalize_pressure(
    *,
    requested_thrusts: Any,
    target_improvement_percent: Any,
    weights: Mapping[
        str,
        Any,
    ] | None = None,
    rigor_budget: Any = None,
) -> praxis_pressure:
    thrusts = _positive_integer(
        requested_thrusts,
        field="requested_thrusts",
        maximum=maximum_thrusts,
    )

    target = normalize_target(
        target_improvement_percent
    )

    normalized_weights = (
        normalize_weights(
            weights
        )
    )

    automatic_budget = (
        adaptive_rigor_budget(
            requested_thrusts=thrusts,
            target_improvement_percent=target,
        )
    )

    if rigor_budget is None:
        budget = automatic_budget
    else:
        budget = _positive_integer(
            rigor_budget,
            field="rigor_budget",
            maximum=2000,
        )

        if budget < thrusts:
            raise thrust_qualification_error(
                "rigor_budget cannot be less "
                "than requested_thrusts"
            )

    return praxis_pressure(
        requested_thrusts=thrusts,
        target_improvement_percent=target,
        weights=normalized_weights,
        rigor_budget=budget,
    )


def _extract_image(
    value: Any,
) -> str | None:
    if isinstance(
        value,
        str,
    ):
        candidate = value.strip()

        if (
            candidate.startswith(
                "data:image/"
            )
            or candidate.startswith(
                "https://"
            )
            or candidate.startswith(
                "http://"
            )
        ):
            return candidate

        return None

    if isinstance(
        value,
        Mapping,
    ):
        preferred = (
            "image",
            "image_url",
            "source",
            "url",
            "rendered_image",
            "preview",
        )

        for key in preferred:
            if key not in value:
                continue

            found = _extract_image(
                value[
                    key
                ]
            )

            if found:
                return found

        for child in value.values():
            found = _extract_image(
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
            found = _extract_image(
                child
            )

            if found:
                return found

    return None


def _history_entry(
    *,
    rigor_number: int,
    accepted_thrust_number:
        int | None,
    baseline_image: str,
    candidate_image: str,
    candidate_projection:
        Mapping[str, Any],
    evaluation:
        Mapping[str, Any],
) -> dict[str, Any]:
    qualifies = bool(
        evaluation.get(
            "qualifies_as_thrust"
        )
    )

    entry = {
        "schema":
            schema,
        "owner":
            owner,
        "rigor":
            rigor_number,
        "thrust":
            (
                accepted_thrust_number
                if qualifies
                else None
            ),
        "kind":
            (
                "thrust"
                if qualifies
                else "rigor"
            ),
        "accepted":
            qualifies,
        "verdict":
            evaluation.get(
                "verdict"
            ),
        "baseline_digest":
            _digest(
                baseline_image
            ),
        "candidate_digest":
            _digest(
                candidate_image
            ),
        "candidate_projection_digest":
            _digest(
                candidate_projection
            ),
        "evaluation_digest":
            evaluation.get(
                "digest"
            )
            or _digest(
                evaluation
            ),
        "improvement_percent":
            (
                evaluation.get(
                    "quantification",
                    {},
                )
                .get(
                    "aggregate",
                    {},
                )
                .get(
                    "conservative_improvement_percent"
                )
            ),
        "qualification_margin_percent":
            (
                evaluation.get(
                    "quantification",
                    {},
                )
                .get(
                    "aggregate",
                    {},
                )
                .get(
                    "qualification_margin_percent"
                )
            ),
        "invariant_failures":
            list(
                evaluation.get(
                    "invariant_failures",
                    [],
                )
            ),
    }

    entry[
        "digest"
    ] = _digest(
        entry
    )

    return entry


def execute(
    *,
    baseline: Any,
    requested_thrusts: Any,
    target_improvement_percent: Any,
    candidate_factory: Callable[
        [
            Mapping[str, Any]
        ],
        Mapping[str, Any],
    ],
    evaluator: Callable[
        [
            Mapping[str, Any]
        ],
        Mapping[str, Any],
    ],
    weights: Mapping[
        str,
        Any,
    ] | None = None,
    rigor_budget: Any = None,
    context: Mapping[
        str,
        Any,
    ] | None = None,
    on_rigor: Callable[
        [
            Mapping[str, Any]
        ],
        None,
    ] | None = None,
) -> dict[str, Any]:
    if not callable(
        candidate_factory
    ):
        raise thrust_qualification_error(
            "candidate_factory must "
            "be callable"
        )

    if not callable(
        evaluator
    ):
        raise thrust_qualification_error(
            "evaluator must be callable"
        )

    if (
        on_rigor is not None
        and not callable(
            on_rigor
        )
    ):
        raise thrust_qualification_error(
            "on_rigor must be callable"
        )

    pressure = normalize_pressure(
        requested_thrusts=(
            requested_thrusts
        ),
        target_improvement_percent=(
            target_improvement_percent
        ),
        weights=weights,
        rigor_budget=rigor_budget,
    )

    baseline_image = _extract_image(
        baseline
    )

    if not baseline_image:
        raise thrust_qualification_error(
            "baseline must contain "
            "an image source"
        )

    immutable_context = dict(
        context
        or {}
    )

    history: list[
        dict[str, Any]
    ] = []

    thrusts: list[
        dict[str, Any]
    ] = []

    current_baseline = (
        baseline_image
    )

    rigor_number = 0

    while (
        len(
            thrusts
        )
        < pressure.requested_thrusts
        and rigor_number
        < pressure.rigor_budget
    ):
        rigor_number += 1

        candidate_request = {
            "schema":
                schema,
            "owner":
                owner,
            "rigor":
                rigor_number,
            "next_thrust":
                len(
                    thrusts
                )
                + 1,
            "baseline":
                current_baseline,
            "target_improvement_percent":
                pressure.target_improvement_percent,
            "weights":
                dict(
                    pressure.weights
                ),
            "previous_rigors":
                tuple(
                    history
                ),
            "context":
                immutable_context,
        }

        candidate_projection = (
            candidate_factory(
                candidate_request
            )
        )

        if not isinstance(
            candidate_projection,
            Mapping,
        ):
            raise thrust_qualification_error(
                "candidate_factory must "
                "return a mapping"
            )

        candidate_image = (
            _extract_image(
                candidate_projection
            )
        )

        if not candidate_image:
            raise thrust_qualification_error(
                "rigor candidate does not "
                "contain an image source"
            )

        evaluation_request = {
            "schema":
                schema,
            "owner":
                owner,
            "rigor":
                rigor_number,
            "next_thrust":
                len(
                    thrusts
                )
                + 1,
            "baseline":
                current_baseline,
            "candidate":
                candidate_image,
            "target_improvement_percent":
                pressure.target_improvement_percent,
            "weights":
                dict(
                    pressure.weights
                ),
            "context":
                immutable_context,
        }

        evaluation = evaluator(
            evaluation_request
        )

        if not isinstance(
            evaluation,
            Mapping,
        ):
            raise thrust_qualification_error(
                "evaluator must return "
                "a mapping"
            )

        qualifies = bool(
            evaluation.get(
                "qualifies_as_thrust"
            )
        )

        thrust_number = (
            len(
                thrusts
            )
            + 1
            if qualifies
            else None
        )

        history_entry = (
            _history_entry(
                rigor_number=(
                    rigor_number
                ),
                accepted_thrust_number=(
                    thrust_number
                ),
                baseline_image=(
                    current_baseline
                ),
                candidate_image=(
                    candidate_image
                ),
                candidate_projection=(
                    candidate_projection
                ),
                evaluation=(
                    evaluation
                ),
            )
        )

        history.append(
            history_entry
        )

        event = {
            "history":
                history_entry,
            "candidate":
                dict(
                    candidate_projection
                ),
            "evaluation":
                dict(
                    evaluation
                ),
        }

        if qualifies:
            thrust = {
                "schema":
                    schema,
                "owner":
                    owner,
                "thrust":
                    thrust_number,
                "source_rigor":
                    rigor_number,
                "image":
                    candidate_image,
                "candidate":
                    dict(
                        candidate_projection
                    ),
                "evaluation":
                    dict(
                        evaluation
                    ),
                "history_digest":
                    history_entry[
                        "digest"
                    ],
            }

            thrust[
                "digest"
            ] = _digest(
                thrust
            )

            thrusts.append(
                thrust
            )

            current_baseline = (
                candidate_image
            )

            event[
                "thrust"
            ] = thrust

        if on_rigor is not None:
            on_rigor(
                event
            )

    complete = (
        len(
            thrusts
        )
        == pressure.requested_thrusts
    )

    if complete:
        state = "complete"
        stop_reason = (
            "requested-thrusts-achieved"
        )
    else:
        state = "exhausted"
        stop_reason = (
            "rigor-budget-exhausted"
        )

    result = {
        "schema":
            schema,
        "owner":
            owner,
        "state":
            state,
        "complete":
            complete,
        "stop_reason":
            stop_reason,
        "requested_thrusts":
            pressure.requested_thrusts,
        "completed_thrusts":
            len(
                thrusts
            ),
        "rigors_attempted":
            rigor_number,
        "rigor_budget":
            pressure.rigor_budget,
        "target_improvement_percent":
            pressure.target_improvement_percent,
        "weights":
            dict(
                pressure.weights
            ),
        "initial_baseline_digest":
            _digest(
                baseline_image
            ),
        "final_image":
            (
                current_baseline
                if thrusts
                else baseline_image
            ),
        "thrusts":
            thrusts,
        "history":
            history,
        "lineage": {
            "history_preserved":
                True,
            "rejected_rigors_preserved":
                True,
            "accepted_thrusts_preserved":
                True,
            "next_baseline_is_last_thrust":
                True,
        },
        "boundaries": {
            "provider_execution":
                False,
            "evaluation_execution":
                False,
            "candidate_execution":
                False,
            "creates_authority":
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
    "maximum_thrusts",
    "normalize_pressure",
    "owner",
    "praxis_pressure",
    "schema",
    "thrust_qualification_error",
]
