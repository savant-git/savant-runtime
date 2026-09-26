from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from ...opus.runtime.resilient_text import (
    execute_text_request_resilient,
)
from .improvement_quantification import (
    dimension_by_id,
    normalize_weights,
    quantify,
)


schema = (
    "savant://runtime/urge/"
    "visual-evaluator/1.0.0"
)

owner = "exile:urge"
provider_owner = "exile:opus"

default_model = "gpt-5.6-sol"


class visual_evaluation_error(
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
        raise visual_evaluation_error(
            "visual evaluation value must "
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


def _mapping(
    value: Any,
    *,
    field: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise visual_evaluation_error(
            field
            + " must be a mapping"
        )

    return value


def _image_source(
    value: Any,
    *,
    field: str,
) -> str:
    if isinstance(
        value,
        str,
    ):
        source = value.strip()
    elif isinstance(
        value,
        Mapping,
    ):
        source = str(
            value.get(
                "source"
            )
            or value.get(
                "url"
            )
            or value.get(
                "image"
            )
            or value.get(
                "image_url"
            )
            or ""
        ).strip()
    else:
        source = ""

    if not source:
        raise visual_evaluation_error(
            field
            + " image source is required"
        )

    if not (
        source.startswith(
            "https://"
        )
        or source.startswith(
            "http://"
        )
        or source.startswith(
            "data:image/"
        )
    ):
        raise visual_evaluation_error(
            field
            + " must be an http(s) URL "
            "or image data URL"
        )

    return source


def _extract_json(
    text: str,
) -> Mapping[str, Any]:
    source = str(
        text
        or ""
    ).strip()

    if not source:
        raise visual_evaluation_error(
            "evaluator returned empty text"
        )

    try:
        value = json.loads(
            source
        )

        if isinstance(
            value,
            Mapping,
        ):
            return value
    except json.JSONDecodeError:
        pass

    if source.startswith(
        "```"
    ):
        lines = source.splitlines()

        if lines:
            lines = lines[
                1:
            ]

        if (
            lines
            and lines[
                -1
            ].strip().startswith(
                "```"
            )
        ):
            lines = lines[
                :-1
            ]

        source = "\n".join(
            lines
        ).strip()

        if source.lower().startswith(
            "json\n"
        ):
            source = source[
                5:
            ].strip()

        try:
            value = json.loads(
                source
            )

            if isinstance(
                value,
                Mapping,
            ):
                return value
        except json.JSONDecodeError:
            pass

    start = source.find(
        "{"
    )

    end = source.rfind(
        "}"
    )

    if (
        start >= 0
        and end > start
    ):
        try:
            value = json.loads(
                source[
                    start:
                    end + 1
                ]
            )

            if isinstance(
                value,
                Mapping,
            ):
                return value
        except json.JSONDecodeError:
            pass

    raise visual_evaluation_error(
        "evaluator did not return "
        "a valid JSON object"
    )


def _dimension_contract(
    weights: Mapping[
        str,
        float,
    ],
) -> list[dict[str, Any]]:
    return [
        {
            "id":
                dimension_id,
            "label":
                dimension_by_id[
                    dimension_id
                ].label,
            "description":
                dimension_by_id[
                    dimension_id
                ].description,
            "family":
                dimension_by_id[
                    dimension_id
                ].family,
            "hard_gate":
                dimension_by_id[
                    dimension_id
                ].hard_gate,
            "weight":
                weight,
        }
        for dimension_id, weight
        in sorted(
            weights.items()
        )
    ]


def _evaluation_prompt(
    *,
    objective: str,
    dimensions: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
    constraints: Sequence[str],
    invariants: Sequence[str],
) -> str:
    contract = _canonical(
        dimensions
    )

    constraint_text = (
        "\n".join(
            "- " + item
            for item in constraints
        )
        if constraints
        else "- none supplied"
    )

    invariant_text = (
        "\n".join(
            "- " + item
            for item in invariants
        )
        if invariants
        else "- none supplied"
    )

    return (
        "You are an expert comparative "
        "visual-design evaluator operating "
        "inside Savant Urge.\n\n"
        "Two images follow. The image labeled "
        "'baseline' is the preceding accepted "
        "state. The image labeled 'candidate' "
        "is the new raw rigor.\n\n"
        "Objective:\n"
        + objective
        + "\n\nConstraints:\n"
        + constraint_text
        + "\n\nProtected invariants:\n"
        + invariant_text
        + "\n\nEvaluate only these dimensions:\n"
        + contract
        + "\n\nFor every dimension, independently "
        "score BOTH baseline and candidate from "
        "0 through 100. Use the entire scale. "
        "Do not award points merely because the "
        "candidate is different. Penalize novelty "
        "that damages fitness, coherence, "
        "legibility, or protected invariants. "
        "Judge the actual visible evidence rather "
        "than the stated intention.\n\n"
        "Confidence must be between 0 and 1 and "
        "represent confidence in the comparative "
        "visual judgment.\n\n"
        "Return JSON only. Do not use markdown. "
        "Use exactly this structure:\n"
        "{"
        "\"confidence\":0.0,"
        "\"scores\":{"
        "\"dimension_id\":{"
        "\"baseline\":0.0,"
        "\"candidate\":0.0"
        "}"
        "},"
        "\"summary\":\"brief comparative reason\","
        "\"invariant_failures\":[]"
        "}"
    )


def _normalize_scores(
    value: Mapping[
        str,
        Any,
    ],
    *,
    selected:
        Sequence[str],
) -> dict[str, dict[str, float]]:
    scores_raw = _mapping(
        value.get(
            "scores"
        ),
        field="scores",
    )

    result: dict[
        str,
        dict[str, float],
    ] = {}

    for dimension_id in selected:
        pair = _mapping(
            scores_raw.get(
                dimension_id
            ),
            field=(
                "scores."
                + dimension_id
            ),
        )

        normalized: dict[
            str,
            float,
        ] = {}

        for side in (
            "baseline",
            "candidate",
        ):
            try:
                score = float(
                    pair.get(
                        side
                    )
                )
            except (
                TypeError,
                ValueError,
            ) as exc:
                raise visual_evaluation_error(
                    "scores."
                    + dimension_id
                    + "."
                    + side
                    + " must be numeric"
                ) from exc

            if not (
                0.0
                <= score
                <= 100.0
            ):
                raise visual_evaluation_error(
                    "scores."
                    + dimension_id
                    + "."
                    + side
                    + " must be between "
                    "0 and 100"
                )

            normalized[
                side
            ] = score

        result[
            dimension_id
        ] = normalized

    return result


def evaluate_once(
    *,
    baseline: Any,
    candidate: Any,
    objective: str,
    weights: Mapping[
        str,
        Any,
    ] | None = None,
    constraints: Sequence[str] = (),
    invariants: Sequence[str] = (),
    judge_id: str = "opus-visual-judge",
    model: str = default_model,
) -> dict[str, Any]:
    baseline_source = _image_source(
        baseline,
        field="baseline",
    )

    candidate_source = _image_source(
        candidate,
        field="candidate",
    )

    normalized_weights = (
        normalize_weights(
            weights
        )
    )

    selected = sorted(
        normalized_weights
    )

    contract = _dimension_contract(
        normalized_weights
    )

    request = {
        "owner":
            owner,
        "model":
            model,
        "required_capabilities": [
            "text_inference",
            "image_input",
            "paired_visual_evaluation",
        ],
        "system": (
            "Return only the requested "
            "machine-readable JSON evaluation. "
            "Do not create authority. "
            "Do not modify either image."
        ),
        "message":
            _evaluation_prompt(
                objective=str(
                    objective
                    or ""
                ).strip(),
                dimensions=contract,
                constraints=tuple(
                    str(item).strip()
                    for item in constraints
                    if str(
                        item
                    ).strip()
                ),
                invariants=tuple(
                    str(item).strip()
                    for item in invariants
                    if str(
                        item
                    ).strip()
                ),
            ),
        "input_images": [
            {
                "label":
                    "baseline",
                "source":
                    baseline_source,
                "detail":
                    "high",
            },
            {
                "label":
                    "candidate",
                "source":
                    candidate_source,
                "detail":
                    "high",
            },
        ],
    }

    provider_result = (
        execute_text_request_resilient(
            request
        )
    )

    parsed = _extract_json(
        str(
            provider_result.get(
                "text"
            )
            or ""
        )
    )

    scores = _normalize_scores(
        parsed,
        selected=selected,
    )

    try:
        confidence = float(
            parsed.get(
                "confidence",
                0.75,
            )
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise visual_evaluation_error(
            "confidence must be numeric"
        ) from exc

    confidence = max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )

    invariant_failures_raw = (
        parsed.get(
            "invariant_failures"
        )
    )

    invariant_failures = (
        [
            str(item).strip()
            for item
            in invariant_failures_raw
            if str(
                item
            ).strip()
        ]
        if isinstance(
            invariant_failures_raw,
            list,
        )
        else []
    )

    evidence = {
        "schema":
            schema,
        "owner":
            owner,
        "provider_owner":
            provider_owner,
        "judge_id":
            judge_id,
        "provider":
            provider_result.get(
                "provider"
            ),
        "model":
            provider_result.get(
                "model"
            ),
        "provider_response_id":
            provider_result.get(
                "provider_response_id"
            ),
        "confidence":
            confidence,
        "scores":
            scores,
        "summary":
            str(
                parsed.get(
                    "summary"
                )
                or ""
            ).strip(),
        "invariant_failures":
            invariant_failures,
        "baseline_digest":
            _digest(
                baseline_source
            ),
        "candidate_digest":
            _digest(
                candidate_source
            ),
        "dimensions":
            selected,
        "lineage":
            provider_result.get(
                "lineage"
            ),
        "boundaries": {
            "creates_authority":
                False,
            "model_judgment":
                True,
            "objective_measurement":
                False,
            "projection_only":
                True,
        },
    }

    evidence[
        "digest"
    ] = _digest(
        evidence
    )

    return evidence


def evaluate_and_quantify(
    *,
    baseline: Any,
    candidate: Any,
    objective: str,
    target_improvement_percent:
        float,
    weights: Mapping[
        str,
        Any,
    ] | None = None,
    constraints: Sequence[str] = (),
    invariants: Sequence[str] = (),
    model: str = default_model,
) -> dict[str, Any]:
    evidence = evaluate_once(
        baseline=baseline,
        candidate=candidate,
        objective=objective,
        weights=weights,
        constraints=constraints,
        invariants=invariants,
        model=model,
    )

    judge = {
        "id":
            evidence[
                "judge_id"
            ],
        "provider":
            evidence.get(
                "provider"
            ),
        "model":
            evidence.get(
                "model"
            ),
        "confidence":
            evidence[
                "confidence"
            ],
        "scores":
            evidence[
                "scores"
            ],
        "evidence_digest":
            evidence[
                "digest"
            ],
    }

    quantification = quantify(
        target_improvement_percent=(
            target_improvement_percent
        ),
        judges=[
            judge
        ],
        weights=weights,
    )

    invariant_failures = (
        evidence[
            "invariant_failures"
        ]
    )

    qualifies = bool(
        quantification[
            "qualifies_as_thrust"
        ]
        and not invariant_failures
    )

    if invariant_failures:
        verdict = (
            "rigor-rejected-invariant"
        )
    else:
        verdict = (
            quantification[
                "verdict"
            ]
        )

    result = {
        "schema":
            schema,
        "owner":
            owner,
        "provider_owner":
            provider_owner,
        "kind":
            (
                "thrust"
                if qualifies
                else "rigor"
            ),
        "verdict":
            verdict,
        "qualifies_as_thrust":
            qualifies,
        "evidence":
            evidence,
        "quantification":
            quantification,
        "invariant_failures":
            invariant_failures,
        "boundaries": {
            "creates_authority":
                False,
            "model_judgment":
                True,
            "objective_measurement":
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


__all__ = [
    "default_model",
    "evaluate_and_quantify",
    "evaluate_once",
    "owner",
    "provider_owner",
    "schema",
    "visual_evaluation_error",
]
