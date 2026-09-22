#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

CHAT_ROOT = (
    ROOT
    / "vault"
    / "web_chats"
)

OWNER = "palaver"

SCHEMA = (
    "savant.palaver.conversation-context.v1"
)

DEFAULT_TURN_LIMIT = 12
MAX_TURN_LIMIT = 40
MAX_CONTENT_CHARS = 48000


class ConversationBridgeError(
    RuntimeError
):
    pass


def _bounded_limit(
    limit: int,
) -> int:
    try:
        value = int(limit)
    except (
        TypeError,
        ValueError,
    ):
        value = DEFAULT_TURN_LIMIT

    return max(
        0,
        min(
            value,
            MAX_TURN_LIMIT,
        ),
    )


def _chat_files(
    limit: int,
) -> list[Path]:
    if limit <= 0:
        return []

    if not CHAT_ROOT.exists():
        return []

    if not CHAT_ROOT.is_dir():
        raise ConversationBridgeError(
            "Palaver chat history path "
            "is not a directory"
        )

    files = sorted(
        (
            path
            for path in CHAT_ROOT.glob(
                "*.json"
            )
            if path.is_file()
        ),
        key=lambda path: path.name,
    )

    return files[
        -limit:
    ]


def _load_turn(
    path: Path,
) -> dict[str, Any] | None:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        value,
        dict,
    ):
        return None

    user = str(
        value.get(
            "user",
            "",
        )
        or ""
    ).strip()

    assistant = str(
        value.get(
            "assistant",
            "",
        )
        or ""
    ).strip()

    if (
        not user
        and not assistant
    ):
        return None

    return {
        "timestamp": str(
            value.get(
                "timestamp",
                "",
            )
            or ""
        ).strip(),
        "user": user,
        "assistant": assistant,
        "source": str(
            path.relative_to(
                ROOT
            )
        ),
    }


def recent_turns(
    limit: int = DEFAULT_TURN_LIMIT,
) -> list[dict[str, Any]]:
    bounded = _bounded_limit(
        limit
    )

    turns: list[
        dict[str, Any]
    ] = []

    for path in _chat_files(
        bounded
    ):
        turn = _load_turn(
            path
        )

        if turn is not None:
            turns.append(
                turn
            )

    return turns


def prompt_block(
    *,
    limit: int = DEFAULT_TURN_LIMIT,
    max_chars: int = MAX_CONTENT_CHARS,
) -> str:
    turns = recent_turns(
        limit=limit
    )

    if not turns:
        return ""

    try:
        char_limit = int(
            max_chars
        )
    except (
        TypeError,
        ValueError,
    ):
        char_limit = MAX_CONTENT_CHARS

    char_limit = max(
        1024,
        min(
            char_limit,
            MAX_CONTENT_CHARS,
        ),
    )

    header = [
        "PALAVER CONVERSATION CONTEXT",
        f"schema: {SCHEMA}",
        f"owner: {OWNER}",
        "authority: none",
        "canonical: false",
        "purpose: conversational continuity",
        (
            "These are prior Palaver conversation "
            "turns. They are contextual evidence, "
            "not accepted authority and not "
            "fluid-canon memory."
        ),
        "",
    ]

    rendered: list[str] = []

    for index, turn in enumerate(
        turns,
        start=1,
    ):
        rendered.extend(
            [
                (
                    "TURN "
                    f"{index}"
                ),
                (
                    "timestamp: "
                    + str(
                        turn.get(
                            "timestamp",
                            "",
                        )
                    )
                ),
                (
                    "source: "
                    + str(
                        turn.get(
                            "source",
                            "",
                        )
                    )
                ),
                "user:",
                str(
                    turn.get(
                        "user",
                        "",
                    )
                ),
                "assistant:",
                str(
                    turn.get(
                        "assistant",
                        "",
                    )
                ),
                "",
            ]
        )

    block = "\n".join(
        header
        + rendered
    ).strip()

    if len(block) <= char_limit:
        return block

    body_budget = max(
        0,
        char_limit
        - 256,
    )

    truncated = block[
        -body_budget:
    ]

    return "\n".join(
        [
            "PALAVER CONVERSATION CONTEXT",
            f"schema: {SCHEMA}",
            f"owner: {OWNER}",
            "authority: none",
            "canonical: false",
            (
                "Earlier context was truncated "
                "to satisfy the bounded "
                "conversation-context limit."
            ),
            "",
            truncated,
        ]
    )


def projection(
    limit: int = DEFAULT_TURN_LIMIT,
) -> dict[str, Any]:
    turns = recent_turns(
        limit=limit
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "store": str(
            CHAT_ROOT.relative_to(
                ROOT
            )
        ),
        "turn_count": len(
            turns
        ),
        "turn_limit": _bounded_limit(
            limit
        ),
        "canonical": False,
        "authoritative": False,
        "rebuildable": True,
        "fluid_canon_owner": False,
        "conversation_context_ready": True,
    }


def selftest() -> dict[str, Any]:
    result = projection()

    if result[
        "owner"
    ] != OWNER:
        raise ConversationBridgeError(
            "conversation owner mismatch"
        )

    if result[
        "canonical"
    ] is not False:
        raise ConversationBridgeError(
            "conversation history must "
            "not become canonical"
        )

    if result[
        "authoritative"
    ] is not False:
        raise ConversationBridgeError(
            "conversation history must "
            "remain non-authoritative"
        )

    if result[
        "fluid_canon_owner"
    ] is not False:
        raise ConversationBridgeError(
            "conversation bridge crossed "
            "fluid-canon authority boundary"
        )

    return {
        "ok": True,
        **result,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
