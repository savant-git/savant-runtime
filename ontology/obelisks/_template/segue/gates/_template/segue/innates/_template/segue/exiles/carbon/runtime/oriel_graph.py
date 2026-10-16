#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from pathlib import Path
from typing import Any, Mapping


owner = "carbon"
component = "oriel-graph"
authority_effect = "none"
schema = "savant.carbon.oriel-graph.v1"

carbon_root = (
    Path(
        __file__
    ).resolve().parent.parent
)


class oriel_graph_error(
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
        raise oriel_graph_error(
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
        raise oriel_graph_error(
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
        raise oriel_graph_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def projection() -> dict[str, Any]:
    carbon = load_json(
        "graph/node.json"
    )

    oriel = load_json(
        "graph/oriel.json"
    )

    module = load_json(
        "registry/module.json"
    )

    node_ids = {
        str(
            value.get(
                "id",
                "",
            )
        )
        for value
        in oriel.get(
            "nodes",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    edges = [
        clone(
            dict(
                value
            )
        )
        for value
        in oriel.get(
            "edges",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    ]

    missing_edge_nodes = []

    for edge in edges:
        for field in (
            "source",
            "target",
        ):
            identifier = str(
                edge.get(
                    field,
                    "",
                )
            )

            if identifier not in node_ids:
                missing_edge_nodes.append(
                    {
                        "edge":
                            clone(
                                edge
                            ),

                        "missing":
                            identifier,
                    }
                )

    specialization = next(
        (
            value
            for value
            in carbon.get(
                "specializations",
                [],
            )
            if (
                isinstance(
                    value,
                    Mapping,
                )
                and value.get(
                    "identity"
                )
                == "carbon.oriel"
            )
        ),
        None,
    )

    graph_reference = (
        module.get(
            "graph",
            {}
        ).get(
            "oriel"
        )
        if isinstance(
            module.get(
                "graph"
            ),
            Mapping,
        )
        else None
    )

    result = {
        "schema":
            schema,

        "kind":
            "oriel-graph-projection",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "carbon_node_id":
            carbon.get(
                "id"
            ),

        "oriel_graph_id":
            oriel.get(
                "id"
            ),

        "oriel_specialization_id":
            (
                specialization.get(
                    "id"
                )
                if isinstance(
                    specialization,
                    Mapping,
                )
                else None
            ),

        "node_count":
            len(
                node_ids
            ),

        "edge_count":
            len(
                edges
            ),

        "nodes":
            clone(
                oriel.get(
                    "nodes",
                    [],
                )
            ),

        "edges":
            edges,

        "validation": {
            "carbon_identity_preserved":
                carbon.get(
                    "id"
                )
                == "exile:carbon",

            "oriel_is_specialization":
                (
                    isinstance(
                        specialization,
                        Mapping,
                    )
                    and specialization.get(
                        "id"
                    )
                    == (
                        "exile:carbon/"
                        "specialization:oriel"
                    )
                ),

            "oriel_is_peer_exile":
                (
                    "exile:oriel"
                    in node_ids
                ),

            "carbon_owns_simulation":
                any(
                    edge.get(
                        "source"
                    )
                    == "exile:carbon"
                    and edge.get(
                        "target"
                    )
                    == "carbon.simulation"
                    and edge.get(
                        "relation"
                    )
                    == "owns"
                    for edge
                    in edges
                ),

            "simulation_substantiates_oriel":
                any(
                    edge.get(
                        "source"
                    )
                    == "carbon.simulation"
                    and edge.get(
                        "target"
                    )
                    == (
                        "exile:carbon/"
                        "specialization:oriel"
                    )
                    and edge.get(
                        "relation"
                    )
                    == "substantiates"
                    for edge
                    in edges
                ),

            "all_edge_nodes_resolved":
                not missing_edge_nodes,

            "module_graph_reference_valid":
                graph_reference
                == "graph/oriel.json",

            "authority_transfer":
                False,
        },

        "missing_edge_nodes":
            missing_edge_nodes,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
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


def status() -> dict[str, Any]:
    value = projection()

    validation = value[
        "validation"
    ]

    ready = bool(
        validation[
            "carbon_identity_preserved"
        ]
        and validation[
            "oriel_is_specialization"
        ]
        and not validation[
            "oriel_is_peer_exile"
        ]
        and validation[
            "carbon_owns_simulation"
        ]
        and validation[
            "simulation_substantiates_oriel"
        ]
        and validation[
            "all_edge_nodes_resolved"
        ]
        and validation[
            "module_graph_reference_valid"
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

        "carbon_node_id":
            value[
                "carbon_node_id"
            ],

        "oriel_specialization_id":
            value[
                "oriel_specialization_id"
            ],

        "node_count":
            value[
                "node_count"
            ],

        "edge_count":
            value[
                "edge_count"
            ],

        "oriel_is_peer_exile":
            validation[
                "oriel_is_peer_exile"
            ],

        "authority_transfer":
            False,

        "ready":
            ready,
    }


def selftest() -> dict[str, Any]:
    value = projection()

    validation = value[
        "validation"
    ]

    required_true = (
        "carbon_identity_preserved",
        "oriel_is_specialization",
        "carbon_owns_simulation",
        "simulation_substantiates_oriel",
        "all_edge_nodes_resolved",
        "module_graph_reference_valid",
    )

    failed = [
        key
        for key
        in required_true
        if not validation.get(
            key
        )
    ]

    if failed:
        raise oriel_graph_error(
            (
                "oriel graph selftest failed: "
                + ", ".join(
                    failed
                )
            )
        )

    if validation[
        "oriel_is_peer_exile"
    ]:
        raise oriel_graph_error(
            (
                "oriel was incorrectly "
                "projected as a peer exile"
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

        "carbon_identity_preserved":
            True,

        "oriel_graph_addressable":
            True,

        "oriel_is_contained_specialization":
            True,

        "oriel_is_peer_exile":
            False,

        "all_edge_nodes_resolved":
            True,

        "carbon_remains_simulation_owner":
            True,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "projection",
    "selftest",
    "status",
]
