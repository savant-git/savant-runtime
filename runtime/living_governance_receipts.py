#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping


schema = "savant.living-governance.evaluation-receipt.v1"
owner = "living-governance"
authority_effect = "none"

allowed_decisions = {
    "allow",
    "deny",
    "advisory",
    "unknown",
    "authority-required",
}


class living_governance_receipt_error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        raise living_governance_receipt_error(
            "expected string collection"
        )

    return sorted(
        {
            str(item).strip()
            for item in value
            if str(item).strip()
        }
    )


def _mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise living_governance_receipt_error(
            label
            + " must be a JSON object"
        )

    return value


def evaluation_decision(
    evaluation: Mapping[str, Any],
) -> str:
    for field in (
        "decision",
        "result",
        "outcome",
        "state",
    ):
        raw = evaluation.get(
            field
        )

        if raw is None:
            continue

        value = (
            str(raw)
            .strip()
            .lower()
            .replace(
                "_",
                "-",
            )
        )

        if value in allowed_decisions:
            return value

    raise living_governance_receipt_error(
        (
            "evaluation must expose "
            "decision/result/outcome/state "
            "as one of: "
            + ", ".join(
                sorted(
                    allowed_decisions
                )
            )
        )
    )


def build_evaluation_receipt(
    evaluation: Mapping[str, Any],
    *,
    mutation_plan: Mapping[
        str,
        Any,
    ]
    | None = None,
    mutation_plan_ref: str
    | None = None,
) -> dict[str, Any]:
    evaluation = _mapping(
        evaluation,
        "evaluation",
    )

    decision = evaluation_decision(
        evaluation
    )

    if mutation_plan is not None:
        mutation_plan = _mapping(
            mutation_plan,
            "mutation_plan",
        )

        plan_digest = digest(
            mutation_plan
        )

    else:
        plan_digest = str(
            evaluation.get(
                "mutation_plan_digest"
            )
            or evaluation.get(
                "plan_digest"
            )
            or ""
        ).strip()

    plan_ref = str(
        mutation_plan_ref
        or evaluation.get(
            "mutation_plan_ref"
        )
        or evaluation.get(
            "plan_ref"
        )
        or ""
    ).strip()

    reason_codes = _string_list(
        evaluation.get(
            "reason_codes",
            evaluation.get(
                "reasons"
            ),
        )
    )

    governing_rules = _string_list(
        evaluation.get(
            "governing_rules",
            evaluation.get(
                "rules"
            ),
        )
    )

    evidence_requirements = (
        _string_list(
            evaluation.get(
                "evidence_requirements"
            )
        )
    )

    affected_objects = _string_list(
        evaluation.get(
            "affected_objects"
        )
    )

    compatibility_obligations = (
        _string_list(
            evaluation.get(
                "compatibility_obligations"
            )
        )
    )

    unresolved_unknowns = (
        _string_list(
            evaluation.get(
                "unresolved_unknowns"
            )
        )
    )

    override_requirements = (
        _string_list(
            evaluation.get(
                "override_requirements"
            )
        )
    )

    evaluation_digest = digest(
        evaluation
    )

    identity_payload = {
        "evaluation_digest":
            evaluation_digest,

        "mutation_plan_digest":
            plan_digest,

        "mutation_plan_ref":
            plan_ref,

        "decision":
            decision,
    }

    receipt_id = (
        "living-governance:"
        "evaluation-receipt:"
        + digest(
            identity_payload
        )
    )

    result = {
        "schema":
            schema,

        "id":
            receipt_id,

        "kind":
            (
                "governance-"
                "evaluation-receipt"
            ),

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "authoritative":
            False,

        "projection_only":
            True,

        "mutation_owner":
            "coda",

        "governance_owner":
            owner,

        "decision":
            decision,

        "evaluation_digest":
            evaluation_digest,

        "mutation_plan_digest":
            plan_digest
            or None,

        "mutation_plan_ref":
            plan_ref
            or None,

        "governing_rules":
            governing_rules,

        "reason_codes":
            reason_codes,

        "evidence_requirements":
            evidence_requirements,

        "affected_objects":
            affected_objects,

        "compatibility_obligations":
            compatibility_obligations,

        "unresolved_unknowns":
            unresolved_unknowns,

        "override_requirements":
            override_requirements,

        "evaluation_trace_ref":
            evaluation.get(
                "evaluation_trace_ref"
            ),

        "source_evaluation":
            clone(
                dict(
                    evaluation
                )
            ),

        "coda_receipt_ref":
            None,

        "coda_receipt_digest":
            None,

        "source_state_mutated":
            False,

        "mutation_applied":
            False,

        "authority_transfer":
            False,
    }

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def link_to_coda_receipt(
    governance_receipt: Mapping[
        str,
        Any,
    ],
    coda_receipt: Mapping[
        str,
        Any,
    ],
    *,
    coda_receipt_ref: str
    | None = None,
) -> dict[str, Any]:
    governance_receipt = _mapping(
        governance_receipt,
        "governance_receipt",
    )

    coda_receipt = _mapping(
        coda_receipt,
        "coda_receipt",
    )

    if (
        governance_receipt.get(
            "owner"
        )
        != owner
    ):
        raise living_governance_receipt_error(
            (
                "governance receipt owner "
                "must remain "
                "living-governance"
            )
        )

    if (
        governance_receipt.get(
            "authority_effect"
        )
        != "none"
    ):
        raise living_governance_receipt_error(
            (
                "governance receipt "
                "authority_effect "
                "must be none"
            )
        )

    if (
        governance_receipt.get(
            "authority_transfer"
        )
        is not False
    ):
        raise living_governance_receipt_error(
            (
                "governance receipt "
                "must not transfer authority"
            )
        )

    coda_digest = digest(
        coda_receipt
    )

    coda_ref = str(
        coda_receipt_ref
        or coda_receipt.get(
            "id"
        )
        or coda_receipt.get(
            "receipt_id"
        )
        or (
            "coda:receipt:"
            + coda_digest
        )
    ).strip()

    linked_governance_receipt = clone(
        dict(
            governance_receipt
        )
    )

    linked_governance_receipt[
        "coda_receipt_ref"
    ] = coda_ref

    linked_governance_receipt[
        "coda_receipt_digest"
    ] = coda_digest

    linked_governance_receipt[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in (
                linked_governance_receipt
                .items()
            )
            if key
            != "digest"
        }
    )

    coda_link = {
        "schema":
            (
                "savant.coda."
                "governance-evaluation-link.v1"
            ),

        "kind":
            (
                "governance-"
                "evaluation-link"
            ),

        (
            "governance_evaluation_"
            "receipt_ref"
        ):
            governance_receipt.get(
                "id"
            ),

        (
            "governance_evaluation_"
            "receipt_digest"
        ):
            linked_governance_receipt[
                "digest"
            ],

        (
            "governance_"
            "evaluation_digest"
        ):
            governance_receipt.get(
                "evaluation_digest"
            ),

        "governance_decision":
            governance_receipt.get(
                "decision"
            ),

        "governance_reason_codes":
            clone(
                governance_receipt.get(
                    "reason_codes",
                    [],
                )
            ),

        "governance_owner":
            owner,

        "mutation_owner":
            "coda",

        "authority_effect":
            "none",

        "authority_transfer":
            False,
    }

    link_receipt = {
        "schema":
            (
                "savant.living-governance."
                "coda-receipt-link.v1"
            ),

        "kind":
            (
                "coda-governance-"
                "receipt-link"
            ),

        "owner":
            owner,

        "authority_effect":
            "none",

        "governance_receipt_ref":
            governance_receipt.get(
                "id"
            ),

        "governance_receipt_digest":
            linked_governance_receipt[
                "digest"
            ],

        "coda_receipt_ref":
            coda_ref,

        "coda_receipt_digest":
            coda_digest,

        "mutation_owner":
            "coda",

        "governance_owner":
            owner,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }

    link_receipt[
        "id"
    ] = (
        "living-governance:"
        "coda-receipt-link:"
        + digest(
            {
                "governance_receipt_ref":
                    link_receipt[
                        "governance_receipt_ref"
                    ],

                "governance_receipt_digest":
                    link_receipt[
                        "governance_receipt_digest"
                    ],

                "coda_receipt_ref":
                    coda_ref,

                "coda_receipt_digest":
                    coda_digest,
            }
        )
    )

    link_receipt[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in link_receipt.items()
            if key
            != "digest"
        }
    )

    return {
        "schema":
            (
                "savant.living-governance."
                "receipt-linkage.v1"
            ),

        "kind":
            "receipt-linkage",

        "owner":
            owner,

        "authority_effect":
            "none",

        "governance_receipt":
            linked_governance_receipt,

        "coda_receipt_link":
            coda_link,

        "link_receipt":
            link_receipt,

        "coda_receipt_mutated":
            False,

        "mutation_owner":
            "coda",

        "authority_transfer":
            False,
    }


def selftest() -> dict[str, Any]:
    evaluation = {
        "decision":
            "unknown",

        "reason_codes":
            [
                "missing-evidence"
            ],

        "governing_rules":
            [
                "rule:test"
            ],

        "evidence_requirements":
            [
                "evidence:test"
            ],

        "unresolved_unknowns":
            [
                "unknown:test"
            ],
    }

    plan = {
        "id":
            "mutation-plan:test",

        "owner":
            "coda",

        "operation":
            "write",
    }

    coda_receipt = {
        "id":
            "coda:receipt:test",

        "owner":
            "coda",

        "ok":
            True,
    }

    first = build_evaluation_receipt(
        evaluation,
        mutation_plan=
            plan,
    )

    second = build_evaluation_receipt(
        evaluation,
        mutation_plan=
            plan,
    )

    if first != second:
        raise living_governance_receipt_error(
            (
                "evaluation receipt "
                "is not deterministic"
            )
        )

    if (
        first[
            "decision"
        ]
        != "unknown"
    ):
        raise living_governance_receipt_error(
            (
                "unknown evaluation "
                "was collapsed"
            )
        )

    linked = link_to_coda_receipt(
        first,
        coda_receipt,
    )

    if (
        linked[
            "coda_receipt_link"
        ][
            "mutation_owner"
        ]
        != "coda"
    ):
        raise living_governance_receipt_error(
            (
                "coda mutation "
                "ownership changed"
            )
        )

    if (
        linked[
            "governance_receipt"
        ][
            "owner"
        ]
        != owner
    ):
        raise living_governance_receipt_error(
            (
                "governance "
                "ownership changed"
            )
        )

    if (
        linked[
            "authority_transfer"
        ]
        is not False
    ):
        raise living_governance_receipt_error(
            "authority transfer detected"
        )

    if (
        linked[
            "coda_receipt_mutated"
        ]
        is not False
    ):
        raise living_governance_receipt_error(
            "coda receipt was mutated"
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "deterministic_receipt":
            True,

        "unknown_preserved":
            True,

        "coda_link_generated":
            True,

        "mutation_owner":
            "coda",

        "governance_owner":
            owner,

        "coda_receipt_mutated":
            False,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "build_evaluation_receipt",
    "evaluation_decision",
    "link_to_coda_receipt",
    "living_governance_receipt_error",
    "selftest",
]
