from __future__ import annotations

import hashlib
import json
from typing import Any


schema = "savant.envoy.trait-primitives.v1"


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def normalize_term(
    value: Any,
) -> str:
    return (
        str(
            value
            or ""
        )
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )
