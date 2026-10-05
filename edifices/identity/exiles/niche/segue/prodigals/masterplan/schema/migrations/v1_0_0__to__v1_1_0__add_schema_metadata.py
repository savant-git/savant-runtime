#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any


MIGRATION_ID = (
    "masterplan.schema."
    "1.0.0-to-1.1.0."
    "add-schema-metadata"
)

FROM_VERSION = "1.0.0"
TO_VERSION = "1.1.0"

DESCRIPTION = (
    "Add authoritative schema metadata and "
    "migration lineage without altering existing "
    "task, segue, decision, event, evidence, "
    "receipt, or attestation authority."
)

REVERSIBLE = True


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


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            value
        )
    ).hexdigest()


def migrate(
    graph: dict[str, Any],
) -> dict[str, Any]:
    migrated = json.loads(
        json.dumps(
            graph
        )
    )

    metadata = migrated.setdefault(
        "schema_metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        raise ValueError(
            "Existing schema_metadata is not an object."
        )

    history = metadata.setdefault(
        "migration_history",
        [],
    )

    if not isinstance(
        history,
        list,
    ):
        raise ValueError(
            "Existing migration history is not a list."
        )

    existing_ids = {
        record.get(
            "migration_id"
        )
        for record in history
        if isinstance(
            record,
            dict,
        )
    }

    if MIGRATION_ID not in existing_ids:
        record = {
            "migration_id": (
                MIGRATION_ID
            ),
            "from_version": (
                FROM_VERSION
            ),
            "to_version": (
                TO_VERSION
            ),
            "description": (
                DESCRIPTION
            ),
            "reversible": (
                REVERSIBLE
            ),
        }

        record[
            "semantic_digest"
        ] = digest(
            record
        )

        history.append(
            record
        )

    metadata[
        "registry_schema"
    ] = (
        "savant://niche/masterplan/"
        "schema-registry/1.0.0"
    )

    metadata[
        "migration_policy"
    ] = {
        "requires_plan": True,
        "requires_lock": True,
        "requires_backup": True,
        "requires_snapshot": True,
        "requires_validation": True,
        "requires_digest_parity": True,
        "allows_projection_authority": False,
        "allows_history_deletion": False,
    }

    migrated[
        "schema_version"
    ] = TO_VERSION

    return migrated


def reverse(
    graph: dict[str, Any],
) -> dict[str, Any]:
    reverted = json.loads(
        json.dumps(
            graph
        )
    )

    metadata = reverted.get(
        "schema_metadata"
    )

    if isinstance(
        metadata,
        dict,
    ):
        history = metadata.get(
            "migration_history"
        )

        if isinstance(
            history,
            list,
        ):
            metadata[
                "migration_history"
            ] = [
                record
                for record in history
                if not (
                    isinstance(
                        record,
                        dict,
                    )
                    and record.get(
                        "migration_id"
                    )
                    == MIGRATION_ID
                )
            ]

        if not metadata.get(
            "migration_history"
        ):
            reverted.pop(
                "schema_metadata",
                None,
            )

    reverted[
        "schema_version"
    ] = FROM_VERSION

    return reverted
