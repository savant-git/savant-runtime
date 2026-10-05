#!/usr/bin/env python3

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .source_datrix import (
    current_from_datrix,
    datrix,
    deletion_record,
    relative_path,
    stable_id,
    utc_now,
    walk_source_paths,
    write_projection,
)


schema = "savant.carbon.straub.source-datrix-stream.v1"
authority_effect = "none"


def hash_file(
    path: Path,
    *,
    chunk_bytes: int = 1024 * 1024,
) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                chunk_bytes
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

            size += len(
                chunk
            )

    return (
        digest.hexdigest(),
        size,
    )


def observation_metadata(
    path: Path,
) -> dict[str, Any]:
    stat_result = path.stat()

    digest, size = hash_file(
        path
    )

    return {
        "path":
            relative_path(
                path
            ),
        "sha256":
            digest,
        "size":
            size,
        "mtime_ns":
            stat_result.st_mtime_ns,
        "mode":
            (
                stat_result.st_mode
                & 0o7777
            ),
    }


def revision_record(
    observation: dict[str, Any],
    *,
    predecessor: str | None,
    event: str,
) -> dict[str, Any]:
    path = str(
        observation[
            "path"
        ]
    )

    digest = str(
        observation[
            "sha256"
        ]
    )

    revision_id = stable_id(
        "source-revision",
        path,
        digest,
    )

    return {
        "id":
            revision_id,
        "kind":
            "source.revision",
        "status":
            "active",
        "authority":
            {
                "authority_effect":
                    "none",
                "filesystem_presence_establishes_authority":
                    False,
                "semantic_authority":
                    None,
            },
        "payload":
            {
                "path":
                    path,
                "sha256":
                    digest,
                "size":
                    observation[
                        "size"
                    ],
                "mtime_ns":
                    observation[
                        "mtime_ns"
                    ],
                "mode":
                    observation[
                        "mode"
                    ],
                "content_embedded":
                    False,
            },
        "metadata":
            {
                "schema":
                    schema,
                "owner":
                    "carbon",
                "module":
                    "straub",
                "source_kind":
                    "regular_file",
                "projection_only":
                    False,
                "content_storage":
                    "external-source",
                "bounded_memory_observation":
                    True,
            },
        "dependencies":
            (
                [predecessor]
                if predecessor
                else []
            ),
        "relationships":
            [],
        "provenance":
            {
                "source":
                    "/root/savant-runtime",
                "path":
                    path,
                "observed_at":
                    utc_now(),
                "observer":
                    "straub.source-datrix-stream",
            },
        "lineage":
            {
                "predecessor":
                    predecessor,
                "event":
                    event,
            },
    }


def reconcile_streaming() -> dict[str, Any]:
    source = datrix()

    current = current_from_datrix(
        source
    )

    remaining = set(
        current
    )

    created = 0
    modified = 0
    unchanged = 0
    deleted = 0
    observed = 0
    source_bytes = 0

    for path in walk_source_paths():
        try:
            item = observation_metadata(
                path
            )

        except (
            FileNotFoundError,
            PermissionError,
            OSError,
        ):
            continue

        relative = str(
            item[
                "path"
            ]
        )

        observed += 1

        source_bytes += int(
            item[
                "size"
            ]
        )

        remaining.discard(
            relative
        )

        existing = current.get(
            relative
        )

        predecessor = (
            str(
                existing[
                    "id"
                ]
            )
            if existing
            else None
        )

        previous_digest = None

        if existing:
            payload = existing.get(
                "payload"
            )

            if isinstance(
                payload,
                dict,
            ):
                previous_digest = (
                    payload.get(
                        "sha256"
                    )
                )

        if (
            previous_digest
            == item[
                "sha256"
            ]
        ):
            unchanged += 1
            continue

        event = (
            "create"
            if existing is None
            else "modify"
        )

        source.registry.substantiate(
            revision_record(
                item,
                predecessor=predecessor,
                event=event,
            )
        )

        if event == "create":
            created += 1
        else:
            modified += 1

    for path in sorted(
        remaining
    ):
        existing = current[
            path
        ]

        source.registry.substantiate(
            deletion_record(
                path,
                predecessor=str(
                    existing[
                        "id"
                    ]
                ),
            )
        )

        deleted += 1

    changed = (
        created
        + modified
        + deleted
    )

    if changed:
        source.checkpoint()

    projection = write_projection(
        source
    )

    return {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "bounded_memory_observation":
            True,
        "source_content_embedded":
            False,
        "observed_files":
            observed,
        "observed_source_bytes":
            source_bytes,
        "created":
            created,
        "modified":
            modified,
        "unchanged":
            unchanged,
        "deleted":
            deleted,
        "current_files":
            projection.get(
                "file_count"
            ),
        "current_source_bytes":
            projection.get(
                "source_bytes"
            ),
    }


def main() -> int:
    result = reconcile_streaming()

    import json

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
