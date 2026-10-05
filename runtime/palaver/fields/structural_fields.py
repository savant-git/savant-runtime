#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import (
    Any,
    Mapping,
)


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).expanduser().absolute()

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from runtime.lineage.model import stable_hash  # noqa: E402

from runtime.palaver.graph.runtime_graph_index import (  # noqa: E402
    RuntimeGraphIndex,
)


GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)

OUT = (
    ROOT
    / "vault"
    / "fields"
    / "structural_fields.json"
)


INCOMING_AUTHORITY_WEIGHTS = {
    "authority": 45,
    "constraint": 32,
    "pattern": 26,
    "source": 26,
    "provenance": 18,
    "ownership": 15,
    "implementation": 12,
    "classification": 10,
    "composition": 4,
    "generic": 2,
}

OUTGOING_AUTHORITY_WEIGHTS = {
    "authority": 24,
    "constraint": 18,
    "pattern": 14,
    "source": 14,
    "provenance": 8,
    "ownership": 8,
    "implementation": 7,
    "classification": 5,
    "composition": 2,
    "generic": 1,
}


def _role_counts(
    edges: list[
        Mapping[str, Any]
    ],
) -> dict[str, int]:
    counts = Counter(
        str(
            edge.get(
                "role",
                "generic",
            )
        )
        for edge in edges
    )

    return dict(
        sorted(
            counts.items()
        )
    )


def _weighted_roles(
    counts: Mapping[
        str,
        int,
    ],
    weights: Mapping[
        str,
        int,
    ],
) -> int:
    return sum(
        int(count)
        * int(
            weights.get(
                role,
                1,
            )
        )
        for role, count
        in counts.items()
    )


def _inheritance_load(
    incoming_edges: list[
        Mapping[str, Any]
    ],
) -> int:
    total = 0

    for edge in incoming_edges:
        inheritance = edge.get(
            "inheritance"
        )

        if not isinstance(
            inheritance,
            Mapping,
        ):
            continue

        mode = str(
            inheritance.get(
                "mode",
                "reference",
            )
        )

        if mode == "merge":
            total += 3

        elif mode == "replace":
            total += 5

        elif mode == "reference":
            total += 1

        fields = inheritance.get(
            "fields",
            []
        )

        if isinstance(
            fields,
            list,
        ):
            total += len(
                fields
            )

    return total


def _propagation_pressure(
    outgoing_edges: list[
        Mapping[str, Any]
    ],
) -> int:
    total = 0

    for edge in outgoing_edges:
        propagation = edge.get(
            "propagation"
        )

        if not isinstance(
            propagation,
            Mapping,
        ):
            continue

        if not propagation.get(
            "enabled",
            True,
        ):
            continue

        channels = propagation.get(
            "channels",
            []
        )

        total += 1

        if isinstance(
            channels,
            list,
        ):
            total += len(
                channels
            )

    return total


def compile_structural_fields(
    graph_payload: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    index = RuntimeGraphIndex(
        graph_payload
    )

    fields: list[
        dict[str, Any]
    ] = []

    for node in index.node_records():
        node_id = str(
            node["id"]
        )

        incoming_edges = (
            index.incoming_edges(
                node_id,
                active_only=False,
            )
        )

        outgoing_edges = (
            index.outgoing_edges(
                node_id,
                active_only=False,
            )
        )

        incoming_by_role = (
            _role_counts(
                incoming_edges
            )
        )

        outgoing_by_role = (
            _role_counts(
                outgoing_edges
            )
        )

        family = index.family(
            node_id
        )

        neighbors = set(
            index.neighbors(
                node_id
            )
        )

        placeholder = bool(
            node.get(
                "metadata",
                {},
            ).get(
                "lineage_placeholder",
                False,
            )
            if isinstance(
                node.get(
                    "metadata"
                ),
                Mapping,
            )
            else False
        )

        authority_mass = (
            100
            if node.get(
                "authority",
                False,
            )
            else 0
        )

        authority_mass += (
            _weighted_roles(
                incoming_by_role,
                INCOMING_AUTHORITY_WEIGHTS,
            )
        )

        authority_mass += (
            _weighted_roles(
                outgoing_by_role,
                OUTGOING_AUTHORITY_WEIGHTS,
            )
        )

        dependency_pressure = (
            incoming_by_role.get(
                "dependency",
                0,
            )
            * 30
            + outgoing_by_role.get(
                "dependency",
                0,
            )
            * 12
        )

        relationship_density = len(
            neighbors
        )

        inheritance_load = (
            _inheritance_load(
                incoming_edges
            )
        )

        propagation_pressure = (
            _propagation_pressure(
                outgoing_edges
            )
        )

        source_mass = (
            incoming_by_role.get(
                "source",
                0,
            )
            * 30
            + outgoing_by_role.get(
                "source",
                0,
            )
            * 10
        )

        pattern_mass = (
            incoming_by_role.get(
                "pattern",
                0,
            )
            * 30
            + outgoing_by_role.get(
                "pattern",
                0,
            )
            * 10
        )

        context_mass = (
            incoming_by_role.get(
                "context",
                0,
            )
            * 20
            + outgoing_by_role.get(
                "context",
                0,
            )
            * 8
        )

        recovery_priority = 0

        if placeholder:
            recovery_priority += 100

        recovery_routes = node.get(
            "recovery_routes",
            []
        )

        if isinstance(
            recovery_routes,
            list,
        ):
            recovery_priority += (
                len(
                    recovery_routes
                )
                * 15
            )

        recovery_priority += (
            incoming_by_role.get(
                "supersession",
                0,
            )
            * 20
        )

        uncertainty_fog = 0

        if placeholder:
            uncertainty_fog += 100

        if not node.get(
            "provenance"
        ):
            uncertainty_fog += 20

        uncertainty_fog += (
            incoming_by_role.get(
                "generic",
                0,
            )
            * 5
        )

        uncertainty_fog += (
            outgoing_by_role.get(
                "generic",
                0,
            )
            * 3
        )

        if (
            not incoming_edges
            and node_id
            not in {
                "savant-runtime",
                "fs:.",
            }
        ):
            uncertainty_fog += 10

        continuation_in = Counter(
            str(
                edge.get(
                    "continuation",
                    "neutral",
                )
            )
            for edge in incoming_edges
        )

        continuation_out = Counter(
            str(
                edge.get(
                    "continuation",
                    "neutral",
                )
            )
            for edge in outgoing_edges
        )

        fields.append({
            "id": node_id,
            "canonical_id": (
                node.get(
                    "canonical_id",
                    node_id,
                )
            ),
            "label": node.get(
                "label",
                node_id,
            ),
            "kind": node.get(
                "kind",
                "unknown",
            ),
            "authority": bool(
                node.get(
                    "authority",
                    False,
                )
            ),
            "placeholder": (
                placeholder
            ),
            "authority_mass": (
                authority_mass
            ),
            "dependency_pressure": (
                dependency_pressure
            ),
            "relationship_density": (
                relationship_density
            ),
            "recovery_priority": (
                recovery_priority
            ),
            "uncertainty_fog": (
                uncertainty_fog
            ),
            "inheritance_load": (
                inheritance_load
            ),
            "propagation_pressure": (
                propagation_pressure
            ),
            "source_mass": (
                source_mass
            ),
            "pattern_mass": (
                pattern_mass
            ),
            "context_mass": (
                context_mass
            ),
            "incoming": len(
                incoming_edges
            ),
            "outgoing": len(
                outgoing_edges
            ),
            "parent_count": len(
                family["parents"]
            ),
            "mother_count": len(
                family["mothers"]
            ),
            "father_count": len(
                family["fathers"]
            ),
            "child_count": len(
                family["children"]
            ),
            "daughter_count": len(
                family["daughters"]
            ),
            "son_count": len(
                family["sons"]
            ),
            "incoming_by_role": (
                incoming_by_role
            ),
            "outgoing_by_role": (
                outgoing_by_role
            ),
            "continuation_in": dict(
                sorted(
                    continuation_in.items()
                )
            ),
            "continuation_out": dict(
                sorted(
                    continuation_out.items()
                )
            ),
        })

    fields.sort(
        key=lambda item: (
            -item[
                "authority_mass"
            ],
            -item[
                "dependency_pressure"
            ],
            -item[
                "relationship_density"
            ],
            item["id"],
        )
    )

    deterministic_core = {
        "schema": (
            "savant."
            "structural_fields.v2"
        ),
        "source_runtime_hash": (
            index.deterministic_hash
        ),
        "count": len(
            fields
        ),
        "fields": fields,
    }

    return {
        "schema": (
            "savant."
            "structural_fields.v2"
        ),
        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "source": (
            "runtime_graph"
        ),
        "source_runtime_hash": (
            index.deterministic_hash
        ),
        "source_lineage_hash": (
            index.source_lineage_hash
        ),
        "deterministic_hash": (
            stable_hash(
                deterministic_core
            )
        ),
        "count": len(
            fields
        ),
        "fields": fields,
    }


def main(
) -> int:
    if not GRAPH.is_file():
        raise SystemExit(
            "runtime graph missing"
        )

    graph_payload = json.loads(
        GRAPH.read_text(
            encoding="utf-8"
        )
    )

    payload = (
        compile_structural_fields(
            graph_payload
        )
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "output": str(
                    OUT
                ),
                "schema": payload[
                    "schema"
                ],
                "count": payload[
                    "count"
                ],
                "deterministic_hash": (
                    payload[
                        "deterministic_hash"
                    ]
                ),
                "source_runtime_hash": (
                    payload[
                        "source_runtime_hash"
                    ]
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
