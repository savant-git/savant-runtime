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


SCHEMA = "savant://carbon/scenario/1"


class ScenarioError(RuntimeError):
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
    encoded = canonical(
        material
    ).encode("utf-8")

    return (
        prefix
        + ":"
        + hashlib.sha256(
            encoded
        ).hexdigest()[:24]
    )


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    name: str
    initial_state: Mapping[str, Any]
    parameters: Mapping[str, Any]
    events: tuple[Any, ...]
    steps: int
    delta_time: float
    seed: int
    tags: tuple[str, ...]
    provenance: Mapping[str, Any]

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "initial_state": clone(
                self.initial_state
            ),
            "parameters": clone(
                self.parameters
            ),
            "events": clone(
                list(self.events)
            ),
            "steps": self.steps,
            "delta_time": (
                self.delta_time
            ),
            "seed": self.seed,
            "tags": list(
                self.tags
            ),
            "provenance": clone(
                self.provenance
            ),
        }


class ScenarioEngine:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime = runtime,
    ) -> None:
        self.runtime = simulation_runtime

    def define(
        self,
        name: str,
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
        tags: Sequence[str] = (),
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> Scenario:
        normalized_name = str(
            name or ""
        ).strip()

        if not normalized_name:
            raise ScenarioError(
                "scenario name is required"
            )

        normalized_steps = int(
            steps
        )

        if normalized_steps < 1:
            raise ScenarioError(
                "scenario steps must be "
                "at least one"
            )

        normalized_delta = float(
            delta_time
        )

        if normalized_delta <= 0:
            raise ScenarioError(
                "delta_time must be "
                "greater than zero"
            )

        normalized_tags = tuple(
            sorted(
                {
                    str(tag).strip()
                    for tag in tags
                    if str(
                        tag
                    ).strip()
                }
            )
        )

        material = {
            "name": normalized_name,
            "initial_state": clone(
                dict(
                    initial_state
                    or {}
                )
            ),
            "parameters": clone(
                dict(
                    parameters
                    or {}
                )
            ),
            "events": clone(
                list(events)
            ),
            "steps": normalized_steps,
            "delta_time": (
                normalized_delta
            ),
            "seed": int(seed),
            "tags": list(
                normalized_tags
            ),
            "provenance": clone(
                dict(
                    provenance
                    or {}
                )
            ),
        }

        return Scenario(
            id=stable_id(
                "carbon-scenario",
                material,
            ),
            name=normalized_name,
            initial_state=material[
                "initial_state"
            ],
            parameters=material[
                "parameters"
            ],
            events=tuple(
                material["events"]
            ),
            steps=normalized_steps,
            delta_time=(
                normalized_delta
            ),
            seed=int(seed),
            tags=normalized_tags,
            provenance=material[
                "provenance"
            ],
        )

    def execute(
        self,
        definition_id: str,
        transition: Transition,
        scenario: Scenario,
    ) -> dict[str, Any]:
        self.runtime._definition(
            definition_id
        )

        instance = (
            self.runtime.instantiate(
                definition_id,
                initial_state=clone(
                    scenario.initial_state
                ),
                seed=scenario.seed,
            )
        )

        produced = (
            self.runtime.execute(
                instance.id,
                transition=transition,
                events=clone(
                    list(
                        scenario.events
                    )
                ),
                steps=scenario.steps,
                delta_time=(
                    scenario.delta_time
                ),
                parameters=clone(
                    scenario.parameters
                ),
            )
        )

        final_state = produced[-1]

        result = {
            "schema": SCHEMA,
            "kind": (
                "scenario_execution"
            ),
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "scenario": (
                scenario.projection()
            ),
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
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-scenario-execution",
            {
                "definition_id": (
                    definition_id
                ),
                "scenario_id": (
                    scenario.id
                ),
                "final_state": (
                    result[
                        "final_state"
                    ]
                ),
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def matrix(
        self,
        definition_id: str,
        transition: Transition,
        scenarios: Sequence[
            Scenario
        ],
    ) -> dict[str, Any]:
        if not scenarios:
            raise ScenarioError(
                "scenario matrix requires "
                "at least one scenario"
            )

        ids = [
            scenario.id
            for scenario in scenarios
        ]

        if len(ids) != len(set(ids)):
            raise ScenarioError(
                "scenario matrix contains "
                "duplicate scenarios"
            )

        executions = [
            self.execute(
                definition_id,
                transition,
                scenario,
            )
            for scenario in scenarios
        ]

        final_states = [
            execution[
                "final_state"
            ].get(
                "values",
                {},
            )
            for execution in (
                executions
            )
        ]

        keys = sorted(
            {
                key
                for state in final_states
                if isinstance(
                    state,
                    Mapping,
                )
                for key in state
            }
        )

        comparison = {}

        for key in keys:
            values = []

            for (
                scenario,
                state,
            ) in zip(
                scenarios,
                final_states,
            ):
                value = (
                    state.get(key)
                    if isinstance(
                        state,
                        Mapping,
                    )
                    else None
                )

                values.append(
                    {
                        "scenario_id": (
                            scenario.id
                        ),
                        "scenario": (
                            scenario.name
                        ),
                        "value": clone(
                            value
                        ),
                    }
                )

            distinct = {
                canonical(
                    item["value"]
                )
                for item in values
            }

            comparison[key] = {
                "values": values,
                "distinct_count": len(
                    distinct
                ),
                "varies": (
                    len(distinct) > 1
                ),
            }

        result = {
            "schema": SCHEMA,
            "kind": "scenario_matrix",
            "owner": OWNER,
            "definition_id": (
                definition_id
            ),
            "scenario_count": len(
                scenarios
            ),
            "scenario_ids": ids,
            "executions": executions,
            "comparison": comparison,
            "invariant_keys": [
                key
                for key, value in (
                    comparison.items()
                )
                if not value["varies"]
            ],
            "variant_keys": [
                key
                for key, value in (
                    comparison.items()
                )
                if value["varies"]
            ],
            "derived": True,
            "authoritative": False,
            "causal_claim": False,
            "authority_effect": "none",
        }

        result["id"] = stable_id(
            "carbon-scenario-matrix",
            {
                "definition_id": (
                    definition_id
                ),
                "scenario_ids": ids,
                "execution_digests": [
                    execution[
                        "digest"
                    ]
                    for execution in (
                        executions
                    )
                ],
            },
        )

        result["digest"] = digest(
            result
        )

        return result

    def branch(
        self,
        scenario: Scenario,
        name: str,
        *,
        state: Mapping[
            str,
            Any,
        ] | None = None,
        parameters: Mapping[
            str,
            Any,
        ] | None = None,
        events: Sequence[
            Any
        ] | None = None,
        steps: int | None = None,
        delta_time: (
            float | None
        ) = None,
        seed: int | None = None,
        tags: Sequence[
            str
        ] = (),
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> Scenario:
        merged_state = clone(
            dict(
                scenario.initial_state
            )
        )

        if state:
            merged_state.update(
                clone(dict(state))
            )

        merged_parameters = clone(
            dict(
                scenario.parameters
            )
        )

        if parameters:
            merged_parameters.update(
                clone(
                    dict(parameters)
                )
            )

        merged_provenance = clone(
            dict(
                scenario.provenance
            )
        )

        merged_provenance.update(
            {
                "parent_scenario_id": (
                    scenario.id
                ),
                "branch_of": (
                    scenario.name
                ),
            }
        )

        if provenance:
            merged_provenance.update(
                clone(
                    dict(provenance)
                )
            )

        merged_tags = tuple(
            sorted(
                set(
                    scenario.tags
                )
                | {
                    str(tag).strip()
                    for tag in tags
                    if str(
                        tag
                    ).strip()
                }
            )
        )

        return self.define(
            name,
            initial_state=(
                merged_state
            ),
            parameters=(
                merged_parameters
            ),
            events=(
                scenario.events
                if events is None
                else events
            ),
            steps=(
                scenario.steps
                if steps is None
                else steps
            ),
            delta_time=(
                scenario.delta_time
                if delta_time is None
                else delta_time
            ),
            seed=(
                scenario.seed
                if seed is None
                else seed
            ),
            tags=merged_tags,
            provenance=(
                merged_provenance
            ),
        )

    def lineage(
        self,
        scenarios: Sequence[
            Scenario
        ],
    ) -> dict[str, Any]:
        nodes = [
            {
                "id": scenario.id,
                "name": (
                    scenario.name
                ),
                "tags": list(
                    scenario.tags
                ),
            }
            for scenario in scenarios
        ]

        known = {
            scenario.id
            for scenario in scenarios
        }

        edges = []

        for scenario in scenarios:
            parent = (
                scenario.provenance
                .get(
                    "parent_scenario_id"
                )
            )

            if (
                isinstance(
                    parent,
                    str,
                )
                and parent
            ):
                edges.append(
                    {
                        "from": parent,
                        "to": (
                            scenario.id
                        ),
                        "type": (
                            "scenario_branch"
                        ),
                        "parent_present": (
                            parent in known
                        ),
                    }
                )

        result = {
            "schema": SCHEMA,
            "kind": (
                "scenario_lineage"
            ),
            "owner": OWNER,
            "nodes": nodes,
            "edges": edges,
            "derived": True,
            "non_mutating": True,
            "authority_effect": "none",
        }

        result["digest"] = digest(
            result
        )

        return result


engine = ScenarioEngine()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "package reproducible simulation "
            "conditions into immutable "
            "scenarios that can be executed, "
            "branched, compared, and replayed"
        ),
        "capabilities": [
            "scenario_definition",
            "scenario_identity",
            "immutable_scenario_packets",
            "scenario_execution",
            "scenario_branching",
            "scenario_lineage",
            "scenario_matrices",
            "cross_scenario_comparison",
            "variant_detection",
            "invariant_detection",
            "parameter_profiles",
            "event_profiles",
            "seed_preservation",
            "provenance_preservation",
            "deterministic_replay",
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
