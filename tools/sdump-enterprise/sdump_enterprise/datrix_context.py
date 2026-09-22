from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


runtime_root = Path(
    "/root/savant-runtime"
).resolve(
    strict=False
)

runtime_python_root = (
    runtime_root
    / "runtime"
)

if str(
    runtime_python_root
) not in sys.path:
    sys.path.insert(
        0,
        str(
            runtime_python_root
        ),
    )


from straub.source_datrix import (  # noqa: E402
    current_from_datrix,
    datrix,
    datrix_path,
    projection_path,
    status_path,
)


schema = "savant.sdump.datrix-semantic-state.v1"


def sha256_file(
    path: Path,
) -> str | None:
    digest = hashlib.sha256()

    try:
        with path.open(
            "rb"
        ) as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

    except OSError:
        return None

    return digest.hexdigest()


def read_json_evidence(
    path: Path,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        value,
        dict,
    ):
        return None

    return value


def source_datrix_semantic_state() -> dict[str, Any]:
    source = datrix()

    current = current_from_datrix(
        source
    )

    revisions: list[
        dict[str, Any]
    ] = []

    source_bytes = 0

    for path in sorted(
        current
    ):
        item = current[
            path
        ]

        payload = item.get(
            "payload"
        )

        if not isinstance(
            payload,
            dict,
        ):
            continue

        try:
            size = int(
                payload.get(
                    "size",
                    0,
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            size = 0

        source_bytes += size

        revisions.append(
            {
                "path":
                    path,
                "revision_id":
                    item.get(
                        "id"
                    ),
                "kind":
                    item.get(
                        "kind"
                    ),
                "sha256":
                    payload.get(
                        "sha256"
                    ),
                "size":
                    size,
                "mtime_ns":
                    payload.get(
                        "mtime_ns"
                    ),
                "mode":
                    payload.get(
                        "mode"
                    ),
                "encoding":
                    payload.get(
                        "encoding"
                    ),
                "observed_at":
                    item.get(
                        "observed_at"
                    ),
            }
        )

    health = source.health()

    status = read_json_evidence(
        status_path
    )

    projection = read_json_evidence(
        projection_path
    )

    projection_summary = None

    if projection is not None:
        projection_summary = {
            "schema":
                projection.get(
                    "schema"
                ),
            "authority_effect":
                projection.get(
                    "authority_effect"
                ),
            "projection_only":
                projection.get(
                    "projection_only"
                ),
            "filesystem_presence_establishes_authority":
                projection.get(
                    "filesystem_presence_establishes_authority"
                ),
            "source_datrix":
                projection.get(
                    "source_datrix"
                ),
            "root":
                projection.get(
                    "root"
                ),
            "generated_at":
                projection.get(
                    "generated_at"
                ),
            "file_count":
                projection.get(
                    "file_count"
                ),
            "source_bytes":
                projection.get(
                    "source_bytes"
                ),
            "sha256":
                sha256_file(
                    projection_path
                ),
        }

    status_summary = None

    if status is not None:
        status_summary = {
            "schema":
                status.get(
                    "schema"
                ),
            "authority_effect":
                status.get(
                    "authority_effect"
                ),
            "state":
                status.get(
                    "state"
                ),
            "root":
                status.get(
                    "root"
                ),
            "datrix":
                status.get(
                    "datrix"
                ),
            "projection":
                status.get(
                    "projection"
                ),
            "poll_seconds":
                status.get(
                    "poll_seconds"
                ),
            "updated_at":
                status.get(
                    "updated_at"
                ),
            "reconciliation":
                status.get(
                    "reconciliation"
                ),
            "error":
                status.get(
                    "error"
                ),
            "sha256":
                sha256_file(
                    status_path
                ),
        }

    return {
        "schema":
            schema,
        "projection_only":
            True,
        "authority_effect":
            "none",
        "semantic_source":
            "straub-source-datrix",
        "semantic_source_is_sqlite":
            False,
        "filesystem_presence_establishes_authority":
            False,
        "source_datrix": {
            "path":
                str(
                    datrix_path
                ),
            "sha256":
                sha256_file(
                    datrix_path
                ),
            "health":
                health,
        },
        "current_revision_count":
            len(
                revisions
            ),
        "current_source_bytes":
            source_bytes,
        "current_revisions":
            revisions,
        "materialized_projection":
            projection_summary,
        "maintenance_status":
            status_summary,
        "source_content_duplicated":
            False,
        "sqlite_consulted":
            False,
    }
