from __future__ import annotations

from typing import Any, Dict


def attachment(
    *,
    id: str,
    type: str,
    uri: str,
    mime_type: str | None = None,
    role: str | None = None,
    **extra: Any
) -> Dict[str, Any]:
    return {
        "id": id,
        "type": type,
        "uri": uri,
        "mime_type": mime_type,
        "role": role,
        **extra
    }
