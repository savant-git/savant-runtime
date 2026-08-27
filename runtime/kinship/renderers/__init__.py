#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Mapping

from .ascii_tree import (
    render_ascii_tree,
)
from .dot import render_dot
from .mermaid import render_mermaid


SUPPORTED_FORMATS = {
    "ascii",
    "dot",
    "json",
    "mermaid",
}


def render_family_tree(
    payload: Mapping[str, Any],
    *,
    format_name: str,
    width: int = 120,
) -> str:
    normalized = str(
        format_name
    ).strip().casefold()

    if normalized == "ascii":
        return render_ascii_tree(
            payload,
            width=width,
        )

    if normalized == "dot":
        return render_dot(
            payload
        )

    if normalized == "mermaid":
        return render_mermaid(
            payload
        )

    if normalized == "json":
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    raise ValueError(
        "unsupported family-tree "
        f"format: {format_name}"
    )


__all__ = [
    "SUPPORTED_FORMATS",
    "render_family_tree",
]
