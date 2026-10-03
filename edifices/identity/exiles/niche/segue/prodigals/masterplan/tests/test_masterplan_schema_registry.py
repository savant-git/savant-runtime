#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest


SUBJECT_ROOT = Path(
    "/root/savant-runtime/edifices/"
    "identity/exiles/niche/prodigals/"
    "masterplan"
)

SCHEMA_ROOT = (
    SUBJECT_ROOT
    / "schema"
)

if str(SCHEMA_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(
            SCHEMA_ROOT
        ),
    )


from masterplan_schema_registry import (  # noqa: E402
    MigrationDescriptor,
    MigrationPathError,
    SchemaValidationError,
    build_registry,
    resolve_migration_path,
    semantic_digest,
    validate_graph,
)


def authority() -> dict:
    return {
        "state": "authoritative",
        "authority_class": (
            "project-owner-directed"
        ),
        "tier": 0,
        "source": "test",
        "accepted_by": "project-owner",
        "accepted_at": (
            "2026-08-01T00:00:00+00:00"
        ),
        "confidence": 1.0,
    }


def graph() -> dict:
    return {
        "schema_version": "1.0.0",
        "graph_id": "savant.masterplan",
        "authority": authority(),
        "records": [
            {
                "id": "SAV-P0-001",
                "title": "Test",
                "status": "active",
                "authority": authority(),
            }
        ],
        "segues": [],
        "events": [],
        "decisions": [],
        "evidence": [],
        "receipts": [],
        "attestations": [],
    }


def descriptor(
    migration_id: str,
    source: str,
    target: str,
) -> MigrationDescriptor:
    return MigrationDescriptor(
        migration_id=migration_id,
        from_version=source,
        to_version=target,
        path=Path(
            f"/tmp/{migration_id}.py"
        ),
        description="test",
        reversible=False,
        module_digest=(
            "0" * 64
        ),
    )


def test_valid_graph_passes() -> None:
    result = validate_graph(
        graph()
    )

    assert result[
        "passed"
    ] is True

    assert result[
        "schema_version"
    ] == "1.0.0"


def test_missing_collection_fails() -> None:
    value = graph()

    value.pop(
        "evidence"
    )

    with pytest.raises(
        SchemaValidationError
    ):
        validate_graph(
            value
        )


def test_duplicate_task_identity_fails() -> None:
    value = graph()

    value[
        "records"
    ].append(
        copy.deepcopy(
            value[
                "records"
            ][0]
        )
    )

    with pytest.raises(
        SchemaValidationError
    ):
        validate_graph(
            value
        )


def test_unknown_segue_reference_fails() -> None:
    value = graph()

    value[
        "segues"
    ].append(
        {
            "id": "segue-test",
            "source": "SAV-P0-001",
            "target": "SAV-UNKNOWN",
            "type": "depends_on",
        }
    )

    with pytest.raises(
        SchemaValidationError
    ):
        validate_graph(
            value
        )


def test_equal_graphs_have_equal_semantic_digest() -> None:
    first = graph()

    second = copy.deepcopy(
        first
    )

    assert semantic_digest(
        first
    ) == semantic_digest(
        second
    )


def test_migration_path_resolves_in_order() -> None:
    migrations = (
        descriptor(
            "one",
            "1.0.0",
            "1.1.0",
        ),
        descriptor(
            "two",
            "1.1.0",
            "2.0.0",
        ),
    )

    path = resolve_migration_path(
        migrations,
        from_version="1.0.0",
        to_version="2.0.0",
    )

    assert [
        item.migration_id
        for item in path
    ] == [
        "one",
        "two",
    ]


def test_missing_migration_path_fails() -> None:
    migrations = (
        descriptor(
            "one",
            "1.0.0",
            "1.1.0",
        ),
    )

    with pytest.raises(
        MigrationPathError
    ):
        resolve_migration_path(
            migrations,
            from_version="1.0.0",
            to_version="2.0.0",
        )


def test_registry_is_deterministic() -> None:
    migrations = (
        descriptor(
            "two",
            "1.1.0",
            "2.0.0",
        ),
        descriptor(
            "one",
            "1.0.0",
            "1.1.0",
        ),
    )

    first = build_registry(
        migrations
    )

    second = build_registry(
        reversed(
            migrations
        )
    )

    assert first[
        "semantic_digest"
    ] == second[
        "semantic_digest"
    ]
