from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .improvement_quantification import (
    normalize_target,
    normalize_weights,
)
from .praxis import (
    execute_step as execute_praxis_step,
)
from .visual_evaluator import (
    evaluate_and_quantify,
)


SCHEMA = (
    "savant://runtime/urge/"
    "praxis-live/1.0.0"
)

CAPABILITY = "exile:urge:praxis-rigor"
OWNER = "exile:urge"
PROVIDER_OWNER = "exile:opus"


class praxis_live_error(
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
        raise praxis_live_error(
            "live praxis projection must be "
            "canonical-json serializable"
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


def _image(
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
        for key in (
            "image",
            "image_url",
            "source",
            "url",
            "rendered_image",
            "preview",
            "projection",
            "renderer",
            "output",
            "result",
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


def _strings(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        values = value.splitlines()
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
        values = value
    else:
        raise praxis_live_error(
            "string collection must be "
            "text or a sequence"
        )

    return tuple(
        str(
            item
        ).strip()
        for item in values
        if str(
            item
        ).strip()
    )


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
        raise praxis_live_error(
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
        raise praxis_live_error(
            field
            + " must be an integer"
        ) from exc

    if (
        parsed < 1
        or parsed > maximum
    ):
        raise praxis_live_error(
            field
            + " must be between 1 and "
            + str(
                maximum
            )
        )

    return parsed


def _baseline(
    parameters: Mapping[
        str,
        Any,
    ],
) -> str | None:
    return _image(
        parameters.get(
            "baseline"
        )
    )


def _previous_projection(
    payload: Mapping[
        str,
        Any,
    ],
) -> Mapping[
    str,
    Any,
] | None:
    previous = payload.get(
        "previous"
    )

    if previous is None:
        return None

    if not isinstance(
        previous,
        Mapping,
    ):
        raise praxis_live_error(
            "previous must be a mapping"
        )

    return previous


def execute(
    payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    if not isinstance(
        payload,
        Mapping,
    ):
        raise praxis_live_error(
            "payload must be a mapping"
        )

    parameters_raw = payload.get(
        "parameters",
        payload,
    )

    if not isinstance(
        parameters_raw,
        Mapping,
    ):
        raise praxis_live_error(
            "parameters must be a mapping"
        )

    parameters = dict(
        parameters_raw
    )

    requested_thrusts = (
        _positive_integer(
            payload.get(
                "requested_thrusts",
                parameters.get(
                    "iterations",
                    1,
                ),
            ),
            field="requested_thrusts",
            maximum=250,
        )
    )

    rigor = _positive_integer(
        payload.get(
            "rigor",
            1,
        ),
        field="rigor",
        maximum=2000,
    )

    target_thrust = (
        _positive_integer(
            payload.get(
                "target_thrust",
                1,
            ),
            field="target_thrust",
            maximum=(
                requested_thrusts
            ),
        )
    )

    target_improvement = (
        normalize_target(
            payload.get(
                "target_improvement_percent",
                15,
            )
        )
    )

    weights = normalize_weights(
        payload.get(
            "weights"
        )
    )

    parameters[
        "iterations"
    ] = requested_thrusts

    baseline_image = _baseline(
        parameters
    )

    previous = _previous_projection(
        payload
    )

    step_payload = {
        "parameters":
            parameters,
        "index":
            target_thrust,
        "previous":
            previous,
    }

    projection = (
        execute_praxis_step(
            step_payload
        )
    )

    candidate_image = _image(
        projection.get(
            "renderer"
        )
    )

    if not candidate_image:
        candidate_image = _image(
            projection
        )

    if not candidate_image:
        raise praxis_live_error(
            "praxis rigor produced no "
            "rendered image"
        )

    common = {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "provider_owner":
            PROVIDER_OWNER,
        "capability":
            CAPABILITY,
        "rigor":
            rigor,
        "target_thrust":
            target_thrust,
        "requested_thrusts":
            requested_thrusts,
        "target_improvement_percent":
            target_improvement,
        "weights":
            weights,
        "projection":
            projection,
        "candidate_image":
            candidate_image,
    }

    if baseline_image is None:
        result = {
            **common,
            "kind":
                "seed",
            "verdict":
                "seed-established",
            "accepted":
                False,
            "qualifies_as_thrust":
                False,
            "seed":
                True,
            "baseline_image":
                candidate_image,
            "evaluation":
                None,
            "next": {
                "rigor":
                    rigor + 1,
                "target_thrust":
                    target_thrust,
                "baseline":
                    candidate_image,
            },
            "lineage": {
                "seed_digest":
                    _digest(
                        candidate_image
                    ),
                "previous_digest":
                    (
                        previous.get(
                            "digest"
                        )
                        if previous
                        else None
                    ),
                "creates_thrust":
                    False,
            },
            "boundaries": {
                "creates_authority":
                    False,
                "model_judgment":
                    False,
                "seed_is_thrust":
                    False,
                "projection_only":
                    True,
            },
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        return result

    objective = str(
        parameters.get(
            "objective",
            "",
        )
    ).strip()

    if not objective:
        raise praxis_live_error(
            "objective is required"
        )

    constraints = _strings(
        parameters.get(
            "constraints"
        )
    )

    invariants = _strings(
        parameters.get(
            "invariants"
        )
    )

    evaluation = (
        evaluate_and_quantify(
            baseline=baseline_image,
            candidate=candidate_image,
            objective=objective,
            target_improvement_percent=(
                target_improvement
            ),
            weights=weights,
            constraints=constraints,
            invariants=invariants,
        )
    )

    qualifies = bool(
        evaluation.get(
            "qualifies_as_thrust"
        )
    )

    if qualifies:
        next_thrust = (
            target_thrust + 1
        )

        complete = (
            target_thrust
            >= requested_thrusts
        )

        next_baseline = (
            candidate_image
        )
    else:
        next_thrust = (
            target_thrust
        )

        complete = False

        next_baseline = (
            baseline_image
        )

    result = {
        **common,
        "kind":
            (
                "thrust"
                if qualifies
                else "rigor"
            ),
        "verdict":
            evaluation.get(
                "verdict"
            ),
        "accepted":
            qualifies,
        "qualifies_as_thrust":
            qualifies,
        "seed":
            False,
        "complete":
            complete,
        "baseline_image":
            baseline_image,
        "evaluation":
            evaluation,
        "next": {
            "rigor":
                rigor + 1,
            "target_thrust":
                (
                    None
                    if complete
                    else next_thrust
                ),
            "baseline":
                next_baseline,
        },
        "lineage": {
            "previous_digest":
                (
                    previous.get(
                        "digest"
                    )
                    if previous
                    else None
                ),
            "baseline_digest":
                _digest(
                    baseline_image
                ),
            "candidate_digest":
                _digest(
                    candidate_image
                ),
            "evaluation_digest":
                evaluation.get(
                    "digest"
                ),
            "accepted_candidate_becomes_baseline":
                qualifies,
            "rejected_candidate_becomes_baseline":
                False,
        },
        "boundaries": {
            "creates_authority":
                False,
            "model_judgment":
                True,
            "objective_measurement":
                False,
            "urge_owns_qualification":
                True,
            "opus_owns_provider_execution":
                True,
            "projection_only":
                True,
        },
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


def register(
    dispatcher: Any,
) -> str:
    if not hasattr(
        dispatcher,
        "register",
    ):
        raise praxis_live_error(
            "dispatcher does not expose register"
        )

    dispatcher.register(
        CAPABILITY,
        execute,
    )

    return CAPABILITY


__all__ = [
    "CAPABILITY",
    "OWNER",
    "PROVIDER_OWNER",
    "SCHEMA",
    "execute",
    "praxis_live_error",
    "register",
]
