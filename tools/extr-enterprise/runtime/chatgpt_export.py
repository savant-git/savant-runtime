#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping
import zipfile


schema = "savant://runtime/sieve/chatgpt-export/1.0.0"
owner = "sieve"
authority_effect = "none"


class chatgpt_export_error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        prefix
        + ":"
        + sha256_bytes(
            canonical_json(
                value
            ).encode(
                "utf-8"
            )
        )
    )


def finite_number(
    value: Any,
) -> float | None:
    if isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        number = float(
            value
        )

        if math.isfinite(
            number
        ):
            return number

    return None


def source_payload(
    path: Path,
) -> tuple[
    bytes,
    str,
]:
    path = path.resolve()

    if not path.is_file():
        raise chatgpt_export_error(
            f"not a file: {path}"
        )

    raw = path.read_bytes()
    lower = (
        path.name.casefold()
    )

    if lower.endswith(
        ".zip"
    ):
        with zipfile.ZipFile(
            io.BytesIO(
                raw
            )
        ) as archive:
            candidates = [
                name
                for name
                in archive.namelist()
                if (
                    not name.endswith(
                        "/"
                    )
                    and Path(
                        name
                    ).name.casefold()
                    == "conversations.json"
                )
            ]

            if (
                len(
                    candidates
                )
                != 1
            ):
                raise chatgpt_export_error(
                    "ChatGPT export zip must "
                    "contain exactly one "
                    "conversations.json; "
                    f"found {len(candidates)}"
                )

            return (
                archive.read(
                    candidates[0]
                ),
                candidates[0],
            )

    return (
        raw,
        path.name,
    )


def load_conversations(
    path: Path,
) -> tuple[
    list[
        Mapping[
            str,
            Any,
        ]
    ],
    dict[
        str,
        Any,
    ],
]:
    payload, member = (
        source_payload(
            path
        )
    )

    try:
        value = json.loads(
            payload.decode(
                "utf-8-sig"
            )
        )

    except Exception as exc:
        raise chatgpt_export_error(
            "unable to parse ChatGPT "
            "conversations JSON"
        ) from exc

    if not isinstance(
        value,
        list,
    ):
        raise chatgpt_export_error(
            "ChatGPT conversations "
            "payload must be a list"
        )

    conversations: list[
        Mapping[
            str,
            Any,
        ]
    ] = []

    for index, item in enumerate(
        value
    ):
        if not isinstance(
            item,
            Mapping,
        ):
            raise chatgpt_export_error(
                "conversation entry must "
                "be an object: "
                f"index {index}"
            )

        conversations.append(
            item
        )

    return (
        conversations,
        {
            "input_path":
                str(
                    path.resolve()
                ),
            "input_sha256":
                sha256_bytes(
                    path.read_bytes()
                ),
            "payload_sha256":
                sha256_bytes(
                    payload
                ),
            "payload_member":
                member,
        },
    )


def content_text(
    content: Any,
) -> tuple[
    str,
    str | None,
]:
    if not isinstance(
        content,
        Mapping,
    ):
        return (
            "",
            None,
        )

    content_type = (
        content.get(
            "content_type"
        )
    )

    parts = content.get(
        "parts"
    )

    if not isinstance(
        parts,
        list,
    ):
        return (
            "",
            (
                str(
                    content_type
                )
                if (
                    content_type
                    is not None
                )
                else None
            ),
        )

    rendered: list[str] = []

    for part in parts:
        if isinstance(
            part,
            str,
        ):
            rendered.append(
                part
            )

        elif part is None:
            continue

        else:
            rendered.append(
                canonical_json(
                    part
                )
            )

    return (
        "\n".join(
            rendered
        ),
        (
            str(
                content_type
            )
            if (
                content_type
                is not None
            )
            else None
        ),
    )


def message_author(
    message: Mapping[
        str,
        Any,
    ],
) -> dict[
    str,
    Any,
]:
    author = message.get(
        "author"
    )

    if not isinstance(
        author,
        Mapping,
    ):
        return {
            "role":
                None,
            "name":
                None,
            "metadata":
                {},
        }

    metadata = author.get(
        "metadata"
    )

    return {
        "role":
            author.get(
                "role"
            ),
        "name":
            author.get(
                "name"
            ),
        "metadata":
            (
                dict(
                    metadata
                )
                if isinstance(
                    metadata,
                    Mapping,
                )
                else {}
            ),
    }


def branch_path(
    node_id: str,
    mapping: Mapping[
        str,
        Any,
    ],
) -> tuple[
    list[str],
    list[str],
]:
    path: list[str] = []
    issues: list[str] = []
    seen: set[str] = set()

    current: (
        str
        | None
    ) = node_id

    while (
        current
        is not None
    ):
        if current in seen:
            issues.append(
                "cycle:"
                + current
            )

            break

        seen.add(
            current
        )

        path.append(
            current
        )

        node = mapping.get(
            current
        )

        if not isinstance(
            node,
            Mapping,
        ):
            issues.append(
                "missing-node:"
                + current
            )

            break

        parent = node.get(
            "parent"
        )

        if parent is None:
            current = None

        elif isinstance(
            parent,
            str,
        ):
            current = parent

        else:
            issues.append(
                "invalid-parent:"
                + current
            )

            break

    path.reverse()

    return (
        path,
        issues,
    )


def current_branch_nodes(
    current_node: Any,
    mapping: Mapping[
        str,
        Any,
    ],
) -> tuple[
    set[str],
    list[str],
]:
    if not isinstance(
        current_node,
        str,
    ):
        return (
            set(),
            [],
        )

    path, issues = (
        branch_path(
            current_node,
            mapping,
        )
    )

    return (
        set(
            path
        ),
        issues,
    )


def fence_blocks(
    text: str,
) -> list[
    dict[
        str,
        Any,
    ]
]:
    lines = text.splitlines(
        keepends=True
    )

    blocks: list[
        dict[
            str,
            Any,
        ]
    ] = []

    position = 0
    index = 0

    open_fence: (
        dict[
            str,
            Any,
        ]
        | None
    ) = None

    body_start = 0
    body_parts: list[str] = []

    for line in lines:
        stripped = (
            line.lstrip(
                " "
            )
        )

        indent = (
            len(
                line
            )
            - len(
                stripped
            )
        )

        candidate = (
            stripped.rstrip(
                "\r\n"
            )
        )

        if (
            open_fence
            is None
        ):
            if (
                indent <= 3
                and candidate
            ):
                marker = (
                    candidate[0]
                )

                if marker in {
                    "`",
                    "~",
                }:
                    width = 0

                    while (
                        width
                        < len(
                            candidate
                        )
                        and candidate[
                            width
                        ]
                        == marker
                    ):
                        width += 1

                    if width >= 3:
                        info = (
                            candidate[
                                width:
                            ].strip()
                        )

                        language = (
                            info.split(
                                None,
                                1,
                            )[0]
                            if info
                            else None
                        )

                        open_fence = {
                            "marker":
                                marker,
                            "width":
                                width,
                            "info":
                                info,
                            "language":
                                language,
                            "fence_start":
                                (
                                    position
                                    + indent
                                ),
                            "body_start":
                                (
                                    position
                                    + len(
                                        line
                                    )
                                ),
                        }

                        body_start = (
                            position
                            + len(
                                line
                            )
                        )

                        body_parts = []

        else:
            marker = (
                open_fence[
                    "marker"
                ]
            )

            width = (
                open_fence[
                    "width"
                ]
            )

            if (
                indent <= 3
                and candidate
            ):
                close_width = 0

                while (
                    close_width
                    < len(
                        candidate
                    )
                    and candidate[
                        close_width
                    ]
                    == marker
                ):
                    close_width += 1

                closing_tail = (
                    candidate[
                        close_width:
                    ].strip()
                )

                if (
                    close_width
                    >= width
                    and closing_tail
                    == ""
                ):
                    body = "".join(
                        body_parts
                    )

                    blocks.append(
                        {
                            "index":
                                index,
                            "language":
                                open_fence[
                                    "language"
                                ],
                            "info":
                                open_fence[
                                    "info"
                                ],
                            "marker":
                                marker,
                            "fence_width":
                                width,
                            "closed":
                                True,
                            "fence_start":
                                open_fence[
                                    "fence_start"
                                ],
                            "body_start":
                                body_start,
                            "body_end":
                                position,
                            "fence_end":
                                (
                                    position
                                    + len(
                                        line
                                    )
                                ),
                            "code":
                                body,
                        }
                    )

                    index += 1
                    open_fence = None
                    body_parts = []

                    position += len(
                        line
                    )

                    continue

            body_parts.append(
                line
            )

        position += len(
            line
        )

    if (
        open_fence
        is not None
    ):
        body = "".join(
            body_parts
        )

        blocks.append(
            {
                "index":
                    index,
                "language":
                    open_fence[
                        "language"
                    ],
                "info":
                    open_fence[
                        "info"
                    ],
                "marker":
                    open_fence[
                        "marker"
                    ],
                "fence_width":
                    open_fence[
                        "width"
                    ],
                "closed":
                    False,
                "fence_start":
                    open_fence[
                        "fence_start"
                    ],
                "body_start":
                    body_start,
                "body_end":
                    len(
                        text
                    ),
                "fence_end":
                    len(
                        text
                    ),
                "code":
                    body,
            }
        )

    return blocks


def project_conversation(
    conversation: Mapping[
        str,
        Any,
    ],
    *,
    conversation_index: int,
    source: Mapping[
        str,
        Any,
    ],
) -> tuple[
    list[
        dict[
            str,
            Any,
        ]
    ],
    list[
        dict[
            str,
            Any,
        ]
    ],
    list[str],
]:
    mapping_raw = (
        conversation.get(
            "mapping"
        )
    )

    if not isinstance(
        mapping_raw,
        Mapping,
    ):
        return (
            [],
            [],
            [
                (
                    "conversation:"
                    f"{conversation_index}:"
                    "missing-mapping"
                )
            ],
        )

    mapping = {
        str(
            key
        ):
            value
        for (
            key,
            value,
        )
        in mapping_raw.items()
    }

    conversation_id = str(
        conversation.get(
            "id"
        )
        or stable_id(
            "chatgpt:conversation",
            {
                "source":
                    source[
                        "payload_sha256"
                    ],
                "index":
                    conversation_index,
                "title":
                    conversation.get(
                        "title"
                    ),
            },
        )
    )

    title = conversation.get(
        "title"
    )

    current_node = (
        conversation.get(
            "current_node"
        )
    )

    (
        current_nodes,
        current_issues,
    ) = current_branch_nodes(
        current_node,
        mapping,
    )

    messages: list[
        dict[
            str,
            Any,
        ]
    ] = []

    codes: list[
        dict[
            str,
            Any,
        ]
    ] = []

    issues = list(
        current_issues
    )

    for (
        mapping_index,
        (
            node_id,
            node_raw,
        ),
    ) in enumerate(
        mapping.items()
    ):
        if not isinstance(
            node_raw,
            Mapping,
        ):
            issues.append(
                (
                    "conversation:"
                    f"{conversation_id}:"
                    "invalid-node:"
                    f"{node_id}"
                )
            )

            continue

        message = node_raw.get(
            "message"
        )

        if not isinstance(
            message,
            Mapping,
        ):
            continue

        message_id = str(
            message.get(
                "id"
            )
            or node_id
        )

        (
            path,
            path_issues,
        ) = branch_path(
            node_id,
            mapping,
        )

        issues.extend(
            (
                "conversation:"
                f"{conversation_id}:"
                f"{issue}"
            )
            for issue
            in path_issues
        )

        (
            text,
            content_type,
        ) = content_text(
            message.get(
                "content"
            )
        )

        children_raw = (
            node_raw.get(
                "children"
            )
        )

        children = (
            [
                str(
                    child
                )
                for child
                in children_raw
                if isinstance(
                    child,
                    str,
                )
            ]
            if isinstance(
                children_raw,
                list,
            )
            else []
        )

        parent = node_raw.get(
            "parent"
        )

        parent_node_id = (
            parent
            if isinstance(
                parent,
                str,
            )
            else None
        )

        create_time = (
            finite_number(
                message.get(
                    "create_time"
                )
            )
        )

        update_time = (
            finite_number(
                message.get(
                    "update_time"
                )
            )
        )

        author = (
            message_author(
                message
            )
        )

        message_metadata = (
            message.get(
                "metadata"
            )
        )

        record = {
            "schema":
                (
                    "savant://runtime/sieve/"
                    "chatgpt-message/1.0.0"
                ),
            "id":
                stable_id(
                    "sieve:chatgpt-message",
                    {
                        "source":
                            source[
                                "payload_sha256"
                            ],
                        "conversation_id":
                            conversation_id,
                        "node_id":
                            node_id,
                        "message_id":
                            message_id,
                    },
                ),
            "owner":
                owner,
            "authority_effect":
                authority_effect,
            "authoritative":
                False,
            "source":
                dict(
                    source
                ),
            "conversation":
                {
                    "id":
                        conversation_id,
                    "index":
                        conversation_index,
                    "title":
                        title,
                    "create_time":
                        finite_number(
                            conversation.get(
                                "create_time"
                            )
                        ),
                    "update_time":
                        finite_number(
                            conversation.get(
                                "update_time"
                            )
                        ),
                    "current_node":
                        (
                            current_node
                            if isinstance(
                                current_node,
                                str,
                            )
                            else None
                        ),
                },
            "graph":
                {
                    "node_id":
                        node_id,
                    "parent_node_id":
                        parent_node_id,
                    "children_node_ids":
                        children,
                    "branch_path":
                        path,
                    "depth":
                        max(
                            len(
                                path
                            )
                            - 1,
                            0,
                        ),
                    "mapping_index":
                        mapping_index,
                    "is_current_branch":
                        (
                            node_id
                            in current_nodes
                        ),
                },
            "message":
                {
                    "id":
                        message_id,
                    "author":
                        author,
                    "recipient":
                        message.get(
                            "recipient"
                        ),
                    "create_time":
                        create_time,
                    "update_time":
                        update_time,
                    "status":
                        message.get(
                            "status"
                        ),
                    "end_turn":
                        message.get(
                            "end_turn"
                        ),
                    "weight":
                        message.get(
                            "weight"
                        ),
                    "content_type":
                        content_type,
                    "metadata":
                        (
                            dict(
                                message_metadata
                            )
                            if isinstance(
                                message_metadata,
                                Mapping,
                            )
                            else {}
                        ),
                },
            "text":
                text,
            "lineage":
                {
                    "source_payload_sha256":
                        source[
                            "payload_sha256"
                        ],
                    "conversation_id":
                        conversation_id,
                    "node_id":
                        node_id,
                    "message_id":
                        message_id,
                },
        }

        blocks = fence_blocks(
            text
        )

        record[
            "code_block_count"
        ] = len(
            blocks
        )

        messages.append(
            record
        )

        for block in blocks:
            code_identity = {
                "message_projection_id":
                    record[
                        "id"
                    ],
                "index":
                    block[
                        "index"
                    ],
                "code":
                    block[
                        "code"
                    ],
            }

            codes.append(
                {
                    "schema":
                        (
                            "savant://runtime/sieve/"
                            "chatgpt-code-block/1.0.0"
                        ),
                    "id":
                        stable_id(
                            "sieve:chatgpt-code",
                            code_identity,
                        ),
                    "owner":
                        owner,
                    "authority_effect":
                        authority_effect,
                    "authoritative":
                        False,
                    "source":
                        dict(
                            source
                        ),
                    "conversation_id":
                        conversation_id,
                    "message_projection_id":
                        record[
                            "id"
                        ],
                    "message_id":
                        message_id,
                    "node_id":
                        node_id,
                    "author_role":
                        author.get(
                            "role"
                        ),
                    "message_create_time":
                        create_time,
                    "is_current_branch":
                        (
                            node_id
                            in current_nodes
                        ),
                    **block,
                    "lineage":
                        {
                            "source_payload_sha256":
                                source[
                                    "payload_sha256"
                                ],
                            "conversation_id":
                                conversation_id,
                            "node_id":
                                node_id,
                            "message_id":
                                message_id,
                            "message_projection_id":
                                record[
                                    "id"
                                ],
                        },
                }
            )

    messages.sort(
        key=lambda row: (
            (
                row[
                    "message"
                ][
                    "create_time"
                ]
                is None
            ),
            (
                row[
                    "message"
                ][
                    "create_time"
                ]
                or 0.0
            ),
            row[
                "graph"
            ][
                "mapping_index"
            ],
            row[
                "graph"
            ][
                "node_id"
            ],
        )
    )

    codes.sort(
        key=lambda row: (
            (
                row[
                    "message_create_time"
                ]
                is None
            ),
            (
                row[
                    "message_create_time"
                ]
                or 0.0
            ),
            row[
                "conversation_id"
            ],
            row[
                "node_id"
            ],
            row[
                "index"
            ],
        )
    )

    return (
        messages,
        codes,
        sorted(
            set(
                issues
            )
        ),
    )


def project(
    conversations: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    source: Mapping[
        str,
        Any,
    ],
) -> tuple[
    list[
        dict[
            str,
            Any,
        ]
    ],
    list[
        dict[
            str,
            Any,
        ]
    ],
    list[str],
]:
    message_rows: list[
        dict[
            str,
            Any,
        ]
    ] = []

    code_rows: list[
        dict[
            str,
            Any,
        ]
    ] = []

    issues: list[str] = []

    ordered = list(
        enumerate(
            conversations
        )
    )

    ordered.sort(
        key=lambda pair: (
            (
                finite_number(
                    pair[
                        1
                    ].get(
                        "create_time"
                    )
                )
                is None
            ),
            (
                finite_number(
                    pair[
                        1
                    ].get(
                        "create_time"
                    )
                )
                or 0.0
            ),
            str(
                pair[
                    1
                ].get(
                    "id"
                )
                or ""
            ),
            pair[
                0
            ],
        )
    )

    for (
        original_index,
        conversation,
    ) in ordered:
        (
            messages,
            codes,
            conversation_issues,
        ) = project_conversation(
            conversation,
            conversation_index=(
                original_index
            ),
            source=source,
        )

        message_rows.extend(
            messages
        )

        code_rows.extend(
            codes
        )

        issues.extend(
            conversation_issues
        )

    return (
        message_rows,
        code_rows,
        sorted(
            set(
                issues
            )
        ),
    )


def jsonl_bytes(
    rows: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> bytes:
    return (
        "".join(
            canonical_json(
                row
            )
            + "\n"
            for row
            in rows
        )
    ).encode(
        "utf-8"
    )


def manifest_value(
    *,
    source: Mapping[
        str,
        Any,
    ],
    messages: list[
        dict[
            str,
            Any,
        ]
    ],
    codes: list[
        dict[
            str,
            Any,
        ]
    ],
    issues: list[str],
    message_bytes: bytes,
    code_bytes: bytes,
) -> dict[
    str,
    Any,
]:
    conversations = {
        row[
            "conversation"
        ][
            "id"
        ]
        for row
        in messages
    }

    return {
        "schema":
            schema,
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "authoritative":
            False,
        "rebuildable":
            True,
        "source":
            dict(
                source
            ),
        "counts":
            {
                "conversations":
                    len(
                        conversations
                    ),
                "messages":
                    len(
                        messages
                    ),
                "code_blocks":
                    len(
                        codes
                    ),
                "graph_issues":
                    len(
                        issues
                    ),
            },
        "outputs":
            {
                "messages.jsonl":
                    {
                        "sha256":
                            sha256_bytes(
                                message_bytes
                            ),
                        "records":
                            len(
                                messages
                            ),
                    },
                "code_blocks.jsonl":
                    {
                        "sha256":
                            sha256_bytes(
                                code_bytes
                            ),
                        "records":
                            len(
                                codes
                            ),
                    },
            },
        "graph_issues":
            issues,
    }


def atomic_write(
    path: Path,
    data: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        descriptor,
        temporary_name,
    ) = tempfile.mkstemp(
        prefix=(
            f".{path.name}."
        ),
        dir=str(
            path.parent
        ),
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
            closefd=True,
        ) as handle:
            handle.write(
                data
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

        directory = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(
                directory
            )

        finally:
            os.close(
                directory
            )

    finally:
        temporary.unlink(
            missing_ok=True
        )


def write_projection(
    input_path: Path,
    output: Path,
) -> dict[
    str,
    Any,
]:
    (
        conversations,
        source,
    ) = load_conversations(
        input_path
    )

    (
        messages,
        codes,
        issues,
    ) = project(
        conversations,
        source,
    )

    message_bytes = (
        jsonl_bytes(
            messages
        )
    )

    code_bytes = (
        jsonl_bytes(
            codes
        )
    )

    manifest = (
        manifest_value(
            source=source,
            messages=messages,
            codes=codes,
            issues=issues,
            message_bytes=(
                message_bytes
            ),
            code_bytes=(
                code_bytes
            ),
        )
    )

    manifest_bytes = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    atomic_write(
        output
        / "messages.jsonl",
        message_bytes,
    )

    atomic_write(
        output
        / "code_blocks.jsonl",
        code_bytes,
    )

    atomic_write(
        output
        / "manifest.json",
        manifest_bytes,
    )

    return manifest


def selftest() -> dict[
    str,
    Any,
]:
    conversation = {
        "id":
            "conversation-a",
        "title":
            "Savant test",
        "create_time":
            10.0,
        "update_time":
            14.0,
        "current_node":
            "assistant-main",
        "mapping":
            {
                "root":
                    {
                        "id":
                            "root",
                        "parent":
                            None,
                        "children":
                            [
                                "user-1"
                            ],
                        "message":
                            None,
                    },
                "user-1":
                    {
                        "id":
                            "user-1",
                        "parent":
                            "root",
                        "children":
                            [
                                "assistant-main",
                                "assistant-alt",
                            ],
                        "message":
                            {
                                "id":
                                    "message-user",
                                "author":
                                    {
                                        "role":
                                            "user",
                                    },
                                "create_time":
                                    11.0,
                                "content":
                                    {
                                        "content_type":
                                            "text",
                                        "parts":
                                            [
                                                "Build Savant."
                                            ],
                                    },
                                "metadata":
                                    {},
                            },
                    },
                "assistant-main":
                    {
                        "id":
                            "assistant-main",
                        "parent":
                            "user-1",
                        "children":
                            [],
                        "message":
                            {
                                "id":
                                    "message-main",
                                "author":
                                    {
                                        "role":
                                            "assistant",
                                    },
                                "create_time":
                                    12.0,
                                "content":
                                    {
                                        "content_type":
                                            "text",
                                        "parts":
                                            [
                                                (
                                                    "Here:\n"
                                                    "```python\n"
                                                    "print('ok')\n"
                                                    "```\n"
                                                    "Tail.\n"
                                                    "~~~sql\n"
                                                    "select 1;\n"
                                                    "~~~"
                                                )
                                            ],
                                    },
                                "metadata":
                                    {
                                        "model_slug":
                                            "test-model"
                                    },
                            },
                    },
                "assistant-alt":
                    {
                        "id":
                            "assistant-alt",
                        "parent":
                            "user-1",
                        "children":
                            [],
                        "message":
                            {
                                "id":
                                    "message-alt",
                                "author":
                                    {
                                        "role":
                                            "assistant",
                                    },
                                "create_time":
                                    13.0,
                                "content":
                                    {
                                        "content_type":
                                            "text",
                                        "parts":
                                            [
                                                (
                                                    "Alternative "
                                                    "branch."
                                                )
                                            ],
                                    },
                                "metadata":
                                    {},
                            },
                    },
            },
    }

    with tempfile.TemporaryDirectory(
        prefix=(
            "sieve-chatgpt-test-"
        )
    ) as temporary:
        root = Path(
            temporary
        )

        conversations_path = (
            root
            / "conversations.json"
        )

        conversations_path.write_text(
            json.dumps(
                [
                    conversation
                ]
            ),
            encoding="utf-8",
        )

        zip_path = (
            root
            / "export.zip"
        )

        with zipfile.ZipFile(
            zip_path,
            "w",
        ) as archive:
            archive.writestr(
                "conversations.json",
                conversations_path.read_bytes(),
            )

        output_a = (
            root
            / "a"
        )

        output_b = (
            root
            / "b"
        )

        manifest_a = (
            write_projection(
                zip_path,
                output_a,
            )
        )

        manifest_b = (
            write_projection(
                zip_path,
                output_b,
            )
        )

        message_lines = [
            json.loads(
                line
            )
            for line
            in (
                output_a
                / "messages.jsonl"
            ).read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        code_lines = [
            json.loads(
                line
            )
            for line
            in (
                output_a
                / "code_blocks.jsonl"
            ).read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

        main = next(
            row
            for row
            in message_lines
            if (
                row[
                    "graph"
                ][
                    "node_id"
                ]
                == "assistant-main"
            )
        )

        alt = next(
            row
            for row
            in message_lines
            if (
                row[
                    "graph"
                ][
                    "node_id"
                ]
                == "assistant-alt"
            )
        )

        import sys

        runtime_root = (
            Path(
                __file__
            ).resolve().parent
        )

        if (
            str(
                runtime_root
            )
            not in sys.path
        ):
            sys.path.insert(
                0,
                str(
                    runtime_root
                ),
            )

        from importer import (
            import_path
        )

        imported = list(
            import_path(
                output_a
                / "messages.jsonl"
            )
        )

        checks = {
            "zip_detected":
                (
                    manifest_a[
                        "source"
                    ][
                        "payload_member"
                    ]
                    == "conversations.json"
                ),

            "three_messages":
                (
                    len(
                        message_lines
                    )
                    == 3
                ),

            "branch_preserved":
                (
                    main[
                        "graph"
                    ][
                        "is_current_branch"
                    ]
                    is True
                    and alt[
                        "graph"
                    ][
                        "is_current_branch"
                    ]
                    is False
                ),

            "parent_preserved":
                (
                    main[
                        "graph"
                    ][
                        "parent_node_id"
                    ]
                    == "user-1"
                ),

            "path_preserved":
                (
                    main[
                        "graph"
                    ][
                        "branch_path"
                    ]
                    == [
                        "root",
                        "user-1",
                        "assistant-main",
                    ]
                ),

            "two_code_blocks":
                (
                    len(
                        code_lines
                    )
                    == 2
                ),

            "languages_preserved":
                (
                    [
                        row[
                            "language"
                        ]
                        for row
                        in code_lines
                    ]
                    == [
                        "python",
                        "sql",
                    ]
                ),

            "code_exact":
                (
                    code_lines[
                        0
                    ][
                        "code"
                    ]
                    == "print('ok')\n"
                ),

            "code_linked":
                all(
                    (
                        row[
                            "message_projection_id"
                        ]
                        == main[
                            "id"
                        ]
                    )
                    for row
                    in code_lines
                ),

            "no_authority":
                all(
                    (
                        row[
                            "authority_effect"
                        ]
                        == "none"
                        and row[
                            "authoritative"
                        ]
                        is False
                    )
                    for row
                    in (
                        message_lines
                        + code_lines
                    )
                ),

            "engine_import_compatible":
                (
                    len(
                        imported
                    )
                    == 3
                ),

            "deterministic_messages":
                (
                    (
                        output_a
                        / "messages.jsonl"
                    ).read_bytes()
                    == (
                        output_b
                        / "messages.jsonl"
                    ).read_bytes()
                ),

            "deterministic_code":
                (
                    (
                        output_a
                        / "code_blocks.jsonl"
                    ).read_bytes()
                    == (
                        output_b
                        / "code_blocks.jsonl"
                    ).read_bytes()
                ),

            "deterministic_manifest":
                (
                    manifest_a
                    == manifest_b
                ),

            "rebuildable":
                (
                    manifest_a[
                        "rebuildable"
                    ]
                    is True
                ),
        }

        return {
            "schema":
                (
                    "savant://runtime/sieve/"
                    "chatgpt-export-selftest/1.0.0"
                ),
            "ok":
                all(
                    checks.values()
                ),
            "checks":
                checks,
            "counts":
                manifest_a[
                    "counts"
                ],
        }


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    arguments = (
        parser.parse_args()
    )

    if arguments.selftest:
        print(
            json.dumps(
                selftest(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return 0

    if arguments.input is None:
        parser.error(
            "input ChatGPT export zip "
            "or conversations.json "
            "is required"
        )

    if arguments.output is None:
        parser.error(
            "--output is required"
        )

    try:
        manifest = (
            write_projection(
                arguments.input,
                arguments.output,
            )
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "ok":
                        False,
                    "error":
                        str(
                            exc
                        ),
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return 1

    print(
        json.dumps(
            {
                "schema":
                    schema,
                "ok":
                    True,
                "output":
                    str(
                        arguments.output.resolve()
                    ),
                "manifest":
                    manifest,
            },
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
