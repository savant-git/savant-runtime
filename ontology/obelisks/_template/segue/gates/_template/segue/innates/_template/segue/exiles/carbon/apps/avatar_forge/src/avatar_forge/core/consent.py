from __future__ import annotations

"""
Consent validation for Carbon Avatar Forge.

No simulation that produces or personalizes a digital human should proceed
without explicit user consent.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


VALID_CONSENT = {
    "yes",
    "true",
    "consent",
    "i consent",
    "i explicitly consent",
}


@dataclass(slots=True)
class ConsentRecord:
    granted: bool
    timestamp: str
    source: str
    metadata: dict[str, Any]


def normalize(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return value.strip().lower() in VALID_CONSENT


def create_record(
    value: str | bool | None,
    source: str = "api",
    metadata: dict[str, Any] | None = None,
) -> ConsentRecord:

    return ConsentRecord(
        granted=normalize(value),
        timestamp=datetime.utcnow().isoformat() + "Z",
        source=source,
        metadata=metadata or {},
    )


def require(record: ConsentRecord) -> None:
    if not record.granted:
        raise PermissionError(
            "Explicit consent is required before creating a personalized digital avatar."
        )


def serialize(record: ConsentRecord) -> dict[str, Any]:
    return {
        "granted": record.granted,
        "timestamp": record.timestamp,
        "source": record.source,
        "metadata": record.metadata,
    }
