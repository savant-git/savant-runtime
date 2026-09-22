#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json

from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


owner = "coda"
component = "governance-surface"
governance_owner = "living-governance"
authority_effect = "none"
schema = "savant.coda.governance-surface.v1"

coda_root = (
    Path(__file__).resolve().parent.parent
)

runtime_root = (
    coda_root
    / "runtime"
)

capability_path = (
    coda_root
    / "interface/capabilities/"
    "governance_receipts.json"
)

contract_path = (
    coda_root
    / "interface/contracts/"
    "governance_receipts.json"
)


class coda_governance_surface_error(
    RuntimeError
):
    pass


def load_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise coda_governance_surface_error(
            (
                "cannot read "
                + str(path)
                + ": "
                + str(exc)
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise coda_governance_surface_error(
            (
                "invalid json in "
                + str(path)
                + ": "
                + str(exc)
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise coda_governance_surface_error(
            (
                "expected json object: "
                + str(path)
            )
        )

    return value


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    if not path.is_file():
        raise coda_governance_surface_error(
            (
                "runtime module missing: "
                + str(path)
            )
        )

    spec = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise coda_governance_surface_error(
            (
                "cannot load runtime module: "
                + str(path)
            )
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


def descriptors() -> dict[str, Any]:
    return {
        "capabilities":
            load_json(
                capability_path
            ),

        "contracts":
            load_json(
                contract_path
            ),
    }


def runtime_status() -> dict[str, Any]:
    governed = load_module(
        (
            "savant_coda_"
            "palaver_governed_bridge"
        ),
        runtime_root
        / "palaver_governed_bridge.py",
    )

    receipts = load_module(
        (
            "savant_coda_"
            "governance_receipts"
        ),
        runtime_root
        / "governance_receipts.py",
    )

    bridge_status_fn = getattr(
        governed,
        "bridge_status",
        None,
    )

    receipt_status_fn = getattr(
        receipts,
        "status",
        None,
    )

    if not callable(
        bridge_status_fn
    ):
        raise coda_governance_surface_error(
            (
                "governed bridge does not "
                "expose bridge_status()"
            )
        )

    if not callable(
        receipt_status_fn
    ):
        raise coda_governance_surface_error(
            (
                "governance receipt runtime "
                "does not expose status()"
            )
        )

    bridge = bridge_status_fn()
    receipt = receipt_status_fn()

    if not isinstance(
        bridge,
        Mapping,
    ):
        raise coda_governance_surface_error(
            (
                "bridge status did not "
                "return an object"
            )
        )

    if not isinstance(
        receipt,
        Mapping,
    ):
        raise coda_governance_surface_error(
            (
                "receipt status did not "
                "return an object"
            )
        )

    return {
        "bridge":
            dict(
                bridge
            ),

        "receipts":
            dict(
                receipt
            ),
    }


def status() -> dict[str, Any]:
    declared = descriptors()
    runtime = runtime_status()

    capability = declared[
        "capabilities"
    ]

    contract = declared[
        "contracts"
    ]

    bridge = runtime[
        "bridge"
    ]

    receipts = runtime[
        "receipts"
    ]

    ready = bool(
        capability.get(
            "owner"
        )
        == "coda"
        and contract.get(
            "owner"
        )
        == "coda"
        and bridge.get(
            "ready"
        )
        is True
        and receipts.get(
            "ready"
        )
        is True
        and bridge.get(
            "mutation_owner"
        )
        == "coda"
        and receipts.get(
            "mutation_owner"
        )
        == "coda"
        and bridge.get(
            "authority_transfer"
        )
        is False
        and receipts.get(
            "authority_transfer"
        )
        is False
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

        "authority_effect":
            authority_effect,

        "capability_descriptor":
            capability.get(
                "id"
            ),

        "contract_descriptor":
            contract.get(
                "id"
            ),

        "live_bridge_schema":
            bridge.get(
                "live_bridge_schema"
            ),

        "live_bridge_ready":
            bridge.get(
                "live_bridge_ready"
            ),

        (
            "governed_bridge_"
            "ready"
        ):
            bridge.get(
                "ready"
            ),

        (
            "durable_receipt_"
            "linkage_ready"
        ):
            receipts.get(
                "ready"
            ),

        "mutation_owner":
            "coda",

        "governance_owner":
            governance_owner,

        "live_bridge_replaced":
            False,

        "second_authority_store_created":
            False,

        "authority_transfer":
            False,

        "ready":
            ready,
    }


def selftest() -> dict[str, Any]:
    declared = descriptors()

    capability = declared[
        "capabilities"
    ]

    contract = declared[
        "contracts"
    ]

    capability_ids = {
        str(
            value.get(
                "id",
                "",
            )
        )
        for value
        in capability.get(
            "capabilities",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    required_capabilities = {
        (
            "governance_evaluation_"
            "receipt_linkage"
        ),
        (
            "palaver_governed_"
            "mutation_bridge"
        ),
        "governance_receipt_surface",
    }

    if not required_capabilities.issubset(
        capability_ids
    ):
        raise coda_governance_surface_error(
            (
                "governance capability "
                "descriptor is incomplete"
            )
        )

    contract_ids = {
        str(
            value.get(
                "id",
                "",
            )
        )
        for value
        in contract.get(
            "contracts",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    required_contracts = {
        (
            "build_governance_"
            "evaluation_link"
        ),
        (
            "persist_governance_"
            "evaluation_link"
        ),
        (
            "palaver_governed_"
            "replace_file"
        ),
    }

    if not required_contracts.issubset(
        contract_ids
    ):
        raise coda_governance_surface_error(
            (
                "governance contract "
                "descriptor is incomplete"
            )
        )

    governed = load_module(
        (
            "savant_coda_"
            "palaver_governed_bridge_test"
        ),
        runtime_root
        / "palaver_governed_bridge.py",
    )

    receipts = load_module(
        (
            "savant_coda_"
            "governance_receipts_test"
        ),
        runtime_root
        / "governance_receipts.py",
    )

    bridge_test = getattr(
        governed,
        "selftest",
        None,
    )

    receipt_test = getattr(
        receipts,
        "selftest",
        None,
    )

    if not callable(
        bridge_test
    ):
        raise coda_governance_surface_error(
            (
                "governed bridge selftest "
                "is unavailable"
            )
        )

    if not callable(
        receipt_test
    ):
        raise coda_governance_surface_error(
            (
                "receipt-link selftest "
                "is unavailable"
            )
        )

    bridge_result = bridge_test()
    receipt_result = receipt_test()

    if (
        not isinstance(
            bridge_result,
            Mapping,
        )
        or bridge_result.get(
            "ok"
        )
        is not True
    ):
        raise coda_governance_surface_error(
            (
                "governed bridge "
                "selftest failed"
            )
        )

    if (
        not isinstance(
            receipt_result,
            Mapping,
        )
        or receipt_result.get(
            "ok"
        )
        is not True
    ):
        raise coda_governance_surface_error(
            (
                "governance receipt "
                "selftest failed"
            )
        )

    current = status()

    if current.get(
        "ready"
    ) is not True:
        raise coda_governance_surface_error(
            (
                "governance surface "
                "is not ready"
            )
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

        "governance_owner":
            governance_owner,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "capabilities_discoverable":
            True,

        "contracts_discoverable":
            True,

        "live_v2_bridge_preserved":
            True,

        "governed_bridge_available":
            True,

        (
            "durable_governance_"
            "receipt_link_available"
        ):
            True,

        "mutation_owner":
            "coda",

        "governance_owner":
            "living-governance",

        "live_bridge_replaced":
            False,

        "second_authority_store_created":
            False,

        "source_state_mutated":
            False,

        "authority_transfer":
            False,
    }


__all__ = [
    "descriptors",
    "runtime_status",
    "selftest",
    "status",
]
