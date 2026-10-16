#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from typing import Any, Mapping, Sequence

from living_policy_composition import authority_rank
from living_policy_temporal import evaluate_record as temporal_evaluate


owner = "living-governance"
authority_effect = "none"
schema = "savant.living-governance.policy-arbitration.v1"


decision_aliases = {
    "allow": "pass",
    "allowed": "pass",
    "permit": "pass",
    "permitted": "pass",
    "deny": "fail",
    "denied": "fail",
    "block": "fail",
    "blocked": "fail",
    "authority_required": "authority-required",
}

valid_decisions = {
    "pass",
    "fail",
    "advisory",
    "unknown",
    "authority-required",
}

blocking_decisions = {
    "fail",
    "unknown",
    "authority-required",
}

selector_fields = (
    "scope",
    "subject",
    "target",
    "action",
    "predicate",
)

wildcards = {
    "",
    "*",
    "any",
    "all",
    "global",
}

reason_codes = {
    "resolved":
        "lg.arbitration.resolved",

    "no_policy":
        "lg.arbitration.no-policy",

    "equal_precedence_conflict":
        "lg.arbitration.equal-precedence-conflict",

    "higher_authority":
        "lg.arbitration.higher-authority",

    "higher_specificity":
        "lg.arbitration.higher-specificity",

    "higher_priority":
        "lg.arbitration.higher-priority",

    "shadowed":
        "lg.arbitration.shadowed",

    "redundant":
        "lg.arbitration.redundant",

    "override_applied":
        "lg.arbitration.override-applied",

    "override_blocked":
        "lg.arbitration.override-blocked",

    "override_target_missing":
        "lg.arbitration.override-target-missing",

    "temporal_unknown":
        "lg.arbitration.temporal-unknown",

    "temporal_invalid":
        "lg.arbitration.temporal-invalid",

    "conditional_unresolved":
        "lg.arbitration.conditional-unresolved",

    "policy_unknown":
        "lg.arbitration.policy-unknown",

    "authority_required":
        "lg.arbitration.authority-required",
}


class living_policy_arbitration_error(RuntimeError):
    pass


def clone(value: Any) -> Any:
    return copy.deepcopy(value)


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


def require_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise living_policy_arbitration_error(
            label + " must be a JSON object"
        )

    return value


def policy_id(record: Mapping[str, Any]) -> str:
    identifier = str(
        record.get("id", "")
    ).strip()

    if not identifier:
        raise living_policy_arbitration_error(
            "policy id is required"
        )

    return identifier


def normalize_decision(
    record: Mapping[str, Any],
) -> tuple[str, list[str]]:
    raw = None

    for field in (
        "decision",
        "effect",
        "result",
        "outcome",
        "state",
    ):
        if record.get(field) is not None:
            raw = record.get(field)
            break

    if raw is None:
        return (
            "unknown",
            [
                reason_codes[
                    "policy_unknown"
                ]
            ],
        )

    value = (
        str(raw)
        .strip()
        .lower()
        .replace("_", "-")
    )

    value = decision_aliases.get(
        value,
        value,
    )

    if value == "conditional":
        condition = record.get(
            "condition_satisfied"
        )

        if condition is True:
            return (
                "pass",
                [],
            )

        if condition is False:
            false_effect = (
                str(
                    record.get(
                        "condition_false_effect",
                        "fail",
                    )
                )
                .strip()
                .lower()
                .replace("_", "-")
            )

            false_effect = (
                decision_aliases.get(
                    false_effect,
                    false_effect,
                )
            )

            if false_effect in valid_decisions:
                return (
                    false_effect,
                    [],
                )

        return (
            "unknown",
            [
                reason_codes[
                    "conditional_unresolved"
                ]
            ],
        )

    if value not in valid_decisions:
        return (
            "unknown",
            [
                reason_codes[
                    "policy_unknown"
                ]
            ],
        )

    return (
        value,
        [],
    )


def numeric_value(
    value: Any,
    *,
    default: int,
    label: str,
) -> int:
    if value is None:
        return default

    if isinstance(value, bool):
        raise living_policy_arbitration_error(
            label + " must be numeric"
        )

    if isinstance(
        value,
        (int, float),
    ):
        return int(value)

    if isinstance(value, str):
        normalized = value.strip()

        if not normalized:
            return default

        try:
            return int(normalized)

        except ValueError as exc:
            raise living_policy_arbitration_error(
                label + " must be numeric"
            ) from exc

    raise living_policy_arbitration_error(
        label + " must be numeric"
    )


def structural_specificity(
    record: Mapping[str, Any],
) -> int:
    count = 0

    for field in selector_fields:
        value = record.get(field)

        if value is None:
            continue

        normalized = str(value).strip().lower()

        if normalized not in wildcards:
            count += 1

    return count


def specificity(
    record: Mapping[str, Any],
) -> int:
    if record.get("specificity") is not None:
        return numeric_value(
            record.get("specificity"),
            default=0,
            label="specificity",
        )

    return structural_specificity(
        record
    )


def priority(
    record: Mapping[str, Any],
) -> int:
    return numeric_value(
        record.get("priority"),
        default=0,
        label="priority",
    )


def precedence(
    record: Mapping[str, Any],
) -> tuple[int, int, int]:
    return (
        authority_rank(record),
        specificity(record),
        priority(record),
    )


def enforcement_mode(
    record: Mapping[str, Any],
) -> str:
    value = (
        str(
            record.get(
                "enforcement_mode",
                "unspecified",
            )
        )
        .strip()
        .lower()
        .replace("_", "-")
    )

    return value or "unspecified"


def reference_values(
    record: Mapping[str, Any],
    fields: Sequence[str],
) -> list[str]:
    values = []

    for field in fields:
        raw = record.get(field)

        if raw is None:
            continue

        if isinstance(raw, str):
            raw = [raw]

        if not isinstance(
            raw,
            Sequence,
        ):
            raw = [raw]

        for item in raw:
            normalized = str(item).strip()

            if normalized:
                values.append(normalized)

    return sorted(
        set(values)
    )


def override_refs(
    record: Mapping[str, Any],
) -> list[str]:
    return reference_values(
        record,
        (
            "overrides",
            "override_of",
            "exception_of",
        ),
    )


def candidate(
    record: Mapping[str, Any],
    *,
    as_of: Any = None,
    sequence: Any = None,
    default_timezone: str | None = None,
) -> dict[str, Any]:
    identifier = policy_id(record)

    temporal = temporal_evaluate(
        record,
        as_of=as_of,
        sequence=sequence,
        default_timezone=default_timezone,
    )

    decision, decision_reasons = (
        normalize_decision(record)
    )

    score = precedence(record)

    return {
        "id":
            identifier,

        "record":
            clone(dict(record)),

        "decision":
            decision,

        "decision_reason_codes":
            decision_reasons,

        "authority_rank":
            score[0],

        "specificity":
            score[1],

        "priority":
            score[2],

        "precedence":
            list(score),

        "enforcement_mode":
            enforcement_mode(record),

        "override_refs":
            override_refs(record),

        "temporal":
            temporal,

        "temporal_state":
            temporal.get("state"),

        "temporally_applicable":
            temporal.get("applicable"),

        "record_digest":
            digest(record),
    }


def apply_overrides(
    candidates: Sequence[
        Mapping[str, Any]
    ],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    index = {
        str(value["id"]):
            value
        for value in candidates
    }

    suppressed = set()
    applied = []
    blocked = []

    ordered = sorted(
        candidates,
        key=lambda value: (
            tuple(value["precedence"]),
            str(value["id"]),
        ),
        reverse=True,
    )

    for source in ordered:
        if source.get(
            "temporally_applicable"
        ) is not True:
            continue

        source_id = str(
            source["id"]
        )

        for target_id in source.get(
            "override_refs",
            [],
        ):
            target = index.get(
                target_id
            )

            if target is None:
                blocked.append(
                    {
                        "class":
                            "override-target-missing",

                        "source":
                            source_id,

                        "target":
                            target_id,

                        "reason_code":
                            reason_codes[
                                "override_target_missing"
                            ],
                    }
                )

                continue

            if target.get(
                "temporally_applicable"
            ) is not True:
                continue

            source_score = tuple(
                source[
                    "precedence"
                ]
            )

            target_score = tuple(
                target[
                    "precedence"
                ]
            )

            if source_score < target_score:
                blocked.append(
                    {
                        "class":
                            "override-blocked",

                        "source":
                            source_id,

                        "target":
                            target_id,

                        "source_precedence":
                            list(
                                source_score
                            ),

                        "target_precedence":
                            list(
                                target_score
                            ),

                        "reason_code":
                            reason_codes[
                                "override_blocked"
                            ],
                    }
                )

                continue

            suppressed.add(
                target_id
            )

            applied.append(
                {
                    "class":
                        "override-applied",

                    "source":
                        source_id,

                    "target":
                        target_id,

                    "source_precedence":
                        list(
                            source_score
                        ),

                    "target_precedence":
                        list(
                            target_score
                        ),

                    "reason_code":
                        reason_codes[
                            "override_applied"
                        ],
                }
            )

    remaining = [
        clone(dict(value))
        for value in candidates
        if str(value["id"])
        not in suppressed
    ]

    return (
        remaining,
        applied,
        blocked,
    )


def unresolved_temporal_candidates(
    candidates: Sequence[
        Mapping[str, Any]
    ],
) -> list[dict[str, Any]]:
    return [
        clone(dict(value))
        for value in candidates
        if value.get(
            "temporal_state"
        )
        in {
            "indeterminate",
            "invalid",
        }
    ]


def active_candidates(
    candidates: Sequence[
        Mapping[str, Any]
    ],
) -> list[dict[str, Any]]:
    return [
        clone(dict(value))
        for value in candidates
        if value.get(
            "temporally_applicable"
        )
        is True
    ]


def classify_lower_candidates(
    winner_score: tuple[int, int, int],
    winner_decision: str,
    candidates: Sequence[
        Mapping[str, Any]
    ],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    shadowed = []
    redundant = []

    for value in candidates:
        score = tuple(
            value[
                "precedence"
            ]
        )

        if score >= winner_score:
            continue

        if (
            value[
                "decision"
            ]
            == winner_decision
        ):
            redundant.append(
                {
                    "policy":
                        value[
                            "id"
                        ],

                    "decision":
                        value[
                            "decision"
                        ],

                    "precedence":
                        clone(
                            value[
                                "precedence"
                            ]
                        ),

                    "reason_code":
                        reason_codes[
                            "redundant"
                        ],
                }
            )

        else:
            shadowed.append(
                {
                    "policy":
                        value[
                            "id"
                        ],

                    "decision":
                        value[
                            "decision"
                        ],

                    "precedence":
                        clone(
                            value[
                                "precedence"
                            ]
                        ),

                    "reason_code":
                        reason_codes[
                            "shadowed"
                        ],
                }
            )

    return (
        shadowed,
        redundant,
    )


def reason_for_precedence(
    winner_score: tuple[int, int, int],
    next_score: tuple[int, int, int] | None,
) -> str:
    if next_score is None:
        return reason_codes[
            "resolved"
        ]

    if winner_score[0] > next_score[0]:
        return reason_codes[
            "higher_authority"
        ]

    if winner_score[1] > next_score[1]:
        return reason_codes[
            "higher_specificity"
        ]

    if winner_score[2] > next_score[2]:
        return reason_codes[
            "higher_priority"
        ]

    return reason_codes[
        "resolved"
    ]


def arbitrate(
    records: Sequence[
        Mapping[str, Any]
    ],
    *,
    as_of: Any = None,
    sequence: Any = None,
    default_timezone: str | None = None,
) -> dict[str, Any]:
    source_digest = digest(
        records
    )

    candidates = [
        candidate(
            record,
            as_of=as_of,
            sequence=sequence,
            default_timezone=default_timezone,
        )
        for record in records
    ]

    (
        remaining,
        overrides_applied,
        overrides_blocked,
    ) = apply_overrides(
        candidates
    )

    active = active_candidates(
        remaining
    )

    unresolved_temporal = (
        unresolved_temporal_candidates(
            remaining
        )
    )

    active_sorted = sorted(
        active,
        key=lambda value: (
            tuple(
                value[
                    "precedence"
                ]
            ),
            str(value["id"]),
        ),
        reverse=True,
    )

    selected = []
    conflicts = []
    shadowed = []
    redundant = []
    arbitration_reason_codes = []

    if not active_sorted:
        if unresolved_temporal:
            decision = "unknown"
            arbitration_reason_codes.append(
                reason_codes[
                    "temporal_unknown"
                ]
            )

        else:
            decision = "unknown"
            arbitration_reason_codes.append(
                reason_codes[
                    "no_policy"
                ]
            )

        winner_score = None

    else:
        winner_score = tuple(
            active_sorted[
                0
            ][
                "precedence"
            ]
        )

        top = [
            value
            for value in active_sorted
            if tuple(
                value[
                    "precedence"
                ]
            )
            == winner_score
        ]

        top_decisions = sorted(
            {
                str(
                    value[
                        "decision"
                    ]
                )
                for value in top
            }
        )

        if len(
            top_decisions
        ) > 1:
            decision = (
                "authority-required"
            )

            selected = [
                value[
                    "id"
                ]
                for value in top
            ]

            conflicts.append(
                {
                    "class":
                        (
                            "equal-precedence-"
                            "contradiction"
                        ),

                    "policies":
                        clone(
                            selected
                        ),

                    "decisions":
                        top_decisions,

                    "precedence":
                        list(
                            winner_score
                        ),

                    "resolution":
                        "authority-required",

                    "reason_code":
                        reason_codes[
                            (
                                "equal_precedence_"
                                "conflict"
                            )
                        ],
                }
            )

            arbitration_reason_codes.extend(
                [
                    reason_codes[
                        (
                            "equal_precedence_"
                            "conflict"
                        )
                    ],
                    reason_codes[
                        "authority_required"
                    ],
                ]
            )

        else:
            decision = (
                top_decisions[0]
            )

            selected = [
                value[
                    "id"
                ]
                for value in top
            ]

            next_score = next(
                (
                    tuple(
                        value[
                            "precedence"
                        ]
                    )
                    for value
                    in active_sorted
                    if tuple(
                        value[
                            "precedence"
                        ]
                    )
                    < winner_score
                ),
                None,
            )

            arbitration_reason_codes.append(
                reason_for_precedence(
                    winner_score,
                    next_score,
                )
            )

            (
                shadowed,
                redundant,
            ) = classify_lower_candidates(
                winner_score,
                decision,
                active_sorted,
            )

        dangerous_unresolved = [
            value
            for value
            in unresolved_temporal
            if tuple(
                value[
                    "precedence"
                ]
            )
            >= winner_score
        ]

        if dangerous_unresolved:
            decision = "unknown"

            arbitration_reason_codes.append(
                reason_codes[
                    "temporal_unknown"
                ]
            )

            conflicts.append(
                {
                    "class":
                        (
                            "higher-or-equal-"
                            "precedence-temporal-"
                            "unknown"
                        ),

                    "policies": [
                        value[
                            "id"
                        ]
                        for value
                        in dangerous_unresolved
                    ],

                    "resolution":
                        "unknown",

                    "reason_code":
                        reason_codes[
                            "temporal_unknown"
                        ],
                }
            )

    invalid_temporal = [
        value
        for value
        in unresolved_temporal
        if value.get(
            "temporal_state"
        )
        == "invalid"
    ]

    if invalid_temporal:
        arbitration_reason_codes.append(
            reason_codes[
                "temporal_invalid"
            ]
        )

    selected_rows = [
        value
        for value in active_sorted
        if value[
            "id"
        ]
        in selected
    ]

    enforcement_modes = sorted(
        {
            value[
                "enforcement_mode"
            ]
            for value
            in selected_rows
        }
    )

    blocking = (
        decision
        in blocking_decisions
    )

    if (
        decision == "advisory"
        or (
            selected_rows
            and all(
                value[
                    "enforcement_mode"
                ]
                in {
                    "advisory",
                    "warn",
                    "warning",
                    "soft",
                }
                for value
                in selected_rows
            )
        )
    ):
        blocking = False

    trace = {
        "source_policy_count":
            len(
                candidates
            ),

        "temporally_active":
            [
                value[
                    "id"
                ]
                for value
                in active_sorted
            ],

        "temporally_unresolved":
            [
                value[
                    "id"
                ]
                for value
                in unresolved_temporal
            ],

        "overrides_applied":
            clone(
                overrides_applied
            ),

        "overrides_blocked":
            clone(
                overrides_blocked
            ),

        "selected":
            clone(
                selected
            ),

        "winner_precedence":
            (
                list(
                    winner_score
                )
                if winner_score
                is not None
                else None
            ),

        "shadowed":
            clone(
                shadowed
            ),

        "redundant":
            clone(
                redundant
            ),

        "conflicts":
            clone(
                conflicts
            ),
    }

    result = {
        "schema":
            schema,

        "kind":
            "policy-arbitration",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "decision":
            decision,

        "blocking":
            blocking,

        "selected_policy_ids":
            clone(
                selected
            ),

        "selected_enforcement_modes":
            enforcement_modes,

        "reason_codes":
            sorted(
                set(
                    arbitration_reason_codes
                )
            ),

        "precedence_order": [
            "authority",
            "specificity",
            "priority",
        ],

        "authority_precedes_specificity":
            True,

        "specificity_precedes_priority":
            True,

        "enforcement_mode_used_as_precedence":
            False,

        "overrides_applied":
            overrides_applied,

        "overrides_blocked":
            overrides_blocked,

        "shadowed":
            shadowed,

        "redundant":
            redundant,

        "conflicts":
            conflicts,

        "temporal_unresolved": [
            {
                "policy":
                    value[
                        "id"
                    ],

                "state":
                    value[
                        "temporal_state"
                    ],

                "precedence":
                    clone(
                        value[
                            "precedence"
                        ]
                    ),
            }
            for value
            in unresolved_temporal
        ],

        "evaluation_trace":
            trace,

        "candidates":
            candidates,

        "source_digest":
            source_digest,

        "projection_only":
            True,

        "source_state_mutated":
            (
                source_digest
                != digest(
                    records
                )
            ),

        "authority_transfer":
            False,
    }

    if result[
        "source_state_mutated"
    ]:
        raise living_policy_arbitration_error(
            "source policies were mutated"
        )

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key != "digest"
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

        "authority_effect":
            authority_effect,

        "authority_precedence":
            True,

        "specificity_precedence":
            True,

        "priority_precedence":
            True,

        "equal_precedence_conflict_preserved":
            True,

        "override_authority_checked":
            True,

        "temporal_uncertainty_preserved":
            True,

        "shadow_detection":
            True,

        "redundancy_detection":
            True,

        "deny_wins_shortcut":
            False,

        "projection_only":
            True,

        "authority_transfer":
            False,

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    higher_authority = arbitrate(
        [
            {
                "id":
                    "policy:high",

                "authority_class":
                    "accepted_decision",

                "effect":
                    "allow",
            },
            {
                "id":
                    "policy:low",

                "authority_class":
                    "inference",

                "effect":
                    "deny",
            },
        ]
    )

    if (
        higher_authority[
            "decision"
        ]
        != "pass"
    ):
        raise living_policy_arbitration_error(
            (
                "higher authority did not "
                "control arbitration"
            )
        )

    equal_conflict = arbitrate(
        [
            {
                "id":
                    "policy:left",

                "authority_class":
                    "constitutional_canon",

                "specificity":
                    5,

                "effect":
                    "allow",
            },
            {
                "id":
                    "policy:right",

                "authority_class":
                    "constitutional_canon",

                "specificity":
                    5,

                "effect":
                    "deny",
            },
        ]
    )

    if (
        equal_conflict[
            "decision"
        ]
        != "authority-required"
    ):
        raise living_policy_arbitration_error(
            (
                "equal-precedence conflict "
                "was silently reconciled"
            )
        )

    specificity_case = arbitrate(
        [
            {
                "id":
                    "policy:general",

                "authority_class":
                    "constitutional_canon",

                "specificity":
                    1,

                "effect":
                    "allow",
            },
            {
                "id":
                    "policy:specific",

                "authority_class":
                    "constitutional_canon",

                "specificity":
                    10,

                "effect":
                    "deny",
            },
        ]
    )

    if (
        specificity_case[
            "decision"
        ]
        != "fail"
    ):
        raise living_policy_arbitration_error(
            "specificity precedence failed"
        )

    blocked_override = arbitrate(
        [
            {
                "id":
                    "policy:protected",

                "authority_class":
                    "accepted_decision",

                "effect":
                    "deny",
            },
            {
                "id":
                    "policy:weak-override",

                "authority_class":
                    "inference",

                "effect":
                    "allow",

                "overrides":
                    [
                        "policy:protected"
                    ],
            },
        ]
    )

    if (
        blocked_override[
            "decision"
        ]
        != "fail"
    ):
        raise living_policy_arbitration_error(
            (
                "lower authority override "
                "weakened protected policy"
            )
        )

    if not blocked_override[
        "overrides_blocked"
    ]:
        raise living_policy_arbitration_error(
            (
                "blocked override "
                "was not exposed"
            )
        )

    valid_override = arbitrate(
        [
            {
                "id":
                    "policy:base",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "deny",
            },
            {
                "id":
                    "policy:exception",

                "authority_class":
                    "constitutional_canon",

                "specificity":
                    10,

                "effect":
                    "allow",

                "exception_of":
                    "policy:base",
            },
        ]
    )

    if (
        valid_override[
            "decision"
        ]
        != "pass"
    ):
        raise living_policy_arbitration_error(
            (
                "valid higher-precedence "
                "exception failed"
            )
        )

    temporal_case = arbitrate(
        [
            {
                "id":
                    "policy:expired",

                "authority_class":
                    "accepted_decision",

                "effect":
                    "deny",

                "valid_until":
                    "2026-09-01T00:00:00Z",
            },
            {
                "id":
                    "policy:current",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            },
        ],
        as_of=
            "2026-09-02T00:00:00Z",
    )

    if (
        temporal_case[
            "decision"
        ]
        != "pass"
    ):
        raise living_policy_arbitration_error(
            (
                "expired policy remained "
                "active"
            )
        )

    temporal_unknown = arbitrate(
        [
            {
                "id":
                    "policy:uncertain-time",

                "authority_class":
                    "accepted_decision",

                "effect":
                    "deny",

                "valid_from":
                    "2026-09-01T00:00:00Z",
            },
            {
                "id":
                    "policy:known",

                "authority_class":
                    "constitutional_canon",

                "effect":
                    "allow",
            },
        ]
    )

    if (
        temporal_unknown[
            "decision"
        ]
        != "unknown"
    ):
        raise living_policy_arbitration_error(
            (
                "higher-authority temporal "
                "unknown was collapsed"
            )
        )

    source = [
        {
            "id":
                "policy:immutable",

            "authority_class":
                "constitutional_canon",

            "effect":
                "allow",
        }
    ]

    before = digest(
        source
    )

    first = arbitrate(
        source
    )

    second = arbitrate(
        source
    )

    if first != second:
        raise living_policy_arbitration_error(
            "arbitration is not deterministic"
        )

    if before != digest(
        source
    ):
        raise living_policy_arbitration_error(
            "arbitration mutated source"
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

        "authority_precedence":
            True,

        "specificity_precedence":
            True,

        "equal_precedence_conflict_preserved":
            True,

        "lower_authority_override_blocked":
            True,

        "valid_exception_applied":
            True,

        "expired_policy_excluded":
            True,

        "temporal_unknown_preserved":
            True,

        "shadow_detection":
            True,

        "redundancy_detection":
            True,

        "deny_wins_shortcut":
            False,

        "deterministic":
            True,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "arbitrate",
    "candidate",
    "living_policy_arbitration_error",
    "selftest",
    "status",
]
