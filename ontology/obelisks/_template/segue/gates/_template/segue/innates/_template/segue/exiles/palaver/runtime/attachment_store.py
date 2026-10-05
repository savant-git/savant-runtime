#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import tempfile

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from attachment_limits import (
    max_attachment_bytes,
    max_attachment_mib,
    validate_attachment_size,
)


schema = "savant.palaver.attachment-store.v1"
owner = "palaver"

runtime_root = Path("/root/savant-runtime")

attachment_root = (
    runtime_root
    / "vault"
    / "palaver"
    / "attachments"
)

blob_root = attachment_root / "blobs"
record_root = attachment_root / "records"


def now() -> str:
    return datetime.now(
        UTC
    ).isoformat()


def safe_filename(
    value: Any,
) -> str:
    raw = str(
        value
        or "attachment"
    ).strip()

    name = Path(
        raw
    ).name

    name = re.sub(
        r"[^a-zA-Z0-9._-]+",
        "_",
        name,
    ).strip(
        "._"
    )

    return (
        name[:240]
        or "attachment"
    )


def normalize_content_type(
    filename: str,
    supplied: Any = None,
) -> str:
    supplied_text = str(
        supplied
        or ""
    ).strip()

    if supplied_text:
        return supplied_text

    guessed, _ = mimetypes.guess_type(
        filename
    )

    return (
        guessed
        or "application/octet-stream"
    )


def digest_bytes(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def attachment_id(
    digest: str,
) -> str:
    return (
        "attachment_"
        + digest[:24]
    )


def metadata_path(
    identifier: str,
) -> Path:
    return (
        record_root
        / f"{identifier}.json"
    )


def blob_path(
    digest: str,
) -> Path:
    return (
        blob_root
        / digest[:2]
        / digest
    )


def ensure_roots() -> None:
    blob_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    record_root.mkdir(
        parents=True,
        exist_ok=True,
    )


def atomic_write_bytes(
    target: Path,
    data: bytes,
) -> None:
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temp_name = tempfile.mkstemp(
        prefix=".palaver-attachment-",
        dir=str(
            target.parent
        ),
    )

    temp = Path(
        temp_name
    )

    try:
        with os.fdopen(
            fd,
            "wb",
        ) as handle:
            handle.write(
                data
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temp,
            target,
        )

    finally:
        try:
            temp.unlink(
                missing_ok=True
            )

        except Exception:
            pass


def atomic_write_json(
    target: Path,
    value: dict[str, Any],
) -> None:
    encoded = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    atomic_write_bytes(
        target,
        encoded,
    )


def store_attachment(
    *,
    filename: Any,
    data: bytes,
    content_type: Any = None,
    source: str = "palaver",
) -> dict[str, Any]:
    if not isinstance(
        data,
        bytes,
    ):
        raise TypeError(
            "attachment data must be bytes"
        )

    size = validate_attachment_size(
        len(
            data
        )
    )

    normalized_name = safe_filename(
        filename
    )

    normalized_type = normalize_content_type(
        normalized_name,
        content_type,
    )

    digest = digest_bytes(
        data
    )

    identifier = attachment_id(
        digest
    )

    ensure_roots()

    stored_blob = blob_path(
        digest
    )

    if not stored_blob.exists():
        atomic_write_bytes(
            stored_blob,
            data,
        )

    existing_record = metadata_path(
        identifier
    )

    created_at = now()

    if existing_record.exists():
        try:
            previous = json.loads(
                existing_record.read_text(
                    encoding="utf-8"
                )
            )

            created_at = str(
                previous.get(
                    "created_at"
                )
                or created_at
            )

        except Exception:
            pass

    record = {
        "schema": schema,
        "owner": owner,
        "attachment_id": identifier,
        "filename": normalized_name,
        "content_type": normalized_type,
        "size_bytes": size,
        "sha256": digest,
        "created_at": created_at,
        "observed_at": now(),
        "source": source,
        "storage": {
            "kind": "content_addressed",
            "blob": str(
                stored_blob.relative_to(
                    runtime_root
                )
            ),
        },
        "limits": {
            "max_attachment_bytes": (
                max_attachment_bytes
            ),
            "max_attachment_mib": (
                max_attachment_mib
            ),
        },
        "authority_effect": "none",
    }

    atomic_write_json(
        existing_record,
        record,
    )

    return record


def get_attachment(
    identifier: str,
) -> dict[str, Any]:
    path = metadata_path(
        str(
            identifier
        ).strip()
    )

    if not path.is_file():
        raise FileNotFoundError(
            "attachment record not found"
        )

    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise RuntimeError(
            "invalid attachment record"
        )

    return value


def read_attachment(
    identifier: str,
) -> bytes:
    record = get_attachment(
        identifier
    )

    relative = (
        record.get(
            "storage",
            {}
        ).get(
            "blob"
        )
    )

    if not relative:
        raise RuntimeError(
            "attachment blob reference missing"
        )

    target = (
        runtime_root
        / str(
            relative
        )
    ).resolve()

    allowed = blob_root.resolve()

    try:
        target.relative_to(
            allowed
        )

    except ValueError as exc:
        raise RuntimeError(
            "attachment blob escaped storage root"
        ) from exc

    return target.read_bytes()


def projection() -> dict[str, Any]:
    return {
        "schema": schema,
        "owner": owner,
        "attachment_root": str(
            attachment_root
        ),
        "max_attachment_bytes": (
            max_attachment_bytes
        ),
        "max_attachment_mib": (
            max_attachment_mib
        ),
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            projection(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
