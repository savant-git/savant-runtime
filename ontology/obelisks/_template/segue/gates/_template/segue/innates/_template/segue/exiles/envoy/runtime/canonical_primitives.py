from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


schema = "savant.envoy.canonical-primitives.v1"


def canonical(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


_canonical = canonical


def digest(
    value: Any,
) -> str:
    return sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()

