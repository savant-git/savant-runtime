#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import heapq
import json
import math

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    import networkx as nx

except ImportError:
    nx = None


try:
    from ortools.sat.python import cp_model

except ImportError:
    cp_model = None


owner = "carbon"
component = "oriel"
authority_effect = "none"

schema = "savant.carbon.oriel.v1"

earth_radius_km = 6371.0088

outcomes = {
    "pass",
    "fail",
    "advisory",
    "unknown",
}

source_classes = {
    "asserted",
    "verified_external",
    "admitted_evidence",
    "derived",
    "estimate",
    "simulation",
    "unknown",
}

precision_classes = {
    "second",
    "minute",
    "hour",
    "day",
    "bounded",
    "unknown",
}

constraint_classes = {
    "hard",
    "soft",
    "informational",
}

transport_defaults = {
    "tour_bus": {
        "minimum_speed_kph":
            62.0,

        "maximum_speed_kph":
            92.0,

        "distance_factor":
            1.18,

        "fixed_minutes":
            20,

        "minimum_recovery_minutes":
            0,
    },

    "car": {
        "minimum_speed_kph":
            68.0,

        "maximum_speed_kph":
            105.0,

        "distance_factor":
            1.17,

        "fixed_minutes":
            10,

        "minimum_recovery_minutes":
            0,
    },

    "rail": {
        "minimum_speed_kph":
            65.0,

        "maximum_speed_kph":
            170.0,

        "distance_factor":
            1.12,

        "fixed_minutes":
            45,

        "minimum_recovery_minutes":
            0,
    },

    "flight": {
        "minimum_speed_kph":
            560.0,

        "maximum_speed_kph":
            850.0,

        "distance_factor":
            1.0,

        "fixed_minutes":
            180,

        "minimum_recovery_minutes":
            30,
    },

    "walk": {
        "minimum_speed_kph":
            3.5,

        "maximum_speed_kph":
            6.0,

        "distance_factor":
            1.12,

        "fixed_minutes":
            0,

        "minimum_recovery_minutes":
            0,
    },
}

enhancements = (
    "bitemporal event metadata",
    "timezone-aware valid-time normalization",
    "dst-safe zoneinfo handling",
    "bounded temporal uncertainty",
    "temporal precision classes",
    "source-class provenance",
    "hard-soft-informational constraints",
    "locked temporal anchors",
    "great-circle geographic calculation",
    "source-backed explicit route edges",
    "weighted route graph traversal",
    "networkx shortest-path acceleration",
    "networkx route alternatives",
    "stdlib deterministic dijkstra fallback",
    "mode-specific transport profiles",
    "road-distance estimation with explicit estimate status",
    "minimum-maximum travel envelopes",
    "border and checkpoint buffers",
    "load-in setup windows",
    "load-out teardown windows",
    "recovery and sleep buffers",
    "entity double-booking detection",
    "venue occupancy collision detection",
    "shared-resource occupancy detection",
    "external historical constraint binding",
    "real-world venue closure binding",
    "real-world booking collision binding",
    "travel feasibility propagation",
    "schedule slack calculation",
    "chronometric pressure scoring",
    "continuous spacetime position projection",
    "route-progress interpolation",
    "entity encounter-window discovery",
    "proximity-window calculation",
    "candidate scene insertion windows",
    "unknown-preserving feasibility",
    "non-mutating quantum candidate evaluation",
    "deterministic itinerary digest",
    "constraint explanation receipts",
    "optional ortools cp-sat scheduling",
    "deterministic cp-sat execution parameters",
    "source-state versus simulation-state separation",
    "capability metadata projection",
    "filament-compatible capability projection metadata",
    "modus-compatible masking metadata",
)


class oriel_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def parse_datetime(
    value: Any,
    *,
    timezone_name: str | None = None,
) -> datetime:
    if isinstance(
        value,
        datetime,
    ):
        parsed = value

    else:
        text = str(
            value
        ).strip()

        if not text:
            raise oriel_error(
                "datetime value is required"
            )

        if text.endswith(
            "Z"
        ):
            text = (
                text[:-1]
                + "+00:00"
            )

        try:
            parsed = datetime.fromisoformat(
                text
            )

        except ValueError as exc:
            raise oriel_error(
                (
                    "invalid ISO datetime: "
                    + str(
                        value
                    )
                )
            ) from exc

    if parsed.tzinfo is None:
        if not timezone_name:
            raise oriel_error(
                (
                    "naive datetime requires "
                    "an explicit timezone"
                )
            )

        try:
            parsed = parsed.replace(
                tzinfo=ZoneInfo(
                    timezone_name
                )
            )

        except ZoneInfoNotFoundError as exc:
            raise oriel_error(
                (
                    "unknown timezone: "
                    + timezone_name
                )
            ) from exc

    return parsed


def to_utc(
    value: datetime,
) -> datetime:
    return value.astimezone(
        timezone.utc
    )


def minutes_between(
    left: datetime,
    right: datetime,
) -> float:
    return (
        to_utc(
            right
        )
        - to_utc(
            left
        )
    ).total_seconds() / 60.0


def midpoint(
    left: datetime,
    right: datetime,
) -> datetime:
    delta = (
        to_utc(
            right
        )
        - to_utc(
            left
        )
    )

    return (
        to_utc(
            left
        )
        + (
            delta
            / 2
        )
    )


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def haversine_km(
    left_latitude: float,
    left_longitude: float,
    right_latitude: float,
    right_longitude: float,
) -> float:
    left_lat = math.radians(
        left_latitude
    )

    right_lat = math.radians(
        right_latitude
    )

    latitude_delta = math.radians(
        right_latitude
        - left_latitude
    )

    longitude_delta = math.radians(
        right_longitude
        - left_longitude
    )

    value = (
        math.sin(
            latitude_delta
            / 2
        )
        ** 2
        + math.cos(
            left_lat
        )
        * math.cos(
            right_lat
        )
        * math.sin(
            longitude_delta
            / 2
        )
        ** 2
    )

    central_angle = (
        2
        * math.atan2(
            math.sqrt(
                value
            ),
            math.sqrt(
                1
                - value
            ),
        )
    )

    return (
        earth_radius_km
        * central_angle
    )


@dataclass(
    frozen=True
)
class temporal_window:
    earliest: datetime

    latest: datetime

    precision: str = "bounded"

    source_class: str = "unknown"

    source_refs: tuple[str, ...] = ()

    locked: bool = False

    transaction_at: str | None = None

    @classmethod
    def from_value(
        cls,
        value: Any,
        *,
        default_timezone:
            str
            | None = None,
        default_source_class:
            str = "unknown",
    ) -> temporal_window:
        if isinstance(
            value,
            temporal_window,
        ):
            return value

        if isinstance(
            value,
            (
                str,
                datetime,
            ),
        ):
            instant = parse_datetime(
                value,
                timezone_name=
                    default_timezone,
            )

            return cls(
                earliest=instant,
                latest=instant,
                precision="second",
                source_class=
                    default_source_class,
            )

        if not isinstance(
            value,
            Mapping,
        ):
            raise oriel_error(
                (
                    "temporal window must be "
                    "a datetime or object"
                )
            )

        timezone_name = (
            str(
                value.get(
                    "timezone"
                )
            ).strip()
            if value.get(
                "timezone"
            )
            is not None
            else default_timezone
        )

        if "at" in value:
            earliest = parse_datetime(
                value[
                    "at"
                ],
                timezone_name=
                    timezone_name,
            )

            latest = earliest

        else:
            earliest = parse_datetime(
                value.get(
                    "earliest"
                ),
                timezone_name=
                    timezone_name,
            )

            latest = parse_datetime(
                value.get(
                    "latest",
                    value.get(
                        "earliest"
                    ),
                ),
                timezone_name=
                    timezone_name,
            )

        if (
            to_utc(
                latest
            )
            < to_utc(
                earliest
            )
        ):
            raise oriel_error(
                (
                    "temporal latest precedes "
                    "temporal earliest"
                )
            )

        precision = str(
            value.get(
                "precision",
                (
                    "second"
                    if earliest
                    == latest
                    else "bounded"
                ),
            )
        ).strip().lower()

        if precision not in precision_classes:
            raise oriel_error(
                (
                    "unsupported temporal precision: "
                    + precision
                )
            )

        source_class = str(
            value.get(
                "source_class",
                default_source_class,
            )
        ).strip().lower()

        if source_class not in source_classes:
            raise oriel_error(
                (
                    "unsupported source class: "
                    + source_class
                )
            )

        source_refs = tuple(
            sorted(
                {
                    str(
                        item
                    ).strip()
                    for item
                    in value.get(
                        "source_refs",
                        [],
                    )
                    if str(
                        item
                    ).strip()
                }
            )
        )

        return cls(
            earliest=earliest,
            latest=latest,
            precision=precision,
            source_class=
                source_class,
            source_refs=
                source_refs,
            locked=bool(
                value.get(
                    "locked",
                    False,
                )
            ),
            transaction_at=(
                str(
                    value.get(
                        "transaction_at"
                    )
                )
                if value.get(
                    "transaction_at"
                )
                is not None
                else None
            ),
        )

    def midpoint(
        self,
    ) -> datetime:
        return midpoint(
            self.earliest,
            self.latest,
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "earliest":
                self.earliest.isoformat(),

            "latest":
                self.latest.isoformat(),

            "precision":
                self.precision,

            "source_class":
                self.source_class,

            "source_refs":
                list(
                    self.source_refs
                ),

            "locked":
                self.locked,

            "transaction_at":
                self.transaction_at,
        }


@dataclass(
    frozen=True
)
class location:
    id: str

    name: str

    latitude: float

    longitude: float

    timezone_name: str

    country: str | None = None

    region: str | None = None

    address: str | None = None

    source_class: str = "unknown"

    source_refs: tuple[str, ...] = ()

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> location:
        identifier = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if not identifier:
            raise oriel_error(
                "location id is required"
            )

        timezone_name = str(
            value.get(
                "timezone",
                "",
            )
        ).strip()

        if not timezone_name:
            raise oriel_error(
                (
                    "location timezone is required: "
                    + identifier
                )
            )

        try:
            ZoneInfo(
                timezone_name
            )

        except ZoneInfoNotFoundError as exc:
            raise oriel_error(
                (
                    "unknown timezone for location "
                    + identifier
                    + ": "
                    + timezone_name
                )
            ) from exc

        source_class = str(
            value.get(
                "source_class",
                "unknown",
            )
        ).strip().lower()

        if source_class not in source_classes:
            raise oriel_error(
                (
                    "unsupported location source class: "
                    + source_class
                )
            )

        return cls(
            id=identifier,
            name=str(
                value.get(
                    "name",
                    identifier,
                )
            ).strip(),
            latitude=float(
                value[
                    "latitude"
                ]
            ),
            longitude=float(
                value[
                    "longitude"
                ]
            ),
            timezone_name=
                timezone_name,
            country=(
                str(
                    value.get(
                        "country"
                    )
                ).strip()
                if value.get(
                    "country"
                )
                is not None
                else None
            ),
            region=(
                str(
                    value.get(
                        "region"
                    )
                ).strip()
                if value.get(
                    "region"
                )
                is not None
                else None
            ),
            address=(
                str(
                    value.get(
                        "address"
                    )
                ).strip()
                if value.get(
                    "address"
                )
                is not None
                else None
            ),
            source_class=
                source_class,
            source_refs=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "source_refs",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            metadata=copy.deepcopy(
                value.get(
                    "metadata",
                    {},
                )
            ),
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "id":
                self.id,

            "name":
                self.name,

            "latitude":
                self.latitude,

            "longitude":
                self.longitude,

            "timezone":
                self.timezone_name,

            "country":
                self.country,

            "region":
                self.region,

            "address":
                self.address,

            "source_class":
                self.source_class,

            "source_refs":
                list(
                    self.source_refs
                ),

            "metadata":
                copy.deepcopy(
                    dict(
                        self.metadata
                    )
                ),
        }


@dataclass(
    frozen=True
)
class transport_profile:
    id: str

    minimum_speed_kph: float

    maximum_speed_kph: float

    distance_factor: float = 1.0

    fixed_minutes: int = 0

    minimum_recovery_minutes: int = 0

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> transport_profile:
        identifier = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if not identifier:
            raise oriel_error(
                "transport profile id is required"
            )

        minimum_speed = float(
            value[
                "minimum_speed_kph"
            ]
        )

        maximum_speed = float(
            value[
                "maximum_speed_kph"
            ]
        )

        if (
            minimum_speed <= 0
            or maximum_speed <= 0
            or maximum_speed
            < minimum_speed
        ):
            raise oriel_error(
                (
                    "invalid speed envelope for "
                    + identifier
                )
            )

        return cls(
            id=identifier,
            minimum_speed_kph=
                minimum_speed,
            maximum_speed_kph=
                maximum_speed,
            distance_factor=float(
                value.get(
                    "distance_factor",
                    1.0,
                )
            ),
            fixed_minutes=int(
                value.get(
                    "fixed_minutes",
                    0,
                )
            ),
            minimum_recovery_minutes=int(
                value.get(
                    "minimum_recovery_minutes",
                    0,
                )
            ),
        )


@dataclass(
    frozen=True
)
class route_edge:
    source: str

    target: str

    mode: str

    distance_km: float

    minimum_minutes: int

    maximum_minutes: int

    bidirectional: bool = True

    border_minutes: int = 0

    source_class: str = "unknown"

    source_refs: tuple[str, ...] = ()

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> route_edge:
        source = str(
            value.get(
                "source",
                "",
            )
        ).strip()

        target = str(
            value.get(
                "target",
                "",
            )
        ).strip()

        mode = str(
            value.get(
                "mode",
                "tour_bus",
            )
        ).strip().lower()

        if (
            not source
            or not target
        ):
            raise oriel_error(
                (
                    "route edge requires "
                    "source and target"
                )
            )

        minimum_minutes = int(
            value[
                "minimum_minutes"
            ]
        )

        maximum_minutes = int(
            value.get(
                "maximum_minutes",
                minimum_minutes,
            )
        )

        if (
            minimum_minutes < 0
            or maximum_minutes
            < minimum_minutes
        ):
            raise oriel_error(
                "invalid route duration envelope"
            )

        source_class = str(
            value.get(
                "source_class",
                "unknown",
            )
        ).strip().lower()

        if source_class not in source_classes:
            raise oriel_error(
                (
                    "unsupported route source class: "
                    + source_class
                )
            )

        return cls(
            source=source,
            target=target,
            mode=mode,
            distance_km=float(
                value.get(
                    "distance_km",
                    0.0,
                )
            ),
            minimum_minutes=
                minimum_minutes,
            maximum_minutes=
                maximum_minutes,
            bidirectional=bool(
                value.get(
                    "bidirectional",
                    True,
                )
            ),
            border_minutes=int(
                value.get(
                    "border_minutes",
                    0,
                )
            ),
            source_class=
                source_class,
            source_refs=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "source_refs",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            metadata=copy.deepcopy(
                value.get(
                    "metadata",
                    {},
                )
            ),
        )


@dataclass(
    frozen=True
)
class event:
    id: str

    kind: str

    entities: tuple[str, ...]

    location_id: str

    start: temporal_window

    end: temporal_window

    duration_minutes: int

    setup_minutes: int = 0

    teardown_minutes: int = 0

    recovery_minutes: int = 0

    resources: tuple[str, ...] = ()

    constraint_class: str = "hard"

    source_class: str = "unknown"

    source_refs: tuple[str, ...] = ()

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        location_timezone:
            str
            | None = None,
    ) -> event:
        identifier = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if not identifier:
            raise oriel_error(
                "event id is required"
            )

        source_class = str(
            value.get(
                "source_class",
                "unknown",
            )
        ).strip().lower()

        if source_class not in source_classes:
            raise oriel_error(
                (
                    "unsupported event source class: "
                    + source_class
                )
            )

        start = temporal_window.from_value(
            value.get(
                "start"
            ),
            default_timezone=
                location_timezone,
            default_source_class=
                source_class,
        )

        duration_value = value.get(
            "duration_minutes"
        )

        if value.get(
            "end"
        ) is not None:
            end = temporal_window.from_value(
                value.get(
                    "end"
                ),
                default_timezone=
                    location_timezone,
                default_source_class=
                    source_class,
            )

            if duration_value is None:
                duration_value = max(
                    0,
                    round(
                        minutes_between(
                            start.earliest,
                            end.earliest,
                        )
                    ),
                )

        else:
            if duration_value is None:
                raise oriel_error(
                    (
                        "event requires end or "
                        "duration_minutes: "
                        + identifier
                    )
                )

            duration = int(
                duration_value
            )

            end = temporal_window(
                earliest=(
                    start.earliest
                    + timedelta(
                        minutes=duration
                    )
                ),
                latest=(
                    start.latest
                    + timedelta(
                        minutes=duration
                    )
                ),
                precision=
                    start.precision,
                source_class=
                    start.source_class,
                source_refs=
                    start.source_refs,
                locked=
                    start.locked,
                transaction_at=
                    start.transaction_at,
            )

        duration_minutes = int(
            duration_value
        )

        if duration_minutes < 0:
            raise oriel_error(
                (
                    "event duration may not "
                    "be negative: "
                    + identifier
                )
            )

        if (
            to_utc(
                end.latest
            )
            < to_utc(
                start.earliest
            )
        ):
            raise oriel_error(
                (
                    "event ends before it starts: "
                    + identifier
                )
            )

        constraint_class = str(
            value.get(
                "constraint_class",
                "hard",
            )
        ).strip().lower()

        if (
            constraint_class
            not in constraint_classes
        ):
            raise oriel_error(
                (
                    "unsupported constraint class: "
                    + constraint_class
                )
            )

        return cls(
            id=identifier,
            kind=str(
                value.get(
                    "kind",
                    "event",
                )
            ).strip().lower(),
            entities=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "entities",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            location_id=str(
                value.get(
                    "location_id",
                    "",
                )
            ).strip(),
            start=start,
            end=end,
            duration_minutes=
                duration_minutes,
            setup_minutes=int(
                value.get(
                    "setup_minutes",
                    0,
                )
            ),
            teardown_minutes=int(
                value.get(
                    "teardown_minutes",
                    0,
                )
            ),
            recovery_minutes=int(
                value.get(
                    "recovery_minutes",
                    0,
                )
            ),
            resources=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "resources",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            constraint_class=
                constraint_class,
            source_class=
                source_class,
            source_refs=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "source_refs",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            metadata=copy.deepcopy(
                value.get(
                    "metadata",
                    {},
                )
            ),
        )

    def midpoint_start(
        self,
    ) -> datetime:
        return self.start.midpoint()

    def midpoint_end(
        self,
    ) -> datetime:
        return self.end.midpoint()

    def possible_start(
        self,
    ) -> datetime:
        return self.start.earliest

    def possible_end(
        self,
    ) -> datetime:
        return self.end.latest

    def certain_start(
        self,
    ) -> datetime:
        return self.start.latest

    def certain_end(
        self,
    ) -> datetime:
        return self.end.earliest

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "id":
                self.id,

            "kind":
                self.kind,

            "entities":
                list(
                    self.entities
                ),

            "location_id":
                self.location_id,

            "start":
                self.start.projection(),

            "end":
                self.end.projection(),

            "duration_minutes":
                self.duration_minutes,

            "setup_minutes":
                self.setup_minutes,

            "teardown_minutes":
                self.teardown_minutes,

            "recovery_minutes":
                self.recovery_minutes,

            "resources":
                list(
                    self.resources
                ),

            "constraint_class":
                self.constraint_class,

            "source_class":
                self.source_class,

            "source_refs":
                list(
                    self.source_refs
                ),

            "metadata":
                copy.deepcopy(
                    dict(
                        self.metadata
                    )
                ),
        }


@dataclass(
    frozen=True
)
class external_constraint:
    id: str

    kind: str

    start: temporal_window

    end: temporal_window

    location_id: str | None = None

    entities: tuple[str, ...] = ()

    resources: tuple[str, ...] = ()

    constraint_class: str = "hard"

    source_class: str = "verified_external"

    source_refs: tuple[str, ...] = ()

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        default_timezone:
            str
            | None = None,
    ) -> external_constraint:
        identifier = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if not identifier:
            raise oriel_error(
                (
                    "external constraint "
                    "id is required"
                )
            )

        source_class = str(
            value.get(
                "source_class",
                "verified_external",
            )
        ).strip().lower()

        if source_class not in source_classes:
            raise oriel_error(
                (
                    "unsupported external "
                    "constraint source class"
                )
            )

        start = temporal_window.from_value(
            value.get(
                "start"
            ),
            default_timezone=
                default_timezone,
            default_source_class=
                source_class,
        )

        end = temporal_window.from_value(
            value.get(
                "end"
            ),
            default_timezone=
                default_timezone,
            default_source_class=
                source_class,
        )

        constraint_class = str(
            value.get(
                "constraint_class",
                "hard",
            )
        ).strip().lower()

        if (
            constraint_class
            not in constraint_classes
        ):
            raise oriel_error(
                (
                    "unsupported external "
                    "constraint class"
                )
            )

        return cls(
            id=identifier,
            kind=str(
                value.get(
                    "kind",
                    "external",
                )
            ).strip().lower(),
            start=start,
            end=end,
            location_id=(
                str(
                    value.get(
                        "location_id"
                    )
                ).strip()
                if value.get(
                    "location_id"
                )
                is not None
                else None
            ),
            entities=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "entities",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            resources=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "resources",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            constraint_class=
                constraint_class,
            source_class=
                source_class,
            source_refs=tuple(
                sorted(
                    {
                        str(
                            item
                        ).strip()
                        for item
                        in value.get(
                            "source_refs",
                            [],
                        )
                        if str(
                            item
                        ).strip()
                    }
                )
            ),
            metadata=copy.deepcopy(
                value.get(
                    "metadata",
                    {},
                )
            ),
        )


def possible_overlap(
    left_start: temporal_window,
    left_end: temporal_window,
    right_start: temporal_window,
    right_end: temporal_window,
) -> bool:
    return not (
        to_utc(
            left_end.latest
        )
        < to_utc(
            right_start.earliest
        )
        or to_utc(
            right_end.latest
        )
        < to_utc(
            left_start.earliest
        )
    )


def forced_overlap(
    left_start: temporal_window,
    left_end: temporal_window,
    right_start: temporal_window,
    right_end: temporal_window,
) -> bool:
    return (
        to_utc(
            left_start.latest
        )
        < to_utc(
            right_end.earliest
        )
        and to_utc(
            right_start.latest
        )
        < to_utc(
            left_end.earliest
        )
    )


def overlap_bounds(
    left_start: temporal_window,
    left_end: temporal_window,
    right_start: temporal_window,
    right_end: temporal_window,
) -> tuple[
    datetime,
    datetime,
] | None:
    start = max(
        to_utc(
            left_start.earliest
        ),
        to_utc(
            right_start.earliest
        ),
    )

    end = min(
        to_utc(
            left_end.latest
        ),
        to_utc(
            right_end.latest
        ),
    )

    if end < start:
        return None

    return (
        start,
        end,
    )


class oriel_engine:
    def __init__(
        self,
    ) -> None:
        self.locations: dict[
            str,
            location,
        ] = {}

        self.events: dict[
            str,
            event,
        ] = {}

        self.routes: list[
            route_edge
        ] = []

        self.constraints: dict[
            str,
            external_constraint,
        ] = {}

        self.transport_profiles: dict[
            str,
            transport_profile,
        ] = {}

        for identifier, values in (
            transport_defaults.items()
        ):
            self.transport_profiles[
                identifier
            ] = transport_profile(
                id=identifier,
                **values,
            )

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
    ) -> oriel_engine:
        engine = cls()

        for value in document.get(
            "transport_profiles",
            [],
        ):
            profile = (
                transport_profile
                .from_mapping(
                    value
                )
            )

            engine.transport_profiles[
                profile.id
            ] = profile

        for value in document.get(
            "locations",
            [],
        ):
            item = location.from_mapping(
                value
            )

            engine.locations[
                item.id
            ] = item

        for value in document.get(
            "routes",
            [],
        ):
            engine.routes.append(
                route_edge.from_mapping(
                    value
                )
            )

        for value in document.get(
            "events",
            [],
        ):
            location_id = str(
                value.get(
                    "location_id",
                    "",
                )
            ).strip()

            location_value = (
                engine.locations.get(
                    location_id
                )
            )

            timezone_name = (
                location_value.timezone_name
                if location_value
                is not None
                else None
            )

            item = event.from_mapping(
                value,
                location_timezone=
                    timezone_name,
            )

            if (
                item.location_id
                and item.location_id
                not in engine.locations
            ):
                raise oriel_error(
                    (
                        "event references unknown "
                        "location: "
                        + item.id
                        + " -> "
                        + item.location_id
                    )
                )

            engine.events[
                item.id
            ] = item

        for value in document.get(
            "external_constraints",
            [],
        ):
            location_id = value.get(
                "location_id"
            )

            timezone_name = None

            if (
                location_id is not None
                and str(
                    location_id
                )
                in engine.locations
            ):
                timezone_name = (
                    engine.locations[
                        str(
                            location_id
                        )
                    ].timezone_name
                )

            item = (
                external_constraint
                .from_mapping(
                    value,
                    default_timezone=
                        timezone_name,
                )
            )

            engine.constraints[
                item.id
            ] = item

        return engine

    def _profile(
        self,
        mode: str,
    ) -> transport_profile:
        identifier = str(
            mode
        ).strip().lower()

        if identifier not in self.transport_profiles:
            raise oriel_error(
                (
                    "unknown transport mode: "
                    + identifier
                )
            )

        return self.transport_profiles[
            identifier
        ]

    def _adjacency(
        self,
        mode: str,
    ) -> dict[
        str,
        list[
            tuple[
                str,
                route_edge,
            ]
        ],
    ]:
        adjacency: dict[
            str,
            list[
                tuple[
                    str,
                    route_edge,
                ]
            ],
        ] = {}

        for edge in self.routes:
            if edge.mode != mode:
                continue

            adjacency.setdefault(
                edge.source,
                [],
            ).append(
                (
                    edge.target,
                    edge,
                )
            )

            if edge.bidirectional:
                adjacency.setdefault(
                    edge.target,
                    [],
                ).append(
                    (
                        edge.source,
                        edge,
                    )
                )

        return adjacency

    def _networkx_graph(
        self,
        mode: str,
    ) -> Any:
        if nx is None:
            return None

        graph = nx.DiGraph()

        for edge in self.routes:
            if edge.mode != mode:
                continue

            graph.add_edge(
                edge.source,
                edge.target,
                edge=edge,
                weight=(
                    edge.minimum_minutes
                    + edge.border_minutes
                ),
            )

            if edge.bidirectional:
                graph.add_edge(
                    edge.target,
                    edge.source,
                    edge=edge,
                    weight=(
                        edge.minimum_minutes
                        + edge.border_minutes
                    ),
                )

        return graph

    def _stdlib_shortest_path(
        self,
        source: str,
        target: str,
        mode: str,
    ) -> list[str] | None:
        adjacency = self._adjacency(
            mode
        )

        queue = [
            (
                0,
                source,
                [
                    source
                ],
            )
        ]

        best = {
            source:
                0
        }

        while queue:
            cost, node, path = (
                heapq.heappop(
                    queue
                )
            )

            if node == target:
                return path

            if cost > best.get(
                node,
                float(
                    "inf"
                ),
            ):
                continue

            for neighbor, edge in adjacency.get(
                node,
                [],
            ):
                next_cost = (
                    cost
                    + edge.minimum_minutes
                    + edge.border_minutes
                )

                if next_cost >= best.get(
                    neighbor,
                    float(
                        "inf"
                    ),
                ):
                    continue

                best[
                    neighbor
                ] = next_cost

                heapq.heappush(
                    queue,
                    (
                        next_cost,
                        neighbor,
                        [
                            *path,
                            neighbor,
                        ],
                    ),
                )

        return None

    def _explicit_path(
        self,
        source: str,
        target: str,
        mode: str,
    ) -> list[str] | None:
        graph = self._networkx_graph(
            mode
        )

        if graph is not None:
            try:
                return list(
                    nx.shortest_path(
                        graph,
                        source=source,
                        target=target,
                        weight="weight",
                    )
                )

            except (
                nx.NetworkXNoPath,
                nx.NodeNotFound,
            ):
                pass

        return self._stdlib_shortest_path(
            source,
            target,
            mode,
        )

    def _edge_for(
        self,
        source: str,
        target: str,
        mode: str,
    ) -> route_edge | None:
        for edge in self.routes:
            if edge.mode != mode:
                continue

            if (
                edge.source == source
                and edge.target == target
            ):
                return edge

            if (
                edge.bidirectional
                and edge.source == target
                and edge.target == source
            ):
                return edge

        return None

    def travel(
        self,
        source: str,
        target: str,
        *,
        mode: str = "tour_bus",
        allow_estimate: bool = True,
    ) -> dict[str, Any]:
        if source == target:
            return {
                "schema":
                    "savant.carbon.oriel.travel.v1",

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "outcome":
                    "pass",

                "source":
                    source,

                "target":
                    target,

                "mode":
                    mode,

                "path": [
                    source
                ],

                "distance_km":
                    0.0,

                "minimum_minutes":
                    0,

                "maximum_minutes":
                    0,

                "source_class":
                    "derived",

                "estimated":
                    False,

                "source_refs": [],
            }

        if (
            source not in self.locations
            or target not in self.locations
        ):
            return {
                "schema":
                    "savant.carbon.oriel.travel.v1",

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "outcome":
                    "unknown",

                "reason":
                    "route endpoint location is unknown",

                "source":
                    source,

                "target":
                    target,

                "mode":
                    mode,
            }

        path = self._explicit_path(
            source,
            target,
            mode,
        )

        if path:
            distance = 0.0
            minimum = 0
            maximum = 0
            source_refs = set()
            source_values = set()
            edges = []

            for left, right in zip(
                path,
                path[
                    1:
                ],
            ):
                edge = self._edge_for(
                    left,
                    right,
                    mode,
                )

                if edge is None:
                    raise oriel_error(
                        (
                            "resolved route lacks "
                            "edge material"
                        )
                    )

                distance += edge.distance_km

                minimum += (
                    edge.minimum_minutes
                    + edge.border_minutes
                )

                maximum += (
                    edge.maximum_minutes
                    + edge.border_minutes
                )

                source_refs.update(
                    edge.source_refs
                )

                source_values.add(
                    edge.source_class
                )

                edges.append(
                    {
                        "source":
                            left,

                        "target":
                            right,

                        "minimum_minutes":
                            edge.minimum_minutes,

                        "maximum_minutes":
                            edge.maximum_minutes,

                        "border_minutes":
                            edge.border_minutes,

                        "distance_km":
                            edge.distance_km,

                        "source_class":
                            edge.source_class,

                        "source_refs":
                            list(
                                edge.source_refs
                            ),
                    }
                )

            source_class = (
                next(
                    iter(
                        source_values
                    )
                )
                if len(
                    source_values
                )
                == 1
                else "derived"
            )

            return {
                "schema":
                    "savant.carbon.oriel.travel.v1",

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "outcome":
                    "pass",

                "source":
                    source,

                "target":
                    target,

                "mode":
                    mode,

                "path":
                    path,

                "edges":
                    edges,

                "distance_km":
                    round(
                        distance,
                        3,
                    ),

                "minimum_minutes":
                    minimum,

                "maximum_minutes":
                    maximum,

                "source_class":
                    source_class,

                "source_refs":
                    sorted(
                        source_refs
                    ),

                "estimated":
                    False,

                "graph_backend":
                    (
                        "networkx"
                        if nx is not None
                        else "stdlib"
                    ),
            }

        if not allow_estimate:
            return {
                "schema":
                    "savant.carbon.oriel.travel.v1",

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "outcome":
                    "unknown",

                "reason":
                    (
                        "no explicit route exists "
                        "and estimation is disabled"
                    ),

                "source":
                    source,

                "target":
                    target,

                "mode":
                    mode,
            }

        profile = self._profile(
            mode
        )

        left = self.locations[
            source
        ]

        right = self.locations[
            target
        ]

        great_circle = haversine_km(
            left.latitude,
            left.longitude,
            right.latitude,
            right.longitude,
        )

        effective_distance = (
            great_circle
            * profile.distance_factor
        )

        minimum_minutes = math.ceil(
            (
                effective_distance
                / profile.maximum_speed_kph
            )
            * 60
            + profile.fixed_minutes
        )

        maximum_minutes = math.ceil(
            (
                effective_distance
                / profile.minimum_speed_kph
            )
            * 60
            + profile.fixed_minutes
        )

        return {
            "schema":
                "savant.carbon.oriel.travel.v1",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "outcome":
                "advisory",

            "source":
                source,

            "target":
                target,

            "mode":
                mode,

            "path": [
                source,
                target,
            ],

            "great_circle_km":
                round(
                    great_circle,
                    3,
                ),

            "distance_km":
                round(
                    effective_distance,
                    3,
                ),

            "minimum_minutes":
                minimum_minutes,

            "maximum_minutes":
                maximum_minutes,

            "source_class":
                "estimate",

            "source_refs": [],

            "estimated":
                True,

            "reason":
                (
                    "travel envelope derived from "
                    "coordinates and transport profile"
                ),
        }

    def route_alternatives(
        self,
        source: str,
        target: str,
        *,
        mode: str = "tour_bus",
        limit: int = 3,
    ) -> dict[str, Any]:
        graph = self._networkx_graph(
            mode
        )

        if graph is None:
            primary = self.travel(
                source,
                target,
                mode=mode,
                allow_estimate=False,
            )

            return {
                "schema":
                    (
                        "savant.carbon.oriel."
                        "route-alternatives.v1"
                    ),

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "backend":
                    "stdlib",

                "alternatives":
                    (
                        [
                            primary
                        ]
                        if primary[
                            "outcome"
                        ]
                        != "unknown"
                        else []
                    ),
            }

        try:
            paths = []

            generator = (
                nx.shortest_simple_paths(
                    graph,
                    source,
                    target,
                    weight="weight",
                )
            )

            for path in generator:
                paths.append(
                    list(
                        path
                    )
                )

                if len(
                    paths
                ) >= max(
                    1,
                    limit,
                ):
                    break

        except (
            nx.NetworkXNoPath,
            nx.NodeNotFound,
        ):
            paths = []

        alternatives = []

        for path in paths:
            distance = 0.0
            minimum = 0
            maximum = 0

            for left, right in zip(
                path,
                path[
                    1:
                ],
            ):
                edge = self._edge_for(
                    left,
                    right,
                    mode,
                )

                if edge is None:
                    continue

                distance += edge.distance_km

                minimum += (
                    edge.minimum_minutes
                    + edge.border_minutes
                )

                maximum += (
                    edge.maximum_minutes
                    + edge.border_minutes
                )

            alternatives.append(
                {
                    "path":
                        path,

                    "distance_km":
                        round(
                            distance,
                            3,
                        ),

                    "minimum_minutes":
                        minimum,

                    "maximum_minutes":
                        maximum,
                }
            )

        return {
            "schema":
                (
                    "savant.carbon.oriel."
                    "route-alternatives.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "backend":
                "networkx",

            "alternatives":
                alternatives,
        }

    def _events_for_entity(
        self,
        entity_id: str,
    ) -> list[event]:
        return sorted(
            [
                item
                for item
                in self.events.values()
                if entity_id
                in item.entities
            ],
            key=lambda item: (
                to_utc(
                    item.start.earliest
                ),
                item.id,
            ),
        )

    def _shared_resources(
        self,
        left: event,
        right: event,
    ) -> list[str]:
        return sorted(
            set(
                left.resources
            )
            & set(
                right.resources
            )
        )

    def _conflict(
        self,
        *,
        check_id: str,
        outcome: str,
        message: str,
        severity: str,
        evidence: Mapping[str, Any],
        reason_code: str,
    ) -> dict[str, Any]:
        if outcome not in outcomes:
            raise oriel_error(
                (
                    "unknown Oriel outcome: "
                    + outcome
                )
            )

        return {
            "check":
                check_id,

            "outcome":
                outcome,

            "severity":
                severity,

            "message":
                message,

            "reason_code":
                reason_code,

            "evidence":
                copy.deepcopy(
                    dict(
                        evidence
                    )
                ),

            "authority_effect":
                "none",
        }

    def _pair_feasibility(
        self,
        previous: event,
        current: event,
        *,
        entity_id: str,
        mode: str,
    ) -> list[dict[str, Any]]:
        checks = []

        maximum_available = (
            minutes_between(
                previous.end.earliest,
                current.start.latest,
            )
        )

        minimum_available = (
            minutes_between(
                previous.end.latest,
                current.start.earliest,
            )
        )

        if maximum_available < 0:
            checks.append(
                self._conflict(
                    check_id=
                        "forced-temporal-overlap",
                    outcome="fail",
                    severity="error",
                    message=(
                        "event windows force an "
                        "entity to overlap itself"
                    ),
                    reason_code=
                        "oriel.entity.forced_overlap",
                    evidence={
                        "entity":
                            entity_id,

                        "previous":
                            previous.id,

                        "current":
                            current.id,

                        "maximum_available_minutes":
                            maximum_available,
                    },
                )
            )

            return checks

        travel = self.travel(
            previous.location_id,
            current.location_id,
            mode=mode,
        )

        if travel[
            "outcome"
        ] == "unknown":
            checks.append(
                self._conflict(
                    check_id=
                        "travel-unresolved",
                    outcome="unknown",
                    severity="warning",
                    message=(
                        "travel feasibility cannot "
                        "be established"
                    ),
                    reason_code=
                        "oriel.travel.unresolved",
                    evidence={
                        "entity":
                            entity_id,

                        "previous":
                            previous.id,

                        "current":
                            current.id,

                        "travel":
                            travel,
                    },
                )
            )

            return checks

        profile = self._profile(
            mode
        )

        minimum_required = (
            previous.teardown_minutes
            + int(
                travel[
                    "minimum_minutes"
                ]
            )
            + current.setup_minutes
            + max(
                previous.recovery_minutes,
                profile.minimum_recovery_minutes,
            )
        )

        maximum_required = (
            previous.teardown_minutes
            + int(
                travel[
                    "maximum_minutes"
                ]
            )
            + current.setup_minutes
            + max(
                previous.recovery_minutes,
                profile.minimum_recovery_minutes,
            )
        )

        if maximum_available <= 0:
            pressure = float(
                "inf"
            )

        else:
            pressure = (
                minimum_required
                / maximum_available
            )

        evidence = {
            "entity":
                entity_id,

            "previous":
                previous.id,

            "current":
                current.id,

            "minimum_available_minutes":
                round(
                    minimum_available,
                    3,
                ),

            "maximum_available_minutes":
                round(
                    maximum_available,
                    3,
                ),

            "minimum_required_minutes":
                minimum_required,

            "maximum_required_minutes":
                maximum_required,

            "minimum_slack_minutes":
                round(
                    maximum_available
                    - minimum_required,
                    3,
                ),

            "pressure":
                (
                    None
                    if math.isinf(
                        pressure
                    )
                    else round(
                        pressure,
                        5,
                    )
                ),

            "travel":
                travel,
        }

        if (
            minimum_required
            > maximum_available
        ):
            checks.append(
                self._conflict(
                    check_id=
                        "travel-feasibility",
                    outcome="fail",
                    severity="error",
                    message=(
                        "even the fastest supported "
                        "travel plan cannot connect "
                        "the events"
                    ),
                    reason_code=
                        "oriel.travel.impossible",
                    evidence=evidence,
                )
            )

        elif (
            maximum_required
            > minimum_available
        ):
            checks.append(
                self._conflict(
                    check_id=
                        "travel-feasibility",
                    outcome="advisory",
                    severity="warning",
                    message=(
                        "the events are feasible only "
                        "within a constrained portion "
                        "of their uncertainty windows"
                    ),
                    reason_code=
                        "oriel.travel.conditional",
                    evidence=evidence,
                )
            )

        else:
            checks.append(
                self._conflict(
                    check_id=
                        "travel-feasibility",
                    outcome="pass",
                    severity="info",
                    message=(
                        "travel, setup, teardown and "
                        "recovery fit between events"
                    ),
                    reason_code=
                        "oriel.travel.feasible",
                    evidence=evidence,
                )
            )

        return checks

    def validate(
        self,
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        checks = []

        entity_ids = sorted(
            {
                entity_id
                for item
                in self.events.values()
                for entity_id
                in item.entities
            }
        )

        for entity_id in entity_ids:
            values = self._events_for_entity(
                entity_id
            )

            for previous, current in zip(
                values,
                values[
                    1:
                ],
            ):
                checks.extend(
                    self._pair_feasibility(
                        previous,
                        current,
                        entity_id=
                            entity_id,
                        mode=mode,
                    )
                )

        values = sorted(
            self.events.values(),
            key=lambda item:
                item.id,
        )

        for index, left in enumerate(
            values
        ):
            for right in values[
                index
                + 1:
            ]:
                if not possible_overlap(
                    left.start,
                    left.end,
                    right.start,
                    right.end,
                ):
                    continue

                shared_entities = sorted(
                    set(
                        left.entities
                    )
                    & set(
                        right.entities
                    )
                )

                shared_resources = (
                    self._shared_resources(
                        left,
                        right,
                    )
                )

                same_exclusive_venue = bool(
                    left.location_id
                    and left.location_id
                    == right.location_id
                    and (
                        left.metadata.get(
                            "exclusive_venue",
                            False,
                        )
                        or right.metadata.get(
                            "exclusive_venue",
                            False,
                        )
                    )
                )

                if not (
                    shared_entities
                    or shared_resources
                    or same_exclusive_venue
                ):
                    continue

                forced = forced_overlap(
                    left.start,
                    left.end,
                    right.start,
                    right.end,
                )

                checks.append(
                    self._conflict(
                        check_id=
                            "occupancy-conflict",
                        outcome=(
                            "fail"
                            if forced
                            else "advisory"
                        ),
                        severity=(
                            "error"
                            if forced
                            else "warning"
                        ),
                        message=(
                            "occupancy collision is forced"
                            if forced
                            else (
                                "occupancy collision is "
                                "possible inside uncertainty "
                                "windows"
                            )
                        ),
                        reason_code=(
                            "oriel.occupancy.forced"
                            if forced
                            else "oriel.occupancy.possible"
                        ),
                        evidence={
                            "left":
                                left.id,

                            "right":
                                right.id,

                            "shared_entities":
                                shared_entities,

                            "shared_resources":
                                shared_resources,

                            "same_exclusive_venue":
                                same_exclusive_venue,
                        },
                    )
                )

        for item in self.events.values():
            for constraint in (
                self.constraints.values()
            ):
                if (
                    constraint.location_id
                    is not None
                    and constraint.location_id
                    != item.location_id
                ):
                    continue

                if (
                    constraint.entities
                    and not (
                        set(
                            constraint.entities
                        )
                        & set(
                            item.entities
                        )
                    )
                ):
                    continue

                if (
                    constraint.resources
                    and not (
                        set(
                            constraint.resources
                        )
                        & set(
                            item.resources
                        )
                    )
                ):
                    continue

                if not possible_overlap(
                    item.start,
                    item.end,
                    constraint.start,
                    constraint.end,
                ):
                    continue

                forced = forced_overlap(
                    item.start,
                    item.end,
                    constraint.start,
                    constraint.end,
                )

                hard = (
                    constraint.constraint_class
                    == "hard"
                )

                if hard and forced:
                    outcome = "fail"
                    severity = "error"

                elif hard:
                    outcome = "advisory"
                    severity = "warning"

                else:
                    outcome = "advisory"
                    severity = "info"

                checks.append(
                    self._conflict(
                        check_id=
                            "external-constraint",
                        outcome=outcome,
                        severity=severity,
                        message=(
                            "event intersects a "
                            "real-world or externally "
                            "sourced constraint"
                        ),
                        reason_code=(
                            "oriel.external."
                            + constraint.kind
                        ),
                        evidence={
                            "event":
                                item.id,

                            "constraint":
                                constraint.id,

                            "constraint_kind":
                                constraint.kind,

                            "constraint_class":
                                constraint.constraint_class,

                            "forced_overlap":
                                forced,

                            "source_class":
                                constraint.source_class,

                            "source_refs":
                                list(
                                    constraint.source_refs
                                ),
                        },
                    )
                )

        failure_count = sum(
            1
            for item
            in checks
            if item[
                "outcome"
            ]
            == "fail"
        )

        unknown_count = sum(
            1
            for item
            in checks
            if item[
                "outcome"
            ]
            == "unknown"
        )

        advisory_count = sum(
            1
            for item
            in checks
            if item[
                "outcome"
            ]
            == "advisory"
        )

        if failure_count:
            overall = "fail"

        elif unknown_count:
            overall = "unknown"

        elif advisory_count:
            overall = "advisory"

        else:
            overall = "pass"

        projection = {
            "schema":
                (
                    "savant.carbon.oriel."
                    "validation.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "outcome":
                overall,

            "valid":
                failure_count == 0,

            "fully_resolved":
                unknown_count == 0,

            "failure_count":
                failure_count,

            "unknown_count":
                unknown_count,

            "advisory_count":
                advisory_count,

            "check_count":
                len(
                    checks
                ),

            "checks":
                checks,

            "source_state_mutated":
                False,

            "simulation_output_is_authority":
                False,
        }

        projection[
            "itinerary_digest"
        ] = digest(
            {
                "locations": [
                    self.locations[
                        key
                    ].projection()
                    for key
                    in sorted(
                        self.locations
                    )
                ],

                "events": [
                    self.events[
                        key
                    ].projection()
                    for key
                    in sorted(
                        self.events
                    )
                ],

                "routes": [
                    {
                        "source":
                            edge.source,

                        "target":
                            edge.target,

                        "mode":
                            edge.mode,

                        "distance_km":
                            edge.distance_km,

                        "minimum_minutes":
                            edge.minimum_minutes,

                        "maximum_minutes":
                            edge.maximum_minutes,

                        "border_minutes":
                            edge.border_minutes,

                        "source_class":
                            edge.source_class,

                        "source_refs":
                            list(
                                edge.source_refs
                            ),
                    }
                    for edge
                    in sorted(
                        self.routes,
                        key=lambda value: (
                            value.source,
                            value.target,
                            value.mode,
                        ),
                    )
                ],
            }
        )

        return projection

    def position_at(
        self,
        entity_id: str,
        timestamp: Any,
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        at = to_utc(
            parse_datetime(
                timestamp
            )
        )

        values = self._events_for_entity(
            entity_id
        )

        for item in values:
            certain_start = to_utc(
                item.certain_start()
            )

            certain_end = to_utc(
                item.certain_end()
            )

            if (
                certain_end
                >= certain_start
                and certain_start
                <= at
                <= certain_end
            ):
                place = self.locations[
                    item.location_id
                ]

                return {
                    "schema":
                        (
                            "savant.carbon.oriel."
                            "position.v1"
                        ),

                    "owner":
                        owner,

                    "component":
                        component,

                    "authority_effect":
                        authority_effect,

                    "entity":
                        entity_id,

                    "timestamp":
                        at.isoformat(),

                    "state":
                        "stationary",

                    "certainty":
                        "certain-within-event-window",

                    "event":
                        item.id,

                    "location":
                        place.projection(),

                    "source_class":
                        item.source_class,

                    "source_refs":
                        list(
                            item.source_refs
                        ),
                }

        for item in values:
            if (
                to_utc(
                    item.possible_start()
                )
                <= at
                <= to_utc(
                    item.possible_end()
                )
            ):
                place = self.locations[
                    item.location_id
                ]

                return {
                    "schema":
                        (
                            "savant.carbon.oriel."
                            "position.v1"
                        ),

                    "owner":
                        owner,

                    "component":
                        component,

                    "authority_effect":
                        authority_effect,

                    "entity":
                        entity_id,

                    "timestamp":
                        at.isoformat(),

                    "state":
                        "event-envelope",

                    "certainty":
                        "possible",

                    "event":
                        item.id,

                    "location":
                        place.projection(),

                    "source_class":
                        item.source_class,

                    "source_refs":
                        list(
                            item.source_refs
                        ),
                }

        previous = None
        upcoming = None

        for item in values:
            if (
                to_utc(
                    item.end.midpoint()
                )
                <= at
            ):
                previous = item

            elif (
                to_utc(
                    item.start.midpoint()
                )
                > at
            ):
                upcoming = item

                break

        if (
            previous is None
            or upcoming is None
        ):
            return {
                "schema":
                    (
                        "savant.carbon.oriel."
                        "position.v1"
                    ),

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "entity":
                    entity_id,

                "timestamp":
                    at.isoformat(),

                "state":
                    "unknown",

                "certainty":
                    "unknown",

                "reason":
                    (
                        "timestamp is outside "
                        "bounded entity chronology"
                    ),
            }

        travel = self.travel(
            previous.location_id,
            upcoming.location_id,
            mode=mode,
        )

        if travel[
            "outcome"
        ] == "unknown":
            return {
                "schema":
                    (
                        "savant.carbon.oriel."
                        "position.v1"
                    ),

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "entity":
                    entity_id,

                "timestamp":
                    at.isoformat(),

                "state":
                    "travel-unresolved",

                "certainty":
                    "unknown",

                "previous_event":
                    previous.id,

                "next_event":
                    upcoming.id,

                "travel":
                    travel,
            }

        departure = to_utc(
            previous.end.midpoint()
        )

        arrival = to_utc(
            upcoming.start.midpoint()
        )

        total_seconds = (
            arrival
            - departure
        ).total_seconds()

        if total_seconds <= 0:
            fraction = 0.5

        else:
            fraction = clamp(
                (
                    (
                        at
                        - departure
                    ).total_seconds()
                    / total_seconds
                ),
                0.0,
                1.0,
            )

        path = travel.get(
            "path",
            [
                previous.location_id,
                upcoming.location_id,
            ],
        )

        position = self._interpolate_path(
            path,
            fraction,
        )

        return {
            "schema":
                (
                    "savant.carbon.oriel."
                    "position.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "entity":
                entity_id,

            "timestamp":
                at.isoformat(),

            "state":
                "travel",

            "certainty":
                (
                    "derived"
                    if not travel.get(
                        "estimated"
                    )
                    else "estimated"
                ),

            "previous_event":
                previous.id,

            "next_event":
                upcoming.id,

            "progress":
                round(
                    fraction,
                    6,
                ),

            "position":
                position,

            "route":
                travel,

            "source_class":
                travel.get(
                    "source_class"
                ),
        }

    def _interpolate_path(
        self,
        path: Sequence[str],
        fraction: float,
    ) -> dict[str, Any]:
        points = [
            self.locations[
                identifier
            ]
            for identifier
            in path
            if identifier
            in self.locations
        ]

        if not points:
            return {
                "latitude":
                    None,

                "longitude":
                    None,
            }

        if len(
            points
        ) == 1:
            return {
                "latitude":
                    points[
                        0
                    ].latitude,

                "longitude":
                    points[
                        0
                    ].longitude,

                "near_location":
                    points[
                        0
                    ].id,
            }

        segments = []

        total_distance = 0.0

        for left, right in zip(
            points,
            points[
                1:
            ],
        ):
            distance = haversine_km(
                left.latitude,
                left.longitude,
                right.latitude,
                right.longitude,
            )

            segments.append(
                (
                    left,
                    right,
                    distance,
                )
            )

            total_distance += distance

        if total_distance <= 0:
            return {
                "latitude":
                    points[
                        0
                    ].latitude,

                "longitude":
                    points[
                        0
                    ].longitude,

                "near_location":
                    points[
                        0
                    ].id,
            }

        target_distance = (
            total_distance
            * clamp(
                fraction,
                0.0,
                1.0,
            )
        )

        traversed = 0.0

        for left, right, distance in segments:
            if (
                traversed
                + distance
                >= target_distance
            ):
                local = (
                    0.0
                    if distance == 0
                    else (
                        target_distance
                        - traversed
                    )
                    / distance
                )

                latitude = (
                    left.latitude
                    + (
                        right.latitude
                        - left.latitude
                    )
                    * local
                )

                longitude = (
                    left.longitude
                    + (
                        right.longitude
                        - left.longitude
                    )
                    * local
                )

                return {
                    "latitude":
                        round(
                            latitude,
                            7,
                        ),

                    "longitude":
                        round(
                            longitude,
                            7,
                        ),

                    "segment": {
                        "source":
                            left.id,

                        "target":
                            right.id,

                        "progress":
                            round(
                                local,
                                6,
                            ),
                    },
                }

            traversed += distance

        last = points[
            -1
        ]

        return {
            "latitude":
                last.latitude,

            "longitude":
                last.longitude,

            "near_location":
                last.id,
        }

    def encounter_windows(
        self,
        left_entity: str,
        right_entity: str,
        *,
        radius_km: float = 1.0,
    ) -> dict[str, Any]:
        left_events = self._events_for_entity(
            left_entity
        )

        right_events = self._events_for_entity(
            right_entity
        )

        matches = []

        for left in left_events:
            for right in right_events:
                bounds = overlap_bounds(
                    left.start,
                    left.end,
                    right.start,
                    right.end,
                )

                if bounds is None:
                    continue

                left_location = self.locations[
                    left.location_id
                ]

                right_location = self.locations[
                    right.location_id
                ]

                distance = haversine_km(
                    left_location.latitude,
                    left_location.longitude,
                    right_location.latitude,
                    right_location.longitude,
                )

                if distance > radius_km:
                    continue

                matches.append(
                    {
                        "left_event":
                            left.id,

                        "right_event":
                            right.id,

                        "left_location":
                            left.location_id,

                        "right_location":
                            right.location_id,

                        "distance_km":
                            round(
                                distance,
                                4,
                            ),

                        "window": {
                            "earliest":
                                bounds[
                                    0
                                ].isoformat(),

                            "latest":
                                bounds[
                                    1
                                ].isoformat(),
                        },

                        "historically_possible":
                            True,

                        "interaction_is_fact":
                            False,
                    }
                )

        return {
            "schema":
                (
                    "savant.carbon.oriel."
                    "encounter-windows.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "left_entity":
                left_entity,

            "right_entity":
                right_entity,

            "radius_km":
                radius_km,

            "match_count":
                len(
                    matches
                ),

            "matches":
                matches,
        }

    def candidate_windows(
        self,
        *,
        entity_id: str,
        location_id: str,
        duration_minutes: int,
        range_start: Any,
        range_end: Any,
        mode: str = "tour_bus",
        setup_minutes: int = 0,
        teardown_minutes: int = 0,
        recovery_minutes: int = 0,
    ) -> dict[str, Any]:
        if location_id not in self.locations:
            raise oriel_error(
                (
                    "unknown candidate location: "
                    + location_id
                )
            )

        start = to_utc(
            parse_datetime(
                range_start
            )
        )

        end = to_utc(
            parse_datetime(
                range_end
            )
        )

        if end <= start:
            raise oriel_error(
                (
                    "candidate range end must "
                    "follow range start"
                )
            )

        values = [
            item
            for item
            in self._events_for_entity(
                entity_id
            )
            if (
                to_utc(
                    item.end.latest
                )
                >= start
                and to_utc(
                    item.start.earliest
                )
                <= end
            )
        ]

        boundaries = [
            None,
            *values,
            None,
        ]

        windows = []

        unknown_gaps = []

        for previous, upcoming in zip(
            boundaries,
            boundaries[
                1:
            ],
        ):
            left_boundary = (
                start
                if previous is None
                else max(
                    start,
                    to_utc(
                        previous.end.latest
                    ),
                )
            )

            right_boundary = (
                end
                if upcoming is None
                else min(
                    end,
                    to_utc(
                        upcoming.start.earliest
                    ),
                )
            )

            earliest = left_boundary

            latest_end = right_boundary

            evidence = {}

            if previous is not None:
                travel_in = self.travel(
                    previous.location_id,
                    location_id,
                    mode=mode,
                )

                evidence[
                    "travel_in"
                ] = travel_in

                if (
                    travel_in[
                        "outcome"
                    ]
                    == "unknown"
                ):
                    unknown_gaps.append(
                        {
                            "previous":
                                previous.id,

                            "upcoming":
                                (
                                    upcoming.id
                                    if upcoming
                                    else None
                                ),

                            "reason":
                                "inbound travel unresolved",
                        }
                    )

                    continue

                earliest += timedelta(
                    minutes=(
                        previous.teardown_minutes
                        + int(
                            travel_in[
                                "maximum_minutes"
                            ]
                        )
                        + max(
                            previous.recovery_minutes,
                            recovery_minutes,
                        )
                        + setup_minutes
                    )
                )

            if upcoming is not None:
                travel_out = self.travel(
                    location_id,
                    upcoming.location_id,
                    mode=mode,
                )

                evidence[
                    "travel_out"
                ] = travel_out

                if (
                    travel_out[
                        "outcome"
                    ]
                    == "unknown"
                ):
                    unknown_gaps.append(
                        {
                            "previous":
                                (
                                    previous.id
                                    if previous
                                    else None
                                ),

                            "upcoming":
                                upcoming.id,

                            "reason":
                                "outbound travel unresolved",
                        }
                    )

                    continue

                latest_start = (
                    latest_end
                    - timedelta(
                        minutes=(
                            duration_minutes
                            + teardown_minutes
                            + int(
                                travel_out[
                                    "maximum_minutes"
                                ]
                            )
                            + upcoming.setup_minutes
                        )
                    )
                )

            else:
                latest_start = (
                    latest_end
                    - timedelta(
                        minutes=(
                            duration_minutes
                            + teardown_minutes
                        )
                    )
                )

            if latest_start < earliest:
                continue

            windows.append(
                {
                    "earliest_start":
                        earliest.isoformat(),

                    "latest_start":
                        latest_start.isoformat(),

                    "duration_minutes":
                        duration_minutes,

                    "slack_minutes":
                        round(
                            minutes_between(
                                earliest,
                                latest_start,
                            ),
                            3,
                        ),

                    "previous_event":
                        (
                            previous.id
                            if previous
                            else None
                        ),

                    "next_event":
                        (
                            upcoming.id
                            if upcoming
                            else None
                        ),

                    "evidence":
                        evidence,
                }
            )

        return {
            "schema":
                (
                    "savant.carbon.oriel."
                    "candidate-windows.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "entity":
                entity_id,

            "location_id":
                location_id,

            "window_count":
                len(
                    windows
                ),

            "windows":
                windows,

            "unresolved_gaps":
                unknown_gaps,

            "source_state_mutated":
                False,
        }

    def solve_schedule(
        self,
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        if cp_model is None:
            return {
                "schema":
                    (
                        "savant.carbon.oriel."
                        "schedule-solver.v1"
                    ),

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "backend":
                    "deterministic-validation",

                "ortools_available":
                    False,

                "outcome":
                    self.validate(
                        mode=mode
                    )[
                        "outcome"
                    ],

                "reason":
                    (
                        "OR-Tools is not available; "
                        "Oriel retained deterministic "
                        "constraint validation without "
                        "inventing an optimized schedule"
                    ),
            }

        values = sorted(
            self.events.values(),
            key=lambda item: (
                to_utc(
                    item.start.earliest
                ),
                item.id,
            ),
        )

        if not values:
            return {
                "schema":
                    (
                        "savant.carbon.oriel."
                        "schedule-solver.v1"
                    ),

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "backend":
                    "ortools-cp-sat",

                "ortools_available":
                    True,

                "outcome":
                    "pass",

                "schedule": [],
            }

        base = min(
            to_utc(
                item.start.earliest
            )
            for item
            in values
        )

        def minute_index(
            value: datetime,
        ) -> int:
            return int(
                round(
                    minutes_between(
                        base,
                        to_utc(
                            value
                        ),
                    )
                )
            )

        model = cp_model.CpModel()

        starts = {}

        intervals = {}

        for item in values:
            lower = minute_index(
                item.start.earliest
            )

            upper = minute_index(
                item.start.latest
            )

            variable = model.NewIntVar(
                lower,
                upper,
                (
                    "start_"
                    + item.id
                ),
            )

            starts[
                item.id
            ] = variable

            occupied_duration = (
                item.setup_minutes
                + item.duration_minutes
                + item.teardown_minutes
            )

            interval = model.NewIntervalVar(
                variable,
                occupied_duration,
                variable
                + occupied_duration,
                (
                    "interval_"
                    + item.id
                ),
            )

            intervals[
                item.id
            ] = interval

        entity_groups = {}

        for item in values:
            for entity_id in item.entities:
                entity_groups.setdefault(
                    entity_id,
                    [],
                ).append(
                    item
                )

        for entity_id, entity_events in (
            entity_groups.items()
        ):
            ordered = sorted(
                entity_events,
                key=lambda item: (
                    int(
                        item.metadata.get(
                            "sequence",
                            1000000,
                        )
                    ),
                    to_utc(
                        item.start.earliest
                    ),
                    item.id,
                ),
            )

            for previous, current in zip(
                ordered,
                ordered[
                    1:
                ],
            ):
                travel = self.travel(
                    previous.location_id,
                    current.location_id,
                    mode=mode,
                )

                if (
                    travel[
                        "outcome"
                    ]
                    == "unknown"
                ):
                    return {
                        "schema":
                            (
                                "savant.carbon.oriel."
                                "schedule-solver.v1"
                            ),

                        "owner":
                            owner,

                        "component":
                            component,

                        "authority_effect":
                            authority_effect,

                        "backend":
                            "ortools-cp-sat",

                        "ortools_available":
                            True,

                        "outcome":
                            "unknown",

                        "reason":
                            (
                                "solver input contains "
                                "an unresolved travel leg"
                            ),

                        "previous":
                            previous.id,

                        "current":
                            current.id,
                    }

                required_gap = (
                    previous.duration_minutes
                    + previous.teardown_minutes
                    + int(
                        travel[
                            "minimum_minutes"
                        ]
                    )
                    + current.setup_minutes
                    + previous.recovery_minutes
                )

                model.Add(
                    starts[
                        current.id
                    ]
                    >= starts[
                        previous.id
                    ]
                    + required_gap
                )

        resource_groups = {}

        for item in values:
            for resource in item.resources:
                resource_groups.setdefault(
                    resource,
                    [],
                ).append(
                    intervals[
                        item.id
                    ]
                )

        for group in (
            resource_groups.values()
        ):
            if len(
                group
            ) > 1:
                model.AddNoOverlap(
                    group
                )

        model.Minimize(
            sum(
                starts.values()
            )
        )

        solver = cp_model.CpSolver()

        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        solver.parameters.max_time_in_seconds = 10.0

        result = solver.Solve(
            model
        )

        feasible_states = {
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        }

        if result not in feasible_states:
            return {
                "schema":
                    (
                        "savant.carbon.oriel."
                        "schedule-solver.v1"
                    ),

                "owner":
                    owner,

                "component":
                    component,

                "authority_effect":
                    authority_effect,

                "backend":
                    "ortools-cp-sat",

                "ortools_available":
                    True,

                "outcome":
                    "fail",

                "solver_status":
                    solver.StatusName(
                        result
                    ),

                "reason":
                    (
                        "no schedule satisfies the "
                        "declared temporal, travel "
                        "and resource constraints"
                    ),
            }

        schedule = []

        for item in values:
            minute = solver.Value(
                starts[
                    item.id
                ]
            )

            resolved_start = (
                base
                + timedelta(
                    minutes=minute
                )
            )

            resolved_end = (
                resolved_start
                + timedelta(
                    minutes=
                        item.duration_minutes
                )
            )

            schedule.append(
                {
                    "event":
                        item.id,

                    "resolved_start":
                        resolved_start.isoformat(),

                    "resolved_end":
                        resolved_end.isoformat(),

                    "location_id":
                        item.location_id,

                    "entities":
                        list(
                            item.entities
                        ),
                }
            )

        return {
            "schema":
                (
                    "savant.carbon.oriel."
                    "schedule-solver.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "backend":
                "ortools-cp-sat",

            "ortools_available":
                True,

            "outcome":
                "pass",

            "solver_status":
                solver.StatusName(
                    result
                ),

            "deterministic_parameters": {
                "num_search_workers":
                    1,

                "random_seed":
                    0,

                "max_time_seconds":
                    10.0,
            },

            "schedule":
                sorted(
                    schedule,
                    key=lambda item: (
                        item[
                            "resolved_start"
                        ],
                        item[
                            "event"
                        ],
                    ),
                ),

            "source_state_mutated":
                False,

            "simulation_output_is_authority":
                False,
        }

    def evaluate_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        document = self.export_document()

        events = list(
            document[
                "events"
            ]
        )

        events.append(
            copy.deepcopy(
                dict(
                    candidate
                )
            )
        )

        document[
            "events"
        ] = events

        candidate_engine = (
            oriel_engine.from_document(
                document
            )
        )

        result = candidate_engine.validate(
            mode=mode
        )

        return {
            "schema":
                (
                    "savant.carbon.oriel."
                    "quantum-feasibility.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "projection_only":
                True,

            "candidate_id":
                candidate.get(
                    "id"
                ),

            "feasible":
                result[
                    "failure_count"
                ]
                == 0,

            "outcome":
                result[
                    "outcome"
                ],

            "validation":
                result,

            "source_state_mutated":
                False,

            "quantum_contract": {
                "consumer":
                    "carbon simulation branching",

                "purpose":
                    (
                        "evaluate a proposed branch "
                        "without selecting, collapsing "
                        "or admitting it"
                    ),

                "branch_selected":
                    False,

                "canon_effect":
                    "none",

                "evidence_admission":
                    False,
            },
        }

    def export_document(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                (
                    "savant.carbon.oriel."
                    "document.v1"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "locations": [
                self.locations[
                    key
                ].projection()
                for key
                in sorted(
                    self.locations
                )
            ],

            "events": [
                self.events[
                    key
                ].projection()
                for key
                in sorted(
                    self.events
                )
            ],

            "routes": [
                {
                    "source":
                        item.source,

                    "target":
                        item.target,

                    "mode":
                        item.mode,

                    "distance_km":
                        item.distance_km,

                    "minimum_minutes":
                        item.minimum_minutes,

                    "maximum_minutes":
                        item.maximum_minutes,

                    "bidirectional":
                        item.bidirectional,

                    "border_minutes":
                        item.border_minutes,

                    "source_class":
                        item.source_class,

                    "source_refs":
                        list(
                            item.source_refs
                        ),

                    "metadata":
                        copy.deepcopy(
                            dict(
                                item.metadata
                            )
                        ),
                }
                for item
                in sorted(
                    self.routes,
                    key=lambda value: (
                        value.source,
                        value.target,
                        value.mode,
                    ),
                )
            ],

            "external_constraints": [
                {
                    "id":
                        item.id,

                    "kind":
                        item.kind,

                    "start":
                        item.start.projection(),

                    "end":
                        item.end.projection(),

                    "location_id":
                        item.location_id,

                    "entities":
                        list(
                            item.entities
                        ),

                    "resources":
                        list(
                            item.resources
                        ),

                    "constraint_class":
                        item.constraint_class,

                    "source_class":
                        item.source_class,

                    "source_refs":
                        list(
                            item.source_refs
                        ),

                    "metadata":
                        copy.deepcopy(
                            dict(
                                item.metadata
                            )
                        ),
                }
                for item
                in sorted(
                    self.constraints.values(),
                    key=lambda value:
                        value.id,
                )
            ],

            "transport_profiles": [
                {
                    "id":
                        item.id,

                    "minimum_speed_kph":
                        item.minimum_speed_kph,

                    "maximum_speed_kph":
                        item.maximum_speed_kph,

                    "distance_factor":
                        item.distance_factor,

                    "fixed_minutes":
                        item.fixed_minutes,

                    "minimum_recovery_minutes":
                        (
                            item
                            .minimum_recovery_minutes
                        ),
                }
                for item
                in sorted(
                    self.transport_profiles.values(),
                    key=lambda value:
                        value.id,
                )
            ],
        }


def capability_manifest() -> dict[str, Any]:
    common_projection = {
        "modes": [
            "reference",
            "instance",
            "composition",
        ],

        "instanceable":
            True,

        "composable":
            True,

        "maskable":
            True,

        "ownership_transfer":
            False,

        "authority_transfer":
            False,
    }

    def capability(
        identifier: str,
        kind: str,
        purpose: str,
        operations: Sequence[str],
        *,
        deterministic:
            bool = True,
    ) -> dict[str, Any]:
        return {
            "id":
                identifier,

            "owner":
                owner,

            "component":
                component,

            "kind":
                kind,

            "purpose":
                purpose,

            "version":
                "1.0.0",

            "status":
                "active",

            "authority_effect":
                "none",

            "execution_owner":
                owner,

            "projection_owner":
                "filament",

            "transformation_owner":
                "modus",

            "operations":
                list(
                    operations
                ),

            "deterministic":
                deterministic,

            "projection":
                copy.deepcopy(
                    common_projection
                ),

            "lineage": {
                "ancestor":
                    "oriel",

                "current_owner":
                    "carbon",

                "relationship":
                    "contained-specialization",
            },
        }

    capabilities = [
        capability(
            "oriel_chronology_validation",
            "constraint",
            (
                "Validate temporally bounded "
                "events without false precision."
            ),
            [
                "validate",
                "explain",
            ],
        ),

        capability(
            "oriel_logistics_validation",
            "constraint",
            (
                "Evaluate travel, setup, teardown, "
                "recovery and resource feasibility."
            ),
            [
                "validate",
                "explain",
            ],
        ),

        capability(
            "oriel_route_projection",
            "projection",
            (
                "Project source-backed or explicitly "
                "estimated travel envelopes."
            ),
            [
                "route",
                "alternatives",
            ],
        ),

        capability(
            "oriel_spacetime_position",
            "projection",
            (
                "Project entity location or route "
                "position at a timestamp."
            ),
            [
                "position_at",
            ],
        ),

        capability(
            "oriel_encounter_windows",
            "projection",
            (
                "Locate historically possible "
                "proximity windows between entities."
            ),
            [
                "encounters",
            ],
        ),

        capability(
            "oriel_candidate_windows",
            "projection",
            (
                "Find insertion windows that preserve "
                "surrounding chronology and logistics."
            ),
            [
                "candidate_windows",
            ],
        ),

        capability(
            "oriel_schedule_solver",
            "solver",
            (
                "Solve bounded temporal/resource "
                "schedules using deterministic CP-SAT "
                "when available."
            ),
            [
                "solve",
            ],
        ),

        capability(
            "oriel_quantum_feasibility",
            "projection",
            (
                "Evaluate candidate branch events "
                "without selecting or admitting them."
            ),
            [
                "evaluate_candidate",
            ],
        ),

        capability(
            "oriel_historical_constraint_binding",
            "evidence",
            (
                "Bind sourced historical closures, "
                "bookings and constraints to "
                "simulation feasibility."
            ),
            [
                "validate",
            ],
        ),

        capability(
            "oriel_uncertainty_preservation",
            "epistemic",
            (
                "Preserve unknown, bounded, derived "
                "and estimated states explicitly."
            ),
            [
                "validate",
                "project",
            ],
        ),
    ]

    return {
        "schema":
            (
                "savant.carbon.oriel."
                "capabilities.v1"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "status":
            "active",

        "singular_purpose":
            (
                "chronology and logistics "
                "intelligence inside carbon simulation"
            ),

        "capabilities":
            capabilities,

        "invariants": {
            "carbon_owns_simulation":
                True,

            "oriel_is_not_an_exile":
                True,

            "oriel_is_not_authority":
                True,

            "source_authority_preserved":
                True,

            "unknown_never_silently_passes":
                True,

            "estimates_are_labeled":
                True,

            "quantum_branching_not_owned_by_oriel":
                True,

            "source_state_not_mutated":
                True,

            "projection_by_reference_supported":
                True,
        },
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            (
                "savant.carbon.oriel."
                "status.v1"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "carbon_owned":
            True,

        "standalone_oriel_root":
            False,

        "networkx_available":
            nx is not None,

        "ortools_available":
            cp_model is not None,

        "timezone_backend":
            "stdlib-zoneinfo",

        "route_fallback":
            "deterministic-stdlib-dijkstra",

        "enhancement_count":
            len(
                enhancements
            ),

        "enhancements":
            list(
                enhancements
            ),

        "capability_count":
            len(
                capability_manifest()[
                    "capabilities"
                ]
            ),

        "quantum_boundary":
            (
                "candidate feasibility only; "
                "branch ownership remains carbon "
                "scenario/counterfactual simulation"
            ),

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    document = {
        "locations": [
            {
                "id":
                    "alpha",

                "name":
                    "alpha",

                "latitude":
                    40.0,

                "longitude":
                    -75.0,

                "timezone":
                    "America/New_York",

                "source_class":
                    "verified_external",
            },
            {
                "id":
                    "beta",

                "name":
                    "beta",

                "latitude":
                    41.0,

                "longitude":
                    -74.0,

                "timezone":
                    "America/New_York",

                "source_class":
                    "verified_external",
            },
        ],

        "routes": [
            {
                "source":
                    "alpha",

                "target":
                    "beta",

                "mode":
                    "tour_bus",

                "distance_km":
                    180,

                "minimum_minutes":
                    150,

                "maximum_minutes":
                    210,

                "source_class":
                    "verified_external",
            }
        ],

        "events": [
            {
                "id":
                    "show-a",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "alpha",

                "start":
                    "2026-01-01T19:00:00-05:00",

                "duration_minutes":
                    120,

                "teardown_minutes":
                    45,

                "source_class":
                    "asserted",
            },
            {
                "id":
                    "show-b",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "beta",

                "start":
                    "2026-01-02T19:00:00-05:00",

                "duration_minutes":
                    120,

                "setup_minutes":
                    60,

                "source_class":
                    "asserted",
            },
        ],
    }

    engine = oriel_engine.from_document(
        document
    )

    validation = engine.validate()

    if validation[
        "failure_count"
    ]:
        raise oriel_error(
            "focused chronology test failed"
        )

    route = engine.travel(
        "alpha",
        "beta",
    )

    if route[
        "outcome"
    ] == "unknown":
        raise oriel_error(
            "focused route test failed"
        )

    position = engine.position_at(
        "band",
        "2026-01-02T06:00:00-05:00",
    )

    return {
        "schema":
            (
                "savant.carbon.oriel."
                "selftest.v1"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "validation_outcome":
            validation[
                "outcome"
            ],

        "route_outcome":
            route[
                "outcome"
            ],

        "position_state":
            position[
                "state"
            ],

        "networkx_available":
            nx is not None,

        "ortools_available":
            cp_model is not None,
    }


__all__ = [
    "capability_manifest",
    "event",
    "external_constraint",
    "haversine_km",
    "location",
    "oriel_engine",
    "oriel_error",
    "route_edge",
    "selftest",
    "status",
    "temporal_window",
    "transport_profile",
]
