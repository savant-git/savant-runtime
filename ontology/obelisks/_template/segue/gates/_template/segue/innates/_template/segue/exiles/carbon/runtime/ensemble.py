#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Mapping, Sequence

from simulation import (
    OWNER,
    SimulationRuntime,
    Transition,
    clone,
    digest,
    runtime,
)


SCHEMA = "savant://carbon/ensemble/1"


class EnsembleError(RuntimeError):
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


def percentile(
    values: Sequence[float],
    quantile: float,
) -> float | None:
    if not values:
        return None

    ordered = sorted(
        float(value)
        for value in values
    )

    if len(ordered) == 1:
        return ordered[0]

    position = (
        (len(ordered) - 1)
        * quantile
    )

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    fraction = position - lower

    return (
        ordered[lower]
        + (
            ordered[upper]
            - ordered[lower]
        )
        * fraction
    )


class EnsembleEngine:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime

    def execute(
        self,
        definition_id: str,
        transition: Transition,
        *,
        initial_state: Mapping[
            str,
            Any,
        ] | None = None,
        parameters: Mapping[
            str,
            Any,
        ] | None = None,
        events: Sequence[Any] = (),
        steps: int = 1,
        delta_time: float = 1.0,
        seeds: Sequence[int],
    ) -> dict[str, Any]:
        self.runtime._definition(
            definition_id
        )

        if steps < 1:
            raise EnsembleError(
                "steps must be at least one"
            )

        if delta_time <= 0:
            raise EnsembleError(
                "delta_time must be "
                "greater than zero"
            )

        normalized_seeds = tuple(
            int(seed)
            for seed in seeds
        )

        if not normalized_seeds:
            raise EnsembleError(
                "ensemble requires at least "
                "one seed"
            )

        if (
            len(normalized_seeds)
            != len(set(normalized_seeds))
        ):
            raise EnsembleError(
                "ensemble seeds must be unique"
            )

        base_state = clone(
            dict(initial_state or {})
        )

        base_parameters = clone(
            dict(parameters or {})
        )

        base_events = clone(
            list(events)
        )

        runs = []

        for index, seed in enumerate(
            normalized_seeds
        ):
            instance = (
                self.runtime.instantiate(
                    definition_id,
                    initial_state=clone(
                        base_state
                    ),
                    seed=seed,
                )
            )

            produced = (
                self.runtime.execute(
                    instance.id,
                    transition=transition,
                    events=clone(
                        base_events
                    ),
                    steps=steps,
                    delta_time=(
                        delta_time
                    ),
                    parameters=clone(
                        base_parameters
                    ),
                )
            )

            final_state = produced[-1]

            run = {
                "index": index,
                "seed": seed,
                "instance_id": (
                    instance.id
                ),
                "branch_id": (
                    final_state.branch_id
                ),
                "produced_state_count": (
                    len(produced)
                ),
                "final_state": (
                    final_state.projection()
                ),
                "replay": (
                    self.runtime
                    .replay_projection(
                        instance.id
                    )
                ),
            }

            run["digest"] = digest(
                run
            )

            runs.append(run)

        result = {
            "schema": SCHEMA,
            "kind": (
                "ensemble_execution"
            ),
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "initial_state": (
                base_state
            ),
            "parameters": (
                base_parameters
            ),
            "events": base_events,
            "steps": int(steps),
            "delta_time": float(
                delta_time
            ),
            "seeds": list(
                normalized_seeds
            ),
            "run_count": len(runs),
            "runs": runs,
            "summary": (
                self.summarize_runs(
                    runs
                )
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-ensemble",
            {
                "definition_id": (
                    definition_id
                ),
                "seeds": list(
                    normalized_seeds
                ),
                "run_digests": [
                    run["digest"]
                    for run in runs
                ],
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def summarize_runs(
        self,
        runs: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        if not runs:
            raise EnsembleError(
                "runs are required"
            )

        states = []

        for run in runs:
            final_state = run.get(
                "final_state"
            )

            if not isinstance(
                final_state,
                Mapping,
            ):
                continue

            values = final_state.get(
                "values"
            )

            if isinstance(
                values,
                Mapping,
            ):
                states.append(
                    values
                )

        keys = sorted(
            {
                key
                for state in states
                for key in state
            }
        )

        metrics = {}

        for key in keys:
            observed = [
                clone(
                    state.get(key)
                )
                for state in states
                if key in state
            ]

            numeric_values = [
                float(value)
                for value in observed
                if numeric(value)
            ]

            if (
                numeric_values
                and len(
                    numeric_values
                ) == len(observed)
            ):
                count = len(
                    numeric_values
                )

                mean = (
                    math.fsum(
                        numeric_values
                    )
                    / count
                )

                variance = (
                    math.fsum(
                        (
                            value
                            - mean
                        )
                        ** 2
                        for value
                        in numeric_values
                    )
                    / count
                )

                metrics[key] = {
                    "kind": "numeric",
                    "count": count,
                    "minimum": min(
                        numeric_values
                    ),
                    "maximum": max(
                        numeric_values
                    ),
                    "mean": mean,
                    "variance": (
                        variance
                    ),
                    "standard_deviation": (
                        math.sqrt(
                            variance
                        )
                    ),
                    "p05": percentile(
                        numeric_values,
                        0.05,
                    ),
                    "p25": percentile(
                        numeric_values,
                        0.25,
                    ),
                    "p50": percentile(
                        numeric_values,
                        0.50,
                    ),
                    "p75": percentile(
                        numeric_values,
                        0.75,
                    ),
                    "p95": percentile(
                        numeric_values,
                        0.95,
                    ),
                }

                continue

            serialized = [
                canonical(value)
                for value in observed
            ]

            counts = Counter(
                serialized
            )

            representatives = {
                canonical(value): value
                for value in observed
            }

            ordered = sorted(
                counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )

            metrics[key] = {
                "kind": "categorical",
                "count": len(
                    observed
                ),
                "distinct_count": len(
                    counts
                ),
                "distribution": [
                    {
                        "value": clone(
                            representatives[
                                encoded
                            ]
                        ),
                        "count": count,
                        "fraction": (
                            count
                            / len(observed)
                        ),
                    }
                    for encoded, count
                    in ordered
                ],
            }

        fingerprints = [
            canonical(state)
            for state in states
        ]

        distinct_outcomes = len(
            set(fingerprints)
        )

        result = {
            "run_count": len(runs),
            "state_count": len(
                states
            ),
            "distinct_final_state_count": (
                distinct_outcomes
            ),
            "deterministic_across_seeds": (
                distinct_outcomes <= 1
            ),
            "metrics": metrics,
        }

        result["digest"] = digest(
            result
        )

        return result

    def convergence(
        self,
        ensemble: Mapping[str, Any],
        *,
        metric: str,
        tolerance: float,
    ) -> dict[str, Any]:
        if tolerance < 0:
            raise EnsembleError(
                "tolerance cannot be negative"
            )

        runs = ensemble.get("runs")

        if not isinstance(
            runs,
            list,
        ):
            raise EnsembleError(
                "ensemble runs are required"
            )

        observations = []

        for run in runs:
            if not isinstance(
                run,
                Mapping,
            ):
                continue

            final_state = run.get(
                "final_state"
            )

            if not isinstance(
                final_state,
                Mapping,
            ):
                continue

            values = final_state.get(
                "values"
            )

            if not isinstance(
                values,
                Mapping,
            ):
                continue

            value = values.get(
                metric
            )

            if numeric(value):
                observations.append(
                    {
                        "seed": (
                            run.get("seed")
                        ),
                        "value": float(
                            value
                        ),
                    }
                )

        if not observations:
            raise EnsembleError(
                "metric has no numeric "
                "ensemble observations"
            )

        numeric_values = [
            item["value"]
            for item in observations
        ]

        spread = (
            max(numeric_values)
            - min(numeric_values)
        )

        converged = (
            spread
            <= float(tolerance)
        )

        result = {
            "schema": SCHEMA,
            "kind": (
                "ensemble_convergence"
            ),
            "owner": OWNER,
            "ensemble_id": (
                ensemble.get("id")
            ),
            "metric": metric,
            "tolerance": float(
                tolerance
            ),
            "observations": (
                observations
            ),
            "minimum": min(
                numeric_values
            ),
            "maximum": max(
                numeric_values
            ),
            "spread": spread,
            "converged": converged,
            "derived": True,
            "authoritative": False,
            "interpretation": (
                "simulation ensemble "
                "convergence only"
            ),
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def stability(
        self,
        ensemble: Mapping[str, Any],
    ) -> dict[str, Any]:
        summary = ensemble.get(
            "summary"
        )

        if not isinstance(
            summary,
            Mapping,
        ):
            raise EnsembleError(
                "ensemble summary is required"
            )

        metrics = summary.get(
            "metrics"
        )

        if not isinstance(
            metrics,
            Mapping,
        ):
            raise EnsembleError(
                "ensemble metrics are required"
            )

        projections = {}

        for key, metric in (
            metrics.items()
        ):
            if not isinstance(
                metric,
                Mapping,
            ):
                continue

            if (
                metric.get("kind")
                == "numeric"
            ):
                mean = metric.get(
                    "mean"
                )

                standard_deviation = (
                    metric.get(
                        "standard_deviation"
                    )
                )

                if not (
                    numeric(mean)
                    and numeric(
                        standard_deviation
                    )
                ):
                    continue

                absolute_mean = abs(
                    float(mean)
                )

                coefficient = (
                    float(
                        standard_deviation
                    )
                    / absolute_mean
                    if absolute_mean
                    else (
                        0.0
                        if float(
                            standard_deviation
                        )
                        == 0.0
                        else None
                    )
                )

                projections[key] = {
                    "kind": "numeric",
                    "standard_deviation": (
                        float(
                            standard_deviation
                        )
                    ),
                    "coefficient_of_variation": (
                        coefficient
                    ),
                }

            elif (
                metric.get("kind")
                == "categorical"
            ):
                distribution = (
                    metric.get(
                        "distribution"
                    )
                )

                dominant_fraction = (
                    max(
                        (
                            float(
                                item.get(
                                    "fraction",
                                    0.0,
                                )
                            )
                            for item
                            in distribution
                            if isinstance(
                                item,
                                Mapping,
                            )
                        ),
                        default=0.0,
                    )
                    if isinstance(
                        distribution,
                        list,
                    )
                    else 0.0
                )

                projections[key] = {
                    "kind": (
                        "categorical"
                    ),
                    "dominant_fraction": (
                        dominant_fraction
                    ),
                    "distinct_count": (
                        metric.get(
                            "distinct_count"
                        )
                    ),
                }

        result = {
            "schema": SCHEMA,
            "kind": (
                "ensemble_stability"
            ),
            "owner": OWNER,
            "ensemble_id": (
                ensemble.get("id")
            ),
            "metrics": projections,
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result


engine = EnsembleEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "execute reproducible families "
            "of simulations across controlled "
            "seeds and project uncertainty, "
            "dispersion, convergence, and "
            "stability without converting "
            "simulation output into authority"
        ),
        "capabilities": [
            "multi_seed_execution",
            "ensemble_replay",
            "outcome_distribution",
            "numeric_aggregation",
            "categorical_aggregation",
            "percentile_projection",
            "variance_projection",
            "standard_deviation_projection",
            "outcome_diversity_detection",
            "cross_seed_determinism_detection",
            "convergence_measurement",
            "stability_projection",
            "coefficient_of_variation",
            "seed_provenance",
            "simulation_uncertainty_projection",
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
