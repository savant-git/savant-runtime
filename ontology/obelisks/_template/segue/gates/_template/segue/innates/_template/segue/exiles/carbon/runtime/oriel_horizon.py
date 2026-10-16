#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from oriel import (
    oriel_engine,
    oriel_error,
    parse_datetime,
    to_utc,
)

from oriel_simulation import (
    engine as simulation_engine,
)

from oriel_reality import (
    engine as reality_engine,
)


owner = "carbon"
component = "oriel-horizon"
authority_effect = "none"
schema = "savant.carbon.oriel-horizon.v1"

immutable_source_classes = {
    "verified_external",
    "admitted_evidence",
}

physical_states = {
    "reachable",
    "unreachable",
    "unresolved",
}

reality_states = {
    "verified_conflict",
    "verified_available",
    "no_conflict_found",
    "unresolved",
}

enhancements = (
    "spacetime reachability cones",
    "next immutable commitment discovery",
    "point-of-no-return projection",
    "conservative maximum-travel envelopes",
    "detour budget calculation",
    "candidate dwell-time feasibility",
    "candidate location ranking",
    "reality-bound candidate windows",
    "verified-conflict blocking",
    "unresolved-availability preservation",
    "complete-calendar no-conflict semantics",
    "in-transit synthetic origin projection",
    "continuous-position reachability",
    "explicit horizon-end support",
    "immutable-anchor deadline precedence",
    "setup-time deadline subtraction",
    "direct-path reserve calculation",
    "detour-overhead calculation",
    "return-to-anchor feasibility",
    "remaining optionality calculation",
    "reachable-location frontier",
    "unreachable-location explanation",
    "unresolved-route explanation",
    "historical-presence opportunity projection",
    "historical-entity opportunity filtering",
    "opportunity-window intersection",
    "minimum dwell guarantees",
    "conservative route selection",
    "deterministic cone identity",
    "deterministic opportunity identity",
    "source-state immutability",
    "canon-neutral projection",
    "evidence-neutral projection",
    "filament-projectable horizon packets",
    "modus-maskable horizon metadata",
)


class oriel_horizon_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


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


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        prefix
        + ":"
        + digest(
            value
        )[:24]
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


def raw_event_index(
    document: Mapping[
        str,
        Any,
    ],
) -> dict[
    str,
    dict[
        str,
        Any,
    ],
]:
    output = {}

    for value in document.get(
        "events",
        [],
    ):
        if not isinstance(
            value,
            Mapping,
        ):
            continue

        identifier = str(
            value.get(
                "id",
                "",
            )
        ).strip()

        if identifier:
            output[
                identifier
            ] = clone(
                dict(
                    value
                )
            )

    return output


def event_locked(
    value: Mapping[
        str,
        Any,
    ],
) -> bool:
    metadata = value.get(
        "metadata",
        {},
    )

    start = value.get(
        "start"
    )

    end = value.get(
        "end"
    )

    return bool(
        value.get(
            "locked",
            False,
        )
        or (
            isinstance(
                metadata,
                Mapping,
            )
            and metadata.get(
                "locked",
                False,
            )
        )
        or (
            isinstance(
                start,
                Mapping,
            )
            and start.get(
                "locked",
                False,
            )
        )
        or (
            isinstance(
                end,
                Mapping,
            )
            and end.get(
                "locked",
                False,
            )
        )
    )


def event_immutable(
    value: Mapping[
        str,
        Any,
    ],
) -> bool:
    return (
        event_locked(
            value
        )
        or str(
            value.get(
                "source_class",
                "unknown",
            )
        ).strip().lower()
        in immutable_source_classes
    )


def future_immutable_anchors(
    document: Mapping[
        str,
        Any,
    ],
    *,
    entity: str,
    timestamp: datetime,
) -> list[dict[str, Any]]:
    engine = oriel_engine.from_document(
        document
    )

    raw = raw_event_index(
        document
    )

    at = to_utc(
        timestamp
    )

    values = []

    for value in engine.events.values():
        if entity not in value.entities:
            continue

        source = raw.get(
            value.id,
            {},
        )

        if not event_immutable(
            source
        ):
            continue

        deadline = (
            to_utc(
                value.start.earliest
            )
            - timedelta(
                minutes=
                    value.setup_minutes
            )
        )

        if deadline < at:
            continue

        values.append(
            {
                "id":
                    value.id,

                "location_id":
                    value.location_id,

                "scheduled_start":
                    to_utc(
                        value.start.earliest
                    ).isoformat(),

                "arrival_deadline":
                    deadline.isoformat(),

                "setup_minutes":
                    value.setup_minutes,

                "source_class":
                    value.source_class,

                "locked":
                    event_locked(
                        source
                    ),

                "immutable":
                    True,
            }
        )

    return sorted(
        values,
        key=lambda value: (
            value[
                "arrival_deadline"
            ],
            value[
                "id"
            ],
        ),
    )


def origin_projection(
    document: Mapping[
        str,
        Any,
    ],
    *,
    entity: str,
    timestamp: Any,
    mode: str,
) -> tuple[
    dict[str, Any],
    str,
    dict[str, Any],
]:
    engine = oriel_engine.from_document(
        document
    )

    position = engine.position_at(
        entity,
        timestamp,
        mode=mode,
    )

    state = str(
        position.get(
            "state",
            "unknown",
        )
    )

    if state in {
        "stationary",
        "event-envelope",
    }:
        location = position.get(
            "location"
        )

        if not isinstance(
            location,
            Mapping,
        ):
            raise oriel_horizon_error(
                (
                    "position lacks location "
                    "projection"
                )
            )

        location_id = str(
            location.get(
                "id",
                "",
            )
        ).strip()

        if not location_id:
            raise oriel_horizon_error(
                "position location lacks id"
            )

        return (
            clone(
                dict(
                    document
                )
            ),
            location_id,
            position,
        )

    if state == "travel":
        point = position.get(
            "position"
        )

        if not isinstance(
            point,
            Mapping,
        ):
            raise oriel_horizon_error(
                (
                    "travel position lacks "
                    "coordinate projection"
                )
            )

        latitude = point.get(
            "latitude"
        )

        longitude = point.get(
            "longitude"
        )

        if not isinstance(
            latitude,
            (
                int,
                float,
            ),
        ) or not isinstance(
            longitude,
            (
                int,
                float,
            ),
        ):
            raise oriel_horizon_error(
                (
                    "travel position lacks "
                    "usable coordinates"
                )
            )

        origin_id = (
            "__oriel_horizon_origin__"
            + digest(
                {
                    "entity":
                        entity,

                    "timestamp":
                        str(
                            timestamp
                        ),

                    "latitude":
                        latitude,

                    "longitude":
                        longitude,
                }
            )[:12]
        )

        output = clone(
            dict(
                document
            )
        )

        locations = list(
            output.get(
                "locations",
                [],
            )
        )

        locations.append(
            {
                "id":
                    origin_id,

                "name":
                    "oriel derived transit origin",

                "latitude":
                    float(
                        latitude
                    ),

                "longitude":
                    float(
                        longitude
                    ),

                "timezone":
                    "UTC",

                "source_class":
                    "derived",

                "metadata": {
                    "synthetic":
                        True,

                    "projection_only":
                        True,

                    "entity":
                        entity,

                    "timestamp":
                        str(
                            timestamp
                        ),
                },
            }
        )

        output[
            "locations"
        ] = locations

        return (
            output,
            origin_id,
            position,
        )

    raise oriel_horizon_error(
        (
            "entity position is unresolved "
            "at requested timestamp"
        )
    )


def conservative_minutes(
    travel: Mapping[
        str,
        Any,
    ],
) -> int | None:
    if travel.get(
        "outcome"
    ) == "unknown":
        return None

    value = travel.get(
        "maximum_minutes"
    )

    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return None

    return int(
        value
    )


def candidate_rank(
    value: Mapping[
        str,
        Any,
    ],
) -> tuple[
    int,
    int,
    float,
    int,
    str,
]:
    physical_rank = {
        "reachable":
            0,

        "unresolved":
            1,

        "unreachable":
            2,
    }.get(
        str(
            value.get(
                "physical_state",
                "unresolved",
            )
        ),
        3,
    )

    reality_rank = {
        "verified_available":
            0,

        "no_conflict_found":
            1,

        "unresolved":
            2,

        "verified_conflict":
            3,
    }.get(
        str(
            value.get(
                "reality_state",
                "unresolved",
            )
        ),
        4,
    )

    available = value.get(
        "available_minutes"
    )

    available_rank = (
        -float(
            available
        )
        if isinstance(
            available,
            (
                int,
                float,
            ),
        )
        else float(
            "inf"
        )
    )

    burden = int(
        value.get(
            "detour_travel_minutes",
            10**9,
        )
    )

    return (
        physical_rank,
        reality_rank,
        available_rank,
        burden,
        str(
            value.get(
                "location_id",
                "",
            )
        ),
    )


def fact_time_bounds(
    value: Mapping[
        str,
        Any,
    ],
) -> tuple[
    datetime,
    datetime,
] | None:
    start = value.get(
        "start"
    )

    end = value.get(
        "end",
        start,
    )

    if start is None:
        return None

    try:
        if isinstance(
            start,
            Mapping,
        ):
            start_value = parse_datetime(
                start.get(
                    "earliest",
                    start.get(
                        "at"
                    ),
                ),
                timezone_name=(
                    str(
                        start.get(
                            "timezone"
                        )
                    )
                    if start.get(
                        "timezone"
                    )
                    is not None
                    else None
                ),
            )

        else:
            start_value = parse_datetime(
                start
            )

        if isinstance(
            end,
            Mapping,
        ):
            end_value = parse_datetime(
                end.get(
                    "latest",
                    end.get(
                        "at",
                        end.get(
                            "earliest"
                        ),
                    ),
                ),
                timezone_name=(
                    str(
                        end.get(
                            "timezone"
                        )
                    )
                    if end.get(
                        "timezone"
                    )
                    is not None
                    else None
                ),
            )

        else:
            end_value = parse_datetime(
                end
            )

    except (
        TypeError,
        ValueError,
        oriel_error,
    ):
        return None

    return (
        to_utc(
            start_value
        ),
        to_utc(
            end_value
        ),
    )


class OrielHorizonEngine:
    def reachability(
        self,
        document: Mapping[
            str,
            Any,
        ],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        entity: str,
        timestamp: Any,
        duration_minutes: int = 60,
        mode: str = "tour_bus",
        candidate_locations:
            Sequence[str] = (),
        until: Any = None,
    ) -> dict[str, Any]:
        if duration_minutes < 0:
            raise oriel_horizon_error(
                (
                    "duration_minutes may not "
                    "be negative"
                )
            )

        world = (
            simulation_engine.compile_world(
                document,
                facts,
            )
        )

        bound_document = world[
            "bound_document"
        ]

        at = to_utc(
            parse_datetime(
                timestamp
            )
        )

        (
            projected_document,
            origin_id,
            position,
        ) = origin_projection(
            bound_document,
            entity=entity,
            timestamp=
                timestamp,
            mode=mode,
        )

        engine = oriel_engine.from_document(
            projected_document
        )

        anchors = future_immutable_anchors(
            bound_document,
            entity=entity,
            timestamp=at,
        )

        anchor = (
            anchors[
                0
            ]
            if anchors
            else None
        )

        explicit_until = (
            to_utc(
                parse_datetime(
                    until
                )
            )
            if until
            is not None
            else None
        )

        if (
            anchor is None
            and explicit_until
            is None
        ):
            raise oriel_horizon_error(
                (
                    "until is required when "
                    "no future immutable anchor exists"
                )
            )

        anchor_deadline = (
            to_utc(
                parse_datetime(
                    anchor[
                        "arrival_deadline"
                    ]
                )
            )
            if anchor
            is not None
            else None
        )

        deadline_candidates = [
            value
            for value
            in (
                anchor_deadline,
                explicit_until,
            )
            if value
            is not None
        ]

        horizon_end = min(
            deadline_candidates
        )

        if horizon_end < at:
            raise oriel_horizon_error(
                (
                    "reachability horizon ends "
                    "before requested timestamp"
                )
            )

        if candidate_locations:
            location_ids = sorted(
                {
                    str(
                        value
                    ).strip()
                    for value
                    in candidate_locations
                    if str(
                        value
                    ).strip()
                }
            )

        else:
            location_ids = sorted(
                {
                    str(
                        value.get(
                            "id",
                            "",
                        )
                    ).strip()
                    for value
                    in bound_document.get(
                        "locations",
                        [],
                    )
                    if (
                        isinstance(
                            value,
                            Mapping,
                        )
                        and str(
                            value.get(
                                "id",
                                "",
                            )
                        ).strip()
                    )
                }
            )

        direct = None
        direct_minutes = None
        point_of_no_return = None
        direct_slack = None

        if anchor is not None:
            direct = engine.travel(
                origin_id,
                anchor[
                    "location_id"
                ],
                mode=mode,
            )

            direct_minutes = (
                conservative_minutes(
                    direct
                )
            )

            if direct_minutes is not None:
                point_of_no_return = (
                    anchor_deadline
                    - timedelta(
                        minutes=
                            direct_minutes
                    )
                )

                direct_slack = minutes_between(
                    at,
                    point_of_no_return,
                )

        rows = []

        for location_id in location_ids:
            if (
                location_id
                not in engine.locations
            ):
                rows.append(
                    {
                        "location_id":
                            location_id,

                        "physical_state":
                            "unresolved",

                        "reality_state":
                            "unresolved",

                        "reason":
                            (
                                "candidate location "
                                "is unknown"
                            ),
                    }
                )

                continue

            inbound = engine.travel(
                origin_id,
                location_id,
                mode=mode,
            )

            inbound_minutes = (
                conservative_minutes(
                    inbound
                )
            )

            outbound = None
            outbound_minutes = 0

            if anchor is not None:
                outbound = engine.travel(
                    location_id,
                    anchor[
                        "location_id"
                    ],
                    mode=mode,
                )

                outbound_minutes = (
                    conservative_minutes(
                        outbound
                    )
                )

            if (
                inbound_minutes is None
                or outbound_minutes is None
            ):
                rows.append(
                    {
                        "location_id":
                            location_id,

                        "physical_state":
                            "unresolved",

                        "reality_state":
                            "unresolved",

                        "inbound":
                            inbound,

                        "outbound":
                            outbound,

                        "reason":
                            (
                                "one or more travel "
                                "legs are unresolved"
                            ),
                    }
                )

                continue

            earliest_arrival = (
                at
                + timedelta(
                    minutes=
                        inbound_minutes
                )
            )

            latest_departure = (
                horizon_end
                - timedelta(
                    minutes=
                        outbound_minutes
                )
            )

            available_minutes = (
                minutes_between(
                    earliest_arrival,
                    latest_departure,
                )
            )

            physical_state = (
                "reachable"
                if available_minutes
                >= duration_minutes
                else "unreachable"
            )

            reality_state = "unresolved"
            availability = None

            if (
                physical_state
                == "reachable"
                and duration_minutes
                > 0
            ):
                dwell_end = (
                    earliest_arrival
                    + timedelta(
                        minutes=
                            duration_minutes
                    )
                )

                availability = (
                    reality_engine.availability(
                        document,
                        facts,
                        location_id=
                            location_id,
                        start=
                            earliest_arrival.isoformat(),
                        end=
                            dwell_end.isoformat(),
                    )
                )

                reality_state = str(
                    availability.get(
                        "state",
                        "unresolved",
                    )
                )

            elif (
                physical_state
                == "reachable"
                and duration_minutes
                == 0
            ):
                reality_state = (
                    "no_conflict_found"
                )

            detour_travel = (
                inbound_minutes
                + outbound_minutes
            )

            detour_overhead = (
                (
                    detour_travel
                    - direct_minutes
                )
                if direct_minutes
                is not None
                else None
            )

            usable = (
                physical_state
                == "reachable"
                and reality_state
                != "verified_conflict"
            )

            rows.append(
                {
                    "location_id":
                        location_id,

                    "physical_state":
                        physical_state,

                    "reality_state":
                        reality_state,

                    "usable":
                        usable,

                    "earliest_arrival":
                        earliest_arrival.isoformat(),

                    "latest_departure":
                        latest_departure.isoformat(),

                    "available_minutes":
                        round(
                            available_minutes,
                            3,
                        ),

                    "required_duration_minutes":
                        duration_minutes,

                    "inbound_minutes":
                        inbound_minutes,

                    "outbound_minutes":
                        outbound_minutes,

                    "detour_travel_minutes":
                        detour_travel,

                    "detour_overhead_minutes":
                        detour_overhead,

                    "inbound":
                        inbound,

                    "outbound":
                        outbound,

                    "availability":
                        availability,

                    "anchor_id":
                        (
                            anchor[
                                "id"
                            ]
                            if anchor
                            is not None
                            else None
                        ),
                }
            )

        rows = sorted(
            rows,
            key=candidate_rank,
        )

        result = {
            "schema":
                schema,

            "kind":
                (
                    "spacetime-"
                    "reachability-cone"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "id":
                stable_id(
                    "carbon-oriel-horizon",
                    {
                        "world_id":
                            world[
                                "id"
                            ],

                        "entity":
                            entity,

                        "timestamp":
                            at.isoformat(),

                        "duration_minutes":
                            duration_minutes,

                        "mode":
                            mode,

                        "anchor":
                            anchor,

                        "until":
                            (
                                explicit_until
                                .isoformat()
                                if explicit_until
                                is not None
                                else None
                            ),

                        "locations":
                            location_ids,
                    },
                ),

            "world_id":
                world[
                    "id"
                ],

            "entity":
                entity,

            "timestamp":
                at.isoformat(),

            "position":
                position,

            "origin_location_id":
                origin_id,

            "origin_is_synthetic":
                origin_id.startswith(
                    (
                        "__oriel_horizon_"
                        "origin__"
                    )
                ),

            "mode":
                mode,

            "duration_minutes":
                duration_minutes,

            "next_immutable_anchor":
                anchor,

            "future_immutable_anchor_count":
                len(
                    anchors
                ),

            "future_immutable_anchors":
                anchors,

            "horizon_end":
                horizon_end.isoformat(),

            "direct_anchor_route":
                direct,

            "direct_anchor_travel_minutes":
                direct_minutes,

            "point_of_no_return":
                (
                    point_of_no_return
                    .isoformat()
                    if point_of_no_return
                    is not None
                    else None
                ),

            "direct_anchor_slack_minutes":
                (
                    round(
                        direct_slack,
                        3,
                    )
                    if direct_slack
                    is not None
                    else None
                ),

            "candidate_count":
                len(
                    rows
                ),

            "reachable_count":
                sum(
                    1
                    for value
                    in rows
                    if value.get(
                        "physical_state"
                    )
                    == "reachable"
                ),

            "usable_count":
                sum(
                    1
                    for value
                    in rows
                    if value.get(
                        "usable"
                    )
                    is True
                ),

            "unresolved_count":
                sum(
                    1
                    for value
                    in rows
                    if value.get(
                        "physical_state"
                    )
                    == "unresolved"
                ),

            "candidates":
                rows,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,

            "absence_of_evidence_is_availability":
                False,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def frontier(
        self,
        cone: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        candidates = [
            value
            for value
            in cone.get(
                "candidates",
                [],
            )
            if (
                isinstance(
                    value,
                    Mapping,
                )
                and value.get(
                    "physical_state"
                )
                == "reachable"
                and value.get(
                    "reality_state"
                )
                != "verified_conflict"
            )
        ]

        frontier = []

        for candidate in candidates:
            candidate_available = float(
                candidate.get(
                    "available_minutes",
                    0.0,
                )
            )

            candidate_burden = float(
                candidate.get(
                    "detour_travel_minutes",
                    0.0,
                )
            )

            dominated = False

            for other in candidates:
                if other is candidate:
                    continue

                other_available = float(
                    other.get(
                        "available_minutes",
                        0.0,
                    )
                )

                other_burden = float(
                    other.get(
                        "detour_travel_minutes",
                        0.0,
                    )
                )

                if (
                    other_available
                    >= candidate_available
                    and other_burden
                    <= candidate_burden
                    and (
                        other_available
                        > candidate_available
                        or other_burden
                        < candidate_burden
                    )
                ):
                    dominated = True
                    break

            if not dominated:
                frontier.append(
                    clone(
                        candidate
                    )
                )

        frontier = sorted(
            frontier,
            key=candidate_rank,
        )

        return {
            "schema":
                schema,

            "kind":
                "reachability-frontier",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "cone_id":
                cone.get(
                    "id"
                ),

            "frontier_count":
                len(
                    frontier
                ),

            "frontier":
                frontier,

            "derived":
                True,

            "source_state_mutated":
                False,
        }

    def historical_opportunities(
        self,
        cone: Mapping[
            str,
            Any,
        ],
        facts: Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
        *,
        historical_entity:
            str | None = None,
    ) -> dict[str, Any]:
        candidates = {
            str(
                value.get(
                    "location_id",
                    "",
                )
            ):
                value
            for value
            in cone.get(
                "candidates",
                [],
            )
            if (
                isinstance(
                    value,
                    Mapping,
                )
                and value.get(
                    "physical_state"
                )
                == "reachable"
                and value.get(
                    "reality_state"
                )
                != "verified_conflict"
            )
        }

        matches = []

        for fact in facts:
            if not isinstance(
                fact,
                Mapping,
            ):
                continue

            if historical_entity:
                entities = {
                    str(
                        value
                    )
                    for value
                    in fact.get(
                        "entities",
                        [],
                    )
                }

                if (
                    historical_entity
                    not in entities
                ):
                    continue

            location_id = str(
                fact.get(
                    "location_id",
                    "",
                )
            ).strip()

            candidate = candidates.get(
                location_id
            )

            if candidate is None:
                continue

            bounds = fact_time_bounds(
                fact
            )

            if bounds is None:
                continue

            candidate_start = to_utc(
                parse_datetime(
                    candidate[
                        "earliest_arrival"
                    ]
                )
            )

            candidate_end = to_utc(
                parse_datetime(
                    candidate[
                        "latest_departure"
                    ]
                )
            )

            overlap_start = max(
                candidate_start,
                bounds[
                    0
                ],
            )

            overlap_end = min(
                candidate_end,
                bounds[
                    1
                ],
            )

            if (
                overlap_end
                < overlap_start
            ):
                continue

            source_class = str(
                fact.get(
                    "source_class",
                    "unknown",
                )
            ).strip().lower()

            verification_state = str(
                fact.get(
                    "verification_state",
                    "unknown",
                )
            ).strip().lower()

            matches.append(
                {
                    "fact_id":
                        fact.get(
                            "id"
                        ),

                    "historical_entity":
                        historical_entity,

                    "location_id":
                        location_id,

                    "earliest":
                        overlap_start.isoformat(),

                    "latest":
                        overlap_end.isoformat(),

                    "window_minutes":
                        round(
                            minutes_between(
                                overlap_start,
                                overlap_end,
                            ),
                            3,
                        ),

                    "source_class":
                        source_class,

                    "verification_state":
                        verification_state,

                    "source_refs":
                        clone(
                            fact.get(
                                "source_refs",
                                [],
                            )
                        ),

                    "historical_presence_verified":
                        (
                            source_class
                            in {
                                "verified_external",
                                "admitted_evidence",
                            }
                            and verification_state
                            in {
                                "verified",
                                "corroborated",
                            }
                        ),

                    "interaction_is_historical_fact":
                        False,

                    "interaction_is_simulation_opportunity":
                        True,
                }
            )

        result = {
            "schema":
                schema,

            "kind":
                (
                    "reachable-historical-"
                    "opportunities"
                ),

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "cone_id":
                cone.get(
                    "id"
                ),

            "historical_entity":
                historical_entity,

            "match_count":
                len(
                    matches
                ),

            "matches":
                sorted(
                    matches,
                    key=lambda value: (
                        value[
                            "earliest"
                        ],
                        value[
                            "location_id"
                        ],
                        str(
                            value.get(
                                "fact_id",
                                "",
                            )
                        ),
                    ),
                ),

            "interaction_claimed_as_fact":
                False,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",
        }

        result[
            "id"
        ] = stable_id(
            (
                "carbon-oriel-"
                "opportunities"
            ),
            result,
        )

        result[
            "digest"
        ] = digest(
            result
        )

        return result


engine = OrielHorizonEngine()


def capability_manifest() -> dict[str, Any]:
    projection = {
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
                True,

            "projection":
                clone(
                    projection
                ),
        }

    return {
        "schema":
            (
                "savant.carbon.oriel-horizon."
                "capabilities.v1"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "capabilities": [
            capability(
                "oriel_spacetime_reachability",
                "spacetime-projection",
                (
                    "Project all candidate "
                    "locations an entity can "
                    "physically reach and leave "
                    "before its next immutable "
                    "commitment."
                ),
                [
                    "reachability",
                ],
            ),

            capability(
                "oriel_point_of_no_return",
                "chronometric-analysis",
                (
                    "Calculate the latest "
                    "instant at which an entity "
                    "can depart for its next "
                    "immutable commitment."
                ),
                [
                    "reachability",
                ],
            ),

            capability(
                "oriel_reachability_frontier",
                "spacetime-analysis",
                (
                    "Retain non-dominated "
                    "reachable locations by "
                    "optional time and travel "
                    "burden."
                ),
                [
                    "frontier",
                ],
            ),

            capability(
                (
                    "oriel_reachable_"
                    "historical_opportunities"
                ),
                "historical-spacetime-analysis",
                (
                    "Intersect reachable "
                    "spacetime with sourced "
                    "historical presence without "
                    "converting opportunity "
                    "into fact."
                ),
                [
                    "historical_opportunities",
                ],
            ),
        ],

        "invariants": {
            "carbon_owns_simulation":
                True,

            "oriel_projects_reachability":
                True,

            "immutable_commitments_are_not_moved":
                True,

            (
                "maximum_travel_time_is_used_"
                "for_guaranteed_reachability"
            ):
                True,

            "absence_of_evidence_is_not_availability":
                True,

            (
                "historical_opportunity_is_not_"
                "historical_interaction"
            ):
                True,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        },
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "carbon_owned":
            True,

        "physical_states":
            sorted(
                physical_states
            ),

        "reality_states":
            sorted(
                reality_states
            ),

        "conservative_travel_envelope":
            "maximum_minutes",

        "future_anchor_behavior":
            (
                "earliest immutable arrival "
                "deadline wins"
            ),

        "absence_of_evidence_is_availability":
            False,

        "enhancement_count":
            len(
                enhancements
            ),

        "enhancements":
            list(
                enhancements
            ),

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

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
            {
                "id":
                    "gamma",

                "name":
                    "gamma",

                "latitude":
                    42.0,

                "longitude":
                    -73.0,

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
                    90,

                "maximum_minutes":
                    120,

                "source_class":
                    "verified_external",
            },
            {
                "source":
                    "beta",

                "target":
                    "gamma",

                "mode":
                    "tour_bus",

                "distance_km":
                    260,

                "minimum_minutes":
                    150,

                "maximum_minutes":
                    180,

                "source_class":
                    "verified_external",
            },
        ],

        "events": [
            {
                "id":
                    "current-scene",

                "kind":
                    "scene",

                "entities": [
                    "band"
                ],

                "location_id":
                    "alpha",

                "start":
                    (
                        "2026-01-01"
                        "T09:00:00-05:00"
                    ),

                "duration_minutes":
                    120,

                "source_class":
                    "simulation",
            },
            {
                "id":
                    "locked-show",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "gamma",

                "start":
                    (
                        "2026-01-01"
                        "T20:00:00-05:00"
                    ),

                "duration_minutes":
                    120,

                "source_class":
                    "verified_external",

                "metadata": {
                    "locked":
                        True,
                },
            },
        ],
    }

    facts = [
        {
            "id":
                "beta-open",

            "kind":
                "venue-availability",

            "effect":
                "available",

            "location_id":
                "beta",

            "start":
                (
                    "2026-01-01"
                    "T11:00:00-05:00"
                ),

            "end":
                (
                    "2026-01-01"
                    "T18:00:00-05:00"
                ),

            "source_class":
                "verified_external",

            "verification_state":
                "verified",

            "source_refs": [
                "focused-test:beta-open"
            ],
        },
    ]

    cone = engine.reachability(
        document,
        facts,
        entity=
            "band",
        timestamp=
            (
                "2026-01-01"
                "T10:00:00-05:00"
            ),
        duration_minutes=
            60,
        candidate_locations=[
            "alpha",
            "beta",
            "gamma",
        ],
    )

    index = {
        value[
            "location_id"
        ]:
            value
        for value
        in cone[
            "candidates"
        ]
    }

    beta = index[
        "beta"
    ]

    if (
        beta[
            "physical_state"
        ]
        != "reachable"
    ):
        raise oriel_horizon_error(
            (
                "selftest failed to "
                "reach beta"
            )
        )

    if (
        beta[
            "reality_state"
        ]
        != "verified_available"
    ):
        raise oriel_horizon_error(
            (
                "selftest failed to preserve "
                "verified availability"
            )
        )

    if (
        cone[
            "next_immutable_anchor"
        ][
            "id"
        ]
        != "locked-show"
    ):
        raise oriel_horizon_error(
            (
                "selftest selected wrong "
                "immutable anchor"
            )
        )

    if (
        cone[
            "point_of_no_return"
        ]
        is None
    ):
        raise oriel_horizon_error(
            (
                "selftest failed to "
                "calculate point of no return"
            )
        )

    frontier = engine.frontier(
        cone
    )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "anchor":
            cone[
                "next_immutable_anchor"
            ][
                "id"
            ],

        "point_of_no_return":
            cone[
                "point_of_no_return"
            ],

        "direct_anchor_slack_minutes":
            cone[
                "direct_anchor_slack_minutes"
            ],

        "beta_reachable":
            True,

        "beta_verified_available":
            True,

        "beta_available_minutes":
            beta[
                "available_minutes"
            ],

        "frontier_count":
            frontier[
                "frontier_count"
            ],

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,
    }


__all__ = [
    "OrielHorizonEngine",
    "capability_manifest",
    "engine",
    "selftest",
    "status",
]
