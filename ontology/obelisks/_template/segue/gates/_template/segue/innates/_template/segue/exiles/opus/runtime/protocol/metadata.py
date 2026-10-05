from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "req") -> str:
    return f"{prefix}_{uuid4().hex}"


def timestamps() -> Dict[str, str]:
    now = utc_now()
    return {
        "created_utc": now,
        "updated_utc": now
    }


def metadata(**values: Any) -> Dict[str, Any]:
    return {
        "runtime": "savant",
        "protocol": "runtime_request_v1",
        **values
    }
