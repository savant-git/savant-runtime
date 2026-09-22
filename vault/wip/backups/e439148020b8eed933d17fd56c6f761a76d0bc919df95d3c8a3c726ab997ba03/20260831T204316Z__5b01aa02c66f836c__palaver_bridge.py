#!/usr/bin/env python3

from __future__ import annotations

import sys

from pathlib import Path
from typing import Any, Mapping


SAVANT_ROOT = Path(
    "/root/savant-runtime"
).resolve()

if str(
    SAVANT_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            SAVANT_ROOT
        ),
    )


from runtime.living_guard import (  # noqa: E402
    evaluate_change,
    status as guard_status,
)

from mutation import (  # noqa: E402
    MutationConflict,
    MutationError,
    replace_text,
    resolve_target,
    status as mutation_status,
)


OWNER = "coda"
CALLER = "palaver"
ROOT = SAVANT_ROOT

SCHEMA = (
    "savant.coda."
    "palaver-mutation-bridge.v2"
)


class CodaPalaverBridgeError(
    RuntimeError
):
    pass


class CodaGovernanceRejection(
    CodaPalaverBridgeError
):
    def __init__(
        self,
        guard: Mapping[str, Any],
    ) -> None:
        self.guard = dict(
            guard
        )

        super().__init__(
            "living governance rejected coda mutation"
        )


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


def _guard_replacement(
    path: str,
    content: str,
) -> dict[str, Any]:
    target, relative = resolve_target(
        path
    )

    guard = evaluate_change(
        path=str(
            target
        ),
        text=content,
    )

    result = {
        **guard,

        "mutation_owner":
            OWNER,

        "caller":
            CALLER,

        "operation":
            "replace_text",

        "relative_path":
            relative,
    }

    if not result[
        "allowed"
    ]:
        raise CodaGovernanceRejection(
            result
        )

    return result


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
        or (
            "palaver authorized "
            "file replacement"
        )
    )

    governance = _guard_replacement(
        path,
        content,
    )

    try:
        result = replace_text(
            path,
            content,
            expected_digest=
                expected_digest,
            requester=CALLER,
            intent=intent,
        )

    except MutationConflict:
        raise

    except MutationError:
        raise

    except Exception as exc:
        raise CodaPalaverBridgeError(
            (
                "coda mutation failed: "
                f"{exc}"
            )
        ) from exc

    return {
        "schema":
            SCHEMA,

        "ok":
            True,

        "owner":
            OWNER,

        "caller":
            CALLER,

        "operation":
            "replace_text",

        "governance":
            governance,

        "authority_effect":
            "none",

        "result":
            result,
    }


def bridge_status() -> dict[str, Any]:
    mutation = mutation_status()

    guard = guard_status()

    return {
        "schema":
            SCHEMA,

        "owner":
            OWNER,

        "caller":
            CALLER,

        "mutation_owner":
            OWNER,

        "governance_owner":
            guard.get(
                "owner"
            ),

        "governance_effect":
            guard.get(
                "authority_effect"
            ),

        "governance_ready":
            guard.get(
                "ready"
            ),

        "governance_checks":
            guard.get(
                "checks"
            ),

        "atomic_file_writes":
            mutation.get(
                "atomic_file_writes"
            ),

        "optimistic_concurrency":
            mutation.get(
                "optimistic_concurrency"
            ),

        "digest_verification":
            mutation.get(
                "digest_verification"
            ),

        "content_addressed_backups":
            mutation.get(
                "content_addressed_backups"
            ),

        "rollback":
            mutation.get(
                "rollback"
            ),

        "receipts":
            mutation.get(
                "receipts"
            ),

        "mutation_plans":
            mutation.get(
                "mutation_plans"
            ),

        "path_containment":
            mutation.get(
                "path_containment"
            ),

        "protected_paths":
            mutation.get(
                "protected_paths"
            ),

        "authority_effect":
            "none",

        "ready":
            bool(
                mutation.get(
                    "ready"
                )
                and guard.get(
                    "ready"
                )
            ),
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
            "governance_owner"
        ]
        != "living-governance"
    ):
        raise CodaPalaverBridgeError(
            (
                "living governance "
                "ownership boundary failed"
            )
        )

    if (
        status[
            "governance_effect"
        ]
        != "guard"
    ):
        raise CodaPalaverBridgeError(
            (
                "living governance "
                "guard boundary failed"
            )
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

    required = (
        "atomic_file_writes",
        "optimistic_concurrency",
        "digest_verification",
        "content_addressed_backups",
        "rollback",
        "receipts",
        "mutation_plans",
        "path_containment",
        "protected_paths",
        "governance_ready",
    )

    missing = [
        name
        for name
        in required
        if not status.get(
            name
        )
    ]

    if missing:
        raise CodaPalaverBridgeError(
            (
                "required mutation guarantees "
                "unavailable: "
                + ", ".join(
                    missing
                )
            )
        )

    safe_guard = evaluate_change(
        path=(
            "/root/savant-runtime/"
            "runtime/example.py"
        ),
        text=(
            "kindred remains canonical"
        ),
    )

    if not safe_guard[
        "allowed"
    ]:
        raise CodaPalaverBridgeError(
            "valid governance preflight failed"
        )

    escape_guard = evaluate_change(
        path="/tmp/coda-escape",
        text="test",
    )

    if escape_guard[
        "allowed"
    ]:
        raise CodaPalaverBridgeError(
            "runtime containment guard failed"
        )

    return {
        "ok":
            True,

        **status,

        "safe_preflight":
            safe_guard[
                "allowed"
            ],

        "escape_rejected":
            not escape_guard[
                "allowed"
            ],
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
