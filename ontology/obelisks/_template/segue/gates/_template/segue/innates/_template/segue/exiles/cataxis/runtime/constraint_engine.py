#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence

from spacetime import (
    OWNER,
    PhysicalEvent,
    Point3,
    TemporalConstraint,
    TimeWindow,
    distance,
    parse_time,
    reachable,
    validate_temporal_constraints,
    windows_overlap,
)

SCHEMA = "savant://cataxis/constraint-engine/1.0.0"


class ConstraintEngineError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResourceWindow:
    resource_id: str
    window: TimeWindow
    location: Point3 | None = None
    capacity: float = 1.0
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class Occupancy:
    subject_id: str
    location_id: str
    window: TimeWindow
    amount: float = 1.0


@dataclass(frozen=True, slots=True)
class RouteEdge:
    source: str
    destination: str
    distance_meters: float
    minimum_seconds: float
    capacity: float | None = None
    available: bool = True
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    event: PhysicalEvent
    window: TimeWindow
    location_id: str | None = None
    resource_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConstraintResult:
    passed: bool
    code: str
    reason: str
    subject: str | None = None
    metrics: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class FeasibilityReport:
    feasible: bool
    results: tuple[ConstraintResult, ...]
    metrics: Mapping[str, Any]
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
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return payload


def _positive(
    value: Any,
    name: str,
) -> float:
    number = float(value)

    if number <= 0:
        raise ConstraintEngineError(
            f"{name} must be positive"
        )

    return number


def occupancy_conflicts(
    occupancies: Sequence[Occupancy],
) -> tuple[ConstraintResult, ...]:
    results: list[ConstraintResult] = []

    ordered = sorted(
        occupancies,
        key=lambda item: (
            item.subject_id,
            parse_time(item.window.start),
            item.location_id,
        ),
    )

    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            if (
                first.subject_id
                != second.subject_id
            ):
                continue

            if (
                first.location_id
                == second.location_id
            ):
                continue

            if windows_overlap(
                first.window,
                second.window,
                touching_counts=False,
            ):
                results.append(
                    ConstraintResult(
                        passed=False,
                        code="double_occupancy",
                        reason=(
                            "subject occupies distinct "
                            "locations simultaneously"
                        ),
                        subject=first.subject_id,
                        metrics={
                            "first_location": (
                                first.location_id
                            ),
                            "second_location": (
                                second.location_id
                            ),
                            "first_window": asdict(
                                first.window
                            ),
                            "second_window": asdict(
                                second.window
                            ),
                        },
                    )
                )

    if not results:
        results.append(
            ConstraintResult(
                passed=True,
                code="occupancy_consistent",
                reason=(
                    "no contradictory simultaneous "
                    "occupancy detected"
                ),
            )
        )

    return tuple(results)


def resource_capacity(
    *,
    resources: Sequence[ResourceWindow],
    occupancies: Sequence[Occupancy],
) -> tuple[ConstraintResult, ...]:
    results: list[ConstraintResult] = []

    for resource in resources:
        capacity = _positive(
            resource.capacity,
            "resource capacity",
        )

        relevant = [
            occupancy
            for occupancy in occupancies
            if (
                occupancy.location_id
                == resource.resource_id
                and windows_overlap(
                    occupancy.window,
                    resource.window,
                    touching_counts=False,
                )
            )
        ]

        boundaries: set[datetime] = set()

        for occupancy in relevant:
            start, end = occupancy.window.bounds()
            boundaries.add(start)
            boundaries.add(end)

        points = sorted(boundaries)

        exceeded = False
        peak = 0.0

        for left, right in zip(
            points,
            points[1:],
        ):
            if right <= left:
                continue

            midpoint = (
                left
                + (right - left) / 2
            )

            load = 0.0

            for occupancy in relevant:
                start, end = (
                    occupancy.window.bounds()
                )

                if start <= midpoint < end:
                    load += float(
                        occupancy.amount
                    )

            peak = max(peak, load)

            if load > capacity:
                exceeded = True

        results.append(
            ConstraintResult(
                passed=not exceeded,
                code=(
                    "capacity_exceeded"
                    if exceeded
                    else "capacity_satisfied"
                ),
                reason=(
                    "resource capacity exceeded"
                    if exceeded
                    else "resource capacity satisfied"
                ),
                subject=resource.resource_id,
                metrics={
                    "capacity": capacity,
                    "peak_load": peak,
                },
            )
        )

    return tuple(results)


def transition_feasibility(
    *,
    subject_id: str,
    origin: Point3,
    destination: Point3,
    departure: Any,
    arrival: Any,
    maximum_velocity: float,
    velocity_unit: str = "m/s",
) -> ConstraintResult:
    result = reachable(
        origin,
        destination,
        departure=departure,
        arrival_deadline=arrival,
        velocity_limit=maximum_velocity,
        velocity_unit=velocity_unit,
    )

    return ConstraintResult(
        passed=result.reachable,
        code=(
            "transition_reachable"
            if result.reachable
            else "transition_unreachable"
        ),
        reason=result.reason,
        subject=subject_id,
        metrics=asdict(result),
    )


def validate_event_graph(
    *,
    events: Sequence[PhysicalEvent],
    constraints: Sequence[
        TemporalConstraint
    ],
) -> ConstraintResult:
    passed, failures = (
        validate_temporal_constraints(
            events,
            constraints,
        )
    )

    return ConstraintResult(
        passed=passed,
        code=(
            "temporal_graph_valid"
            if passed
            else "temporal_graph_invalid"
        ),
        reason=(
            "temporal constraints satisfied"
            if passed
            else "; ".join(failures)
        ),
        metrics={
            "event_count": len(events),
            "constraint_count": len(
                constraints
            ),
            "failures": list(failures),
        },
    )


def shortest_route(
    *,
    edges: Sequence[RouteEdge],
    origin: str,
    destination: str,
) -> dict[str, Any] | None:
    adjacency: dict[
        str,
        list[RouteEdge],
    ] = {}

    for edge in edges:
        if not edge.available:
            continue

        if edge.minimum_seconds < 0:
            raise ConstraintEngineError(
                "route duration cannot be negative"
            )

        adjacency.setdefault(
            edge.source,
            [],
        ).append(edge)

    queue: list[
        tuple[float, str, tuple[str, ...]]
    ] = [
        (
            0.0,
            origin,
            (origin,),
        )
    ]

    best: dict[str, float] = {
        origin: 0.0
    }

    while queue:
        seconds, node, path = (
            heapq.heappop(queue)
        )

        if node == destination:
            return {
                "origin": origin,
                "destination": destination,
                "path": list(path),
                "minimum_seconds": seconds,
            }

        if seconds > best.get(
            node,
            float("inf"),
        ):
            continue

        for edge in adjacency.get(
            node,
            (),
        ):
            candidate = (
                seconds
                + edge.minimum_seconds
            )

            if candidate >= best.get(
                edge.destination,
                float("inf"),
            ):
                continue

            best[edge.destination] = (
                candidate
            )

            heapq.heappush(
                queue,
                (
                    candidate,
                    edge.destination,
                    path
                    + (
                        edge.destination,
                    ),
                ),
            )

    return None


def route_arrival(
    *,
    route: Mapping[str, Any],
    departure: Any,
) -> str:
    start = parse_time(departure)

    seconds = float(
        route["minimum_seconds"]
    )

    if seconds < 0:
        raise ConstraintEngineError(
            "route duration cannot be negative"
        )

    return (
        start
        + timedelta(seconds=seconds)
    ).isoformat()


def route_distance(
    *,
    points: Mapping[str, Point3],
    path: Sequence[str],
) -> float:
    if len(path) < 2:
        return 0.0

    total = 0.0

    for source, destination in zip(
        path,
        path[1:],
    ):
        try:
            first = points[source]
            second = points[destination]
        except KeyError as exc:
            raise ConstraintEngineError(
                f"missing route point: {exc.args[0]}"
            ) from exc

        total += distance(
            first,
            second,
            output_unit="m",
        )

    return total


def assess(
    results: Iterable[
        ConstraintResult
    ],
) -> FeasibilityReport:
    normalized = tuple(results)

    feasible = all(
        result.passed
        for result in normalized
    )

    failed = tuple(
        result.code
        for result in normalized
        if not result.passed
    )

    return FeasibilityReport(
        feasible=feasible,
        results=normalized,
        metrics={
            "check_count": len(
                normalized
            ),
            "passed_count": sum(
                1
                for result in normalized
                if result.passed
            ),
            "failed_count": len(
                failed
            ),
            "failed_codes": list(
                failed
            ),
        },
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "spacetime",
        "authority_effect": "none",
        "capabilities": [
            "occupancy_consistency",
            "double_occupancy_detection",
            "resource_capacity",
            "temporal_dependency_validation",
            "physical_transition_feasibility",
            "velocity_bounded_reachability",
            "route_graphs",
            "shortest_route",
            "route_arrival_projection",
            "route_distance",
            "resource_windows",
            "event_windows",
            "logistical_feasibility",
            "constraint_aggregation",
            "failure_reason_projection",
            "deterministic_reports",
            "mobius_logistics_support",
            "carbon_world_constraint_support",
            "filament_projection_support",
            "zero_quantitative_boundary",
        ],
    }
