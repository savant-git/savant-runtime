#!/usr/bin/env python3

from __future__ import annotations

import re

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


schema = "savant.living-policy.v1"
owner = "living-governance"
authority_effect = "none"

missing = object()

epistemic_classes = {
    "fact",
    "assertion",
    "inference",
    "estimate",
    "speculation",
    "unknown",
    "projection",
}

governance_types = {
    "policy",
    "rule",
    "permission",
    "invariant",
}

effects = {
    "allow",
    "deny",
    "require",
    "advisory",
    "authority_required",
}

enforcement_modes = {
    "enforce",
    "advisory",
    "disabled",
    "authority_required",
}

outcomes = {
    "pass",
    "fail",
    "advisory",
    "unknown",
    "authority-required",
}

inactive_statuses = {
    "inactive",
    "superseded",
    "withdrawn",
    "retired",
    "rejected",
}

Predicate = Callable[
    [
        Any,
        Any,
        Mapping[str, Any],
    ],
    bool | None,
]

predicate_registry: dict[
    str,
    Predicate,
] = {}


def _canonical_name(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip().lower().replace(
        "-",
        "_",
    )


def _parse_time(
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


def _path_value(
    value: Any,
    path: str,
) -> Any:
    current = value

    if not path:
        return current

    for part in path.split(
        "."
    ):
        if isinstance(
            current,
            Mapping,
        ):
            if part not in current:
                return missing

            current = current[
                part
            ]

            continue

        if isinstance(
            current,
            Sequence,
        ) and not isinstance(
            current,
            (
                str,
                bytes,
                bytearray,
            ),
        ):
            try:
                index = int(
                    part
                )

            except ValueError:
                return missing

            try:
                current = current[
                    index
                ]

            except IndexError:
                return missing

            continue

        return missing

    return current


def register_predicate(
    name: str,
    function: Predicate,
    *,
    replace: bool = False,
) -> None:
    canonical = _canonical_name(
        name
    )

    if not canonical:
        raise ValueError(
            "predicate name is required"
        )

    if (
        canonical
        in predicate_registry
        and not replace
    ):
        raise ValueError(
            (
                "predicate already registered: "
                + canonical
            )
        )

    predicate_registry[
        canonical
    ] = function


def _equals(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool:
    return actual == expected


def _not_equals(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool:
    return actual != expected


def _exists(
    actual: Any,
    _: Any,
    __: Mapping[str, Any],
) -> bool:
    return actual is not missing


def _absent(
    actual: Any,
    _: Any,
    __: Mapping[str, Any],
) -> bool:
    return actual is missing


def _in(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
    if actual is missing:
        return None

    if not isinstance(
        expected,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        return None

    return actual in expected


def _not_in(
    actual: Any,
    expected: Any,
    context: Mapping[str, Any],
) -> bool | None:
    result = _in(
        actual,
        expected,
        context,
    )

    if result is None:
        return None

    return not result


def _contains(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
    if actual is missing:
        return None

    try:
        return expected in actual

    except TypeError:
        return None


def _starts_with(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
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


def _ends_with(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
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


def _matches(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
    if not isinstance(
        actual,
        str,
    ):
        return None

    try:
        pattern = re.compile(
            str(
                expected
            )
        )

    except re.error:
        return None

    return bool(
        pattern.search(
            actual
        )
    )


def _is_lowercase(
    actual: Any,
    _: Any,
    __: Mapping[str, Any],
) -> bool | None:
    if not isinstance(
        actual,
        str,
    ):
        return None

    return actual == actual.lower()


def _is_absolute(
    actual: Any,
    _: Any,
    __: Mapping[str, Any],
) -> bool | None:
    if not isinstance(
        actual,
        str,
    ):
        return None

    return Path(
        actual
    ).is_absolute()


def _truthy(
    actual: Any,
    _: Any,
    __: Mapping[str, Any],
) -> bool:
    if actual is missing:
        return False

    return bool(
        actual
    )


def _falsy(
    actual: Any,
    expected: Any,
    context: Mapping[str, Any],
) -> bool:
    return not _truthy(
        actual,
        expected,
        context,
    )


def _compare(
    actual: Any,
    expected: Any,
    operation: str,
) -> bool | None:
    if actual is missing:
        return None

    try:
        if operation == "gt":
            return actual > expected

        if operation == "gte":
            return actual >= expected

        if operation == "lt":
            return actual < expected

        if operation == "lte":
            return actual <= expected

    except TypeError:
        return None

    return None


def _gt(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
    return _compare(
        actual,
        expected,
        "gt",
    )


def _gte(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
    return _compare(
        actual,
        expected,
        "gte",
    )


def _lt(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
    return _compare(
        actual,
        expected,
        "lt",
    )


def _lte(
    actual: Any,
    expected: Any,
    _: Mapping[str, Any],
) -> bool | None:
    return _compare(
        actual,
        expected,
        "lte",
    )


for _name, _function in (
    (
        "eq",
        _equals,
    ),
    (
        "ne",
        _not_equals,
    ),
    (
        "exists",
        _exists,
    ),
    (
        "absent",
        _absent,
    ),
    (
        "in",
        _in,
    ),
    (
        "not_in",
        _not_in,
    ),
    (
        "contains",
        _contains,
    ),
    (
        "starts_with",
        _starts_with,
    ),
    (
        "ends_with",
        _ends_with,
    ),
    (
        "matches",
        _matches,
    ),
    (
        "is_lowercase",
        _is_lowercase,
    ),
    (
        "is_absolute",
        _is_absolute,
    ),
    (
        "truthy",
        _truthy,
    ),
    (
        "falsy",
        _falsy,
    ),
    (
        "gt",
        _gt,
    ),
    (
        "gte",
        _gte,
    ),
    (
        "lt",
        _lt,
    ),
    (
        "lte",
        _lte,
    ),
):
    register_predicate(
        _name,
        _function,
    )


def _predicate_trace(
    *,
    operator: str,
    path: str | None,
    expected: Any,
    actual: Any,
    result: bool | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "operator":
            operator,

        "path":
            path,

        "expected":
            expected,

        "actual":
            (
                None
                if actual is missing
                else actual
            ),

        "value_present":
            actual is not missing,

        "result":
            result,

        "reason":
            reason,
    }


def evaluate_predicate(
    predicate: Any,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    if predicate is None:
        return {
            "result":
                True,

            "trace": [
                {
                    "operator":
                        "unconditional",

                    "result":
                        True,

                    "reason":
                        "no predicate supplied",
                }
            ],
        }

    if not isinstance(
        predicate,
        Mapping,
    ):
        return {
            "result":
                None,

            "trace": [
                {
                    "operator":
                        "invalid",

                    "result":
                        None,

                    "reason":
                        "predicate must be an object",
                }
            ],
        }

    operator = _canonical_name(
        predicate.get(
            "operator"
        )
    )

    if operator in {
        "all",
        "any",
    }:
        children = predicate.get(
            "predicates"
        )

        if not isinstance(
            children,
            list,
        ):
            return {
                "result":
                    None,

                "trace": [
                    {
                        "operator":
                            operator,

                        "result":
                            None,

                        "reason":
                            "composite predicate requires predicates list",
                    }
                ],
            }

        evaluated = [
            evaluate_predicate(
                child,
                context,
            )
            for child
            in children
        ]

        child_results = [
            item[
                "result"
            ]
            for item
            in evaluated
        ]

        if operator == "all":
            if False in child_results:
                result = False

            elif None in child_results:
                result = None

            else:
                result = True

        else:
            if True in child_results:
                result = True

            elif None in child_results:
                result = None

            else:
                result = False

        return {
            "result":
                result,

            "trace": [
                {
                    "operator":
                        operator,

                    "result":
                        result,

                    "children":
                        evaluated,
                }
            ],
        }

    if operator == "not":
        child = evaluate_predicate(
            predicate.get(
                "predicate"
            ),
            context,
        )

        child_result = child[
            "result"
        ]

        result = (
            None
            if child_result is None
            else not child_result
        )

        return {
            "result":
                result,

            "trace": [
                {
                    "operator":
                        "not",

                    "result":
                        result,

                    "child":
                        child,
                }
            ],
        }

    function = predicate_registry.get(
        operator
    )

    if function is None:
        return {
            "result":
                None,

            "trace": [
                {
                    "operator":
                        operator,

                    "result":
                        None,

                    "reason":
                        "predicate operator is not registered",
                }
            ],
        }

    path_value = predicate.get(
        "path"
    )

    path = (
        str(
            path_value
        )
        if path_value is not None
        else ""
    )

    actual = _path_value(
        context,
        path,
    )

    expected = predicate.get(
        "value"
    )

    try:
        result = function(
            actual,
            expected,
            context,
        )

    except Exception:
        result = None

    return {
        "result":
            result,

        "trace": [
            _predicate_trace(
                operator=operator,
                path=path or None,
                expected=expected,
                actual=actual,
                result=result,
                reason=(
                    "predicate evaluated"
                    if result is not None
                    else "predicate could not be deterministically evaluated"
                ),
            )
        ],
    }


def _selector_match(
    selector: Any,
    actual: Any,
    context: Mapping[str, Any],
) -> bool | None:
    if selector is None:
        return True

    if isinstance(
        selector,
        Mapping,
    ):
        if "operator" in selector:
            operator = _canonical_name(
                selector.get(
                    "operator"
                )
            )

            function = predicate_registry.get(
                operator
            )

            if function is None:
                return None

            try:
                return function(
                    actual,
                    selector.get(
                        "value"
                    ),
                    context,
                )

            except Exception:
                return None

        if not isinstance(
            actual,
            Mapping,
        ):
            return False

        unknown_seen = False

        for key, child_selector in selector.items():
            if key not in actual:
                return False

            child_result = _selector_match(
                child_selector,
                actual[
                    key
                ],
                context,
            )

            if child_result is False:
                return False

            if child_result is None:
                unknown_seen = True

        return (
            None
            if unknown_seen
            else True
        )

    if isinstance(
        selector,
        list,
    ):
        if isinstance(
            actual,
            list,
        ):
            return any(
                item in selector
                for item
                in actual
            )

        return actual in selector

    return actual == selector


def _applicability_dimension(
    *,
    name: str,
    selector: Any,
    actual: Any,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    result = _selector_match(
        selector,
        actual,
        context,
    )

    return {
        "dimension":
            name,

        "selector":
            selector,

        "actual":
            actual,

        "result":
            result,
    }


def _temporal_applicability(
    record: Mapping[str, Any],
    at: datetime,
) -> dict[str, Any]:
    valid_from_raw = record.get(
        "valid_from"
    )

    valid_until_raw = record.get(
        "valid_until"
    )

    valid_from = _parse_time(
        valid_from_raw
    )

    valid_until = _parse_time(
        valid_until_raw
    )

    if (
        valid_from_raw is not None
        and valid_from is None
    ):
        return {
            "result":
                None,

            "reason":
                "invalid valid_from timestamp",

            "valid_from":
                valid_from_raw,

            "valid_until":
                valid_until_raw,
        }

    if (
        valid_until_raw is not None
        and valid_until is None
    ):
        return {
            "result":
                None,

            "reason":
                "invalid valid_until timestamp",

            "valid_from":
                valid_from_raw,

            "valid_until":
                valid_until_raw,
        }

    if (
        valid_from is not None
        and at < valid_from
    ):
        return {
            "result":
                False,

            "reason":
                "policy validity has not begun",

            "valid_from":
                valid_from_raw,

            "valid_until":
                valid_until_raw,
        }

    if (
        valid_until is not None
        and at > valid_until
    ):
        return {
            "result":
                False,

            "reason":
                "policy validity has ended",

            "valid_from":
                valid_from_raw,

            "valid_until":
                valid_until_raw,
        }

    return {
        "result":
            True,

        "reason":
            "policy is temporally valid",

        "valid_from":
            valid_from_raw,

        "valid_until":
            valid_until_raw,
    }


def applicable(
    record: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    at: datetime | str | None = None,
) -> dict[str, Any]:
    at_time = (
        _parse_time(
            at
        )
        if at is not None
        else datetime.now(
            timezone.utc
        )
    )

    if at_time is None:
        return {
            "schema":
                "savant.living-policy.applicability.v1",

            "id":
                record.get(
                    "id"
                ),

            "applicable":
                None,

            "reason":
                "evaluation timestamp is invalid",

            "trace":
                [],
        }

    status = _canonical_name(
        record.get(
            "status",
            "active",
        )
    )

    if status in inactive_statuses:
        return {
            "schema":
                "savant.living-policy.applicability.v1",

            "id":
                record.get(
                    "id"
                ),

            "applicable":
                False,

            "reason":
                "record status is inactive",

            "trace": [
                {
                    "dimension":
                        "status",

                    "actual":
                        status,

                    "result":
                        False,
                }
            ],
        }

    temporal = _temporal_applicability(
        record,
        at_time,
    )

    if temporal[
        "result"
    ] is not True:
        return {
            "schema":
                "savant.living-policy.applicability.v1",

            "id":
                record.get(
                    "id"
                ),

            "applicable":
                temporal[
                    "result"
                ],

            "reason":
                temporal[
                    "reason"
                ],

            "trace": [
                {
                    "dimension":
                        "temporal",

                    **temporal,
                }
            ],
        }

    dimensions = []

    for name in (
        "scope",
        "subject",
        "target",
        "action",
    ):
        selector = record.get(
            name
        )

        actual = context.get(
            name
        )

        dimensions.append(
            _applicability_dimension(
                name=name,
                selector=selector,
                actual=actual,
                context=context,
            )
        )

    if any(
        item[
            "result"
        ] is False
        for item
        in dimensions
    ):
        result: bool | None = False

    elif any(
        item[
            "result"
        ] is None
        for item
        in dimensions
    ):
        result = None

    else:
        result = True

    return {
        "schema":
            "savant.living-policy.applicability.v1",

        "id":
            record.get(
                "id"
            ),

        "applicable":
            result,

        "reason":
            (
                "all applicability selectors matched"
                if result is True
                else (
                    "one or more applicability selectors did not match"
                    if result is False
                    else "applicability could not be fully resolved"
                )
            ),

        "evaluated_at":
            at_time.isoformat(),

        "trace": [
            {
                "dimension":
                    "temporal",

                **temporal,
            },
            *dimensions,
        ],
    }


def _evidence_ids(
    context: Mapping[str, Any],
) -> set[str]:
    evidence = context.get(
        "evidence",
        []
    )

    values: set[str] = set()

    if isinstance(
        evidence,
        Mapping,
    ):
        evidence = evidence.get(
            "ids",
            [],
        )

    if not isinstance(
        evidence,
        list,
    ):
        return values

    for item in evidence:
        if isinstance(
            item,
            Mapping,
        ):
            identifier = item.get(
                "id"
            )

            if identifier is not None:
                values.add(
                    str(
                        identifier
                    )
                )

        else:
            values.add(
                str(
                    item
                )
            )

    return values


def _evidence_requirements(
    record: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    requirements = record.get(
        "evidence",
        []
    )

    if requirements is None:
        requirements = []

    if not isinstance(
        requirements,
        list,
    ):
        return {
            "satisfied":
                None,

            "required":
                requirements,

            "present":
                sorted(
                    _evidence_ids(
                        context
                    )
                ),

            "missing": [],

            "reason":
                "evidence requirements must be a list",
        }

    required_ids = []

    for requirement in requirements:
        if isinstance(
            requirement,
            str,
        ):
            required_ids.append(
                requirement
            )

            continue

        if isinstance(
            requirement,
            Mapping,
        ):
            identifier = requirement.get(
                "id"
            )

            if identifier is not None:
                required_ids.append(
                    str(
                        identifier
                    )
                )

    present = _evidence_ids(
        context
    )

    missing_ids = sorted(
        {
            identifier
            for identifier
            in required_ids
            if identifier not in present
        }
    )

    return {
        "satisfied":
            not missing_ids,

        "required":
            sorted(
                set(
                    required_ids
                )
            ),

        "present":
            sorted(
                present
            ),

        "missing":
            missing_ids,

        "reason":
            (
                "evidence requirements satisfied"
                if not missing_ids
                else "required evidence is missing"
            ),
    }


def _exception_match(
    exception: Any,
    context: Mapping[str, Any],
) -> bool | None:
    if not isinstance(
        exception,
        Mapping,
    ):
        return None

    results = []

    for name in (
        "scope",
        "subject",
        "target",
        "action",
    ):
        if name not in exception:
            continue

        results.append(
            _selector_match(
                exception.get(
                    name
                ),
                context.get(
                    name
                ),
                context,
            )
        )

    if "predicate" in exception:
        results.append(
            evaluate_predicate(
                exception.get(
                    "predicate"
                ),
                context,
            )[
                "result"
            ]
        )

    if not results:
        return None

    if False in results:
        return False

    if None in results:
        return None

    return True


def _exceptions(
    record: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    values = record.get(
        "exceptions",
        record.get(
            "exception",
            [],
        ),
    )

    if values is None:
        values = []

    if isinstance(
        values,
        Mapping,
    ):
        values = [
            values
        ]

    if not isinstance(
        values,
        list,
    ):
        return {
            "matched":
                None,

            "index":
                None,

            "trace": [],

            "reason":
                "exceptions must be an object or list",
        }

    trace = []

    unknown_seen = False

    for index, exception in enumerate(
        values
    ):
        result = _exception_match(
            exception,
            context,
        )

        trace.append(
            {
                "index":
                    index,

                "result":
                    result,

                "exception":
                    exception,
            }
        )

        if result is True:
            return {
                "matched":
                    True,

                "index":
                    index,

                "trace":
                    trace,

                "reason":
                    "explicit exception matched",
            }

        if result is None:
            unknown_seen = True

    return {
        "matched":
            (
                None
                if unknown_seen
                else False
            ),

        "index":
            None,

        "trace":
            trace,

        "reason":
            (
                "exception applicability unresolved"
                if unknown_seen
                else "no explicit exception matched"
            ),
    }


def _authority_granted(
    context: Mapping[str, Any],
) -> bool:
    authority = context.get(
        "authority"
    )

    if isinstance(
        authority,
        Mapping,
    ):
        return bool(
            authority.get(
                "granted",
                False,
            )
        )

    return False


def _reason_code(
    record: Mapping[str, Any],
    *,
    effect: str,
    outcome: str,
    suffix: str | None = None,
) -> str:
    explicit = record.get(
        "reason_code"
    )

    if explicit:
        return str(
            explicit
        )

    parts = [
        "living_policy",
        effect or "unknown_effect",
        outcome.replace(
            "-",
            "_",
        ),
    ]

    if suffix:
        parts.append(
            suffix
        )

    return ".".join(
        parts
    )


def _result(
    record: Mapping[str, Any],
    *,
    applicable_value: bool | None,
    outcome: str,
    reason_code: str,
    reason: str,
    predicate: dict[str, Any] | None,
    applicability: dict[str, Any],
    evidence: dict[str, Any] | None,
    exceptions: dict[str, Any] | None,
    effect: str,
    enforcement_mode: str,
) -> dict[str, Any]:
    return {
        "schema":
            "savant.living-policy.evaluation.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "id":
            record.get(
                "id"
            ),

        "stream":
            record.get(
                "stream"
            ),

        "type":
            record.get(
                "type"
            ),

        "epistemic_class":
            record.get(
                "epistemic_class",
                "unknown",
            ),

        "applicable":
            applicable_value,

        "outcome":
            outcome,

        "effect":
            effect,

        "enforcement_mode":
            enforcement_mode,

        "reason_code":
            reason_code,

        "reason":
            reason,

        "remediation":
            record.get(
                "remediation"
            ),

        "applicability":
            applicability,

        "evidence":
            evidence,

        "exceptions":
            exceptions,

        "predicate":
            predicate,

        "trace": {
            "applicability":
                applicability.get(
                    "trace",
                    [],
                ),

            "exceptions":
                (
                    exceptions.get(
                        "trace",
                        [],
                    )
                    if exceptions
                    else []
                ),

            "predicate":
                (
                    predicate.get(
                        "trace",
                        [],
                    )
                    if predicate
                    else []
                ),
        },
    }


def evaluate_policy(
    record: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    at: datetime | str | None = None,
) -> dict[str, Any]:
    applicability_result = applicable(
        record,
        context,
        at=at,
    )

    effect = _canonical_name(
        record.get(
            "effect",
            "require",
        )
    )

    enforcement_mode = _canonical_name(
        record.get(
            "enforcement_mode",
            "enforce",
        )
    )

    if effect not in effects:
        return _result(
            record,
            applicable_value=None,
            outcome="unknown",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="unknown",
                suffix="unsupported_effect",
            ),
            reason="policy effect is unsupported",
            predicate=None,
            applicability=applicability_result,
            evidence=None,
            exceptions=None,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    if enforcement_mode not in enforcement_modes:
        return _result(
            record,
            applicable_value=None,
            outcome="unknown",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="unknown",
                suffix="unsupported_enforcement_mode",
            ),
            reason="policy enforcement mode is unsupported",
            predicate=None,
            applicability=applicability_result,
            evidence=None,
            exceptions=None,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    if enforcement_mode == "disabled":
        return _result(
            record,
            applicable_value=False,
            outcome="pass",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="pass",
                suffix="disabled",
            ),
            reason="policy enforcement is disabled",
            predicate=None,
            applicability=applicability_result,
            evidence=None,
            exceptions=None,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    if applicability_result[
        "applicable"
    ] is False:
        return _result(
            record,
            applicable_value=False,
            outcome="pass",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="pass",
                suffix="not_applicable",
            ),
            reason=applicability_result[
                "reason"
            ],
            predicate=None,
            applicability=applicability_result,
            evidence=None,
            exceptions=None,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    if applicability_result[
        "applicable"
    ] is None:
        return _result(
            record,
            applicable_value=None,
            outcome="unknown",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="unknown",
                suffix="applicability_unresolved",
            ),
            reason=applicability_result[
                "reason"
            ],
            predicate=None,
            applicability=applicability_result,
            evidence=None,
            exceptions=None,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    exception_result = _exceptions(
        record,
        context,
    )

    if exception_result[
        "matched"
    ] is True:
        return _result(
            record,
            applicable_value=True,
            outcome="pass",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="pass",
                suffix="exception_applied",
            ),
            reason="explicit policy exception applied",
            predicate=None,
            applicability=applicability_result,
            evidence=None,
            exceptions=exception_result,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    if exception_result[
        "matched"
    ] is None:
        return _result(
            record,
            applicable_value=True,
            outcome="unknown",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="unknown",
                suffix="exception_unresolved",
            ),
            reason="exception applicability could not be resolved",
            predicate=None,
            applicability=applicability_result,
            evidence=None,
            exceptions=exception_result,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    evidence_result = _evidence_requirements(
        record,
        context,
    )

    if evidence_result[
        "satisfied"
    ] is not True:
        return _result(
            record,
            applicable_value=True,
            outcome="unknown",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="unknown",
                suffix="evidence_missing",
            ),
            reason=evidence_result[
                "reason"
            ],
            predicate=None,
            applicability=applicability_result,
            evidence=evidence_result,
            exceptions=exception_result,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    predicate_result = evaluate_predicate(
        record.get(
            "predicate"
        ),
        context,
    )

    predicate_value = predicate_result[
        "result"
    ]

    if predicate_value is None:
        return _result(
            record,
            applicable_value=True,
            outcome="unknown",
            reason_code=_reason_code(
                record,
                effect=effect,
                outcome="unknown",
                suffix="predicate_unresolved",
            ),
            reason="policy predicate could not be deterministically resolved",
            predicate=predicate_result,
            applicability=applicability_result,
            evidence=evidence_result,
            exceptions=exception_result,
            effect=effect,
            enforcement_mode=enforcement_mode,
        )

    if (
        enforcement_mode
        == "authority_required"
        or effect
        == "authority_required"
    ):
        if (
            predicate_value
            and not _authority_granted(
                context
            )
        ):
            outcome = "authority-required"
            reason = "applicable policy requires explicit authority"

        else:
            outcome = "pass"
            reason = "authority requirement is satisfied or not triggered"

    elif effect == "deny":
        outcome = (
            "fail"
            if predicate_value
            else "pass"
        )

        reason = (
            "denied condition matched"
            if predicate_value
            else "denied condition did not match"
        )

    elif effect in {
        "allow",
        "require",
    }:
        outcome = (
            "pass"
            if predicate_value
            else "fail"
        )

        reason = (
            "required policy condition satisfied"
            if predicate_value
            else "required policy condition failed"
        )

    elif effect == "advisory":
        outcome = (
            "advisory"
            if predicate_value
            else "pass"
        )

        reason = (
            "advisory condition matched"
            if predicate_value
            else "advisory condition did not match"
        )

    else:
        outcome = "unknown"
        reason = "policy effect could not be resolved"

    if (
        outcome == "fail"
        and enforcement_mode == "advisory"
    ):
        outcome = "advisory"
        reason = (
            "policy condition failed under advisory enforcement"
        )

    return _result(
        record,
        applicable_value=True,
        outcome=outcome,
        reason_code=_reason_code(
            record,
            effect=effect,
            outcome=outcome,
        ),
        reason=reason,
        predicate=predicate_result,
        applicability=applicability_result,
        evidence=evidence_result,
        exceptions=exception_result,
        effect=effect,
        enforcement_mode=enforcement_mode,
    )


def _overall_outcome(
    evaluations: Sequence[
        Mapping[str, Any]
    ],
) -> str:
    present = {
        str(
            item.get(
                "outcome",
                "unknown",
            )
        )
        for item
        in evaluations
        if item.get(
            "applicable"
        )
        is not False
    }

    for candidate in (
        "fail",
        "authority-required",
        "unknown",
        "advisory",
        "pass",
    ):
        if candidate in present:
            return candidate

    return "pass"


def evaluate_policies(
    records: Sequence[
        Mapping[str, Any]
    ],
    context: Mapping[str, Any],
    *,
    at: datetime | str | None = None,
) -> dict[str, Any]:
    evaluations = [
        evaluate_policy(
            record,
            context,
            at=at,
        )
        for record
        in records
    ]

    overall = _overall_outcome(
        evaluations
    )

    counts = {
        outcome:
            sum(
                1
                for item
                in evaluations
                if item.get(
                    "outcome"
                )
                == outcome
            )
        for outcome
        in sorted(
            outcomes
        )
    }

    governing_rules = [
        str(
            item.get(
                "id"
            )
        )
        for item
        in evaluations
        if (
            item.get(
                "applicable"
            )
            is True
            and item.get(
                "id"
            )
            is not None
        )
    ]

    reason_codes = sorted(
        {
            str(
                item.get(
                    "reason_code"
                )
            )
            for item
            in evaluations
            if item.get(
                "reason_code"
            )
        }
    )

    unresolved = [
        {
            "id":
                item.get(
                    "id"
                ),

            "reason_code":
                item.get(
                    "reason_code"
                ),

            "reason":
                item.get(
                    "reason"
                ),
        }
        for item
        in evaluations
        if item.get(
            "outcome"
        )
        == "unknown"
    ]

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "decision":
            overall,

        "allowed":
            overall
            not in {
                "fail",
                "authority-required",
                "unknown",
            },

        "evaluation_count":
            len(
                evaluations
            ),

        "outcome_counts":
            counts,

        "governing_rules":
            governing_rules,

        "reason_codes":
            reason_codes,

        "unresolved_unknowns":
            unresolved,

        "evaluations":
            evaluations,
    }


def explain(
    records: Sequence[
        Mapping[str, Any]
    ],
    context: Mapping[str, Any],
    *,
    at: datetime | str | None = None,
) -> dict[str, Any]:
    result = evaluate_policies(
        records,
        context,
        at=at,
    )

    return {
        **result,

        "schema":
            "savant.living-policy.explanation.v1",

        "explanation": [
            {
                "id":
                    item.get(
                        "id"
                    ),

                "applicable":
                    item.get(
                        "applicable"
                    ),

                "outcome":
                    item.get(
                        "outcome"
                    ),

                "reason_code":
                    item.get(
                        "reason_code"
                    ),

                "reason":
                    item.get(
                        "reason"
                    ),

                "remediation":
                    item.get(
                        "remediation"
                    ),
            }
            for item
            in result[
                "evaluations"
            ]
        ],
    }


def why(
    records: Sequence[
        Mapping[str, Any]
    ],
    context: Mapping[str, Any],
    *,
    at: datetime | str | None = None,
) -> dict[str, Any]:
    result = explain(
        records,
        context,
        at=at,
    )

    decisive = [
        item
        for item
        in result[
            "evaluations"
        ]
        if (
            item.get(
                "applicable"
            )
            is True
            and item.get(
                "outcome"
            )
            == result[
                "decision"
            ]
        )
    ]

    return {
        "schema":
            "savant.living-policy.why.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "decision":
            result[
                "decision"
            ],

        "because":
            [
                {
                    "id":
                        item.get(
                            "id"
                        ),

                    "reason_code":
                        item.get(
                            "reason_code"
                        ),

                    "reason":
                        item.get(
                            "reason"
                        ),
                }
                for item
                in decisive
            ],

        "evaluation":
            result,
    }


def why_not(
    records: Sequence[
        Mapping[str, Any]
    ],
    context: Mapping[str, Any],
    *,
    desired: str = "pass",
    at: datetime | str | None = None,
) -> dict[str, Any]:
    desired_value = _canonical_name(
        desired
    ).replace(
        "_",
        "-",
    )

    result = explain(
        records,
        context,
        at=at,
    )

    blockers = [
        item
        for item
        in result[
            "evaluations"
        ]
        if (
            item.get(
                "applicable"
            )
            is True
            and item.get(
                "outcome"
            )
            != desired_value
        )
    ]

    return {
        "schema":
            "savant.living-policy.why-not.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "desired":
            desired_value,

        "actual":
            result[
                "decision"
            ],

        "satisfied":
            result[
                "decision"
            ]
            == desired_value,

        "blockers":
            [
                {
                    "id":
                        item.get(
                            "id"
                        ),

                    "outcome":
                        item.get(
                            "outcome"
                        ),

                    "reason_code":
                        item.get(
                            "reason_code"
                        ),

                    "reason":
                        item.get(
                            "reason"
                        ),

                    "remediation":
                        item.get(
                            "remediation"
                        ),
                }
                for item
                in blockers
            ],

        "evaluation":
            result,
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            "savant.living-policy.status.v1",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "governance_types":
            sorted(
                governance_types
            ),

        "epistemic_classes":
            sorted(
                epistemic_classes
            ),

        "effects":
            sorted(
                effects
            ),

        "enforcement_modes":
            sorted(
                enforcement_modes
            ),

        "outcomes":
            sorted(
                outcomes
            ),

        "predicate_operators":
            sorted(
                predicate_registry
            ),

        "operations": [
            "applicable",
            "evaluate",
            "explain",
            "why",
            "why-not",
        ],

        "authority_store":
            False,

        "projection_only":
            True,

        "ready":
            True,
    }


__all__ = [
    "applicable",
    "evaluate_policies",
    "evaluate_policy",
    "evaluate_predicate",
    "explain",
    "predicate_registry",
    "register_predicate",
    "status",
    "why",
    "why_not",
]
