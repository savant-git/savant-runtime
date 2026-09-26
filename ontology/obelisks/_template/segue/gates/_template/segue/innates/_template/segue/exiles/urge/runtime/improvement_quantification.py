from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


schema = (
    "savant://runtime/urge/"
    "improvement-quantification/1.0.1"
)

owner = "exile:urge"

minimum_target_percent = 1.0
maximum_target_percent = 30.0

minimum_score = 0.0
maximum_score = 100.0

default_confidence = 0.75
minimum_confidence = 0.0
maximum_confidence = 1.0

default_regression_tolerance = 2.0
maximum_regression_tolerance = 10.0

default_consensus_penalty = 0.35
default_confidence_penalty = 0.25

epsilon = 1e-9


class improvement_error(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class dimension:
    id: str
    label: str
    description: str
    default_weight: float
    hard_gate: bool
    family: str


dimensions = (
    dimension(
        id="artistic_quality",
        label="artistic quality",
        description=(
            "overall aesthetic resolution, "
            "intentionality, visual judgment, "
            "and professional finish"
        ),
        default_weight=1.0,
        hard_gate=False,
        family="aesthetic",
    ),
    dimension(
        id="craftsmanship",
        label="craftsmanship",
        description=(
            "precision, refinement, detail "
            "discipline, edge quality, spacing, "
            "and execution quality"
        ),
        default_weight=0.9,
        hard_gate=False,
        family="execution",
    ),
    dimension(
        id="sophistication",
        label="sophistication",
        description=(
            "depth, restraint, hierarchy, "
            "nuance, and maturity of the design"
        ),
        default_weight=1.0,
        hard_gate=False,
        family="aesthetic",
    ),
    dimension(
        id="concept_novelty",
        label="concept novelty",
        description=(
            "distance from obvious, generic, "
            "derivative, or conventionally "
            "expected solutions"
        ),
        default_weight=1.0,
        hard_gate=False,
        family="concept",
    ),
    dimension(
        id="distinctiveness",
        label="distinctiveness",
        description=(
            "ability to remain recognizably "
            "different from plausible competing "
            "identity solutions"
        ),
        default_weight=1.0,
        hard_gate=False,
        family="concept",
    ),
    dimension(
        id="semantic_density",
        label="semantic density",
        description=(
            "amount of relevant meaning carried "
            "by the design without unnecessary "
            "visual complexity"
        ),
        default_weight=0.9,
        hard_gate=False,
        family="concept",
    ),
    dimension(
        id="brief_alignment",
        label="brief alignment",
        description=(
            "degree to which the result satisfies "
            "the explicit objective, constraints, "
            "identity, and intended character"
        ),
        default_weight=1.0,
        hard_gate=True,
        family="fitness",
    ),
    dimension(
        id="composition",
        label="composition",
        description=(
            "balance, hierarchy, proportion, "
            "rhythm, tension, and spatial logic"
        ),
        default_weight=0.9,
        hard_gate=False,
        family="structure",
    ),
    dimension(
        id="visual_coherence",
        label="visual coherence",
        description=(
            "degree to which all visual decisions "
            "operate as one intentional system"
        ),
        default_weight=0.9,
        hard_gate=False,
        family="structure",
    ),
    dimension(
        id="typography",
        label="typography",
        description=(
            "letterform quality, spacing, "
            "relationship to the mark, hierarchy, "
            "and typographic appropriateness"
        ),
        default_weight=0.8,
        hard_gate=False,
        family="structure",
    ),
    dimension(
        id="legibility",
        label="legibility",
        description=(
            "clarity of intended forms and "
            "lettering across realistic viewing "
            "conditions"
        ),
        default_weight=0.8,
        hard_gate=True,
        family="utility",
    ),
    dimension(
        id="scalability",
        label="scalability",
        description=(
            "ability to retain identity and "
            "clarity from small icon scale to "
            "large-format use"
        ),
        default_weight=0.8,
        hard_gate=True,
        family="utility",
    ),
    dimension(
        id="reproduction",
        label="reproduction",
        description=(
            "robustness under monochrome, limited "
            "color, print, screen, and simplified "
            "production conditions"
        ),
        default_weight=0.75,
        hard_gate=True,
        family="utility",
    ),
    dimension(
        id="memorability",
        label="memorability",
        description=(
            "strength of the design's retrievable "
            "visual signature after brief exposure"
        ),
        default_weight=1.0,
        hard_gate=False,
        family="identity",
    ),
    dimension(
        id="recognizability",
        label="recognizability",
        description=(
            "speed and reliability with which the "
            "identity can be recognized across "
            "contexts and variations"
        ),
        default_weight=0.9,
        hard_gate=False,
        family="identity",
    ),
    dimension(
        id="system_potential",
        label="system potential",
        description=(
            "capacity of the core idea to generate "
            "a coherent broader identity language"
        ),
        default_weight=0.8,
        hard_gate=False,
        family="identity",
    ),
    dimension(
        id="versatility",
        label="versatility",
        description=(
            "ability to survive varied formats, "
            "placements, crops, lockups, and "
            "environmental demands"
        ),
        default_weight=0.75,
        hard_gate=False,
        family="utility",
    ),
    dimension(
        id="economy",
        label="economy",
        description=(
            "amount of identity achieved per "
            "visual element, rewarding meaningful "
            "compression rather than decoration"
        ),
        default_weight=0.8,
        hard_gate=False,
        family="structure",
    ),
    dimension(
        id="intentionality",
        label="intentionality",
        description=(
            "evidence that visible decisions serve "
            "the concept rather than appearing "
            "accidental or arbitrary"
        ),
        default_weight=0.9,
        hard_gate=False,
        family="execution",
    ),
    dimension(
        id="contemporary_relevance",
        label="contemporary relevance",
        description=(
            "fitness for present visual culture "
            "without depending on short-lived "
            "fashion or generic trend mimicry"
        ),
        default_weight=0.6,
        hard_gate=False,
        family="fitness",
    ),
)


dimension_by_id = {
    item.id: item
    for item in dimensions
}


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
        raise improvement_error(
            "improvement projection must be "
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


def _number(
    value: Any,
    *,
    field: str,
    minimum: float,
    maximum: float,
) -> float:
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise improvement_error(
            f"{field} must be numeric"
        ) from exc

    if not math.isfinite(
        result
    ):
        raise improvement_error(
            f"{field} must be finite"
        )

    if (
        result < minimum
        or result > maximum
    ):
        raise improvement_error(
            f"{field} must be between "
            f"{minimum:g} and {maximum:g}"
        )

    return result


def _score(
    value: Any,
    *,
    field: str,
) -> float:
    return _number(
        value,
        field=field,
        minimum=minimum_score,
        maximum=maximum_score,
    )


def normalize_target(
    value: Any,
) -> float:
    return _number(
        value,
        field=(
            "target_improvement_percent"
        ),
        minimum=minimum_target_percent,
        maximum=maximum_target_percent,
    )


def normalize_weights(
    value: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, float]:
    explicit = (
        value is not None
    )

    if explicit and not isinstance(
        value,
        Mapping,
    ):
        raise improvement_error(
            "weights must be a mapping"
        )

    requested = (
        dict(
            value
        )
        if explicit
        else {}
    )

    unknown = (
        set(
            requested
        )
        - set(
            dimension_by_id
        )
    )

    if unknown:
        raise improvement_error(
            "unknown improvement dimensions: "
            + ", ".join(
                sorted(
                    unknown
                )
            )
        )

    output: dict[
        str,
        float,
    ] = {}

    if explicit:
        candidates = (
            (
                dimension_by_id[
                    dimension_id
                ],
                raw_weight,
            )
            for (
                dimension_id,
                raw_weight,
            )
            in requested.items()
        )
    else:
        candidates = (
            (
                item,
                item.default_weight,
            )
            for item in dimensions
        )

    for item, raw in candidates:
        weight = _number(
            raw,
            field=(
                "weight."
                + item.id
            ),
            minimum=0.0,
            maximum=10.0,
        )

        if weight > 0.0:
            output[
                item.id
            ] = weight

    if not output:
        raise improvement_error(
            "at least one improvement "
            "dimension must be enabled"
        )

    total = sum(
        output.values()
    )

    return {
        key:
            weight / total
        for key, weight
        in output.items()
    }


def dimension_projection() -> list[
    dict[str, Any]
]:
    return [
        {
            "id":
                item.id,
            "label":
                item.label,
            "description":
                item.description,
            "default_weight":
                item.default_weight,
            "hard_gate":
                item.hard_gate,
            "family":
                item.family,
        }
        for item in dimensions
    ]


def _median(
    values: Sequence[
        float
    ],
) -> float:
    if not values:
        raise improvement_error(
            "median requires values"
        )

    return float(
        statistics.median(
            values
        )
    )


def _mad(
    values: Sequence[
        float
    ],
    center: float,
) -> float:
    if len(
        values
    ) < 2:
        return 0.0

    return float(
        statistics.median(
            [
                abs(
                    value
                    - center
                )
                for value
                in values
            ]
        )
    )


def _headroom_improvement(
    baseline: float,
    candidate: float,
) -> float:
    delta = (
        candidate
        - baseline
    )

    if abs(
        delta
    ) <= epsilon:
        return 0.0

    if delta > 0.0:
        headroom = max(
            maximum_score
            - baseline,
            1.0,
        )

        return min(
            maximum_target_percent,
            (
                delta
                / headroom
            )
            * maximum_target_percent,
        )

    available_loss = max(
        baseline,
        1.0,
    )

    return max(
        -maximum_target_percent,
        (
            delta
            / available_loss
        )
        * maximum_target_percent,
    )


def _weighted_mean(
    values: Mapping[
        str,
        float,
    ],
    weights: Mapping[
        str,
        float,
    ],
) -> float:
    numerator = 0.0
    denominator = 0.0

    for key, weight in (
        weights.items()
    ):
        if key not in values:
            continue

        numerator += (
            values[
                key
            ]
            * weight
        )

        denominator += weight

    if denominator <= epsilon:
        raise improvement_error(
            "no weighted values available"
        )

    return (
        numerator
        / denominator
    )


def _weighted_harmonic_positive(
    values: Mapping[
        str,
        float,
    ],
    weights: Mapping[
        str,
        float,
    ],
) -> float:
    numerator = 0.0
    denominator = 0.0

    for key, weight in (
        weights.items()
    ):
        if key not in values:
            continue

        candidate = max(
            values[
                key
            ],
            0.0,
        )

        numerator += weight

        denominator += (
            weight
            / max(
                candidate,
                0.25,
            )
        )

    if (
        numerator <= epsilon
        or denominator <= epsilon
    ):
        return 0.0

    return (
        numerator
        / denominator
    )


def _judge_projection(
    judge: Mapping[
        str,
        Any,
    ],
    *,
    selected:
        set[str],
    dimensions_seen:
        dict[
            str,
            dict[
                str,
                list[
                    float
                ],
            ],
        ],
) -> dict[str, Any]:
    judge_id = str(
        judge.get(
            "id",
            "",
        )
    ).strip()

    if not judge_id:
        raise improvement_error(
            "judge id is required"
        )

    confidence = _number(
        judge.get(
            "confidence",
            default_confidence,
        ),
        field=(
            "judge."
            + judge_id
            + ".confidence"
        ),
        minimum=minimum_confidence,
        maximum=maximum_confidence,
    )

    scores = judge.get(
        "scores"
    )

    if not isinstance(
        scores,
        Mapping,
    ):
        raise improvement_error(
            "judge scores must be a mapping"
        )

    normalized_scores: dict[
        str,
        dict[str, float],
    ] = {}

    for dimension_id in (
        selected
    ):
        pair = scores.get(
            dimension_id
        )

        if not isinstance(
            pair,
            Mapping,
        ):
            raise improvement_error(
                "judge "
                + judge_id
                + " is missing "
                + dimension_id
            )

        baseline = _score(
            pair.get(
                "baseline"
            ),
            field=(
                "judge."
                + judge_id
                + "."
                + dimension_id
                + ".baseline"
            ),
        )

        candidate = _score(
            pair.get(
                "candidate"
            ),
            field=(
                "judge."
                + judge_id
                + "."
                + dimension_id
                + ".candidate"
            ),
        )

        dimensions_seen[
            dimension_id
        ][
            "baseline"
        ].append(
            baseline
        )

        dimensions_seen[
            dimension_id
        ][
            "candidate"
        ].append(
            candidate
        )

        dimensions_seen[
            dimension_id
        ][
            "confidence"
        ].append(
            confidence
        )

        normalized_scores[
            dimension_id
        ] = {
            "baseline":
                baseline,
            "candidate":
                candidate,
        }

    return {
        "id":
            judge_id,
        "confidence":
            confidence,
        "scores":
            normalized_scores,
        "evidence_digest":
            str(
                judge.get(
                    "evidence_digest",
                    "",
                )
            ).strip()
            or None,
        "provider":
            str(
                judge.get(
                    "provider",
                    "",
                )
            ).strip()
            or None,
        "model":
            str(
                judge.get(
                    "model",
                    "",
                )
            ).strip()
            or None,
    }


def quantify(
    *,
    target_improvement_percent:
        float,
    judges: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
    weights: Mapping[
        str,
        Any,
    ] | None = None,
    regression_tolerance:
        float = (
            default_regression_tolerance
        ),
    consensus_penalty:
        float = (
            default_consensus_penalty
        ),
    confidence_penalty:
        float = (
            default_confidence_penalty
        ),
) -> dict[str, Any]:
    target = normalize_target(
        target_improvement_percent
    )

    normalized_weights = (
        normalize_weights(
            weights
        )
    )

    regression_tolerance = (
        _number(
            regression_tolerance,
            field=(
                "regression_tolerance"
            ),
            minimum=0.0,
            maximum=(
                maximum_regression_tolerance
            ),
        )
    )

    consensus_penalty = (
        _number(
            consensus_penalty,
            field=(
                "consensus_penalty"
            ),
            minimum=0.0,
            maximum=1.0,
        )
    )

    confidence_penalty = (
        _number(
            confidence_penalty,
            field=(
                "confidence_penalty"
            ),
            minimum=0.0,
            maximum=1.0,
        )
    )

    if (
        not isinstance(
            judges,
            Sequence,
        )
        or isinstance(
            judges,
            (
                str,
                bytes,
                bytearray,
            ),
        )
        or not judges
    ):
        raise improvement_error(
            "at least one judge is required"
        )

    selected = set(
        normalized_weights
    )

    dimensions_seen = {
        dimension_id: {
            "baseline": [],
            "candidate": [],
            "confidence": [],
        }
        for dimension_id
        in selected
    }

    normalized_judges: list[
        dict[str, Any]
    ] = []

    judge_ids: set[str] = set()

    for raw_judge in judges:
        if not isinstance(
            raw_judge,
            Mapping,
        ):
            raise improvement_error(
                "each judge must be a mapping"
            )

        projected = (
            _judge_projection(
                raw_judge,
                selected=selected,
                dimensions_seen=(
                    dimensions_seen
                ),
            )
        )

        judge_id = projected[
            "id"
        ]

        if judge_id in judge_ids:
            raise improvement_error(
                "duplicate judge id: "
                + judge_id
            )

        judge_ids.add(
            judge_id
        )

        normalized_judges.append(
            projected
        )

    dimension_results: dict[
        str,
        dict[str, Any],
    ] = {}

    conservative_values: dict[
        str,
        float,
    ] = {}

    raw_values: dict[
        str,
        float,
    ] = {}

    regressions: list[
        str
    ] = []

    hard_gate_failures: list[
        str
    ] = []

    for dimension_id in sorted(
        selected
    ):
        values = (
            dimensions_seen[
                dimension_id
            ]
        )

        baseline = _median(
            values[
                "baseline"
            ]
        )

        candidate = _median(
            values[
                "candidate"
            ]
        )

        baseline_mad = _mad(
            values[
                "baseline"
            ],
            baseline,
        )

        candidate_mad = _mad(
            values[
                "candidate"
            ],
            candidate,
        )

        disagreement = min(
            1.0,
            (
                baseline_mad
                + candidate_mad
            )
            / 50.0,
        )

        confidence = _median(
            values[
                "confidence"
            ]
        )

        raw_improvement = (
            _headroom_improvement(
                baseline,
                candidate,
            )
        )

        uncertainty = (
            maximum_target_percent
            * (
                (
                    disagreement
                    * consensus_penalty
                )
                + (
                    (
                        1.0
                        - confidence
                    )
                    * confidence_penalty
                )
            )
        )

        if raw_improvement >= 0:
            conservative = max(
                0.0,
                raw_improvement
                - uncertainty,
            )
        else:
            conservative = min(
                0.0,
                raw_improvement
                - uncertainty,
            )

        definition = (
            dimension_by_id[
                dimension_id
            ]
        )

        regressed = (
            conservative
            < -regression_tolerance
        )

        hard_gate_failed = (
            definition.hard_gate
            and regressed
        )

        if regressed:
            regressions.append(
                dimension_id
            )

        if hard_gate_failed:
            hard_gate_failures.append(
                dimension_id
            )

        raw_values[
            dimension_id
        ] = raw_improvement

        conservative_values[
            dimension_id
        ] = conservative

        dimension_results[
            dimension_id
        ] = {
            "id":
                dimension_id,
            "label":
                definition.label,
            "family":
                definition.family,
            "weight":
                normalized_weights[
                    dimension_id
                ],
            "hard_gate":
                definition.hard_gate,
            "baseline_score":
                round(
                    baseline,
                    4,
                ),
            "candidate_score":
                round(
                    candidate,
                    4,
                ),
            "score_delta":
                round(
                    candidate
                    - baseline,
                    4,
                ),
            "raw_improvement_percent":
                round(
                    raw_improvement,
                    4,
                ),
            "uncertainty_penalty":
                round(
                    uncertainty,
                    4,
                ),
            "conservative_improvement_percent":
                round(
                    conservative,
                    4,
                ),
            "confidence":
                round(
                    confidence,
                    4,
                ),
            "disagreement":
                round(
                    disagreement,
                    4,
                ),
            "regressed":
                regressed,
            "hard_gate_failed":
                hard_gate_failed,
        }

    weighted_raw = (
        _weighted_mean(
            raw_values,
            normalized_weights,
        )
    )

    weighted_conservative = (
        _weighted_mean(
            conservative_values,
            normalized_weights,
        )
    )

    balanced_conservative = (
        _weighted_harmonic_positive(
            conservative_values,
            normalized_weights,
        )
    )

    negative_pressure = sum(
        abs(
            min(
                candidate,
                0.0,
            )
        )
        * normalized_weights[
            key
        ]
        for key, candidate
        in conservative_values.items()
    )

    aggregate = max(
        0.0,
        min(
            maximum_target_percent,
            (
                (
                    weighted_conservative
                    * 0.65
                )
                + (
                    balanced_conservative
                    * 0.35
                )
                - negative_pressure
            ),
        ),
    )

    judge_confidence = (
        _median(
            [
                item[
                    "confidence"
                ]
                for item
                in normalized_judges
            ]
        )
    )

    qualification_margin = (
        aggregate
        - target
    )

    qualifies = (
        aggregate
        + epsilon
        >= target
        and not hard_gate_failures
    )

    if qualifies:
        verdict = "thrust"
    elif hard_gate_failures:
        verdict = (
            "rigor-rejected-regression"
        )
    else:
        verdict = (
            "rigor-rejected-improvement"
        )

    result = {
        "schema":
            schema,
        "owner":
            owner,
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
        "target_improvement_percent":
            round(
                target,
                4,
            ),
        "aggregate": {
            "raw_improvement_percent":
                round(
                    weighted_raw,
                    4,
                ),
            "conservative_improvement_percent":
                round(
                    aggregate,
                    4,
                ),
            "weighted_conservative_percent":
                round(
                    weighted_conservative,
                    4,
                ),
            "balanced_conservative_percent":
                round(
                    balanced_conservative,
                    4,
                ),
            "qualification_margin_percent":
                round(
                    qualification_margin,
                    4,
                ),
            "judge_confidence":
                round(
                    judge_confidence,
                    4,
                ),
        },
        "dimensions":
            dimension_results,
        "regressions":
            sorted(
                regressions
            ),
        "hard_gate_failures":
            sorted(
                hard_gate_failures
            ),
        "weights": {
            key:
                round(
                    candidate,
                    8,
                )
            for key, candidate
            in sorted(
                normalized_weights.items()
            )
        },
        "judges":
            normalized_judges,
        "method": {
            "comparison":
                "paired-baseline-candidate",
            "score_range":
                [0, 100],
            "target_range_percent":
                [
                    minimum_target_percent,
                    maximum_target_percent,
                ],
            "improvement_normalization":
                "remaining-headroom",
            "aggregation":
                (
                    "65% weighted conservative "
                    "+ 35% balanced harmonic "
                    "- regression pressure"
                ),
            "uncertainty":
                (
                    "median absolute disagreement "
                    "+ evaluator confidence"
                ),
            "qualification":
                (
                    "conservative aggregate clears "
                    "target and no hard gate fails"
                ),
            "authority_effect":
                "none",
            "projection_only":
                True,
        },
        "boundaries": {
            "objective_measurement":
                False,
            "model_judgment":
                True,
            "creates_authority":
                False,
            "mutates_canon":
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


def adaptive_rigor_budget(
    *,
    requested_thrusts: int,
    target_improvement_percent:
        float,
) -> int:
    try:
        thrusts = int(
            requested_thrusts
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise improvement_error(
            "requested_thrusts must be "
            "an integer"
        ) from exc

    if (
        thrusts < 1
        or thrusts > 250
    ):
        raise improvement_error(
            "requested_thrusts must be "
            "between 1 and 250"
        )

    target = normalize_target(
        target_improvement_percent
    )

    difficulty = (
        target
        / maximum_target_percent
    )

    attempts_per_thrust = (
        2
        + math.ceil(
            difficulty
            * 6
        )
    )

    return min(
        2000,
        thrusts
        * attempts_per_thrust,
    )


def ui_projection() -> dict[
    str,
    Any,
]:
    return {
        "schema":
            schema,
        "terminology": {
            "raw_attempt":
                "rigor",
            "accepted_iteration":
                "thrust",
            "session":
                "praxis",
            "sessions":
                "praxi",
        },
        "target": {
            "minimum":
                minimum_target_percent,
            "maximum":
                maximum_target_percent,
            "default":
                15.0,
            "presets": [
                {
                    "value": 5,
                    "label": "subtle",
                },
                {
                    "value": 10,
                    "label": "measured",
                },
                {
                    "value": 15,
                    "label": "substantial",
                },
                {
                    "value": 20,
                    "label": "aggressive",
                },
                {
                    "value": 25,
                    "label": "transformative",
                },
                {
                    "value": 30,
                    "label": "maximum",
                },
            ],
        },
        "dimensions":
            dimension_projection(),
        "interaction": {
            "primary_control":
                "improvement-pressure",
            "dimension_weights":
                True,
            "dimension_enablement":
                True,
            "live_rigor_evidence":
                True,
            "live_thrust_qualification":
                True,
            "rejected_rigors_visible":
                True,
            "uncertainty_visible":
                True,
            "regression_visible":
                True,
            "qualification_margin_visible":
                True,
            "judge_disagreement_visible":
                True,
            "immutable_history":
                True,
        },
    }


__all__ = [
    "adaptive_rigor_budget",
    "dimension_projection",
    "dimensions",
    "improvement_error",
    "maximum_target_percent",
    "minimum_target_percent",
    "normalize_target",
    "normalize_weights",
    "owner",
    "quantify",
    "schema",
    "ui_projection",
]
