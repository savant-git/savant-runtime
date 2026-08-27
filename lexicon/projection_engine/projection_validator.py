#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from projection_engine import (
    ProjectionEngine,
    ProjectionError,
)


ROOT = Path(__file__).resolve().parent
LEXICON_ROOT = ROOT.parent

PROJECTION_REGISTRY = (
    ROOT
    / "projection_registry.yaml"
)

INSTANCE_REGISTRY = (
    LEXICON_ROOT
    / "instances"
    / "instance_registry.yaml"
)

SEGUE_REGISTRY = (
    LEXICON_ROOT
    / "instances"
    / "segue_registry.yaml"
)

PROJECTION_PATTERN = re.compile(
    r"^projection:[a-z][a-z0-9_-]*"
    r"(?::[a-z][a-z0-9_-]*)*$"
)

STATUS_VALUES = {
    "active",
    "dormant",
    "deprecated",
    "superseded",
    "reserved",
}

SOURCE_TYPES = {
    "instance",
    "segue",
}

TRANSFORMS = {
    "copy",
    "string",
    "integer",
    "float",
    "boolean",
    "lower",
    "upper",
    "sorted",
    "unique",
    "keys",
    "values",
    "length",
}

OPERATIONS = {
    "set",
    "delete",
    "copy",
    "append",
}

CONDITION_OPERATORS = {
    "equals",
    "not_equals",
    "exists",
    "missing",
    "truthy",
    "falsy",
    "contains",
    "in",
}

CONFIDENCE_VALUES = {
    "confirmed",
    "inferred",
    "projected",
}


def load_yaml(
    path: Path,
) -> dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            str(path)
        )

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


def text(
    value: Any,
) -> str:

    if value is None:

        return ""

    return str(
        value
    ).strip()


def add_issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    severity: str = "error",
    reference: str | None = None,
    field: str | None = None,
    value: Any = None,
) -> None:

    record: dict[str, Any] = {
        "code": code,
        "message": message,
        "severity": severity,
    }

    if reference:

        record[
            "reference"
        ] = reference

    if field:

        record[
            "field"
        ] = field

    if value is not None:

        record[
            "value"
        ] = value

    issues.append(
        record
    )


def validate_condition(
    issues: list[dict[str, Any]],
    projection_id: str,
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
                "projection.condition.empty",
                "Condition cannot be empty",
                reference=projection_id,
                field=field,
            )

        return

    if not isinstance(
        condition,
        dict,
    ):

        add_issue(
            issues,
            "projection.condition.invalid",
            "Condition must be boolean, string, or object",
            reference=projection_id,
            field=field,
        )

        return

    logical = [
        key
        for key in (
            "all",
            "any",
            "not",
        )
        if key in condition
    ]

    if logical:

        if len(
            logical
        ) > 1:

            add_issue(
                issues,
                "projection.condition.logical_conflict",
                "Condition has multiple logical operators",
                reference=projection_id,
                field=field,
                value=logical,
            )

            return

        operator = logical[0]
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
                    "projection.condition.logical_list_required",
                    "Logical condition requires a list",
                    reference=projection_id,
                    field=f"{field}.{operator}",
                )

                return

            for index, child in enumerate(
                value
            ):

                validate_condition(
                    issues,
                    projection_id,
                    child,
                    (
                        f"{field}.{operator}"
                        f"[{index}]"
                    ),
                )

            return

        validate_condition(
            issues,
            projection_id,
            value,
            f"{field}.not",
        )

        return

    path = text(
        condition.get(
            "path"
        )
    )

    operator = text(
        condition.get(
            "operator",
            "equals",
        )
    )

    if not path:

        add_issue(
            issues,
            "projection.condition.path_missing",
            "Condition path is missing",
            reference=projection_id,
            field=f"{field}.path",
        )

    if operator not in CONDITION_OPERATORS:

        add_issue(
            issues,
            "projection.condition.operator_invalid",
            "Condition operator is invalid",
            reference=projection_id,
            field=f"{field}.operator",
            value=operator,
        )

    if (
        operator
        not in {
            "exists",
            "missing",
            "truthy",
            "falsy",
        }
        and "value"
        not in condition
    ):

        add_issue(
            issues,
            "projection.condition.value_missing",
            "Condition value is required",
            reference=projection_id,
            field=f"{field}.value",
        )


def validate() -> list[dict[str, Any]]:

    issues: list[
        dict[str, Any]
    ] = []

    projection_data = load_yaml(
        PROJECTION_REGISTRY
    )

    instance_data = load_yaml(
        INSTANCE_REGISTRY
    )

    segue_data = load_yaml(
        SEGUE_REGISTRY
    )

    projections = projection_data.get(
        "projections",
        [],
    )

    if not isinstance(
        projections,
        list,
    ):

        add_issue(
            issues,
            "projection.registry.invalid",
            "projections must be a list",
        )

        return issues

    instance_ids = {
        text(
            record.get("id")
        )
        for record in instance_data.get(
            "instances",
            [],
        )
        if isinstance(
            record,
            dict,
        )
        and text(
            record.get("id")
        )
    }

    segue_ids = {
        text(
            record.get("id")
        )
        for record in segue_data.get(
            "segues",
            [],
        )
        if isinstance(
            record,
            dict,
        )
        and text(
            record.get("id")
        )
    }

    projection_ids: set[str] = set()

    canonical_index: dict[
        str,
        list[str],
    ] = defaultdict(
        list
    )

    output_index: dict[
        str,
        list[str],
    ] = defaultdict(
        list
    )

    records: dict[
        str,
        dict[str, Any],
    ] = {}

    for position, record in enumerate(
        projections
    ):

        if not isinstance(
            record,
            dict,
        ):

            add_issue(
                issues,
                "projection.record.invalid",
                "Projection record must be an object",
                value=position,
            )

            continue

        projection_id = text(
            record.get(
                "id"
            )
        )

        if not projection_id:

            add_issue(
                issues,
                "projection.id.missing",
                "Projection id is missing",
                value=position,
            )

            continue

        if not PROJECTION_PATTERN.fullmatch(
            projection_id
        ):

            add_issue(
                issues,
                "projection.id.invalid",
                "Projection id format is invalid",
                reference=projection_id,
                field="id",
            )

        if projection_id in projection_ids:

            add_issue(
                issues,
                "projection.id.duplicate",
                "Projection id is duplicated",
                reference=projection_id,
            )

        projection_ids.add(
            projection_id
        )

        records[
            projection_id
        ] = record

        canonical = text(
            record.get(
                "canonical"
            )
        )

        if not canonical:

            add_issue(
                issues,
                "projection.canonical.missing",
                "Canonical name is missing",
                reference=projection_id,
                field="canonical",
            )

        else:

            canonical_index[
                canonical.casefold()
            ].append(
                projection_id
            )

        status = text(
            record.get(
                "status",
                "active",
            )
        )

        if status not in STATUS_VALUES:

            add_issue(
                issues,
                "projection.status.invalid",
                "Projection status is invalid",
                reference=projection_id,
                field="status",
                value=status,
            )

        source_type = text(
            record.get(
                "source_type"
            )
        )

        if source_type not in SOURCE_TYPES:

            add_issue(
                issues,
                "projection.source_type.invalid",
                "Projection source type is invalid",
                reference=projection_id,
                field="source_type",
                value=source_type,
            )

        output = text(
            record.get(
                "output"
            )
        )

        if not output:

            add_issue(
                issues,
                "projection.output.missing",
                "Projection output is missing",
                reference=projection_id,
                field="output",
            )

        else:

            output_index[
                output
            ].append(
                projection_id
            )

        conditions = record.get(
            "conditions",
            [],
        )

        if not isinstance(
            conditions,
            list,
        ):

            add_issue(
                issues,
                "projection.conditions.invalid",
                "Projection conditions must be a list",
                reference=projection_id,
                field="conditions",
            )

        else:

            for index, condition in enumerate(
                conditions
            ):

                validate_condition(
                    issues,
                    projection_id,
                    condition,
                    f"conditions[{index}]",
                )

        fields = record.get(
            "fields",
            [],
        )

        if not isinstance(
            fields,
            list,
        ):

            add_issue(
                issues,
                "projection.fields.invalid",
                "Projection fields must be a list",
                reference=projection_id,
                field="fields",
            )

        else:

            target_paths: set[str] = set()

            for index, field_record in enumerate(
                fields
            ):

                field_name = (
                    f"fields[{index}]"
                )

                if not isinstance(
                    field_record,
                    dict,
                ):

                    add_issue(
                        issues,
                        "projection.field.invalid",
                        "Projection field must be an object",
                        reference=projection_id,
                        field=field_name,
                    )

                    continue

                source = text(
                    field_record.get(
                        "source"
                    )
                )

                target = text(
                    field_record.get(
                        "target"
                    )
                )

                transform = text(
                    field_record.get(
                        "transform",
                        "copy",
                    )
                )

                if not source:

                    add_issue(
                        issues,
                        "projection.field.source_missing",
                        "Projection field source is missing",
                        reference=projection_id,
                        field=f"{field_name}.source",
                    )

                if not target:

                    add_issue(
                        issues,
                        "projection.field.target_missing",
                        "Projection field target is missing",
                        reference=projection_id,
                        field=f"{field_name}.target",
                    )

                elif target in target_paths:

                    add_issue(
                        issues,
                        "projection.field.target_duplicate",
                        "Projection target path is duplicated",
                        reference=projection_id,
                        field=f"{field_name}.target",
                        value=target,
                    )

                else:

                    target_paths.add(
                        target
                    )

                if transform not in TRANSFORMS:

                    add_issue(
                        issues,
                        "projection.field.transform_invalid",
                        "Projection transform is invalid",
                        reference=projection_id,
                        field=f"{field_name}.transform",
                        value=transform,
                    )

        operations = record.get(
            "operations",
            [],
        )

        if not isinstance(
            operations,
            list,
        ):

            add_issue(
                issues,
                "projection.operations.invalid",
                "Projection operations must be a list",
                reference=projection_id,
                field="operations",
            )

        else:

            for index, operation in enumerate(
                operations
            ):

                field_name = (
                    f"operations[{index}]"
                )

                if not isinstance(
                    operation,
                    dict,
                ):

                    add_issue(
                        issues,
                        "projection.operation.invalid",
                        "Projection operation must be an object",
                        reference=projection_id,
                        field=field_name,
                    )

                    continue

                operation_type = text(
                    operation.get(
                        "operation"
                    )
                )

                target = text(
                    operation.get(
                        "target"
                    )
                )

                if operation_type not in OPERATIONS:

                    add_issue(
                        issues,
                        "projection.operation.type_invalid",
                        "Projection operation is invalid",
                        reference=projection_id,
                        field=f"{field_name}.operation",
                        value=operation_type,
                    )

                if not target:

                    add_issue(
                        issues,
                        "projection.operation.target_missing",
                        "Projection operation target is missing",
                        reference=projection_id,
                        field=f"{field_name}.target",
                    )

                if (
                    operation_type == "copy"
                    and not text(
                        operation.get(
                            "source"
                        )
                    )
                ):

                    add_issue(
                        issues,
                        "projection.operation.source_missing",
                        "Copy operation source is missing",
                        reference=projection_id,
                        field=f"{field_name}.source",
                    )

                if (
                    operation_type
                    in {
                        "set",
                        "append",
                    }
                    and "value"
                    not in operation
                ):

                    add_issue(
                        issues,
                        "projection.operation.value_missing",
                        "Projection operation value is missing",
                        reference=projection_id,
                        field=f"{field_name}.value",
                    )

        provenance = record.get(
            "provenance"
        )

        if not isinstance(
            provenance,
            dict,
        ):

            add_issue(
                issues,
                "projection.provenance.invalid",
                "Projection provenance must be an object",
                reference=projection_id,
                field="provenance",
            )

        else:

            confidence = text(
                provenance.get(
                    "confidence"
                )
            )

            if confidence not in CONFIDENCE_VALUES:

                add_issue(
                    issues,
                    "projection.provenance.confidence_invalid",
                    "Projection confidence is invalid",
                    reference=projection_id,
                    field="provenance.confidence",
                    value=confidence,
                )

        lineage = record.get(
            "lineage"
        )

        if not isinstance(
            lineage,
            dict,
        ):

            add_issue(
                issues,
                "projection.lineage.invalid",
                "Projection lineage must be an object",
                reference=projection_id,
                field="lineage",
            )

    all_dependencies = {
        *instance_ids,
        *segue_ids,
        *projection_ids,
    }

    for projection_id, record in records.items():

        dependencies = record.get(
            "dependencies",
            [],
        )

        if not isinstance(
            dependencies,
            list,
        ):

            add_issue(
                issues,
                "projection.dependencies.invalid",
                "Projection dependencies must be a list",
                reference=projection_id,
                field="dependencies",
            )

            continue

        for dependency in dependencies:

            dependency_id = text(
                dependency
            )

            if dependency_id not in all_dependencies:

                add_issue(
                    issues,
                    "projection.dependency.unresolved",
                    "Projection dependency does not resolve",
                    reference=projection_id,
                    field="dependencies",
                    value=dependency_id,
                )

    for canonical, owners in sorted(
        canonical_index.items()
    ):

        if len(
            owners
        ) > 1:

            add_issue(
                issues,
                "projection.canonical.duplicate",
                "Projection canonical name is duplicated",
                value={
                    "canonical": canonical,
                    "owners": sorted(
                        owners
                    ),
                },
            )

    for output, owners in sorted(
        output_index.items()
    ):

        if len(
            owners
        ) > 1:

            add_issue(
                issues,
                "projection.output.duplicate",
                "Projection output is shared",
                severity="warning",
                value={
                    "output": output,
                    "owners": sorted(
                        owners
                    ),
                },
            )

    engine = ProjectionEngine()

    for projection_id, record in records.items():

        if record.get(
            "status",
            "active",
        ) != "active":

            continue

        source_type = record.get(
            "source_type"
        )

        if source_type == "instance":

            source_ids = sorted(
                engine.instances
            )

        elif source_type == "segue":

            source_ids = sorted(
                engine.segues
            )

        else:

            continue

        if not source_ids:

            add_issue(
                issues,
                "projection.runtime.no_sources",
                "Projection has no source records",
                severity="warning",
                reference=projection_id,
            )

            continue

        runtime_success = False

        for source_id in source_ids:

            try:

                engine.project_record(
                    projection_id,
                    source_id,
                )

                runtime_success = True

                break

            except ProjectionError:

                continue

            except Exception as error:

                add_issue(
                    issues,
                    "projection.runtime.failure",
                    "Projection execution failed",
                    reference=projection_id,
                    value={
                        "source": source_id,
                        "exception": type(
                            error
                        ).__name__,
                        "message": str(
                            error
                        ),
                    },
                )

                break

        if not runtime_success:

            add_issue(
                issues,
                "projection.runtime.no_matches",
                "Projection matched no source records",
                severity="warning",
                reference=projection_id,
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
                                "projection_validator."
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
