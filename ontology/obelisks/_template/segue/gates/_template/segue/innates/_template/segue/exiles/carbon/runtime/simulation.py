#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence


OWNER = "carbon"
SCHEMA = "savant://carbon/simulation-runtime/1"


class SimulationError(RuntimeError):
    pass


class SimulationInvariantError(SimulationError):
    pass


class SimulationNotFound(SimulationError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def stable_id(prefix: str, material: Any) -> str:
    return f"{prefix}:{digest(material)[:24]}"


def clone(value: Any) -> Any:
    return copy.deepcopy(value)


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_mapping(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return clone(dict(value or {}))


def normalize_sequence(
    value: Sequence[Any] | None,
) -> list[Any]:
    if value is None:
        return []
    return clone(list(value))


@dataclass(frozen=True, slots=True)
class SimulationDefinition:
    id: str
    name: str
    parameters: Mapping[str, Any]
    constraints: tuple[Any, ...]
    dependencies: tuple[str, ...]
    sources: tuple[Any, ...]
    execution_rules: Mapping[str, Any]
    uncertainty: Mapping[str, Any]
    created_at: str

    def projection(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "simulation_definition",
            "id": self.id,
            "owner": OWNER,
            "name": self.name,
            "parameters": clone(self.parameters),
            "constraints": clone(self.constraints),
            "dependencies": list(self.dependencies),
            "sources": clone(self.sources),
            "execution_rules": clone(
                self.execution_rules
            ),
            "uncertainty": clone(self.uncertainty),
            "created_at": self.created_at,
            "authority_effect": "none",
            "authoritative": False,
            "derived": True,
        }
        payload["digest"] = digest(payload)
        return payload


@dataclass(slots=True)
class SimulationState:
    id: str
    instance_id: str
    branch_id: str
    sequence: int
    values: dict[str, Any]
    simulation_time: float
    parent_state_id: str | None
    event: Any
    created_at: str
    digest: str = ""

    def projection(self) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "kind": "simulation_state",
            "id": self.id,
            "owner": OWNER,
            "instance_id": self.instance_id,
            "branch_id": self.branch_id,
            "sequence": self.sequence,
            "values": clone(self.values),
            "simulation_time": self.simulation_time,
            "parent_state_id": self.parent_state_id,
            "event": clone(self.event),
            "created_at": self.created_at,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }
        payload["digest"] = (
            self.digest or digest(payload)
        )
        return payload


@dataclass(slots=True)
class SimulationBranch:
    id: str
    instance_id: str
    parent_branch_id: str | None
    fork_state_id: str | None
    label: str
    counterfactual: bool
    created_at: str
    states: list[str] = field(default_factory=list)

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "kind": "simulation_branch",
            "id": self.id,
            "owner": OWNER,
            "instance_id": self.instance_id,
            "parent_branch_id": self.parent_branch_id,
            "fork_state_id": self.fork_state_id,
            "label": self.label,
            "counterfactual": self.counterfactual,
            "created_at": self.created_at,
            "states": list(self.states),
            "derived": True,
            "authority_effect": "none",
        }


@dataclass(frozen=True, slots=True)
class SimulationCheckpoint:
    id: str
    instance_id: str
    branch_id: str
    state_id: str
    state_digest: str
    label: str
    created_at: str

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "kind": "simulation_checkpoint",
            "id": self.id,
            "owner": OWNER,
            "instance_id": self.instance_id,
            "branch_id": self.branch_id,
            "state_id": self.state_id,
            "state_digest": self.state_digest,
            "label": self.label,
            "created_at": self.created_at,
            "immutable": True,
            "derived": True,
            "authority_effect": "none",
        }


@dataclass(slots=True)
class SimulationInstance:
    id: str
    definition_id: str
    seed: int
    created_at: str
    root_branch_id: str
    branches: dict[str, SimulationBranch] = field(
        default_factory=dict
    )
    states: dict[str, SimulationState] = field(
        default_factory=dict
    )
    checkpoints: dict[
        str,
        SimulationCheckpoint,
    ] = field(default_factory=dict)
    receipts: list[dict[str, Any]] = field(
        default_factory=list
    )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "kind": "simulation_instance",
            "id": self.id,
            "owner": OWNER,
            "definition_id": self.definition_id,
            "seed": self.seed,
            "created_at": self.created_at,
            "root_branch_id": self.root_branch_id,
            "branches": {
                key: value.projection()
                for key, value in sorted(
                    self.branches.items()
                )
            },
            "checkpoints": {
                key: value.projection()
                for key, value in sorted(
                    self.checkpoints.items()
                )
            },
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


Transition = Callable[
    [
        Mapping[str, Any],
        Any,
        random.Random,
        Mapping[str, Any],
    ],
    Mapping[str, Any],
]


class SimulationRuntime:
    def __init__(self) -> None:
        self.definitions: dict[
            str,
            SimulationDefinition,
        ] = {}
        self.instances: dict[
            str,
            SimulationInstance,
        ] = {}

    def define(
        self,
        name: str,
        *,
        parameters: Mapping[str, Any] | None = None,
        constraints: Sequence[Any] | None = None,
        dependencies: Sequence[str] | None = None,
        sources: Sequence[Any] | None = None,
        execution_rules: Mapping[
            str,
            Any,
        ] | None = None,
        uncertainty: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> SimulationDefinition:
        normalized_name = normalize_text(name)

        if not normalized_name:
            raise SimulationInvariantError(
                "simulation name is required"
            )

        material = {
            "name": normalized_name,
            "parameters": normalize_mapping(parameters),
            "constraints": normalize_sequence(
                constraints
            ),
            "dependencies": sorted(
                {
                    normalize_text(value)
                    for value in (
                        dependencies or ()
                    )
                    if normalize_text(value)
                }
            ),
            "sources": normalize_sequence(sources),
            "execution_rules": normalize_mapping(
                execution_rules
            ),
            "uncertainty": normalize_mapping(
                uncertainty
            ),
        }

        definition = SimulationDefinition(
            id=stable_id(
                "carbon-definition",
                material,
            ),
            name=normalized_name,
            parameters=material["parameters"],
            constraints=tuple(
                material["constraints"]
            ),
            dependencies=tuple(
                material["dependencies"]
            ),
            sources=tuple(material["sources"]),
            execution_rules=material[
                "execution_rules"
            ],
            uncertainty=material["uncertainty"],
            created_at=utc_now(),
        )

        self.definitions[definition.id] = definition
        return definition

    def instantiate(
        self,
        definition_id: str,
        *,
        initial_state: Mapping[
            str,
            Any,
        ] | None = None,
        seed: int | None = None,
    ) -> SimulationInstance:
        definition = self._definition(
            definition_id
        )

        actual_seed = (
            int(seed)
            if seed is not None
            else random.SystemRandom().randrange(
                0,
                2**63,
            )
        )

        instance_id = (
            "carbon-instance:"
            + uuid.uuid4().hex
        )

        root_branch_id = (
            "carbon-branch:"
            + uuid.uuid4().hex
        )

        instance = SimulationInstance(
            id=instance_id,
            definition_id=definition.id,
            seed=actual_seed,
            created_at=utc_now(),
            root_branch_id=root_branch_id,
        )

        branch = SimulationBranch(
            id=root_branch_id,
            instance_id=instance_id,
            parent_branch_id=None,
            fork_state_id=None,
            label="root",
            counterfactual=False,
            created_at=utc_now(),
        )

        instance.branches[branch.id] = branch

        self.instances[instance.id] = instance

        self._append_state(
            instance,
            branch,
            values=normalize_mapping(
                initial_state
            ),
            simulation_time=0.0,
            parent_state_id=None,
            event={
                "type": "simulation_instantiated"
            },
        )

        self._receipt(
            instance,
            operation="instantiate",
            branch_id=branch.id,
            inputs={
                "definition_id": definition.id,
                "seed": actual_seed,
            },
        )

        return instance

    def execute(
        self,
        instance_id: str,
        *,
        transition: Transition,
        events: Sequence[Any] = (),
        branch_id: str | None = None,
        steps: int = 1,
        delta_time: float = 1.0,
        parameters: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> list[SimulationState]:
        if steps < 1:
            raise SimulationInvariantError(
                "steps must be at least one"
            )

        if delta_time < 0:
            raise SimulationInvariantError(
                "delta_time cannot be negative"
            )

        instance = self._instance(instance_id)
        definition = self._definition(
            instance.definition_id
        )
        branch = self._branch(
            instance,
            branch_id or instance.root_branch_id,
        )

        effective_parameters = (
            normalize_mapping(
                definition.parameters
            )
        )
        effective_parameters.update(
            normalize_mapping(parameters)
        )

        rng = random.Random(instance.seed)

        existing_steps = max(
            0,
            len(branch.states) - 1,
        )

        for _ in range(existing_steps):
            rng.random()

        supplied_events = normalize_sequence(events)
        produced: list[SimulationState] = []

        for offset in range(steps):
            current = self._latest_state(
                instance,
                branch,
            )

            event = (
                supplied_events[offset]
                if offset < len(supplied_events)
                else None
            )

            result = transition(
                clone(current.values),
                clone(event),
                rng,
                clone(effective_parameters),
            )

            if not isinstance(result, Mapping):
                raise SimulationInvariantError(
                    "transition must return a mapping"
                )

            state = self._append_state(
                instance,
                branch,
                values=dict(result),
                simulation_time=(
                    current.simulation_time
                    + delta_time
                ),
                parent_state_id=current.id,
                event=event,
            )

            produced.append(state)

        self._receipt(
            instance,
            operation="execute",
            branch_id=branch.id,
            inputs={
                "steps": steps,
                "delta_time": delta_time,
                "events": supplied_events,
                "parameters": effective_parameters,
            },
            outputs=[
                state.id for state in produced
            ],
        )

        return produced

    def checkpoint(
        self,
        instance_id: str,
        *,
        branch_id: str | None = None,
        state_id: str | None = None,
        label: str = "",
    ) -> SimulationCheckpoint:
        instance = self._instance(instance_id)
        branch = self._branch(
            instance,
            branch_id or instance.root_branch_id,
        )

        state = (
            self._state(instance, state_id)
            if state_id
            else self._latest_state(
                instance,
                branch,
            )
        )

        if state.branch_id != branch.id:
            raise SimulationInvariantError(
                "checkpoint state does not belong "
                "to branch"
            )

        material = {
            "instance_id": instance.id,
            "branch_id": branch.id,
            "state_id": state.id,
            "state_digest": state.digest,
            "label": normalize_text(label),
        }

        checkpoint = SimulationCheckpoint(
            id=stable_id(
                "carbon-checkpoint",
                material,
            ),
            instance_id=instance.id,
            branch_id=branch.id,
            state_id=state.id,
            state_digest=state.digest,
            label=normalize_text(label),
            created_at=utc_now(),
        )

        instance.checkpoints[
            checkpoint.id
        ] = checkpoint

        self._receipt(
            instance,
            operation="checkpoint",
            branch_id=branch.id,
            inputs={
                "state_id": state.id,
                "label": checkpoint.label,
            },
            outputs=[checkpoint.id],
        )

        return checkpoint

    def fork(
        self,
        instance_id: str,
        checkpoint_id: str,
        *,
        label: str = "",
        counterfactual: bool = True,
    ) -> SimulationBranch:
        instance = self._instance(instance_id)

        try:
            checkpoint = instance.checkpoints[
                checkpoint_id
            ]
        except KeyError as exc:
            raise SimulationNotFound(
                f"checkpoint not found: "
                f"{checkpoint_id}"
            ) from exc

        source_state = self._state(
            instance,
            checkpoint.state_id,
        )

        if source_state.digest != (
            checkpoint.state_digest
        ):
            raise SimulationInvariantError(
                "checkpoint state digest mismatch"
            )

        branch = SimulationBranch(
            id=(
                "carbon-branch:"
                + uuid.uuid4().hex
            ),
            instance_id=instance.id,
            parent_branch_id=checkpoint.branch_id,
            fork_state_id=source_state.id,
            label=(
                normalize_text(label)
                or "fork"
            ),
            counterfactual=bool(counterfactual),
            created_at=utc_now(),
        )

        instance.branches[branch.id] = branch

        self._append_state(
            instance,
            branch,
            values=source_state.values,
            simulation_time=(
                source_state.simulation_time
            ),
            parent_state_id=source_state.id,
            event={
                "type": "branch_fork",
                "checkpoint_id": checkpoint.id,
            },
        )

        self._receipt(
            instance,
            operation="fork",
            branch_id=branch.id,
            inputs={
                "checkpoint_id": checkpoint.id,
                "parent_branch_id": (
                    checkpoint.branch_id
                ),
                "counterfactual": (
                    branch.counterfactual
                ),
            },
            outputs=[branch.id],
        )

        return branch

    def compare(
        self,
        instance_id: str,
        left_state_id: str,
        right_state_id: str,
    ) -> dict[str, Any]:
        instance = self._instance(instance_id)
        left = self._state(
            instance,
            left_state_id,
        )
        right = self._state(
            instance,
            right_state_id,
        )

        keys = sorted(
            set(left.values)
            | set(right.values)
        )

        differences: dict[str, Any] = {}

        for key in keys:
            left_value = left.values.get(key)
            right_value = right.values.get(key)

            if left_value != right_value:
                differences[key] = {
                    "left": clone(left_value),
                    "right": clone(right_value),
                }

        return {
            "schema": SCHEMA,
            "kind": "simulation_comparison",
            "owner": OWNER,
            "instance_id": instance.id,
            "left_state_id": left.id,
            "right_state_id": right.id,
            "same": not differences,
            "differences": differences,
            "derived": True,
            "non_mutating": True,
            "authority_effect": "none",
        }

    def interrogate(
        self,
        instance_id: str,
        *,
        branch_id: str | None = None,
        state_id: str | None = None,
        keys: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        instance = self._instance(instance_id)

        if state_id:
            state = self._state(
                instance,
                state_id,
            )
        else:
            branch = self._branch(
                instance,
                branch_id
                or instance.root_branch_id,
            )
            state = self._latest_state(
                instance,
                branch,
            )

        requested = [
            normalize_text(key)
            for key in (keys or ())
            if normalize_text(key)
        ]

        values = (
            {
                key: clone(
                    state.values.get(key)
                )
                for key in requested
            }
            if requested
            else clone(state.values)
        )

        return {
            "schema": SCHEMA,
            "kind": "simulation_interrogation",
            "owner": OWNER,
            "instance_id": instance.id,
            "state_id": state.id,
            "branch_id": state.branch_id,
            "simulation_time": (
                state.simulation_time
            ),
            "values": values,
            "state_digest": state.digest,
            "derived": True,
            "non_mutating": True,
            "authority_effect": "none",
        }

    def replay_projection(
        self,
        instance_id: str,
        *,
        branch_id: str | None = None,
    ) -> dict[str, Any]:
        instance = self._instance(instance_id)
        branch = self._branch(
            instance,
            branch_id or instance.root_branch_id,
        )

        states = [
            self._state(
                instance,
                state_id,
            ).projection()
            for state_id in branch.states
        ]

        material = {
            "instance_id": instance.id,
            "definition_id": (
                instance.definition_id
            ),
            "seed": instance.seed,
            "branch": branch.projection(),
            "states": states,
        }

        return {
            "schema": SCHEMA,
            "kind": "simulation_replay_projection",
            "owner": OWNER,
            **material,
            "replay_digest": digest(material),
            "derived": True,
            "authority_effect": "none",
        }

    def export_instance(
        self,
        instance_id: str,
    ) -> dict[str, Any]:
        instance = self._instance(instance_id)
        definition = self._definition(
            instance.definition_id
        )

        payload = {
            "schema": SCHEMA,
            "kind": "simulation_export",
            "owner": OWNER,
            "definition": (
                definition.projection()
            ),
            "instance": instance.projection(),
            "states": {
                key: value.projection()
                for key, value in sorted(
                    instance.states.items()
                )
            },
            "receipts": clone(
                instance.receipts
            ),
            "authority_effect": "none",
            "authoritative": False,
        }

        payload["digest"] = digest(payload)
        return payload

    def _definition(
        self,
        definition_id: str,
    ) -> SimulationDefinition:
        try:
            return self.definitions[
                definition_id
            ]
        except KeyError as exc:
            raise SimulationNotFound(
                f"definition not found: "
                f"{definition_id}"
            ) from exc

    def _instance(
        self,
        instance_id: str,
    ) -> SimulationInstance:
        try:
            return self.instances[instance_id]
        except KeyError as exc:
            raise SimulationNotFound(
                f"instance not found: "
                f"{instance_id}"
            ) from exc

    @staticmethod
    def _branch(
        instance: SimulationInstance,
        branch_id: str,
    ) -> SimulationBranch:
        try:
            return instance.branches[branch_id]
        except KeyError as exc:
            raise SimulationNotFound(
                f"branch not found: {branch_id}"
            ) from exc

    @staticmethod
    def _state(
        instance: SimulationInstance,
        state_id: str | None,
    ) -> SimulationState:
        if not state_id:
            raise SimulationNotFound(
                "state id is required"
            )

        try:
            return instance.states[state_id]
        except KeyError as exc:
            raise SimulationNotFound(
                f"state not found: {state_id}"
            ) from exc

    def _latest_state(
        self,
        instance: SimulationInstance,
        branch: SimulationBranch,
    ) -> SimulationState:
        if not branch.states:
            raise SimulationInvariantError(
                "branch has no state"
            )

        return self._state(
            instance,
            branch.states[-1],
        )

    def _append_state(
        self,
        instance: SimulationInstance,
        branch: SimulationBranch,
        *,
        values: Mapping[str, Any],
        simulation_time: float,
        parent_state_id: str | None,
        event: Any,
    ) -> SimulationState:
        sequence = len(branch.states)

        material = {
            "instance_id": instance.id,
            "branch_id": branch.id,
            "sequence": sequence,
            "values": clone(dict(values)),
            "simulation_time": simulation_time,
            "parent_state_id": parent_state_id,
            "event": clone(event),
        }

        state = SimulationState(
            id=stable_id(
                "carbon-state",
                {
                    **material,
                    "nonce": uuid.uuid4().hex,
                },
            ),
            instance_id=instance.id,
            branch_id=branch.id,
            sequence=sequence,
            values=clone(dict(values)),
            simulation_time=float(
                simulation_time
            ),
            parent_state_id=parent_state_id,
            event=clone(event),
            created_at=utc_now(),
        )

        state.digest = digest(
            state.projection()
        )

        instance.states[state.id] = state
        branch.states.append(state.id)

        return state

    def _receipt(
        self,
        instance: SimulationInstance,
        *,
        operation: str,
        branch_id: str,
        inputs: Mapping[str, Any],
        outputs: Sequence[str] = (),
    ) -> dict[str, Any]:
        material = {
            "instance_id": instance.id,
            "definition_id": (
                instance.definition_id
            ),
            "operation": operation,
            "branch_id": branch_id,
            "inputs": clone(dict(inputs)),
            "outputs": list(outputs),
            "sequence": len(
                instance.receipts
            ),
        }

        receipt = {
            "schema": SCHEMA,
            "kind": "simulation_receipt",
            "id": stable_id(
                "carbon-receipt",
                material,
            ),
            "owner": OWNER,
            **material,
            "created_at": utc_now(),
            "derived": True,
            "authority_effect": "none",
        }

        receipt["digest"] = digest(receipt)
        instance.receipts.append(receipt)

        return receipt


runtime = SimulationRuntime()


def status() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "advanced proprietary simulation"
        ),
        "definitions": len(
            runtime.definitions
        ),
        "instances": len(runtime.instances),
        "capabilities": [
            "define",
            "instantiate",
            "execute",
            "checkpoint",
            "fork",
            "compare",
            "interrogate",
            "replay_projection",
            "export_instance",
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
