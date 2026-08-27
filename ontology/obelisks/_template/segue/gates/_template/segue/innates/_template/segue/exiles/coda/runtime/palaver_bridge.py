#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from mutation import (
    MutationConflict,
    MutationError,
    replace_text,
    status as mutation_status,
)


OWNER = "coda"
CALLER = "palaver"
ROOT = Path("/root/savant-runtime").resolve()

SCHEMA = "savant.coda.palaver-mutation-bridge.v1"


class CodaPalaverBridgeError(RuntimeError):
    pass


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _request(
    value: Any,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise CodaPalaverBridgeError(
            "mutation request must be an object"
        )

    return value


def replace_file(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    value = _request(
        request
    )

    path = _text(
        value.get(
            "path"
        )
    )

    if not path:
        raise CodaPalaverBridgeError(
            "mutation path is required"
        )

    if "content" not in value:
        raise CodaPalaverBridgeError(
            "mutation content is required"
        )

    content = value[
        "content"
    ]

    if not isinstance(
        content,
        str,
    ):
        raise CodaPalaverBridgeError(
            "mutation content must be text"
        )

    expected_digest_value = (
        value.get(
            "expected_digest"
        )
    )

    expected_digest = (
        _text(
            expected_digest_value
        )
        if expected_digest_value
        is not None
        else None
    )

    intent = (
        _text(
            value.get(
                "intent"
            )
        )
        or "palaver authorized file replacement"
    )

    try:
        result = replace_text(
            path,
            content,
            expected_digest=expected_digest,
            requester=CALLER,
            intent=intent,
        )
    except MutationConflict:
        raise
    except MutationError:
        raise
    except Exception as exc:
        raise CodaPalaverBridgeError(
            f"coda mutation failed: {exc}"
        ) from exc

    return {
        "schema": SCHEMA,
        "ok": True,
        "owner": OWNER,
        "caller": CALLER,
        "operation": "replace_text",
        "authority_effect": "none",
        "result": result,
    }


def bridge_status() -> dict[str, Any]:
    mutation = mutation_status()

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "caller": CALLER,
        "mutation_owner": OWNER,
        "mutation_operation": (
            mutation.get(
                "operation"
            )
        ),
        "atomic": (
            mutation.get(
                "atomic"
            )
        ),
        "optimistic_concurrency": (
            mutation.get(
                "optimistic_concurrency"
            )
        ),
        "digest_verification": (
            mutation.get(
                "digest_verification"
            )
        ),
        "receipts": (
            mutation.get(
                "receipts"
            )
        ),
        "authority_effect": "none",
        "ready": True,
    }


def selftest() -> dict[str, Any]:
    status = bridge_status()

    if status[
        "owner"
    ] != OWNER:
        raise CodaPalaverBridgeError(
            "coda ownership boundary failed"
        )

    if status[
        "caller"
    ] != CALLER:
        raise CodaPalaverBridgeError(
            "palaver caller boundary failed"
        )

    if (
        status[
            "authority_effect"
        ]
        != "none"
    ):
        raise CodaPalaverBridgeError(
            "bridge may not create authority"
        )

    if not status[
        "atomic"
    ]:
        raise CodaPalaverBridgeError(
            "atomic mutation unavailable"
        )

    if not status[
        "digest_verification"
    ]:
        raise CodaPalaverBridgeError(
            "digest verification unavailable"
        )

    return {
        "ok": True,
        **status,
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
