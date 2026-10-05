#!/usr/bin/env python3

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any

from attachment_store import (
    get_attachment,
    read_attachment,
)


schema = "savant.palaver.attachment-context.v1"
owner = "palaver"

max_text_bytes = 4_194_304
max_text_chars = 1_000_000

text_extensions = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".csv",
    ".tsv",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".py",
    ".pyi",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".rb",
    ".php",
    ".java",
    ".kt",
    ".kts",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".cs",
    ".swift",
    ".sql",
    ".graphql",
    ".gql",
    ".proto",
    ".dockerfile",
    ".env",
    ".log",
}

text_mime_prefixes = (
    "text/",
)

text_mime_types = {
    "application/json",
    "application/ld+json",
    "application/xml",
    "application/javascript",
    "application/x-javascript",
    "application/yaml",
    "application/x-yaml",
    "application/toml",
    "application/sql",
}


def normalize_identifier(
    value: Any,
) -> str:
    if isinstance(
        value,
        dict,
    ):
        value = (
            value.get(
                "attachment_id"
            )
            or value.get(
                "id"
            )
            or ""
        )

    return str(
        value
        or ""
    ).strip()


def is_text_attachment(
    record: dict[str, Any],
) -> bool:
    content_type = str(
        record.get(
            "content_type"
        )
        or ""
    ).lower()

    filename = str(
        record.get(
            "filename"
        )
        or ""
    )

    suffix = Path(
        filename
    ).suffix.lower()

    if content_type.startswith(
        text_mime_prefixes
    ):
        return True

    if content_type in text_mime_types:
        return True

    return (
        suffix
        in text_extensions
    )


def decode_text(
    data: bytes,
) -> tuple[str, str]:
    candidates = (
        "utf-8",
        "utf-8-sig",
        "utf-16",
        "latin-1",
    )

    for encoding in candidates:
        try:
            return (
                data.decode(
                    encoding
                ),
                encoding,
            )

        except UnicodeDecodeError:
            continue

    return (
        data.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replacement",
    )


def normalize_text(
    text: str,
) -> str:
    text = text.replace(
        "\x00",
        ""
    )

    text = re.sub(
        r"\r\n?",
        "\n",
        text,
    )

    return text[
        :max_text_chars
    ]


def project_attachment(
    value: Any,
) -> dict[str, Any]:
    identifier = normalize_identifier(
        value
    )

    if not identifier:
        return {
            "ok": False,
            "error": "attachment id missing",
        }

    try:
        record = get_attachment(
            identifier
        )

    except Exception as exc:
        return {
            "ok": False,
            "attachment_id": identifier,
            "error": str(
                exc
            ),
        }

    projection = {
        "ok": True,
        "attachment_id": (
            record.get(
                "attachment_id"
            )
        ),
        "filename": (
            record.get(
                "filename"
            )
        ),
        "content_type": (
            record.get(
                "content_type"
            )
        ),
        "size_bytes": (
            record.get(
                "size_bytes"
            )
        ),
        "sha256": (
            record.get(
                "sha256"
            )
        ),
        "source": (
            record.get(
                "source"
            )
        ),
        "text_available": False,
    }

    if not is_text_attachment(
        record
    ):
        projection[
            "reason"
        ] = (
            "binary attachment retained by palaver; "
            "text projection unavailable"
        )

        return projection

    try:
        raw = read_attachment(
            identifier
        )

        raw = raw[
            :max_text_bytes
        ]

        text, encoding = decode_text(
            raw
        )

        text = normalize_text(
            text
        )

        projection.update(
            {
                "text_available": True,
                "encoding": encoding,
                "text": text,
                "text_truncated": (
                    int(
                        record.get(
                            "size_bytes"
                        )
                        or 0
                    )
                    > max_text_bytes
                    or len(
                        text
                    )
                    >= max_text_chars
                ),
            }
        )

    except Exception as exc:
        projection[
            "text_error"
        ] = str(
            exc
        )

    return projection


def build_attachment_context(
    attachments: Any,
) -> dict[str, Any]:
    if not isinstance(
        attachments,
        list,
    ):
        attachments = []

    projections = [
        project_attachment(
            item
        )
        for item
        in attachments
    ]

    readable = [
        item
        for item
        in projections
        if item.get(
            "text_available"
        )
    ]

    blocks = []

    for item in readable:
        blocks.append(
            "\n".join(
                [
                    (
                        "attachment: "
                        + str(
                            item.get(
                                "filename"
                            )
                            or item.get(
                                "attachment_id"
                            )
                        )
                    ),
                    (
                        "attachment_id: "
                        + str(
                            item.get(
                                "attachment_id"
                            )
                        )
                    ),
                    (
                        "sha256: "
                        + str(
                            item.get(
                                "sha256"
                            )
                        )
                    ),
                    (
                        "content_type: "
                        + str(
                            item.get(
                                "content_type"
                            )
                        )
                    ),
                    "content:",
                    str(
                        item.get(
                            "text"
                        )
                        or ""
                    ),
                ]
            )
        )

    return {
        "schema": schema,
        "owner": owner,
        "count": len(
            projections
        ),
        "text_count": len(
            readable
        ),
        "attachments": projections,
        "context": (
            "\n\n---\n\n".join(
                blocks
            )
        ),
        "authority_effect": "none",
    }


def merge_context(
    context: Any,
    attachments: Any,
) -> tuple[str, dict[str, Any]]:
    existing = str(
        context
        or ""
    ).strip()

    projection = (
        build_attachment_context(
            attachments
        )
    )

    derived = str(
        projection.get(
            "context"
        )
        or ""
    ).strip()

    parts = [
        value
        for value
        in (
            existing,
            derived,
        )
        if value
    ]

    return (
        "\n\n".join(
            parts
        ),
        projection,
    )


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "schema": schema,
                "owner": owner,
                "max_text_bytes": (
                    max_text_bytes
                ),
                "max_text_chars": (
                    max_text_chars
                ),
                "authority_effect": "none",
            },
            indent=2,
            sort_keys=True,
        )
    )
