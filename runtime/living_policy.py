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
                text[:-1]
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
    ("eq", _equals),
    ("ne", _not_equals),
    ("exists", _exists),
    ("absent", _absent),
    ("in", _in),
    ("not_in", _not_in),
    ("contains", _contains),
    ("starts_with", _starts_with),
    ("ends_with", _ends_with),
    ("matches", _matches),
    ("is_lowercase", _is_lowercase),
    ("is_absolute", _is_absolute),
    ("truthy", _truthy),
    ("falsy", _falsy),
    ("gt", _gt),
    ("gte", _gte),
    ("lt", _lt),
    ("lte", _lte),
):
    register_predicate(
        _name,
        _function,
    )


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

        return {
            "result":
                (
                    None
                    if child_result is None
                    else not child_result
                ),

            "trace": [
                {
                    "operator":
                        "not",

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

    path = str(
        predicate.get(
            "path",
            "",
        )
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
            {
                "operator":
                    operator,

                "path":
                    path or None,

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
            }
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
            function = predicate_registry.get(
                _canonical_name(
                    selector.get(
                        "operator"
                    )
                )
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

            result = _selector_match(
                child_selector,
                actual[
                    key
                ],
                context,
            )

            if result is False:
                return False

            if result is None:
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

    status_value = _canonical_name(
        record.get(
            "status",
            "active",
        )
    )

    if status_value in inactive_statuses:
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

            "trace": [],
        }

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
        temporal: bool | None = None

    elif (
        valid_until_raw is not None
        and valid_until is None
    ):
        temporal = None

    elif (
        valid_from is not None
        and at_time < valid_from
    ):
        temporal = False

    elif (
        valid_until is not None
        and at_time > valid_until
    ):
        temporal = False

    else:
        temporal = True

    trace = [
        {
            "dimension":
                "temporal",

            "result":
                temporal,

            "valid_from":
                valid_from_raw,

            "valid_until":
                valid_until_raw,
        }
    ]

    if temporal is not True:
        return {
            "schema":
                "savant.living-policy.applicability.v1",

            "id":
                record.get(
                    "id"
                ),

            "applicable":
                temporal,

            "reason":
                (
                    "policy is outside temporal validity"
                    if temporal is False
                    else "temporal validity could not be resolved"
                ),

            "trace":
                trace,
        }

    results = []

    for name in (
        "scope",
        "subject",
        "target",
        "action",
    ):
        result = _selector_match(
            record.get(
                name
            ),
            context.get(
                name
            ),
            context,
        )

        results.append(
            result
        )

        trace.append(
            {
                "dimension":
                    name,

                "selector":
                    record.get(
                        name
                    ),

                "actual":
                    context.get(
                        name
                    ),

                "result":
                    result,
            }
        )

    if False in results:
        applicability: bool | None = False

    elif None in results:
        applicability = None

    else:
        applicability = True

    return {
        "schema":
            "savant.living-policy.applicability.v1",

        "id":
            record.get(
                "id"
            ),

        "applicable":
            applicability,

        "reason":
            (
                "all applicability selectors matched"
                if applicability is True
                else (
                    "one or more applicability selectors did not match"
                    if applicability is False
                    else "applicability could not be fully resolved"
                )
            ),

        "evaluated_at":
            at_time.isoformat(),

        "trace":
            trace,
    }


def _evidence_result(
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

            "present": [],

            "missing": [],
        }

    present_raw = context.get(
        "evidence",
        []
    )

    if isinstance(
        present_raw,
        Mapping,
    ):
        present_raw = present_raw.get(
            "ids",
            [],
        )

    present = set()

    if isinstance(
        present_raw,
        list,
    ):
        for item in present_raw:
            if isinstance(
                item,
                Mapping,
            ):
                identifier = item.get(
                    "id"
                )

                if identifier is not None:
                    present.add(
                        str(
                            identifier
                        )
                    )

            else:
                present.add(
                    str(
                        item
                    )
                )

    required = []

    for requirement in requirements:
        if isinstance(
            requirement,
            str,
        ):
            required.append(
                requirement
            )

        elif isinstance(
            requirement,
            Mapping,
        ):
            identifier = requirement.get(
                "id"
            )

            if identifier is not None:
                required.append(
                    str(
                        identifier
                    )
                )

    missing_ids = sorted(
        set(
            required
        )
        - present
    )

    return {
        "satisfied":
            not missing_ids,

        "required":
            sorted(
                set(
                    required
                )
            ),

        "present":
            sorted(
                present
            ),

        "missing":
            missing_ids,
    }


def evaluate_policy(
    record: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    at: datetime | str | None = None,
) -> dict[str, Any]:
    applicability = applicable(
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

    if applicability[
        "applicable"
    ] is False:
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

            "applicable":
                False,

            "effect":
                effect,

            "enforcement_mode":
                enforcement_mode,

            "outcome":
                "pass",

            "reason_code":
                "living_policy.not_applicable",

            "reason":
                applicability[
                    "reason"
                ],

            "applicability":
                applicability,
        }

    if applicability[
        "applicable"
    ] is None:
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

            "applicable":
                None,

            "effect":
                effect,

            "enforcement_mode":
                enforcement_mode,

            "outcome":
                "unknown",

            "reason_code":
                "living_policy.applicability_unknown",

            "reason":
                applicability[
                    "reason"
                ],

            "applicability":
                applicability,
        }

    evidence = _evidence_result(
        record,
        context,
    )

    if evidence[
        "satisfied"
    ] is not True:
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

            "applicable":
                True,

            "effect":
                effect,

            "enforcement_mode":
                enforcement_mode,

            "outcome":
                "unknown",

            "reason_code":
                "living_policy.required_evidence_missing",

            "reason":
                "required evidence is unavailable",

            "evidence":
                evidence,

            "applicability":
                applicability,
        }

    predicate = evaluate_predicate(
        record.get(
            "predicate"
        ),
        context,
    )

    matched = predicate[
        "result"
    ]

    if matched is None:
        outcome = "unknown"
        reason = "predicate could not be deterministically resolved"

    elif (
        enforcement_mode
        == "authority_required"
        or effect
        == "authority_required"
    ):
        granted = bool(
            (
                context.get(
                    "authority"
                )
                or {}
            ).get(
                "granted",
                False,
            )
        ) if isinstance(
            context.get(
                "authority"
            ),
            Mapping,
        ) else False

        outcome = (
            "pass"
            if (
                not matched
                or granted
            )
            else "authority-required"
        )

        reason = (
            "authority requirement satisfied"
            if outcome == "pass"
            else "explicit authority is required"
        )

    elif effect == "deny":
        outcome = (
            "fail"
            if matched
            else "pass"
        )

        reason = (
            "denied condition matched"
            if matched
            else "denied condition did not match"
        )

    elif effect in {
        "allow",
        "require",
    }:
        outcome = (
            "pass"
            if matched
            else "fail"
        )

        reason = (
            "required condition satisfied"
            if matched
            else "required condition failed"
        )

    elif effect == "advisory":
        outcome = (
            "advisory"
            if matched
            else "pass"
        )

        reason = (
            "advisory condition matched"
            if matched
            else "advisory condition did not match"
        )

    else:
        outcome = "unknown"
        reason = "unsupported policy effect"

    if (
        outcome == "fail"
        and enforcement_mode == "advisory"
    ):
        outcome = "advisory"

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
            True,

        "effect":
            effect,

        "enforcement_mode":
            enforcement_mode,

        "outcome":
            outcome,

        "reason_code":
            str(
                record.get(
                    "reason_code"
                )
                or (
                    "living_policy."
                    + effect
                    + "."
                    + outcome.replace(
                        "-",
                        "_",
                    )
                )
            ),

        "reason":
            reason,

        "remediation":
            record.get(
                "remediation"
            ),

        "evidence":
            evidence,

        "predicate":
            predicate,

        "applicability":
            applicability,

        "trace": {
            "applicability":
                applicability.get(
                    "trace",
                    [],
                ),

            "predicate":
                predicate.get(
                    "trace",
                    [],
                ),
        },
    }


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

    decision = _overall_outcome(
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

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "decision":
            decision,

        "allowed":
            decision
            not in {
                "fail",
                "unknown",
                "authority-required",
            },

        "evaluation_count":
            len(
                evaluations
            ),

        "outcome_counts":
            counts,

        "governing_rules": [
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
        ],

        "reason_codes":
            sorted(
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
            ),

        "unresolved_unknowns": [
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
        ],

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

        "because": [
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
            blockers,

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
