from __future__ import annotations

import json
from typing import Any


schema = "savant.palaver.runtime-json-encoding.v1"


def json_bytes(
    value: dict[str, Any],
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
    ).encode(
        "utf-8"
    )
