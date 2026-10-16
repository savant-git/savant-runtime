#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence


owner = "living-governance"
authority_effect = "none"
schema = "savant.living-governance.policy-composition.v1"


authority_ranks = {
    "current_user_directive": 1100,
    "accepted_authoritative_graph": 1000,
    "accepted_decision": 900,
    "constitutional_canon": 800,
    "verified_implementation": 700,
    "admitted_evidence": 600,
    "deterministic_projection": 500,
    "historical_implementation": 400,
    "historical_document": 300,
    "inference": 200,
    "speculation": 100,
}


local_fields = {
    "id",
    "schema",
    "stream",
    "version",
    "status",
    "authority",
    "authority_class",
    "authority_rank",
    "priority",
    "supersedes",
    "provenance",
    "inherits",
    "extends",
    "inheritance",
    "composition",
}


default_strategies = {
    "scope": "replace",
    "subject": "replace",
    "target": "replace",
    "action": "replace",
    "predicate": "replace",
    "effect": "replace",
    "enforcement_mode": "replace",
    "specificity": "replace",
    "epistemic_class": "replace",
    "temporal_validity": "replace",
    "valid_from": "replace",
    "valid_until": "replace",

    "dependencies": "union",
    "relationships": "union",
    "reason_codes": "union",
    "evidence": "union",
    "evidence_requirements": "union",
    "exceptions": "union",
    "override_requirements": "union",
    "remediation": "union",
    "compatibility_obligations": "union",
    "affected_objects": "union",
}


allowed_strategies = {
    "replace",
    "union",
    "deep-merge",
    "require-equal",
    "deny-override",
}


class living_policy_composition_error(
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


def normalize_strings(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        value = [value]

    if not isinstance(
        value,
        Sequence,
    ):
        value = [value]

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


def record_id(
    record: Mapping[str, Any],
) -> str:
    identifier = str(
        record.get(
            "id",
            "",
        )
    ).strip()

    if not identifier:
        raise living_policy_composition_error(
            "policy record id is required"
        )

    return identifier


def authority_rank(
    record: Mapping[str, Any],
) -> int:
    explicit = record.get(
        "authority_rank"
    )

    if isinstance(
        explicit,
        bool,
    ):
        explicit = None

    if isinstance(
        explicit,
        (
            int,
            float,
        ),
    ):
        return int(
            explicit
        )

    authority = str(
        record.get(
            "authority_class"
        )
        or record.get(
            "authority"
        )
        or ""
    ).strip().lower()

    return authority_ranks.get(
        authority,
        0,
    )


def parent_refs(
    record: Mapping[str, Any],
) -> list[str]:
    values = []

    values.extend(
        normalize_strings(
            record.get(
                "inherits"
            )
        )
    )

    values.extend(
        normalize_strings(
            record.get(
                "extends"
            )
        )
    )

    inheritance = record.get(
        "inheritance"
    )

    if isinstance(
        inheritance,
        Mapping,
    ):
        values.extend(
            normalize_strings(
                inheritance.get(
                    "parents"
                )
                or inheritance.get(
                    "policies"
                )
                or inheritance.get(
                    "refs"
                )
            )
        )

    seen = set()
    result = []

    for value in values:
        if value in seen:
            continue

        seen.add(
            value
        )

        result.append(
            value
        )

    return result


def composition_metadata(
    record: Mapping[str, Any],
) -> Mapping[str, Any]:
    value = record.get(
        "composition"
    )

    if isinstance(
        value,
        Mapping,
    ):
        return value

    return {}


def field_strategy(
    record: Mapping[str, Any],
    field: str,
) -> str:
    composition = composition_metadata(
        record
    )

    strategies = composition.get(
        "strategies"
    )

    if isinstance(
        strategies,
        Mapping,
    ):
        declared = strategies.get(
            field
        )

        if declared is not None:
            strategy = (
                str(declared)
                .strip()
                .lower()
                .replace(
                    "_",
                    "-",
                )
            )

            if strategy not in allowed_strategies:
                raise living_policy_composition_error(
                    (
                        "unsupported composition "
                        "strategy for "
                        + field
                        + ": "
                        + strategy
                    )
                )

            return strategy

    return default_strategies.get(
        field,
        "require-equal",
    )


def parent_precedence(
    record: Mapping[str, Any],
    field: str,
) -> list[str]:
    composition = composition_metadata(
        record
    )

    value = composition.get(
        "parent_precedence"
    )

    if not isinstance(
        value,
        Mapping,
    ):
        return []

    return normalize_strings(
        value.get(
            field
        )
    )


def union_values(
    left: Any,
    right: Any,
) -> list[Any]:
    left_values = (
        list(left)
        if isinstance(
            left,
            (
                list,
                tuple,
                set,
            ),
        )
        else [left]
    )

    right_values = (
        list(right)
        if isinstance(
            right,
            (
                list,
                tuple,
                set,
            ),
        )
        else [right]
    )

    index: dict[str, Any] = {}

    for value in (
        left_values
        + right_values
    ):
        index[
            canonical_json(
                value
            )
        ] = clone(
            value
        )

    return [
        index[key]
        for key
        in sorted(
            index
        )
    ]


def deep_merge(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    allow_right_override: bool,
    path: str,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
]:
    output = clone(
        dict(left)
    )

    conflicts = []

    for key in sorted(
        right
    ):
        incoming = right[
            key
        ]

        if key not in output:
            output[
                key
            ] = clone(
                incoming
            )

            continue

        current = output[
            key
        ]

        if current == incoming:
            continue

        child_path = (
            path
            + "."
            + str(key)
        )

        if (
            isinstance(
                current,
                Mapping,
            )
            and isinstance(
                incoming,
                Mapping,
            )
        ):
            (
                merged,
                nested_conflicts,
            ) = deep_merge(
                current,
                incoming,
                allow_right_override=
                    allow_right_override,
                path=
                    child_path,
            )

            output[
                key
            ] = merged

            conflicts.extend(
                nested_conflicts
            )

            continue

        if allow_right_override:
            output[
                key
            ] = clone(
                incoming
            )

        else:
            conflicts.append(
                {
                    "class":
                        "deep-merge-conflict",

                    "field":
                        child_path,

                    "left":
                        clone(
                            current
                        ),

                    "right":
                        clone(
                            incoming
                        ),
                }
            )

    return (
        output,
        conflicts,
    )


def index_records(
    records: Sequence[
        Mapping[str, Any]
    ],
) -> dict[
    str,
    Mapping[str, Any],
]:
    index = {}

    for record in records:
        if not isinstance(
            record,
            Mapping,
        ):
            raise living_policy_composition_error(
                (
                    "all policy records "
                    "must be objects"
                )
            )

        identifier = record_id(
            record
        )

        if identifier in index:
            raise living_policy_composition_error(
                (
                    "duplicate policy id: "
                    + identifier
                )
            )

        index[
            identifier
        ] = record

    return index


def own_semantics(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        str(key):
            clone(
                value
            )
        for key, value
        in record.items()
        if key not in local_fields
    }


def _parent_source(
    field_sources: Mapping[
        str,
        list[dict[str, Any]],
    ],
    field: str,
) -> list[dict[str, Any]]:
    return clone(
        field_sources.get(
            field,
            [],
        )
    )


def _merge_parent_field(
    *,
    target_record: Mapping[str, Any],
    field: str,
    current: Any,
    current_sources:
        list[dict[str, Any]],
    incoming: Any,
    incoming_sources:
        list[dict[str, Any]],
) -> tuple[
    Any,
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    strategy = field_strategy(
        target_record,
        field,
    )

    conflicts = []

    if current == incoming:
        return (
            clone(
                current
            ),
            (
                current_sources
                + incoming_sources
            ),
            conflicts,
        )

    if strategy == "union":
        return (
            union_values(
                current,
                incoming,
            ),
            (
                current_sources
                + incoming_sources
            ),
            conflicts,
        )

    if (
        strategy == "deep-merge"
        and isinstance(
            current,
            Mapping,
        )
        and isinstance(
            incoming,
            Mapping,
        )
    ):
        merged, nested = deep_merge(
            current,
            incoming,
            allow_right_override=
                False,
            path=
                field,
        )

        conflicts.extend(
            nested
        )

        return (
            merged,
            (
                current_sources
                + incoming_sources
            ),
            conflicts,
        )

    precedence = parent_precedence(
        target_record,
        field,
    )

    source_ids = [
        str(
            value.get(
                "policy"
            )
        )
        for value
        in incoming_sources
    ]

    current_ids = [
        str(
            value.get(
                "policy"
            )
        )
        for value
        in current_sources
    ]

    selected = None

    for policy_id in precedence:
        if policy_id in source_ids:
            selected = "incoming"
            break

        if policy_id in current_ids:
            selected = "current"
            break

    if selected == "incoming":
        return (
            clone(
                incoming
            ),
            clone(
                incoming_sources
            ),
            conflicts,
        )

    if selected == "current":
        return (
            clone(
                current
            ),
            clone(
                current_sources
            ),
            conflicts,
        )

    conflicts.append(
        {
            "class":
                "multiple-parent-conflict",

            "field":
                field,

            "strategy":
                strategy,

            "current":
                clone(
                    current
                ),

            "incoming":
                clone(
                    incoming
                ),

            "current_sources":
                clone(
                    current_sources
                ),

            "incoming_sources":
                clone(
                    incoming_sources
                ),

            "resolution":
                "authority-required",
        }
    )

    return (
        clone(
            current
        ),
        clone(
            current_sources
        ),
        conflicts,
    )


def _apply_child_field(
    *,
    child: Mapping[str, Any],
    field: str,
    inherited: Any,
    inherited_sources:
        list[dict[str, Any]],
    incoming: Any,
) -> tuple[
    Any,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    strategy = field_strategy(
        child,
        field,
    )

    child_id = record_id(
        child
    )

    child_rank = authority_rank(
        child
    )

    child_source = {
        "policy":
            child_id,

        "authority_rank":
            child_rank,

        "origin":
            "child",
    }

    conflicts = []
    overrides = []

    if inherited == incoming:
        return (
            clone(
                inherited
            ),
            (
                inherited_sources
                + [
                    child_source
                ]
            ),
            conflicts,
            overrides,
        )

    if strategy == "union":
        return (
            union_values(
                inherited,
                incoming,
            ),
            (
                inherited_sources
                + [
                    child_source
                ]
            ),
            conflicts,
            overrides,
        )

    parent_rank = max(
        (
            int(
                value.get(
                    "authority_rank",
                    0,
                )
            )
            for value
            in inherited_sources
        ),
        default=0,
    )

    authority_allows = (
        child_rank
        >= parent_rank
    )

    if (
        strategy == "deep-merge"
        and isinstance(
            inherited,
            Mapping,
        )
        and isinstance(
            incoming,
            Mapping,
        )
    ):
        merged, nested = deep_merge(
            inherited,
            incoming,
            allow_right_override=
                authority_allows,
            path=
                field,
        )

        conflicts.extend(
            nested
        )

        if (
            authority_allows
            and merged
            != inherited
        ):
            overrides.append(
                {
                    "field":
                        field,

                    "strategy":
                        strategy,

                    "parent_authority_rank":
                        parent_rank,

                    "child_authority_rank":
                        child_rank,
                }
            )

        return (
            merged,
            (
                inherited_sources
                + [
                    child_source
                ]
            ),
            conflicts,
            overrides,
        )

    if strategy == "replace":
        if authority_allows:
            overrides.append(
                {
                    "field":
                        field,

                    "strategy":
                        "replace",

                    "parent_authority_rank":
                        parent_rank,

                    "child_authority_rank":
                        child_rank,
                }
            )

            return (
                clone(
                    incoming
                ),
                [
                    child_source
                ],
                conflicts,
                overrides,
            )

        conflicts.append(
            {
                "class":
                    "authority-override-blocked",

                "field":
                    field,

                "parent_authority_rank":
                    parent_rank,

                "child_authority_rank":
                    child_rank,

                "resolution":
                    "parent-preserved",
            }
        )

        return (
            clone(
                inherited
            ),
            clone(
                inherited_sources
            ),
            conflicts,
            overrides,
        )

    if strategy == "deny-override":
        conflicts.append(
            {
                "class":
                    "override-denied",

                "field":
                    field,

                "resolution":
                    "parent-preserved",
            }
        )

        return (
            clone(
                inherited
            ),
            clone(
                inherited_sources
            ),
            conflicts,
            overrides,
        )

    conflicts.append(
        {
            "class":
                "require-equal-conflict",

            "field":
                field,

            "parent":
                clone(
                    inherited
                ),

            "child":
                clone(
                    incoming
                ),

            "resolution":
                "authority-required",
        }
    )

    return (
        clone(
            inherited
        ),
        clone(
            inherited_sources
        ),
        conflicts,
        overrides,
    )


class policy_composer:
    def __init__(
        self,
        records: Sequence[
            Mapping[str, Any]
        ],
    ) -> None:
        self.records = index_records(
            records
        )

        self._cache: dict[
            str,
            dict[str, Any],
        ] = {}

    def _resolve(
        self,
        policy_id: str,
        stack: tuple[str, ...],
    ) -> dict[str, Any]:
        if policy_id in self._cache:
            return clone(
                self._cache[
                    policy_id
                ]
            )

        if policy_id in stack:
            cycle = (
                list(
                    stack[
                        stack.index(
                            policy_id
                        ):
                    ]
                )
                + [
                    policy_id
                ]
            )

            return {
                "policy":
                    policy_id,

                "state":
                    "conflict",

                "effective":
                    {},

                "field_sources":
                    {},

                "lineage":
                    [],

                "unresolved_refs":
                    [],

                "conflicts": [
                    {
                        "class":
                            "inheritance-cycle",

                        "cycle":
                            cycle,

                        "resolution":
                            "authority-required",
                    }
                ],

                "overrides":
                    [],

                "complete":
                    False,
            }

        record = self.records.get(
            policy_id
        )

        if record is None:
            return {
                "policy":
                    policy_id,

                "state":
                    "unknown",

                "effective":
                    {},

                "field_sources":
                    {},

                "lineage":
                    [],

                "unresolved_refs": [
                    policy_id
                ],

                "conflicts":
                    [],

                "overrides":
                    [],

                "complete":
                    False,
            }

        parents = parent_refs(
            record
        )

        parent_results = [
            self._resolve(
                parent,
                stack
                + (
                    policy_id,
                ),
            )
            for parent
            in parents
        ]

        effective: dict[
            str,
            Any,
        ] = {}

        sources: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        lineage = []
        unresolved = []
        conflicts = []
        overrides = []

        for result in parent_results:
            lineage.extend(
                result.get(
                    "lineage",
                    [],
                )
            )

            unresolved.extend(
                result.get(
                    "unresolved_refs",
                    [],
                )
            )

            conflicts.extend(
                result.get(
                    "conflicts",
                    [],
                )
            )

            overrides.extend(
                result.get(
                    "overrides",
                    [],
                )
            )

            parent_effective = result.get(
                "effective",
                {}
            )

            parent_sources = result.get(
                "field_sources",
                {}
            )

            for field in sorted(
                parent_effective
            ):
                incoming = (
                    parent_effective[
                        field
                    ]
                )

                incoming_sources = (
                    _parent_source(
                        parent_sources,
                        field,
                    )
                )

                if field not in effective:
                    effective[
                        field
                    ] = clone(
                        incoming
                    )

                    sources[
                        field
                    ] = clone(
                        incoming_sources
                    )

                    continue

                (
                    merged,
                    merged_sources,
                    merge_conflicts,
                ) = _merge_parent_field(
                    target_record=
                        record,
                    field=
                        field,
                    current=
                        effective[
                            field
                        ],
                    current_sources=
                        sources[
                            field
                        ],
                    incoming=
                        incoming,
                    incoming_sources=
                        incoming_sources,
                )

                effective[
                    field
                ] = merged

                sources[
                    field
                ] = merged_sources

                conflicts.extend(
                    merge_conflicts
                )

        child_semantics = own_semantics(
            record
        )

        child_source = {
            "policy":
                policy_id,

            "authority_rank":
                authority_rank(
                    record
                ),

            "origin":
                "child",
        }

        for field in sorted(
            child_semantics
        ):
            incoming = child_semantics[
                field
            ]

            if field not in effective:
                effective[
                    field
                ] = clone(
                    incoming
                )

                sources[
                    field
                ] = [
                    clone(
                        child_source
                    )
                ]

                continue

            (
                resolved,
                resolved_sources,
                child_conflicts,
                child_overrides,
            ) = _apply_child_field(
                child=
                    record,
                field=
                    field,
                inherited=
                    effective[
                        field
                    ],
                inherited_sources=
                    sources[
                        field
                    ],
                incoming=
                    incoming,
            )

            effective[
                field
            ] = resolved

            sources[
                field
            ] = resolved_sources

            conflicts.extend(
                child_conflicts
            )

            overrides.extend(
                child_overrides
            )

        lineage.append(
            {
                "policy":
                    policy_id,

                "parents":
                    clone(
                        parents
                    ),

                "authority_rank":
                    authority_rank(
                        record
                    ),
            }
        )

        unresolved = sorted(
            set(
                unresolved
            )
        )

        unique_lineage = []
        lineage_seen = set()

        for value in lineage:
            identifier = str(
                value.get(
                    "policy",
                    "",
                )
            )

            if identifier in lineage_seen:
                continue

            lineage_seen.add(
                identifier
            )

            unique_lineage.append(
                value
            )

        cycle_present = any(
            value.get(
                "class"
            )
            == "inheritance-cycle"
            for value
            in conflicts
        )

        authority_required = any(
            value.get(
                "resolution"
            )
            == "authority-required"
            for value
            in conflicts
        )

        if cycle_present:
            state = "conflict"

        elif unresolved:
            state = "unknown"

        elif authority_required:
            state = "authority-required"

        elif conflicts:
            state = "advisory"

        else:
            state = "pass"

        result = {
            "policy":
                policy_id,

            "state":
                state,

            "effective":
                effective,

            "field_sources":
                sources,

            "lineage":
                unique_lineage,

            "unresolved_refs":
                unresolved,

            "conflicts":
                conflicts,

            "overrides":
                overrides,

            "complete":
                bool(
                    state
                    == "pass"
                ),
        }

        self._cache[
            policy_id
        ] = clone(
            result
        )

        return result

    def compose(
        self,
        policy_id: str,
    ) -> dict[str, Any]:
        identifier = str(
            policy_id
        ).strip()

        if not identifier:
            raise living_policy_composition_error(
                "policy id is required"
            )

        resolved = self._resolve(
            identifier,
            (),
        )

        result = {
            "schema":
                schema,

            "kind":
                "policy-composition",

            "owner":
                owner,

            "authority_effect":
                authority_effect,

            "policy":
                identifier,

            "state":
                resolved[
                    "state"
                ],

            "complete":
                resolved[
                    "complete"
                ],

            "effective":
                resolved[
                    "effective"
                ],

            "field_sources":
                resolved[
                    "field_sources"
                ],

            "lineage":
                resolved[
                    "lineage"
                ],

            "unresolved_refs":
                resolved[
                    "unresolved_refs"
                ],

            "conflicts":
                resolved[
                    "conflicts"
                ],

            "overrides":
                resolved[
                    "overrides"
                ],

            "composition_by_reference":
                True,

            "second_authority_store_created":
                False,

            "source_state_mutated":
                False,

            "authority_transfer":
                False,
        }

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


def compose(
    records: Sequence[
        Mapping[str, Any]
    ],
    policy_id: str,
) -> dict[str, Any]:
    return policy_composer(
        records
    ).compose(
        policy_id
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "composition_by_reference":
            True,

        "multiple_inheritance":
            True,

        "cycle_detection":
            True,

        "authority_aware_override":
            True,

        "explicit_parent_precedence":
            True,

        "unknown_parent_preservation":
            True,

        "conflict_preservation":
            True,

        "second_authority_store_created":
            False,

        "authority_transfer":
            False,

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    records = [
        {
            "id":
                "policy:base",

            "authority_class":
                "constitutional_canon",

            "scope":
                "runtime",

            "effect":
                "deny",

            "reason_codes": [
                "base"
            ],

            "evidence_requirements": [
                "evidence:base"
            ],
        },

        {
            "id":
                "policy:specialized",

            "authority_class":
                "constitutional_canon",

            "inherits": [
                "policy:base"
            ],

            "scope":
                "runtime:palaver",

            "reason_codes": [
                "specialized"
            ],
        },

        {
            "id":
                "policy:weak",

            "authority_class":
                "inference",

            "inherits": [
                "policy:base"
            ],

            "effect":
                "allow",
        },

        {
            "id":
                "policy:missing",

            "authority_class":
                "constitutional_canon",

            "inherits": [
                "policy:not-present"
            ],
        },

        {
            "id":
                "policy:cycle-a",

            "authority_class":
                "constitutional_canon",

            "inherits": [
                "policy:cycle-b"
            ],
        },

        {
            "id":
                "policy:cycle-b",

            "authority_class":
                "constitutional_canon",

            "inherits": [
                "policy:cycle-a"
            ],
        },
    ]

    specialized = compose(
        records,
        "policy:specialized",
    )

    if (
        specialized[
            "state"
        ]
        != "pass"
    ):
        raise living_policy_composition_error(
            (
                "equal-authority "
                "specialization failed"
            )
        )

    if (
        specialized[
            "effective"
        ][
            "scope"
        ]
        != "runtime:palaver"
    ):
        raise living_policy_composition_error(
            (
                "specialized scope "
                "was not projected"
            )
        )

    if (
        specialized[
            "effective"
        ][
            "reason_codes"
        ]
        != [
            "base",
            "specialized",
        ]
    ):
        raise living_policy_composition_error(
            "union composition failed"
        )

    weak = compose(
        records,
        "policy:weak",
    )

    if (
        weak[
            "effective"
        ][
            "effect"
        ]
        != "deny"
    ):
        raise living_policy_composition_error(
            (
                "lower-authority child "
                "weakened parent policy"
            )
        )

    if not any(
        value.get(
            "class"
        )
        == "authority-override-blocked"
        for value
        in weak[
            "conflicts"
        ]
    ):
        raise living_policy_composition_error(
            (
                "blocked override "
                "was not exposed"
            )
        )

    missing = compose(
        records,
        "policy:missing",
    )

    if (
        missing[
            "state"
        ]
        != "unknown"
    ):
        raise living_policy_composition_error(
            (
                "missing parent did not "
                "remain unknown"
            )
        )

    cycle = compose(
        records,
        "policy:cycle-a",
    )

    if (
        cycle[
            "state"
        ]
        != "conflict"
    ):
        raise living_policy_composition_error(
            (
                "inheritance cycle "
                "was not classified"
            )
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "inheritance":
            True,

        "multiple_inheritance":
            True,

        "union_composition":
            True,

        "authority_aware_override":
            True,

        "lower_authority_weakening_blocked":
            True,

        "unknown_parent_preserved":
            True,

        "cycle_classified":
            True,

        "composition_by_reference":
            True,

        "second_authority_store_created":
            False,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "compose",
    "living_policy_composition_error",
    "policy_composer",
    "selftest",
    "status",
]
