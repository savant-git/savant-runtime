#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from typing import Any, Mapping, Sequence


owner = "living-governance"
supersession_owner = "pryme"
authority_effect = "none"
schema = "savant.living-governance.policy-lifecycle.v1"


lifecycle_order = (
    "proposed",
    "accepted_for_implementation",
    "materialized",
    "verified",
    "active",
    "superseded",
    "retired",
)

lifecycle_rank = {
    state: index
    for index, state in enumerate(lifecycle_order)
}

terminal_states = {
    "superseded",
    "retired",
}

allowed_transitions = {
    "proposed": {
        "accepted_for_implementation",
    },
    "accepted_for_implementation": {
        "materialized",
    },
    "materialized": {
        "verified",
    },
    "verified": {
        "active",
    },
    "active": {
        "superseded",
        "retired",
    },
    "superseded": {
        "retired",
    },
    "retired": set(),
}

reason_codes = {
    "declared":
        "lg.lifecycle.declared",

    "event_applied":
        "lg.lifecycle.event-applied",

    "invalid_transition":
        "lg.lifecycle.invalid-transition",

    "unknown_state":
        "lg.lifecycle.unknown-state",

    "supersession_claim":
        "lg.lifecycle.supersession-claim",

    "supersession_applied":
        "lg.lifecycle.supersession-applied",

    "partial_supersession":
        "lg.lifecycle.partial-supersession",

    "supersession_unresolved":
        "lg.lifecycle.supersession-unresolved",

    "supersession_cycle":
        "lg.lifecycle.supersession-cycle",

    "supersession_target_missing":
        "lg.lifecycle.supersession-target-missing",

    "pryme_required":
        "lg.lifecycle.pryme-required",
}


class living_policy_lifecycle_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(value)


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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


def normalize_state(
    value: Any,
) -> str | None:
    if value is None:
        return None

    normalized = (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    aliases = {
        "accepted":
            "accepted_for_implementation",

        "accepted_for_impl":
            "accepted_for_implementation",

        "implemented":
            "materialized",

        "inactive":
            "retired",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return normalized or None


def policy_id(
    record: Mapping[str, Any],
) -> str:
    identifier = str(
        record.get(
            "id",
            "",
        )
    ).strip()

    if not identifier:
        raise living_policy_lifecycle_error(
            "policy id is required"
        )

    return identifier


def lifecycle_metadata(
    record: Mapping[str, Any],
) -> Mapping[str, Any]:
    value = record.get(
        "lifecycle"
    )

    if isinstance(
        value,
        Mapping,
    ):
        return value

    return {}


def declared_state(
    record: Mapping[str, Any],
) -> str:
    metadata = lifecycle_metadata(
        record
    )

    raw = (
        metadata.get(
            "state"
        )
        or record.get(
            "lifecycle_state"
        )
        or record.get(
            "status"
        )
        or "proposed"
    )

    state = normalize_state(
        raw
    )

    if state not in lifecycle_rank:
        raise living_policy_lifecycle_error(
            (
                "unsupported lifecycle state: "
                + str(raw)
            )
        )

    return state


def event_sequence(
    event: Mapping[str, Any],
) -> int:
    raw = event.get(
        "sequence"
    )

    if raw is None:
        return 0

    if isinstance(
        raw,
        bool,
    ):
        raise living_policy_lifecycle_error(
            (
                "lifecycle event sequence "
                "must be numeric"
            )
        )

    try:
        value = int(
            raw
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise living_policy_lifecycle_error(
            (
                "lifecycle event sequence "
                "must be numeric"
            )
        ) from exc

    if value < 0:
        raise living_policy_lifecycle_error(
            (
                "lifecycle event sequence "
                "cannot be negative"
            )
        )

    return value


def record_events(
    record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    metadata = lifecycle_metadata(
        record
    )

    values = (
        metadata.get(
            "events"
        )
        or record.get(
            "lifecycle_events"
        )
        or []
    )

    if (
        not isinstance(
            values,
            Sequence,
        )
        or isinstance(
            values,
            str,
        )
    ):
        raise living_policy_lifecycle_error(
            "lifecycle events must be an array"
        )

    rows = []

    for value in values:
        if not isinstance(
            value,
            Mapping,
        ):
            raise living_policy_lifecycle_error(
                (
                    "every lifecycle event "
                    "must be an object"
                )
            )

        rows.append(
            clone(
                dict(value)
            )
        )

    rows.sort(
        key=lambda value: (
            event_sequence(
                value
            ),
            str(
                value.get(
                    "id",
                    "",
                )
            ),
            digest(
                value
            ),
        )
    )

    return rows


def transition_target(
    event: Mapping[str, Any],
) -> str | None:
    kind = (
        str(
            event.get(
                "kind"
            )
            or event.get(
                "type"
            )
            or ""
        )
        .strip()
        .lower()
        .replace(
            "_",
            "-",
        )
    )

    if kind not in {
        "lifecycle-transition",
        "transition",
        "policy-lifecycle-transition",
    }:
        return None

    return normalize_state(
        event.get(
            "to"
        )
        or event.get(
            "state"
        )
        or event.get(
            "target_state"
        )
    )


def apply_lifecycle_events(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    identifier = policy_id(
        record
    )

    state = declared_state(
        record
    )

    history = []
    violations = []

    for event in record_events(
        record
    ):
        target = transition_target(
            event
        )

        if target is None:
            continue

        before = state

        if target not in lifecycle_rank:
            violations.append(
                {
                    "class":
                        "unknown-lifecycle-state",

                    "policy":
                        identifier,

                    "from":
                        before,

                    "to":
                        target,

                    "event":
                        clone(event),

                    "reason_code":
                        reason_codes[
                            "unknown_state"
                        ],
                }
            )

            continue

        if target == before:
            history.append(
                {
                    "from":
                        before,

                    "to":
                        target,

                    "event":
                        clone(event),

                    "applied":
                        False,

                    "idempotent":
                        True,
                }
            )

            continue

        if (
            target
            not in allowed_transitions[
                before
            ]
        ):
            violations.append(
                {
                    "class":
                        (
                            "invalid-lifecycle-"
                            "transition"
                        ),

                    "policy":
                        identifier,

                    "from":
                        before,

                    "to":
                        target,

                    "event":
                        clone(event),

                    "reason_code":
                        reason_codes[
                            "invalid_transition"
                        ],
                }
            )

            continue

        state = target

        history.append(
            {
                "from":
                    before,

                "to":
                    target,

                "event":
                    clone(event),

                "applied":
                    True,

                "reason_code":
                    reason_codes[
                        "event_applied"
                    ],
            }
        )

    return {
        "policy":
            identifier,

        "declared_state":
            declared_state(
                record
            ),

        "state":
            state,

        "history":
            history,

        "violations":
            violations,

        "valid":
            not violations,
    }


def normalize_refs(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        value = [
            value
        ]

    if not isinstance(
        value,
        Sequence,
    ):
        value = [
            value
        ]

    return sorted(
        {
            str(item).strip()
            for item in value
            if str(item).strip()
        }
    )


def supersession_claims(
    records: Sequence[
        Mapping[str, Any]
    ],
) -> list[dict[str, Any]]:
    claims = []

    for record in records:
        identifier = policy_id(
            record
        )

        for target in normalize_refs(
            record.get(
                "supersedes"
            )
        ):
            claims.append(
                {
                    "source":
                        identifier,

                    "target":
                        target,

                    "direction":
                        "supersedes",

                    "reason_code":
                        reason_codes[
                            "supersession_claim"
                        ],
                }
            )

        for source in normalize_refs(
            record.get(
                "superseded_by"
            )
        ):
            claims.append(
                {
                    "source":
                        source,

                    "target":
                        identifier,

                    "direction":
                        "superseded_by",

                    "reason_code":
                        reason_codes[
                            "supersession_claim"
                        ],
                }
            )

    claims.sort(
        key=lambda value: (
            value[
                "source"
            ],
            value[
                "target"
            ],
            value[
                "direction"
            ],
        )
    )

    return claims


def supersession_events(
    events: Sequence[
        Mapping[str, Any]
    ]
    | None,
) -> list[dict[str, Any]]:
    if events is None:
        return []

    rows = []

    for event in events:
        if not isinstance(
            event,
            Mapping,
        ):
            raise living_policy_lifecycle_error(
                (
                    "every supersession event "
                    "must be an object"
                )
            )

        kind = (
            str(
                event.get(
                    "kind"
                )
                or event.get(
                    "type"
                )
                or "supersession"
            )
            .strip()
            .lower()
            .replace(
                "_",
                "-",
            )
        )

        if kind not in {
            "supersession",
            "policy-supersession",
            "supersession-event",
        }:
            continue

        source = str(
            event.get(
                "source"
            )
            or event.get(
                "superseded"
            )
            or ""
        ).strip()

        target = str(
            event.get(
                "target"
            )
            or event.get(
                "superseding"
            )
            or ""
        ).strip()

        if (
            not source
            or not target
        ):
            raise living_policy_lifecycle_error(
                (
                    "supersession event requires "
                    "source and target"
                )
            )

        coverage = (
            str(
                event.get(
                    "coverage"
                )
                or "full"
            )
            .strip()
            .lower()
            .replace(
                "_",
                "-",
            )
        )

        if coverage not in {
            "full",
            "partial",
        }:
            raise living_policy_lifecycle_error(
                (
                    "supersession coverage must "
                    "be full or partial"
                )
            )

        resolution_owner = (
            str(
                event.get(
                    "resolution_owner"
                )
                or event.get(
                    "owner"
                )
                or ""
            )
            .strip()
            .lower()
        )

        accepted = (
            event.get(
                "accepted"
            )
            is True
        )

        rows.append(
            {
                "id":
                    (
                        str(
                            event.get(
                                "id"
                            )
                            or ""
                        ).strip()
                        or None
                    ),

                "source":
                    source,

                "target":
                    target,

                "coverage":
                    coverage,

                "resolution_owner":
                    resolution_owner,

                "accepted":
                    accepted,

                "scope":
                    clone(
                        event.get(
                            "scope"
                        )
                    ),

                "sequence":
                    event_sequence(
                        event
                    ),

                "event":
                    clone(
                        dict(event)
                    ),
            }
        )

    rows.sort(
        key=lambda value: (
            value[
                "sequence"
            ],
            value[
                "source"
            ],
            value[
                "target"
            ],
            str(
                value[
                    "id"
                ]
                or ""
            ),
        )
    )

    return rows


def accepted_supersession(
    event: Mapping[str, Any],
) -> bool:
    return bool(
        event.get(
            "accepted"
        )
        is True
        and event.get(
            "resolution_owner"
        )
        == supersession_owner
    )


def cycle_nodes(
    edges: Sequence[
        Mapping[str, Any]
    ],
) -> set[str]:
    graph: dict[
        str,
        set[str],
    ] = {}

    for edge in edges:
        source = str(
            edge[
                "source"
            ]
        )

        target = str(
            edge[
                "target"
            ]
        )

        graph.setdefault(
            source,
            set(),
        ).add(
            target
        )

        graph.setdefault(
            target,
            set(),
        )

    visiting = set()
    visited = set()
    cycles = set()

    def walk(
        node: str,
        stack: list[str],
    ) -> None:
        if node in visiting:
            if node in stack:
                start = stack.index(
                    node
                )

                cycles.update(
                    stack[
                        start:
                    ]
                )

            cycles.add(
                node
            )

            return

        if node in visited:
            return

        visiting.add(
            node
        )

        stack.append(
            node
        )

        for target in sorted(
            graph.get(
                node,
                set(),
            )
        ):
            walk(
                target,
                stack,
            )

        stack.pop()

        visiting.remove(
            node
        )

        visited.add(
            node
        )

    for node in sorted(
        graph
    ):
        walk(
            node,
            [],
        )

    return cycles


def project(
    records: Sequence[
        Mapping[str, Any]
    ],
    *,
    supersession: Sequence[
        Mapping[str, Any]
    ]
    | None = None,
) -> dict[str, Any]:
    source_digest = digest(
        records
    )

    supersession_source_digest = digest(
        supersession
        or []
    )

    index = {}
    lifecycle = {}

    for record in records:
        if not isinstance(
            record,
            Mapping,
        ):
            raise living_policy_lifecycle_error(
                (
                    "every policy record "
                    "must be an object"
                )
            )

        identifier = policy_id(
            record
        )

        if identifier in index:
            raise living_policy_lifecycle_error(
                (
                    "duplicate policy id: "
                    + identifier
                )
            )

        index[
            identifier
        ] = record

        lifecycle[
            identifier
        ] = apply_lifecycle_events(
            record
        )

    claims = supersession_claims(
        records
    )

    events = supersession_events(
        supersession
    )

    applied_edges = []
    unresolved_edges = []
    partial_edges = []
    missing_targets = []

    for event in events:
        source = event[
            "source"
        ]

        target = event[
            "target"
        ]

        if (
            source not in index
            or target not in index
        ):
            missing_targets.append(
                {
                    "source":
                        source,

                    "target":
                        target,

                    "reason_code":
                        reason_codes[
                            (
                                "supersession_"
                                "target_missing"
                            )
                        ],

                    "event":
                        clone(
                            event[
                                "event"
                            ]
                        ),
                }
            )

            continue

        if not accepted_supersession(
            event
        ):
            unresolved_edges.append(
                {
                    "source":
                        source,

                    "target":
                        target,

                    "coverage":
                        event[
                            "coverage"
                        ],

                    "resolution_owner":
                        event[
                            "resolution_owner"
                        ],

                    "accepted":
                        event[
                            "accepted"
                        ],

                    "reason_codes": [
                        reason_codes[
                            (
                                "supersession_"
                                "unresolved"
                            )
                        ],
                        reason_codes[
                            "pryme_required"
                        ],
                    ],
                }
            )

            continue

        edge = {
            "source":
                source,

            "target":
                target,

            "coverage":
                event[
                    "coverage"
                ],

            "resolution_owner":
                supersession_owner,

            "accepted":
                True,

            "scope":
                clone(
                    event.get(
                        "scope"
                    )
                ),

            "sequence":
                event[
                    "sequence"
                ],

            "reason_code":
                (
                    reason_codes[
                        "partial_supersession"
                    ]
                    if event[
                        "coverage"
                    ]
                    == "partial"
                    else reason_codes[
                        "supersession_applied"
                    ]
                ),
        }

        if (
            event[
                "coverage"
            ]
            == "partial"
        ):
            partial_edges.append(
                edge
            )

        else:
            applied_edges.append(
                edge
            )

    cycles = cycle_nodes(
        applied_edges
    )

    effective = {}

    for identifier in sorted(
        index
    ):
        base = lifecycle[
            identifier
        ]

        state = base[
            "state"
        ]

        reasons = [
            reason_codes[
                "declared"
            ]
        ]

        full_incoming = [
            edge
            for edge in applied_edges
            if edge[
                "source"
            ]
            == identifier
        ]

        partial_incoming = [
            edge
            for edge in partial_edges
            if edge[
                "source"
            ]
            == identifier
        ]

        superseded_by = sorted(
            {
                edge[
                    "target"
                ]
                for edge
                in full_incoming
            }
        )

        partially_superseded_by = sorted(
            {
                edge[
                    "target"
                ]
                for edge
                in partial_incoming
            }
        )

        unresolved_for_policy = [
            edge
            for edge in unresolved_edges
            if (
                edge[
                    "source"
                ]
                == identifier
                or edge[
                    "target"
                ]
                == identifier
            )
        ]

        if identifier in cycles:
            effective_state = (
                "indeterminate"
            )

            reasons.append(
                reason_codes[
                    "supersession_cycle"
                ]
            )

        elif superseded_by:
            effective_state = (
                "superseded"
            )

            reasons.append(
                reason_codes[
                    "supersession_applied"
                ]
            )

        else:
            effective_state = state

        if partially_superseded_by:
            reasons.append(
                reason_codes[
                    "partial_supersession"
                ]
            )

        if unresolved_for_policy:
            reasons.extend(
                [
                    reason_codes[
                        (
                            "supersession_"
                            "unresolved"
                        )
                    ],
                    reason_codes[
                        "pryme_required"
                    ],
                ]
            )

        effective[
            identifier
        ] = {
            "policy":
                identifier,

            "declared_state":
                base[
                    "declared_state"
                ],

            "event_state":
                state,

            "effective_state":
                effective_state,

            "terminal":
                (
                    effective_state
                    in terminal_states
                ),

            "superseded_by":
                superseded_by,

            "partially_superseded_by":
                partially_superseded_by,

            "unresolved_supersession":
                clone(
                    unresolved_for_policy
                ),

            "lifecycle_history":
                clone(
                    base[
                        "history"
                    ]
                ),

            "lifecycle_violations":
                clone(
                    base[
                        "violations"
                    ]
                ),

            "reason_codes":
                sorted(
                    set(
                        reasons
                    )
                ),
        }

    overall_state = "pass"

    if cycles:
        overall_state = (
            "authority-required"
        )

    elif missing_targets:
        overall_state = "unknown"

    elif unresolved_edges:
        overall_state = (
            "authority-required"
        )

    elif any(
        lifecycle[
            value
        ][
            "violations"
        ]
        for value
        in lifecycle
    ):
        overall_state = "advisory"

    result = {
        "schema":
            schema,

        "kind":
            "policy-lifecycle-projection",

        "owner":
            owner,

        "supersession_resolution_owner":
            supersession_owner,

        "authority_effect":
            authority_effect,

        "state":
            overall_state,

        "policy_count":
            len(
                index
            ),

        "policies":
            effective,

        "supersession_claims":
            claims,

        "accepted_full_supersession_edges":
            applied_edges,

        "accepted_partial_supersession_edges":
            partial_edges,

        "unresolved_supersession_edges":
            unresolved_edges,

        "missing_supersession_targets":
            missing_targets,

        "supersession_cycle_policy_ids":
            sorted(
                cycles
            ),

        "active_policy_ids": [
            identifier
            for identifier
            in sorted(
                effective
            )
            if effective[
                identifier
            ][
                "effective_state"
            ]
            == "active"
        ],

        "superseded_policy_ids": [
            identifier
            for identifier
            in sorted(
                effective
            )
            if effective[
                identifier
            ][
                "effective_state"
            ]
            == "superseded"
        ],

        "retired_policy_ids": [
            identifier
            for identifier
            in sorted(
                effective
            )
            if effective[
                identifier
            ][
                "effective_state"
            ]
            == "retired"
        ],

        "indeterminate_policy_ids": [
            identifier
            for identifier
            in sorted(
                effective
            )
            if effective[
                identifier
            ][
                "effective_state"
            ]
            == "indeterminate"
        ],

        "claims_apply_supersession":
            False,

        "pryme_resolution_required_for_supersession":
            True,

        "history_rewritten":
            False,

        "append_only_semantics":
            True,

        "projection_only":
            True,

        "source_state_mutated":
            (
                source_digest
                != digest(
                    records
                )
            ),

        "supersession_source_mutated":
            (
                supersession_source_digest
                != digest(
                    supersession
                    or []
                )
            ),

        "authority_transfer":
            False,
    }

    if result[
        "source_state_mutated"
    ]:
        raise living_policy_lifecycle_error(
            (
                "policy records "
                "were mutated"
            )
        )

    if result[
        "supersession_source_mutated"
    ]:
        raise living_policy_lifecycle_error(
            (
                "supersession events "
                "were mutated"
            )
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


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "supersession_resolution_owner":
            supersession_owner,

        "authority_effect":
            authority_effect,

        "immutable_history":
            True,

        "append_only_lifecycle":
            True,

        "explicit_transition_validation":
            True,

        "full_supersession":
            True,

        "partial_supersession":
            True,

        "supersession_cycle_detection":
            True,

        "supersession_claims_are_authority":
            False,

        "pryme_resolution_required":
            True,

        "projection_only":
            True,

        "authority_transfer":
            False,

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    records = [
        {
            "id":
                "policy:a",

            "lifecycle_state":
                "active",

            "superseded_by": [
                "policy:b"
            ],
        },
        {
            "id":
                "policy:b",

            "lifecycle_state":
                "active",

            "supersedes": [
                "policy:a"
            ],
        },
        {
            "id":
                "policy:c",

            "lifecycle_state":
                "active",
        },
        {
            "id":
                "policy:d",

            "lifecycle_state":
                "active",
        },
    ]

    unresolved = project(
        records
    )

    if (
        unresolved[
            "policies"
        ][
            "policy:a"
        ][
            "effective_state"
        ]
        != "active"
    ):
        raise living_policy_lifecycle_error(
            (
                "supersession claim changed "
                "lifecycle without Pryme"
            )
        )

    events = [
        {
            "id":
                "supersession:1",

            "kind":
                "supersession",

            "source":
                "policy:a",

            "target":
                "policy:b",

            "coverage":
                "full",

            "resolution_owner":
                "pryme",

            "accepted":
                True,

            "sequence":
                1,
        },
        {
            "id":
                "supersession:2",

            "kind":
                "supersession",

            "source":
                "policy:c",

            "target":
                "policy:d",

            "coverage":
                "partial",

            "resolution_owner":
                "pryme",

            "accepted":
                True,

            "sequence":
                2,
        },
    ]

    resolved = project(
        records,
        supersession=
            events,
    )

    if (
        resolved[
            "policies"
        ][
            "policy:a"
        ][
            "effective_state"
        ]
        != "superseded"
    ):
        raise living_policy_lifecycle_error(
            (
                "accepted full supersession "
                "was not projected"
            )
        )

    if (
        resolved[
            "policies"
        ][
            "policy:c"
        ][
            "effective_state"
        ]
        != "active"
    ):
        raise living_policy_lifecycle_error(
            (
                "partial supersession "
                "incorrectly deactivated source"
            )
        )

    if (
        resolved[
            "policies"
        ][
            "policy:c"
        ][
            "partially_superseded_by"
        ]
        != [
            "policy:d"
        ]
    ):
        raise living_policy_lifecycle_error(
            (
                "partial supersession edge "
                "was not preserved"
            )
        )

    wrong_owner = project(
        records,
        supersession=[
            {
                "kind":
                    "supersession",

                "source":
                    "policy:a",

                "target":
                    "policy:b",

                "coverage":
                    "full",

                "resolution_owner":
                    "living-governance",

                "accepted":
                    True,
            }
        ],
    )

    if (
        wrong_owner[
            "policies"
        ][
            "policy:a"
        ][
            "effective_state"
        ]
        != "active"
    ):
        raise living_policy_lifecycle_error(
            (
                "non-Pryme supersession "
                "was applied"
            )
        )

    if (
        wrong_owner[
            "state"
        ]
        != "authority-required"
    ):
        raise living_policy_lifecycle_error(
            (
                "unresolved supersession "
                "did not require authority"
            )
        )

    cycle = project(
        records[
            :2
        ],
        supersession=[
            {
                "kind":
                    "supersession",

                "source":
                    "policy:a",

                "target":
                    "policy:b",

                "resolution_owner":
                    "pryme",

                "accepted":
                    True,
            },
            {
                "kind":
                    "supersession",

                "source":
                    "policy:b",

                "target":
                    "policy:a",

                "resolution_owner":
                    "pryme",

                "accepted":
                    True,
            },
        ],
    )

    if (
        cycle[
            "state"
        ]
        != "authority-required"
    ):
        raise living_policy_lifecycle_error(
            (
                "supersession cycle "
                "was not blocked"
            )
        )

    if (
        sorted(
            cycle[
                (
                    "supersession_cycle_"
                    "policy_ids"
                )
            ]
        )
        != [
            "policy:a",
            "policy:b",
        ]
    ):
        raise living_policy_lifecycle_error(
            (
                "supersession cycle nodes "
                "were not projected"
            )
        )

    transition_record = {
        "id":
            "policy:transition",

        "lifecycle_state":
            "proposed",

        "lifecycle_events": [
            {
                "id":
                    "e1",

                "kind":
                    "transition",

                "to":
                    (
                        "accepted_for_"
                        "implementation"
                    ),

                "sequence":
                    1,
            },
            {
                "id":
                    "e2",

                "kind":
                    "transition",

                "to":
                    "materialized",

                "sequence":
                    2,
            },
            {
                "id":
                    "e3",

                "kind":
                    "transition",

                "to":
                    "verified",

                "sequence":
                    3,
            },
            {
                "id":
                    "e4",

                "kind":
                    "transition",

                "to":
                    "active",

                "sequence":
                    4,
            },
        ],
    }

    transition = project(
        [
            transition_record
        ]
    )

    if (
        transition[
            "policies"
        ][
            "policy:transition"
        ][
            "effective_state"
        ]
        != "active"
    ):
        raise living_policy_lifecycle_error(
            (
                "valid lifecycle transition "
                "chain failed"
            )
        )

    invalid_transition = project(
        [
            {
                "id":
                    "policy:invalid",

                "lifecycle_state":
                    "proposed",

                "lifecycle_events": [
                    {
                        "kind":
                            "transition",

                        "to":
                            "active",

                        "sequence":
                            1,
                    }
                ],
            }
        ]
    )

    if not (
        invalid_transition[
            "policies"
        ][
            "policy:invalid"
        ][
            "lifecycle_violations"
        ]
    ):
        raise living_policy_lifecycle_error(
            (
                "invalid lifecycle transition "
                "was hidden"
            )
        )

    before = digest(
        records
    )

    first = project(
        records,
        supersession=
            events,
    )

    second = project(
        records,
        supersession=
            events,
    )

    if first != second:
        raise living_policy_lifecycle_error(
            (
                "lifecycle projection "
                "is not deterministic"
            )
        )

    if (
        before
        != digest(
            records
        )
    ):
        raise living_policy_lifecycle_error(
            (
                "lifecycle projection "
                "mutated source"
            )
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "supersession_resolution_owner":
            supersession_owner,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "lifecycle_transition_chain":
            True,

        "invalid_transition_exposed":
            True,

        "supersession_claim_not_applied":
            True,

        "pryme_resolved_supersession_applied":
            True,

        "partial_supersession_preserved":
            True,

        "non_pryme_supersession_blocked":
            True,

        "supersession_cycle_detected":
            True,

        "immutable_history":
            True,

        "deterministic":
            True,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "apply_lifecycle_events",
    "living_policy_lifecycle_error",
    "project",
    "selftest",
    "status",
]
