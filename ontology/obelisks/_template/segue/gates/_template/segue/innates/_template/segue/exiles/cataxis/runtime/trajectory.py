#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, Sequence

from spacetime import (
    OWNER,
    EPSILON,
    Point3,
    convert,
    distance,
    parse_time,
)

SCHEMA = "savant://cataxis/trajectory/1.0.0"


class TrajectoryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Waypoint:
    waypoint_id: str
    location: Point3
    at: str

    def timestamp(self) -> datetime:
        return parse_time(self.at)


@dataclass(frozen=True, slots=True)
class Segment:
    segment_id: str
    origin: Waypoint
    destination: Waypoint
    distance_meters: float
    duration_seconds: float
    velocity_mps: float


@dataclass(frozen=True, slots=True)
class TrajectoryProjection:
    trajectory_id: str
    waypoints: tuple[Waypoint, ...]
    segments: tuple[Segment, ...]
    total_distance_meters: float
    total_duration_seconds: float
    average_velocity_mps: float
    valid: bool
    violations: tuple[str, ...]
    metadata: Mapping[str, Any]
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


def ordered_waypoints(
    waypoints: Sequence[Waypoint],
) -> tuple[Waypoint, ...]:
    return tuple(
        sorted(
            waypoints,
            key=lambda item: (
                item.timestamp(),
                item.waypoint_id,
            ),
        )
    )


def segment(
    origin: Waypoint,
    destination: Waypoint,
    *,
    segment_id: str | None = None,
) -> Segment:
    start = origin.timestamp()
    end = destination.timestamp()

    seconds = (
        end - start
    ).total_seconds()

    if seconds < 0:
        raise TrajectoryError(
            "destination precedes origin"
        )

    meters = distance(
        origin.location,
        destination.location,
        output_unit="m",
    )

    if seconds <= EPSILON:
        velocity = (
            0.0
            if meters <= EPSILON
            else math.inf
        )
    else:
        velocity = meters / seconds

    return Segment(
        segment_id=(
            segment_id
            or (
                f"{origin.waypoint_id}"
                f"->{destination.waypoint_id}"
            )
        ),
        origin=origin,
        destination=destination,
        distance_meters=meters,
        duration_seconds=seconds,
        velocity_mps=velocity,
    )


def build(
    trajectory_id: str,
    waypoints: Sequence[Waypoint],
    *,
    maximum_velocity: float | None = None,
    velocity_unit: str = "m/s",
    preserve_input_order: bool = True,
    metadata: Mapping[str, Any] | None = None,
) -> TrajectoryProjection:
    points = tuple(waypoints)

    if not points:
        raise TrajectoryError(
            "trajectory requires at least one waypoint"
        )

    violations: list[str] = []

    if preserve_input_order:
        for first, second in zip(
            points,
            points[1:],
        ):
            if (
                second.timestamp()
                < first.timestamp()
            ):
                violations.append(
                    f"{first.waypoint_id}"
                    f"->{second.waypoint_id}: "
                    "temporal order reversed"
                )
    else:
        points = ordered_waypoints(points)

    segments = tuple(
        segment(
            first,
            second,
            segment_id=f"segment:{index}",
        )
        for index, (first, second)
        in enumerate(
            zip(
                points,
                points[1:],
            ),
            start=1,
        )
    )

    limit_mps: float | None = None

    if maximum_velocity is not None:
        limit_mps = convert(
            maximum_velocity,
            from_unit=velocity_unit,
            to_unit="m/s",
            dimension="velocity",
        )

        if limit_mps < 0:
            raise TrajectoryError(
                "maximum velocity must be nonnegative"
            )

        for item in segments:
            if (
                item.velocity_mps
                > limit_mps + EPSILON
            ):
                violations.append(
                    f"{item.segment_id}: "
                    "velocity limit exceeded"
                )

    total_distance = sum(
        item.distance_meters
        for item in segments
    )

    total_duration = sum(
        item.duration_seconds
        for item in segments
    )

    average_velocity = (
        0.0
        if total_duration <= EPSILON
        and total_distance <= EPSILON
        else (
            math.inf
            if total_duration <= EPSILON
            else total_distance
            / total_duration
        )
    )

    return TrajectoryProjection(
        trajectory_id=str(
            trajectory_id
        ).strip(),
        waypoints=points,
        segments=segments,
        total_distance_meters=total_distance,
        total_duration_seconds=total_duration,
        average_velocity_mps=average_velocity,
        valid=not violations,
        violations=tuple(violations),
        metadata={
            **dict(metadata or {}),
            "maximum_velocity_mps": (
                limit_mps
            ),
        },
    )


def interpolate(
    first: Waypoint,
    second: Waypoint,
    at: Any,
) -> Point3:
    start = first.timestamp()
    end = second.timestamp()
    target = parse_time(at)

    if target < start or target > end:
        raise TrajectoryError(
            "interpolation time is outside segment"
        )

    duration = (
        end - start
    ).total_seconds()

    if duration <= EPSILON:
        if distance(
            first.location,
            second.location,
            output_unit="m",
        ) > EPSILON:
            raise TrajectoryError(
                "instantaneous nonzero displacement "
                "cannot be interpolated"
            )

        return first.location

    fraction = (
        target - start
    ).total_seconds() / duration

    ax, ay, az = first.location.meters()
    bx, by, bz = second.location.meters()

    return Point3(
        x=ax + ((bx - ax) * fraction),
        y=ay + ((by - ay) * fraction),
        z=az + ((bz - az) * fraction),
        unit="m",
    )


def position_at(
    trajectory: TrajectoryProjection,
    at: Any,
) -> Point3:
    target = parse_time(at)

    first = trajectory.waypoints[0]
    last = trajectory.waypoints[-1]

    if target < first.timestamp():
        raise TrajectoryError(
            "time precedes trajectory"
        )

    if target > last.timestamp():
        raise TrajectoryError(
            "time follows trajectory"
        )

    if target == first.timestamp():
        return first.location

    for origin, destination in zip(
        trajectory.waypoints,
        trajectory.waypoints[1:],
    ):
        if (
            origin.timestamp()
            <= target
            <= destination.timestamp()
        ):
            return interpolate(
                origin,
                destination,
                target,
            )

    return last.location


def collision_candidates(
    first: TrajectoryProjection,
    second: TrajectoryProjection,
    *,
    threshold: float = 0.0,
    threshold_unit: str = "m",
    sample_seconds: float = 1.0,
) -> tuple[dict[str, Any], ...]:
    threshold_meters = convert(
        threshold,
        from_unit=threshold_unit,
        to_unit="m",
        dimension="distance",
    )

    if threshold_meters < 0:
        raise TrajectoryError(
            "collision threshold must be nonnegative"
        )

    if sample_seconds <= 0:
        raise TrajectoryError(
            "sample_seconds must be positive"
        )

    start = max(
        first.waypoints[0].timestamp(),
        second.waypoints[0].timestamp(),
    )

    end = min(
        first.waypoints[-1].timestamp(),
        second.waypoints[-1].timestamp(),
    )

    if end < start:
        return ()

    collisions: list[
        dict[str, Any]
    ] = []

    cursor = start

    while cursor <= end:
        first_position = position_at(
            first,
            cursor,
        )
        second_position = position_at(
            second,
            cursor,
        )

        separation = distance(
            first_position,
            second_position,
            output_unit="m",
        )

        if separation <= (
            threshold_meters + EPSILON
        ):
            collisions.append(
                {
                    "at": cursor.isoformat(),
                    "distance_meters": separation,
                    "first_position": asdict(
                        first_position
                    ),
                    "second_position": asdict(
                        second_position
                    ),
                }
            )

        cursor += timedelta(
            seconds=sample_seconds
        )

    return tuple(collisions)


def trajectory_digest(
    trajectory: TrajectoryProjection,
) -> str:
    payload = asdict(trajectory)

    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "spacetime",
        "authority_effect": "none",
        "capabilities": [
            "waypoints",
            "trajectory_segments",
            "trajectory_construction",
            "temporal_order_validation",
            "distance_accumulation",
            "duration_accumulation",
            "average_velocity",
            "velocity_limit_validation",
            "position_interpolation",
            "position_at_time",
            "trajectory_digest",
            "trajectory_replay",
            "collision_candidate_detection",
            "proximity_thresholds",
            "three_dimensional_motion",
            "timezone_aware_trajectories",
            "physical_impossibility_detection",
            "carbon_motion_support",
            "mobius_logistics_support",
            "filament_trajectory_projection",
        ],
    }
