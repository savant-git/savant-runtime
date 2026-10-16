#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from simulation import (
    OWNER,
    SimulationRuntime,
    Transition,
    clone,
    digest,
    runtime,
)


SCHEMA = "savant://carbon/experiment/1"


class ExperimentError(RuntimeError):
    pass


Metric = Callable[
    [Mapping[str, Any]],
    Any,
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


@dataclass(frozen=True, slots=True)
class Arm:
    id: str
    name: str
    parameters: Mapping[str, Any]
    initial_state: Mapping[str, Any]
    events: tuple[Any, ...]
    tags: tuple[str, ...]

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parameters": clone(
                self.parameters
            ),
            "initial_state": clone(
                self.initial_state
            ),
            "events": clone(
                list(self.events)
            ),
            "tags": list(
                self.tags
            ),
        }


@dataclass(frozen=True, slots=True)
class Experiment:
    id: str
    name: str
    definition_id: str
    arms: tuple[Arm, ...]
    seeds: tuple[int, ...]
    steps: int
    delta_time: float
    provenance: Mapping[str, Any]

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "definition_id": (
                self.definition_id
            ),
            "arms": [
                arm.projection()
                for arm in self.arms
            ],
            "seeds": list(
                self.seeds
            ),
            "steps": self.steps,
            "delta_time": (
                self.delta_time
            ),
            "provenance": clone(
                self.provenance
            ),
        }


class ExperimentEngine:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime

    def arm(
        self,
        name: str,
        *,
        parameters: Mapping[
            str,
            Any,
        ] | None = None,
        initial_state: Mapping[
            str,
            Any,
        ] | None = None,
        events: Sequence[Any] = (),
        tags: Sequence[str] = (),
    ) -> Arm:
        normalized_name = str(
            name or ""
        ).strip()

        if not normalized_name:
            raise ExperimentError(
                "arm name is required"
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
            "parameters": clone(
                dict(parameters or {})
            ),
            "initial_state": clone(
                dict(initial_state or {})
            ),
            "events": clone(
                list(events)
            ),
            "tags": list(
                normalized_tags
            ),
        }

        return Arm(
            id=stable_id(
                "carbon-experiment-arm",
                material,
            ),
            name=normalized_name,
            parameters=material[
                "parameters"
            ],
            initial_state=material[
                "initial_state"
            ],
            events=tuple(
                material["events"]
            ),
            tags=normalized_tags,
        )

    def define(
        self,
        name: str,
        definition_id: str,
        *,
        arms: Sequence[Arm],
        seeds: Sequence[int] = (0,),
        steps: int = 1,
        delta_time: float = 1.0,
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> Experiment:
        normalized_name = str(
            name or ""
        ).strip()

        normalized_definition = str(
            definition_id or ""
        ).strip()

        if not normalized_name:
            raise ExperimentError(
                "experiment name is required"
            )

        if not normalized_definition:
            raise ExperimentError(
                "definition_id is required"
            )

        if len(arms) < 2:
            raise ExperimentError(
                "experiment requires at "
                "least two arms"
            )

        arm_ids = [
            arm.id
            for arm in arms
        ]

        if len(arm_ids) != len(
            set(arm_ids)
        ):
            raise ExperimentError(
                "experiment arms must "
                "be unique"
            )

        normalized_seeds = tuple(
            int(seed)
            for seed in seeds
        )

        if not normalized_seeds:
            raise ExperimentError(
                "experiment requires "
                "at least one seed"
            )

        if (
            len(normalized_seeds)
            != len(set(normalized_seeds))
        ):
            raise ExperimentError(
                "experiment seeds must "
                "be unique"
            )

        normalized_steps = int(
            steps
        )

        normalized_delta = float(
            delta_time
        )

        if normalized_steps < 1:
            raise ExperimentError(
                "steps must be at least one"
            )

        if normalized_delta <= 0:
            raise ExperimentError(
                "delta_time must be "
                "greater than zero"
            )

        material = {
            "name": normalized_name,
            "definition_id": (
                normalized_definition
            ),
            "arms": [
                arm.projection()
                for arm in arms
            ],
            "seeds": list(
                normalized_seeds
            ),
            "steps": normalized_steps,
            "delta_time": (
                normalized_delta
            ),
            "provenance": clone(
                dict(provenance or {})
            ),
        }

        return Experiment(
            id=stable_id(
                "carbon-experiment",
                material,
            ),
            name=normalized_name,
            definition_id=(
                normalized_definition
            ),
            arms=tuple(arms),
            seeds=normalized_seeds,
            steps=normalized_steps,
            delta_time=(
                normalized_delta
            ),
            provenance=material[
                "provenance"
            ],
        )

    def execute(
        self,
        experiment: Experiment,
        transition: Transition,
    ) -> dict[str, Any]:
        self.runtime._definition(
            experiment.definition_id
        )

        runs = []

        for arm in experiment.arms:
            for seed in experiment.seeds:
                instance = (
                    self.runtime.instantiate(
                        experiment.definition_id,
                        initial_state=clone(
                            arm.initial_state
                        ),
                        seed=seed,
                    )
                )

                produced = (
                    self.runtime.execute(
                        instance.id,
                        transition=transition,
                        events=clone(
                            list(
                                arm.events
                            )
                        ),
                        steps=experiment.steps,
                        delta_time=(
                            experiment.delta_time
                        ),
                        parameters=clone(
                            arm.parameters
                        ),
                    )
                )

                final_state = produced[-1]

                run = {
                    "arm_id": arm.id,
                    "arm_name": arm.name,
                    "seed": seed,
                    "instance_id": (
                        instance.id
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
                "controlled_experiment"
            ),
            "owner": OWNER,
            "experiment": (
                experiment.projection()
            ),
            "run_count": len(runs),
            "runs": runs,
            "balance": (
                self._balance(
                    experiment,
                    runs,
                )
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "interpretation": (
                "controlled simulation "
                "experiment only"
            ),
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-experiment-execution",
            {
                "experiment_id": (
                    experiment.id
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

    def measure(
        self,
        execution: Mapping[str, Any],
        *,
        metric_name: str,
        metric: Metric,
    ) -> dict[str, Any]:
        normalized_name = str(
            metric_name or ""
        ).strip()

        if not normalized_name:
            raise ExperimentError(
                "metric_name is required"
            )

        runs = execution.get(
            "runs"
        )

        if not isinstance(
            runs,
            list,
        ):
            raise ExperimentError(
                "experiment runs are required"
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

            try:
                value = metric(
                    clone(
                        dict(final_state)
                    )
                )

                error = None

            except Exception as exc:
                value = None
                error = {
                    "type": (
                        type(exc).__name__
                    ),
                    "message": str(exc),
                }

            observations.append(
                {
                    "arm_id": (
                        run.get("arm_id")
                    ),
                    "arm_name": (
                        run.get(
                            "arm_name"
                        )
                    ),
                    "seed": (
                        run.get("seed")
                    ),
                    "value": clone(
                        value
                    ),
                    "error": error,
                }
            )

        grouped: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        for observation in (
            observations
        ):
            arm_id = str(
                observation[
                    "arm_id"
                ]
            )

            grouped.setdefault(
                arm_id,
                [],
            ).append(
                observation
            )

        summaries = {}

        for arm_id, items in (
            grouped.items()
        ):
            valid = [
                item["value"]
                for item in items
                if (
                    item["error"] is None
                    and isinstance(
                        item["value"],
                        (int, float),
                    )
                    and not isinstance(
                        item["value"],
                        bool,
                    )
                )
            ]

            summaries[arm_id] = {
                "arm_name": (
                    items[0][
                        "arm_name"
                    ]
                    if items
                    else None
                ),
                "observation_count": len(
                    items
                ),
                "numeric_count": len(
                    valid
                ),
                "mean": (
                    sum(
                        float(value)
                        for value in valid
                    )
                    / len(valid)
                    if valid
                    else None
                ),
                "minimum": (
                    min(valid)
                    if valid
                    else None
                ),
                "maximum": (
                    max(valid)
                    if valid
                    else None
                ),
            }

        result = {
            "schema": SCHEMA,
            "kind": (
                "experiment_measurement"
            ),
            "owner": OWNER,
            "execution_id": (
                execution.get("id")
            ),
            "metric": (
                normalized_name
            ),
            "observations": (
                observations
            ),
            "arm_summaries": (
                summaries
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-experiment-measurement",
            {
                "execution_id": (
                    execution.get("id")
                ),
                "metric": (
                    normalized_name
                ),
                "observations": (
                    observations
                ),
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def contrast(
        self,
        measurement: Mapping[
            str,
            Any,
        ],
        *,
        control_arm_id: str,
        treatment_arm_id: str,
    ) -> dict[str, Any]:
        summaries = measurement.get(
            "arm_summaries"
        )

        if not isinstance(
            summaries,
            Mapping,
        ):
            raise ExperimentError(
                "arm summaries are required"
            )

        control = summaries.get(
            control_arm_id
        )

        treatment = summaries.get(
            treatment_arm_id
        )

        if not (
            isinstance(
                control,
                Mapping,
            )
            and isinstance(
                treatment,
                Mapping,
            )
        ):
            raise ExperimentError(
                "control and treatment "
                "arms are required"
            )

        control_mean = control.get(
            "mean"
        )

        treatment_mean = treatment.get(
            "mean"
        )

        if not (
            isinstance(
                control_mean,
                (int, float),
            )
            and isinstance(
                treatment_mean,
                (int, float),
            )
        ):
            raise ExperimentError(
                "contrast requires numeric "
                "arm means"
            )

        absolute_difference = (
            float(treatment_mean)
            - float(control_mean)
        )

        relative_difference = None

        if float(control_mean) != 0.0:
            relative_difference = (
                absolute_difference
                / abs(
                    float(control_mean)
                )
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "experiment_contrast"
            ),
            "owner": OWNER,
            "measurement_id": (
                measurement.get("id")
            ),
            "metric": (
                measurement.get(
                    "metric"
                )
            ),
            "control_arm_id": (
                control_arm_id
            ),
            "treatment_arm_id": (
                treatment_arm_id
            ),
            "control_mean": (
                float(control_mean)
            ),
            "treatment_mean": (
                float(treatment_mean)
            ),
            "absolute_difference": (
                absolute_difference
            ),
            "relative_difference": (
                relative_difference
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "interpretation": (
                "difference between "
                "controlled simulation arms; "
                "not an external-world "
                "causal assertion"
            ),
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def _balance(
        self,
        experiment: Experiment,
        runs: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        expected = len(
            experiment.seeds
        )

        counts = {
            arm.id: 0
            for arm in experiment.arms
        }

        seeds = {
            arm.id: []
            for arm in experiment.arms
        }

        for run in runs:
            arm_id = run.get(
                "arm_id"
            )

            if arm_id in counts:
                counts[arm_id] += 1
                seeds[arm_id].append(
                    run.get("seed")
                )

        balanced = all(
            counts[arm.id] == expected
            and tuple(
                seeds[arm.id]
            )
            == experiment.seeds
            for arm in experiment.arms
        )

        return {
            "expected_runs_per_arm": (
                expected
            ),
            "counts": counts,
            "seeds": seeds,
            "balanced": balanced,
        }


engine = ExperimentEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "run reproducible controlled "
            "simulation experiments with "
            "explicit arms, matched seeds, "
            "measurements, and contrasts "
            "without promoting projected "
            "effects into real-world fact"
        ),
        "capabilities": [
            "experiment_definition",
            "immutable_experiment_arms",
            "control_arms",
            "treatment_arms",
            "matched_seed_execution",
            "balanced_experiments",
            "multi_arm_experiments",
            "metric_extraction",
            "arm_aggregation",
            "control_treatment_contrast",
            "absolute_effect_projection",
            "relative_effect_projection",
            "reproducible_execution",
            "experiment_provenance",
            "deterministic_identity",
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
