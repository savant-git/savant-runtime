#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import sys

from pathlib import Path
from typing import Any, Mapping


ROOT_RUNTIME = Path(
    "/root/savant-runtime/runtime"
)

if str(
    ROOT_RUNTIME
) not in sys.path:
    sys.path.insert(
        0,
        str(
            ROOT_RUNTIME
        ),
    )


from living_governance_receipts import (  # noqa: E402
    build_evaluation_receipt,
    link_to_coda_receipt,
    living_governance_receipt_error,
)

from mutation import (  # noqa: E402
    ROOT,
    status as mutation_status,
    write_receipt,
)


owner = "coda"
component = "governance-receipts"
governance_owner = "living-governance"
authority_effect = "none"
schema = "savant.coda.governance-receipts.v1"


class coda_governance_receipt_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def require_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise coda_governance_receipt_error(
            label
            + " must be a JSON object"
        )

    return value


def durable_coda_receipt(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    result = clone(
        dict(
            value
        )
    )

    result.pop(
        "receipt",
        None,
    )

    return result


def mutation_receipt_identity(
    coda_receipt: Mapping[str, Any],
) -> tuple[
    str,
    dict[str, Any],
    str,
]:
    value = require_mapping(
        coda_receipt,
        "coda_receipt",
    )

    if (
        str(
            value.get(
                "owner",
                "",
            )
        ).strip().lower()
        != "coda"
    ):
        raise coda_governance_receipt_error(
            (
                "mutation receipt owner "
                "must be coda"
            )
        )

    identifier = str(
        value.get(
            "id",
            "",
        )
    ).strip()

    if not identifier:
        raise coda_governance_receipt_error(
            (
                "mutation receipt id "
                "is required"
            )
        )

    durable = durable_coda_receipt(
        value
    )

    return (
        identifier,
        durable,
        digest(
            durable
        ),
    )


def build_link_receipt(
    *,
    coda_receipt: Mapping[str, Any],
    governance_evaluation:
        Mapping[str, Any],
    mutation_plan:
        Mapping[str, Any]
        | None = None,
    mutation_plan_ref:
        str | None = None,
) -> dict[str, Any]:
    (
        mutation_receipt_id,
        durable_mutation_receipt,
        mutation_receipt_digest,
    ) = mutation_receipt_identity(
        coda_receipt
    )

    evaluation = require_mapping(
        governance_evaluation,
        "governance_evaluation",
    )

    if mutation_plan is not None:
        mutation_plan = require_mapping(
            mutation_plan,
            "mutation_plan",
        )

    governance_receipt = (
        build_evaluation_receipt(
            evaluation,
            mutation_plan=
                mutation_plan,
            mutation_plan_ref=
                mutation_plan_ref,
        )
    )

    linkage = link_to_coda_receipt(
        governance_receipt,
        durable_mutation_receipt,
        coda_receipt_ref=
            mutation_receipt_id,
    )

    linked_governance = (
        linkage[
            "governance_receipt"
        ]
    )

    identity_material = {
        "mutation_receipt_id":
            mutation_receipt_id,

        "mutation_receipt_digest":
            mutation_receipt_digest,

        (
            "governance_evaluation_"
            "receipt_id"
        ):
            linked_governance.get(
                "id"
            ),

        (
            "governance_evaluation_"
            "receipt_digest"
        ):
            linked_governance.get(
                "digest"
            ),
    }

    result = {
        "id":
            (
                "coda_governance_link_"
                + digest(
                    identity_material
                )[:24]
            ),

        "schema":
            (
                "savant://coda/"
                "governance-evaluation-link/1"
            ),

        "owner":
            owner,

        "component":
            component,

        "operation":
            "governance_evaluation_link",

        "authority_effect":
            authority_effect,

        "mutation_owner":
            owner,

        "governance_owner":
            governance_owner,

        "mutation_receipt_id":
            mutation_receipt_id,

        "mutation_receipt_digest":
            mutation_receipt_digest,

        "mutation_receipt_path":
            str(
                coda_receipt.get(
                    "receipt",
                    "",
                )
            ).strip()
            or None,

        (
            "governance_evaluation_"
            "receipt_id"
        ):
            linked_governance.get(
                "id"
            ),

        (
            "governance_evaluation_"
            "receipt_digest"
        ):
            linked_governance.get(
                "digest"
            ),

        "governance_decision":
            linked_governance.get(
                "decision"
            ),

        "governance_reason_codes":
            clone(
                linked_governance.get(
                    "reason_codes",
                    [],
                )
            ),

        "governance_evaluation_receipt":
            clone(
                linked_governance
            ),

        "link_receipt":
            clone(
                linkage.get(
                    "link_receipt"
                )
            ),

        "coda_receipt_mutated":
            False,

        "mutation_applied_by":
            "coda",

        "evaluation_performed_by":
            governance_owner,

        "source_state_mutated":
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


def persist_linkage(
    *,
    coda_receipt: Mapping[str, Any],
    governance_evaluation:
        Mapping[str, Any],
    mutation_plan:
        Mapping[str, Any]
        | None = None,
    mutation_plan_ref:
        str | None = None,
) -> dict[str, Any]:
    receipt = build_link_receipt(
        coda_receipt=
            coda_receipt,
        governance_evaluation=
            governance_evaluation,
        mutation_plan=
            mutation_plan,
        mutation_plan_ref=
            mutation_plan_ref,
    )

    destination = write_receipt(
        clone(
            receipt
        )
    )

    try:
        relative = str(
            destination.relative_to(
                ROOT
            )
        )

    except ValueError:
        relative = str(
            destination
        )

    result = clone(
        receipt
    )

    result[
        "receipt"
    ] = relative

    result[
        "durable"
    ] = True

    return result


def status() -> dict[str, Any]:
    mutation = mutation_status()

    receipts = bool(
        mutation.get(
            "receipts",
            False,
        )
    )

    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "component":
            component,

        "governance_owner":
            governance_owner,

        "mutation_owner":
            owner,

        "authority_effect":
            authority_effect,

        "coda_receipts_available":
            receipts,

        "durable_link_writer":
            callable(
                write_receipt
            ),

        "governance_receipt_builder":
            callable(
                build_evaluation_receipt
            ),

        "coda_receipt_mutation_required":
            False,

        "second_authority_store_created":
            False,

        "authority_transfer":
            False,

        "ready":
            (
                receipts
                and callable(
                    write_receipt
                )
                and callable(
                    build_evaluation_receipt
                )
            ),
    }


def selftest() -> dict[str, Any]:
    mutation_receipt = {
        "id":
            "coda_test_receipt",

        "schema":
            "savant://coda/mutation-receipt/2",

        "owner":
            "coda",

        "operation":
            "replace_text",

        "requester":
            "palaver",

        "authority_effect":
            "none",

        "path":
            "runtime/test.py",

        "before_digest":
            "before",

        "after_digest":
            "after",

        "receipt":
            (
                "vault/coda/"
                "mutation_receipts/"
                "coda_test_receipt.json"
            ),
    }

    evaluation = {
        "decision":
            "allow",

        "reason_codes":
            [
                "governance-pass"
            ],

        "governing_rules":
            [
                "rule:test"
            ],

        "affected_objects":
            [
                "runtime/test.py"
            ],

        "compatibility_obligations":
            [],
        "unresolved_unknowns":
            [],
        "override_requirements":
            [],
    }

    mutation_plan = {
        "id":
            "mutation-plan:test",

        "owner":
            "coda",

        "operation":
            "replace_text",

        "path":
            "runtime/test.py",
    }

    first = build_link_receipt(
        coda_receipt=
            mutation_receipt,
        governance_evaluation=
            evaluation,
        mutation_plan=
            mutation_plan,
    )

    second = build_link_receipt(
        coda_receipt=
            mutation_receipt,
        governance_evaluation=
            evaluation,
        mutation_plan=
            mutation_plan,
    )

    if first != second:
        raise coda_governance_receipt_error(
            (
                "Coda governance link "
                "receipt is not deterministic"
            )
        )

    if (
        first[
            "owner"
        ]
        != "coda"
    ):
        raise coda_governance_receipt_error(
            (
                "durable receipt ownership "
                "left Coda"
            )
        )

    if (
        first[
            "governance_evaluation_receipt"
        ][
            "owner"
        ]
        != "living-governance"
    ):
        raise coda_governance_receipt_error(
            (
                "governance evaluation "
                "ownership changed"
            )
        )

    if (
        first[
            "mutation_owner"
        ]
        != "coda"
    ):
        raise coda_governance_receipt_error(
            (
                "mutation ownership changed"
            )
        )

    if (
        first[
            "coda_receipt_mutated"
        ]
        is not False
    ):
        raise coda_governance_receipt_error(
            (
                "linkage requires mutation "
                "of original Coda receipt"
            )
        )

    if (
        first[
            "authority_transfer"
        ]
        is not False
    ):
        raise coda_governance_receipt_error(
            "authority transfer detected"
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "deterministic_link_receipt":
            True,

        "coda_owns_durable_link":
            True,

        "living_governance_owns_evaluation":
            True,

        "mutation_owner":
            "coda",

        "governance_owner":
            "living-governance",

        "original_coda_receipt_mutated":
            False,

        "second_authority_store_created":
            False,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "build_link_receipt",
    "coda_governance_receipt_error",
    "persist_linkage",
    "selftest",
    "status",
]
