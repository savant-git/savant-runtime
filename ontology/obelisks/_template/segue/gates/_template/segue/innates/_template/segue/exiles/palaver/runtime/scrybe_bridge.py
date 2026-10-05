#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
).resolve()

ROOT_TEXT = str(
    ROOT
)

if ROOT_TEXT not in sys.path:
    sys.path.insert(
        0,
        ROOT_TEXT,
    )


from runtime.constitution import ConstitutionalRegistry
from runtime.scrybe import Scrybe


DEFAULT_INSTANCE = "lore"
DEFAULT_LIMIT = 8

# PALAVER_SCRYBE_CONTEXT_RECEIPT_V1
_LAST_CONTEXT_RECEIPT: ContextVar[
    dict[str, Any] | None
] = ContextVar(
    "palaver_scrybe_context_receipt",
    default=None,
)


class PalaverScrybeError(
    RuntimeError
):
    pass


def hydrate(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    at: str | None = None,
) -> dict[str, Any]:
    value = str(
        query
        or ""
    ).strip()

    if not value:
        raise PalaverScrybeError(
            "context query is empty"
        )

    if limit < 0:
        raise PalaverScrybeError(
            "context limit must be non-negative"
        )

    registry = ConstitutionalRegistry.load(
        ROOT
    )

    scrybe = Scrybe.install(
        registry,
        instance=DEFAULT_INSTANCE,
    )

    packet = scrybe.hydrate(
        value,
        limit=limit,
        at=at,
    )

    if not isinstance(
        packet,
        dict,
    ):
        raise PalaverScrybeError(
            "Scrybe returned invalid context packet"
        )

    if packet.get(
        "authoritative"
    ) is not False:
        raise PalaverScrybeError(
            "Scrybe context became authoritative"
        )

    if packet.get(
        "rebuildable"
    ) is not True:
        raise PalaverScrybeError(
            "Scrybe context is not rebuildable"
        )

    if int(
        packet.get(
            "memory_count",
            0,
        )
    ) > limit:
        raise PalaverScrybeError(
            "Scrybe context exceeded requested bound"
        )

    _LAST_CONTEXT_RECEIPT.set(
        {
            "owner": "scrybe",
            "instance_id": packet.get(
                "instance_id"
            ),
            "canonical_memory_store": (
                "fluid-canon"
            ),
            "digest": packet.get(
                "digest"
            ),
            "memory_count": int(
                packet.get(
                    "memory_count",
                    0,
                )
            ),
            "limit": int(
                packet.get(
                    "limit",
                    limit,
                )
            ),
            "authoritative": False,
            "rebuildable": True,
        }
    )

    return packet


def context_receipt() -> dict[str, Any] | None:
    value = _LAST_CONTEXT_RECEIPT.get()

    if value is None:
        return None

    return dict(value)


def clear_context_receipt() -> None:
    _LAST_CONTEXT_RECEIPT.set(
        None
    )


def _memory_line(
    item: dict[str, Any],
) -> str:
    memory = item.get(
        "memory"
    )

    if not isinstance(
        memory,
        dict,
    ):
        memory = {}

    identity = str(
        memory.get(
            "identity",
            "unknown",
        )
    )

    memory_type = str(
        memory.get(
            "memory_type",
            "unknown",
        )
    )

    content = memory.get(
        "content"
    )

    authority = memory.get(
        "authority"
    )

    confidence = memory.get(
        "confidence"
    )

    provenance = memory.get(
        "provenance"
    )

    validity = memory.get(
        "validity"
    )

    supersession = memory.get(
        "supersession"
    )

    score = item.get(
        "score"
    )

    rank = item.get(
        "rank"
    )

    return "\n".join(
        (
            f"[memory rank={rank} id={identity} type={memory_type}]",
            f"content: {content}",
            f"score: {score}",
            "authority: "
            + json.dumps(
                authority,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
            f"confidence: {confidence}",
            "validity: "
            + json.dumps(
                validity,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
            "supersession: "
            + json.dumps(
                supersession,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
            "provenance: "
            + json.dumps(
                provenance,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
        )
    )


def prompt_block(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    at: str | None = None,
) -> str:
    packet = hydrate(
        query,
        limit=limit,
        at=at,
    )

    memories = packet.get(
        "memories"
    )

    if not isinstance(
        memories,
        (
            list,
            tuple,
        ),
    ):
        memories = ()

    if not memories:
        return ""

    lines = [
        "SCRYBE MEMORY CONTEXT",
        "authority: non-authoritative projection",
        "canonical_store: fluid-canon",
        f"instance: {packet.get('instance_id')}",
        f"digest: {packet.get('digest')}",
        f"limit: {packet.get('limit')}",
        f"memory_count: {packet.get('memory_count')}",
        "",
    ]

    for item in memories:
        if isinstance(
            item,
            dict,
        ):
            lines.append(
                _memory_line(
                    item
                )
            )

            lines.append(
                ""
            )

    return "\n".join(
        lines
    ).strip()


def integration_status() -> dict[str, Any]:
    registry = ConstitutionalRegistry.load(
        ROOT
    )

    scrybe = Scrybe.install(
        registry,
        instance=DEFAULT_INSTANCE,
    )

    return {
        "owner": "palaver",
        "delegates_memory_context_to": "scrybe",
        "scrybe_instance": (
            scrybe.instance.instance_id
        ),
        "canon_owner": "lore",
        "canonical_memory_store": (
            scrybe.instance.canonical_memory_store
        ),
        "independent_memory_store": (
            scrybe.instance.independent_memory_store
        ),
        "context_authoritative": False,
        "context_rebuildable": True,
        "default_limit": DEFAULT_LIMIT,
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            integration_status(),
            indent=2,
            sort_keys=True,
        )
    )
