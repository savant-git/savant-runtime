#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


from runtime.living_governance import (
    append_event,
    authority_order,
    canonical_json,
    next_version,
    project,
    read_events,
    resolved_records,
    stream_records,
    utc_now,
)


schema = "savant.living-policy.v1"
stream = "policies"

record_types = {
    "rule",
    "permission",
    "invariant",
    "decision",
    "unknown",
    "risk",
    "compatibility",
    "dependency",
    "milestone",
    "structure",
    "terminology",
    "policy",
    "exception",
    "evidence",
    "assumption",
    "hypothesis",
    "contradiction",
    "conclusion",
    "blocker",
}

effects = {
    "allow",
    "deny",
    "conditional",
    "require_authority",
}

enforcement_modes = {
    "advisory",
    "warn",
    "block",
    "require_authority",
}

epistemic_states = {
    "fact",
    "assertion",
    "inference",
    "estimate",
    "speculation",
    "unknown",
    "projection",
}

evaluation_states = {
    "pass",
    "fail",
    "advisory",
    "unknown",
    "authority_required",
    "not_applicable",
}


class living_policy_error(
    RuntimeError
):
    pass


def sha256_value(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def parse_timestamp(
    value: str | None,
) -> datetime | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    if text.endswith(
        "Z"
    ):
        text = (
            text[:-1]
            + "+00:00"
        )

    try:
        result = datetime.fromisoformat(
            text
        )

    except ValueError as exc:
        raise living_policy_error(
            (
                "invalid timestamp: "
                + str(
                    value
                )
            )
        ) from exc

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=timezone.utc
        )

    return result.astimezone(
        timezone.utc
    )


def normalize_string_list(
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
        list,
    ):
        raise living_policy_error(
            "expected string or list"
        )

    return sorted(
        {
            str(
                item
            ).strip()
            for item in value
            if str(
                item
            ).strip()
        }
    )


def normalize_mapping(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise living_policy_error(
            "expected object"
        )

    return {
        str(
            key
        ):
            item
        for key, item
        in value.items()
    }


def normalize_relationships(
    value: Any,
) -> list[dict[str, str]]:
    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        raise living_policy_error(
            "relationships must be a list"
        )

    output = []

    for relationship in value:
        if not isinstance(
            relationship,
            Mapping,
        ):
            raise living_policy_error(
                "relationship must be an object"
            )

        kind = str(
            relationship.get(
                "kind",
                "",
            )
        ).strip()

        target = str(
            relationship.get(
                "target",
                "",
            )
        ).strip()

        if (
            not kind
            or not target
        ):
            raise living_policy_error(
                (
                    "relationship requires "
                    "kind and target"
                )
            )

        output.append(
            {
                "kind":
                    kind,

                "target":
                    target,
            }
        )

    return sorted(
        output,
        key=lambda item: (
            item[
                "kind"
            ],
            item[
                "target"
            ],
        ),
    )


def normalize_semantic(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = normalize_mapping(
        value
    )

    record_type = str(
        source.get(
            "type",
            "policy",
        )
    ).strip()

    if record_type not in record_types:
        raise living_policy_error(
            (
                "unsupported semantic type: "
                + record_type
            )
        )

    effect = str(
        source.get(
            "effect",
            "conditional",
        )
    ).strip()

    if effect not in effects:
        raise living_policy_error(
            (
                "unsupported effect: "
                + effect
            )
        )

    enforcement = str(
        source.get(
            "enforcement",
            "advisory",
        )
    ).strip()

    if enforcement not in enforcement_modes:
        raise living_policy_error(
            (
                "unsupported enforcement mode: "
                + enforcement
            )
        )

    epistemic_state = str(
        source.get(
            "epistemic_state",
            "assertion",
        )
    ).strip()

    if epistemic_state not in epistemic_states:
        raise living_policy_error(
            (
                "unsupported epistemic state: "
                + epistemic_state
            )
        )

    confidence_value = source.get(
        "confidence"
    )

    confidence = None

    if confidence_value is not None:
        confidence = float(
            confidence_value
        )

        if not (
            0.0
            <= confidence
            <= 1.0
        ):
            raise living_policy_error(
                (
                    "confidence must be "
                    "between 0 and 1"
                )
            )

    effective_from = source.get(
        "effective_from"
    )

    effective_until = source.get(
        "effective_until"
    )

    from_time = parse_timestamp(
        effective_from
    )

    until_time = parse_timestamp(
        effective_until
    )

    if (
        from_time is not None
        and until_time is not None
        and until_time
        < from_time
    ):
        raise living_policy_error(
            (
                "effective_until precedes "
                "effective_from"
            )
        )

    reason_code = str(
        source.get(
            "reason_code",
            "",
        )
    ).strip()

    if (
        reason_code
        and reason_code
        != reason_code.lower()
    ):
        raise living_policy_error(
            "reason_code must be lowercase"
        )

    predicate = source.get(
        "predicate"
    )

    if (
        predicate is not None
        and not isinstance(
            predicate,
            Mapping,
        )
    ):
        raise living_policy_error(
            "predicate must be an object"
        )

    return {
        "type":
            record_type,

        "scope":
            normalize_string_list(
                source.get(
                    "scope"
                )
            ),

        "selectors":
            normalize_mapping(
                source.get(
                    "selectors"
                )
            ),

        "subjects":
            normalize_string_list(
                source.get(
                    "subjects"
                )
            ),

        "targets":
            normalize_string_list(
                source.get(
                    "targets"
                )
            ),

        "actions":
            normalize_string_list(
                source.get(
                    "actions"
                )
            ),

        "predicate":
            (
                dict(
                    predicate
                )
                if predicate
                is not None
                else None
            ),

        "effect":
            effect,

        "enforcement":
            enforcement,

        "specificity":
            int(
                source.get(
                    "specificity",
                    0,
                )
            ),

        "epistemic_state":
            epistemic_state,

        "confidence":
            confidence,

        "evidence_requirements":
            normalize_string_list(
                source.get(
                    "evidence_requirements"
                )
            ),

        "exceptions":
            normalize_string_list(
                source.get(
                    "exceptions"
                )
            ),

        "effective_from":
            (
                str(
                    effective_from
                )
                if effective_from
                is not None
                else None
            ),

        "effective_until":
            (
                str(
                    effective_until
                )
                if effective_until
                is not None
                else None
            ),

        "reason":
            str(
                source.get(
                    "reason",
                    "",
                )
            ).strip(),

        "reason_code":
            reason_code,

        "remediation":
            str(
                source.get(
                    "remediation",
                    "",
                )
            ).strip(),

        "metadata":
            normalize_mapping(
                source.get(
                    "metadata"
                )
            ),
    }


def assert_policy(
    *,
    semantic_id: str,
    text: str,
    semantic: Mapping[str, Any],
    authority: str = "current_user_directive",
    priority: int = 1000,
    status: str = "active",
    supersedes: Iterable[str] = (),
    dependencies: Iterable[str] = (),
    relationships: Iterable[
        Mapping[str, Any]
    ] = (),
    asserted_by: str = "user",
    sources: Iterable[str] = (),
) -> dict[str, Any]:
    semantic_id = str(
        semantic_id
    ).strip()

    if not semantic_id:
        raise living_policy_error(
            "semantic id is required"
        )

    if semantic_id != semantic_id.lower():
        raise living_policy_error(
            "semantic id must be lowercase"
        )

    text = str(
        text
    ).strip()

    if not text:
        raise living_policy_error(
            "policy text is required"
        )

    if authority not in authority_order:
        raise living_policy_error(
            (
                "unknown authority: "
                + authority
            )
        )

    normalized = normalize_semantic(
        semantic
    )

    provenance = {
        "asserted_by":
            str(
                asserted_by
            ).strip()
            or "user",

        "method":
            "living-policy",

        "sources":
            sorted(
                {
                    str(
                        source
                    ).strip()
                    for source
                    in sources
                    if str(
                        source
                    ).strip()
                }
            ),

        "created_at":
            utc_now(),
    }

    record = {
        "schema":
            schema,

        "id":
            semantic_id,

        "stream":
            stream,

        "version":
            next_version(
                stream,
                semantic_id,
            ),

        "status":
            str(
                status
            ).strip()
            or "active",

        "authority":
            authority,

        "authority_rank":
            authority_order[
                authority
            ],

        "priority":
            int(
                priority
            ),

        "text":
            text,

        "supersedes":
            sorted(
                {
                    str(
                        value
                    ).strip()
                    for value
                    in supersedes
                    if str(
                        value
                    ).strip()
                }
            ),

        "dependencies":
            sorted(
                {
                    str(
                        value
                    ).strip()
                    for value
                    in dependencies
                    if str(
                        value
                    ).strip()
                }
            ),

        "relationships":
            normalize_relationships(
                list(
                    relationships
                )
            ),

        "provenance":
            provenance,

        "semantic":
            normalized,
    }

    event = append_event(
        record
    )

    projection = project()

    return {
        "event":
            event,

        "projection":
            projection,
    }


def context_value(
    context: Mapping[str, Any],
    path: str,
) -> tuple[
    bool,
    Any,
]:
    current: Any = context

    for part in str(
        path
    ).split(
        "."
    ):
        if not isinstance(
            current,
            Mapping,
        ):
            return (
                False,
                None,
            )

        if part not in current:
            return (
                False,
                None,
            )

        current = current[
            part
        ]

    return (
        True,
        current,
    )


def compare(
    *,
    actual: Any,
    operator: str,
    expected: Any,
) -> bool | None:
    if operator == "eq":
        return (
            actual
            == expected
        )

    if operator == "neq":
        return (
            actual
            != expected
        )

    if operator == "exists":
        return bool(
            actual
        ) == bool(
            expected
        )

    if operator == "in":
        if not isinstance(
            expected,
            list,
        ):
            return None

        return actual in expected

    if operator == "not_in":
        if not isinstance(
            expected,
            list,
        ):
            return None

        return actual not in expected

    if operator == "contains":
        try:
            return (
                expected
                in actual
            )

        except TypeError:
            return None

    if operator == "prefix":
        if not isinstance(
            actual,
            str,
        ):
            return None

        return actual.startswith(
            str(
                expected
            )
        )

    if operator == "suffix":
        if not isinstance(
            actual,
            str,
        ):
            return None

        return actual.endswith(
            str(
                expected
            )
        )

    if operator == "regex":
        if not isinstance(
            actual,
            str,
        ):
            return None

        try:
            return (
                re.search(
                    str(
                        expected
                    ),
                    actual,
                )
                is not None
            )

        except re.error:
            return None

    if operator == "lt":
        try:
            return (
                actual
                < expected
            )

        except TypeError:
            return None

    if operator == "lte":
        try:
            return (
                actual
                <= expected
            )

        except TypeError:
            return None

    if operator == "gt":
        try:
            return (
                actual
                > expected
            )

        except TypeError:
            return None

    if operator == "gte":
        try:
            return (
                actual
                >= expected
            )

        except TypeError:
            return None

    return None


def evaluate_predicate(
    predicate: Mapping[str, Any] | None,
    context: Mapping[str, Any],
) -> tuple[
    bool | None,
    dict[str, Any],
]:
    if predicate is None:
        return (
            True,
            {
                "operator":
                    "none",

                "result":
                    True,
            },
        )

    if "all" in predicate:
        children = predicate.get(
            "all"
        )

        if not isinstance(
            children,
            list,
        ):
            return (
                None,
                {
                    "operator":
                        "all",

                    "result":
                        None,

                    "reason":
                        "children_not_list",
                },
            )

        traces = []

        has_unknown = False

        for child in children:
            if not isinstance(
                child,
                Mapping,
            ):
                result = None

                trace = {
                    "result":
                        None,

                    "reason":
                        "child_not_object",
                }

            else:
                result, trace = (
                    evaluate_predicate(
                        child,
                        context,
                    )
                )

            traces.append(
                trace
            )

            if result is False:
                return (
                    False,
                    {
                        "operator":
                            "all",

                        "result":
                            False,

                        "children":
                            traces,
                    },
                )

            if result is None:
                has_unknown = True

        result = (
            None
            if has_unknown
            else True
        )

        return (
            result,
            {
                "operator":
                    "all",

                "result":
                    result,

                "children":
                    traces,
            },
        )

    if "any" in predicate:
        children = predicate.get(
            "any"
        )

        if not isinstance(
            children,
            list,
        ):
            return (
                None,
                {
                    "operator":
                        "any",

                    "result":
                        None,

                    "reason":
                        "children_not_list",
                },
            )

        traces = []

        has_unknown = False

        for child in children:
            if not isinstance(
                child,
                Mapping,
            ):
                result = None

                trace = {
                    "result":
                        None,

                    "reason":
                        "child_not_object",
                }

            else:
                result, trace = (
                    evaluate_predicate(
                        child,
                        context,
                    )
                )

            traces.append(
                trace
            )

            if result is True:
                return (
                    True,
                    {
                        "operator":
                            "any",

                        "result":
                            True,

                        "children":
                            traces,
                    },
                )

            if result is None:
                has_unknown = True

        result = (
            None
            if has_unknown
            else False
        )

        return (
            result,
            {
                "operator":
                    "any",

                "result":
                    result,

                "children":
                    traces,
            },
        )

    if "not" in predicate:
        child = predicate.get(
            "not"
        )

        if not isinstance(
            child,
            Mapping,
        ):
            return (
                None,
                {
                    "operator":
                        "not",

                    "result":
                        None,

                    "reason":
                        "child_not_object",
                },
            )

        result, trace = evaluate_predicate(
            child,
            context,
        )

        inverted = (
            None
            if result is None
            else not result
        )

        return (
            inverted,
            {
                "operator":
                    "not",

                "result":
                    inverted,

                "child":
                    trace,
            },
        )

    field = str(
        predicate.get(
            "field",
            "",
        )
    ).strip()

    operator = str(
        predicate.get(
            "op",
            "eq",
        )
    ).strip()

    expected = predicate.get(
        "value"
    )

    if not field:
        return (
            None,
            {
                "operator":
                    operator,

                "result":
                    None,

                "reason":
                    "field_missing",
            },
        )

    found, actual = context_value(
        context,
        field,
    )

    if not found:
        return (
            None,
            {
                "field":
                    field,

                "operator":
                    operator,

                "expected":
                    expected,

                "result":
                    None,

                "reason":
                    "context_value_unknown",
            },
        )

    result = compare(
        actual=actual,
        operator=operator,
        expected=expected,
    )

    return (
        result,
        {
            "field":
                field,

            "operator":
                operator,

            "expected":
                expected,

            "actual":
                actual,

            "result":
                result,
        },
    )


def selector_result(
    expected: Any,
    actual: Any,
) -> bool:
    if isinstance(
        expected,
        list,
    ):
        if isinstance(
            actual,
            list,
        ):
            return bool(
                set(
                    str(
                        value
                    )
                    for value
                    in expected
                )
                & set(
                    str(
                        value
                    )
                    for value
                    in actual
                )
            )

        return str(
            actual
        ) in {
            str(
                value
            )
            for value
            in expected
        }

    if isinstance(
        actual,
        list,
    ):
        return str(
            expected
        ) in {
            str(
                value
            )
            for value
            in actual
        }

    return (
        actual
        == expected
    )


def temporal_state(
    semantic: Mapping[str, Any],
    *,
    at: datetime,
) -> tuple[
    bool,
    str,
]:
    effective_from = parse_timestamp(
        semantic.get(
            "effective_from"
        )
    )

    effective_until = parse_timestamp(
        semantic.get(
            "effective_until"
        )
    )

    if (
        effective_from is not None
        and at < effective_from
    ):
        return (
            False,
            "not_yet_effective",
        )

    if (
        effective_until is not None
        and at > effective_until
    ):
        return (
            False,
            "expired",
        )

    return (
        True,
        "effective",
    )


def applicability(
    record: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    at: datetime,
) -> dict[str, Any]:
    semantic = normalize_semantic(
        record.get(
            "semantic"
        )
    )

    temporal, temporal_reason = (
        temporal_state(
            semantic,
            at=at,
        )
    )

    if not temporal:
        return {
            "applicable":
                False,

            "known":
                True,

            "reason":
                temporal_reason,

            "selectors":
                [],
        }

    selectors = semantic.get(
        "selectors",
        {}
    )

    traces = []

    unknown = False

    for field in sorted(
        selectors
    ):
        expected = selectors[
            field
        ]

        found, actual = context_value(
            context,
            field,
        )

        if not found:
            unknown = True

            traces.append(
                {
                    "field":
                        field,

                    "expected":
                        expected,

                    "known":
                        False,

                    "matches":
                        None,
                }
            )

            continue

        matches = selector_result(
            expected,
            actual,
        )

        traces.append(
            {
                "field":
                    field,

                "expected":
                    expected,

                "actual":
                    actual,

                "known":
                    True,

                "matches":
                    matches,
            }
        )

        if not matches:
            return {
                "applicable":
                    False,

                "known":
                    True,

                "reason":
                    "selector_mismatch",

                "selectors":
                    traces,
            }

    if unknown:
        return {
            "applicable":
                None,

            "known":
                False,

            "reason":
                "selector_context_unknown",

            "selectors":
                traces,
        }

    return {
        "applicable":
            True,

        "known":
            True,

        "reason":
            "applicable",

        "selectors":
            traces,
    }


def policy_records(
    events: Iterable[
        Mapping[str, Any]
    ] | None = None,
) -> list[dict[str, Any]]:
    if events is None:
        values = stream_records(
            stream
        )

    else:
        values = [
            record
            for record
            in resolved_records(
                events
            )
            if record.get(
                "stream"
            )
            == stream
        ]

    return sorted(
        [
            dict(
                record
            )
            for record
            in values
        ],
        key=lambda record: (
            int(
                record.get(
                    "authority_rank",
                    1000,
                )
            ),
            int(
                record.get(
                    "priority",
                    1000,
                )
            ),
            -int(
                normalize_semantic(
                    record.get(
                        "semantic"
                    )
                ).get(
                    "specificity",
                    0,
                )
            ),
            str(
                record.get(
                    "id",
                    "",
                )
            ),
        ),
    )


def evaluate_record(
    record: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    at: datetime,
) -> dict[str, Any]:
    semantic = normalize_semantic(
        record.get(
            "semantic"
        )
    )

    applicable = applicability(
        record,
        context,
        at=at,
    )

    if applicable[
        "applicable"
    ] is False:
        return {
            "id":
                record[
                    "id"
                ],

            "version":
                record[
                    "version"
                ],

            "state":
                "not_applicable",

            "effect":
                semantic[
                    "effect"
                ],

            "enforcement":
                semantic[
                    "enforcement"
                ],

            "applicability":
                applicable,

            "predicate":
                None,

            "reason_code":
                semantic[
                    "reason_code"
                ],

            "remediation":
                semantic[
                    "remediation"
                ],
        }

    if applicable[
        "applicable"
    ] is None:
        return {
            "id":
                record[
                    "id"
                ],

            "version":
                record[
                    "version"
                ],

            "state":
                "unknown",

            "effect":
                semantic[
                    "effect"
                ],

            "enforcement":
                semantic[
                    "enforcement"
                ],

            "applicability":
                applicable,

            "predicate":
                None,

            "reason_code":
                (
                    semantic[
                        "reason_code"
                    ]
                    or "selector_context_unknown"
                ),

            "remediation":
                semantic[
                    "remediation"
                ],
        }

    predicate_result, predicate_trace = (
        evaluate_predicate(
            semantic.get(
                "predicate"
            ),
            context,
        )
    )

    if predicate_result is None:
        state = "unknown"

    elif predicate_result is False:
        state = "pass"

    else:
        if (
            semantic[
                "effect"
            ]
            == "require_authority"
            or semantic[
                "enforcement"
            ]
            == "require_authority"
        ):
            state = (
                "authority_required"
            )

        elif semantic[
            "effect"
        ] == "deny":
            if semantic[
                "enforcement"
            ] == "block":
                state = "fail"

            else:
                state = "advisory"

        elif semantic[
            "enforcement"
        ] in {
            "advisory",
            "warn",
        }:
            state = "advisory"

        else:
            state = "pass"

    return {
        "id":
            record[
                "id"
            ],

        "version":
            record[
                "version"
            ],

        "state":
            state,

        "effect":
            semantic[
                "effect"
            ],

        "enforcement":
            semantic[
                "enforcement"
            ],

        "authority":
            record[
                "authority"
            ],

        "authority_rank":
            record[
                "authority_rank"
            ],

        "priority":
            record[
                "priority"
            ],

        "specificity":
            semantic[
                "specificity"
            ],

        "applicability":
            applicable,

        "predicate":
            predicate_trace,

        "evidence_requirements":
            semantic[
                "evidence_requirements"
            ],

        "exceptions":
            semantic[
                "exceptions"
            ],

        "reason":
            semantic[
                "reason"
            ],

        "reason_code":
            semantic[
                "reason_code"
            ],

        "remediation":
            semantic[
                "remediation"
            ],

        "epistemic_state":
            semantic[
                "epistemic_state"
            ],

        "confidence":
            semantic[
                "confidence"
            ],
    }


def evaluate(
    context: Mapping[str, Any],
    *,
    at: str | None = None,
    records: Iterable[
        Mapping[str, Any]
    ] | None = None,
) -> dict[str, Any]:
    timestamp = (
        parse_timestamp(
            at
        )
        or datetime.now(
            timezone.utc
        )
    )

    values = (
        [
            dict(
                record
            )
            for record
            in records
        ]
        if records is not None
        else policy_records()
    )

    trace = [
        evaluate_record(
            record,
            context,
            at=timestamp,
        )
        for record
        in values
    ]

    failures = [
        item
        for item
        in trace
        if item[
            "state"
        ]
        == "fail"
    ]

    authority_required = [
        item
        for item
        in trace
        if item[
            "state"
        ]
        == "authority_required"
    ]

    unknowns = [
        item
        for item
        in trace
        if item[
            "state"
        ]
        == "unknown"
    ]

    advisories = [
        item
        for item
        in trace
        if item[
            "state"
        ]
        == "advisory"
    ]

    if failures:
        decision = "deny"

    elif authority_required:
        decision = (
            "authority_required"
        )

    elif unknowns:
        decision = "unknown"

    elif advisories:
        decision = "advisory"

    else:
        decision = "allow"

    receipt_payload = {
        "context":
            context,

        "at":
            timestamp.isoformat(),

        "decision":
            decision,

        "trace":
            trace,
    }

    digest = sha256_value(
        receipt_payload
    )

    return {
        "schema":
            (
                "savant.living-policy."
                "evaluation.v1"
            ),

        "owner":
            "living-governance",

        "authority_effect":
            "evaluation",

        "decision":
            decision,

        "allowed":
            (
                True
                if decision
                in {
                    "allow",
                    "advisory",
                }
                else (
                    False
                    if decision
                    == "deny"
                    else None
                )
            ),

        "at":
            timestamp.isoformat(),

        "considered":
            len(
                trace
            ),

        "applicable":
            sum(
                1
                for item
                in trace
                if item[
                    "state"
                ]
                != "not_applicable"
            ),

        "failures":
            len(
                failures
            ),

        "authority_required":
            len(
                authority_required
            ),

        "unknowns":
            len(
                unknowns
            ),

        "advisories":
            len(
                advisories
            ),

        "reason_codes":
            sorted(
                {
                    str(
                        item.get(
                            "reason_code",
                            "",
                        )
                    )
                    for item
                    in trace
                    if str(
                        item.get(
                            "reason_code",
                            "",
                        )
                    )
                }
            ),

        "trace":
            trace,

        "receipt_digest":
            digest,

        "credential_values_exposed":
            False,
    }


def events_until_sequence(
    sequence: int,
) -> list[dict[str, Any]]:
    if sequence < 
