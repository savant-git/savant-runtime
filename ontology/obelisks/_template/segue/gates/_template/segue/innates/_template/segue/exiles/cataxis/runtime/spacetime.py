#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence

OWNER = "cataxis"
SCHEMA = "savant://cataxis/spacetime/1.0.0"

EPSILON = 1e-12

DISTANCE_FACTORS_METERS = {
    "m": 1.0,
    "km": 1000.0,
    "cm": 0.01,
    "mm": 0.001,
    "mi": 1609.344,
    "ft": 0.3048,
    "in": 0.0254,
}

DURATION_FACTORS_SECONDS = {
    "s": 1.0,
    "ms": 0.001,
    "min": 60.0,
    "h": 3600.0,
    "day": 86400.0,
}

VELOCITY_FACTORS_MPS = {
    "m/s": 1.0,
    "km/h": 1000.0 / 3600.0,
    "mph": 1609.344 / 3600.0,
    "ft/s": 0.3048,
}


class CataxisError(RuntimeError):
    pass


class UnitError(CataxisError):
    pass


class TemporalError(CataxisError):
    pass


class SpatialError(CataxisError):
    pass


class FeasibilityError(CataxisError):
    pass


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


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _finite(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CataxisError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise CataxisError(
            f"{name} must be finite"
        )

    return number


def _nonnegative(value: Any, name: str) -> float:
    number = _finite(value, name)

    if number < 0:
        raise CataxisError(
            f"{name} must be nonnegative"
        )

    return number


def parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()

        if not text:
            raise TemporalError(
                "timestamp is required"
            )

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise TemporalError(
                f"invalid timestamp: {value}"
            ) from exc

    if parsed.tzinfo is None:
        raise TemporalError(
            "timestamp must include timezone"
        )

    return parsed.astimezone(UTC)


def convert(
    value: Any,
    *,
    from_unit: str,
    to_unit: str,
    dimension: str,
) -> float:
    tables = {
        "distance": DISTANCE_FACTORS_METERS,
        "duration": DURATION_FACTORS_SECONDS,
        "velocity": VELOCITY_FACTORS_MPS,
    }

    table = tables.get(
        str(dimension).strip().lower()
    )

    if table is None:
        raise UnitError(
            f"unsupported dimension: {dimension}"
        )

    source = str(from_unit).strip()
    target = str(to_unit).strip()

    if source not in table:
        raise UnitError(
            f"unsupported {dimension} unit: {source}"
        )

    if target not in table:
        raise UnitError(
            f"unsupported {dimension} unit: {target}"
        )

    number = _finite(value, "value")

    base = number * table[source]

    return base / table[target]


@dataclass(frozen=True, slots=True)
class Point3:
    x: float
    y: float
    z: float = 0.0
    unit: str = "m"

    def meters(self) -> tuple[float, float, float]:
        if self.unit not in DISTANCE_FACTORS_METERS:
            raise UnitError(
                f"unsupported distance unit: {self.unit}"
            )

        factor = DISTANCE_FACTORS_METERS[
            self.unit
        ]

        return (
            _finite(self.x, "x") * factor,
            _finite(self.y, "y") * factor,
            _finite(self.z, "z") * factor,
        )


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start: str
    end: str

    def bounds(
        self,
    ) -> tuple[datetime, datetime]:
        start = parse_time(self.start)
        end = parse_time(self.end)

        if end < start:
            raise TemporalError(
                "time window ends before it starts"
            )

        return start, end

    @property
    def seconds(self) -> float:
        start, end = self.bounds()
        return (end - start).total_seconds()


@dataclass(frozen=True, slots=True)
class PhysicalEvent:
    event_id: str
    at: str
    location: Point3 | None = None
    duration_seconds: float = 0.0
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def timestamp(self) -> datetime:
        return parse_time(self.at)


@dataclass(frozen=True, slots=True)
class TemporalConstraint:
    before: str
    after: str
    minimum_gap_seconds: float = 0.0
    maximum_gap_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class Reachability:
    reachable: bool
    distance_meters: float
    available_seconds: float
    required_seconds: float | None
    required_velocity_mps: float | None
    velocity_limit_mps: float | None
    reason: str


@dataclass(frozen=True, slots=True)
class FeasibilityProjection:
    feasible: bool
    temporal: bool
    spatial: bool
    physical: bool
    reasons: tuple[str, ...]
    metrics: Mapping[str, Any]
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = utc_now()
        payload["digest"] = digest(payload)
        return payload


def distance(
    first: Point3,
    second: Point3,
    *,
    output_unit: str = "m",
) -> float:
    ax, ay, az = first.meters()
    bx, by, bz = second.meters()

    meters = math.sqrt(
        ((bx - ax) ** 2)
        + ((by - ay) ** 2)
        + ((bz - az) ** 2)
    )

    return convert(
        meters,
        from_unit="m",
        to_unit=output_unit,
        dimension="distance",
    )


def duration_between(
    start: Any,
    end: Any,
    *,
    output_unit: str = "s",
) -> float:
    start_dt = parse_time(start)
    end_dt = parse_time(end)

    seconds = (
        end_dt - start_dt
    ).total_seconds()

    return convert(
        seconds,
        from_unit="s",
        to_unit=output_unit,
        dimension="duration",
    )


def required_velocity(
    first: Point3,
    second: Point3,
    *,
    start: Any,
    end: Any,
    output_unit: str = "m/s",
) -> float:
    seconds = duration_between(
        start,
        end,
        output_unit="s",
    )

    meters = distance(
        first,
        second,
        output_unit="m",
    )

    if seconds < 0:
        raise TemporalError(
            "arrival precedes departure"
        )

    if abs(seconds) <= EPSILON:
        if meters <= EPSILON:
            return 0.0

        return math.inf

    meters_per_second = meters / seconds

    return convert(
        meters_per_second,
        from_unit="m/s",
        to_unit=output_unit,
        dimension="velocity",
    )


def travel_time(
    first: Point3,
    second: Point3,
    *,
    velocity: Any,
    velocity_unit: str = "m/s",
    output_unit: str = "s",
) -> float:
    speed_mps = convert(
        _nonnegative(velocity, "velocity"),
        from_unit=velocity_unit,
        to_unit="m/s",
        dimension="velocity",
    )

    meters = distance(
        first,
        second,
        output_unit="m",
    )

    if speed_mps <= EPSILON:
        if meters <= EPSILON:
            seconds = 0.0
        else:
            return math.inf
    else:
        seconds = meters / speed_mps

    return convert(
        seconds,
        from_unit="s",
        to_unit=output_unit,
        dimension="duration",
    )


def reachable(
    first: Point3,
    second: Point3,
    *,
    departure: Any,
    arrival_deadline: Any,
    velocity_limit: Any | None = None,
    velocity_unit: str = "m/s",
) -> Reachability:
    available = duration_between(
        departure,
        arrival_deadline,
        output_unit="s",
    )

    meters = distance(
        first,
        second,
        output_unit="m",
    )

    if available < 0:
        return Reachability(
            reachable=False,
            distance_meters=meters,
            available_seconds=available,
            required_seconds=None,
            required_velocity_mps=None,
            velocity_limit_mps=None,
            reason="arrival deadline precedes departure",
        )

    if meters <= EPSILON:
        return Reachability(
            reachable=True,
            distance_meters=0.0,
            available_seconds=available,
            required_seconds=0.0,
            required_velocity_mps=0.0,
            velocity_limit_mps=(
                None
                if velocity_limit is None
                else convert(
                    velocity_limit,
                    from_unit=velocity_unit,
                    to_unit="m/s",
                    dimension="velocity",
                )
            ),
            reason="origin and destination coincide",
        )

    if available <= EPSILON:
        return Reachability(
            reachable=False,
            distance_meters=meters,
            available_seconds=available,
            required_seconds=None,
            required_velocity_mps=math.inf,
            velocity_limit_mps=None,
            reason="no positive travel time available",
        )

    required_mps = meters / available

    if velocity_limit is None:
        return Reachability(
            reachable=True,
            distance_meters=meters,
            available_seconds=available,
            required_seconds=None,
            required_velocity_mps=required_mps,
            velocity_limit_mps=None,
            reason=(
                "geometrically reachable; "
                "no velocity limit supplied"
            ),
        )

    limit_mps = convert(
        _nonnegative(
            velocity_limit,
            "velocity_limit",
        ),
        from_unit=velocity_unit,
        to_unit="m/s",
        dimension="velocity",
    )

    required_seconds = (
        math.inf
        if limit_mps <= EPSILON
        else meters / limit_mps
    )

    possible = (
        required_mps
        <= limit_mps + EPSILON
    )

    return Reachability(
        reachable=possible,
        distance_meters=meters,
        available_seconds=available,
        required_seconds=required_seconds,
        required_velocity_mps=required_mps,
        velocity_limit_mps=limit_mps,
        reason=(
            "reachable within velocity limit"
            if possible
            else "velocity limit makes arrival infeasible"
        ),
    )


def windows_overlap(
    first: TimeWindow,
    second: TimeWindow,
    *,
    touching_counts: bool = True,
) -> bool:
    a_start, a_end = first.bounds()
    b_start, b_end = second.bounds()

    if touching_counts:
        return (
            a_start <= b_end
            and b_start <= a_end
        )

    return (
        a_start < b_end
        and b_start < a_end
    )


def intersection(
    first: TimeWindow,
    second: TimeWindow,
) -> TimeWindow | None:
    a_start, a_end = first.bounds()
    b_start, b_end = second.bounds()

    start = max(a_start, b_start)
    end = min(a_end, b_end)

    if end < start:
        return None

    return TimeWindow(
        start=start.isoformat(),
        end=end.isoformat(),
    )


def event_order(
    events: Iterable[PhysicalEvent],
) -> tuple[PhysicalEvent, ...]:
    return tuple(
        sorted(
            events,
            key=lambda event: (
                event.timestamp(),
                event.event_id,
            ),
        )
    )


def validate_temporal_constraints(
    events: Sequence[PhysicalEvent],
    constraints: Sequence[
        TemporalConstraint
    ],
) -> tuple[bool, tuple[str, ...]]:
    by_id = {
        event.event_id: event
        for event in events
    }

    failures: list[str] = []

    for constraint in constraints:
        before = by_id.get(
            constraint.before
        )
        after = by_id.get(
            constraint.after
        )

        if before is None:
            failures.append(
                f"missing event: {constraint.before}"
            )
            continue

        if after is None:
            failures.append(
                f"missing event: {constraint.after}"
            )
            continue

        minimum = _nonnegative(
            constraint.minimum_gap_seconds,
            "minimum_gap_seconds",
        )

        maximum = (
            None
            if constraint.maximum_gap_seconds
            is None
            else _nonnegative(
                constraint.maximum_gap_seconds,
                "maximum_gap_seconds",
            )
        )

        if (
            maximum is not None
            and maximum < minimum
        ):
            failures.append(
                f"{constraint.before}->{constraint.after}: "
                "maximum gap is below minimum gap"
            )
            continue

        before_end = (
            before.timestamp()
            + timedelta(
                seconds=_nonnegative(
                    before.duration_seconds,
                    "duration_seconds",
                )
            )
        )

        gap = (
            after.timestamp()
            - before_end
        ).total_seconds()

        if gap + EPSILON < minimum:
            failures.append(
                f"{constraint.before}->{constraint.after}: "
                f"gap {gap} below minimum {minimum}"
            )

        if (
            maximum is not None
            and gap - EPSILON > maximum
        ):
            failures.append(
                f"{constraint.before}->{constraint.after}: "
                f"gap {gap} above maximum {maximum}"
            )

    return (
        not failures,
        tuple(failures),
    )


def assess_transition(
    *,
    origin: Point3,
    destination: Point3,
    departure: Any,
    arrival_deadline: Any,
    velocity_limit: Any | None = None,
    velocity_unit: str = "m/s",
    constraints_satisfied: bool = True,
    additional_reasons: Sequence[str] = (),
) -> FeasibilityProjection:
    reach = reachable(
        origin,
        destination,
        departure=departure,
        arrival_deadline=arrival_deadline,
        velocity_limit=velocity_limit,
        velocity_unit=velocity_unit,
    )

    temporal = (
        reach.available_seconds >= 0
    )

    spatial = math.isfinite(
        reach.distance_meters
    )

    physical = reach.reachable

    reasons = list(additional_reasons)

    if not temporal:
        reasons.append(
            "temporal ordering is infeasible"
        )

    if not spatial:
        reasons.append(
            "spatial distance is invalid"
        )

    if not physical:
        reasons.append(
            reach.reason
        )

    if not constraints_satisfied:
        reasons.append(
            "external physical constraints are unsatisfied"
        )

    feasible = (
        temporal
        and spatial
        and physical
        and constraints_satisfied
    )

    if feasible and not reasons:
        reasons.append(
            "transition satisfies supplied spacetime constraints"
        )

    return FeasibilityProjection(
        feasible=feasible,
        temporal=temporal,
        spatial=spatial,
        physical=physical,
        reasons=tuple(reasons),
        metrics={
            "distance_meters": (
                reach.distance_meters
            ),
            "available_seconds": (
                reach.available_seconds
            ),
            "required_seconds": (
                reach.required_seconds
            ),
            "required_velocity_mps": (
                reach.required_velocity_mps
            ),
            "velocity_limit_mps": (
                reach.velocity_limit_mps
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
            "timezone_aware_time",
            "duration",
            "time_windows",
            "window_intersection",
            "event_ordering",
            "temporal_constraints",
            "three_dimensional_points",
            "distance",
            "unit_conversion",
            "velocity",
            "travel_time",
            "reachability",
            "physical_feasibility",
            "temporal_feasibility",
            "spatial_feasibility",
            "trajectory_primitives",
            "constraint_projection",
            "deterministic_metrics",
            "digestable_projection",
            "mobius_logistics_support",
            "carbon_physics_support",
            "zero_mathematics_boundary",
        ],
    }
