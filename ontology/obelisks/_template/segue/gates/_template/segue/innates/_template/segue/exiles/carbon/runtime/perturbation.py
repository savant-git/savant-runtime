#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
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


SCHEMA = "savant://carbon/perturbation/1"


class PerturbationError(RuntimeError):
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


@dataclass(frozen=True, slots=True)
class Perturbation:
    id: str
    target: str
    mode: str
    value: Any
    label: str

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target": self.target,
            "mode": self.mode,
            "value": clone(self.value),
            "label": self.label,
        }


class PerturbationEngine:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime

    def define(
        self,
        target: str,
        *,
        mode: str,
        value: Any,
        label: str = "",
    ) -> Perturbation:
        normalized_target = str(
            target or ""
        ).strip()

        if not normalized_target:
            raise PerturbationError(
                "perturbation target is required"
            )

        normalized_mode = str(
            mode or ""
        ).strip().lower()

        allowed = {
            "set",
            "add",
            "multiply",
            "delete",
        }

        if normalized_mode not in allowed:
            raise PerturbationError(
                "perturbation mode must be "
                "set, add, multiply, or delete"
            )

        normalized_label = (
            str(label or "").strip()
            or (
                f"{normalized_mode}:"
                f"{normalized_target}"
            )
        )

        material = {
            "target": normalized_target,
            "mode": normalized_mode,
            "value": clone(value),
            "label": normalized_label,
        }

        return Perturbation(
            id=stable_id(
                "carbon-perturbation",
                material,
            ),
            target=normalized_target,
            mode=normalized_mode,
            value=clone(value),
            label=normalized_label,
        )

    def apply(
        self,
        values: Mapping[str, Any],
        perturbations: Sequence[
            Perturbation
        ],
    ) -> dict[str, Any]:
        projected = clone(
            dict(values)
        )

        receipts = []

        for perturbation in perturbations:
            before_present = (
                perturbation.target
                in projected
            )

            before = clone(
                projected.get(
                    perturbation.target
                )
            )

            if perturbation.mode == "delete":
                projected.pop(
                    perturbation.target,
                    None,
                )

            elif perturbation.mode == "set":
                projected[
                    perturbation.target
                ] = clone(
                    perturbation.value
                )

            elif perturbation.mode == "add":
                if not before_present:
                    raise PerturbationError(
                        "add target does not exist: "
                        + perturbation.target
                    )

                if not (
                    numeric(before)
                    and numeric(
                        perturbation.value
                    )
                ):
                    raise PerturbationError(
                        "add requires numeric values: "
                        + perturbation.target
                    )

                projected[
                    perturbation.target
                ] = (
                    float(before)
                    + float(
                        perturbation.value
                    )
                )

            elif (
                perturbation.mode
                == "multiply"
            ):
                if not before_present:
                    raise PerturbationError(
                        "multiply target does not exist: "
                        + perturbation.target
                    )

                if not (
                    numeric(before)
                    and numeric(
                        perturbation.value
                    )
                ):
                    raise PerturbationError(
                        "multiply requires numeric values: "
                        + perturbation.target
                    )

                projected[
                    perturbation.target
                ] = (
                    float(before)
                    * float(
                        perturbation.value
                    )
                )

            after_present = (
                perturbation.target
                in projected
            )

            after = clone(
                projected.get(
                    perturbation.target
                )
            )

            receipts.append(
                {
                    "perturbation": (
                        perturbation
                        .projection()
                    ),
                    "before_present": (
                        before_present
                    ),
                    "before": before,
                    "after_present": (
                        after_present
                    ),
                    "after": after,
                    "changed": (
                        canonical(before)
                        != canonical(after)
                        or before_present
                        != after_present
                    ),
                }
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "perturbation_projection"
            ),
            "owner": OWNER,
            "input_digest": digest(
                dict(values)
            ),
            "values": projected,
            "receipts": receipts,
            "perturbation_count": len(
                receipts
            ),
            "derived": True,
            "non_mutating": True,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def sweep(
        self,
        definition_id: str,
        transition: Transition,
        *,
        target: str,
        values: Sequence[Any],
        mode: str = "set",
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
        surface: str = "state",
    ) -> dict[str, Any]:
        self.runtime._definition(
            definition_id
        )

        if steps < 1:
            raise PerturbationError(
                "steps must be at least one"
            )

        normalized_surface = str(
            surface or ""
        ).strip().lower()

        if normalized_surface not in {
            "state",
            "parameters",
        }:
            raise PerturbationError(
                "surface must be state "
                "or parameters"
            )

        if not values:
            raise PerturbationError(
                "sweep requires at least "
                "one perturbation value"
            )

        base_state = clone(
            dict(initial_state or {})
        )
        base_parameters = clone(
            dict(parameters or {})
        )
        event_sequence = clone(
            list(events)
        )

        runs = []

        for index, value in enumerate(
            values
        ):
            perturbation = self.define(
                target,
                mode=mode,
                value=value,
                label=(
                    f"sweep:{target}:{index}"
                ),
            )

            state = clone(base_state)
            params = clone(
                base_parameters
            )

            if (
                normalized_surface
                == "state"
            ):
                projection = self.apply(
                    state,
                    [perturbation],
                )
                state = projection[
                    "values"
                ]
            else:
                projection = self.apply(
                    params,
                    [perturbation],
                )
                params = projection[
                    "values"
                ]

            execution = self._execute(
                definition_id,
                transition,
                initial_state=state,
                parameters=params,
                events=event_sequence,
                steps=steps,
                delta_time=delta_time,
                seed=seed,
            )

            runs.append(
                {
                    "index": index,
                    "surface": (
                        normalized_surface
                    ),
                    "perturbation": (
                        perturbation
                        .projection()
                    ),
                    "projection": (
                        projection
                    ),
                    "execution": execution,
                }
            )

        result = {
            "schema": SCHEMA,
            "kind": "perturbation_sweep",
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "target": target,
            "mode": mode,
            "surface": normalized_surface,
            "seed": seed,
            "run_count": len(runs),
            "runs": runs,
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-perturbation-sweep",
            {
                "definition_id": (
                    definition_id
                ),
                "target": target,
                "surface": (
                    normalized_surface
                ),
                "runs": [
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

    def local_response(
        self,
        sweep: Mapping[str, Any],
        *,
        outcome: str,
    ) -> dict[str, Any]:
        runs = sweep.get("runs")

        if not isinstance(runs, list):
            raise PerturbationError(
                "sweep runs are required"
            )

        observations = []

        for run in runs:
            if not isinstance(
                run,
                Mapping,
            ):
                continue

            perturbation = run.get(
                "perturbation"
            )
            execution = run.get(
                "execution"
            )

            if not (
                isinstance(
                    perturbation,
                    Mapping,
                )
                and isinstance(
                    execution,
                    Mapping,
                )
            ):
                continue

            final_state = execution.get(
                "final_state"
            )

            if not isinstance(
                final_state,
                Mapping,
            ):
                continue

            final_values = (
                final_state.get(
                    "values"
                )
            )

            if not isinstance(
                final_values,
                Mapping,
            ):
                continue

            input_value = (
                perturbation.get(
                    "value"
                )
            )
            output_value = (
                final_values.get(
                    outcome
                )
            )

            observations.append(
                {
                    "input": clone(
                        input_value
                    ),
                    "output": clone(
                        output_value
                    ),
                }
            )

        numeric_observations = [
            item
            for item in observations
            if (
                numeric(item["input"])
                and numeric(
                    item["output"]
                )
            )
        ]

        slopes = []

        for index in range(
            1,
            len(numeric_observations),
        ):
            previous = (
                numeric_observations[
                    index - 1
                ]
            )
            current = (
                numeric_observations[
                    index
                ]
            )

            dx = (
                float(current["input"])
                - float(
                    previous["input"]
                )
            )

            if dx == 0:
                continue

            dy = (
                float(current["output"])
                - float(
                    previous["output"]
                )
            )

            slopes.append(
                {
                    "from_index": (
                        index - 1
                    ),
                    "to_index": index,
                    "slope": dy / dx,
                }
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "perturbation_local_response"
            ),
            "owner": OWNER,
            "sweep_id": sweep.get("id"),
            "target": sweep.get(
                "target"
            ),
            "outcome": outcome,
            "observations": observations,
            "local_slopes": slopes,
            "derived": True,
            "non_mutating": True,
            "causal_claim": False,
            "interpretation": (
                "simulation response only"
            ),
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def _execute(
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
            seed=seed,
        )

        produced = self.runtime.execute(
            instance.id,
            transition=transition,
            events=clone(
                list(events)
            ),
            steps=steps,
            delta_time=delta_time,
            parameters=clone(
                parameters
            ),
        )

        final_state = produced[-1]

        result = {
            "instance_id": (
                instance.id
            ),
            "seed": seed,
            "branch_id": (
                final_state.branch_id
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

        result["digest"] = digest(
            result
        )

        return result


engine = PerturbationEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "apply controlled reversible "
            "perturbations to simulated "
            "state and parameters and "
            "measure projected response"
        ),
        "capabilities": [
            "state_perturbation",
            "parameter_perturbation",
            "set_perturbation",
            "additive_perturbation",
            "multiplicative_perturbation",
            "deletion_perturbation",
            "perturbation_receipts",
            "parameter_sweeps",
            "state_sweeps",
            "local_response_projection",
            "deterministic_replay",
            "baseline_preservation",
            "non_authoritative_projection",
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
