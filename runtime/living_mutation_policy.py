#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


from runtime.living_governance import (
    stream_records,
)

from runtime.living_guard import (
    evaluate_change,
    status as guard_status,
)

from runtime.living_policy import (
    evaluate_policies,
    status as policy_status,
)


root = Path(
    "/root/savant-runtime"
).resolve()

owner = "living-governance"

authority_effect = "guard"

policy_streams = (
    "rules",
    "permissions",
    "invariants",
)

blocking_decisions = {
    "fail",
    "unknown",
    "authority-required",
}


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _typed_policy(
    record: Mapping[str, Any],
) -> bool:
    if "effect" not in record:
        return False

    record_type = _text(
        record.get(
            "type"
        )
    ).lower()

    if (
        record_type
        and record_type
        not in {
            "policy",
            "rule",
            "permission",
            "invariant",
        }
    ):
        return False

    return True


def typed_policy_records() -> list[
    dict[
        str,
        Any,
    ]
]:
    records = []

    for stream in policy_streams:
        for record in stream_records(
            stream
        ):
            if not isinstance(
                record,
                Mapping,
            ):
                continue

            if not _typed_policy(
                record
            ):
                continue

            records.append(
                dict(
                    record
                )
            )

    return sorted(
        records,
        key=lambda item: (
            int(
                item.get(
                    "priority",
                    1000,
                )
            ),
            str(
                item.get(
                    "stream",
                    "",
                )
            ),
            str(
                item.get(
                    "id",
                    "",
                )
            ),
        ),
    )


def mutation_context(
    *,
    path: str,
    content: str,
    operation: str,
    caller: str,
    mutation_owner: str,
    relative_path: str | None = None,
    expected_digest: str | None = None,
    intent: str | None = None,
    authority_granted: bool = False,
    evidence: list[Any] | None = None,
) -> dict[str, Any]:
    candidate = Path(
        path
    ).resolve()

    if relative_path is None:
        try:
            relative_path = str(
                candidate.relative_to(
                    root
                )
            )

        except ValueError:
            relative_path = None

    return {
        "scope": {
            "domain":
                "runtime",

            "root":
                str(
                    root
                ),
        },

        "subject": {
            "caller":
                caller,

            "mutation_owner":
                mutation_owner,
        },

        "target": {
            "path":
                str(
                    candidate
                ),

            "relative_path":
                relative_path,
        },

        "action": {
            "name":
                operation,

            "class":
                "durable-mutation",
        },

        "authority": {
            "granted":
                bool(
                    authority_granted
                ),
        },

        "evidence":
            list(
                evidence
                or []
            ),

        "mutation": {
            "operation":
                operation,

            "path":
                str(
                    candidate
                ),

            "relative_path":
                relative_path,

            "content_length":
                len(
                    content
                ),

            "expected_digest":
                expected_digest,

            "expected_digest_present":
                expected_digest
                is not None,

            "intent":
                intent,
        },

        "path":
            str(
                candidate
            ),

        "relative_path":
            relative_path,

        "operation":
            operation,

        "caller":
            caller,

        "mutation_owner":
            mutation_owner,

        "content_length":
            len(
                content
            ),

        "expected_digest":
            expected_digest,

        "expected_digest_present":
            expected_digest
            is not None,

        "intent":
            intent,
    }


def _empty_policy_result() -> dict[str, Any]:
    return {
        "schema":
            "savant.living-policy.v1",

        "owner":
            owner,

        "authority_effect":
            "none",

        "decision":
            "pass",

        "allowed":
            True,

        "evaluation_count":
            0,

        "outcome_counts": {
            "advisory":
                0,

            "authority-required":
                0,

            "fail":
                0,

            "pass":
                0,

            "unknown":
                0,
        },

        "governing_rules": [],

        "reason_codes": [],

        "unresolved_unknowns": [],

        "evaluations": [],
    }


def evaluate_mutation(
    *,
    path: str,
    content: str,
    operation: str = "replace_text",
    caller: str = "palaver",
    mutation_owner: str = "coda",
    relative_path: str | None = None,
    expected_digest: str | None = None,
    intent: str | None = None,
    authority_granted: bool = False,
    evidence: list[Any] | None = None,
) -> dict[str, Any]:
    legacy = evaluate_change(
        path=path,
        text=content,
    )

    context = mutation_context(
        path=path,
        content=content,
        operation=operation,
        caller=caller,
        mutation_owner=mutation_owner,
        relative_path=relative_path,
        expected_digest=expected_digest,
        intent=intent,
        authority_granted=authority_granted,
        evidence=evidence,
    )

    policies = typed_policy_records()

    typed = (
        evaluate_policies(
            policies,
            context,
        )
        if policies
        else _empty_policy_result()
    )

    typed_decision = str(
        typed.get(
            "decision",
            "unknown",
        )
    )

    legacy_allowed = bool(
        legacy.get(
            "allowed"
        )
    )

    if not legacy_allowed:
        decision = "fail"

    elif typed_decision in blocking_decisions:
        decision = typed_decision

    elif typed_decision == "advisory":
        decision = "advisory"

    else:
        decision = "pass"

    allowed = (
        legacy_allowed
        and typed_decision
        not in blocking_decisions
    )

    reason_codes = sorted(
        {
            *[
                (
                    "legacy_guard."
                    + str(
                        item.get(
                            "check",
                            "unknown",
                        )
                    ).replace(
                        "-",
                        "_",
                    )
                )
                for item
                in legacy.get(
                    "checks",
                    []
                )
                if (
                    not item.get(
                        "passed",
                        False,
                    )
                    and item.get(
                        "severity"
                    )
                    == "error"
                )
            ],
            *[
                str(
                    value
                )
                for value
                in typed.get(
                    "reason_codes",
                    []
                )
            ],
        }
    )

    return {
        "schema":
            (
                "savant.living-governance."
                "mutation-evaluation.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "mutation_owner":
            mutation_owner,

        "caller":
            caller,

        "decision":
            decision,

        "allowed":
            allowed,

        "reason_codes":
            reason_codes,

        "typed_policy_count":
            len(
                policies
            ),

        "context":
            context,

        "legacy_guard":
            legacy,

        "typed_policy":
            typed,

        "checks":
            legacy.get(
                "checks",
                []
            ),

        "check_count":
            legacy.get(
                "check_count",
                0,
            ),

        "failure_count":
            legacy.get(
                "failure_count",
                0,
            ),

        "warning_count":
            legacy.get(
                "warning_count",
                0,
            ),

        "credential_values_exposed":
            False,
    }


def status() -> dict[str, Any]:
    legacy = guard_status()

    policy = policy_status()

    policies = typed_policy_records()

    return {
        "schema":
            (
                "savant.living-governance."
                "mutation-policy-status.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "canonical_root":
            str(
                root
            ),

        "policy_streams":
            list(
                policy_streams
            ),

        "typed_policy_count":
            len(
                policies
            ),

        "typed_policy_ids": [
            str(
                record.get(
                    "id"
                )
            )
            for record
            in policies
        ],

        "legacy_guard":
            legacy,

        "policy_engine":
            policy,

        "unknown_blocks_mutation":
            True,

        "authority_required_blocks_mutation":
            True,

        "coda_ownership_preserved":
            True,

        "credential_values_exposed":
            False,

        "ready":
            bool(
                legacy.get(
                    "ready"
                )
                and policy.get(
                    "ready"
                )
            ),
    }


__all__ = [
    "evaluate_mutation",
    "mutation_context",
    "status",
    "typed_policy_records",
]
