#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence

from physics import Vector3
from spacetime import OWNER

SCHEMA = "savant://cataxis/integrator/1.0.0"


class IntegrationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DynamicState:
    time_seconds: float
    position: Vector3
    velocity: Vector3
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    method: str
    initial: DynamicState
    final: DynamicState
    steps: int
    step_seconds: float
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = (
            datetime.now(UTC).isoformat()
        )
        payload["digest"] = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return payload


Acceleration = Callable[
    [DynamicState],
    Vector3,
]


def _validate(
    *,
    step_seconds: float,
    steps: int,
) -> None:
    if step_seconds <= 0:
        raise IntegrationError(
            "step_seconds must be positive"
        )

    if steps < 0:
        raise IntegrationError(
            "steps must be nonnegative"
        )


def euler(
    state: DynamicState,
    acceleration: Acceleration,
    *,
    step_seconds: float,
    steps: int,
) -> IntegrationResult:
    _validate(
        step_seconds=step_seconds,
        steps=steps,
    )

    current = state

    for _ in range(steps):
        a = acceleration(current)

        current = DynamicState(
            time_seconds=(
                current.time_seconds
                + step_seconds
            ),
            position=(
                current.position.add(
                    current.velocity.scale(
                        step_seconds
                    )
                )
            ),
            velocity=(
                current.velocity.add(
                    a.scale(
                        step_seconds
                    )
                )
            ),
            metadata=current.metadata,
        )

    return IntegrationResult(
        method="euler",
        initial=state,
        final=current,
        steps=steps,
        step_seconds=step_seconds,
    )


def symplectic_euler(
    state: DynamicState,
    acceleration: Acceleration,
    *,
    step_seconds: float,
    steps: int,
) -> IntegrationResult:
    _validate(
        step_seconds=step_seconds,
        steps=steps,
    )

    current = state

    for _ in range(steps):
        a = acceleration(current)

        velocity = (
            current.velocity.add(
                a.scale(step_seconds)
            )
        )

        position = (
            current.position.add(
                velocity.scale(
                    step_seconds
                )
            )
        )

        current = DynamicState(
            time_seconds=(
                current.time_seconds
                + step_seconds
            ),
            position=position,
            velocity=velocity,
            metadata=current.metadata,
        )

    return IntegrationResult(
        method="symplectic_euler",
        initial=state,
        final=current,
        steps=steps,
        step_seconds=step_seconds,
    )


def velocity_verlet(
    state: DynamicState,
    acceleration: Acceleration,
    *,
    step_seconds: float,
    steps: int,
) -> IntegrationResult:
    _validate(
        step_seconds=step_seconds,
        steps=steps,
    )

    current = state
    dt = step_seconds

    for _ in range(steps):
        first_acceleration = (
            acceleration(current)
        )

        position = (
            current.position
            .add(
                current.velocity.scale(dt)
            )
            .add(
                first_acceleration.scale(
                    0.5 * dt * dt
                )
            )
        )

        provisional = DynamicState(
            time_seconds=(
                current.time_seconds + dt
            ),
            position=position,
            velocity=current.velocity,
            metadata=current.metadata,
        )

        second_acceleration = (
            acceleration(provisional)
        )

        velocity = (
            current.velocity
            .add(
                first_acceleration
                .add(second_acceleration)
                .scale(0.5 * dt)
            )
        )

        current = DynamicState(
            time_seconds=(
                current.time_seconds + dt
            ),
            position=position,
            velocity=velocity,
            metadata=current.metadata,
        )

    return IntegrationResult(
        method="velocity_verlet",
        initial=state,
        final=current,
        steps=steps,
        step_seconds=step_seconds,
    )


def trajectory(
    state: DynamicState,
    acceleration: Acceleration,
    *,
    step_seconds: float,
    steps: int,
) -> tuple[DynamicState, ...]:
    _validate(
        step_seconds=step_seconds,
        steps=steps,
    )

    states = [state]
    current = state
    dt = step_seconds

    for _ in range(steps):
        result = velocity_verlet(
            current,
            acceleration,
            step_seconds=dt,
            steps=1,
        )

        current = result.final
        states.append(current)

    return tuple(states)


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "time_integration",
            "euler_integration",
            "symplectic_euler",
            "velocity_verlet",
            "trajectory_projection",
            "deterministic_steps",
            "dynamic_state_receipts",
            "carbon_simulation_integration",
        ],
    }
