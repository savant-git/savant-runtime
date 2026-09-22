#!/usr/bin/env python3

from __future__ import annotations

from typing import Any


schema = "savant.palaver.attachment-limits.v1"

owner = "palaver"

max_attachment_bytes = 52_428_800

max_attachment_mib = 50

transport_request_mib = 70


class attachment_limit_error(
    ValueError
):
    pass


def validate_attachment_size(
    size: Any,
) -> int:
    try:
        normalized = int(
            size
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise attachment_limit_error(
            "attachment size must be an integer"
        ) from exc

    if normalized < 0:
        raise attachment_limit_error(
            "attachment size cannot be negative"
        )

    if normalized > max_attachment_bytes:
        raise attachment_limit_error(
            "attachment exceeds Palaver "
            f"{max_attachment_mib} MiB limit"
        )

    return normalized


def projection() -> dict[str, Any]:
    return {
        "schema": schema,
        "owner": owner,
        "max_attachment_bytes": (
            max_attachment_bytes
        ),
        "max_attachment_mib": (
            max_attachment_mib
        ),
        "transport_request_mib": (
            transport_request_mib
        ),
        "authority_effect": "none",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            projection(),
            indent=2,
            sort_keys=True,
        )
    )
