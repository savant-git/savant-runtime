from __future__ import annotations

import json

from .exile_flow_binding import (
    capability_prepare,
    capability_receipt,
    capability_status,
    contracts,
    handler_for,
    preparation,
    schema,
    status,
)


def selftest() -> dict[str, object]:
    prepared = handler_for(
        capability_prepare
    )(
        {
            "task_id":
                "flow-selftest-task",
            "operation":
                "focused-flow-check",
            "payload": {
                "value":
                    "niche-flow",
            },
            "task_state":
                "prepared",
            "priority":
                1,
            "dependencies": (
                "dependency-a",
            ),
            "lineage": {
                "source":
                    "niche-flow-selftest",
            },
            "provenance": {
                "source":
                    "focused-runtime-check",
            },
            "metadata": {
                "purpose":
                    "flow-binding-selftest",
            },
        }
    )

    receipt = handler_for(
        capability_receipt
    )(
        {
            "prepared":
                prepared,
            "execution_state":
                "complete",
            "attempt":
                1,
            "result": {
                "ok":
                    True,
            },
        }
    )

    lifecycle_status = handler_for(
        capability_status
    )(
        {}
    )

    prepared_exile = preparation()
    binding_status = status()

    checks = {
        "three_contracts":
            len(
                contracts()
            )
            == 3,
        "prepare_owner_preserved":
            prepared.get(
                "owner"
            )
            == "exile:niche",
        "mechanics_owner_preserved":
            prepared.get(
                "mechanics_owner"
            )
            == "living:dryve",
        "task_governance_preserved":
            prepared.get(
                "task_governance_owner"
            )
            == "exile:niche",
        "dryve_cannot_transition_task":
            prepared.get(
                "task_transition_authorized_by_dryve"
            )
            is False,
        "prepared_non_authoritative":
            prepared.get(
                "authoritative"
            )
            is False,
        "prepared_authority_effect_none":
            prepared.get(
                "authority_effect"
            )
            == "none",
        "receipt_present":
            isinstance(
                receipt,
                dict,
            )
            and bool(
                receipt
            ),
        "status_owner_preserved":
            lifecycle_status.get(
                "owner"
            )
            == "exile:niche",
        "status_mechanics_owner_preserved":
            lifecycle_status.get(
                "mechanics_owner"
            )
            == "living:dryve",
        "flow_creates_no_authority":
            binding_status.get(
                "creates_authority"
            )
            is False,
        "flow_changes_no_governance":
            binding_status.get(
                "changes_task_governance"
            )
            is False,
        "prepared_extension_space":
            bool(
                prepared_exile[
                    "boundaries"
                ][
                    "extension_space_reserved"
                ]
            ),
        "prepared_without_authority":
            not bool(
                prepared_exile[
                    "boundaries"
                ][
                    "creates_authority"
                ]
            ),
    }

    return {
        "schema":
            (
                "savant://runtime/niche/"
                "exile-flow-binding-selftest/1.0.0"
            ),
        "binding_schema":
            schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
