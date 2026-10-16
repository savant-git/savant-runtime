#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from typing import Any, Mapping, Sequence

from simulation import OWNER, clone, digest


SCHEMA = "savant://carbon/emergence/1"


class EmergenceError(RuntimeError):
    pass


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
            canonical(material).encode("utf-8")
        ).hexdigest()[:24]
    )


def numeric(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def entropy(values: Sequence[Any]) -> float:
    if not values:
        return 0.0

    counts = Counter(
        canonical(value)
        for value in values
    )

    total = float(len(values))

    return -sum(
        (count / total)
        * math.log2(count / total)
        for count in counts.values()
    )


def normalized_entropy(
    values: Sequence[Any],
) -> float:
    if len(values) <= 1:
        return 0.0

    distinct = len(
        {
            canonical(value)
            for value in values
        }
    )

    if distinct <= 1:
        return 0.0

    maximum = math.log2(distinct)

    return (
        entropy(values) / maximum
        if maximum
        else 0.0
    )


class EmergenceEngine:
    def analyze_states(
        self,
        states: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        if len(states) < 2:
            raise EmergenceError(
                "at least two states are required"
            )

        normalized = [
            self._values(state)
            for state in states
        ]

        keys = sorted(
            {
                key
                for values in normalized
                for key in values
            }
        )

        dimensions: dict[str, Any] = {}

        for key in keys:
            series = [
                values.get(key)
                for values in normalized
            ]

            dimensions[key] = (
                self._dimension(series)
            )

        transitions = [
            self._transition_delta(
                normalized[index - 1],
                normalized[index],
                index=index,
            )
            for index in range(
                1,
                len(normalized),
            )
        ]

        novelty = self._novelty(
            normalized
        )

        result = {
            "schema": SCHEMA,
            "kind": "emergence_analysis",
            "owner": OWNER,
            "state_count": len(
                normalized
            ),
            "dimensions": dimensions,
            "transitions": transitions,
            "novelty": novelty,
            "system": self._system(
                normalized,
                dimensions,
                transitions,
                novelty,
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-emergence",
            {
                "states": normalized,
                "dimensions": dimensions,
            },
        )

        result["digest"] = digest(result)

        return result

    def compare_runs(
        self,
        runs: Sequence[
            Sequence[Mapping[str, Any]]
        ],
    ) -> dict[str, Any]:
        if len(runs) < 2:
            raise EmergenceError(
                "at least two runs are required"
            )

        analyses = [
            self.analyze_states(run)
            for run in runs
        ]

        signatures = [
            self.signature(analysis)
            for analysis in analyses
        ]

        signature_values = [
            signature["signature"]
            for signature in signatures
        ]

        frequencies = Counter(
            canonical(value)
            for value in signature_values
        )

        representatives = {
            canonical(value): value
            for value in signature_values
        }

        result = {
            "schema": SCHEMA,
            "kind": "emergence_comparison",
            "owner": OWNER,
            "run_count": len(runs),
            "analyses": analyses,
            "signatures": signatures,
            "signature_entropy": entropy(
                signature_values
            ),
            "signature_distribution": [
                {
                    "signature": clone(
                        representatives[key]
                    ),
                    "count": count,
                    "fraction": (
                        count / len(runs)
                    ),
                }
                for key, count in sorted(
                    frequencies.items(),
                    key=lambda item: (
                        -item[1],
                        item[0],
                    ),
                )
            ],
            "recurrent": (
                len(frequencies)
                < len(runs)
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-emergence-comparison",
            {
                "signatures": (
                    signature_values
                ),
            },
        )

        result["digest"] = digest(result)

        return result

    def signature(
        self,
        analysis: Mapping[str, Any],
    ) -> dict[str, Any]:
        dimensions = analysis.get(
            "dimensions"
        )

        if not isinstance(
            dimensions,
            Mapping,
        ):
            raise EmergenceError(
                "analysis dimensions are required"
            )

        signature: dict[str, Any] = {}

        for key, dimension in sorted(
            dimensions.items()
        ):
            if not isinstance(
                dimension,
                Mapping,
            ):
                continue

            signature[key] = {
                "kind": dimension.get(
                    "kind"
                ),
                "changed": dimension.get(
                    "changed"
                ),
                "trend": dimension.get(
                    "trend"
                ),
                "entropy_band": (
                    self._band(
                        dimension.get(
                            "normalized_entropy",
                            0.0,
                        )
                    )
                ),
            }

        system = analysis.get(
            "system",
            {}
        )

        if isinstance(system, Mapping):
            signature["_system"] = {
                "change_band": self._band(
                    system.get(
                        "change_fraction",
                        0.0,
                    )
                ),
                "novelty_band": self._band(
                    system.get(
                        "novelty_fraction",
                        0.0,
                    )
                ),
                "diversity_band": self._band(
                    system.get(
                        "mean_normalized_entropy",
                        0.0,
                    )
                ),
            }

        result = {
            "schema": SCHEMA,
            "kind": "emergence_signature",
            "owner": OWNER,
            "analysis_id": analysis.get(
                "id"
            ),
            "signature": signature,
            "derived": True,
            "non_mutating": True,
            "authority_effect": "none",
        }

        result["digest"] = digest(result)

        return result

    def detect_thresholds(
        self,
        states: Sequence[
            Mapping[str, Any]
        ],
        *,
        minimum_relative_change: float = 0.25,
    ) -> dict[str, Any]:
        if minimum_relative_change < 0:
            raise EmergenceError(
                "minimum_relative_change "
                "cannot be negative"
            )

        normalized = [
            self._values(state)
            for state in states
        ]

        if len(normalized) < 2:
            raise EmergenceError(
                "at least two states are required"
            )

        findings = []

        keys = sorted(
            {
                key
                for values in normalized
                for key in values
            }
        )

        for key in keys:
            series = [
                values.get(key)
                for values in normalized
            ]

            if not all(
                numeric(value)
                for value in series
            ):
                continue

            numbers = [
                float(value)
                for value in series
            ]

            for index in range(
                1,
                len(numbers),
            ):
                before = numbers[
                    index - 1
                ]
                after = numbers[index]

                absolute = (
                    after - before
                )

                denominator = max(
                    abs(before),
                    abs(after),
                    1e-12,
                )

                relative = (
                    abs(absolute)
                    / denominator
                )

                if (
                    relative
                    >= minimum_relative_change
                ):
                    findings.append(
                        {
                            "key": key,
                            "state_index": (
                                index
                            ),
                            "before": before,
                            "after": after,
                            "absolute_change": (
                                absolute
                            ),
                            "relative_change": (
                                relative
                            ),
                        }
                    )

        result = {
            "schema": SCHEMA,
            "kind": "emergence_thresholds",
            "owner": OWNER,
            "minimum_relative_change": (
                minimum_relative_change
            ),
            "findings": findings,
            "finding_count": len(
                findings
            ),
            "derived": True,
            "non_mutating": True,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["digest"] = digest(result)

        return result

    def _dimension(
        self,
        series: Sequence[Any],
    ) -> dict[str, Any]:
        unique = {
            canonical(value)
            for value in series
        }

        result: dict[str, Any] = {
            "count": len(series),
            "distinct": len(unique),
            "changed": len(unique) > 1,
            "entropy": entropy(series),
            "normalized_entropy": (
                normalized_entropy(series)
            ),
        }

        if series and all(
            numeric(value)
            for value in series
        ):
            numbers = [
                float(value)
                for value in series
            ]

            differences = [
                numbers[index]
                - numbers[index - 1]
                for index in range(
                    1,
                    len(numbers),
                )
            ]

            result.update(
                {
                    "kind": "numeric",
                    "minimum": min(
                        numbers
                    ),
                    "maximum": max(
                        numbers
                    ),
                    "mean": (
                        statistics.fmean(
                            numbers
                        )
                    ),
                    "population_stddev": (
                        statistics.pstdev(
                            numbers
                        )
                        if len(numbers) > 1
                        else 0.0
                    ),
                    "net_change": (
                        numbers[-1]
                        - numbers[0]
                    ),
                    "mean_step_change": (
                        statistics.fmean(
                            differences
                        )
                        if differences
                        else 0.0
                    ),
                    "trend": self._trend(
                        numbers
                    ),
                }
            )

            return result

        result.update(
            {
                "kind": "categorical",
                "trend": "non_numeric",
            }
        )

        return result

    def _transition_delta(
        self,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        *,
        index: int,
    ) -> dict[str, Any]:
        keys = sorted(
            set(before)
            | set(after)
        )

        changes = []

        for key in keys:
            left = before.get(key)
            right = after.get(key)

            if canonical(left) == canonical(
                right
            ):
                continue

            change = {
                "key": key,
                "before": clone(left),
                "after": clone(right),
            }

            if (
                numeric(left)
                and numeric(right)
            ):
                change["delta"] = (
                    float(right)
                    - float(left)
                )

            changes.append(change)

        return {
            "from_index": index - 1,
            "to_index": index,
            "changes": changes,
            "change_count": len(
                changes
            ),
        }

    def _novelty(
        self,
        states: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        seen: set[str] = set()
        novel = []

        for index, state in enumerate(
            states
        ):
            encoded = canonical(state)
            state_digest = (
                hashlib.sha256(
                    encoded.encode("utf-8")
                ).hexdigest()
            )

            is_novel = (
                state_digest not in seen
            )

            if is_novel:
                seen.add(state_digest)

            novel.append(
                {
                    "index": index,
                    "state_digest": (
                        state_digest
                    ),
                    "novel": is_novel,
                }
            )

        novel_count = sum(
            1
            for item in novel
            if item["novel"]
        )

        return {
            "states": novel,
            "novel_state_count": (
                novel_count
            ),
            "novelty_fraction": (
                novel_count
                / len(states)
                if states
                else 0.0
            ),
        }

    def _system(
        self,
        states: Sequence[
            Mapping[str, Any]
        ],
        dimensions: Mapping[
            str,
            Mapping[str, Any],
        ],
        transitions: Sequence[
            Mapping[str, Any]
        ],
        novelty: Mapping[str, Any],
    ) -> dict[str, Any]:
        dimension_count = len(
            dimensions
        )

        changed = sum(
            1
            for dimension in (
                dimensions.values()
            )
            if dimension.get(
                "changed"
            )
        )

        entropy_values = [
            float(
                dimension.get(
                    "normalized_entropy",
                    0.0,
                )
            )
            for dimension in (
                dimensions.values()
            )
        ]

        total_changes = sum(
            int(
                transition.get(
                    "change_count",
                    0,
                )
            )
            for transition in transitions
        )

        possible_changes = (
            max(
                len(states) - 1,
                0,
            )
            * dimension_count
        )

        return {
            "dimension_count": (
                dimension_count
            ),
            "changed_dimensions": (
                changed
            ),
            "change_fraction": (
                changed
                / dimension_count
                if dimension_count
                else 0.0
            ),
            "transition_change_density": (
                total_changes
                / possible_changes
                if possible_changes
                else 0.0
            ),
            "mean_normalized_entropy": (
                statistics.fmean(
                    entropy_values
                )
                if entropy_values
                else 0.0
            ),
            "novelty_fraction": (
                novelty.get(
                    "novelty_fraction",
                    0.0,
                )
            ),
        }

    @staticmethod
    def _values(
        state: Mapping[str, Any],
    ) -> dict[str, Any]:
        values = state.get("values")

        if isinstance(
            values,
            Mapping,
        ):
            return clone(dict(values))

        return clone(dict(state))

    @staticmethod
    def _trend(
        numbers: Sequence[float],
    ) -> str:
        if len(numbers) < 2:
            return "stable"

        differences = [
            numbers[index]
            - numbers[index - 1]
            for index in range(
                1,
                len(numbers),
            )
        ]

        positive = all(
            value >= 0
            for value in differences
        )
        negative = all(
            value <= 0
            for value in differences
        )

        if all(
            value == 0
            for value in differences
        ):
            return "stable"

        if positive:
            return "nondecreasing"

        if negative:
            return "nonincreasing"

        if numbers[-1] > numbers[0]:
            return "mixed_upward"

        if numbers[-1] < numbers[0]:
            return "mixed_downward"

        return "mixed_flat"

    @staticmethod
    def _band(value: Any) -> str:
        try:
            number = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return "unknown"

        if number <= 0.0:
            return "none"

        if number < 0.25:
            return "low"

        if number < 0.5:
            return "moderate"

        if number < 0.75:
            return "high"

        return "extreme"


engine = EmergenceEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "detect and project patterns "
            "that emerge across simulation "
            "state evolution without "
            "promoting derived patterns "
            "into authority"
        ),
        "capabilities": [
            "state_evolution_analysis",
            "novelty_detection",
            "entropy_projection",
            "change_density",
            "trend_detection",
            "threshold_detection",
            "emergence_signatures",
            "cross_run_recurrence",
            "cross_run_divergence",
            "pattern_projection",
            "non_authoritative_emergence",
        ],
        "causal_claims_by_default": False,
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
