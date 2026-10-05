from __future__ import annotations

from .idempotency import (
    project,
)
from .idempotency_guard import (
    idempotency_conflict_error,
    require_compatible,
)


def main() -> None:
    first = project(
        {
            "tenant_id": "tenant-a",
            "client_key_id": "key-a",
            "idempotency_key": "job-1",
            "messages": [
                {
                    "role": "user",
                    "content": "alpha",
                }
            ],
        }
    )

    same = project(
        {
            "tenant_id": "tenant-a",
            "client_key_id": "key-a",
            "idempotency_key": "job-1",
            "messages": [
                {
                    "role": "user",
                    "content": "alpha",
                }
            ],
        }
    )

    compatible = require_compatible(
        first,
        same,
    )

    assert compatible[
        "same_identity"
    ] is True

    assert compatible[
        "same_request"
    ] is True

    assert compatible[
        "conflict"
    ] is False

    changed = project(
        {
            "tenant_id": "tenant-a",
            "client_key_id": "key-a",
            "idempotency_key": "job-1",
            "messages": [
                {
                    "role": "user",
                    "content": "beta",
                }
            ],
        }
    )

    failed = False

    try:
        require_compatible(
            first,
            changed,
        )

    except idempotency_conflict_error:
        failed = True

    assert failed

    print(
        "opus idempotency guard: ok"
    )


if __name__ == "__main__":
    main()
