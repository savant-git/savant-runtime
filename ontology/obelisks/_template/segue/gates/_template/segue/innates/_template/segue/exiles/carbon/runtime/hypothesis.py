#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from simulation import OWNER, clone, digest


SCHEMA = "savant://carbon/hypothesis/1"


class HypothesisError(RuntimeError):
    pass


Predicate = Callable[
    [Mapping[str, Any]],
    bool,
]


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def stable_id(
    prefix: str,
    material: Any,
) -> str:
    return (
        prefix
        + ":"
        + hashlib.sha256(
            canonical(material).encode(
                "utf-8"
            )
        ).hexdigest()[:24]
    )


def numeric(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def values_of(
    state: Mapping[str, Any],
) -> Mapping[str, Any]:
    values = state.get("values")

    if isinstance(values, Mapping):
        return values

    return state


@dataclass(frozen=True, slots=True)
class Hypothesis:
    id: str
    name: str
    description: str
    metric: str
    operator: str
    expected: Any
    tolerance: float
    minimum_support: int
    tags: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": (
                self.description
            ),
            "metric": self.metric,
            "operator": self.operator,
            "expected": clone(
                self.expected
            ),
            "tolerance": (
                self.tolerance
            ),
            "minimum_support": (
                self.minimum_support
            ),
            "tags": list(
                self.tags
            ),
        }


class HypothesisEngine:
    OPERATORS = frozenset(
        {
            "eq",
            "ne",
            "gt",
            "gte",
            "lt",
            "lte",
            "within",
            "exists",
            "absent",
        }
    )

    def define(
        self,
        name: str,
        *,
        metric: str,
        operator: str,
        expected: Any = None,
        tolerance: float = 0.0,
        minimum_support: int = 1,
        description: str = "",
        tags: Sequence[str] = (),
    ) -> Hypothesis:
        normalized_name = str(
            name or ""
        ).strip()

        normalized_metric = str(
            metric or ""
        ).strip()

        normalized_operator = str(
            operator or ""
        ).strip().lower()

        if not normalized_name:
            raise HypothesisError(
                "hypothesis name is required"
            )

        if not normalized_metric:
            raise HypothesisError(
                "hypothesis metric is required"
            )

        if (
            normalized_operator
            not in self.OPERATORS
        ):
            raise HypothesisError(
                "unsupported hypothesis operator"
            )

        normalized_tolerance = float(
            tolerance
        )

        if normalized_tolerance < 0:
            raise HypothesisError(
                "tolerance cannot be negative"
            )

        normalized_support = int(
            minimum_support
        )

        if normalized_support < 1:
            raise HypothesisError(
                "minimum_support must be "
                "at least one"
            )

        normalized_tags = tuple(
            sorted(
                {
                    str(tag).strip()
                    for tag in tags
                    if str(tag).strip()
                }
            )
        )

        material = {
            "name": normalized_name,
            "description": str(
                description or ""
            ).strip(),
            "metric": normalized_metric,
            "operator": (
                normalized_operator
            ),
            "expected": clone(
                expected
            ),
            "tolerance": (
                normalized_tolerance
            ),
            "minimum_support": (
                normalized_support
            ),
            "tags": list(
                normalized_tags
            ),
        }

        return Hypothesis(
            id=stable_id(
                "carbon-hypothesis",
                material,
            ),
            name=normalized_name,
            description=material[
                "description"
            ],
            metric=normalized_metric,
            operator=(
                normalized_operator
            ),
            expected=clone(
                expected
            ),
            tolerance=(
                normalized_tolerance
            ),
            minimum_support=(
                normalized_support
            ),
            tags=normalized_tags,
        )

    def evaluate(
        self,
        hypothesis: Hypothesis,
        observations: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        if not observations:
            raise HypothesisError(
                "observations are required"
            )

        evaluations = []

        for index, observation in enumerate(
            observations
        ):
            state = values_of(
                observation
            )

            present = (
                hypothesis.metric in state
            )

            observed = clone(
                state.get(
                    hypothesis.metric
                )
            )

            passed, reason = (
                self._evaluate_value(
                    present=present,
                    observed=observed,
                    hypothesis=hypothesis,
                )
            )

            evaluations.append(
                {
                    "index": index,
                    "present": present,
                    "observed": observed,
                    "passed": passed,
                    "reason": reason,
                }
            )

        supported = [
            item
            for item in evaluations
            if item["passed"] is True
        ]

        contradicted = [
            item
            for item in evaluations
            if item["passed"] is False
        ]

        indeterminate = [
            item
            for item in evaluations
            if item["passed"] is None
        ]

        decisive_count = (
            len(supported)
            + len(contradicted)
        )

        support_fraction = (
            len(supported)
            / decisive_count
            if decisive_count
            else 0.0
        )

        if (
            len(supported)
            >= hypothesis.minimum_support
            and not contradicted
        ):
            disposition = "supported"

        elif contradicted:
            disposition = "contradicted"

        else:
            disposition = (
                "insufficient_evidence"
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "hypothesis_evaluation"
            ),
            "owner": OWNER,
            "hypothesis": (
                hypothesis.projection()
            ),
            "observation_count": len(
                observations
            ),
            "support_count": len(
                supported
            ),
            "contradiction_count": len(
                contradicted
            ),
            "indeterminate_count": len(
                indeterminate
            ),
            "decisive_count": (
                decisive_count
            ),
            "support_fraction": (
                support_fraction
            ),
            "disposition": disposition,
            "evaluations": evaluations,
            "derived": True,
            "authoritative": False,
            "verified_fact": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-hypothesis-evaluation",
            {
                "hypothesis_id": (
                    hypothesis.id
                ),
                "evaluations": evaluations,
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def compare(
        self,
        evaluations: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        if not evaluations:
            raise HypothesisError(
                "evaluations are required"
            )

        ranking = []

        for evaluation in evaluations:
            hypothesis = evaluation.get(
                "hypothesis"
            )

            if not isinstance(
                hypothesis,
                Mapping,
            ):
                raise HypothesisError(
                    "evaluation hypothesis "
                    "is required"
                )

            ranking.append(
                {
                    "hypothesis_id": (
                        hypothesis.get("id")
                    ),
                    "name": (
                        hypothesis.get(
                            "name"
                        )
                    ),
                    "disposition": (
                        evaluation.get(
                            "disposition"
                        )
                    ),
                    "support_count": int(
                        evaluation.get(
                            "support_count",
                            0,
                        )
                    ),
                    "contradiction_count": (
                        int(
                            evaluation.get(
                                "contradiction_count",
                                0,
                            )
                        )
                    ),
                    "support_fraction": (
                        float(
                            evaluation.get(
                                "support_fraction",
                                0.0,
                            )
                        )
                    ),
                }
            )

        order = {
            "supported": 0,
            "insufficient_evidence": 1,
            "contradicted": 2,
        }

        ranking.sort(
            key=lambda item: (
                order.get(
                    str(
                        item[
                            "disposition"
                        ]
                    ),
                    3,
                ),
                -item[
                    "support_fraction"
                ],
                -item[
                    "support_count"
                ],
                item["name"] or "",
            )
        )

        result = {
            "schema": SCHEMA,
            "kind": (
                "hypothesis_comparison"
            ),
            "owner": OWNER,
            "evaluation_count": len(
                evaluations
            ),
            "ranking": ranking,
            "derived": True,
            "non_mutating": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def evaluate_predicate(
        self,
        name: str,
        observations: Sequence[
            Mapping[str, Any]
        ],
        predicate: Predicate,
        *,
        description: str = "",
    ) -> dict[str, Any]:
        if not observations:
            raise HypothesisError(
                "observations are required"
            )

        normalized_name = str(
            name or ""
        ).strip()

        if not normalized_name:
            raise HypothesisError(
                "predicate hypothesis "
                "name is required"
            )

        results = []

        for index, observation in enumerate(
            observations
        ):
            try:
                passed = bool(
                    predicate(
                        clone(
                            dict(
                                observation
                            )
                        )
                    )
                )

                error = None

            except Exception as exc:
                passed = None
                error = {
                    "type": (
                        type(exc).__name__
                    ),
                    "message": str(exc),
                }

            results.append(
                {
                    "index": index,
                    "passed": passed,
                    "error": error,
                }
            )

        support = sum(
            item["passed"] is True
            for item in results
        )

        contradiction = sum(
            item["passed"] is False
            for item in results
        )

        indeterminate = sum(
            item["passed"] is None
            for item in results
        )

        result = {
            "schema": SCHEMA,
            "kind": (
                "predicate_hypothesis"
            ),
            "owner": OWNER,
            "name": normalized_name,
            "description": str(
                description or ""
            ).strip(),
            "results": results,
            "support_count": support,
            "contradiction_count": (
                contradiction
            ),
            "indeterminate_count": (
                indeterminate
            ),
            "derived": True,
            "authoritative": False,
            "verified_fact": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-predicate-hypothesis",
            {
                "name": normalized_name,
                "results": results,
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def _evaluate_value(
        self,
        *,
        present: bool,
        observed: Any,
        hypothesis: Hypothesis,
    ) -> tuple[
        bool | None,
        str,
    ]:
        operator = hypothesis.operator
        expected = hypothesis.expected

        if operator == "exists":
            return (
                present,
                (
                    "metric present"
                    if present
                    else "metric absent"
                ),
            )

        if operator == "absent":
            return (
                not present,
                (
                    "metric absent"
                    if not present
                    else "metric present"
                ),
            )

        if not present:
            return (
                None,
                "metric absent",
            )

        if operator == "eq":
            passed = (
                canonical(observed)
                == canonical(expected)
            )

        elif operator == "ne":
            passed = (
                canonical(observed)
                != canonical(expected)
            )

        elif operator in {
            "gt",
            "gte",
            "lt",
            "lte",
            "within",
        }:
            if not (
                numeric(observed)
                and numeric(expected)
            ):
                return (
                    None,
                    "numeric comparison "
                    "requires numeric values",
                )

            left = float(observed)
            right = float(expected)

            if operator == "gt":
                passed = left > right

            elif operator == "gte":
                passed = left >= right

            elif operator == "lt":
                passed = left < right

            elif operator == "lte":
                passed = left <= right

            else:
                passed = (
                    abs(left - right)
                    <= hypothesis.tolerance
                )

        else:
            raise HypothesisError(
                "unsupported hypothesis "
                "operator"
            )

        return (
            passed,
            (
                "observation supports "
                "hypothesis"
                if passed
                else "observation contradicts "
                "hypothesis"
            ),
        )


engine = HypothesisEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "form explicit falsifiable "
            "simulation hypotheses and "
            "evaluate them against projected "
            "observations without converting "
            "simulation evidence into fact"
        ),
        "capabilities": [
            "falsifiable_hypotheses",
            "metric_hypotheses",
            "equality_testing",
            "inequality_testing",
            "tolerance_testing",
            "existence_testing",
            "predicate_hypotheses",
            "support_measurement",
            "contradiction_detection",
            "insufficient_evidence_detection",
            "hypothesis_comparison",
            "deterministic_evaluation",
            "simulation_fact_separation",
            "non_authoritative_projection",
        ],
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )
