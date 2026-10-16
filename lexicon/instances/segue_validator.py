#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from instance_validator import validate as validate_instances
from segue_engine import SegueEngine


ROOT = Path(__file__).resolve().parent
SEGUE_REGISTRY = ROOT / "segue_registry.yaml"

ALLOWED_OPERATORS = {
    "equals",
    "not_equals",
    "exists",
    "missing",
    "truthy",
    "falsy",
    "contains",
    "in",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
}

ALLOWED_EFFECT_OPERATIONS = {
    "set",
    "delete",
    "append",
    "increment",
}


def load_yaml(
    path: Path,
) -> dict[str, Any]:

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = yaml.safe_load(
            handle
        )

    if not isinstance(
        data,
        dict,
    ):

        raise ValueError(
            f"Invalid YAML root: {path}"
        )

    return data


def add_issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    reference: str | None = None,
    field: str | None = None,
    value: Any = None,
    severity: str = "error",
) -> None:

    issue: dict[str, Any] = {
        "code": code,
        "message": message,
        "severity": severity,
    }

    if reference is not None:

        issue["reference"] = reference

    if field is not None:

        issue["field"] = field

    if value is not None:

        issue["value"] = value

    issues.append(
        issue
    )


def validate_condition(
    issues: list[dict[str, Any]],
    segue_id: str,
    condition: Any,
    field: str,
) -> None:

    if isinstance(
        condition,
        bool,
    ):

        return

    if isinstance(
        condition,
        str,
    ):

        if not condition.strip():

            add_issue(
                issues,
                "segue.condition.empty",
                "String condition cannot be empty",
                reference=segue_id,
                field=field,
            )

        return

    if not isinstance(
        condition,
        dict,
    ):

        add_issue(
            issues,
            "segue.condition.invalid",
            "Condition must be a boolean, string, or object",
            reference=segue_id,
            field=field,
        )

        return

    logical_keys = [
        key
        for key in (
            "all",
            "any",
            "not",
        )
        if key in condition
    ]

    if logical_keys:

        if len(
            logical_keys
        ) > 1:

            add_issue(
                issues,
                "segue.condition.logical_conflict",
                "Condition cannot contain multiple logical operators",
                reference=segue_id,
                field=field,
                value=logical_keys,
            )

            return

        operator = logical_keys[0]
        value = condition[
            operator
        ]

        if operator in {
            "all",
            "any",
        }:

            if not isinstance(
                value,
                list,
            ):

                add_issue(
                    issues,
                    "segue.condition.logical_list_required",
                    f"{operator} must contain a list",
                    reference=segue_id,
                    field=f"{field}.{operator}",
                )

                return

            if not value:

                add_issue(
                    issues,
                    "segue.condition.logical_empty",
                    f"{operator} cannot be empty",
                    reference=segue_id,
                    field=f"{field}.{operator}",
                )

            for index, child in enumerate(
                value
            ):

                validate_condition(
                    issues,
                    segue_id,
                    child,
                    (
                        f"{field}.{operator}"
                        f"[{index}]"
                    ),
                )

            return

        validate_condition(
            issues,
            segue_id,
            value,
            f"{field}.not",
        )

        return

    condition_field = condition.get(
        "field"
    )

    operator = condition.get(
        "operator",
        "equals",
    )

    if not isinstance(
        condition_field,
        str,
    ) or not condition_field.strip():

        add_issue(
            issues,
            "segue.condition.field_missing",
            "Condition field is missing",
            reference=segue_id,
            field=f"{field}.field",
        )

    if operator not in ALLOWED_OPERATORS:

        add_issue(
            issues,
            "segue.condition.operator_invalid",
            "Condition operator is invalid",
            reference=segue_id,
            field=f"{field}.operator",
            value=operator,
        )

    operators_without_value = {
        "exists",
        "missing",
        "truthy",
        "falsy",
    }

    if (
        operator
        not in operators_without_value
        and "value"
        not in condition
    ):

        add_issue(
            issues,
            "segue.condition.value_missing",
            "Condition value is required",
            reference=segue_id,
            field=f"{field}.value",
        )


def validate_effect(
    issues: list[dict[str, Any]],
    segue_id: str,
    effect: Any,
    field: str,
) -> None:

    if not isinstance(
        effect,
        dict,
    ):

        add_issue(
            issues,
            "segue.effect.invalid",
            "Effect must be an object",
            reference=segue_id,
            field=field,
        )

        return

    operation = effect.get(
        "operation",
        "set",
    )

    target_field = effect.get(
        "field"
    )

    if operation not in ALLOWED_EFFECT_OPERATIONS:

        add_issue(
            issues,
            "segue.effect.operation_invalid",
            "Effect operation is invalid",
            reference=segue_id,
            field=f"{field}.operation",
            value=operation,
        )

    if not isinstance(
        target_field,
        str,
    ) or not target_field.strip():

        add_issue(
            issues,
            "segue.effect.field_missing",
            "Effect field is missing",
            reference=segue_id,
            field=f"{field}.field",
        )

    if (
        operation
        in {
            "set",
            "append",
            "increment",
        }
        and "value"
        not in effect
    ):

        add_issue(
            issues,
            "segue.effect.value_missing",
            "Effect value is required",
            reference=segue_id,
            field=f"{field}.value",
        )

    if (
        operation == "increment"
        and "value" in effect
        and not isinstance(
            effect["value"],
            (
                int,
                float,
            ),
        )
    ):

        add_issue(
            issues,
            "segue.effect.increment_invalid",
            "Increment value must be numeric",
            reference=segue_id,
            field=f"{field}.value",
            value=effect["value"],
        )


def validate() -> list[dict[str, Any]]:

    issues = validate_instances()

    data = load_yaml(
        SEGUE_REGISTRY
    )

    segues = data.get(
        "segues",
        [],
    )

    if not isinstance(
        segues,
        list,
    ):

        return issues

    engine = SegueEngine()

    pair_index: dict[
        tuple[str, str, str],
        list[str],
    ] = {}

    for position, record in enumerate(
        segues
    ):

        if not isinstance(
            record,
            dict,
        ):

            continue

        segue_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        if not segue_id:

            continue

        source = str(
            record.get(
                "from",
                "",
            )
        ).strip()

        target = str(
            record.get(
                "to",
                "",
            )
        ).strip()

        relation = str(
            record.get(
                "relation",
                "",
            )
        ).strip()

        direction = str(
            record.get(
                "direction",
                "directed",
            )
        ).strip()

        conditions = record.get(
            "conditions",
            [],
        )

        effects = record.get(
            "effects",
            [],
        )

        metadata = record.get(
            "metadata",
            {},
        )

        if isinstance(
            conditions,
            list,
        ):

            for index, condition in enumerate(
                conditions
            ):

                validate_condition(
                    issues,
                    segue_id,
                    condition,
                    f"conditions[{index}]",
                )

        if isinstance(
            effects,
            list,
        ):

            for index, effect in enumerate(
                effects
            ):

                validate_effect(
                    issues,
                    segue_id,
                    effect,
                    f"effects[{index}]",
                )

        if not isinstance(
            metadata,
            dict,
        ):

            add_issue(
                issues,
                "segue.metadata.invalid",
                "Segue metadata must be an object",
                reference=segue_id,
                field="metadata",
            )

        else:

            weight = metadata.get(
                "weight",
                1,
            )

            if not isinstance(
                weight,
                (
                    int,
                    float,
                ),
            ):

                add_issue(
                    issues,
                    "segue.weight.invalid",
                    "Segue weight must be numeric",
                    reference=segue_id,
                    field="metadata.weight",
                    value=weight,
                )

            elif weight < 0:

                add_issue(
                    issues,
                    "segue.weight.negative",
                    "Segue weight cannot be negative",
                    reference=segue_id,
                    field="metadata.weight",
                    value=weight,
                )

        if direction == "directed":

            pair_key = (
                source,
                target,
                relation,
            )

        else:

            pair_key = (
                *sorted(
                    (
                        source,
                        target,
                    )
                ),
                relation,
            )

        owners = pair_index.setdefault(
            pair_key,
            [],
        )

        owners.append(
            segue_id
        )

        if (
            source in engine.instances
            and target in engine.instances
        ):

            try:

                engine.is_active(
                    record,
                    {},
                )

            except Exception as error:

                add_issue(
                    issues,
                    "segue.condition.runtime_failure",
                    "Segue condition evaluation failed",
                    reference=segue_id,
                    value={
                        "exception": type(
                            error
                        ).__name__,
                        "message": str(
                            error
                        ),
                    },
                )

            try:

                engine.execute(
                    segue_id,
                    context={},
                    state={},
                )

            except Exception as error:

                add_issue(
                    issues,
                    "segue.execution.runtime_failure",
                    "Segue execution failed",
                    reference=segue_id,
                    value={
                        "exception": type(
                            error
                        ).__name__,
                        "message": str(
                            error
                        ),
                    },
                )

    for pair, owners in sorted(
        pair_index.items()
    ):

        if len(
            owners
        ) > 1:

            add_issue(
                issues,
                "segue.parallel_duplicate",
                "Multiple segues share the same endpoints and relation",
                severity="warning",
                value={
                    "pair": list(
                        pair
                    ),
                    "segues": sorted(
                        owners
                    ),
                },
            )

    return issues


def main() -> int:

    try:

        issues = validate()

    except Exception as error:

        print(
            json.dumps(
                {
                    "valid": False,
                    "error_count": 1,
                    "warning_count": 0,
                    "issues": [
                        {
                            "code": (
                                "segue_validator."
                                "runtime_failure"
                            ),
                            "severity": "error",
                            "message": str(
                                error
                            ),
                            "exception": type(
                                error
                            ).__name__,
                        }
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    errors = [
        issue
        for issue in issues
        if issue.get(
            "severity"
        ) == "error"
    ]

    warnings = [
        issue
        for issue in issues
        if issue.get(
            "severity"
        ) == "warning"
    ]

    print(
        json.dumps(
            {
                "valid": not errors,
                "error_count": len(
                    errors
                ),
                "warning_count": len(
                    warnings
                ),
                "issues": issues,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return (
        1
        if errors
        else 0
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
