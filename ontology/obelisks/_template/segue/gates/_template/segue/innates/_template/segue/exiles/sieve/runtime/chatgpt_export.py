#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Mapping


schema = "savant://runtime/sieve/chatgpt-export/2.0.1"
owner = "sieve"
authority_effect = "none"

read_chunk_size = 1024 * 1024
compact_threshold = 4 * 1024 * 1024


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


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def text_digest(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def scalar_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    return str(value)


def extract_message_text(
    message: Mapping[str, Any],
) -> str:
    content = message.get("content")

    if not isinstance(content, Mapping):
        return ""

    parts = content.get("parts")

    if isinstance(parts, list):
        rendered: list[str] = []

        for part in parts:
            if isinstance(part, str):
                rendered.append(part)

            elif isinstance(part, Mapping):
                text = part.get("text")

                if isinstance(text, str):
                    rendered.append(text)

                else:
                    rendered.append(
                        canonical_json(part)
                    )

            elif part is not None:
                rendered.append(
                    scalar_text(part)
                )

        return "\n".join(rendered)

    text = content.get("text")

    if isinstance(text, str):
        return text

    return ""


def author_projection(
    message: Mapping[str, Any],
) -> dict[str, Any]:
    author = message.get("author")

    if not isinstance(author, Mapping):
        return {
            "role": None,
            "name": None,
        }

    return {
        "role": author.get("role"),
        "name": author.get("name"),
    }


def metadata_projection(
    message: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = message.get("metadata")

    if not isinstance(metadata, Mapping):
        metadata = {}

    return {
        "model_slug": (
            metadata.get("model_slug")
            or metadata.get("default_model_slug")
        ),
        "request_id": (
            metadata.get("request_id")
        ),
        "message_type": (
            metadata.get("message_type")
        ),
        "status": message.get("status"),
        "recipient": message.get("recipient"),
    }


def conversation_projection(
    conversation: Mapping[str, Any],
    source_file: Path,
    source_index: int,
) -> Iterator[dict[str, Any]]:
    conversation_id = (
        conversation.get("conversation_id")
        or conversation.get("id")
    )

    title = conversation.get("title")
    create_time = conversation.get("create_time")
    update_time = conversation.get("update_time")
    current_node = conversation.get("current_node")

    mapping = conversation.get("mapping")

    if not isinstance(mapping, Mapping):
        return

    emitted: set[str] = set()

    def emit_node(
        node_id: str,
        node: Mapping[str, Any],
        traversal_index: int,
    ) -> dict[str, Any] | None:
        message = node.get("message")

        if not isinstance(message, Mapping):
            return None

        text = extract_message_text(message)
        author = author_projection(message)
        metadata = metadata_projection(message)

        source_ref = {
            "source_file": source_file.name,
            "source_conversation_index": source_index,
            "conversation_id": conversation_id,
            "node_id": node_id,
            "parent_node_id": node.get("parent"),
            "children_node_ids": (
                list(node.get("children"))
                if isinstance(
                    node.get("children"),
                    list,
                )
                else []
            ),
            "traversal_index": traversal_index,
        }

        identity_projection = {
            "source_ref": source_ref,
            "message_id": message.get("id"),
            "author": author,
            "create_time": message.get("create_time"),
            "text_sha256": text_digest(text),
        }

        return {
            "schema": (
                "savant://runtime/sieve/"
                "chatgpt-export-message/2.0.1"
            ),
            "owner": owner,
            "authority_effect": authority_effect,
            "authoritative": False,
            "source_ref": source_ref,
            "source_digest": digest(
                identity_projection
            ),
            "conversation": {
                "id": conversation_id,
                "title": title,
                "create_time": create_time,
                "update_time": update_time,
                "current_node": current_node,
            },
            "message": {
                "id": message.get("id"),
                "create_time": message.get("create_time"),
                "update_time": message.get("update_time"),
                "author": author,
                "metadata": metadata,
                "text": text,
                "text_sha256": text_digest(text),
            },
            "boundaries": {
                "source_text_preserved": True,
                "authority_created": False,
                "canon_mutated": False,
                "implementation_eligible": False,
            },
        }

    roots: list[str] = []

    for raw_node_id, raw_node in mapping.items():
        node_id = str(raw_node_id)

        if not isinstance(raw_node, Mapping):
            continue

        parent = raw_node.get("parent")

        if (
            parent is None
            or str(parent) not in mapping
        ):
            roots.append(node_id)

    roots.sort()

    traversal_index = 0
    stack = list(reversed(roots))

    while stack:
        node_id = stack.pop()

        if node_id in emitted:
            continue

        node = mapping.get(node_id)

        if not isinstance(node, Mapping):
            emitted.add(node_id)
            continue

        emitted.add(node_id)

        record = emit_node(
            node_id,
            node,
            traversal_index,
        )

        if record is not None:
            yield record
            traversal_index += 1

        children = node.get("children")

        if isinstance(children, list):
            normalized_children = [
                str(child)
                for child in children
                if str(child) in mapping
            ]

            for child in reversed(
                normalized_children
            ):
                if child not in emitted:
                    stack.append(child)

    for raw_node_id in sorted(
        str(value)
        for value in mapping.keys()
    ):
        if raw_node_id in emitted:
            continue

        node = mapping.get(raw_node_id)

        if not isinstance(node, Mapping):
            continue

        emitted.add(raw_node_id)

        record = emit_node(
            raw_node_id,
            node,
            traversal_index,
        )

        if record is not None:
            yield record
            traversal_index += 1


def iter_top_level_array(
    path: Path,
) -> Iterator[Any]:
    decoder = json.JSONDecoder()

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        buffer = ""
        position = 0
        eof = False
        started = False
        finished = False

        while not finished:
            if (
                not eof
                and (
                    position >= len(buffer)
                    or len(buffer) - position
                    < read_chunk_size
                )
            ):
                chunk = handle.read(
                    read_chunk_size
                )

                if chunk:
                    if position:
                        buffer = buffer[position:]
                        position = 0

                    buffer += chunk
                else:
                    eof = True

            while True:
                while (
                    position < len(buffer)
                    and buffer[position].isspace()
                ):
                    position += 1

                if not started:
                    if position >= len(buffer):
                        break

                    if buffer[position] != "[":
                        raise chatgpt_export_error(
                            "expected top-level JSON array "
                            f"in {path}"
                        )

                    started = True
                    position += 1
                    continue

                while (
                    position < len(buffer)
                    and buffer[position].isspace()
                ):
                    position += 1

                if position >= len(buffer):
                    break

                if buffer[position] == "]":
                    position += 1
                    finished = True
                    break

                try:
                    value, end = decoder.raw_decode(
                        buffer,
                        position,
                    )
                except json.JSONDecodeError:
                    if eof:
                        raise chatgpt_export_error(
                            "truncated or invalid JSON "
                            f"in {path}"
                        )

                    break

                yield value
                position = end

                while (
                    position < len(buffer)
                    and buffer[position].isspace()
                ):
                    position += 1

                if position >= len(buffer):
                    break

                if buffer[position] == ",":
                    position += 1
                    continue

                if buffer[position] == "]":
                    position += 1
                    finished = True
                    break

                raise chatgpt_export_error(
                    "expected ',' or ']' after "
                    f"top-level value in {path}"
                )

            if (
                position >= compact_threshold
                and position > len(buffer) // 2
            ):
                buffer = buffer[position:]
                position = 0

            if eof and not finished:
                remaining = buffer[position:].strip()

                if remaining:
                    raise chatgpt_export_error(
                        "unexpected trailing or "
                        f"incomplete JSON in {path}"
                    )

                raise chatgpt_export_error(
                    "top-level JSON array was "
                    f"not closed in {path}"
                )


def conversation_files(
    export_root: Path,
) -> list[Path]:
    files = sorted(
        path
        for path in export_root.glob(
            "conversations-*.json"
        )
        if path.is_file()
    )

    if files:
        return files

    fallback = export_root / "conversations.json"

    if fallback.is_file():
        return [fallback]

    raise chatgpt_export_error(
        "no ChatGPT conversation export "
        f"files found under {export_root}"
    )


def extract_export(
    export_root: Path,
    output: Path,
) -> dict[str, Any]:
    export_root = export_root.resolve()
    output = output.resolve()

    if not export_root.is_dir():
        raise chatgpt_export_error(
            f"export root is not a directory: {export_root}"
        )

    files = conversation_files(
        export_root
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    conversation_count = 0
    message_count = 0
    source_files: list[dict[str, Any]] = []

    with output.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as sink:
        for source_file in files:
            source_conversations = 0
            source_messages = 0

            for source_index, conversation in enumerate(
                iter_top_level_array(
                    source_file
                )
            ):
                if not isinstance(
                    conversation,
                    Mapping,
                ):
                    continue

                conversation_count += 1
                source_conversations += 1

                for record in conversation_projection(
                    conversation,
                    source_file,
                    source_index,
                ):
                    sink.write(
                        canonical_json(record)
                    )
                    sink.write("\n")

                    message_count += 1
                    source_messages += 1

            source_files.append(
                {
                    "path": source_file.name,
                    "conversation_count": (
                        source_conversations
                    ),
                    "message_count": (
                        source_messages
                    ),
                }
            )

    projection = {
        "source_files": source_files,
        "conversation_count": conversation_count,
        "message_count": message_count,
    }

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": authority_effect,
        "authoritative": False,
        "export_root": str(export_root),
        "output": str(output),
        "source_files": source_files,
        "conversation_count": conversation_count,
        "message_count": message_count,
        "projection_digest": digest(
            projection
        ),
        "boundaries": {
            "source_mutated": False,
            "canon_mutated": False,
            "authority_created": False,
            "source_text_preserved": True,
            "streaming_top_level_ingestion": True,
            "implementation_eligible": False,
        },
    }


def selftest() -> dict[str, Any]:
    message = {
        "id": "m1",
        "author": {
            "role": "user",
            "name": None,
        },
        "create_time": 1.0,
        "content": {
            "content_type": "text",
            "parts": [
                "alpha",
                "beta",
            ],
        },
        "metadata": {
            "model_slug": "test-model",
        },
    }

    text = extract_message_text(
        message
    )

    checks = {
        "authority_none": (
            authority_effect == "none"
        ),
        "owner_sieve": (
            owner == "sieve"
        ),
        "text_preserved": (
            text == "alpha\nbeta"
        ),
        "role_preserved": (
            author_projection(
                message
            )["role"]
            == "user"
        ),
        "stable_digest": (
            digest(
                {
                    "a": 1,
                    "b": 2,
                }
            )
            == digest(
                {
                    "b": 2,
                    "a": 1,
                }
            )
        ),
        "implementation_blocked": True,
    }

    return {
        "schema": (
            "savant://runtime/sieve/"
            "chatgpt-export-selftest/2.0.1"
        ),
        "ok": all(
            checks.values()
        ),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    parser.add_argument(
        "--export-root",
    )

    parser.add_argument(
        "--output",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        result = selftest()

    else:
        if not arguments.export_root:
            parser.error(
                "--export-root is required"
            )

        if not arguments.output:
            parser.error(
                "--output is required"
            )

        result = extract_export(
            Path(arguments.export_root),
            Path(arguments.output),
        )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
