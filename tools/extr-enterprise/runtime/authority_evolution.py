#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping


schema = "savant://runtime/sieve/authority-evolution/1.0.0"
selftest_schema = (
    "savant://runtime/sieve/authority-evolution-selftest/1.0.0"
)
owner = "sieve"
authority_effect = "none"

candidate_states = (
    "alternate-branch-evidence",
    "user-supersession-candidate",
    "user-rejection-candidate",
    "user-acceptance-candidate",
    "user-directive-candidate",
    "assistant-proposal",
    "example-or-hypothetical",
    "question-or-request",
    "ordinary-discussion",
)

state_precedence = candidate_states


class authority_evolution_error(RuntimeError):
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


def normalized_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.strip().casefold(),
    )


def contains_any(
    value: str,
    patterns: Iterable[str],
) -> bool:
    return any(
        re.search(pattern, value, re.IGNORECASE)
        is not None
        for pattern in patterns
    )


supersession_patterns = (
    r"\bsupersed(?:e|es|ed|ing)\b",
    r"\breplace(?:d|s|ment|ing)?\b",
    r"\binstead of\b",
    r"\bfrom now on\b",
    r"\bno longer\b",
    r"\bchange\b.{0,80}\bto\b",
    r"\brename\b.{0,80}\bto\b",
)

rejection_patterns = (
    r"^\s*no\b",
    r"\breject(?:ed|ing)?\b",
    r"\bdo not use\b",
    r"\bdon't use\b",
    r"\bdo not keep\b",
    r"\bdon't keep\b",
    r"\bforget (?:that|it|the)\b",
    r"\bnot that\b",
    r"\bremove (?:that|it|the)\b",
)

acceptance_patterns = (
    r"^\s*accepted\b",
    r"^\s*approved\b",
    r"\bthat's correct\b",
    r"\bthat is correct\b",
    r"\bgo with (?:that|this)\b",
    r"\bkeep (?:that|this)\b",
    r"\bmake (?:that|this) canonical\b",
)

directive_patterns = (
    r"^\s*(?:use|keep|make|change|rename|replace|remove|add|set|store|preserve|implement|build|create|treat|never|always|continue|do)\b",
    r"\bmust\b",
    r"\bshall\b",
    r"\bno exceptions\b",
)

proposal_patterns = (
    r"\bi (?:recommend|suggest|propose)\b",
    r"\bwe could\b",
    r"\bwe can\b",
    r"\bone option\b",
    r"\bpossible approach\b",
)

example_patterns = (
    r"\bfor example\b",
    r"\be\.g\.\b",
    r"\bhypothetical(?:ly)?\b",
    r"\bexample only\b",
    r"\bsample only\b",
    r"\bimagine that\b",
)

question_patterns = (
    r"\?\s*$",
    r"^\s*(?:what|why|how|when|where|which|who|can|could|would|should|is|are|do|does|did)\b",
)


def message_role(
    row: Mapping[str, Any],
) -> str | None:
    message = row.get(
        "message"
    )

    if not isinstance(
        message,
        Mapping,
    ):
        return None

    author = message.get(
        "author"
    )

    if not isinstance(
        author,
        Mapping,
    ):
        return None

    role = author.get(
        "role"
    )

    return (
        str(role)
        if role is not None
        else None
    )


def current_branch(
    row: Mapping[str, Any],
) -> bool | None:
    graph = row.get(
        "graph"
    )

    if not isinstance(
        graph,
        Mapping,
    ):
        return None

    value = graph.get(
        "is_current_branch"
    )

    return (
        value
        if isinstance(
            value,
            bool,
        )
        else None
    )


def message_time(
    row: Mapping[str, Any],
) -> float | None:
    message = row.get(
        "message"
    )

    if not isinstance(
        message,
        Mapping,
    ):
        return None

    value = message.get(
        "create_time"
    )

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
        return float(
            value
        )

    return None


def classify_message(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        row,
        Mapping,
    ):
        raise authority_evolution_error(
            "message projection row must be an object"
        )

    row_schema = row.get(
        "schema"
    )

    if (
        row_schema
        != "savant://runtime/sieve/chatgpt-message/1.0.0"
    ):
        raise authority_evolution_error(
            "unsupported message schema: "
            f"{row_schema!r}"
        )

    text = row.get(
        "text"
    )

    if not isinstance(
        text,
        str,
    ):
        text = ""

    normalized = normalized_text(
        text
    )

    role = message_role(
        row
    )

    branch = current_branch(
        row
    )

    signals: list[str] = []

    if branch is False:
        signals.append(
            "alternate-branch-evidence"
        )

    if role == "user":
        if contains_any(
            normalized,
            supersession_patterns,
        ):
            signals.append(
                "user-supersession-candidate"
            )

        if contains_any(
            normalized,
            rejection_patterns,
        ):
            signals.append(
                "user-rejection-candidate"
            )

        if contains_any(
            normalized,
            acceptance_patterns,
        ):
            signals.append(
                "user-acceptance-candidate"
            )

        if contains_any(
            normalized,
            directive_patterns,
        ):
            signals.append(
                "user-directive-candidate"
            )

    if (
        role == "assistant"
        and contains_any(
            normalized,
            proposal_patterns,
        )
    ):
        signals.append(
            "assistant-proposal"
        )

    if contains_any(
        normalized,
        example_patterns,
    ):
        signals.append(
            "example-or-hypothetical"
        )

    if contains_any(
        normalized,
        question_patterns,
    ):
        signals.append(
            "question-or-request"
        )

    if not signals:
        signals.append(
            "ordinary-discussion"
        )

    unique_signals = tuple(
        state
        for state
        in state_precedence
        if state
        in set(
            signals
        )
    )

    primary_state = (
        unique_signals[
            0
        ]
    )

    authority_candidate = (
        role == "user"
        and branch is not False
        and any(
            state
            in unique_signals
            for state in (
                "user-supersession-candidate",
                "user-rejection-candidate",
                "user-acceptance-candidate",
                "user-directive-candidate",
            )
        )
    )

    evolution_candidate = any(
        state
        in unique_signals
        for state in (
            "user-supersession-candidate",
            "user-rejection-candidate",
            "user-acceptance-candidate",
        )
    )

    semantic_review_required = (
        authority_candidate
        or evolution_candidate
        or (
            "assistant-proposal"
            in unique_signals
        )
    )

    source_id = row.get(
        "id"
    )

    result = {
        "schema":
            (
                "savant://runtime/sieve/"
                "authority-evolution-candidate/1.0.0"
            ),
        "id":
            (
                "sieve:authority-evolution:"
                + digest(
                    {
                        "source_message_projection_id":
                            source_id,
                        "text_sha256":
                            text_digest(
                                text
                            ),
                        "signals":
                            unique_signals,
                    }
                )
            ),
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "authoritative":
            False,
        "admission_eligible":
            False,
        "classification_basis":
            (
                "deterministic-explicit-"
                "message-and-branch-signals-only"
            ),
        "source_message_projection_id":
            source_id,
        "source_message_schema":
            row_schema,
        "source_text_sha256":
            text_digest(
                text
            ),
        "conversation_id":
            (
                row.get(
                    "conversation",
                    {},
                ).get(
                    "id"
                )
                if isinstance(
                    row.get(
                        "conversation"
                    ),
                    Mapping,
                )
                else None
            ),
        "node_id":
            (
                row.get(
                    "graph",
                    {},
                ).get(
                    "node_id"
                )
                if isinstance(
                    row.get(
                        "graph"
                    ),
                    Mapping,
                )
                else None
            ),
        "message_id":
            (
                row.get(
                    "message",
                    {},
                ).get(
                    "id"
                )
                if isinstance(
                    row.get(
                        "message"
                    ),
                    Mapping,
                )
                else None
            ),
        "role":
            role,
        "create_time":
            message_time(
                row
            ),
        "is_current_branch":
            branch,
        "primary_state":
            primary_state,
        "candidate_states":
            list(
                unique_signals
            ),
        "authority_candidate":
            authority_candidate,
        "evolution_candidate":
            evolution_candidate,
        "semantic_review_required":
            semantic_review_required,
        "reconciliation_required":
            authority_candidate,
        "lineage":
            {
                "source_message_projection_id":
                    source_id,
                "source_text_sha256":
                    text_digest(
                        text
                    ),
            },
    }

    return result


def read_jsonl(
    path: Path,
) -> list[
    dict[
        str,
        Any,
    ]
]:
    if not path.is_file():
        raise authority_evolution_error(
            "messages JSONL unavailable: "
            f"{path}"
        )

    rows: list[
        dict[
            str,
            Any,
        ]
    ] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for (
            line_number,
            line,
        ) in enumerate(
            handle,
            1,
        ):
            if not line.strip():
                continue

            try:
                value = json.loads(
                    line
                )

            except Exception as exc:
                raise authority_evolution_error(
                    "invalid JSONL at line "
                    f"{line_number}"
                ) from exc

            if not isinstance(
                value,
                dict,
            ):
                raise authority_evolution_error(
                    "JSONL row must be an "
                    "object at line "
                    f"{line_number}"
                )

            rows.append(
                value
            )

    return rows


def project_rows(
    rows: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> list[
    dict[
        str,
        Any,
    ]
]:
    projected = [
        classify_message(
            row
        )
        for row in rows
    ]

    projected.sort(
        key=lambda row: (
            row[
                "create_time"
            ]
            is None,
            row[
                "create_time"
            ]
            or 0.0,
            str(
                row[
                    "conversation_id"
                ]
                or ""
            ),
            str(
                row[
                    "node_id"
                ]
                or ""
            ),
            str(
                row[
                    "message_id"
                ]
                or ""
            ),
        )
    )

    return projected


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
            for row in rows
        )
    ).encode(
        "utf-8"
    )


def manifest_value(
    source: Path,
    rows: list[
        dict[
            str,
            Any,
        ]
    ],
    payload: bytes,
) -> dict[
    str,
    Any,
]:
    counts: dict[
        str,
        int,
    ] = {}

    for row in rows:
        state = row[
            "primary_state"
        ]

        counts[
            state
        ] = (
            counts.get(
                state,
                0,
            )
            + 1
        )

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
        "admission_eligible":
            False,
        "classification_basis":
            (
                "deterministic-explicit-"
                "message-and-branch-signals-only"
            ),
        "source":
            {
                "path":
                    str(
                        source.resolve()
                    ),
                "sha256":
                    hashlib.sha256(
                        source.read_bytes()
                    ).hexdigest(),
            },
        "counts":
            {
                "records":
                    len(
                        rows
                    ),
                "authority_candidates":
                    sum(
                        1
                        for row
                        in rows
                        if row[
                            "authority_candidate"
                        ]
                    ),
                "evolution_candidates":
                    sum(
                        1
                        for row
                        in rows
                        if row[
                            "evolution_candidate"
                        ]
                    ),
                "semantic_review_required":
                    sum(
                        1
                        for row
                        in rows
                        if row[
                            "semantic_review_required"
                        ]
                    ),
                "by_primary_state":
                    dict(
                        sorted(
                            counts.items()
                        )
                    ),
            },
        "output":
            {
                "authority_evolution.jsonl":
                    {
                        "sha256":
                            hashlib.sha256(
                                payload
                            ).hexdigest(),
                        "records":
                            len(
                                rows
                            ),
                    }
            },
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
    messages: Path,
    output: Path,
) -> dict[
    str,
    Any,
]:
    rows = read_jsonl(
        messages
    )

    projected = project_rows(
        rows
    )

    payload = jsonl_bytes(
        projected
    )

    manifest = manifest_value(
        messages,
        projected,
        payload,
    )

    atomic_write(
        output
        / "authority_evolution.jsonl",
        payload,
    )

    atomic_write(
        output
        / "manifest.json",
        (
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode(
            "utf-8"
        ),
    )

    return manifest


def test_message(
    ordinal: int,
    role: str,
    text: str,
    *,
    current: bool = True,
) -> dict[
    str,
    Any,
]:
    return {
        "schema":
            (
                "savant://runtime/sieve/"
                "chatgpt-message/1.0.0"
            ),
        "id":
            (
                "message-projection-"
                f"{ordinal}"
            ),
        "owner":
            "sieve",
        "authority_effect":
            "none",
        "authoritative":
            False,
        "conversation":
            {
                "id":
                    "conversation-test",
            },
        "graph":
            {
                "node_id":
                    f"node-{ordinal}",
                "is_current_branch":
                    current,
            },
        "message":
            {
                "id":
                    f"message-{ordinal}",
                "author":
                    {
                        "role":
                            role,
                    },
                "create_time":
                    float(
                        ordinal
                    ),
            },
        "text":
            text,
    }


def selftest() -> dict[
    str,
    Any,
]:
    rows = [
        test_message(
            1,
            "user",
            (
                "Use glyph as the atomic "
                "programming level. "
                "No exceptions."
            ),
        ),
        test_message(
            2,
            "user",
            (
                "No, reject that. "
                "Replace hierarchy with "
                "edifice from now on."
            ),
        ),
        test_message(
            3,
            "assistant",
            (
                "I recommend adding "
                "a second database."
            ),
        ),
        test_message(
            4,
            "user",
            (
                "For example, imagine "
                "that a sea is level nine."
            ),
        ),
        test_message(
            5,
            "user",
            (
                "What should we call "
                "this layer?"
            ),
        ),
        test_message(
            6,
            "user",
            (
                "Use obsolete-name "
                "as canonical."
            ),
            current=False,
        ),
        test_message(
            7,
            "user",
            (
                "I was listening to "
                "music today."
            ),
        ),
        test_message(
            8,
            "user",
            (
                "Accepted. "
                "Go with this."
            ),
        ),
    ]

    first = project_rows(
        rows
    )

    second = project_rows(
        rows
    )

    by_message = {
        row[
            "message_id"
        ]:
            row
        for row
        in first
    }

    checks = {
        "authority_none":
            (
                authority_effect
                == "none"
            ),

        "deterministic":
            (
                first
                == second
            ),

        "directive_candidate":
            (
                by_message[
                    "message-1"
                ][
                    "authority_candidate"
                ]
                is True
                and (
                    "user-directive-candidate"
                    in by_message[
                        "message-1"
                    ][
                        "candidate_states"
                    ]
                )
            ),

        "supersession_candidate":
            (
                by_message[
                    "message-2"
                ][
                    "primary_state"
                ]
                == (
                    "user-supersession-"
                    "candidate"
                )
                and by_message[
                    "message-2"
                ][
                    "evolution_candidate"
                ]
                is True
            ),

        "rejection_preserved":
            (
                "user-rejection-candidate"
                in by_message[
                    "message-2"
                ][
                    "candidate_states"
                ]
            ),

        "assistant_proposal_not_authority":
            (
                by_message[
                    "message-3"
                ][
                    "primary_state"
                ]
                == "assistant-proposal"
                and by_message[
                    "message-3"
                ][
                    "authority_candidate"
                ]
                is False
            ),

        "example_not_authority":
            (
                by_message[
                    "message-4"
                ][
                    "primary_state"
                ]
                == "example-or-hypothetical"
                and by_message[
                    "message-4"
                ][
                    "authority_candidate"
                ]
                is False
            ),

        "question_preserved":
            (
                by_message[
                    "message-5"
                ][
                    "primary_state"
                ]
                == "question-or-request"
            ),

        "alternate_branch_suppressed":
            (
                by_message[
                    "message-6"
                ][
                    "primary_state"
                ]
                == "alternate-branch-evidence"
                and by_message[
                    "message-6"
                ][
                    "authority_candidate"
                ]
                is False
            ),

        "ordinary_preserved":
            (
                by_message[
                    "message-7"
                ][
                    "primary_state"
                ]
                == "ordinary-discussion"
            ),

        "acceptance_candidate":
            (
                by_message[
                    "message-8"
                ][
                    "primary_state"
                ]
                == (
                    "user-acceptance-"
                    "candidate"
                )
                and by_message[
                    "message-8"
                ][
                    "authority_candidate"
                ]
                is True
            ),

        "nothing_admitted":
            all(
                (
                    row[
                        "admission_eligible"
                    ]
                    is False
                    and row[
                        "authoritative"
                    ]
                    is False
                )
                for row
                in first
            ),

        "reconciliation_required_for_authority":
            all(
                (
                    not row[
                        "authority_candidate"
                    ]
                    or row[
                        "reconciliation_required"
                    ]
                    is True
                )
                for row
                in first
            ),
    }

    return {
        "schema":
            selftest_schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "count":
            len(
                first
            ),
    }


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "messages",
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

    if arguments.messages is None:
        parser.error(
            "messages.jsonl is required"
        )

    if arguments.output is None:
        parser.error(
            "--output is required"
        )

    try:
        manifest = write_projection(
            arguments.messages,
            arguments.output,
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
