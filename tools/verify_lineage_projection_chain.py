#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

RUNTIME_GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)

STRUCTURAL_FIELDS = (
    ROOT
    / "vault"
    / "fields"
    / "structural_fields.json"
)

TOPOLOGY_PROJECTION = (
    ROOT
    / "vault"
    / "graphs"
    / "topology_projection.json"
)


def read_json(
    path: Path,
) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"required projection missing: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(
            handle
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            f"projection must be an object: {path}"
        )

    return payload


def main() -> int:
    runtime = read_json(
        RUNTIME_GRAPH
    )

    fields = read_json(
        STRUCTURAL_FIELDS
    )

    topology = read_json(
        TOPOLOGY_PROJECTION
    )

    runtime_hash = runtime.get(
        "deterministic_hash"
    )

    lineage_hash = runtime.get(
        "source_lineage_hash"
    )

    assert runtime_hash, (
        "runtime graph lacks deterministic_hash"
    )

    assert lineage_hash, (
        "runtime graph lacks source_lineage_hash"
    )

    assert (
        fields.get(
            "source_runtime_hash"
        )
        == runtime_hash
    ), (
        "structural fields do not descend "
        "from the current runtime graph"
    )

    assert (
        topology.get(
            "source_runtime_hash"
        )
        == runtime_hash
    ), (
        "topology projection does not descend "
        "from the current runtime graph"
    )

    assert (
        fields.get(
            "source_lineage_hash"
        )
        == lineage_hash
    ), (
        "structural fields do not expose "
        "the current lineage provenance"
    )

    assert (
        topology.get(
            "source_lineage_hash"
        )
        == lineage_hash
    ), (
        "topology projection does not expose "
        "the current lineage provenance"
    )

    report = {
        "runtime_hash": runtime_hash,
        "lineage_hash": lineage_hash,
        "field_count": fields.get(
            "count",
            0,
        ),
        "topology_nodes": topology.get(
            "node_count",
            0,
        ),
        "topology_edges": topology.get(
            "edge_count",
            0,
        ),
        "components": topology.get(
            "component_count",
            0,
        ),
        "roles": topology.get(
            "role_counts",
            {},
        ),
        "verified": True,
    }

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
