#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Mapping, Sequence


owner = "living-governance"
authority_effect = "none"
schema = "savant.living-governance.policy-temporal.v1"


states = {
    "active",
    "scheduled",
    "expired",
    "indeterminate",
    "invalid",
}


reason_codes = {
    "active":
        "lg.temporal.active",

    "unbounded":
        "lg.temporal.unbounded",

    "scheduled":
        "lg.temporal.scheduled",

    "expired":
        "lg.temporal.expired",

    "missing_timestamp":
        "lg.temporal.timestamp-required",

    "missing_sequence":
        "lg.temporal.sequence-required",

    "invalid_timestamp":
        "lg.temporal.invalid-timestamp",

    "invalid_sequence":
        "lg.temporal.invalid-sequence",

    "invalid_timestamp_range":
        "lg.temporal.invalid-timestamp-range",

    "invalid_sequence_range":
        "lg.temporal.invalid-sequence-range",

    "ambiguous_timezone":
        "lg.temporal.ambiguous-timezone",
}


timestamp_start_fields = (
    "valid_from",
    "effective_from",
    "not_before",
    "starts_at",
)

timestamp_end_fields = (
    "valid_until",
    "expires_at",
    "not_after",
    "ends_at",
)

sequence_start_fields = (
    "valid_from_sequence",
    "effective_from_sequence",
    "sequence_from",
    "not_before_sequence",
)

sequence_end_fields = (
    "valid_until_sequence",
    "expires_at_sequence",
    "sequence_until",
    "not_after_sequence",
)


class living_policy_temporal_error(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class parsed_timestamp:
    value: datetime
    source: str
    original: Any
    precision: str


@dataclass(frozen=True)
class temporal_bounds:
    start: parsed_timestamp | None
    end: parsed_timestamp | None
    start_inclusive: bool
    end_inclusive: bool
    sequence_start: int | None
    sequence_end: int | None
    sequence_start_inclusive: bool
    sequence_end_inclusive: bool
    sources: dict[str, str]


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


def require_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise living_policy_temporal_error(
            label
            + " must be a JSON object"
        )

    return value


def normalize_timezone_name(
    value: Any,
) -> str | None:
    if value is None:
        return None

    normalized = str(
        value
    ).strip()

    return (
        normalized
        if normalized
        else None
    )


def resolve_timezone(
    value: str | None,
) -> timezone | None:
    if value is None:
        return None

    normalized = (
        value.strip()
        .upper()
    )

    if normalized in {
        "UTC",
        "Z",
        "+00:00",
        "-00:00",
    }:
        return timezone.utc

    if (
        len(normalized)
        == 6
        and normalized[0]
        in {
            "+",
            "-",
        }
        and normalized[3]
        == ":"
    ):
        try:
            hours = int(
                normalized[1:3]
            )

            minutes = int(
                normalized[4:6]
            )

        except ValueError:
            return None

        if (
            hours > 23
            or minutes > 59
        ):
            return None

        total_minutes = (
            hours * 60
            + minutes
        )

        if normalized[0] == "-":
            total_minutes *= -1

        from datetime import timedelta

        return timezone(
            timedelta(
                minutes=
                    total_minutes
            )
        )

    return None


def parse_datetime_value(
    value: Any,
    *,
    source: str,
    default_timezone:
        str | None = None,
) -> parsed_timestamp:
    if isinstance(
        value,
        datetime,
    ):
        parsed = value
        precision = "datetime"

    elif isinstance(
        value,
        date,
    ):
        parsed = datetime.combine(
            value,
            time.min,
        )

        precision = "date"

    elif isinstance(
        value,
        str,
    ):
        raw = value.strip()

        if not raw:
            raise living_policy_temporal_error(
                (
                    "empty temporal timestamp "
                    "at "
                    + source
                )
            )

        normalized = raw

        if normalized.endswith(
            "Z"
        ):
            normalized = (
                normalized[:-1]
                + "+00:00"
            )

        try:
            if (
                len(normalized)
                == 10
                and normalized[4]
                == "-"
                and normalized[7]
                == "-"
            ):
                parsed_date = (
                    date.fromisoformat(
                        normalized
                    )
                )

                parsed = datetime.combine(
                    parsed_date,
                    time.min,
                )

                precision = "date"

            else:
                parsed = (
                    datetime.fromisoformat(
                        normalized
                    )
                )

                precision = "datetime"

        except ValueError as exc:
            raise living_policy_temporal_error(
                (
                    "invalid ISO temporal "
                    "timestamp at "
                    + source
                    + ": "
                    + raw
                )
            ) from exc

    else:
        raise living_policy_temporal_error(
            (
                "unsupported temporal "
                "timestamp at "
                + source
            )
        )

    if (
        parsed.tzinfo is None
        or parsed.utcoffset()
        is None
    ):
        resolved_timezone = (
            resolve_timezone(
                default_timezone
            )
        )

        if resolved_timezone is None:
            raise living_policy_temporal_error(
                (
                    "timezone required for "
                    "naive temporal timestamp "
                    "at "
                    + source
                )
            )

        parsed = parsed.replace(
            tzinfo=
                resolved_timezone
        )

    return parsed_timestamp(
        value=
            parsed.astimezone(
                timezone.utc
            ),

        source=
            source,

        original=
            clone(
                value
            ),

        precision=
            precision,
    )


def integer_sequence(
    value: Any,
    *,
    source: str,
) -> int:
    if isinstance(
        value,
        bool,
    ):
        raise living_policy_temporal_error(
            (
                "invalid sequence at "
                + source
            )
        )

    if isinstance(
        value,
        int,
    ):
        parsed = value

    elif (
        isinstance(
            value,
            str,
        )
        and value.strip()
    ):
        try:
            parsed = int(
                value.strip()
            )

        except ValueError as exc:
            raise living_policy_temporal_error(
                (
                    "invalid sequence at "
                    + source
                )
            ) from exc

    else:
        raise living_policy_temporal_error(
            (
                "invalid sequence at "
                + source
            )
        )

    if parsed < 0:
        raise living_policy_temporal_error(
            (
                "sequence cannot be negative "
                "at "
                + source
            )
        )

    return parsed


def first_declared(
    containers: Sequence[
        tuple[
            str,
            Mapping[str, Any],
        ]
    ],
    fields: Sequence[str],
) -> tuple[
    Any,
    str,
] | tuple[
    None,
    None,
]:
    for prefix, container in containers:
        for field in fields:
            if (
                field in container
                and container.get(
                    field
                )
                is not None
            ):
                return (
                    container.get(
                        field
                    ),
                    (
                        prefix
                        + field
                    ),
                )

    return (
        None,
        None,
    )


def temporal_metadata(
    record: Mapping[str, Any],
) -> Mapping[str, Any]:
    value = record.get(
        "temporal_validity"
    )

    if isinstance(
        value,
        Mapping,
    ):
        return value

    return {}


def extract_bounds(
    record: Mapping[str, Any],
) -> temporal_bounds:
    record = require_mapping(
        record,
        "record",
    )

    metadata = temporal_metadata(
        record
    )

    containers = (
        (
            "",
            record,
        ),
        (
            "temporal_validity.",
            metadata,
        ),
    )

    default_timezone = (
        normalize_timezone_name(
            metadata.get(
                "timezone"
            )
            or record.get(
                "timezone"
            )
        )
    )

    start_raw, start_source = (
        first_declared(
            containers,
            timestamp_start_fields,
        )
    )

    end_raw, end_source = (
        first_declared(
            containers,
            timestamp_end_fields,
        )
    )

    sequence_start_raw, sequence_start_source = (
        first_declared(
            containers,
            sequence_start_fields,
        )
    )

    sequence_end_raw, sequence_end_source = (
        first_declared(
            containers,
            sequence_end_fields,
        )
    )

    start = (
        parse_datetime_value(
            start_raw,
            source=
                str(
                    start_source
                ),
            default_timezone=
                default_timezone,
        )
        if start_source
        else None
    )

    end = (
        parse_datetime_value(
            end_raw,
            source=
                str(
                    end_source
                ),
            default_timezone=
                default_timezone,
        )
        if end_source
        else None
    )

    sequence_start = (
        integer_sequence(
            sequence_start_raw,
            source=
                str(
                    sequence_start_source
                ),
        )
        if sequence_start_source
        else None
    )

    sequence_end = (
        integer_sequence(
            sequence_end_raw,
            source=
                str(
                    sequence_end_source
                ),
        )
        if sequence_end_source
        else None
    )

    start_inclusive = bool(
        metadata.get(
            "start_inclusive",
            record.get(
                "valid_from_inclusive",
                True,
            ),
        )
    )

    end_inclusive = bool(
        metadata.get(
            "end_inclusive",
            record.get(
                "valid_until_inclusive",
                False,
            ),
        )
    )

    sequence_start_inclusive = bool(
        metadata.get(
            "sequence_start_inclusive",
            record.get(
                (
                    "valid_from_sequence_"
                    "inclusive"
                ),
                True,
            ),
        )
    )

    sequence_end_inclusive = bool(
        metadata.get(
            "sequence_end_inclusive",
            record.get(
                (
                    "valid_until_sequence_"
                    "inclusive"
                ),
                False,
            ),
        )
    )

    return temporal_bounds(
        start=
            start,

        end=
            end,

        start_inclusive=
            start_inclusive,

        end_inclusive=
            end_inclusive,

        sequence_start=
            sequence_start,

        sequence_end=
            sequence_end,

        sequence_start_inclusive=
            sequence_start_inclusive,

        sequence_end_inclusive=
            sequence_end_inclusive,

        sources={
            "start":
                str(
                    start_source
                    or ""
                ),

            "end":
                str(
                    end_source
                    or ""
                ),

            "sequence_start":
                str(
                    sequence_start_source
                    or ""
                ),

            "sequence_end":
                str(
                    sequence_end_source
                    or ""
                ),

            "timezone":
                default_timezone
                or "",
        },
    )


def evaluate_lower_bound(
    current: Any,
    lower: Any,
    inclusive: bool,
) -> bool:
    if inclusive:
        return current >= lower

    return current > lower


def evaluate_upper_bound(
    current: Any,
    upper: Any,
    inclusive: bool,
) -> bool:
    if inclusive:
        return current <= upper

    return current < upper


def timestamp_axis(
    bounds: temporal_bounds,
    *,
    as_of: parsed_timestamp
    | None,
) -> dict[str, Any]:
    if (
        bounds.start is None
        and bounds.end is None
    ):
        return {
            "declared":
                False,

            "state":
                "active",

            "reason_code":
                reason_codes[
                    "unbounded"
                ],

            "applicable":
                True,

            "trace":
                [],
        }

    if as_of is None:
        return {
            "declared":
                True,

            "state":
                "indeterminate",

            "reason_code":
                reason_codes[
                    "missing_timestamp"
                ],

            "applicable":
                None,

            "trace": [
                {
                    "operation":
                        "require-as-of",

                    "result":
                        "indeterminate",
                }
            ],
        }

    trace = []

    if bounds.start is not None:
        start_pass = (
            evaluate_lower_bound(
                as_of.value,
                bounds.start.value,
                bounds.start_inclusive,
            )
        )

        trace.append(
            {
                "operation":
                    (
                        "timestamp-lower-bound"
                    ),

                "boundary":
                    (
                        bounds.start.value
                        .isoformat()
                    ),

                "inclusive":
                    bounds.start_inclusive,

                "as_of":
                    as_of.value.isoformat(),

                "result":
                    start_pass,
            }
        )

        if not start_pass:
            return {
                "declared":
                    True,

                "state":
                    "scheduled",

                "reason_code":
                    reason_codes[
                        "scheduled"
                    ],

                "applicable":
                    False,

                "trace":
                    trace,
            }

    if bounds.end is not None:
        end_pass = evaluate_upper_bound(
            as_of.value,
            bounds.end.value,
            bounds.end_inclusive,
        )

        trace.append(
            {
                "operation":
                    (
                        "timestamp-upper-bound"
                    ),

                "boundary":
                    (
                        bounds.end.value
                        .isoformat()
                    ),

                "inclusive":
                    bounds.end_inclusive,

                "as_of":
                    as_of.value.isoformat(),

                "result":
                    end_pass,
            }
        )

        if not end_pass:
            return {
                "declared":
                    True,

                "state":
                    "expired",

                "reason_code":
                    reason_codes[
                        "expired"
                    ],

                "applicable":
                    False,

                "trace":
                    trace,
            }

    return {
        "declared":
            True,

        "state":
            "active",

        "reason_code":
            reason_codes[
                "active"
            ],

        "applicable":
            True,

        "trace":
            trace,
    }


def sequence_axis(
    bounds: temporal_bounds,
    *,
    sequence: int | None,
) -> dict[str, Any]:
    if (
        bounds.sequence_start
        is None
        and bounds.sequence_end
        is None
    ):
        return {
            "declared":
                False,

            "state":
                "active",

            "reason_code":
                reason_codes[
                    "unbounded"
                ],

            "applicable":
                True,

            "trace":
                [],
        }

    if sequence is None:
        return {
            "declared":
                True,

            "state":
                "indeterminate",

            "reason_code":
                reason_codes[
                    "missing_sequence"
                ],

            "applicable":
                None,

            "trace": [
                {
                    "operation":
                        "require-sequence",

                    "result":
                        "indeterminate",
                }
            ],
        }

    trace = []

    if bounds.sequence_start is not None:
        start_pass = (
            evaluate_lower_bound(
                sequence,
                bounds.sequence_start,
                bounds.sequence_start_inclusive,
            )
        )

        trace.append(
            {
                "operation":
                    "sequence-lower-bound",

                "boundary":
                    bounds.sequence_start,

                "inclusive":
                    bounds.sequence_start_inclusive,

                "sequence":
                    sequence,

                "result":
                    start_pass,
            }
        )

        if not start_pass:
            return {
                "declared":
                    True,

                "state":
                    "scheduled",

                "reason_code":
                    reason_codes[
                        "scheduled"
                    ],

                "applicable":
                    False,

                "trace":
                    trace,
            }

    if bounds.sequence_end is not None:
        end_pass = evaluate_upper_bound(
            sequence,
            bounds.sequence_end,
            bounds.sequence_end_inclusive,
        )

        trace.append(
            {
                "operation":
                    "sequence-upper-bound",

                "boundary":
                    bounds.sequence_end,

                "inclusive":
                    bounds.sequence_end_inclusive,

                "sequence":
                    sequence,

                "result":
                    end_pass,
            }
        )

        if not end_pass:
            return {
                "declared":
                    True,

                "state":
                    "expired",

                "reason_code":
                    reason_codes[
                        "expired"
                    ],

                "applicable":
                    False,

                "trace":
                    trace,
            }

    return {
        "declared":
            True,

        "state":
            "active",

        "reason_code":
            reason_codes[
                "active"
            ],

        "applicable":
            True,

        "trace":
            trace,
    }


def validate_bounds(
    bounds: temporal_bounds,
) -> list[dict[str, Any]]:
    violations = []

    if (
        bounds.start is not None
        and bounds.end is not None
        and bounds.end.value
        < bounds.start.value
    ):
        violations.append(
            {
                "reason_code":
                    reason_codes[
                        (
                            "invalid_"
                            "timestamp_range"
                        )
                    ],

                "class":
                    (
                        "invalid-"
                        "timestamp-range"
                    ),

                "start":
                    bounds.start.value
                    .isoformat(),

                "end":
                    bounds.end.value
                    .isoformat(),
            }
        )

    if (
        bounds.start is not None
        and bounds.end is not None
        and bounds.end.value
        == bounds.start.value
        and (
            not bounds.start_inclusive
            or not bounds.end_inclusive
        )
    ):
        violations.append(
            {
                "reason_code":
                    reason_codes[
                        (
                            "invalid_"
                            "timestamp_range"
                        )
                    ],

                "class":
                    (
                        "empty-"
                        "timestamp-range"
                    ),

                "start":
                    bounds.start.value
                    .isoformat(),

                "end":
                    bounds.end.value
                    .isoformat(),
            }
        )

    if (
        bounds.sequence_start
        is not None
        and bounds.sequence_end
        is not None
        and bounds.sequence_end
        < bounds.sequence_start
    ):
        violations.append(
            {
                "reason_code":
                    reason_codes[
                        (
                            "invalid_"
                            "sequence_range"
                        )
                    ],

                "class":
                    (
                        "invalid-"
                        "sequence-range"
                    ),

                "start":
                    bounds.sequence_start,

                "end":
                    bounds.sequence_end,
            }
        )

    if (
        bounds.sequence_start
        is not None
        and bounds.sequence_end
        is not None
        and bounds.sequence_end
        == bounds.sequence_start
        and (
            not bounds.sequence_start_inclusive
            or not bounds.sequence_end_inclusive
        )
    ):
        violations.append(
            {
                "reason_code":
                    reason_codes[
                        (
                            "invalid_"
                            "sequence_range"
                        )
                    ],

                "class":
                    (
                        "empty-"
                        "sequence-range"
                    ),

                "start":
                    bounds.sequence_start,

                "end":
                    bounds.sequence_end,
            }
        )

    return violations


def serialized_bounds(
    bounds: temporal_bounds,
) -> dict[str, Any]:
    return {
        "timestamp": {
            "start":
                (
                    bounds.start.value
                    .isoformat()
                    if bounds.start
                    else None
                ),

            "start_precision":
                (
                    bounds.start.precision
                    if bounds.start
                    else None
                ),

            "start_inclusive":
                bounds.start_inclusive,

            "end":
                (
                    bounds.end.value
                    .isoformat()
                    if bounds.end
                    else None
                ),

            "end_precision":
                (
                    bounds.end.precision
                    if bounds.end
                    else None
                ),

            "end_inclusive":
                bounds.end_inclusive,
        },

        "sequence": {
            "start":
                bounds.sequence_start,

            "start_inclusive":
                (
                    bounds
                    .sequence_start_inclusive
                ),

            "end":
                bounds.sequence_end,

            "end_inclusive":
                (
                    bounds
                    .sequence_end_inclusive
                ),
        },

        "sources":
            clone(
                bounds.sources
            ),
    }


def evaluate_record(
    record: Mapping[str, Any],
    *,
    as_of: Any = None,
    sequence: Any = None,
    default_timezone:
        str | None = None,
) -> dict[str, Any]:
    record = require_mapping(
        record,
        "record",
    )

    identifier = str(
        record.get(
            "id",
            "",
        )
    ).strip()

    if not identifier:
        raise living_policy_temporal_error(
            "policy record id is required"
        )

    try:
        bounds = extract_bounds(
            record
        )

    except living_policy_temporal_error as exc:
        result = {
            "schema":
                schema,

            "kind":
                "policy-temporal-evaluation",

            "owner":
                owner,

            "authority_effect":
                authority_effect,

            "policy":
                identifier,

            "state":
                "invalid",

            "applicable":
                False,

            "reason_codes": [
                reason_codes[
                    "invalid_timestamp"
                ]
            ],

            "violations": [
                {
                    "class":
                        "temporal-parse-error",

                    "error":
                        str(exc),
                }
            ],

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
                if key != "digest"
            }
        )

        return result

    violations = validate_bounds(
        bounds
    )

    if violations:
        result = {
            "schema":
                schema,

            "kind":
                "policy-temporal-evaluation",

            "owner":
                owner,

            "authority_effect":
                authority_effect,

            "policy":
                identifier,

            "state":
                "invalid",

            "applicable":
                False,

            "reason_codes":
                sorted(
                    {
                        str(
                            value.get(
                                "reason_code"
                            )
                        )
                        for value
                        in violations
                    }
                ),

            "bounds":
                serialized_bounds(
                    bounds
                ),

            "violations":
                violations,

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
                if key != "digest"
            }
        )

        return result

    metadata = temporal_metadata(
        record
    )

    effective_timezone = (
        normalize_timezone_name(
            default_timezone
        )
        or normalize_timezone_name(
            metadata.get(
                "timezone"
            )
            or record.get(
                "timezone"
            )
        )
    )

    parsed_as_of = None

    if as_of is not None:
        try:
            parsed_as_of = (
                parse_datetime_value(
                    as_of,
                    source=
                        "evaluation.as_of",
                    default_timezone=
                        effective_timezone,
                )
            )

        except living_policy_temporal_error as exc:
            result = {
                "schema":
                    schema,

                "kind":
                    (
                        "policy-temporal-"
                        "evaluation"
                    ),

                "owner":
                    owner,

                "authority_effect":
                    authority_effect,

                "policy":
                    identifier,

                "state":
                    "invalid",

                "applicable":
                    False,

                "reason_codes": [
                    reason_codes[
                        "invalid_timestamp"
                    ]
                ],

                "violations": [
                    {
                        "class":
                            (
                                "invalid-"
                                "evaluation-timestamp"
                            ),

                        "error":
                            str(exc),
                    }
                ],

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
                    if key != "digest"
                }
            )

            return result

    parsed_sequence = None

    if sequence is not None:
        try:
            parsed_sequence = (
                integer_sequence(
                    sequence,
                    source=
                        "evaluation.sequence",
                )
            )

        except living_policy_temporal_error as exc:
            result = {
                "schema":
                    schema,

                "kind":
                    (
                        "policy-temporal-"
                        "evaluation"
                    ),

                "owner":
                    owner,

                "authority_effect":
                    authority_effect,

                "policy":
                    identifier,

                "state":
                    "invalid",

                "applicable":
                    False,

                "reason_codes": [
                    reason_codes[
                        "invalid_sequence"
                    ]
                ],

                "violations": [
                    {
                        "class":
                            (
                                "invalid-"
                                "evaluation-sequence"
                            ),

                        "error":
                            str(exc),
                    }
                ],

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
                    if key != "digest"
                }
            )

            return result

    time_result = timestamp_axis(
        bounds,
        as_of=
            parsed_as_of,
    )

    sequence_result = sequence_axis(
        bounds,
        sequence=
            parsed_sequence,
    )

    axis_results = (
        time_result,
        sequence_result,
    )

    if any(
        value[
            "state"
        ]
        == "indeterminate"
        for value
        in axis_results
    ):
        state = "indeterminate"
        applicable = None

    elif any(
        value[
            "state"
        ]
        == "expired"
        for value
        in axis_results
    ):
        state = "expired"
        applicable = False

    elif any(
        value[
            "state"
        ]
        == "scheduled"
        for value
        in axis_results
    ):
        state = "scheduled"
        applicable = False

    else:
        state = "active"
        applicable = True

    result_reason_codes = sorted(
        {
            value[
                "reason_code"
            ]
            for value
            in axis_results
        }
    )

    result = {
        "schema":
            schema,

        "kind":
            "policy-temporal-evaluation",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "policy":
            identifier,

        "state":
            state,

        "applicable":
            applicable,

        "as_of":
            (
                parsed_as_of.value
                .isoformat()
                if parsed_as_of
                else None
            ),

        "sequence":
            parsed_sequence,

        "bounds":
            serialized_bounds(
                bounds
            ),

        "axes": {
            "timestamp":
                time_result,

            "sequence":
                sequence_result,
        },

        "reason_codes":
            result_reason_codes,

        "evaluation_trace":
            (
                clone(
                    time_result[
                        "trace"
                    ]
                )
                + clone(
                    sequence_result[
                        "trace"
                    ]
                )
            ),

        "deterministic_without_wall_clock":
            True,

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
            if key != "digest"
        }
    )

    return result


def evaluate_records(
    records: Sequence[
        Mapping[str, Any]
    ],
    *,
    as_of: Any = None,
    sequence: Any = None,
    default_timezone:
        str | None = None,
) -> dict[str, Any]:
    rows = [
        evaluate_record(
            record,
            as_of=
                as_of,
            sequence=
                sequence,
            default_timezone=
                default_timezone,
        )
        for record
        in records
    ]

    counts = {
        state: 0
        for state
        in states
    }

    for row in rows:
        counts[
            row[
                "state"
            ]
        ] += 1

    result = {
        "schema":
            (
                "savant.living-governance."
                "policy-temporal-set.v1"
            ),

        "kind":
            "policy-temporal-set",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "as_of":
            as_of,

        "sequence":
            sequence,

        "count":
            len(
                rows
            ),

        "counts":
            counts,

        "records":
            rows,

        "active_policy_ids":
            [
                row[
                    "policy"
                ]
                for row
                in rows
                if row[
                    "state"
                ]
                == "active"
            ],

        "indeterminate_policy_ids":
            [
                row[
                    "policy"
                ]
                for row
                in rows
                if row[
                    "state"
                ]
                == "indeterminate"
            ],

        "invalid_policy_ids":
            [
                row[
                    "policy"
                ]
                for row
                in rows
                if row[
                    "state"
                ]
                == "invalid"
            ],

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
            if key != "digest"
        }
    )

    return result


def applicable_records(
    records: Sequence[
        Mapping[str, Any]
    ],
    *,
    as_of: Any = None,
    sequence: Any = None,
    default_timezone:
        str | None = None,
) -> dict[str, Any]:
    evaluation = evaluate_records(
        records,
        as_of=
            as_of,
        sequence=
            sequence,
        default_timezone=
            default_timezone,
    )

    index = {
        str(
            record.get(
                "id",
                "",
            )
        ):
            record
        for record
        in records
        if isinstance(
            record,
            Mapping,
        )
    }

    active_ids = evaluation[
        "active_policy_ids"
    ]

    return {
        "schema":
            (
                "savant.living-governance."
                "applicable-policy-set.v1"
            ),

        "kind":
            "applicable-policy-set",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "as_of":
            as_of,

        "sequence":
            sequence,

        "active_policy_ids":
            clone(
                active_ids
            ),

        "records":
            [
                clone(
                    dict(
                        index[
                            identifier
                        ]
                    )
                )
                for identifier
                in active_ids
                if identifier
                in index
            ],

        "temporal_evaluation_digest":
            evaluation[
                "digest"
            ],

        "indeterminate_policy_ids":
            clone(
                evaluation[
                    "indeterminate_policy_ids"
                ]
            ),

        "invalid_policy_ids":
            clone(
                evaluation[
                    "invalid_policy_ids"
                ]
            ),

        "projection_only":
            True,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


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

        "timestamp_validity":
            True,

        "sequence_validity":
            True,

        "inclusive_boundaries":
            True,

        "timezone_explicit":
            True,

        "scheduled_state":
            True,

        "expired_state":
            True,

        "indeterminate_state":
            True,

        "invalid_range_detection":
            True,

        "wall_clock_implicit":
            False,

        "projection_only":
            True,

        "authority_transfer":
            False,

        "ready":
            True,
    }


def selftest() -> dict[str, Any]:
    unbounded = evaluate_record(
        {
            "id":
                "policy:unbounded",
        }
    )

    if (
        unbounded[
            "state"
        ]
        != "active"
    ):
        raise living_policy_temporal_error(
            "unbounded policy not active"
        )

    scheduled = evaluate_record(
        {
            "id":
                "policy:scheduled",

            "valid_from":
                (
                    "2026-09-03"
                    "T00:00:00Z"
                ),
        },
        as_of=
            "2026-09-02T12:00:00Z",
    )

    if (
        scheduled[
            "state"
        ]
        != "scheduled"
    ):
        raise living_policy_temporal_error(
            "scheduled state failed"
        )

    active = evaluate_record(
        {
            "id":
                "policy:active",

            "valid_from":
                (
                    "2026-09-01"
                    "T00:00:00Z"
                ),

            "valid_until":
                (
                    "2026-09-04"
                    "T00:00:00Z"
                ),
        },
        as_of=
            "2026-09-02T12:00:00Z",
    )

    if (
        active[
            "state"
        ]
        != "active"
    ):
        raise living_policy_temporal_error(
            "active window failed"
        )

    expired = evaluate_record(
        {
            "id":
                "policy:expired",

            "valid_until":
                (
                    "2026-09-02"
                    "T00:00:00Z"
                ),
        },
        as_of=
            "2026-09-02T12:00:00Z",
    )

    if (
        expired[
            "state"
        ]
        != "expired"
    ):
        raise living_policy_temporal_error(
            "expired state failed"
        )

    missing_context = evaluate_record(
        {
            "id":
                "policy:requires-time",

            "valid_from":
                (
                    "2026-09-01"
                    "T00:00:00Z"
                ),
        }
    )

    if (
        missing_context[
            "state"
        ]
        != "indeterminate"
    ):
        raise living_policy_temporal_error(
            (
                "missing replay timestamp "
                "did not remain indeterminate"
            )
        )

    sequence_active = evaluate_record(
        {
            "id":
                "policy:sequence",

            "valid_from_sequence":
                10,

            "valid_until_sequence":
                20,
        },
        sequence=
            15,
    )

    if (
        sequence_active[
            "state"
        ]
        != "active"
    ):
        raise living_policy_temporal_error(
            "sequence window failed"
        )

    sequence_expired = evaluate_record(
        {
            "id":
                "policy:sequence-expired",

            "valid_until_sequence":
                20,
        },
        sequence=
            20,
    )

    if (
        sequence_expired[
            "state"
        ]
        != "expired"
    ):
        raise living_policy_temporal_error(
            (
                "exclusive sequence "
                "end boundary failed"
            )
        )

    invalid = evaluate_record(
        {
            "id":
                "policy:invalid",

            "valid_from":
                (
                    "2026-09-05"
                    "T00:00:00Z"
                ),

            "valid_until":
                (
                    "2026-09-01"
                    "T00:00:00Z"
                ),
        },
        as_of=
            "2026-09-02T12:00:00Z",
    )

    if (
        invalid[
            "state"
        ]
        != "invalid"
    ):
        raise living_policy_temporal_error(
            (
                "invalid temporal range "
                "was not rejected"
            )
        )

    date_with_timezone = evaluate_record(
        {
            "id":
                "policy:date",

            "temporal_validity": {
                "timezone":
                    "UTC",

                "valid_from":
                    "2026-09-02",
            },
        },
        as_of=
            "2026-09-02T12:00:00Z",
    )

    if (
        date_with_timezone[
            "state"
        ]
        != "active"
    ):
        raise living_policy_temporal_error(
            (
                "explicit timezone date "
                "validity failed"
            )
        )

    source = {
        "id":
            "policy:immutable-test",

        "valid_from_sequence":
            5,
    }

    before = digest(
        source
    )

    evaluate_record(
        source,
        sequence=
            5,
    )

    after = digest(
        source
    )

    if before != after:
        raise living_policy_temporal_error(
            "source policy was mutated"
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

        "unbounded_active":
            True,

        "scheduled_state":
            True,

        "active_window":
            True,

        "expired_state":
            True,

        "missing_context_indeterminate":
            True,

        "sequence_window":
            True,

        "exclusive_end_boundary":
            True,

        "invalid_range_rejected":
            True,

        "explicit_timezone_supported":
            True,

        "implicit_wall_clock_used":
            False,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "applicable_records",
    "evaluate_record",
    "evaluate_records",
    "extract_bounds",
    "living_policy_temporal_error",
    "selftest",
    "status",
]
