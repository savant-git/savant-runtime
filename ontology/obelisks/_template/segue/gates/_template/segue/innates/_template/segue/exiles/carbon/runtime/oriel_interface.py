#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from pathlib import Path
from typing import Any, Mapping

from oriel_capabilities import (
    collect as collect_capabilities,
)

from oriel_introspection import (
    snapshot as introspection_snapshot,
)


owner = "carbon"
component = "oriel-interface"
authority_effect = "none"
schema = "savant.carbon.oriel-interface.v1"

carbon_root = (
    Path(
        __file__
    ).resolve().parent.parent
)


operation_groups = {
    "discovery": (
        "profile",
        "status",
        "capabilities",
        "contracts",
        "health",
    ),

    "chronology_logistics": (
        "validate",
        "position",
        "encounters",
        "availability",
    ),

    "simulation": (
        "superpose",
        "inverse",
        "consequences",
        "reachability",
        "worldline",
    ),

    "analysis": (
        "causal_graph",
        "critical_corridor",
        "inevitability_horizon",
        "occupants",
        "intersections",
        "gaps",
    ),
}


runtime_bindings = {
    "validate":
        (
            "oriel_simulation:"
            "engine.validate_world"
        ),

    "position":
        (
            "oriel_simulation:"
            "engine.position"
        ),

    "encounters":
        (
            "oriel_simulation:"
            "engine.encounters"
        ),

    "availability":
        (
            "oriel_simulation:"
            "engine.availability"
        ),

    "superpose":
        (
            "oriel_simulation:"
            "engine.superpose"
        ),

    "inverse":
        (
            "oriel_simulation:"
            "engine.inverse"
        ),

    "consequences":
        (
            "oriel_consequence:"
            "engine.superpose"
        ),

    "reachability":
        (
            "oriel_horizon:"
            "engine.reachability"
        ),

    "worldline":
        (
            "oriel_worldline:"
            "engine.build"
        ),

    "causal_graph":
        (
            "oriel_causality:"
            "engine.graph"
        ),

    "critical_corridor":
        (
            "oriel_causality:"
            "engine.critical_corridor"
        ),

    "inevitability_horizon":
        (
            "oriel_causality:"
            "engine.inevitability_horizon"
        ),

    "occupants":
        (
            "oriel_worldline:"
            "engine.occupants"
        ),

    "intersections":
        (
            "oriel_worldline:"
            "engine.intersections"
        ),

    "gaps":
        (
            "oriel_worldline:"
            "engine.gaps"
        ),
}


class oriel_interface_error(
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


def load_json(
    relative_path: str,
) -> dict[str, Any]:
    path = (
        carbon_root
        / relative_path
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise oriel_interface_error(
            (
                "cannot read "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_interface_error(
            (
                "invalid json in "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_interface_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def contract_registry() -> dict[str, Any]:
    return load_json(
        (
            "interface/contracts/"
            "contracts.json"
        )
    )


def carbon_capability_registry(
) -> dict[str, Any]:
    return load_json(
        (
            "interface/capabilities/"
            "capabilities.json"
        )
    )


def operation_catalog() -> dict[str, Any]:
    operations = []

    for group, names in (
        operation_groups.items()
    ):
        for name in names:
            operations.append(
                {
                    "id":
                        name,

                    "group":
                        group,

                    "runtime_binding":
                        runtime_bindings.get(
                            name
                        ),

                    "authority_effect":
                        "none",

                    "mutates_source":
                        False,
                }
            )

    return {
        "schema":
            schema,

        "kind":
            "operation-catalog",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "operations":
            operations,

        "operation_count":
            len(
                operations
            ),
    }


def profile() -> dict[str, Any]:
    capabilities = collect_capabilities()

    health = introspection_snapshot()

    contracts = contract_registry()

    carbon_capabilities = (
        carbon_capability_registry()
    )

    catalog = operation_catalog()

    result = {
        "schema":
            schema,

        "kind":
            "public-specialization-profile",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "specialization":
            "oriel",

        "purpose":
            (
                "chronology and logistics "
                "intelligence inside carbon "
                "simulation"
            ),

        "simulation_owner":
            "carbon",

        "quantum_owner":
            "carbon",

        "causal_simulation_owner":
            "carbon",

        "projection_owner":
            "filament",

        "transformation_owner":
            "modus",

        "capability_surface_id":
            capabilities.get(
                "id"
            ),

        "capability_count":
            capabilities.get(
                "capability_count",
                0,
            ),

        "provider_count":
            capabilities.get(
                "provider_count",
                0,
            ),

        "health_state":
            health.get(
                "oriel_state"
            ),

        "carbon_effect":
            health.get(
                "carbon_effect"
            ),

        "operation_catalog":
            catalog,

        "contract_registry_id":
            contracts.get(
                "id"
            ),

        "carbon_capability_registry_id":
            carbon_capabilities.get(
                "id"
            ),

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
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


def interface_contracts() -> dict[str, Any]:
    contracts = contract_registry()

    selected = [
        clone(
            dict(
                value
            )
        )
        for value
        in contracts.get(
            "contracts",
            [],
        )
        if (
            isinstance(
                value,
                Mapping,
            )
            and str(
                value.get(
                    "id",
                    "",
                )
            ).startswith(
                "oriel_"
            )
        )
    ]

    return {
        "schema":
            schema,

        "kind":
            "oriel-interface-contracts",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "contract_count":
            len(
                selected
            ),

        "contracts":
            selected,
    }


def status() -> dict[str, Any]:
    value = profile()

    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "health_state":
            value[
                "health_state"
            ],

        "capability_count":
            value[
                "capability_count"
            ],

        "provider_count":
            value[
                "provider_count"
            ],

        "operation_count":
            value[
                "operation_catalog"
            ][
                "operation_count"
            ],

        "contract_count":
            interface_contracts()[
                "contract_count"
            ],

        "authority_transfer":
            False,

        "ready":
            value[
                "health_state"
            ]
            != "blocked",
    }


def selftest() -> dict[str, Any]:
    carbon_capabilities = (
        carbon_capability_registry()
    )

    capability_ids = {
        str(
            value.get(
                "id",
                "",
            )
        )
        for value
        in carbon_capabilities.get(
            "capabilities",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    if (
        "oriel"
        not in capability_ids
    ):
        raise oriel_interface_error(
            (
                "carbon capability registry "
                "does not expose oriel"
            )
        )

    contracts = interface_contracts()

    contract_ids = {
        str(
            value.get(
                "id",
                "",
            )
        )
        for value
        in contracts[
            "contracts"
        ]
    }

    required = {
        "oriel_discover",
        "oriel_interrogate",
    }

    if not required.issubset(
        contract_ids
    ):
        raise oriel_interface_error(
            (
                "carbon contract registry "
                "does not expose required "
                "oriel contracts"
            )
        )

    value = profile()

    if (
        value[
            "health_state"
        ]
        == "blocked"
    ):
        raise oriel_interface_error(
            (
                "oriel public interface "
                "is blocked"
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

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "oriel_capability_exposed":
            True,

        "oriel_contracts_exposed":
            True,

        "health_state":
            value[
                "health_state"
            ],

        "capability_count":
            value[
                "capability_count"
            ],

        "operation_count":
            value[
                "operation_catalog"
            ][
                "operation_count"
            ],

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "carbon_capability_registry",
    "contract_registry",
    "interface_contracts",
    "operation_catalog",
    "profile",
    "selftest",
    "status",
]
