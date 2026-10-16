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
            "execution_id":
                "execution:opus:flow-selftest",
            "operation":
                "focused-flow-check",
            "payload": {
                "value":
                    "opus-flow",
            },
            "provider_route":
                "selftest-provider-route",
            "model_route":
                "selftest-model-route",
            "dependencies": (
                "dependency-a",
            ),
            "lineage": {
                "source":
                    "opus-flow-selftest",
            },
            "provenance": {
                "source":
                    "focused-runtime-check",
            },
            "retry_policy": {
                "owner":
                    "exile:opus",
                "maximum_attempts":
                    1,
            },
            "timeout_policy": {
                "owner":
                    "exile:opus",
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
            == "exile:opus",
        "mechanics_owner_preserved":
            prepared.get(
                "mechanics_owner"
            )
            == "living:dryve",
        "provider_execution_owner_preserved":
            prepared.get(
                "provider_execution_owner"
            )
            == "exile:opus",
        "provider_routing_owner_preserved":
            prepared.get(
                "provider_routing_owner"
            )
            == "exile:opus",
        "dryve_cannot_select_provider":
            prepared.get(
                "provider_selection_authorized_by_dryve"
            )
            is False,
        "dryve_cannot_access_provider":
            prepared.get(
                "provider_access_authorized_by_dryve"
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
            == "exile:opus",
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
        "flow_changes_no_provider_ownership":
            binding_status.get(
                "changes_provider_ownership"
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
                "savant://runtime/opus/"
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
