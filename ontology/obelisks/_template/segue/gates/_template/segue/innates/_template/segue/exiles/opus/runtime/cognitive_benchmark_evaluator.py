from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Sequence


def _normalized(
    text: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text).strip().lower(),
    )


def _contains(
    text: str,
    fragment: str,
) -> bool:
    return (
        _normalized(fragment)
        in _normalized(text)
    )


def _expected_score(
    text: str,
    expected: Sequence[str],
) -> float:
    values = [
        str(value).strip()
        for value in expected
        if str(value).strip()
    ]

    if not values:
        return 1.0

    matched = sum(
        1
        for value in values
        if _contains(
            text,
            value,
        )
    )

    return matched / len(
        values
    )


def _forbidden_score(
    text: str,
    forbidden: Sequence[str],
) -> float:
    values = [
        str(value).strip()
        for value in forbidden
        if str(value).strip()
    ]

    if not values:
        return 1.0

    violations = sum(
        1
        for value in values
        if _contains(
            text,
            value,
        )
    )

    return max(
        0.0,
        1.0
        - (
            violations
            / len(values)
        ),
    )


def _constraint_score(
    case_id: str,
    text: str,
) -> float:
    if case_id != "constraint_satisfaction":
        return 1.0

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return (
        1.0
        if lines
        == [
            "shade",
            "segue",
            "projection",
        ]
        else 0.0
    )


def evaluate_output(
    *,
    case_id: str,
    text: str,
    ok: bool,
    expected_constraints: Sequence[str],
    forbidden_claims: Sequence[str],
) -> Dict[str, Any]:
    if not ok:
        return {
            "expected_coverage": 0.0,
            "forbidden_claim_control": 0.0,
            "constraint_exactness": 0.0,
            "validation_success": 0.0,
            "deterministic_score": 0.0,
        }

    expected = _expected_score(
        text,
        expected_constraints,
    )

    forbidden = _forbidden_score(
        text,
        forbidden_claims,
    )

    constraint = _constraint_score(
        case_id,
        text,
    )

    validation = (
        1.0
        if text.strip()
        else 0.0
    )

    deterministic_score = (
        expected * 0.35
        + forbidden * 0.30
        + constraint * 0.20
        + validation * 0.15
    )

    return {
        "expected_coverage":
            round(expected, 6),
        "forbidden_claim_control":
            round(forbidden, 6),
        "constraint_exactness":
            round(constraint, 6),
        "validation_success":
            round(validation, 6),
        "deterministic_score":
            round(
                deterministic_score,
                6,
            ),
    }


def evaluate_pair(
    pair: Mapping[str, Any],
) -> Dict[str, Any]:
    expected = pair.get(
        "expected_constraints"
    ) or ()

    forbidden = pair.get(
        "forbidden_claims"
    ) or ()

    basic = pair.get(
        "basic"
    ) or {}

    opus = pair.get(
        "opus"
    ) or {}

    basic_eval = evaluate_output(
        case_id=str(
            pair.get(
                "case_id"
            )
            or ""
        ),
        text=str(
            basic.get(
                "text"
            )
            or ""
        ),
        ok=bool(
            basic.get(
                "ok"
            )
        ),
        expected_constraints=expected,
        forbidden_claims=forbidden,
    )

    opus_eval = evaluate_output(
        case_id=str(
            pair.get(
                "case_id"
            )
            or ""
        ),
        text=str(
            opus.get(
                "text"
            )
            or ""
        ),
        ok=bool(
            opus.get(
                "ok"
            )
        ),
        expected_constraints=expected,
        forbidden_claims=forbidden,
    )

    delta = (
        opus_eval[
            "deterministic_score"
        ]
        - basic_eval[
            "deterministic_score"
        ]
    )

    return {
        "case_id":
            pair.get(
                "case_id"
            ),
        "category":
            pair.get(
                "category"
            ),
        "basic":
            basic_eval,
        "opus":
            opus_eval,
        "score_delta":
            round(
                delta,
                6,
            ),
        "opus_better":
            delta > 0.0,
        "equal":
            delta == 0.0,
        "basic_better":
            delta < 0.0,
    }


def evaluate_suite(
    raw: Mapping[str, Any],
) -> Dict[str, Any]:
    evaluations = [
        evaluate_pair(
            pair
        )
        for pair in (
            raw.get(
                "results"
            )
            or ()
        )
    ]

    basic_scores = [
        value["basic"][
            "deterministic_score"
        ]
        for value in evaluations
    ]

    opus_scores = [
        value["opus"][
            "deterministic_score"
        ]
        for value in evaluations
    ]

    basic_mean = (
        sum(basic_scores)
        / len(basic_scores)
        if basic_scores
        else 0.0
    )

    opus_mean = (
        sum(opus_scores)
        / len(opus_scores)
        if opus_scores
        else 0.0
    )

    delta = (
        opus_mean
        - basic_mean
    )

    wins = sum(
        1
        for value in evaluations
        if value[
            "opus_better"
        ]
    )

    losses = sum(
        1
        for value in evaluations
        if value[
            "basic_better"
        ]
    )

    ties = sum(
        1
        for value in evaluations
        if value[
            "equal"
        ]
    )

    return {
        "schema":
            "opus.cognitive.benchmark.evaluation.v1",
        "case_count":
            len(evaluations),
        "basic_mean":
            round(
                basic_mean,
                6,
            ),
        "opus_mean":
            round(
                opus_mean,
                6,
            ),
        "mean_delta":
            round(
                delta,
                6,
            ),
        "opus_wins":
            wins,
        "basic_wins":
            losses,
        "ties":
            ties,
        "deterministic_improvement_observed":
            bool(
                evaluations
                and delta > 0.0
                and wins > losses
            ),
        "evaluations":
            evaluations,
    }
