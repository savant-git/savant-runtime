#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
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


SCHEMA = "savant://carbon/counterfactual/1"


class CounterfactualError(RuntimeError):
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


def deep_delta(
    baseline: Any,
    alternative: Any,
    *,
    path: str = "",
) -> list[dict[str, Any]]:
    if canonical(baseline) == canonical(
        alternative
    ):
        return []

    if (
        isinstance(baseline, Mapping)
        and isinstance(alternative, Mapping)
    ):
        changes: list[
            dict[str, Any]
        ] = []

        keys = sorted(
            set(baseline)
            | set(alternative)
        )

        for key in keys:
            child_path = (
                f"{path}.{key}"
                if path
                else str(key)
            )

            if key not in baseline:
                changes.append(
                    {
                        "path": child_path,
                        "kind": "added",
                        "before": None,
                        "after": clone(
                            alternative[key]
                        ),
                    }
                )
                continue

            if key not in alternative:
                changes.append(
                    {
                        "path": child_path,
                        "kind": "removed",
                        "before": clone(
                            baseline[key]
                        ),
                        "after": None,
                    }
                )
                continue

            changes.extend(
                deep_delta(
                    baseline[key],
                    alternative[key],
                    path=child_path,
                )
            )

        return changes

    return [
        {
            "path": path or "$",
            "kind": "changed",
            "before": clone(baseline),
            "after": clone(alternative),
        }
    ]


@dataclass(frozen=True, slots=True)
class Counterfactual:
    id: str
    name: str
    state_overrides: Mapping[str, Any]
    parameter_overrides: Mapping[str, Any]
    event_overrides: Mapping[int, Any]
    seed: int | None

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state_overrides": clone(
                self.state_overrides
            ),
            "parameter_overrides": clone(
                self.parameter_overrides
            ),
            "event_overrides": {
                str(key): clone(value)
                for key, value in sorted(
                    self.event_overrides.items()
                )
            },
            "seed": self.seed,
        }


class CounterfactualEngine:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime

    def define(
        self,
        name: str,
        *,
        state_overrides: Mapping[
            str,
            Any,
        ] | None = None,
        parameter_overrides: Mapping[
            str,
            Any,
        ] | None = None,
        event_overrides: Mapping[
            int,
            Any,
        ] | None = None,
        seed: int | None = None,
    ) -> Counterfactual:
        normalized_name = str(
            name or ""
        ).strip()

        if not normalized_name:
            raise CounterfactualError(
                "counterfactual name is required"
            )

        normalized_events: dict[
            int,
            Any,
        ] = {}

        for raw_step, event in (
            event_overrides or {}
        ).items():
            step = int(raw_step)

            if step < 0:
                raise CounterfactualError(
                    "event override step "
                    "cannot be negative"
                )

            normalized_events[
                step
            ] = clone(event)

        material = {
            "name": normalized_name,
            "state_overrides": clone(
                dict(
                    state_overrides
                    or {}
                )
            ),
            "parameter_overrides": clone(
                dict(
                    parameter_overrides
                    or {}
                )
            ),
            "event_overrides": {
                str(key): clone(value)
                for key, value in sorted(
                    normalized_events.items()
                )
            },
            "seed": (
                int(seed)
                if seed is not None
                else None
            ),
        }

        return Counterfactual(
            id=stable_id(
                "carbon-counterfactual",
                material,
            ),
            name=normalized_name,
            state_overrides=material[
                "state_overrides"
            ],
            parameter_overrides=material[
                "parameter_overrides"
            ],
            event_overrides=(
                normalized_events
            ),
            seed=material["seed"],
        )

    def run(
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
        seed: int = 0,
        alternatives: Sequence[
            Counterfactual
        ],
    ) -> dict[str, Any]:
        self.runtime._definition(
            definition_id
        )

        if steps < 1:
            raise CounterfactualError(
                "steps must be at least one"
            )

        if not alternatives:
            raise CounterfactualError(
                "at least one counterfactual "
                "is required"
            )

        baseline_state = clone(
            dict(initial_state or {})
        )
        baseline_parameters = clone(
            dict(parameters or {})
        )
        baseline_events = clone(
            list(events)
        )

        baseline = self._execute(
            definition_id,
            transition,
            initial_state=baseline_state,
            parameters=baseline_parameters,
            events=baseline_events,
            steps=steps,
            delta_time=delta_time,
            seed=seed,
        )

        projections = []

        for alternative in alternatives:
            alternative_state = clone(
                baseline_state
            )
            alternative_state.update(
                clone(
                    alternative
                    .state_overrides
                )
            )

            alternative_parameters = clone(
                baseline_parameters
            )
            alternative_parameters.update(
                clone(
                    alternative
                    .parameter_overrides
                )
            )

            alternative_events = clone(
                baseline_events
            )

            required_length = max(
                (
                    max(
                        alternative
                        .event_overrides
                    )
                    + 1
                    if alternative
                    .event_overrides
                    else 0
                ),
                len(alternative_events),
            )

            while (
                len(alternative_events)
                < required_length
            ):
                alternative_events.append(
                    None
                )

            for (
                event_step,
                event,
            ) in (
                alternative
                .event_overrides
                .items()
            ):
                alternative_events[
                    event_step
                ] = clone(event)

            execution = self._execute(
                definition_id,
                transition,
                initial_state=(
                    alternative_state
                ),
                parameters=(
                    alternative_parameters
                ),
                events=alternative_events,
                steps=steps,
                delta_time=delta_time,
                seed=(
                    alternative.seed
                    if alternative.seed
                    is not None
                    else seed
                ),
            )

            baseline_values = (
                baseline["final_state"][
                    "values"
                ]
            )
            alternative_values = (
                execution[
                    "final_state"
                ]["values"]
            )

            changes = deep_delta(
                baseline_values,
                alternative_values,
            )

            projection = {
                "counterfactual": (
                    alternative
                    .projection()
                ),
                "execution": execution,
                "outcome_delta": changes,
                "changed": bool(changes),
                "change_count": len(
                    changes
                ),
            }

            projection["digest"] = digest(
                projection
            )

            projections.append(
                projection
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "counterfactual_analysis"
            ),
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "baseline": baseline,
            "alternatives": projections,
            "alternative_count": len(
                projections
            ),
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-counterfactual-analysis",
            {
                "definition_id": (
                    definition_id
                ),
                "baseline_digest": (
                    baseline["digest"]
                ),
                "alternatives": [
                    item["digest"]
                    for item in (
                        projections
                    )
                ],
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def contrast(
        self,
        analysis: Mapping[
            str,
            Any,
        ],
        *,
        paths: Sequence[str] = (),
    ) -> dict[str, Any]:
        baseline = analysis.get(
            "baseline"
        )
        alternatives = analysis.get(
            "alternatives"
        )

        if not isinstance(
            baseline,
            Mapping,
        ):
            raise CounterfactualError(
                "analysis baseline is required"
            )

        if not isinstance(
            alternatives,
            list,
        ):
            raise CounterfactualError(
                "analysis alternatives "
                "are required"
            )

        path_filter = {
            str(path).strip()
            for path in paths
            if str(path).strip()
        }

        contrasted = []

        for alternative in alternatives:
            if not isinstance(
                alternative,
                Mapping,
            ):
                continue

            changes = alternative.get(
                "outcome_delta",
                [],
            )

            if not isinstance(
                changes,
                list,
            ):
                continue

            selected = []

            for change in changes:
                if not isinstance(
                    change,
                    Mapping,
                ):
                    continue

                change_path = str(
                    change.get(
                        "path",
                        "",
                    )
                )

                if (
                    path_filter
                    and change_path
                    not in path_filter
                ):
                    continue

                selected.append(
                    clone(change)
                )

            counterfactual = (
                alternative.get(
                    "counterfactual",
                    {},
                )
            )

            contrasted.append(
                {
                    "counterfactual_id": (
                        counterfactual.get(
                            "id"
                        )
                        if isinstance(
                            counterfactual,
                            Mapping,
                        )
                        else None
                    ),
                    "name": (
                        counterfactual.get(
                            "name"
                        )
                        if isinstance(
                            counterfactual,
                            Mapping,
                        )
                        else None
                    ),
                    "changes": selected,
                    "change_count": len(
                        selected
                    ),
                }
            )

        result = {
            "schema": SCHEMA,
            "kind": (
                "counterfactual_contrast"
            ),
            "owner": OWNER,
            "analysis_id": (
                analysis.get("id")
            ),
            "paths": sorted(
                path_filter
            ),
            "alternatives": contrasted,
            "derived": True,
            "non_mutating": True,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result

    def invariants(
        self,
        analysis: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        baseline = analysis.get(
            "baseline"
        )
        alternatives = analysis.get(
            "alternatives"
        )

        if (
            not isinstance(
                baseline,
                Mapping,
            )
            or not isinstance(
                alternatives,
                list,
            )
        ):
            raise CounterfactualError(
                "invalid counterfactual "
                "analysis"
            )

        baseline_final = baseline.get(
            "final_state"
        )

        if not isinstance(
            baseline_final,
            Mapping,
        ):
            raise CounterfactualError(
                "baseline final state "
                "is required"
            )

        baseline_values = (
            baseline_final.get(
                "values"
            )
        )

        if not isinstance(
            baseline_values,
            Mapping,
        ):
            raise CounterfactualError(
                "baseline values are required"
            )

        invariant = {}
        variant = {}

        for key in sorted(
            baseline_values
        ):
            base_value = (
                baseline_values[key]
            )

            values = [
                clone(base_value)
            ]

            for alternative in alternatives:
                if not isinstance(
                    alternative,
                    Mapping,
                ):
                    continue

                execution = (
                    alternative.get(
                        "execution"
                    )
                )

                if not isinstance(
                    execution,
                    Mapping,
                ):
                    continue

                final_state = (
                    execution.get(
                        "final_state"
                    )
                )

                if not isinstance(
                    final_state,
                    Mapping,
                ):
                    continue

                projected = (
                    final_state.get(
                        "values"
                    )
                )

                if not isinstance(
                    projected,
                    Mapping,
                ):
                    continue

                values.append(
                    clone(
                        projected.get(
                            key
                        )
                    )
                )

            unique = {
                canonical(value)
                for value in values
            }

            if len(unique) == 1:
                invariant[key] = clone(
                    base_value
                )
            else:
                variant[key] = values

        result = {
            "schema": SCHEMA,
            "kind": (
                "counterfactual_invariants"
            ),
            "owner": OWNER,
            "analysis_id": (
                analysis.get("id")
            ),
            "invariant_values": (
                invariant
            ),
            "variant_values": variant,
            "invariant_keys": sorted(
                invariant
            ),
            "variant_keys": sorted(
                variant
            ),
            "derived": True,
            "non_mutating": True,
            "causal_claim": False,
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
            initial_state=initial_state,
            seed=seed,
        )

        produced = self.runtime.execute(
            instance.id,
            transition=transition,
            events=events,
            steps=steps,
            delta_time=delta_time,
            parameters=parameters,
        )

        final_state = produced[-1]

        result = {
            "instance_id": instance.id,
            "branch_id": (
                final_state.branch_id
            ),
            "seed": seed,
            "parameters": clone(
                parameters
            ),
            "events": clone(
                list(events)
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


engine = CounterfactualEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "derive controlled alternative "
            "simulation histories without "
            "mutating baseline reality or "
            "claiming unsupported causality"
        ),
        "capabilities": [
            "baseline_preservation",
            "state_counterfactuals",
            "parameter_counterfactuals",
            "event_counterfactuals",
            "seed_counterfactuals",
            "alternative_history_execution",
            "deep_outcome_deltas",
            "targeted_contrast",
            "invariant_detection",
            "variant_detection",
            "deterministic_replay",
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
