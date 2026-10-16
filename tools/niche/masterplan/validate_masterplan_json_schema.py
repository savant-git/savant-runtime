#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

SCHEMA_PATH = (
    ROOT
    / "edifices"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
    / "schema"
    / "masterplan_graph.schema.json"
)

PUBLISHED_SCHEMA_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "schema"
    / "masterplan_graph.schema.json"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "schema-validation"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds"
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")


def deterministic_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(value.items())
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def semantic_digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(value)
        )
    ).hexdigest()


def sha256_path(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b""
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def atomic_write_text(
    path: Path,
    value: str
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent)
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8"
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary_path,
            path
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True
        )
        + "\n"
    )


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()

    except ValueError:
        return str(path)


def resolve_path(path: Path) -> Path:
    path = path.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    return path.resolve()


def error_record(error: Any) -> dict[str, Any]:
    return {
        "message": error.message,
        "validator": error.validator,
        "validator_value": error.validator_value,
        "instance_path": [
            str(value)
            for value in error.absolute_path
        ],
        "schema_path": [
            str(value)
            for value in error.absolute_schema_path
        ],
        "context": [
            error_record(child)
            for child in error.context
        ]
    }


def validate(
    graph_path: Path,
    schema_path: Path
) -> dict[str, Any]:
    if not graph_path.is_file():
        raise FileNotFoundError(graph_path)

    if not schema_path.is_file():
        raise FileNotFoundError(schema_path)

    graph = load_json(graph_path)
    schema = load_json(schema_path)

    if not isinstance(graph, dict):
        raise ValueError(
            "Authoritative graph must be a JSON object."
        )

    if not isinstance(schema, dict):
        raise ValueError(
            "JSON Schema must be a JSON object."
        )

    Draft202012Validator.check_schema(
        schema
    )

    validator = Draft202012Validator(
        schema
    )

    errors = sorted(
        validator.iter_errors(graph),
        key=lambda error: (
            tuple(
                str(value)
                for value in error.absolute_path
            ),
            error.message
        )
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "json-schema-validation/1.0.0"
        ),
        "operation": (
            "validate_masterplan_json_schema"
        ),
        "generated_at": utc_now(),
        "passed": not errors,
        "graph": {
            "path": relative_path(graph_path),
            "sha256": sha256_path(graph_path),
            "semantic_digest": semantic_digest(
                graph
            ),
            "schema_version": graph.get(
                "schema_version"
            )
        },
        "json_schema": {
            "path": relative_path(schema_path),
            "sha256": sha256_path(schema_path),
            "id": schema.get("$id"),
            "draft": schema.get("$schema")
        },
        "statistics": {
            "error_count": len(errors)
        },
        "errors": [
            error_record(error)
            for error in errors
        ]
    }

    result["semantic_digest"] = (
        semantic_digest(result)
    )

    return result


def publish_schema(
    schema_path: Path
) -> dict[str, Any]:
    schema = load_json(
        schema_path
    )

    Draft202012Validator.check_schema(
        schema
    )

    atomic_write_json(
        PUBLISHED_SCHEMA_PATH,
        schema
    )

    return {
        "path": relative_path(
            PUBLISHED_SCHEMA_PATH
        ),
        "sha256": sha256_path(
            PUBLISHED_SCHEMA_PATH
        ),
        "id": schema.get("$id")
    }


def persist_report(
    result: dict[str, Any]
) -> dict[str, str]:
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    run_id = timestamp()

    historical = (
        REPORT_ROOT
        / f"{run_id}__schema-validation.json"
    )

    latest = (
        REPORT_ROOT
        / "latest.json"
    )

    atomic_write_json(
        historical,
        result
    )

    atomic_write_json(
        latest,
        result
    )

    return {
        "historical": relative_path(
            historical
        ),
        "latest": relative_path(
            latest
        )
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the authoritative Masterplan "
            "graph against its Draft 2020-12 JSON Schema."
        )
    )

    parser.add_argument(
        "--graph",
        type=Path,
        default=GRAPH_PATH
    )

    parser.add_argument(
        "--schema",
        type=Path,
        default=SCHEMA_PATH
    )

    parser.add_argument(
        "--publish-schema",
        action="store_true"
    )

    parser.add_argument(
        "--strict",
        action="store_true"
    )

    arguments = parser.parse_args()

    try:
        graph_path = resolve_path(
            arguments.graph
        )

        schema_path = resolve_path(
            arguments.schema
        )

        result = validate(
            graph_path,
            schema_path
        )

        if arguments.publish_schema:
            result["published_schema"] = (
                publish_schema(
                    schema_path
                )
            )

        result["reports"] = persist_report(
            result
        )

    except SchemaError as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "validate_masterplan_json_schema"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "code": (
                            "masterplan.schema."
                            "invalid_json_schema"
                        )
                    }
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True
            )
        )

        return 1

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "validate_masterplan_json_schema"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "code": (
                            "masterplan.schema."
                            "validation_failed"
                        )
                    }
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True
        )
    )

    if (
        arguments.strict
        and not result["passed"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
