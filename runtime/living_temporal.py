#!/usr/bin/env python3

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence


from runtime.living_governance import (
    projection_digest,
    read_events,
)


owner = "living-governance"
authority_effect = "none"

inactive_statuses = {
    "inactive",
    "superseded",
    "withdrawn",
}


class living_temporal_error(
    RuntimeError
):
    pass


def _canonical_time(
    value: Any,
) -> datetime | None:
    if value is None:
        return None

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
            return None

        if text.endswith(
            "Z"
        ):
            text = (
                text[
                    :-1
                ]
                + "+00:00"
            )

        try:
            parsed = datetime.fromisoformat(
                text
            )

        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def _event_sequence(
    event: Mapping[str, Any],
) -> int:
    value = event.get(
        "sequence",
        event.get(
            "seq",
            0,
        ),
    )

    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0


def _event_time(
    event: Mapping[str, Any],
) -> datetime | None:
    for key in (
        "asserted_at",
        "timestamp",
        "created_at",
    ):
        parsed = _canonical_time(
            event.get(
                key
            )
        )

        if parsed is not None:
            return parsed

    record = event.get(
        "record"
    )

    if isinstance(
        record,
        Mapping,
    ):
        provenance = record.get(
            "provenance"
        )

        if isinstance(
            provenance,
            Mapping,
        ):
            parsed = _canonical_time(
                provenance.get(
                    "created_at"
                )
            )

            if parsed is not None:
                return parsed

    return None


def _clean_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        str(key):
            value
        for key, value
        in record.items()
        if not str(
            key
        ).startswith(
            "_"
        )
    }


def _event_record(
    event: Mapping[str, Any],
) -> dict[str, Any] | None:
    record = event.get(
        "record"
    )

    if not isinstance(
        record,
        Mapping,
    ):
        return None

    value = dict(
        record
    )

    value[
        "_event_sequence"
    ] = _event_sequence(
        event
    )

    event_time = _event_time(
        event
    )

    if event_time is not None:
        value[
            "_event_time"
        ] = event_time.isoformat()

    return value


def resolve_events(
    events: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> tuple[
    dict[
        str,
        Any,
    ],
    ...,
]:
    grouped: dict[
        tuple[
            str,
            str,
        ],
        list[
            dict[
                str,
                Any,
            ]
        ],
    ] = defaultdict(
        list
    )

    for event in events:
        record = _event_record(
            event
        )

        if record is None:
            continue

        stream = str(
            record.get(
                "stream",
                "",
            )
        )

        semantic_id = str(
            record.get(
                "id",
                "",
            )
        )

        if (
            not stream
            or not semantic_id
        ):
            continue

        grouped[
            (
                stream,
                semantic_id,
            )
        ].append(
            record
        )

    resolved = []

    for _, values in grouped.items():
        best_rank = min(
            int(
                value.get(
                    "authority_rank",
                    1000,
                )
            )
            for value
            in values
        )

        strongest = [
            value
            for value
            in values
            if int(
                value.get(
                    "authority_rank",
                    1000,
                )
            )
            == best_rank
        ]

        highest_version = max(
            int(
                value.get(
                    "version",
                    0,
                )
            )
            for value
            in strongest
        )

        latest_version = [
            value
            for value
            in strongest
            if int(
                value.get(
                    "version",
                    0,
                )
            )
            == highest_version
        ]

        selected = max(
            latest_version,
            key=lambda item: int(
                item.get(
                    "_event_sequence",
                    0,
                )
            ),
        )

        if str(
            selected.get(
                "status",
                "active",
            )
        ).strip().lower() in inactive_statuses:
            continue

        resolved.append(
            selected
        )

    return tuple(
        sorted(
            resolved,
            key=lambda item: (
                str(
                    item.get(
                        "stream",
                        "",
                    )
                ),
                int(
                    item.get(
                        "priority",
                        1000,
                    )
                ),
                str(
                    item.get(
                        "id",
                        "",
                    )
                ),
            ),
        )
    )


def _state_payload(
    records: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
    *,
    boundary: Mapping[str, Any],
    complete: bool = True,
    unresolved_events: Sequence[
        Mapping[
            str,
            Any,
        ]
    ] = (),
) -> dict[str, Any]:
    clean = [
        _clean_record(
            record
        )
        for record
        in records
    ]

    return {
        "schema":
            "savant.living-governance.state.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "projection_only":
            True,

        "complete":
            complete,

        "boundary":
            dict(
                boundary
            ),

        "record_count":
            len(
                clean
            ),

        "digest":
            projection_digest(
                clean
            ),

        "unresolved_event_count":
            len(
                unresolved_events
            ),

        "unresolved_events":
            [
                dict(
                    value
                )
                for value
                in unresolved_events
            ],

        "records":
            clean,
    }


def current_state() -> dict[str, Any]:
    events = read_events()

    records = resolve_events(
        events
    )

    highest_sequence = max(
        (
            _event_sequence(
                event
            )
            for event
            in events
        ),
        default=0,
    )

    return _state_payload(
        records,
        boundary={
            "kind":
                "current",

            "sequence":
                highest_sequence,
        },
    )


def state_at_sequence(
    sequence: int,
) -> dict[str, Any]:
    if sequence < 0:
        raise living_temporal_error(
            "sequence must be non-negative"
        )

    events = [
        event
        for event
        in read_events()
        if _event_sequence(
            event
        )
        <= sequence
    ]

    records = resolve_events(
        events
    )

    return _state_payload(
        records,
        boundary={
            "kind":
                "sequence",

            "sequence":
                sequence,
        },
    )


def state_at_timestamp(
    timestamp: str | datetime,
) -> dict[str, Any]:
    boundary = _canonical_time(
        timestamp
    )

    if boundary is None:
        raise living_temporal_error(
            "timestamp is invalid"
        )

    included = []

    unresolved = []

    for event in read_events():
        event_time = _event_time(
            event
        )

        if event_time is None:
            unresolved.append(
                {
                    "sequence":
                        _event_sequence(
                            event
                        ),

                    "reason":
                        "event timestamp unavailable",
                }
            )

            continue

        if event_time <= boundary:
            included.append(
                event
            )

    records = resolve_events(
        included
    )

    return _state_payload(
        records,
        boundary={
            "kind":
                "timestamp",

            "timestamp":
                boundary.isoformat(),
        },
        complete=not unresolved,
        unresolved_events=unresolved,
    )


def _record_index(
    state: Mapping[str, Any],
) -> dict[
    tuple[
        str,
        str,
    ],
    dict[
        str,
        Any,
    ],
]:
    index = {}

    records = state.get(
        "records",
        []
    )

    if not isinstance(
        records,
        list,
    ):
        return index

    for record in records:
        if not isinstance(
            record,
            Mapping,
        ):
            continue

        key = (
            str(
                record.get(
                    "stream",
                    "",
                )
            ),
            str(
                record.get(
                    "id",
                    "",
                )
            ),
        )

        if all(
            key
        ):
            index[
                key
            ] = dict(
                record
            )

    return index


def _field_delta(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    keys = sorted(
        set(
            before
        )
        | set(
            after
        )
    )

    changes = {}

    for key in keys:
        old = before.get(
            key
        )

        new = after.get(
            key
        )

        if old == new:
            continue

        changes[
            key
        ] = {
            "before":
                old,

            "after":
                new,
        }

    return changes


def diff_states(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    before_index = _record_index(
        before
    )

    after_index = _record_index(
        after
    )

    added = []

    removed = []

    changed = []

    for key in sorted(
        set(
            before_index
        )
        | set(
            after_index
        )
    ):
        old = before_index.get(
            key
        )

        new = after_index.get(
            key
        )

        stream, semantic_id = key

        if old is None:
            added.append(
                {
                    "stream":
                        stream,

                    "id":
                        semantic_id,

                    "record":
                        new,
                }
            )

            continue

        if new is None:
            removed.append(
                {
                    "stream":
                        stream,

                    "id":
                        semantic_id,

                    "record":
                        old,
                }
            )

            continue

        delta = _field_delta(
            old,
            new,
        )

        if delta:
            changed.append(
                {
                    "stream":
                        stream,

                    "id":
                        semantic_id,

                    "fields":
                        delta,
                }
            )

    return {
        "schema":
            "savant.living-governance.state-diff.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "projection_only":
            True,

        "before":
            before.get(
                "boundary"
            ),

        "after":
            after.get(
                "boundary"
            ),

        "before_digest":
            before.get(
                "digest"
            ),

        "after_digest":
            after.get(
                "digest"
            ),

        "complete":
            bool(
                before.get(
                    "complete",
                    True,
                )
                and after.get(
                    "complete",
                    True,
                )
            ),

        "added_count":
            len(
                added
            ),

        "removed_count":
            len(
                removed
            ),

        "changed_count":
            len(
                changed
            ),

        "added":
            added,

        "removed":
            removed,

        "changed":
            changed,
    }


def diff_sequences(
    before_sequence: int,
    after_sequence: int,
) -> dict[str, Any]:
    return diff_states(
        state_at_sequence(
            before_sequence
        ),
        state_at_sequence(
            after_sequence
        ),
    )


def diff_timestamps(
    before_timestamp: str,
    after_timestamp: str,
) -> dict[str, Any]:
    return diff_states(
        state_at_timestamp(
            before_timestamp
        ),
        state_at_timestamp(
            after_timestamp
        ),
    )


def supersession_trace(
    *,
    stream: str,
    semantic_id: str,
) -> dict[str, Any]:
    own_events = []

    inbound = []

    for event in read_events():
        record = event.get(
            "record"
        )

        if not isinstance(
            record,
            Mapping,
        ):
            continue

        record_stream = str(
            record.get(
                "stream",
                "",
            )
        )

        record_id = str(
            record.get(
                "id",
                "",
            )
        )

        if (
            record_stream == stream
            and record_id == semantic_id
        ):
            own_events.append(
                {
                    "sequence":
                        _event_sequence(
                            event
                        ),

                    "timestamp":
                        (
                            _event_time(
                                event
                            ).isoformat()
                            if _event_time(
                                event
                            )
                            is not None
                            else None
                        ),

                    "version":
                        record.get(
                            "version"
                        ),

                    "status":
                        record.get(
                            "status"
                        ),

                    "authority":
                        record.get(
                            "authority"
                        ),

                    "authority_rank":
                        record.get(
                            "authority_rank"
                        ),

                    "supersedes":
                        list(
                            record.get(
                                "supersedes",
                                [],
                            )
                        ),

                    "text":
                        record.get(
                            "text"
                        ),
                }
            )

        supersedes = record.get(
            "supersedes",
            []
        )

        if (
            isinstance(
                supersedes,
                list,
            )
            and semantic_id
            in {
                str(
                    value
                )
                for value
                in supersedes
            }
        ):
            inbound.append(
                {
                    "sequence":
                        _event_sequence(
                            event
                        ),

                    "stream":
                        record_stream,

                    "id":
                        record_id,

                    "version":
                        record.get(
                            "version"
                        ),

                    "status":
                        record.get(
                            "status"
                        ),

                    "authority":
                        record.get(
                            "authority"
                        ),
                }
            )

    return {
        "schema":
            "savant.living-governance.supersession-trace.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "projection_only":
            True,

        "stream":
            stream,

        "id":
            semantic_id,

        "history":
            sorted(
                own_events,
                key=lambda item: int(
                    item[
                        "sequence"
                    ]
                ),
            ),

        "superseded_by":
            sorted(
                inbound,
                key=lambda item: int(
                    item[
                        "sequence"
                    ]
                ),
            ),
    }


def _current_records() -> list[
    dict[
        str,
        Any,
    ]
]:
    return [
        _clean_record(
            record
        )
        for record
        in resolve_events(
            read_events()
        )
    ]


def reverse_dependencies(
    records: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[str, list[str]]:
    reverse: dict[
        str,
        list[
            str
        ],
    ] = defaultdict(
        list
    )

    for record in records:
        source = str(
            record.get(
                "id",
                "",
            )
        )

        if not source:
            continue

        for dependency in record.get(
            "dependencies",
            [],
        ):
            reverse[
                str(
                    dependency
                )
            ].append(
                source
            )

    return {
        key:
            sorted(
                set(
                    values
                )
            )
        for key, values
        in sorted(
            reverse.items()
        )
    }


def impact(
    semantic_id: str,
) -> dict[str, Any]:
    records = _current_records()

    index = {
        str(
            record.get(
                "id"
            )
        ):
            record
        for record
        in records
        if record.get(
            "id"
        )
    }

    if semantic_id not in index:
        raise living_temporal_error(
            (
                "unknown semantic id: "
                + semantic_id
            )
        )

    reverse = reverse_dependencies(
        records
    )

    queue = deque(
        [
            (
                semantic_id,
                0,
            )
        ]
    )

    visited = {
        semantic_id
    }

    affected = []

    while queue:
        current, depth = queue.popleft()

        for dependent in reverse.get(
            current,
            [],
        ):
            if dependent in visited:
                continue

            visited.add(
                dependent
            )

            record = index.get(
                dependent,
                {}
            )

            affected.append(
                {
                    "id":
                        dependent,

                    "stream":
                        record.get(
                            "stream"
                        ),

                    "depth":
                        depth + 1,

                    "status":
                        record.get(
                            "status"
                        ),

                    "authority":
                        record.get(
                            "authority"
                        ),

                    "text":
                        record.get(
                            "text"
                        ),
                }
            )

            queue.append(
                (
                    dependent,
                    depth + 1,
                )
            )

    return {
        "schema":
            "savant.living-governance.impact.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "projection_only":
            True,

        "id":
            semantic_id,

        "direct_dependents":
            reverse.get(
                semantic_id,
                [],
            ),

        "affected_count":
            len(
                affected
            ),

        "affected":
            sorted(
                affected,
                key=lambda item: (
                    int(
                        item[
                            "depth"
                        ]
                    ),
                    str(
                        item[
                            "id"
                        ]
                    ),
                ),
            ),
    }


def _dependency_adjacency(
    records: Sequence[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[str, list[str]]:
    ids = {
        str(
            record.get(
                "id"
            )
        )
        for record
        in records
        if record.get(
            "id"
        )
    }

    adjacency = {}

    for record in records:
        source = str(
            record.get(
                "id",
                "",
            )
        )

        if not source:
            continue

        adjacency[
            source
        ] = sorted(
            {
                str(
                    dependency
                )
                for dependency
                in record.get(
                    "dependencies",
                    [],
                )
                if str(
                    dependency
                )
                in ids
            }
        )

    return adjacency


def _strongly_connected_components(
    adjacency: Mapping[
        str,
        Sequence[
            str
        ],
    ],
) -> list[list[str]]:
    index = 0

    indexes: dict[
        str,
        int,
    ] = {}

    lowlinks: dict[
        str,
        int,
    ] = {}

    stack: list[str] = []

    on_stack: set[str] = set()

    components: list[
        list[
            str
        ]
    ] = []

    def visit(
        node: str,
    ) -> None:
        nonlocal index

        indexes[
            node
        ] = index

        lowlinks[
            node
        ] = index

        index += 1

        stack.append(
            node
        )

        on_stack.add(
            node
        )

        for target in adjacency.get(
            node,
            [],
        ):
            if target not in indexes:
                visit(
                    target
                )

                lowlinks[
                    node
                ] = min(
                    lowlinks[
                        node
                    ],
                    lowlinks[
                        target
                    ],
                )

            elif target in on_stack:
                lowlinks[
                    node
                ] = min(
                    lowlinks[
                        node
                    ],
                    indexes[
                        target
                    ],
                )

        if (
            lowlinks[
                node
            ]
            != indexes[
                node
            ]
        ):
            return

        component = []

        while stack:
            target = stack.pop()

            on_stack.remove(
                target
            )

            component.append(
                target
            )

            if target == node:
                break

        components.append(
            sorted(
                component
            )
        )

    for node in sorted(
        adjacency
    ):
        if node not in indexes:
            visit(
                node
            )

    return components


def classify_cycles() -> dict[str, Any]:
    records = _current_records()

    adjacency = _dependency_adjacency(
        records
    )

    components = _strongly_connected_components(
        adjacency
    )

    cycles = []

    for component in components:
        if len(
            component
        ) == 1:
            node = component[
                0
            ]

            if node not in adjacency.get(
                node,
                [],
            ):
                continue

            cycle_type = "self-cycle"

        else:
            cycle_type = "dependency-cycle"

        members = set(
            component
        )

        edges = []

        for source in component:
            for target in adjacency.get(
                source,
                [],
            ):
                if target in members:
                    edges.append(
                        {
                            "source":
                                source,

                            "target":
                                target,
                        }
                    )

        cycles.append(
            {
                "class":
                    cycle_type,

                "members":
                    component,

                "member_count":
                    len(
                        component
                    ),

                "edges":
                    sorted(
                        edges,
                        key=lambda item: (
                            item[
                                "source"
                            ],
                            item[
                                "target"
                            ],
                        ),
                    ),
            }
        )

    return {
        "schema":
            "savant.living-governance.cycle-classification.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "projection_only":
            True,

        "cycle_count":
            len(
                cycles
            ),

        "acyclic":
            not cycles,

        "cycles":
            sorted(
                cycles,
                key=lambda item: (
                    item[
                        "class"
                    ],
                    item[
                        "members"
                    ],
                ),
            ),
    }


def status() -> dict[str, Any]:
    events = read_events()

    timestamped = sum(
        1
        for event
        in events
        if _event_time(
            event
        )
        is not None
    )

    return {
        "schema":
            "savant.living-governance.temporal-status.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "projection_only":
            True,

        "ledger_events":
            len(
                events
            ),

        "timestamped_events":
            timestamped,

        "untimestamped_events":
            (
                len(
                    events
                )
                - timestamped
            ),

        "operations": [
            "current-state",
            "state-at-sequence",
            "state-at-timestamp",
            "state-diff",
            "supersession-trace",
            "transitive-impact",
            "cycle-classification",
        ],

        "ready":
            True,
    }


__all__ = [
    "classify_cycles",
    "current_state",
    "diff_sequences",
    "diff_states",
    "diff_timestamps",
    "impact",
    "resolve_events",
    "state_at_sequence",
    "state_at_timestamp",
    "status",
    "supersession_trace",
]
