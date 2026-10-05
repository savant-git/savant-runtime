#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT = Path("/root/savant-runtime")

SUBJECT_ROOT = (
    ROOT
    / "edifices"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
)

RUNTIME_ROOT = (
    SUBJECT_ROOT
    / "runtime"
)

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )


from masterplan_lock import (  # noqa: E402
    MasterplanLock,
    deterministic_projection,
    digest,
    graph_digest,
)


GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

SCHEMA_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "schema"
)

REGISTRY_PATH = (
    SCHEMA_ROOT
    / "registry.json"
)

MIGRATION_ROOT = (
    SUBJECT_ROOT
    / "schema"
    / "migrations"
)

SNAPSHOT_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
    / "snapshots"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "masterplan"
    / "schema-migrations"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "schema-migrations"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "schema"
)

CURRENT_SCHEMA_VERSION = "1.0.0"

VERSION_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)$"
)

MIGRATION_FILENAME_PATTERN = re.compile(
    r"^v(?P<from>[0-9]+_[0-9]+_[0-9]+)"
    r"__to__"
    r"v(?P<to>[0-9]+_[0-9]+_[0-9]+)"
    r"__"
    r"(?P<name>[a-z0-9_]+)\.py$"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}


MigrationFunction = Callable[
    [dict[str, Any]],
    dict[str, Any],
]


@dataclass(frozen=True)
class MigrationDescriptor:
    migration_id: str
    from_version: str
    to_version: str
    path: Path
    description: str
    reversible: bool
    module_digest: str


class SchemaRegistryError(RuntimeError):
    pass


class SchemaValidationError(SchemaRegistryError):
    pass


class MigrationPathError(SchemaRegistryError):
    pass


class MigrationExecutionError(SchemaRegistryError):
    pass


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )


def semantic_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(
                value
            )
        )
    ).hexdigest()


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise SchemaValidationError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(
            path.parent
        ),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                value
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(
            path
        )


def normalize_version(
    value: str,
) -> str:
    match = VERSION_PATTERN.fullmatch(
        value.strip()
    )

    if match is None:
        raise SchemaValidationError(
            f"Invalid semantic version: {value}"
        )

    return ".".join(
        str(
            int(part)
        )
        for part in match.groups()
    )


def version_tuple(
    value: str,
) -> tuple[int, int, int]:
    normalized = normalize_version(
        value
    )

    return tuple(
        int(part)
        for part in normalized.split(
            "."
        )
    )  # type: ignore[return-value]


def filename_version(
    value: str,
) -> str:
    return normalize_version(
        value.replace(
            "_",
            ".",
        )
    )


def validate_collection(
    graph: dict[str, Any],
    name: str,
) -> list[dict[str, Any]]:
    value = graph.get(
        name
    )

    if not isinstance(
        value,
        list,
    ):
        raise SchemaValidationError(
            (
                "Graph collection must be a list: "
                f"{name}"
            )
        )

    identifiers: set[str] = set()

    for index, record in enumerate(
        value
    ):
        if not isinstance(
            record,
            dict,
        ):
            raise SchemaValidationError(
                (
                    f"Invalid {name} record at "
                    f"index {index}."
                )
            )

        identifier = record.get(
            "id"
        )

        if not isinstance(
            identifier,
            str,
        ):
            raise SchemaValidationError(
                (
                    f"{name} record has no string "
                    f"identifier at index {index}."
                )
            )

        if identifier in identifiers:
            raise SchemaValidationError(
                (
                    f"Duplicate {name} identifier: "
                    f"{identifier}"
                )
            )

        identifiers.add(
            identifier
        )

    return value


def validate_graph(
    graph: dict[str, Any],
    *,
    expected_version: str | None = None,
) -> dict[str, Any]:
    required_fields = {
        "schema_version",
        "graph_id",
        "authority",
        "records",
        "segues",
        "events",
        "decisions",
        "evidence",
        "receipts",
        "attestations",
    }

    missing = sorted(
        required_fields
        - set(
            graph
        )
    )

    if missing:
        raise SchemaValidationError(
            (
                "Graph is missing required fields: "
                + ", ".join(
                    missing
                )
            )
        )

    schema_version = normalize_version(
        str(
            graph[
                "schema_version"
            ]
        )
    )

    if (
        expected_version
        is not None
        and schema_version
        != normalize_version(
            expected_version
        )
    ):
        raise SchemaValidationError(
            (
                "Graph schema version mismatch: "
                f"expected {expected_version}, "
                f"received {schema_version}"
            )
        )

    if not isinstance(
        graph.get(
            "graph_id"
        ),
        str,
    ):
        raise SchemaValidationError(
            "Graph identifier must be a string."
        )

    authority = graph.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        raise SchemaValidationError(
            "Graph authority must be an object."
        )

    collections = {}

    for name in (
        "records",
        "segues",
        "events",
        "decisions",
        "evidence",
        "receipts",
        "attestations",
    ):
        collections[
            name
        ] = validate_collection(
            graph,
            name,
        )

    task_ids = {
        record[
            "id"
        ]
        for record in collections[
            "records"
        ]
    }

    reference_issues: list[
        dict[str, Any]
    ] = []

    for segue in collections[
        "segues"
    ]:
        source = segue.get(
            "source"
        )
        target = segue.get(
            "target"
        )

        if source not in task_ids:
            reference_issues.append(
                {
                    "collection": "segues",
                    "record_id": segue[
                        "id"
                    ],
                    "field": "source",
                    "value": source,
                }
            )

        if target not in task_ids:
            reference_issues.append(
                {
                    "collection": "segues",
                    "record_id": segue[
                        "id"
                    ],
                    "field": "target",
                    "value": target,
                }
            )

    for name in (
        "events",
        "evidence",
        "receipts",
        "attestations",
    ):
        for record in collections[
            name
        ]:
            task_id = record.get(
                "task_id"
            )

            if task_id not in task_ids:
                reference_issues.append(
                    {
                        "collection": name,
                        "record_id": record[
                            "id"
                        ],
                        "field": "task_id",
                        "value": task_id,
                    }
                )

    for decision in collections[
        "decisions"
    ]:
        subject = decision.get(
            "subject"
        )

        if subject not in task_ids:
            reference_issues.append(
                {
                    "collection": "decisions",
                    "record_id": decision[
                        "id"
                    ],
                    "field": "subject",
                    "value": subject,
                }
            )

    if reference_issues:
        raise SchemaValidationError(
            json.dumps(
                {
                    "code": (
                        "masterplan.schema."
                        "invalid_references"
                    ),
                    "issues": (
                        reference_issues
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    return {
        "passed": True,
        "schema_version": (
            schema_version
        ),
        "graph_id": graph[
            "graph_id"
        ],
        "graph_digest": (
            semantic_digest(
                graph
            )
        ),
        "counts": {
            name: len(
                values
            )
            for name, values
            in collections.items()
        },
    }


def import_migration_module(
    path: Path,
) -> Any:
    module_name = (
        "savant_masterplan_migration_"
        + hashlib.sha256(
            str(
                path
            ).encode(
                "utf-8"
            )
        ).hexdigest()[
            :16
        ]
    )

    specification = (
        importlib.util
        .spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader
        is None
    ):
        raise MigrationExecutionError(
            (
                "Unable to load migration "
                f"module: {path}"
            )
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


def migration_descriptor(
    path: Path,
) -> MigrationDescriptor:
    match = (
        MIGRATION_FILENAME_PATTERN
        .fullmatch(
            path.name
        )
    )

    if match is None:
        raise SchemaValidationError(
            (
                "Invalid migration filename: "
                f"{path.name}"
            )
        )

    from_version = filename_version(
        match.group(
            "from"
        )
    )

    to_version = filename_version(
        match.group(
            "to"
        )
    )

    module = import_migration_module(
        path
    )

    module_from = normalize_version(
        str(
            getattr(
                module,
                "FROM_VERSION",
                "",
            )
        )
    )

    module_to = normalize_version(
        str(
            getattr(
                module,
                "TO_VERSION",
                "",
            )
        )
    )

    if (
        module_from
        != from_version
        or module_to
        != to_version
    ):
        raise SchemaValidationError(
            (
                "Migration module version "
                "metadata does not match "
                f"filename: {path.name}"
            )
        )

    migrate = getattr(
        module,
        "migrate",
        None,
    )

    if not callable(
        migrate
    ):
        raise SchemaValidationError(
            (
                "Migration module has no "
                f"callable migrate(): {path}"
            )
        )

    migration_id = str(
        getattr(
            module,
            "MIGRATION_ID",
            path.stem,
        )
    )

    description = str(
        getattr(
            module,
            "DESCRIPTION",
            "",
        )
    )

    reversible = bool(
        getattr(
            module,
            "REVERSIBLE",
            False,
        )
    )

    return MigrationDescriptor(
        migration_id=migration_id,
        from_version=from_version,
        to_version=to_version,
        path=path,
        description=description,
        reversible=reversible,
        module_digest=(
            sha256_path(
                path
            )
        ),
    )


def discover_migrations(
    root: Path = MIGRATION_ROOT,
) -> tuple[
    MigrationDescriptor,
    ...,
]:
    if not root.is_dir():
        return ()

    descriptors = [
        migration_descriptor(
            path
        )
        for path in sorted(
            root.glob(
                "v*__to__v*__*.py"
            ),
            key=lambda candidate: (
                candidate.name
            ),
        )
        if path.is_file()
    ]

    identifiers: set[str] = set()
    edges: set[
        tuple[
            str,
            str,
        ]
    ] = set()

    for descriptor in descriptors:
        if (
            descriptor.migration_id
            in identifiers
        ):
            raise SchemaValidationError(
                (
                    "Duplicate migration ID: "
                    f"{descriptor.migration_id}"
                )
            )

        edge = (
            descriptor.from_version,
            descriptor.to_version,
        )

        if edge in edges:
            raise SchemaValidationError(
                (
                    "Duplicate migration edge: "
                    f"{edge[0]}->{edge[1]}"
                )
            )

        identifiers.add(
            descriptor.migration_id
        )

        edges.add(
            edge
        )

    return tuple(
        descriptors
    )


def migration_graph(
    descriptors: Iterable[
        MigrationDescriptor
    ],
) -> dict[
    str,
    tuple[
        MigrationDescriptor,
        ...,
    ]
]:
    adjacency: dict[
        str,
        list[
            MigrationDescriptor
        ],
    ] = {}

    for descriptor in descriptors:
        adjacency.setdefault(
            descriptor.from_version,
            [],
        ).append(
            descriptor
        )

    return {
        version: tuple(
            sorted(
                values,
                key=lambda value: (
                    version_tuple(
                        value.to_version
                    ),
                    value.migration_id,
                ),
            )
        )
        for version, values
        in sorted(
            adjacency.items()
        )
    }


def resolve_migration_path(
    descriptors: Iterable[
        MigrationDescriptor
    ],
    *,
    from_version: str,
    to_version: str,
) -> tuple[
    MigrationDescriptor,
    ...,
]:
    source = normalize_version(
        from_version
    )

    target = normalize_version(
        to_version
    )

    if source == target:
        return ()

    adjacency = migration_graph(
        descriptors
    )

    queue: list[
        tuple[
            str,
            tuple[
                MigrationDescriptor,
                ...,
            ],
        ]
    ] = [
        (
            source,
            (),
        )
    ]

    visited = {
        source
    }

    while queue:
        current, path = queue.pop(
            0
        )

        for descriptor in adjacency.get(
            current,
            (),
        ):
            next_version = (
                descriptor.to_version
            )

            next_path = (
                *path,
                descriptor,
            )

            if next_version == target:
                return next_path

            if next_version in visited:
                continue

            visited.add(
                next_version
            )

            queue.append(
                (
                    next_version,
                    next_path,
                )
            )

    raise MigrationPathError(
        (
            "No migration path exists: "
            f"{source}->{target}"
        )
    )


def invoke_migration(
    descriptor: MigrationDescriptor,
    graph: dict[str, Any],
) -> dict[str, Any]:
    module = import_migration_module(
        descriptor.path
    )

    migrate: MigrationFunction = (
        getattr(
            module,
            "migrate",
        )
    )

    before = json.loads(
        json.dumps(
            graph
        )
    )

    result = migrate(
        json.loads(
            json.dumps(
                graph
            )
        )
    )

    if not isinstance(
        result,
        dict,
    ):
        raise MigrationExecutionError(
            (
                "Migration did not return "
                f"a graph object: "
                f"{descriptor.migration_id}"
            )
        )

    if deterministic_projection(
        graph
    ) != deterministic_projection(
        before
    ):
        raise MigrationExecutionError(
            (
                "Migration mutated its "
                "input graph in place: "
                f"{descriptor.migration_id}"
            )
        )

    result[
        "schema_version"
    ] = descriptor.to_version

    validate_graph(
        result,
        expected_version=(
            descriptor.to_version
        ),
    )

    return result


def build_registry(
    descriptors: Iterable[
        MigrationDescriptor
    ],
) -> dict[str, Any]:
    migrations = [
        {
            "id": (
                descriptor.migration_id
            ),
            "from_version": (
                descriptor.from_version
            ),
            "to_version": (
                descriptor.to_version
            ),
            "path": relative_path(
                descriptor.path
            ),
            "description": (
                descriptor.description
            ),
            "reversible": (
                descriptor.reversible
            ),
            "sha256": (
                descriptor.module_digest
            ),
        }
        for descriptor in sorted(
            descriptors,
            key=lambda value: (
                version_tuple(
                    value.from_version
                ),
                version_tuple(
                    value.to_version
                ),
                value.migration_id,
            ),
        )
    ]

    registry = {
        "schema": (
            "savant://niche/masterplan/"
            "schema-registry/1.0.0"
        ),
        "registry_version": (
            "1.0.0"
        ),
        "current_schema_version": (
            CURRENT_SCHEMA_VERSION
        ),
        "migrations": migrations,
    }

    registry[
        "semantic_digest"
    ] = semantic_digest(
        registry
    )

    return registry


def backup_graph(
    transaction_id: str,
) -> Path:
    destination = (
        BACKUP_ROOT
        / transaction_id
        / "masterplan.json"
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        GRAPH_PATH,
        destination,
    )

    if (
        sha256_path(
            GRAPH_PATH
        )
        != sha256_path(
            destination
        )
    ):
        raise MigrationExecutionError(
            "Schema migration backup hash mismatch."
        )

    return destination


def restore_graph(
    backup: Path,
) -> dict[str, Any]:
    shutil.copy2(
        backup,
        GRAPH_PATH,
    )

    expected = sha256_path(
        backup
    )

    actual = sha256_path(
        GRAPH_PATH
    )

    return {
        "passed": (
            expected
            == actual
        ),
        "backup": relative_path(
            backup
        ),
        "graph": relative_path(
            GRAPH_PATH
        ),
        "expected_sha256": (
            expected
        ),
        "actual_sha256": (
            actual
        ),
    }


def migrate_graph(
    *,
    target_version: str,
    apply: bool,
    owner: str,
) -> dict[str, Any]:
    if not GRAPH_PATH.is_file():
        raise FileNotFoundError(
            GRAPH_PATH
        )

    descriptors = discover_migrations()

    graph_before = load_json(
        GRAPH_PATH
    )

    validation_before = validate_graph(
        graph_before
    )

    source_version = validation_before[
        "schema_version"
    ]

    target = normalize_version(
        target_version
    )

    path = resolve_migration_path(
        descriptors,
        from_version=(
            source_version
        ),
        to_version=target,
    )

    graph_after = json.loads(
        json.dumps(
            graph_before
        )
    )

    steps: list[
        dict[str, Any]
    ] = []

    for descriptor in path:
        step_before_digest = (
            semantic_digest(
                graph_after
            )
        )

        migrated = invoke_migration(
            descriptor,
            graph_after,
        )

        step_after_digest = (
            semantic_digest(
                migrated
            )
        )

        steps.append(
            {
                "migration_id": (
                    descriptor.migration_id
                ),
                "from_version": (
                    descriptor.from_version
                ),
                "to_version": (
                    descriptor.to_version
                ),
                "path": relative_path(
                    descriptor.path
                ),
                "module_sha256": (
                    descriptor.module_digest
                ),
                "graph_digest_before": (
                    step_before_digest
                ),
                "graph_digest_after": (
                    step_after_digest
                ),
            }
        )

        graph_after = migrated

    validation_after = validate_graph(
        graph_after,
        expected_version=target,
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "schema-migration/1.0.0"
        ),
        "operation": (
            "migrate_masterplan_schema"
        ),
        "generated_at": utc_now(),
        "passed": True,
        "applied": False,
        "owner": owner,
        "source_version": (
            source_version
        ),
        "target_version": (
            target
        ),
        "graph_digest_before": (
            validation_before[
                "graph_digest"
            ]
        ),
        "graph_digest_after": (
            validation_after[
                "graph_digest"
            ]
        ),
        "steps": steps,
        "backup": None,
        "snapshot": None,
        "rollback": None,
    }

    if not apply:
        result[
            "semantic_digest"
        ] = semantic_digest(
            result
        )

        return result

    expected_digest = graph_digest(
        GRAPH_PATH
    )

    transaction_id = (
        f"{timestamp()}__"
        f"{semantic_digest(result)[:16]}"
    )

    transaction_root = (
        TRANSACTION_ROOT
        / transaction_id
    )

    transaction_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    backup: Path | None = None
    rollback: (
        dict[str, Any]
        | None
    ) = None

    lock = MasterplanLock(
        owner=owner,
        operation=(
            "masterplan.schema.migrate"
        ),
        expected_graph_digest=(
            expected_digest
        ),
        timeout_seconds=30.0,
        lease_seconds=300,
    )

    lock.acquire()

    try:
        lock.validate_graph_precondition()

        backup = backup_graph(
            transaction_id
        )

        atomic_write_json(
            transaction_root
            / "graph-before.json",
            graph_before,
        )

        atomic_write_json(
            transaction_root
            / "graph-proposed.json",
            graph_after,
        )

        atomic_write_json(
            transaction_root
            / "migration-plan.json",
            result,
        )

        atomic_write_json(
            GRAPH_PATH,
            graph_after,
        )

        written = load_json(
            GRAPH_PATH
        )

        written_validation = (
            validate_graph(
                written,
                expected_version=target,
            )
        )

        if (
            written_validation[
                "graph_digest"
            ]
            != validation_after[
                "graph_digest"
            ]
        ):
            raise MigrationExecutionError(
                (
                    "Written graph digest "
                    "does not match migration result."
                )
            )

        SNAPSHOT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        snapshot = (
            SNAPSHOT_ROOT
            / (
                f"{transaction_id}__"
                "masterplan.json"
            )
        )

        atomic_write_json(
            snapshot,
            written,
        )

        result[
            "applied"
        ] = True

        result[
            "backup"
        ] = relative_path(
            backup
        )

        result[
            "snapshot"
        ] = relative_path(
            snapshot
        )

        result[
            "transaction"
        ] = {
            "id": transaction_id,
            "root": relative_path(
                transaction_root
            ),
        }

        result[
            "semantic_digest"
        ] = semantic_digest(
            result
        )

        atomic_write_json(
            transaction_root
            / "result.json",
            result,
        )

        lock.release(
            passed=True,
            post_graph_digest=(
                graph_digest(
                    GRAPH_PATH
                )
            ),
        )

    except Exception:
        if backup is not None:
            rollback = restore_graph(
                backup
            )

        result[
            "passed"
        ] = False

        result[
            "rollback"
        ] = rollback

        lock.release(
            passed=False,
            post_graph_digest=(
                graph_digest(
                    GRAPH_PATH
                )
                if GRAPH_PATH.is_file()
                else None
            ),
            failure_code=(
                "masterplan.schema."
                "migration_failed"
            ),
        )

        raise

    return result


def persist_report(
    result: dict[str, Any],
) -> dict[str, str]:
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    historical = (
        REPORT_ROOT
        / f"{run_id}__schema.json"
    )

    latest = (
        REPORT_ROOT
        / "latest.json"
    )

    atomic_write_json(
        historical,
        result,
    )

    atomic_write_json(
        latest,
        result,
    )

    return {
        "historical": relative_path(
            historical
        ),
        "latest": relative_path(
            latest
        ),
    }


def command_status() -> dict[str, Any]:
    descriptors = discover_migrations()

    registry = build_registry(
        descriptors
    )

    atomic_write_json(
        REGISTRY_PATH,
        registry,
    )

    graph = load_json(
        GRAPH_PATH
    )

    validation = validate_graph(
        graph
    )

    return {
        "operation": (
            "masterplan_schema_status"
        ),
        "passed": True,
        "generated_at": utc_now(),
        "graph": validation,
        "registry": {
            "path": relative_path(
                REGISTRY_PATH
            ),
            "semantic_digest": (
                registry[
                    "semantic_digest"
                ]
            ),
            "migration_count": len(
                descriptors
            ),
            "current_schema_version": (
                CURRENT_SCHEMA_VERSION
            ),
        },
    }


def command_validate() -> dict[str, Any]:
    graph = load_json(
        GRAPH_PATH
    )

    validation = validate_graph(
        graph
    )

    return {
        "operation": (
            "validate_masterplan_schema"
        ),
        "passed": True,
        "generated_at": utc_now(),
        "validation": validation,
    }


def command_registry() -> dict[str, Any]:
    descriptors = discover_migrations()

    registry = build_registry(
        descriptors
    )

    atomic_write_json(
        REGISTRY_PATH,
        registry,
    )

    return {
        "operation": (
            "build_masterplan_schema_registry"
        ),
        "passed": True,
        "generated_at": utc_now(),
        "registry": {
            "path": relative_path(
                REGISTRY_PATH
            ),
            "migration_count": len(
                descriptors
            ),
            "semantic_digest": (
                registry[
                    "semantic_digest"
                ]
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate, register, plan, and apply "
            "versioned Masterplan schema migrations."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "status"
    )

    subparsers.add_parser(
        "validate"
    )

    subparsers.add_parser(
        "registry"
    )

    plan_parser = subparsers.add_parser(
        "plan"
    )

    plan_parser.add_argument(
        "target_version",
    )

    plan_parser.add_argument(
        "--owner",
        default="project-owner",
    )

    apply_parser = subparsers.add_parser(
        "apply"
    )

    apply_parser.add_argument(
        "target_version",
    )

    apply_parser.add_argument(
        "--owner",
        default="project-owner",
    )

    arguments = parser.parse_args()

    try:
        if arguments.command == "status":
            result = command_status()

        elif arguments.command == "validate":
            result = command_validate()

        elif arguments.command == "registry":
            result = command_registry()

        elif arguments.command == "plan":
            result = migrate_graph(
                target_version=(
                    arguments.target_version
                ),
                apply=False,
                owner=arguments.owner,
            )

        elif arguments.command == "apply":
            result = migrate_graph(
                target_version=(
                    arguments.target_version
                ),
                apply=True,
                owner=arguments.owner,
            )

        else:
            return 2

        reports = persist_report(
            result
        )

        result[
            "reports"
        ] = reports

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "masterplan_schema_registry"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result.get(
            "passed"
        )
        is True
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
