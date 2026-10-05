#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


LEXICON_ROOT = Path(
    __file__
).resolve().parents[1]

PROJECTION_ROOT = (
    LEXICON_ROOT
    / "projection_engine"
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

PROJECTION_REGISTRY = (
    PROJECTION_ROOT
    / "projection_registry.yaml"
)

DEFAULT_OUTPUT = (
    PROJECTION_ROOT
    / "runtime"
)


class ProjectionError(
    RuntimeError
):
    pass


class ProjectionEngine:

    def __init__(
        self,
    ) -> None:

        self.instances: dict[
            str,
            dict[str, Any],
        ] = {}

        self.segues: dict[
            str,
            dict[str, Any],
        ] = {}

        self.projections: dict[
            str,
            dict[str, Any],
        ] = {}

        self.projection_index: dict[
            str,
            list[str],
        ] = defaultdict(
            list
        )

        self.load()

    def load_yaml(
        self,
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

    def load(
        self,
    ) -> None:

        instance_data = self.load_yaml(
            INSTANCE_REGISTRY
        )

        segue_data = self.load_yaml(
            SEGUE_REGISTRY
        )

        projection_data = self.load_yaml(
            PROJECTION_REGISTRY
        )

        for record in instance_data.get(
            "instances",
            [],
        ):

            if not isinstance(
                record,
                dict,
            ):

                continue

            reference = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if reference:

                self.instances[
                    reference
                ] = record

        for record in segue_data.get(
            "segues",
            [],
        ):

            if not isinstance(
                record,
                dict,
            ):

                continue

            reference = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if reference:

                self.segues[
                    reference
                ] = record

        for record in projection_data.get(
            "projections",
            [],
        ):

            if not isinstance(
                record,
                dict,
            ):

                continue

            reference = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if not reference:

                continue

            self.projections[
                reference
            ] = record

            source_type = str(
                record.get(
                    "source_type",
                    "",
                )
            ).strip()

            if source_type:

                self.projection_index[
                    source_type
                ].append(
                    reference
                )

        for key in self.projection_index:

            self.projection_index[
                key
            ] = sorted(
                self.projection_index[
                    key
                ]
            )

    def resolve_projection(
        self,
        projection_id: str,
    ) -> dict[str, Any]:

        if projection_id not in self.projections:

            raise KeyError(
                projection_id
            )

        return self.projections[
            projection_id
        ]

    def resolve_source(
        self,
        source_type: str,
        source_id: str,
    ) -> dict[str, Any]:

        if source_type == "instance":

            collection = self.instances

        elif source_type == "segue":

            collection = self.segues

        else:

            raise ProjectionError(
                f"Unsupported source type: "
                f"{source_type}"
            )

        if source_id not in collection:

            raise KeyError(
                source_id
            )

        return collection[
            source_id
        ]

    def read_path(
        self,
        source: Any,
        path: str,
        default: Any = None,
    ) -> Any:

        if not path:

            return source

        current = source

        for part in path.split(
            "."
        ):

            if isinstance(
                current,
                dict,
            ):

                if part not in current:

                    return default

                current = current[
                    part
                ]

                continue

            if isinstance(
                current,
                list,
            ):

                try:

                    index = int(
                        part
                    )

                except ValueError:

                    return default

                if (
                    index < 0
                    or index >= len(
                        current
                    )
                ):

                    return default

                current = current[
                    index
                ]

                continue

            return default

        return current

    def write_path(
        self,
        target: dict[str, Any],
        path: str,
        value: Any,
    ) -> None:

        if not path:

            raise ProjectionError(
                "Projection target path is empty"
            )

        parts = path.split(
            "."
        )

        cursor = target

        for part in parts[:-1]:

            child = cursor.get(
                part
            )

            if not isinstance(
                child,
                dict,
            ):

                child = {}

                cursor[
                    part
                ] = child

            cursor = child

        cursor[
            parts[-1]
        ] = value

    def delete_path(
        self,
        target: dict[str, Any],
        path: str,
    ) -> None:

        parts = path.split(
            "."
        )

        cursor: Any = target

        for part in parts[:-1]:

            if not isinstance(
                cursor,
                dict,
            ):

                return

            cursor = cursor.get(
                part
            )

            if cursor is None:

                return

        if isinstance(
            cursor,
            dict,
        ):

            cursor.pop(
                parts[-1],
                None,
            )

    def normalize_value(
        self,
        value: Any,
        transform: str | None,
    ) -> Any:

        if not transform:

            return value

        if transform == "copy":

            return copy.deepcopy(
                value
            )

        if transform == "string":

            if value is None:

                return ""

            return str(
                value
            )

        if transform == "integer":

            return int(
                value
            )

        if transform == "float":

            return float(
                value
            )

        if transform == "boolean":

            return bool(
                value
            )

        if transform == "lower":

            return str(
                value
            ).lower()

        if transform == "upper":

            return str(
                value
            ).upper()

        if transform == "sorted":

            if isinstance(
                value,
                dict,
            ):

                return {
                    key: value[key]
                    for key in sorted(
                        value
                    )
                }

            if isinstance(
                value,
                list,
            ):

                return sorted(
                    value,
                    key=lambda item: json.dumps(
                        item,
                        sort_keys=True,
                        default=str,
                    ),
                )

            return value

        if transform == "unique":

            if not isinstance(
                value,
                list,
            ):

                return value

            seen: set[str] = set()
            result = []

            for item in value:

                fingerprint = json.dumps(
                    item,
                    sort_keys=True,
                    default=str,
                )

                if fingerprint in seen:

                    continue

                seen.add(
                    fingerprint
                )

                result.append(
                    item
                )

            return result

        if transform == "keys":

            if isinstance(
                value,
                dict,
            ):

                return sorted(
                    value.keys()
                )

            return []

        if transform == "values":

            if isinstance(
                value,
                dict,
            ):

                return [
                    value[key]
                    for key in sorted(
                        value
                    )
                ]

            return []

        if transform == "length":

            try:

                return len(
                    value
                )

            except TypeError:

                return 0

        raise ProjectionError(
            f"Unsupported transform: "
            f"{transform}"
        )

    def condition_matches(
        self,
        source: dict[str, Any],
        condition: Any,
    ) -> bool:

        if isinstance(
            condition,
            bool,
        ):

            return condition

        if isinstance(
            condition,
            str,
        ):

            return bool(
                self.read_path(
                    source,
                    condition,
                )
            )

        if not isinstance(
            condition,
            dict,
        ):

            return False

        if "all" in condition:

            children = condition.get(
                "all"
            )

            if not isinstance(
                children,
                list,
            ):

                return False

            return all(
                self.condition_matches(
                    source,
                    child,
                )
                for child in children
            )

        if "any" in condition:

            children = condition.get(
                "any"
            )

            if not isinstance(
                children,
                list,
            ):

                return False

            return any(
                self.condition_matches(
                    source,
                    child,
                )
                for child in children
            )

        if "not" in condition:

            return not self.condition_matches(
                source,
                condition.get(
                    "not"
                ),
            )

        path = str(
            condition.get(
                "path",
                "",
            )
        ).strip()

        operator = str(
            condition.get(
                "operator",
                "equals",
            )
        ).strip()

        expected = condition.get(
            "value"
        )

        actual = self.read_path(
            source,
            path,
        )

        if operator == "equals":

            return actual == expected

        if operator == "not_equals":

            return actual != expected

        if operator == "exists":

            return actual is not None

        if operator == "missing":

            return actual is None

        if operator == "truthy":

            return bool(
                actual
            )

        if operator == "falsy":

            return not bool(
                actual
            )

        if operator == "contains":

            try:

                return expected in actual

            except TypeError:

                return False

        if operator == "in":

            try:

                return actual in expected

            except TypeError:

                return False

        return False

    def apply_field_projection(
        self,
        source: dict[str, Any],
        output: dict[str, Any],
        field_projection: dict[str, Any],
    ) -> None:

        source_path = str(
            field_projection.get(
                "source",
                "",
            )
        ).strip()

        target_path = str(
            field_projection.get(
                "target",
                source_path,
            )
        ).strip()

        required = bool(
            field_projection.get(
                "required",
                False,
            )
        )

        default = field_projection.get(
            "default"
        )

        transform = field_projection.get(
            "transform",
            "copy",
        )

        value = self.read_path(
            source,
            source_path,
            default,
        )

        if (
            required
            and value is None
        ):

            raise ProjectionError(
                f"Required projection field "
                f"is missing: {source_path}"
            )

        value = self.normalize_value(
            value,
            transform,
        )

        self.write_path(
            output,
            target_path,
            value,
        )

    def apply_operation(
        self,
        source: dict[str, Any],
        output: dict[str, Any],
        operation: dict[str, Any],
    ) -> None:

        operation_type = str(
            operation.get(
                "operation",
                "",
            )
        ).strip()

        target_path = str(
            operation.get(
                "target",
                "",
            )
        ).strip()

        if operation_type == "set":

            value = copy.deepcopy(
                operation.get(
                    "value"
                )
            )

            self.write_path(
                output,
                target_path,
                value,
            )

            return

        if operation_type == "delete":

            self.delete_path(
                output,
                target_path,
            )

            return

        if operation_type == "copy":

            source_path = str(
                operation.get(
                    "source",
                    "",
                )
            ).strip()

            value = self.read_path(
                source,
                source_path,
            )

            self.write_path(
                output,
                target_path,
                copy.deepcopy(
                    value
                ),
            )

            return

        if operation_type == "append":

            current = self.read_path(
                output,
                target_path,
                [],
            )

            if not isinstance(
                current,
                list,
            ):

                current = []

            value = copy.deepcopy(
                operation.get(
                    "value"
                )
            )

            current = [
                *current,
                value,
            ]

            self.write_path(
                output,
                target_path,
                current,
            )

            return

        raise ProjectionError(
            f"Unsupported projection "
            f"operation: {operation_type}"
        )

    def project_record(
        self,
        projection_id: str,
        source_id: str,
    ) -> dict[str, Any]:

        projection = self.resolve_projection(
            projection_id
        )

        status = str(
            projection.get(
                "status",
                "active",
            )
        ).strip()

        if status != "active":

            raise ProjectionError(
                f"Projection is not active: "
                f"{projection_id}"
            )

        source_type = str(
            projection.get(
                "source_type",
                "",
            )
        ).strip()

        source = self.resolve_source(
            source_type,
            source_id,
        )

        conditions = projection.get(
            "conditions",
            [],
        )

        if conditions:

            if not isinstance(
                conditions,
                list,
            ):

                raise ProjectionError(
                    "Projection conditions "
                    "must be a list"
                )

            if not all(
                self.condition_matches(
                    source,
                    condition,
                )
                for condition in conditions
            ):

                raise ProjectionError(
                    f"Projection conditions "
                    f"failed: {projection_id}"
                )

        output: dict[str, Any] = {}

        fields = projection.get(
            "fields",
            [],
        )

        if not isinstance(
            fields,
            list,
        ):

            raise ProjectionError(
                "Projection fields must "
                "be a list"
            )

        for field_projection in fields:

            if not isinstance(
                field_projection,
                dict,
            ):

                raise ProjectionError(
                    "Projection field must "
                    "be an object"
                )

            self.apply_field_projection(
                source,
                output,
                field_projection,
            )

        operations = projection.get(
            "operations",
            [],
        )

        if not isinstance(
            operations,
            list,
        ):

            raise ProjectionError(
                "Projection operations "
                "must be a list"
            )

        for operation in operations:

            if not isinstance(
                operation,
                dict,
            ):

                raise ProjectionError(
                    "Projection operation "
                    "must be an object"
                )

            self.apply_operation(
                source,
                output,
                operation,
            )

        metadata = {
            "projection": projection_id,
            "source_type": source_type,
            "source_id": source_id,
            "authority": projection.get(
                "authority"
            ),
            "version": projection.get(
                "version"
            ),
            "dependencies": copy.deepcopy(
                projection.get(
                    "dependencies",
                    [],
                )
            ),
            "provenance": copy.deepcopy(
                projection.get(
                    "provenance",
                    {},
                )
            ),
            "lineage": {
                "projection": projection_id,
                "source": source_id,
                "source_digest": hashlib.sha256(
                    json.dumps(
                        source,
                        sort_keys=True,
                        separators=(
                            ",",
                            ":",
                        ),
                        default=str,
                    ).encode(
                        "utf-8"
                    )
                ).hexdigest(),
            },
        }

        return {
            "metadata": metadata,
            "data": output,
        }

    def project_all(
        self,
        projection_id: str,
    ) -> dict[str, Any]:

        projection = self.resolve_projection(
            projection_id
        )

        source_type = str(
            projection.get(
                "source_type",
                "",
            )
        ).strip()

        if source_type == "instance":

            source_ids = sorted(
                self.instances
            )

        elif source_type == "segue":

            source_ids = sorted(
                self.segues
            )

        else:

            raise ProjectionError(
                f"Unsupported source type: "
                f"{source_type}"
            )

        projected = {}
        skipped = {}

        for source_id in source_ids:

            try:

                projected[
                    source_id
                ] = self.project_record(
                    projection_id,
                    source_id,
                )

            except ProjectionError as error:

                skipped[
                    source_id
                ] = str(
                    error
                )

        return {
            "projection": projection_id,
            "source_type": source_type,
            "projected": projected,
            "skipped": skipped,
        }

    def snapshot(
        self,
        projection_id: str,
    ) -> dict[str, Any]:

        result = self.project_all(
            projection_id
        )

        digest = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                default=str,
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        return {
            "projection": projection_id,
            "projected_count": len(
                result[
                    "projected"
                ]
            ),
            "skipped_count": len(
                result[
                    "skipped"
                ]
            ),
            "digest": digest,
        }

    def write_json(
        self,
        path: Path,
        payload: Any,
    ) -> None:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = path.with_name(
            f".{path.name}.tmp"
        )

        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            temporary,
            path,
        )

    def materialize(
        self,
        projection_id: str,
        output_root: Path,
    ) -> dict[str, Any]:

        projection = self.resolve_projection(
            projection_id
        )

        output_name = str(
            projection.get(
                "output",
                projection_id.replace(
                    ":",
                    "_",
                ),
            )
        ).strip()

        result = self.project_all(
            projection_id
        )

        snapshot = self.snapshot(
            projection_id
        )

        projection_output = (
            output_root
            / output_name
        )

        self.write_json(
            projection_output
            / "projection.json",
            result,
        )

        self.write_json(
            projection_output
            / "snapshot.json",
            snapshot,
        )

        manifest = {
            "projection": projection_id,
            "output": str(
                projection_output.resolve()
            ),
            "files": [
                "projection.json",
                "snapshot.json",
            ],
            "snapshot": snapshot,
        }

        self.write_json(
            projection_output
            / "manifest.json",
            manifest,
        )

        return manifest

    def materialize_all(
        self,
        output_root: Path,
    ) -> dict[str, Any]:

        manifests = {}

        for projection_id in sorted(
            self.projections
        ):

            projection = self.projections[
                projection_id
            ]

            if projection.get(
                "status",
                "active",
            ) != "active":

                continue

            manifests[
                projection_id
            ] = self.materialize(
                projection_id,
                output_root,
            )

        aggregate = {
            "projection_count": len(
                manifests
            ),
            "projections": manifests,
        }

        self.write_json(
            output_root
            / "manifest.json",
            aggregate,
        )

        return aggregate


def main(
) -> int:

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    resolve_parser = subparsers.add_parser(
        "resolve"
    )

    resolve_parser.add_argument(
        "projection_id"
    )

    record_parser = subparsers.add_parser(
        "record"
    )

    record_parser.add_argument(
        "projection_id"
    )

    record_parser.add_argument(
        "source_id"
    )

    all_parser = subparsers.add_parser(
        "all"
    )

    all_parser.add_argument(
        "projection_id"
    )

    snapshot_parser = subparsers.add_parser(
        "snapshot"
    )

    snapshot_parser.add_argument(
        "projection_id"
    )

    materialize_parser = subparsers.add_parser(
        "materialize"
    )

    materialize_parser.add_argument(
        "projection_id"
    )

    materialize_parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT
        ),
    )

    materialize_all_parser = (
        subparsers.add_parser(
            "materialize-all"
        )
    )

    materialize_all_parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT
        ),
    )

    args = parser.parse_args()

    engine = ProjectionEngine()

    if args.command == "resolve":

        result = engine.resolve_projection(
            args.projection_id
        )

    elif args.command == "record":

        result = engine.project_record(
            args.projection_id,
            args.source_id,
        )

    elif args.command == "all":

        result = engine.project_all(
            args.projection_id
        )

    elif args.command == "snapshot":

        result = engine.snapshot(
            args.projection_id
        )

    elif args.command == "materialize":

        result = engine.materialize(
            args.projection_id,
            Path(
                args.output
            ),
        )

    elif args.command == "materialize-all":

        result = engine.materialize_all(
            Path(
                args.output
            )
        )

    else:

        raise RuntimeError(
            args.command
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
