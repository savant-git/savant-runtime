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

from oriel_composition import (
    profile as composition_profile,
)

from oriel_graph import (
    projection as graph_projection,
)

from oriel_interface import (
    profile as interface_profile,
)

from oriel_introspection import (
    snapshot as introspection_snapshot,
)

from oriel_lineage import (
    projection as lineage_projection,
)


owner = "carbon"
component = "oriel-observatory"
authority_effect = "none"
schema = "savant.carbon.oriel-observatory.v1"

carbon_root = (
    Path(__file__).resolve().parent.parent
)


class oriel_observatory_error(
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
        separators=(",", ":"),
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
        raise oriel_observatory_error(
            (
                "cannot read "
                + relative_path
                + ": "
                + str(exc)
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_observatory_error(
            (
                "invalid json in "
                + relative_path
                + ": "
                + str(exc)
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_observatory_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def static_projection() -> dict[str, Any]:
    value = load_json(
        "observatory/carbon_projection.json"
    )

    if (
        value.get(
            "authority_effect"
        )
        != "none"
    ):
        raise oriel_observatory_error(
            (
                "carbon observatory "
                "authority effect is invalid"
            )
        )

    if (
        value.get(
            "authoritative"
        )
        is not False
    ):
        raise oriel_observatory_error(
            (
                "carbon observatory "
                "must remain non-authoritative"
            )
        )

    if (
        value.get(
            "rebuildable"
        )
        is not True
    ):
        raise oriel_observatory_error(
            (
                "carbon observatory "
                "must remain rebuildable"
            )
        )

    return value


def snapshot(
    *,
    full: bool = False,
) -> dict[str, Any]:
    static = static_projection()

    introspection = (
        introspection_snapshot()
    )

    graph = graph_projection()

    lineage = lineage_projection()

    composition = (
        composition_profile()
    )

    interface = (
        interface_profile()
    )

    capabilities = (
        collect_capabilities()
    )

    graph_validation = graph.get(
        "validation",
        {},
    )

    lineage_validation = lineage.get(
        "validation",
        {},
    )

    unresolved_dependencies = (
        introspection.get(
            "dependency_resolution",
            {},
        ).get(
            "unresolved",
            [],
        )
    )

    externally_resolved_dependencies = (
        introspection.get(
            "dependency_resolution",
            {},
        ).get(
            "externally_resolved",
            [],
        )
    )

    provider_state = introspection.get(
        "providers",
        {},
    )

    result = {
        "schema":
            schema,

        "kind":
            "oriel-observatory-snapshot",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "authoritative":
            False,

        "rebuildable":
            True,

        "specialization":
            "carbon.oriel",

        "observed_state":
            introspection.get(
                "oriel_state"
            ),

        "carbon_effect":
            introspection.get(
                "carbon_effect"
            ),

        "health": {
            "blocking_reasons":
                clone(
                    introspection.get(
                        "blocking_reasons",
                        [],
                    )
                ),

            "degraded_reasons":
                clone(
                    introspection.get(
                        "degraded_reasons",
                        [],
                    )
                ),

            "healthy_providers":
                clone(
                    provider_state.get(
                        "healthy",
                        [],
                    )
                ),

            "unready_providers":
                clone(
                    provider_state.get(
                        "unready",
                        [],
                    )
                ),

            "unavailable_providers":
                clone(
                    provider_state.get(
                        "unavailable",
                        [],
                    )
                ),

            "errored_providers":
                clone(
                    provider_state.get(
                        "errored",
                        [],
                    )
                ),
        },

        "capabilities": {
            "surface_id":
                capabilities.get(
                    "id"
                ),

            "count":
                capabilities.get(
                    "capability_count",
                    0,
                ),

            "provider_count":
                capabilities.get(
                    "provider_count",
                    0,
                ),

            "unmanifested_modules":
                clone(
                    capabilities.get(
                        "unmanifested_modules",
                        [],
                    )
                ),

            "unavailable_modules":
                clone(
                    capabilities.get(
                        "unavailable_modules",
                        [],
                    )
                ),
        },

        "dependencies": {
            "unresolved_count":
                len(
                    unresolved_dependencies
                ),

            "externally_resolved_count":
                len(
                    externally_resolved_dependencies
                ),

            "unresolved":
                clone(
                    unresolved_dependencies
                ),

            "externally_resolved":
                clone(
                    externally_resolved_dependencies
                ),
        },

        "graph": {
            "graph_id":
                graph.get(
                    "oriel_graph_id"
                ),

            "node_count":
                graph.get(
                    "node_count",
                    0,
                ),

            "edge_count":
                graph.get(
                    "edge_count",
                    0,
                ),

            "contained_specialization":
                bool(
                    graph_validation.get(
                        "oriel_is_specialization",
                        False,
                    )
                ),

            "peer_exile":
                bool(
                    graph_validation.get(
                        "oriel_is_peer_exile",
                        False,
                    )
                ),

            "all_edge_nodes_resolved":
                bool(
                    graph_validation.get(
                        "all_edge_nodes_resolved",
                        False,
                    )
                ),
        },

        "lineage": {
            "historical_identity":
                "oriel",

            "current_identity":
                "carbon.oriel",

            "historical_lineage_valid":
                bool(
                    lineage_validation.get(
                        "historical_lineage_valid",
                        False,
                    )
                ),

            "specialization_lineage_valid":
                bool(
                    lineage_validation.get(
                        "specialization_lineage_valid",
                        False,
                    )
                ),

            "standalone_oriel_restored":
                bool(
                    lineage_validation.get(
                        "standalone_oriel_restored",
                        False,
                    )
                ),

            "identities_conflated":
                bool(
                    lineage_validation.get(
                        (
                            "historical_and_current_"
                            "oriel_conflated"
                        ),
                        False,
                    )
                ),
        },

        "composition": {
            "mode":
                composition.get(
                    "composition_mode"
                ),

            "projection_owner":
                composition.get(
                    "projection_owner"
                ),

            "transformation_owner":
                composition.get(
                    "transformation_owner"
                ),

            "ownership_transfer":
                bool(
                    composition.get(
                        "ownership_transfer",
                        False,
                    )
                ),

            "authority_transfer":
                bool(
                    composition.get(
                        "authority_transfer",
                        False,
                    )
                ),
        },

        "interface": {
            "health_state":
                interface.get(
                    "health_state"
                ),

            "operation_count":
                interface.get(
                    "operation_catalog",
                    {},
                ).get(
                    "operation_count",
                    0,
                ),

            "capability_count":
                interface.get(
                    "capability_count",
                    0,
                ),
        },

        "observatory_rules": {
            "creates_authority":
                False,

            "mutates_authority":
                False,

            "mutates_source":
                False,

            "claims_simulation_as_fact":
                False,

            "hides_degraded_state":
                False,

            "hides_blocked_state":
                False,
        },

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "authority_transfer":
            False,
    }

    if full:
        result[
            "projections"
        ] = {
            "static":
                clone(
                    static
                ),

            "introspection":
                clone(
                    introspection
                ),

            "capability_surface":
                clone(
                    capabilities
                ),

            "graph":
                clone(
                    graph
                ),

            "lineage":
                clone(
                    lineage
                ),

            "composition":
                clone(
                    composition
                ),

            "interface":
                clone(
                    interface
                ),
        }

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key != "digest"
        }
    )

    return result


def status() -> dict[str, Any]:
    value = snapshot()

    graph = value[
        "graph"
    ]

    lineage = value[
        "lineage"
    ]

    composition = value[
        "composition"
    ]

    ready = bool(
        graph[
            "contained_specialization"
        ]
        and not graph[
            "peer_exile"
        ]
        and graph[
            "all_edge_nodes_resolved"
        ]
        and lineage[
            "historical_lineage_valid"
        ]
        and lineage[
            "specialization_lineage_valid"
        ]
        and not lineage[
            "standalone_oriel_restored"
        ]
        and not lineage[
            "identities_conflated"
        ]
        and not composition[
            "ownership_transfer"
        ]
        and not composition[
            "authority_transfer"
        ]
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

        "authority_effect":
            authority_effect,

        "observed_state":
            value[
                "observed_state"
            ],

        "carbon_effect":
            value[
                "carbon_effect"
            ],

        "capability_count":
            value[
                "capabilities"
            ][
                "count"
            ],

        "provider_count":
            value[
                "capabilities"
            ][
                "provider_count"
            ],

        "unresolved_dependency_count":
            value[
                "dependencies"
            ][
                "unresolved_count"
            ],

        "graph_addressable":
            graph[
                "contained_specialization"
            ],

        "lineage_valid":
            (
                lineage[
                    "historical_lineage_valid"
                ]
                and lineage[
                    "specialization_lineage_valid"
                ]
            ),

        "authoritative":
            False,

        "authority_transfer":
            False,

        "ready":
            ready,
    }


def selftest() -> dict[str, Any]:
    static = static_projection()

    surfaces = static.get(
        "surfaces",
        {},
    )

    required_surfaces = {
        "oriel_manifest",
        "oriel_capabilities",
        "oriel_graph",
        "oriel_ancestor_lineage",
        "oriel_specialization_lineage",
    }

    missing = sorted(
        required_surfaces
        - set(
            surfaces
        )
    )

    if missing:
        raise oriel_observatory_error(
            (
                "carbon observatory lacks "
                "oriel surfaces: "
                + ", ".join(
                    missing
                )
            )
        )

    value = snapshot()

    if (
        value[
            "graph"
        ][
            "peer_exile"
        ]
    ):
        raise oriel_observatory_error(
            (
                "observatory reports oriel "
                "as a peer exile"
            )
        )

    if (
        value[
            "lineage"
        ][
            "standalone_oriel_restored"
        ]
    ):
        raise oriel_observatory_error(
            (
                "observatory reports historical "
                "oriel as restored"
            )
        )

    if (
        value[
            "composition"
        ][
            "authority_transfer"
        ]
        or value[
            "composition"
        ][
            "ownership_transfer"
        ]
    ):
        raise oriel_observatory_error(
            (
                "observatory detected illegal "
                "composition transfer"
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

        "observatory_non_authoritative":
            True,

        "observatory_rebuildable":
            True,

        "oriel_surfaces_exposed":
            True,

        "degraded_state_visible":
            True,

        "blocked_state_visible":
            True,

        "oriel_is_contained_specialization":
            True,

        "historical_oriel_restored":
            False,

        "ownership_transfer":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "selftest",
    "snapshot",
    "static_projection",
    "status",
]
