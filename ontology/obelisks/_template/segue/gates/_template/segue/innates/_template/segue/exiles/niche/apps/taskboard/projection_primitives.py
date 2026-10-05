from __future__ import annotations

import hashlib
import json
from typing import Any


schema = "savant.niche.taskboard.projection-primitives.v1"


def canonical_digest(
    value: Any,
) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()
