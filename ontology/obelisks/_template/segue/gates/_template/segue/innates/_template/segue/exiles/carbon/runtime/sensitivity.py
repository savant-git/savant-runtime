#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from simulation import (
    OWNER,
    SimulationRuntime,
    Transition,
    clone,
    digest,
    runtime,
)


SCHEMA = "savant://carbon/sensitivity/1"


class SensitivityError(RuntimeError):
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


def final_values(
    projection: Mapping[str, Any],
) -> Mapping[str, Any]:
    final_state = projection.get(
        "final_state"
    )

    if not isinstance(
        final_state,
        Mapping,
    ):
        return {}

    values = final_state.get(
        "values"
    )

    if isinstance(
        values,
        Mapping,
    ):
        return values

    return {}


class SensitivityEngine:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime

    def execute_once(
        self,
        definition_id: str,
        transition: Transition,
        *,
        initial_state: Mapping[
            str,
            Any,
        ],
        parameters: Mapping[
            str,
            Any,
        ],
        events: Sequence[Any],
        steps: int,
        delta_time: float,
        seed: int,
    ) -> dict[str, Any]:
        instance = self.runtime.instantiate(
            definition_id,
            initial_state=clone(
                initial_state
            ),
            seed=int(seed),
        )

        produced = self.runtime.execute(
            instance.id,
            transition=transition,
            events=clone(
                list(events)
            ),
            steps=int(steps),
            delta_time=float(
                delta_time
            ),
            parameters=clone(
                parameters
            ),
        )

        final_state = produced[-1]

        result = {
            "instance_id": instance.id,
            "seed": int(seed),
            "produced_state_count": len(
                produced
            ),
            "final_state": (
                final_state.projection()
            ),
        }

        result["digest"] = digest(
            result
        )

        return result

    def parameter_sweep(
        self,
        definition_id: str,
        transition: Transition,
        *,
        parameter: str,
        values: Sequence[Any],
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
        seed: int = 0,
    ) -> dict[str, Any]:
        self.runtime._definition(
            definition_id
        )

        normalized_parameter = str(
            parameter or ""
        ).strip()

        if not normalized_parameter:
            raise SensitivityError(
                "parameter is required"
            )

        if not values:
            raise SensitivityError(
                "parameter sweep requires "
                "at least one value"
            )

        if int(steps) < 1:
            raise SensitivityError(
                "steps must be at least one"
            )

        if float(delta_time) <= 0:
            raise SensitivityError(
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

        for index, value in enumerate(
            values
        ):
            run_parameters = clone(
                base_parameters
            )

            run_parameters[
                normalized_parameter
            ] = clone(value)

            execution = self.execute_once(
                definition_id,
                transition,
                initial_state=base_state,
                parameters=run_parameters,
                events=base_events,
                steps=int(steps),
                delta_time=float(
                    delta_time
                ),
                seed=int(seed),
            )

            runs.append(
                {
                    "index": index,
                    "parameter_value": clone(
                        value
                    ),
                    "execution": execution,
                }
            )

        result = {
            "schema": SCHEMA,
            "kind": "parameter_sweep",
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "parameter": (
                normalized_parameter
            ),
            "base_parameters": (
                base_parameters
            ),
            "parameter_values": clone(
                list(values)
            ),
            "run_count": len(runs),
            "runs": runs,
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-parameter-sweep",
            {
                "definition_id": (
                    definition_id
                ),
                "parameter": (
                    normalized_parameter
                ),
                "values": list(values),
                "run_digests": [
                    run["execution"][
                        "digest"
                    ]
                    for run in runs
                ],
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def local(
        self,
        definition_id: str,
        transition: Transition,
        *,
        parameter: str,
        baseline: float,
        perturbation: float,
        metric: str,
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
        seed: int = 0,
    ) -> dict[str, Any]:
        if not numeric(baseline):
            raise SensitivityError(
                "baseline must be finite "
                "and numeric"
            )

        if not numeric(perturbation):
            raise SensitivityError(
                "perturbation must be finite "
                "and numeric"
            )

        delta = float(
            perturbation
        )

        if delta <= 0:
            raise SensitivityError(
                "perturbation must be "
                "greater than zero"
            )

        normalized_metric = str(
            metric or ""
        ).strip()

        if not normalized_metric:
            raise SensitivityError(
                "metric is required"
            )

        center = float(
            baseline
        )

        low = center - delta
        high = center + delta

        sweep = self.parameter_sweep(
            definition_id,
            transition,
            parameter=parameter,
            values=[
                low,
                center,
                high,
            ],
            initial_state=initial_state,
            parameters=parameters,
            events=events,
            steps=steps,
            delta_time=delta_time,
            seed=seed,
        )

        observations = []

        for run in sweep["runs"]:
            values_projection = (
                final_values(
                    run["execution"]
                )
            )

            observed = (
                values_projection.get(
                    normalized_metric
                )
            )

            observations.append(
                {
                    "parameter_value": (
                        run[
                            "parameter_value"
                        ]
                    ),
                    "metric_value": clone(
                        observed
                    ),
                }
            )

        if not all(
            numeric(
                item["metric_value"]
            )
            for item in observations
        ):
            raise SensitivityError(
                "local sensitivity metric "
                "must be numeric in every run"
            )

        low_output = float(
            observations[0][
                "metric_value"
            ]
        )

        center_output = float(
            observations[1][
                "metric_value"
            ]
        )

        high_output = float(
            observations[2][
                "metric_value"
            ]
        )

        derivative = (
            high_output
            - low_output
        ) / (
            high - low
        )

        forward_derivative = (
            high_output
            - center_output
        ) / delta

        backward_derivative = (
            center_output
            - low_output
        ) / delta

        curvature = (
            high_output
            - 2.0 * center_output
            + low_output
        ) / (
            delta ** 2
        )

        normalized_sensitivity = None

        if center_output != 0.0:
            normalized_sensitivity = (
                derivative
                * center
                / center_output
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "local_sensitivity"
            ),
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "parameter": parameter,
            "metric": (
                normalized_metric
            ),
            "baseline": center,
            "perturbation": delta,
            "observations": (
                observations
            ),
            "central_derivative": (
                derivative
            ),
            "forward_derivative": (
                forward_derivative
            ),
            "backward_derivative": (
                backward_derivative
            ),
            "curvature": curvature,
            "normalized_sensitivity": (
                normalized_sensitivity
            ),
            "sweep_id": sweep["id"],
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "interpretation": (
                "local simulation response "
                "under controlled parameter "
                "perturbation"
            ),
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-local-sensitivity",
            {
                "sweep_id": (
                    sweep["id"]
                ),
                "metric": (
                    normalized_metric
                ),
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def rank(
        self,
        sensitivities: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        if not sensitivities:
            raise SensitivityError(
                "sensitivities are required"
            )

        ranking = []

        for sensitivity in (
            sensitivities
        ):
            parameter = str(
                sensitivity.get(
                    "parameter",
                    "",
                )
            ).strip()

            metric = str(
                sensitivity.get(
                    "metric",
                    "",
                )
            ).strip()

            derivative = (
                sensitivity.get(
                    "central_derivative"
                )
            )

            if not (
                parameter
                and metric
                and numeric(
                    derivative
                )
            ):
                raise SensitivityError(
                    "invalid local "
                    "sensitivity projection"
                )

            normalized = (
                sensitivity.get(
                    "normalized_sensitivity"
                )
            )

            ranking.append(
                {
                    "parameter": (
                        parameter
                    ),
                    "metric": metric,
                    "central_derivative": (
                        float(
                            derivative
                        )
                    ),
                    "absolute_derivative": (
                        abs(
                            float(
                                derivative
                            )
                        )
                    ),
                    "normalized_sensitivity": (
                        float(normalized)
                        if numeric(
                            normalized
                        )
                        else None
                    ),
                    "sensitivity_id": (
                        sensitivity.get(
                            "id"
                        )
                    ),
                }
            )

        ranking.sort(
            key=lambda item: (
                -(
                    abs(
                        item[
                            "normalized_sensitivity"
                        ]
                    )
                    if item[
                        "normalized_sensitivity"
                    ]
                    is not None
                    else item[
                        "absolute_derivative"
                    ]
                ),
                item["parameter"],
            )
        )

        result = {
            "schema": SCHEMA,
            "kind": (
                "sensitivity_ranking"
            ),
            "owner": OWNER,
            "count": len(
                ranking
            ),
            "ranking": ranking,
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def elasticity(
        self,
        sensitivity: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        baseline = sensitivity.get(
            "baseline"
        )

        observations = sensitivity.get(
            "observations"
        )

        derivative = sensitivity.get(
            "central_derivative"
        )

        if not (
            numeric(baseline)
            and numeric(derivative)
            and isinstance(
                observations,
                list,
            )
            and len(observations) >= 2
        ):
            raise SensitivityError(
                "valid local sensitivity "
                "projection is required"
            )

        center_output = (
            observations[1].get(
                "metric_value"
            )
            if isinstance(
                observations[1],
                Mapping,
            )
            else None
        )

        if not numeric(
            center_output
        ):
            raise SensitivityError(
                "baseline metric output "
                "must be numeric"
            )

        output = float(
            center_output
        )

        parameter_value = float(
            baseline
        )

        value = None

        if output != 0.0:
            value = (
                float(derivative)
                * parameter_value
                / output
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "simulation_elasticity"
            ),
            "owner": OWNER,
            "sensitivity_id": (
                sensitivity.get("id")
            ),
            "parameter": (
                sensitivity.get(
                    "parameter"
                )
            ),
            "metric": (
                sensitivity.get(
                    "metric"
                )
            ),
            "elasticity": value,
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result


engine = SensitivityEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "measure how controlled changes "
            "to simulation parameters alter "
            "projected outcomes while keeping "
            "sensitivity distinct from causal "
            "or authoritative claims"
        ),
        "capabilities": [
            "parameter_sweeps",
            "controlled_perturbation",
            "local_sensitivity",
            "central_difference",
            "forward_difference",
            "backward_difference",
            "curvature_projection",
            "normalized_sensitivity",
            "elasticity_projection",
            "sensitivity_ranking",
            "metric_response_analysis",
            "parameter_response_analysis",
            "fixed_seed_comparison",
            "deterministic_sweeps",
            "simulation_causality_separation",
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
