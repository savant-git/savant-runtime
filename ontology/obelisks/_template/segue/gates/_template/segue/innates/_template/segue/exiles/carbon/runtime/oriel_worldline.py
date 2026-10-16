#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from oriel import (
    oriel_engine,
    parse_datetime,
    to_utc,
)

from oriel_simulation import (
    engine as simulation_engine,
)


owner = "carbon"
component = "oriel-worldline"
authority_effect = "none"
schema = "savant.carbon.oriel-worldline.v1"

segment_states = {
    "stationary",
    "stationary-gap",
    "travel",
    "unresolved-travel",
    "impossible-transition",
}

enhancements = (
    "continuous entity worldlines",
    "reality-bound worldline compilation",
    "stationary event segments",
    "same-location dwell segments",
    "travel transition segments",
    "unresolved travel segments",
    "impossible transition marking",
    "minimum travel envelope projection",
    "maximum travel envelope projection",
    "route lineage preservation",
    "event lineage preservation",
    "temporal uncertainty preservation",
    "entity chronology inversion",
    "location occupancy inversion",
    "interval occupant queries",
    "exact position delegation",
    "worldline segment lookup",
    "worldline intersection discovery",
    "co-location interval discovery",
    "unknown chronology gap discovery",
    "continuity coverage metrics",
    "transition slack projection",
    "travel reserve projection",
    "immutable-anchor marking",
    "source-class preservation",
    "multi-entity worldline atlas",
    "deterministic worldline identity",
    "deterministic atlas identity",
    "deterministic intersection identity",
    "replay-stable segment ordering",
    "source-state immutability",
    "canon-neutral projection",
    "evidence-neutral projection",
    "filament-projectable worldlines",
    "modus-maskable worldline metadata",
)


class oriel_worldline_error(
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


def utc(
    value: Any,
) -> datetime:
    if isinstance(
        value,
        datetime,
    ):
        return to_utc(
            value
        )

    return to_utc(
        parse_datetime(
            value
        )
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


def overlap(
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> tuple[
    datetime,
    datetime,
] | None:
    start = max(
        to_utc(
            left_start
        ),
        to_utc(
            right_start
        ),
    )

    end = min(
        to_utc(
            left_end
        ),
        to_utc(
            right_end
        ),
    )

    if end < start:
        return None

    return (
        start,
        end,
    )


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


def segment_bounds(
    value: Mapping[
        str,
        Any,
    ],
) -> tuple[
    datetime,
    datetime,
]:
    return (
        utc(
            value[
                "start"
            ]
        ),
        utc(
            value[
                "end"
            ]
        ),
    )


def segment_duration(
    value: Mapping[
        str,
        Any,
    ],
) -> float:
    start, end = segment_bounds(
        value
    )

    return max(
        0.0,
        minutes_between(
            start,
            end,
        ),
    )


def entity_ids(
    document: Mapping[
        str,
        Any,
    ],
) -> list[str]:
    return sorted(
        {
            str(
                entity
            )
            for value
            in document.get(
                "events",
                [],
            )
            if isinstance(
                value,
                Mapping,
            )
            for entity
            in value.get(
                "entities",
                [],
            )
            if str(
                entity
            ).strip()
        }
    )


def make_segment(
    *,
    entity: str,
    state: str,
    start: datetime,
    end: datetime,
    location_id: str | None = None,
    source_location_id: str | None = None,
    target_location_id: str | None = None,
    event_id: str | None = None,
    next_event_id: str | None = None,
    source_class: str = "derived",
    locked: bool = False,
    travel: Mapping[
        str,
        Any,
    ]
    | None = None,
    metadata: Mapping[
        str,
        Any,
    ]
    | None = None,
) -> dict[str, Any]:
    if state not in segment_states:
        raise oriel_worldline_error(
            (
                "unsupported segment state: "
                + state
            )
        )

    start_utc = to_utc(
        start
    )

    end_utc = to_utc(
        end
    )

    if end_utc < start_utc:
        raise oriel_worldline_error(
            (
                "worldline segment ends "
                "before it starts"
            )
        )

    result = {
        "entity":
            entity,

        "state":
            state,

        "start":
            start_utc.isoformat(),

        "end":
            end_utc.isoformat(),

        "duration_minutes":
            round(
                minutes_between(
                    start_utc,
                    end_utc,
                ),
                6,
            ),

        "location_id":
            location_id,

        "source_location_id":
            source_location_id,

        "target_location_id":
            target_location_id,

        "event_id":
            event_id,

        "next_event_id":
            next_event_id,

        "source_class":
            source_class,

        "locked":
            bool(
                locked
            ),

        "travel":
            clone(
                travel
            ),

        "metadata":
            clone(
                dict(
                    metadata
                    or {}
                )
            ),

        "authority_effect":
            "none",
    }

    result[
        "id"
    ] = stable_id(
        "carbon-oriel-worldline-segment",
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "id"
        },
    )

    result[
        "digest"
    ] = digest(
        result
    )

    return result


class OrielWorldlineEngine:
    def build(
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
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        world = (
            simulation_engine.compile_world(
                document,
                facts,
            )
        )

        bound_document = world[
            "bound_document"
        ]

        engine = oriel_engine.from_document(
            bound_document
        )

        raw = raw_event_index(
            bound_document
        )

        events = sorted(
            [
                value
                for value
                in engine.events.values()
                if entity
                in value.entities
            ],
            key=lambda value: (
                to_utc(
                    value.start.earliest
                ),
                value.id,
            ),
        )

        if not events:
            raise oriel_worldline_error(
                (
                    "entity has no chronology: "
                    + entity
                )
            )

        segments = []

        for index, value in enumerate(
            events
        ):
            source = raw.get(
                value.id,
                {},
            )

            event_start = to_utc(
                value.start.earliest
            )

            event_end = to_utc(
                value.end.latest
            )

            segments.append(
                make_segment(
                    entity=
                        entity,
                    state=
                        "stationary",
                    start=
                        event_start,
                    end=
                        event_end,
                    location_id=
                        value.location_id,
                    event_id=
                        value.id,
                    source_class=
                        value.source_class,
                    locked=
                        event_locked(
                            source
                        ),
                    metadata={
                        "kind":
                            value.kind,

                        "start_window":
                            value.start
                            .projection(),

                        "end_window":
                            value.end
                            .projection(),

                        "resources":
                            list(
                                value.resources
                            ),
                    },
                )
            )

            if (
                index
                >= len(
                    events
                )
                - 1
            ):
                continue

            next_value = events[
                index
                + 1
            ]

            next_start = to_utc(
                next_value.start.earliest
            )

            gap_minutes = minutes_between(
                event_end,
                next_start,
            )

            if gap_minutes < 0:
                segments.append(
                    make_segment(
                        entity=
                            entity,
                        state=
                            "impossible-transition",
                        start=
                            next_start,
                        end=
                            event_end,
                        source_location_id=
                            value.location_id,
                        target_location_id=
                            next_value.location_id,
                        event_id=
                            value.id,
                        next_event_id=
                            next_value.id,
                        source_class=
                            "derived",
                        metadata={
                            "reason":
                                (
                                    "events overlap "
                                    "in chronology"
                                ),

                            "overlap_minutes":
                                round(
                                    abs(
                                        gap_minutes
                                    ),
                                    6,
                                ),
                        },
                    )
                )

                continue

            if (
                value.location_id
                == next_value.location_id
            ):
                if gap_minutes > 0:
                    segments.append(
                        make_segment(
                            entity=
                                entity,
                            state=
                                "stationary-gap",
                            start=
                                event_end,
                            end=
                                next_start,
                            location_id=
                                value.location_id,
                            event_id=
                                value.id,
                            next_event_id=
                                next_value.id,
                            source_class=
                                "derived",
                            metadata={
                                "continuity":
                                    "same-location",
                            },
                        )
                    )

                continue

            travel = engine.travel(
                value.location_id,
                next_value.location_id,
                mode=mode,
            )

            if (
                travel.get(
                    "outcome"
                )
                == "unknown"
            ):
                segments.append(
                    make_segment(
                        entity=
                            entity,
                        state=
                            "unresolved-travel",
                        start=
                            event_end,
                        end=
                            next_start,
                        source_location_id=
                            value.location_id,
                        target_location_id=
                            next_value.location_id,
                        event_id=
                            value.id,
                        next_event_id=
                            next_value.id,
                        source_class=
                            "derived",
                        travel=
                            travel,
                        metadata={
                            "available_minutes":
                                round(
                                    gap_minutes,
                                    6,
                                ),

                            "reason":
                                (
                                    "travel duration "
                                    "is unresolved"
                                ),
                        },
                    )
                )

                continue

            minimum = int(
                travel[
                    "minimum_minutes"
                ]
            )

            maximum = int(
                travel[
                    "maximum_minutes"
                ]
            )

            if gap_minutes < minimum:
                segments.append(
                    make_segment(
                        entity=
                            entity,
                        state=
                            "impossible-transition",
                        start=
                            event_end,
                        end=
                            next_start,
                        source_location_id=
                            value.location_id,
                        target_location_id=
                            next_value.location_id,
                        event_id=
                            value.id,
                        next_event_id=
                            next_value.id,
                        source_class=
                            "derived",
                        travel=
                            travel,
                        metadata={
                            "available_minutes":
                                round(
                                    gap_minutes,
                                    6,
                                ),

                            "minimum_required_minutes":
                                minimum,

                            "shortfall_minutes":
                                round(
                                    minimum
                                    - gap_minutes,
                                    6,
                                ),

                            "reason":
                                (
                                    "available interval "
                                    "is shorter than "
                                    "minimum travel time"
                                ),
                        },
                    )
                )

                continue

            travel_end = min(
                next_start,
                (
                    event_end
                    + timedelta(
                        minutes=
                            maximum
                    )
                ),
            )

            segments.append(
                make_segment(
                    entity=
                        entity,
                    state=
                        "travel",
                    start=
                        event_end,
                    end=
                        travel_end,
                    source_location_id=
                        value.location_id,
                    target_location_id=
                        next_value.location_id,
                    event_id=
                        value.id,
                    next_event_id=
                        next_value.id,
                    source_class=
                        str(
                            travel.get(
                                "source_class",
                                "derived",
                            )
                        ),
                    travel=
                        travel,
                    metadata={
                        "minimum_travel_minutes":
                            minimum,

                        "maximum_travel_minutes":
                            maximum,

                        "available_minutes":
                            round(
                                gap_minutes,
                                6,
                            ),

                        "reserve_minutes":
                            round(
                                gap_minutes
                                - maximum,
                                6,
                            ),

                        "arrival_envelope": {
                            "earliest":
                                (
                                    event_end
                                    + timedelta(
                                        minutes=
                                            minimum
                                    )
                                ).isoformat(),

                            "latest":
                                (
                                    event_end
                                    + timedelta(
                                        minutes=
                                            maximum
                                    )
                                ).isoformat(),
                        },
                    },
                )
            )

            if travel_end < next_start:
                segments.append(
                    make_segment(
                        entity=
                            entity,
                        state=
                            "stationary-gap",
                        start=
                            travel_end,
                        end=
                            next_start,
                        location_id=
                            next_value.location_id,
                        event_id=
                            value.id,
                        next_event_id=
                            next_value.id,
                        source_class=
                            "derived",
                        metadata={
                            "continuity":
                                (
                                    "post-travel "
                                    "arrival reserve"
                                ),
                        },
                    )
                )

        segments = sorted(
            segments,
            key=lambda value: (
                value[
                    "start"
                ],
                value[
                    "end"
                ],
                value[
                    "id"
                ],
            ),
        )

        unknown_segments = [
            value
            for value
            in segments
            if value[
                "state"
            ]
            in {
                "unresolved-travel",
                "impossible-transition",
            }
        ]

        total_minutes = sum(
            segment_duration(
                value
            )
            for value
            in segments
        )

        unresolved_minutes = sum(
            segment_duration(
                value
            )
            for value
            in unknown_segments
        )

        known_minutes = max(
            0.0,
            total_minutes
            - unresolved_minutes,
        )

        coverage = (
            (
                known_minutes
                / total_minutes
            )
            if total_minutes > 0
            else 1.0
        )

        result = {
            "schema":
                schema,

            "kind":
                "entity-worldline",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "world_id":
                world[
                    "id"
                ],

            "entity":
                entity,

            "mode":
                mode,

            "event_count":
                len(
                    events
                ),

            "segment_count":
                len(
                    segments
                ),

            "segments":
                segments,

            "start":
                (
                    segments[
                        0
                    ][
                        "start"
                    ]
                    if segments
                    else None
                ),

            "end":
                (
                    segments[
                        -1
                    ][
                        "end"
                    ]
                    if segments
                    else None
                ),

            "total_projected_minutes":
                round(
                    total_minutes,
                    6,
                ),

            "known_minutes":
                round(
                    known_minutes,
                    6,
                ),

            "unresolved_minutes":
                round(
                    unresolved_minutes,
                    6,
                ),

            "continuity_coverage":
                round(
                    coverage,
                    9,
                ),

            "unresolved_segment_count":
                len(
                    unknown_segments
                ),

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        }

        result[
            "id"
        ] = stable_id(
            "carbon-oriel-worldline",
            {
                "world_id":
                    world[
                        "id"
                    ],

                "entity":
                    entity,

                "mode":
                    mode,

                "segment_digests": [
                    value[
                        "digest"
                    ]
                    for value
                    in segments
                ],
            },
        )

        result[
            "digest"
        ] = digest(
            {
                key:
                    value
                for key, value
                in result.items()
                if key
                != "digest"
            }
        )

        return result

    def atlas(
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
        entities:
            Sequence[str] = (),
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        selected = (
            sorted(
                {
                    str(
                        value
                    ).strip()
                    for value
                    in entities
                    if str(
                        value
                    ).strip()
                }
            )
            if entities
            else entity_ids(
                document
            )
        )

        worldlines = []

        for entity in selected:
            try:
                worldlines.append(
                    self.build(
                        document,
                        facts,
                        entity=
                            entity,
                        mode=
                            mode,
                    )
                )

            except oriel_worldline_error:
                continue

        result = {
            "schema":
                schema,

            "kind":
                "worldline-atlas",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "mode":
                mode,

            "entity_count":
                len(
                    worldlines
                ),

            "entities": [
                value[
                    "entity"
                ]
                for value
                in worldlines
            ],

            "worldlines":
                worldlines,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",

            "evidence_admission":
                False,
        }

        result[
            "id"
        ] = stable_id(
            "carbon-oriel-worldline-atlas",
            {
                "mode":
                    mode,

                "worldlines": [
                    value[
                        "id"
                    ]
                    for value
                    in worldlines
                ],
            },
        )

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def locate(
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
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        world = (
            simulation_engine.compile_world(
                document,
                facts,
            )
        )

        position = (
            oriel_engine.from_document(
                world[
                    "bound_document"
                ]
            ).position_at(
                entity,
                timestamp,
                mode=mode,
            )
        )

        line = self.build(
            document,
            facts,
            entity=entity,
            mode=mode,
        )

        at = utc(
            timestamp
        )

        matching = []

        for value in line[
            "segments"
        ]:
            start, end = segment_bounds(
                value
            )

            if (
                start
                <= at
                <= end
            ):
                matching.append(
                    value
                )

        return {
            "schema":
                schema,

            "kind":
                "worldline-location",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "entity":
                entity,

            "timestamp":
                at.isoformat(),

            "worldline_id":
                line[
                    "id"
                ],

            "position":
                position,

            "matching_segments":
                matching,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",
        }

    def occupants(
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
        location_id: str,
        start: Any,
        end: Any,
        entities:
            Sequence[str] = (),
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        query_start = utc(
            start
        )

        query_end = utc(
            end
        )

        if query_end < query_start:
            raise oriel_worldline_error(
                (
                    "occupancy query ends "
                    "before it starts"
                )
            )

        atlas = self.atlas(
            document,
            facts,
            entities=
                entities,
            mode=
                mode,
        )

        matches = []

        for line in atlas[
            "worldlines"
        ]:
            for value in line[
                "segments"
            ]:
                if value[
                    "state"
                ] not in {
                    "stationary",
                    "stationary-gap",
                }:
                    continue

                if (
                    value.get(
                        "location_id"
                    )
                    != location_id
                ):
                    continue

                start_value, end_value = (
                    segment_bounds(
                        value
                    )
                )

                intersection = overlap(
                    start_value,
                    end_value,
                    query_start,
                    query_end,
                )

                if intersection is None:
                    continue

                matches.append(
                    {
                        "entity":
                            line[
                                "entity"
                            ],

                        "worldline_id":
                            line[
                                "id"
                            ],

                        "segment_id":
                            value[
                                "id"
                            ],

                        "state":
                            value[
                                "state"
                            ],

                        "event_id":
                            value.get(
                                "event_id"
                            ),

                        "earliest":
                            intersection[
                                0
                            ].isoformat(),

                        "latest":
                            intersection[
                                1
                            ].isoformat(),

                        "overlap_minutes":
                            round(
                                minutes_between(
                                    intersection[
                                        0
                                    ],
                                    intersection[
                                        1
                                    ],
                                ),
                                6,
                            ),

                        "source_class":
                            value.get(
                                "source_class"
                            ),

                        "locked":
                            value.get(
                                "locked",
                                False,
                            ),
                    }
                )

        result = {
            "schema":
                schema,

            "kind":
                "location-occupancy",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "location_id":
                location_id,

            "start":
                query_start.isoformat(),

            "end":
                query_end.isoformat(),

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
                            "entity"
                        ],
                    ),
                ),

            "absence_of_match_is_presence_proof":
                False,

            "source_state_mutated":
                False,

            "canon_effect":
                "none",
        }

        result[
            "id"
        ] = stable_id(
            "carbon-oriel-occupancy",
            result,
        )

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def intersections(
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
        left_entity: str,
        right_entity: str,
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        left = self.build(
            document,
            facts,
            entity=
                left_entity,
            mode=
                mode,
        )

        right = self.build(
            document,
            facts,
            entity=
                right_entity,
            mode=
                mode,
        )

        matches = []

        left_segments = [
            value
            for value
            in left[
                "segments"
            ]
            if value[
                "state"
            ]
            in {
                "stationary",
                "stationary-gap",
            }
        ]

        right_segments = [
            value
            for value
            in right[
                "segments"
            ]
            if value[
                "state"
            ]
            in {
                "stationary",
                "stationary-gap",
            }
        ]

        for left_value in left_segments:
            location_id = (
                left_value.get(
                    "location_id"
                )
            )

            if not location_id:
                continue

            left_start, left_end = (
                segment_bounds(
                    left_value
                )
            )

            for right_value in right_segments:
                if (
                    right_value.get(
                        "location_id"
                    )
                    != location_id
                ):
                    continue

                right_start, right_end = (
                    segment_bounds(
                        right_value
                    )
                )

                intersection = overlap(
                    left_start,
                    left_end,
                    right_start,
                    right_end,
                )

                if intersection is None:
                    continue

                matches.append(
                    {
                        "location_id":
                            location_id,

                        "earliest":
                            intersection[
                                0
                            ].isoformat(),

                        "latest":
                            intersection[
                                1
                            ].isoformat(),

                        "overlap_minutes":
                            round(
                                minutes_between(
                                    intersection[
                                        0
                                    ],
                                    intersection[
                                        1
                                    ],
                                ),
                                6,
                            ),

                        "left_segment":
                            left_value[
                                "id"
                            ],

                        "right_segment":
                            right_value[
                                "id"
                            ],

                        "left_event":
                            left_value.get(
                                "event_id"
                            ),

                        "right_event":
                            right_value.get(
                                "event_id"
                            ),

                        "interaction_is_fact":
                            False,

                        "co_location_is_projection":
                            True,
                    }
                )

        result = {
            "schema":
                schema,

            "kind":
                "worldline-intersections",

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
                "worldline-intersections"
            ),
            result,
        )

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def gaps(
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
        mode: str = "tour_bus",
    ) -> dict[str, Any]:
        line = self.build(
            document,
            facts,
            entity=
                entity,
            mode=
                mode,
        )

        values = [
            clone(
                value
            )
            for value
            in line[
                "segments"
            ]
            if value[
                "state"
            ]
            in {
                "unresolved-travel",
                "impossible-transition",
            }
        ]

        return {
            "schema":
                schema,

            "kind":
                "worldline-gaps",

            "owner":
                owner,

            "component":
                component,

            "authority_effect":
                authority_effect,

            "entity":
                entity,

            "worldline_id":
                line[
                    "id"
                ],

            "gap_count":
                len(
                    values
                ),

            "gaps":
                values,

            "continuity_coverage":
                line[
                    "continuity_coverage"
                ],

            "source_state_mutated":
                False,

            "canon_effect":
                "none",
        }


engine = OrielWorldlineEngine()


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
                "savant.carbon.oriel-worldline."
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
                "oriel_entity_worldline",
                "chronometric-projection",
                (
                    "Materialize one continuous "
                    "reality-bound chronology for "
                    "an entity from stationary events, "
                    "travel and unresolved transitions."
                ),
                [
                    "build",
                    "locate",
                    "gaps",
                ],
            ),

            capability(
                "oriel_worldline_atlas",
                "chronometric-composition",
                (
                    "Compose multiple entity "
                    "worldlines into one deterministic "
                    "spacetime atlas."
                ),
                [
                    "atlas",
                ],
            ),

            capability(
                "oriel_inverse_occupancy",
                "spacetime-query",
                (
                    "Invert chronology to determine "
                    "which entity worldlines occupy "
                    "a location during an interval."
                ),
                [
                    "occupants",
                ],
            ),

            capability(
                "oriel_worldline_intersection",
                "spacetime-analysis",
                (
                    "Discover projected co-location "
                    "intervals between entity "
                    "worldlines without asserting "
                    "interaction as fact."
                ),
                [
                    "intersections",
                ],
            ),

            capability(
                "oriel_chronology_gap_projection",
                "epistemic",
                (
                    "Expose unresolved and impossible "
                    "transitions in an entity worldline "
                    "instead of fabricating continuity."
                ),
                [
                    "gaps",
                ],
            ),
        ],

        "invariants": {
            "carbon_owns_simulation":
                True,

            "oriel_projects_worldlines":
                True,

            "unresolved_travel_remains_unresolved":
                True,

            "co_location_is_not_interaction":
                True,

            "absence_of_occupancy_match_is_not_proof":
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

        "segment_states":
            sorted(
                segment_states
            ),

        "reality_bound":
            True,

        "continuous_projection":
            True,

        "inverse_occupancy":
            True,

        "intersection_projection":
            True,

        "unknown_preservation":
            True,

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
        ],

        "events": [
            {
                "id":
                    "band-alpha",

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
                        "T10:00:00-05:00"
                    ),

                "duration_minutes":
                    60,

                "source_class":
                    "simulation",
            },
            {
                "id":
                    "band-beta",

                "kind":
                    "show",

                "entities": [
                    "band"
                ],

                "location_id":
                    "beta",

                "start":
                    (
                        "2026-01-01"
                        "T14:00:00-05:00"
                    ),

                "duration_minutes":
                    120,

                "source_class":
                    "simulation",
            },
            {
                "id":
                    "guest-beta",

                "kind":
                    "scene",

                "entities": [
                    "guest"
                ],

                "location_id":
                    "beta",

                "start":
                    (
                        "2026-01-01"
                        "T14:30:00-05:00"
                    ),

                "duration_minutes":
                    30,

                "source_class":
                    "simulation",
            },
        ],
    }

    line = engine.build(
        document,
        [],
        entity=
            "band",
    )

    if not any(
        value[
            "state"
        ]
        == "travel"
        for value
        in line[
            "segments"
        ]
    ):
        raise oriel_worldline_error(
            (
                "selftest failed to "
                "materialize travel segment"
            )
        )

    occupancy = engine.occupants(
        document,
        [],
        location_id=
            "beta",
        start=(
            "2026-01-01"
            "T14:30:00-05:00"
        ),
        end=(
            "2026-01-01"
            "T15:00:00-05:00"
        ),
    )

    occupants = {
        value[
            "entity"
        ]
        for value
        in occupancy[
            "matches"
        ]
    }

    if not {
        "band",
        "guest",
    }.issubset(
        occupants
    ):
        raise oriel_worldline_error(
            (
                "selftest failed inverse "
                "occupancy query"
            )
        )

    intersections = (
        engine.intersections(
            document,
            [],
            left_entity=
                "band",
            right_entity=
                "guest",
        )
    )

    if (
        intersections[
            "match_count"
        ]
        < 1
    ):
        raise oriel_worldline_error(
            (
                "selftest failed worldline "
                "intersection query"
            )
        )

    gaps = engine.gaps(
        document,
        [],
        entity=
            "band",
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

        "travel_segment_materialized":
            True,

        "inverse_occupancy_found_band":
            True,

        "inverse_occupancy_found_guest":
            True,

        "worldline_intersection_found":
            True,

        "band_segment_count":
            line[
                "segment_count"
            ],

        "band_continuity_coverage":
            line[
                "continuity_coverage"
            ],

        "band_gap_count":
            gaps[
                "gap_count"
            ],

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,
    }


__all__ = [
    "OrielWorldlineEngine",
    "capability_manifest",
    "engine",
    "selftest",
    "status",
]
