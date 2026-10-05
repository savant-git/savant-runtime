from __future__ import annotations

from typing import Any, Dict, Tuple


REQUEST_REQUIRED = [
    "id",
    "type",
    "source",
    "destination",
    "payload",
    "timestamps"
]


def validate_request(obj: Dict[str, Any]) -> Tuple[bool, list[str]]:
    missing = [k for k in REQUEST_REQUIRED if k not in obj]
    return not missing, missing
