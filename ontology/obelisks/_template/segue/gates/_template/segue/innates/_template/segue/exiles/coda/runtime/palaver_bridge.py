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


from runtime.living_mutation_policy import (  # noqa: E402
    evaluate_mutation,
    status as governance_status,
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
            (
                "living governance rejected "
                "coda mutation"
            )
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


def _evidence(
    value: Any,
) -> list[Any]:
    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        raise CodaPalaverBridgeError(
            "mutation evidence must be a list"
        )

    return list(
        value
    )


def _guard_replacement(
    *,
    path: str,
    content: str,
    expected_digest: str | None,
    intent: str,
    authority_granted: bool,
    evidence: list[Any],
) -> dict[str, Any]:
    target, relative = resolve_target(
        path
    )

    guard = evaluate_mutation(
        path=str(
            target
        ),
        content=content,
        operation="replace_text",
        caller=CALLER,
        mutation_owner=OWNER,
        relative_path=relative,
        expected_digest=expected_digest,
        intent=intent,
        authority_granted=authority_granted,
        evidence=evidence,
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

    expected_digest_value = value.get(
        "expected_digest"
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

    authority_granted = bool(
        value.get(
            "authority_granted",
            False,
        )
    )

    evidence = _evidence(
        value.get(
            "evidence"
        )
    )

    governance = _guard_replacement(
        path=path,
        content=content,
        expected_digest=expected_digest,
        intent=intent,
        authority_granted=authority_granted,
        evidence=evidence,
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

    governance = governance_status()

    legacy = governance.get(
        "legacy_guard",
        {},
    )

    policy = governance.get(
        "policy_engine",
        {},
    )

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
            governance.get(
                "owner"
            ),

        "governance_effect":
            governance.get(
                "authority_effect"
            ),

        "governance_ready":
            governance.get(
                "ready"
            ),

        "governance_checks":
            legacy.get(
                "checks"
            ),

        "typed_policy_ready":
            policy.get(
                "ready"
            ),

        "typed_policy_count":
            governance.get(
                "typed_policy_count"
            ),

        "unknown_blocks_mutation":
            governance.get(
                "unknown_blocks_mutation"
            ),

        "authority_required_blocks_mutation":
            governance.get(
                "authority_required_blocks_mutation"
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
                and governance.get(
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
        "typed_policy_ready",
        "unknown_blocks_mutation",
        "authority_required_blocks_mutation",
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

    safe_guard = evaluate_mutation(
        path=(
            "/root/savant-runtime/"
            "runtime/example.py"
        ),
        content=(
            "kindred remains canonical"
        ),
        operation="replace_text",
        caller=CALLER,
        mutation_owner=OWNER,
        intent="focused governance selftest",
    )

    if not safe_guard[
        "allowed"
    ]:
        raise CodaPalaverBridgeError(
            "valid governance preflight failed"
        )

    escape_guard = evaluate_mutation(
        path="/tmp/coda-escape",
        content="test",
        operation="replace_text",
        caller=CALLER,
        mutation_owner=OWNER,
        intent="focused containment selftest",
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

        "safe_policy_decision":
            safe_guard[
                "decision"
            ],

        "escape_rejected":
            not escape_guard[
                "allowed"
            ],

        "escape_policy_decision":
            escape_guard[
                "decision"
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
