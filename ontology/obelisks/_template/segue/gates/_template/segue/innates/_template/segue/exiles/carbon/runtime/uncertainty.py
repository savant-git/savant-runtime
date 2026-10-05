#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from simulation import (
    OWNER,
    SimulationRuntime,
    Transition,
    clone,
    digest,
    runtime,
)


SCHEMA = "savant://carbon/uncertainty/1"


class UncertaintyError(RuntimeError):
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
        * float(quantile)
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


@dataclass(frozen=True, slots=True)
class Distribution:
    name: str
    kind: str
    parameters: Mapping[str, Any]

    def projection(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "parameters": clone(
                self.parameters
            ),
        }


class UncertaintyEngine:
    DISTRIBUTIONS = frozenset(
        {
            "constant",
            "uniform",
            "normal",
            "triangular",
            "choice",
        }
    )

    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime

    def distribution(
        self,
        name: str,
        kind: str,
        **parameters: Any,
    ) -> Distribution:
        normalized_name = str(
            name or ""
        ).strip()

        normalized_kind = str(
            kind or ""
        ).strip().lower()

        if not normalized_name:
            raise UncertaintyError(
                "distribution name is required"
            )

        if (
            normalized_kind
            not in self.DISTRIBUTIONS
        ):
            raise UncertaintyError(
                "unsupported distribution"
            )

        self._validate_distribution(
            normalized_kind,
            parameters,
        )

        return Distribution(
            name=normalized_name,
            kind=normalized_kind,
            parameters=clone(
                parameters
            ),
        )

    def sample(
        self,
        distribution: Distribution,
        *,
        rng: random.Random,
    ) -> Any:
        kind = distribution.kind
        parameters = (
            distribution.parameters
        )

        if kind == "constant":
            return clone(
                parameters.get("value")
            )

        if kind == "uniform":
            return rng.uniform(
                float(parameters["low"]),
                float(parameters["high"]),
            )

        if kind == "normal":
            return rng.gauss(
                float(parameters["mean"]),
                float(parameters["sigma"]),
            )

        if kind == "triangular":
            return rng.triangular(
                float(parameters["low"]),
                float(parameters["high"]),
                float(
                    parameters.get(
                        "mode",
                        (
                            float(
                                parameters[
                                    "low"
                                ]
                            )
                            + float(
                                parameters[
                                    "high"
                                ]
                            )
                        )
                        / 2.0,
                    )
                ),
            )

        if kind == "choice":
            values = list(
                parameters["values"]
            )

            weights = parameters.get(
                "weights"
            )

            if weights is None:
                return clone(
                    rng.choice(values)
                )

            return clone(
                rng.choices(
                    values,
                    weights=list(weights),
                    k=1,
                )[0]
            )

        raise UncertaintyError(
            "unsupported distribution"
        )

    def design(
        self,
        distributions: Sequence[
            Distribution
        ],
        *,
        samples: int,
        seed: int = 0,
    ) -> dict[str, Any]:
        if int(samples) < 1:
            raise UncertaintyError(
                "samples must be at least one"
            )

        names = [
            distribution.name
            for distribution in distributions
        ]

        if not names:
            raise UncertaintyError(
                "at least one distribution "
                "is required"
            )

        if len(names) != len(set(names)):
            raise UncertaintyError(
                "distribution names must "
                "be unique"
            )

        rng = random.Random(
            int(seed)
        )

        draws = []

        for index in range(
            int(samples)
        ):
            values = {}

            for distribution in (
                distributions
            ):
                values[
                    distribution.name
                ] = self.sample(
                    distribution,
                    rng=rng,
                )

            draws.append(
                {
                    "index": index,
                    "values": values,
                }
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "uncertainty_design"
            ),
            "owner": OWNER,
            "seed": int(seed),
            "sample_count": int(
                samples
            ),
            "distributions": [
                distribution.projection()
                for distribution
                in distributions
            ],
            "draws": draws,
            "deterministic_given_seed": (
                True
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-uncertainty-design",
            {
                "seed": int(seed),
                "distributions": result[
                    "distributions"
                ],
                "draws": draws,
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def propagate(
        self,
        definition_id: str,
        transition: Transition,
        design: Mapping[str, Any],
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
        simulation_seed: int = 0,
    ) -> dict[str, Any]:
        self.runtime._definition(
            definition_id
        )

        draws = design.get(
            "draws"
        )

        if not isinstance(
            draws,
            list,
        ) or not draws:
            raise UncertaintyError(
                "uncertainty design draws "
                "are required"
            )

        if int(steps) < 1:
            raise UncertaintyError(
                "steps must be at least one"
            )

        if float(delta_time) <= 0:
            raise UncertaintyError(
                "delta_time must be "
                "greater than zero"
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

        for draw in draws:
            if not isinstance(
                draw,
                Mapping,
            ):
                raise UncertaintyError(
                    "invalid uncertainty draw"
                )

            sampled = draw.get(
                "values"
            )

            if not isinstance(
                sampled,
                Mapping,
            ):
                raise UncertaintyError(
                    "uncertainty draw values "
                    "must be a mapping"
                )

            run_parameters = clone(
                base_parameters
            )

            run_parameters.update(
                clone(
                    dict(sampled)
                )
            )

            run_seed = (
                int(simulation_seed)
                + int(
                    draw.get(
                        "index",
                        0,
                    )
                )
            )

            instance = (
                self.runtime.instantiate(
                    definition_id,
                    initial_state=clone(
                        base_state
                    ),
                    seed=run_seed,
                )
            )

            produced = (
                self.runtime.execute(
                    instance.id,
                    transition=transition,
                    events=clone(
                        base_events
                    ),
                    steps=int(steps),
                    delta_time=float(
                        delta_time
                    ),
                    parameters=(
                        run_parameters
                    ),
                )
            )

            final_state = produced[-1]

            run = {
                "draw_index": (
                    draw.get("index")
                ),
                "sampled_parameters": (
                    clone(
                        dict(sampled)
                    )
                ),
                "simulation_seed": (
                    run_seed
                ),
                "instance_id": (
                    instance.id
                ),
                "final_state": (
                    final_state.projection()
                ),
            }

            run["digest"] = digest(
                run
            )

            runs.append(run)

        result = {
            "schema": SCHEMA,
            "kind": (
                "uncertainty_propagation"
            ),
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "design_id": (
                design.get("id")
            ),
            "run_count": len(runs),
            "runs": runs,
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "interpretation": (
                "propagated simulation "
                "uncertainty only"
            ),
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-uncertainty-propagation",
            {
                "definition_id": (
                    definition_id
                ),
                "design_id": (
                    design.get("id")
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

    def summarize(
        self,
        propagation: Mapping[
            str,
            Any,
        ],
        *,
        metric: str,
    ) -> dict[str, Any]:
        normalized_metric = str(
            metric or ""
        ).strip()

        if not normalized_metric:
            raise UncertaintyError(
                "metric is required"
            )

        runs = propagation.get(
            "runs"
        )

        if not isinstance(
            runs,
            list,
        ):
            raise UncertaintyError(
                "propagation runs are required"
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
                normalized_metric
            )

            if numeric(value):
                observations.append(
                    {
                        "draw_index": (
                            run.get(
                                "draw_index"
                            )
                        ),
                        "value": float(
                            value
                        ),
                    }
                )

        if not observations:
            raise UncertaintyError(
                "metric has no numeric "
                "observations"
            )

        values = [
            item["value"]
            for item in observations
        ]

        count = len(values)

        mean = (
            math.fsum(values)
            / count
        )

        variance = (
            math.fsum(
                (
                    value - mean
                )
                ** 2
                for value in values
            )
            / count
        )

        result = {
            "schema": SCHEMA,
            "kind": (
                "uncertainty_summary"
            ),
            "owner": OWNER,
            "propagation_id": (
                propagation.get("id")
            ),
            "metric": (
                normalized_metric
            ),
            "count": count,
            "minimum": min(values),
            "maximum": max(values),
            "mean": mean,
            "variance": variance,
            "standard_deviation": (
                math.sqrt(
                    variance
                )
            ),
            "p01": percentile(
                values,
                0.01,
            ),
            "p05": percentile(
                values,
                0.05,
            ),
            "p25": percentile(
                values,
                0.25,
            ),
            "p50": percentile(
                values,
                0.50,
            ),
            "p75": percentile(
                values,
                0.75,
            ),
            "p95": percentile(
                values,
                0.95,
            ),
            "p99": percentile(
                values,
                0.99,
            ),
            "observations": (
                observations
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def exceedance(
        self,
        summary: Mapping[
            str,
            Any,
        ],
        *,
        threshold: float,
        direction: str = "above",
    ) -> dict[str, Any]:
        normalized_direction = str(
            direction or ""
        ).strip().lower()

        if normalized_direction not in {
            "above",
            "below",
        }:
            raise UncertaintyError(
                "direction must be above "
                "or below"
            )

        observations = summary.get(
            "observations"
        )

        if not isinstance(
            observations,
            list,
        ) or not observations:
            raise UncertaintyError(
                "summary observations "
                "are required"
            )

        limit = float(
            threshold
        )

        hits = []

        for observation in (
            observations
        ):
            value = observation.get(
                "value"
            )

            if not numeric(value):
                continue

            matched = (
                float(value) > limit
                if normalized_direction
                == "above"
                else float(value) < limit
            )

            if matched:
                hits.append(
                    clone(
                        dict(
                            observation
                        )
                    )
                )

        valid_count = sum(
            1
            for observation
            in observations
            if numeric(
                observation.get(
                    "value"
                )
            )
        )

        result = {
            "schema": SCHEMA,
            "kind": (
                "uncertainty_exceedance"
            ),
            "owner": OWNER,
            "summary_digest": (
                summary.get("digest")
            ),
            "metric": (
                summary.get("metric")
            ),
            "threshold": limit,
            "direction": (
                normalized_direction
            ),
            "observation_count": (
                valid_count
            ),
            "exceedance_count": len(
                hits
            ),
            "fraction": (
                len(hits)
                / valid_count
                if valid_count
                else 0.0
            ),
            "matches": hits,
            "derived": True,
            "authoritative": False,
            "probability_claim": (
                "empirical simulation "
                "frequency only"
            ),
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def _validate_distribution(
        self,
        kind: str,
        parameters: Mapping[
            str,
            Any,
        ],
    ) -> None:
        if kind == "constant":
            if "value" not in parameters:
                raise UncertaintyError(
                    "constant requires value"
                )

            return

        if kind == "uniform":
            low = parameters.get("low")
            high = parameters.get(
                "high"
            )

            if not (
                numeric(low)
                and numeric(high)
                and float(low)
                <= float(high)
            ):
                raise UncertaintyError(
                    "uniform requires finite "
                    "low <= high"
                )

            return

        if kind == "normal":
            mean = parameters.get(
                "mean"
            )

            sigma = parameters.get(
                "sigma"
            )

            if not (
                numeric(mean)
                and numeric(sigma)
                and float(sigma) >= 0
            ):
                raise UncertaintyError(
                    "normal requires finite "
                    "mean and sigma >= 0"
                )

            return

        if kind == "triangular":
            low = parameters.get("low")
            high = parameters.get(
                "high"
            )

            mode = parameters.get(
                "mode",
                (
                    (
                        float(low)
                        + float(high)
                    )
                    / 2.0
                    if (
                        numeric(low)
                        and numeric(high)
                    )
                    else None
                ),
            )

            if not (
                numeric(low)
                and numeric(high)
                and numeric(mode)
                and float(low)
                <= float(mode)
                <= float(high)
            ):
                raise UncertaintyError(
                    "triangular requires "
                    "low <= mode <= high"
                )

            return

        if kind == "choice":
            values = parameters.get(
                "values"
            )

            if not isinstance(
                values,
                Sequence,
            ) or isinstance(
                values,
                (str, bytes),
            ) or not values:
                raise UncertaintyError(
                    "choice requires "
                    "non-empty values"
                )

            weights = parameters.get(
                "weights"
            )

            if weights is None:
                return

            if not isinstance(
                weights,
                Sequence,
            ) or isinstance(
                weights,
                (str, bytes),
            ):
                raise UncertaintyError(
                    "choice weights must "
                    "be a sequence"
                )

            if len(weights) != len(
                values
            ):
                raise UncertaintyError(
                    "choice weights must "
                    "match values"
                )

            if not all(
                numeric(weight)
                and float(weight) >= 0
                for weight in weights
            ):
                raise UncertaintyError(
                    "choice weights must "
                    "be finite and "
                    "non-negative"
                )

            if not any(
                float(weight) > 0
                for weight in weights
            ):
                raise UncertaintyError(
                    "at least one choice "
                    "weight must be positive"
                )


engine = UncertaintyEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "represent uncertain simulation "
            "inputs explicitly, generate "
            "reproducible parameter designs, "
            "propagate them through Carbon, "
            "and project outcome uncertainty "
            "without confusing simulated "
            "frequency with external fact"
        ),
        "capabilities": [
            "explicit_uncertainty_models",
            "constant_distributions",
            "uniform_distributions",
            "normal_distributions",
            "triangular_distributions",
            "categorical_distributions",
            "weighted_choice",
            "seeded_sampling",
            "reproducible_designs",
            "uncertainty_propagation",
            "parameter_sampling",
            "outcome_distributions",
            "percentile_projection",
            "variance_projection",
            "standard_deviation_projection",
            "threshold_exceedance",
            "empirical_frequency_projection",
            "simulation_probability_separation",
            "deterministic_identity",
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
