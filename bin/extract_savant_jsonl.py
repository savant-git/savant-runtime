#!/usr/bin/env python3

from __future__ import annotations

import argparse
import bz2
import gzip
import hashlib
import json
import lzma
import os
import sys
import tempfile
import time
import unicodedata
import zipfile

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator, Mapping, Sequence


PROGRAM = "extract_savant_jsonl"
VERSION = "3.0.0"
SCHEMA = "savant://extract/chatgpt/savant-jsonl/3.0.0"

SAVANT_ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

BIN_ROOT = SAVANT_ROOT / "bin"

DEFAULT_THRESHOLD = 2
DEFAULT_CONTEXT_WINDOW = 0
DEFAULT_PROGRESS_INTERVAL = 1000
DEFAULT_MAX_ERRORS = 100
DEFAULT_BRANCH_MODE = "all"
DEFAULT_OUTPUT_NAME = "savant_output.jsonl"

ROLE_VALUES = frozenset(
    {
        "assistant",
        "user",
        "system",
        "tool",
        "developer",
        "unknown",
    }
)

try:
    import ijson  # type: ignore
except Exception:
    ijson = None

try:
    import orjson  # type: ignore
except Exception:
    orjson = None

try:
    from savant_extraction_classifier import classify
except Exception as exc:
    classify = None
    CLASSIFIER_IMPORT_ERROR = str(exc)
else:
    CLASSIFIER_IMPORT_ERROR = None


class ExtractorError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: int
    exact_hits: tuple[str, ...]
    fuzzy_hits: tuple[str, ...]
    include_hits: tuple[str, ...]
    excluded: bool
    title_score: int = 0

    def projection(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "exact_hits": list(self.exact_hits),
            "fuzzy_hits": list(self.fuzzy_hits),
            "include_hits": list(self.include_hits),
            "excluded": self.excluded,
            "title_score": self.title_score,
        }


@dataclass(slots=True)
class Statistics:
    conversations_seen: int = 0
    conversations_with_matches: int = 0
    messages_seen: int = 0
    messages_with_text: int = 0
    messages_matched: int = 0
    messages_context: int = 0
    messages_written: int = 0
    messages_duplicate: int = 0
    messages_role_filtered: int = 0
    messages_date_filtered: int = 0
    messages_length_filtered: int = 0
    messages_excluded: int = 0
    malformed_conversations: int = 0
    malformed_messages: int = 0
    errors: int = 0
    roles: Counter[str] = field(default_factory=Counter)
    signals: Counter[str] = field(default_factory=Counter)

    def projection(self) -> dict[str, Any]:
        return {
            "conversations_seen": self.conversations_seen,
            "conversations_with_matches": self.conversations_with_matches,
            "messages_seen": self.messages_seen,
            "messages_with_text": self.messages_with_text,
            "messages_matched": self.messages_matched,
            "messages_context": self.messages_context,
            "messages_written": self.messages_written,
            "messages_duplicate": self.messages_duplicate,
            "messages_role_filtered": self.messages_role_filtered,
            "messages_date_filtered": self.messages_date_filtered,
            "messages_length_filtered": self.messages_length_filtered,
            "messages_excluded": self.messages_excluded,
            "malformed_conversations": self.malformed_conversations,
            "malformed_messages": self.malformed_messages,
            "errors": self.errors,
            "roles": dict(sorted(self.roles.items())),
            "signals": dict(
                sorted(
                    self.signals.items(),
                    key=lambda row: (-row[1], row[0]),
                )
            ),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)

            if not chunk:
                break

            hasher.update(chunk)

    return hasher.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def stable_digest(value: Any) -> str:
    return sha256_bytes(
        canonical_json(value).encode("utf-8")
    )


def json_dumps_line(value: Any) -> bytes:
    if orjson is not None:
        return orjson.dumps(
            value,
            option=orjson.OPT_APPEND_NEWLINE,
            default=str,
        )

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        + "\n"
    ).encode("utf-8")


def json_load_bytes(value: bytes) -> Any:
    if orjson is not None:
        return orjson.loads(value)

    return json.loads(
        value.decode("utf-8")
    )


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize(
        "NFKC",
        value,
    )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(
        value,
        (int, float, bool),
    ):
        return str(value)

    if isinstance(value, list):
        return " ".join(
            part
            for part in (
                normalize_text(item).strip()
                for item in value
            )
            if part
        )

    if isinstance(value, Mapping):
        if isinstance(
            value.get("parts"),
            list,
        ):
            return normalize_text(
                value["parts"]
            )

        for key in (
            "text",
            "content",
        ):
            if key in value:
                text = normalize_text(
                    value.get(key)
                ).strip()

                if text:
                    return text

        recovered = []

        for key in (
            "result",
            "value",
            "caption",
            "name",
            "title",
        ):
            if key in value:
                text = normalize_text(
                    value.get(key)
                ).strip()

                if text:
                    recovered.append(text)

        if recovered:
            return " ".join(recovered)

        return " ".join(
            part
            for part in (
                normalize_text(item).strip()
                for item in value.values()
            )
            if part
        )

    return str(value)


def format_timestamp(
    value: Any,
) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        candidate = value.strip()

        if not candidate:
            return None

        try:
            numeric = float(candidate)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(
                    candidate.replace(
                        "Z",
                        "+00:00",
                    )
                )
            except ValueError:
                return None

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            ).isoformat()
    else:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None

    try:
        return datetime.fromtimestamp(
            numeric,
            tz=timezone.utc,
        ).isoformat()
    except (
        OverflowError,
        OSError,
        ValueError,
    ):
        return None


def parse_boundary(
    value: str | None,
) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise ExtractorError(
            f"invalid datetime boundary: {value}"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def timestamp_datetime(
    value: str | None,
) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def resolve_input_path(
    value: str,
) -> Path:
    candidate = Path(
        os.path.expandvars(
            os.path.expanduser(value)
        )
    )

    if candidate.is_absolute():
        return candidate.resolve()

    cwd_candidate = (
        Path.cwd()
        / candidate
    ).resolve()

    if cwd_candidate.exists():
        return cwd_candidate

    return (
        SAVANT_ROOT
        / candidate
    ).resolve()


def resolve_output_path(
    value: str | None,
    input_path: Path,
) -> Path:
    if value:
        candidate = Path(
            os.path.expandvars(
                os.path.expanduser(value)
            )
        )

        if candidate.is_absolute():
            return candidate.resolve()

        return (
            Path.cwd()
            / candidate
        ).resolve()

    return (
        input_path.parent
        / DEFAULT_OUTPUT_NAME
    ).resolve()


def extract_zip_member(
    archive_path: Path,
) -> tuple[BinaryIO, str, Any]:
    archive = zipfile.ZipFile(
        archive_path,
        "r",
    )

    names = [
        name
        for name in archive.namelist()
        if not name.endswith("/")
    ]

    preferred = [
        name
        for name in names
        if Path(name).name
        == "conversations.json"
    ]

    selected = (
        preferred[0]
        if preferred
        else (
            names[0]
            if len(names) == 1
            else None
        )
    )

    if selected is None:
        archive.close()

        raise ExtractorError(
            "ZIP archive contains multiple files "
            "and no conversations.json"
        )

    stream = archive.open(
        selected,
        "r",
    )

    return (
        stream,
        f"{archive_path}!{selected}",
        archive,
    )


def open_input_stream(
    path: Path,
) -> tuple[BinaryIO, str, Any]:
    suffix = path.suffix.casefold()

    if suffix == ".gz":
        handle = gzip.open(
            path,
            "rb",
        )
        return handle, str(path), handle

    if suffix == ".bz2":
        handle = bz2.open(
            path,
            "rb",
        )
        return handle, str(path), handle

    if suffix in {
        ".xz",
        ".lzma",
    }:
        handle = lzma.open(
            path,
            "rb",
        )
        return handle, str(path), handle

    if suffix == ".zip":
        return extract_zip_member(path)

    handle = path.open("rb")

    return handle, str(path), handle


def iter_conversations_stdlib(
    path: Path,
) -> Iterator[dict[str, Any]]:
    stream, _, closer = open_input_stream(
        path
    )

    try:
        payload = json_load_bytes(
            stream.read()
        )
    finally:
        closer.close()

    if isinstance(payload, list):
        for conversation in payload:
            if isinstance(
                conversation,
                dict,
            ):
                yield conversation
        return

    if isinstance(payload, dict):
        conversations = payload.get(
            "conversations"
        )

        if isinstance(
            conversations,
            list,
        ):
            for conversation in conversations:
                if isinstance(
                    conversation,
                    dict,
                ):
                    yield conversation
            return

    raise ExtractorError(
        "ChatGPT export must contain a "
        "top-level conversation array"
    )


def iter_conversations_streaming(
    path: Path,
) -> Iterator[dict[str, Any]]:
    if ijson is None:
        yield from iter_conversations_stdlib(
            path
        )
        return

    stream, _, closer = open_input_stream(
        path
    )

    try:
        yielded = False

        for conversation in ijson.items(
            stream,
            "item",
        ):
            if isinstance(
                conversation,
                dict,
            ):
                yielded = True
                yield conversation

        if yielded:
            return
    finally:
        closer.close()

    yield from iter_conversations_stdlib(
        path
    )


def extract_author(
    message: Mapping[str, Any],
) -> dict[str, Any]:
    author = message.get(
        "author"
    )

    if not isinstance(
        author,
        Mapping,
    ):
        return {
            "role": "unknown",
            "name": None,
            "metadata": {},
        }

    role = str(
        author.get(
            "role",
            "unknown",
        )
        or "unknown"
    )

    return {
        "role": role,
        "name": author.get("name"),
        "metadata": author.get(
            "metadata",
            {},
        ),
    }


def root_nodes(
    mapping: Mapping[str, Any],
) -> tuple[str, ...]:
    roots = []

    for node_id, node in mapping.items():
        if not isinstance(
            node,
            Mapping,
        ):
            continue

        parent = node.get("parent")

        if (
            parent is None
            or parent not in mapping
        ):
            roots.append(
                str(node_id)
            )

    return tuple(
        sorted(roots)
    )


def current_branch_ids(
    conversation: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> frozenset[str]:
    current = conversation.get(
        "current_node"
    )

    if current not in mapping:
        return frozenset()

    result: set[str] = set()
    cursor: str | None = str(current)

    while (
        cursor
        and cursor in mapping
        and cursor not in result
    ):
        result.add(cursor)

        node = mapping.get(cursor)

        if not isinstance(
            node,
            Mapping,
        ):
            break

        parent = node.get("parent")

        cursor = (
            str(parent)
            if parent is not None
            else None
        )

    return frozenset(result)


def traverse_mapping(
    conversation: Mapping[str, Any],
    branch_mode: str,
) -> list[dict[str, Any]]:
    mapping = conversation.get(
        "mapping"
    )

    if not isinstance(
        mapping,
        Mapping,
    ):
        return []

    current_ids = current_branch_ids(
        conversation,
        mapping,
    )

    roots = root_nodes(mapping)

    if not roots:
        roots = tuple(
            sorted(
                str(key)
                for key in mapping
            )
        )

    queue = deque(
        (
            root,
            0,
            (),
        )
        for root in roots
    )

    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    traversal_index = 0

    while queue:
        node_id, depth, ancestry = (
            queue.popleft()
        )

        if node_id in seen:
            continue

        seen.add(node_id)

        node = mapping.get(node_id)

        if not isinstance(
            node,
            Mapping,
        ):
            continue

        message = node.get(
            "message"
        )

        if isinstance(
            message,
            Mapping,
        ):
            if (
                branch_mode != "current"
                or node_id in current_ids
            ):
                author = extract_author(
                    message
                )

                raw_content = message.get(
                    "content"
                )

                text = normalize_text(
                    raw_content
                ).strip()

                records.append(
                    {
                        "message_id": str(
                            message.get("id")
                            or node_id
                        ),
                        "node_id": node_id,
                        "parent": (
                            str(node["parent"])
                            if node.get("parent")
                            is not None
                            else None
                        ),
                        "children": [
                            str(child)
                            for child in (
                                node.get("children")
                                or ()
                            )
                            if isinstance(
                                child,
                                str,
                            )
                        ],
                        "depth": depth,
                        "ancestry": list(
                            ancestry
                        ),
                        "on_current_branch": (
                            node_id
                            in current_ids
                        ),
                        "timestamp": (
                            format_timestamp(
                                message.get(
                                    "create_time"
                                )
                            )
                        ),
                        "role": author["role"],
                        "author": author,
                        "text": text,
                        "raw_content": (
                            raw_content
                        ),
                        "message_metadata": {
                            key: value
                            for key, value
                            in message.items()
                            if key not in {
                                "content",
                                "author",
                                "create_time",
                                "parent",
                            }
                        },
                        "traversal_index": (
                            traversal_index
                        ),
                    }
                )

                traversal_index += 1

        children = node.get(
            "children"
        )

        if (
            not isinstance(
                children,
                Sequence,
            )
            or isinstance(
                children,
                (str, bytes),
            )
        ):
            children = ()

        next_ancestry = (
            *ancestry,
            node_id,
        )

        for child in sorted(
            str(value)
            for value in children
            if isinstance(
                value,
                str,
            )
        ):
            queue.append(
                (
                    child,
                    depth + 1,
                    next_ancestry,
                )
            )

    records.sort(
        key=lambda row: (
            row["timestamp"] is None,
            row["timestamp"] or "",
            row["traversal_index"],
            row["message_id"],
        )
    )

    return records


def score_message(
    text: str,
    *,
    title: str,
    include_terms: Sequence[str],
    exclude_terms: Sequence[str],
    fuzzy: bool,
    fuzzy_cutoff: int,
) -> ScoreResult:
    if classify is None:
        raise ExtractorError(
            "classification module unavailable: "
            f"{CLASSIFIER_IMPORT_ERROR}"
        )

    result = classify(
        text,
        title=title,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        fuzzy=fuzzy,
        fuzzy_cutoff=fuzzy_cutoff,
    )

    return ScoreResult(
        score=int(result.score),
        exact_hits=tuple(
            result.exact_hits
        ),
        fuzzy_hits=tuple(
            result.fuzzy_hits
        ),
        include_hits=tuple(
            result.include_hits
        ),
        excluded=bool(
            result.excluded
        ),
        title_score=int(
            result.title_score
        ),
    )


def within_date_range(
    timestamp: str | None,
    *,
    after: datetime | None,
    before: datetime | None,
) -> bool:
    if (
        after is None
        and before is None
    ):
        return True

    parsed = timestamp_datetime(
        timestamp
    )

    if parsed is None:
        return False

    if (
        after is not None
        and parsed < after
    ):
        return False

    if (
        before is not None
        and parsed > before
    ):
        return False

    return True


def conversation_identity(
    conversation: Mapping[str, Any],
) -> str:
    return str(
        conversation.get(
            "conversation_id"
        )
        or conversation.get("id")
        or stable_digest(
            {
                "title": conversation.get(
                    "title"
                ),
                "create_time": (
                    conversation.get(
                        "create_time"
                    )
                ),
                "update_time": (
                    conversation.get(
                        "update_time"
                    )
                ),
            }
        )[:24]
    )


def conversation_metadata(
    conversation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value
        in conversation.items()
        if key not in {
            "mapping",
            "moderation_results",
        }
    }


def record_fingerprint(
    conversation_id: str,
    message: Mapping[str, Any],
) -> str:
    return stable_digest(
        {
            "conversation_id": (
                conversation_id
            ),
            "message_id": message.get(
                "message_id"
            ),
            "role": message.get("role"),
            "timestamp": message.get(
                "timestamp"
            ),
            "text": message.get("text"),
        }
    )


def existing_fingerprints(
    output_path: Path,
) -> set[str]:
    if not output_path.is_file():
        return set()

    result: set[str] = set()

    with output_path.open(
        "rb"
    ) as handle:
        for raw in handle:
            try:
                row = json_load_bytes(raw)
            except Exception:
                continue

            if not isinstance(
                row,
                Mapping,
            ):
                continue

            fingerprint = row.get(
                "fingerprint"
            )

            if isinstance(
                fingerprint,
                str,
            ):
                result.add(fingerprint)

    return result


def select_with_context(
    rows: list[
        tuple[
            dict[str, Any],
            ScoreResult,
            bool,
        ]
    ],
    window: int,
) -> list[
    tuple[
        dict[str, Any],
        ScoreResult,
        str,
    ]
]:
    matched_indices = {
        index
        for index, (
            _,
            _,
            matched,
        )
        in enumerate(rows)
        if matched
    }

    selected = {
        index: "match"
        for index in matched_indices
    }

    if window > 0:
        for index in matched_indices:
            start = max(
                0,
                index - window,
            )

            end = min(
                len(rows),
                index + window + 1,
            )

            for context_index in range(
                start,
                end,
            ):
                selected.setdefault(
                    context_index,
                    "context",
                )

    return [
        (
            rows[index][0],
            rows[index][1],
            selected[index],
        )
        for index in sorted(selected)
    ]


def build_output_entry(
    *,
    conversation: Mapping[str, Any],
    message: Mapping[str, Any],
    score: ScoreResult,
    selection_reason: str,
    preserve_raw: bool,
    source_identity: str,
) -> dict[str, Any]:
    conversation_id = (
        conversation_identity(
            conversation
        )
    )

    title = str(
        conversation.get(
            "title",
            "Untitled Conversation",
        )
        or "Untitled Conversation"
    )

    entry = {
        "schema": SCHEMA,
        "conversation_id": (
            conversation_id
        ),
        "title": title,
        "conversation_created": (
            format_timestamp(
                conversation.get(
                    "create_time"
                )
            )
        ),
        "conversation_updated": (
            format_timestamp(
                conversation.get(
                    "update_time"
                )
            )
        ),
        "message_id": message[
            "message_id"
        ],
        "node_id": message["node_id"],
        "parent": message["parent"],
        "children": message["children"],
        "depth": message["depth"],
        "ancestry": message["ancestry"],
        "on_current_branch": (
            message[
                "on_current_branch"
            ]
        ),
        "timestamp": message[
            "timestamp"
        ],
        "role": message["role"],
        "author": message["author"],
        "text": message["text"],
        "metadata": message[
            "message_metadata"
        ],
        "conversation_metadata": (
            conversation_metadata(
                conversation
            )
        ),
        "relevance": (
            score.projection()
        ),
        "selection_reason": (
            selection_reason
        ),
        "source": {
            "type": "chatgpt-export",
            "identity": (
                source_identity
            ),
        },
        "traversal_index": (
            message[
                "traversal_index"
            ]
        ),
    }

    if preserve_raw:
        entry["raw_content"] = (
            message["raw_content"]
        )

    entry["fingerprint"] = (
        record_fingerprint(
            conversation_id,
            message,
        )
    )

    return entry


def atomic_output(
    destination: Path,
) -> tuple[Path, BinaryIO]:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, name = (
        tempfile.mkstemp(
            prefix=(
                f".{destination.name}."
            ),
            suffix=".tmp",
            dir=str(
                destination.parent
            ),
        )
    )

    return (
        Path(name),
        os.fdopen(
            descriptor,
            "wb",
        ),
    )


def process_conversation(
    conversation: Mapping[str, Any],
    *,
    args: argparse.Namespace,
    source_identity: str,
    stats: Statistics,
    seen_fingerprints: set[str],
) -> list[dict[str, Any]]:
    stats.conversations_seen += 1

    title = str(
        conversation.get(
            "title",
            "",
        )
        or ""
    )

    messages = traverse_mapping(
        conversation,
        args.branch,
    )

    if not messages:
        stats.malformed_conversations += 1
        return []

    candidate_rows = []

    for message in messages:
        stats.messages_seen += 1

        text = str(
            message.get(
                "text",
                "",
            )
            or ""
        ).strip()

        if not text:
            continue

        stats.messages_with_text += 1

        role = str(
            message.get(
                "role",
                "unknown",
            )
            or "unknown"
        )

        stats.roles[role] += 1

        if (
            args.roles
            and role not in args.roles
        ):
            stats.messages_role_filtered += 1
            continue

        if not within_date_range(
            message.get("timestamp"),
            after=args.after_dt,
            before=args.before_dt,
        ):
            stats.messages_date_filtered += 1
            continue

        length = len(text)

        if (
            args.min_length is not None
            and length < args.min_length
        ):
            stats.messages_length_filtered += 1
            continue

        if (
            args.max_length is not None
            and length > args.max_length
        ):
            stats.messages_length_filtered += 1
            continue

        score = score_message(
            text,
            title=title,
            include_terms=args.include,
            exclude_terms=args.exclude,
            fuzzy=args.fuzzy,
            fuzzy_cutoff=(
                args.fuzzy_cutoff
            ),
        )

        if score.excluded:
            stats.messages_excluded += 1

        matched = (
            not score.excluded
            and score.score
            >= args.threshold
        )

        candidate_rows.append(
            (
                message,
                score,
                matched,
            )
        )

    selected = select_with_context(
        candidate_rows,
        args.context_window,
    )

    results = []
    matched_conversation = False

    for (
        message,
        score,
        reason,
    ) in selected:
        if reason == "match":
            stats.messages_matched += 1
            matched_conversation = True

            for signal in (
                score.exact_hits
            ):
                stats.signals[
                    signal
                ] += 1
        else:
            stats.messages_context += 1

        entry = build_output_entry(
            conversation=conversation,
            message=message,
            score=score,
            selection_reason=reason,
            preserve_raw=(
                args.preserve_raw
            ),
            source_identity=(
                source_identity
            ),
        )

        fingerprint = entry[
            "fingerprint"
        ]

        if fingerprint in (
            seen_fingerprints
        ):
            stats.messages_duplicate += 1
            continue

        seen_fingerprints.add(
            fingerprint
        )

        results.append(entry)

    if matched_conversation:
        stats.conversations_with_matches += 1

    return results


def dependency_status() -> dict[str, Any]:
    classifier_status = {
        "available": (
            classify is not None
        ),
        "path": str(
            BIN_ROOT
            / "savant_extraction_classifier.py"
        ),
        "error": (
            CLASSIFIER_IMPORT_ERROR
        ),
    }

    return {
        "ijson": {
            "available": (
                ijson is not None
            ),
            "purpose": (
                "bounded-memory streaming"
            ),
        },
        "orjson": {
            "available": (
                orjson is not None
            ),
            "purpose": (
                "accelerated JSON encoding"
            ),
        },
        "classifier": classifier_status,
    }


def write_receipt(
    *,
    output_path: Path,
    input_path: Path,
    stats: Statistics,
    args: argparse.Namespace,
    started_at: str,
    duration_seconds: float,
) -> Path:
    receipt_path = (
        output_path.with_suffix(
            output_path.suffix
            + ".receipt.json"
        )
    )

    receipt = {
        "schema": (
            "savant://extract/"
            "chatgpt/receipt/2"
        ),
        "program": PROGRAM,
        "version": VERSION,
        "started_at": started_at,
        "completed_at": utc_now(),
        "duration_seconds": round(
            duration_seconds,
            6,
        ),
        "source": {
            "path": str(input_path),
            "sha256": (
                sha256_file(input_path)
            ),
        },
        "output": {
            "path": str(output_path),
            "sha256": (
                sha256_file(output_path)
            ),
            "bytes": (
                output_path.stat().st_size
            ),
        },
        "configuration": {
            "threshold": (
                args.threshold
            ),
            "branch": args.branch,
            "context_window": (
                args.context_window
            ),
            "fuzzy": args.fuzzy,
            "fuzzy_cutoff": (
                args.fuzzy_cutoff
            ),
            "roles": (
                sorted(args.roles)
                if args.roles
                else None
            ),
            "after": args.after,
            "before": args.before,
            "min_length": (
                args.min_length
            ),
            "max_length": (
                args.max_length
            ),
            "include": args.include,
            "exclude": args.exclude,
            "preserve_raw": (
                args.preserve_raw
            ),
            "resume": args.resume,
        },
        "statistics": (
            stats.projection()
        ),
        "dependencies": (
            dependency_status()
        ),
        "classifier_owner": (
            "savant_extraction_classifier"
        ),
        "authority_effect": "none",
        "authoritative": False,
        "rebuildable": True,
    }

    receipt["digest"] = (
        stable_digest(receipt)
    )

    temporary, handle = (
        atomic_output(
            receipt_path
        )
    )

    try:
        handle.write(
            json.dumps(
                receipt,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                default=str,
            ).encode("utf-8")
        )

        handle.write(b"\n")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()

        os.replace(
            temporary,
            receipt_path,
        )
    except Exception:
        try:
            handle.close()
        except Exception:
            pass

        temporary.unlink(
            missing_ok=True
        )
        raise

    return receipt_path


def progress(
    stats: Statistics,
    started: float,
) -> None:
    elapsed = max(
        time.monotonic()
        - started,
        0.000001,
    )

    rate = (
        stats.messages_seen
        / elapsed
    )

    print(
        (
            "[progress] "
            f"conversations={stats.conversations_seen} "
            f"messages={stats.messages_seen} "
            f"matched={stats.messages_matched} "
            f"written={stats.messages_written} "
            f"rate={rate:.1f} msg/s"
        ),
        file=sys.stderr,
        flush=True,
    )


def run_extraction(
    args: argparse.Namespace,
) -> int:
    if classify is None:
        raise ExtractorError(
            "Savant classifier could not be loaded: "
            f"{CLASSIFIER_IMPORT_ERROR}"
        )

    input_path = resolve_input_path(
        args.input
    )

    if not input_path.is_file():
        raise ExtractorError(
            f"input file not found: {input_path}"
        )

    output_path = resolve_output_path(
        args.output,
        input_path,
    )

    if output_path == input_path:
        raise ExtractorError(
            "output path may not equal input path"
        )

    args.after_dt = parse_boundary(
        args.after
    )

    args.before_dt = parse_boundary(
        args.before
    )

    if (
        args.after_dt
        and args.before_dt
        and args.after_dt
        > args.before_dt
    ):
        raise ExtractorError(
            "--after must not be later than --before"
        )

    source_identity = str(
        input_path
    )

    stats = Statistics()

    seen_fingerprints = (
        existing_fingerprints(
            output_path
        )
        if args.resume
        else set()
    )

    started_at = utc_now()
    started = time.monotonic()

    if args.dry_run:
        destination = None
        temporary = None
        output_handle = None
    elif args.resume:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = output_path
        temporary = None
        output_handle = (
            output_path.open("ab")
        )
    else:
        destination = output_path

        temporary, output_handle = (
            atomic_output(
                output_path
            )
        )

    try:
        for conversation in (
            iter_conversations_streaming(
                input_path
            )
        ):
            try:
                entries = (
                    process_conversation(
                        conversation,
                        args=args,
                        source_identity=(
                            source_identity
                        ),
                        stats=stats,
                        seen_fingerprints=(
                            seen_fingerprints
                        ),
                    )
                )

                for entry in entries:
                    if output_handle:
                        output_handle.write(
                            json_dumps_line(
                                entry
                            )
                        )

                    stats.messages_written += 1

            except Exception as exc:
                stats.errors += 1

                if args.fail_fast:
                    raise

                print(
                    (
                        "[warning] conversation "
                        f"processing failed: {exc}"
                    ),
                    file=sys.stderr,
                )

                if (
                    stats.errors
                    > args.max_errors
                ):
                    raise ExtractorError(
                        "maximum error budget exceeded"
                    ) from exc

            if (
                args.progress_interval > 0
                and stats.conversations_seen
                % args.progress_interval
                == 0
            ):
                progress(
                    stats,
                    started,
                )

        if output_handle:
            output_handle.flush()
            os.fsync(
                output_handle.fileno()
            )
            output_handle.close()

        if (
            not args.dry_run
            and not args.resume
            and temporary is not None
        ):
            os.replace(
                temporary,
                destination,
            )

    except Exception:
        if output_handle:
            try:
                output_handle.close()
            except Exception:
                pass

        if temporary:
            temporary.unlink(
                missing_ok=True
            )

        raise

    duration = (
        time.monotonic()
        - started
    )

    summary = {
        "program": PROGRAM,
        "version": VERSION,
        "input": str(input_path),
        "output": (
            str(output_path)
            if not args.dry_run
            else None
        ),
        "dry_run": args.dry_run,
        "statistics": (
            stats.projection()
        ),
        "duration_seconds": round(
            duration,
            6,
        ),
        "classifier": (
            "savant_extraction_classifier"
        ),
        "optional_acceleration": {
            "ijson": (
                ijson is not None
            ),
            "orjson": (
                orjson is not None
            ),
        },
    }

    if (
        not args.dry_run
        and args.receipt
    ):
        receipt_path = write_receipt(
            output_path=output_path,
            input_path=input_path,
            stats=stats,
            args=args,
            started_at=started_at,
            duration_seconds=(
                duration
            ),
        )

        summary["receipt"] = str(
            receipt_path
        )

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return 0


def self_test() -> int:
    fixture = [
        {
            "id": "conv-test-1",
            "conversation_id": (
                "conv-test-1"
            ),
            "title": (
                "Savant architecture"
            ),
            "create_time": 1760000000,
            "update_time": 1760000100,
            "current_node": "n3",
            "mapping": {
                "n1": {
                    "parent": None,
                    "children": ["n2"],
                    "message": {
                        "id": "m1",
                        "author": {
                            "role": "user",
                        },
                        "create_time": (
                            1760000000
                        ),
                        "content": {
                            "content_type": (
                                "text"
                            ),
                            "parts": [
                                (
                                    "Implement Savant "
                                    "authority graph."
                                )
                            ],
                        },
                    },
                },
                "n2": {
                    "parent": "n1",
                    "children": ["n3"],
                    "message": {
                        "id": "m2",
                        "author": {
                            "role": (
                                "assistant"
                            ),
                        },
                        "create_time": (
                            1760000010
                        ),
                        "content": {
                            "content_type": (
                                "text"
                            ),
                            "parts": [
                                (
                                    "Palaver delegates "
                                    "persona to Envoy."
                                )
                            ],
                        },
                    },
                },
                "n3": {
                    "parent": "n2",
                    "children": [],
                    "message": {
                        "id": "m3",
                        "author": {
                            "role": "user",
                        },
                        "create_time": (
                            1760000020
                        ),
                        "content": {
                            "content_type": (
                                "text"
                            ),
                            "parts": [
                                (
                                    "Completely unrelated "
                                    "grocery list."
                                )
                            ],
                        },
                    },
                },
            },
        }
    ]

    with tempfile.TemporaryDirectory(
        prefix=(
            "extract-savant-selftest-"
        )
    ) as directory:
        root = Path(directory)

        source = (
            root
            / "conversations.json"
        )

        destination = (
            root
            / "output.jsonl"
        )

        source.write_text(
            json.dumps(
                fixture,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        parser = build_parser()

        args = parser.parse_args(
            [
                str(source),
                str(destination),
                "--context-window",
                "0",
                "--no-receipt",
            ]
        )

        result = run_extraction(
            args
        )

        if result != 0:
            raise ExtractorError(
                "self-test extraction failed"
            )

        lines = [
            json.loads(line)
            for line in (
                destination.read_text(
                    encoding="utf-8"
                ).splitlines()
            )
            if line.strip()
        ]

        ids = {
            row["message_id"]
            for row in lines
        }

        if not {
            "m1",
            "m2",
        }.issubset(ids):
            raise ExtractorError(
                "self-test expected Savant "
                "messages were not extracted"
            )

        if "m3" in ids:
            raise ExtractorError(
                "self-test unrelated message "
                "was incorrectly extracted"
            )

        print(
            json.dumps(
                {
                    "ok": True,
                    "program": PROGRAM,
                    "version": VERSION,
                    "messages": len(lines),
                    "branch_reconstruction": True,
                    "classifier": (
                        "savant_extraction_classifier"
                    ),
                    "jsonl": True,
                },
                indent=2,
                sort_keys=True,
            )
        )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=(
            "High-fidelity Savant extraction "
            "from ChatGPT conversations.json."
        ),
    )

    parser.add_argument(
        "input",
        nargs="?",
    )

    parser.add_argument(
        "output",
        nargs="?",
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
    )

    parser.add_argument(
        "--branch",
        choices=(
            "all",
            "current",
        ),
        default=DEFAULT_BRANCH_MODE,
    )

    parser.add_argument(
        "--context-window",
        type=int,
        default=(
            DEFAULT_CONTEXT_WINDOW
        ),
    )

    parser.add_argument(
        "--include",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--role",
        dest="roles",
        action="append",
        choices=tuple(
            sorted(ROLE_VALUES)
        ),
    )

    parser.add_argument(
        "--after",
    )

    parser.add_argument(
        "--before",
    )

    parser.add_argument(
        "--min-length",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--fuzzy",
        action="store_true",
    )

    parser.add_argument(
        "--fuzzy-cutoff",
        type=int,
        default=94,
    )

    parser.add_argument(
        "--preserve-raw",
        action="store_true",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
    )

    parser.add_argument(
        "--max-errors",
        type=int,
        default=DEFAULT_MAX_ERRORS,
    )

    parser.add_argument(
        "--progress-interval",
        type=int,
        default=(
            DEFAULT_PROGRESS_INTERVAL
        ),
    )

    parser.add_argument(
        "--receipt",
        action=(
            argparse.BooleanOptionalAction
        ),
        default=True,
    )

    parser.add_argument(
        "--dependencies",
        action="store_true",
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"%(prog)s {VERSION}"
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.dependencies:
        print(
            json.dumps(
                dependency_status(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                default=str,
            )
        )
        return 0

    if args.self_test:
        return self_test()

    if not args.input:
        parser.error(
            "input is required unless "
            "--self-test or --dependencies "
            "is used"
        )

    if args.threshold < 0:
        parser.error(
            "--threshold must be >= 0"
        )

    if args.context_window < 0:
        parser.error(
            "--context-window must be >= 0"
        )

    if not (
        0
        <= args.fuzzy_cutoff
        <= 100
    ):
        parser.error(
            "--fuzzy-cutoff must be "
            "between 0 and 100"
        )

    if (
        args.min_length is not None
        and args.min_length < 0
    ):
        parser.error(
            "--min-length must be >= 0"
        )

    if (
        args.max_length is not None
        and args.max_length < 0
    ):
        parser.error(
            "--max-length must be >= 0"
        )

    if (
        args.min_length is not None
        and args.max_length is not None
        and args.min_length
        > args.max_length
    ):
        parser.error(
            "--min-length must not exceed "
            "--max-length"
        )

    try:
        return run_extraction(args)
    except KeyboardInterrupt:
        print(
            "[aborted] interrupted",
            file=sys.stderr,
        )
        return 130
    except (
        ExtractorError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"[error] {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
