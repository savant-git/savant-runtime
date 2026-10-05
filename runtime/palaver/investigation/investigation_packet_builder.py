#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping


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

from runtime.palaver.contracts.investigation_contract import (  # noqa: E402
    InvestigationPacket,
)

from runtime.palaver.graph.runtime_graph_index import (  # noqa: E402
    RuntimeGraphIndex,
)


DEFAULT_GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)

DEFAULT_AUTHORITY = (
    ROOT
    / "vault"
    / "authority"
    / "authority_index.json"
)

DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "vault"
    / "investigations"
)


def read_json(
    path: Path,
    *,
    required: bool = True,
) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise FileNotFoundError(
                f"required JSON file missing: {path}"
            )

        return {}

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise TypeError(
            f"JSON root must be an object: {path}"
        )

    return dict(
        payload
    )


def _authority_lookup(
    payload: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(
        payload,
        Mapping,
    ):
        return {}

    records = payload.get(
        "records",
        []
    )

    if not isinstance(
        records,
        list,
    ):
        return {}

    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:
        if not isinstance(
            record,
            Mapping,
        ):
            continue

        node_id = str(
            record.get(
                "id",
                "",
            )
        ).strip()

        if node_id:
            result[
                node_id
            ] = dict(
                record
            )

    return result


def _resolve_starting_nodes(
    index: RuntimeGraphIndex,
    explicit_nodes: Iterable[str],
    *,
    objective: str,
    limit: int = 5,
) -> list[str]:
    resolved: list[str] = []

    for identifier in explicit_nodes:
        node_id = index.resolve_node_id(
            identifier
        )

        if node_id not in resolved:
            resolved.append(
                node_id
            )

    if resolved:
        return resolved

    results = index.search(
        objective,
        limit=max(
            1,
            limit,
        ),
    )

    for result in results:
        node_id = str(
            result["id"]
        )

        if node_id not in resolved:
            resolved.append(
                node_id
            )

    if resolved:
        return resolved

    roots = [
        node_id
        for node_id
        in index.node_ids()
        if not index.incoming_edges(
            node_id
        )
    ]

    return roots[
        :max(
            1,
            limit,
        )
    ]


def _metadata_contradictions(
    node: Mapping[
        str,
        Any,
    ],
) -> list[str]:
    metadata = node.get(
        "metadata"
    )

    if not isinstance(
        metadata,
        Mapping,
    ):
        return []

    values = metadata.get(
        "contradictions",
        []
    )

    if isinstance(
        values,
        str,
    ):
        return [
            values
        ]

    if not isinstance(
        values,
        list,
    ):
        return []

    return [
        str(value)
        for value in values
        if str(
            value
        ).strip()
    ]


def build_investigation(
    index: RuntimeGraphIndex,
    *,
    title: str,
    objective: str,
    starting_nodes: Iterable[str] = (),
    direction: str = "both",
    roles: Iterable[str] | None = None,
    depth: int = 3,
    authority_payload: Mapping[
        str,
        Any,
    ] | None = None,
    notes: Iterable[str] = (),
) -> InvestigationPacket:
    resolved_starts = (
        _resolve_starting_nodes(
            index,
            starting_nodes,
            objective=objective,
        )
    )

    role_filter = (
        [
            str(role)
            for role in roles
            if str(role).strip()
        ]
        if roles is not None
        else None
    )

    traversal: list[
        dict[str, Any]
    ] = []

    traversed_nodes: set[str] = set(
        resolved_starts
    )

    traversed_edges: set[str] = set()

    for start in resolved_starts:
        branch = index.traverse(
            start,
            direction=direction,
            roles=role_filter,
            max_depth=max(
                0,
                depth,
            ),
            include_start=True,
        )

        for item in branch:
            enriched = deepcopy(
                item
            )

            enriched[
                "starting_node"
            ] = start

            traversal.append(
                enriched
            )

            traversed_nodes.add(
                str(
                    item["id"]
                )
            )

            edge_id = item.get(
                "via_edge"
            )

            if edge_id:
                traversed_edges.add(
                    str(
                        edge_id
                    )
                )

    traversal.sort(
        key=lambda item: (
            str(
                item[
                    "starting_node"
                ]
            ),
            int(
                item.get(
                    "depth",
                    0,
                )
            ),
            str(
                item["id"]
            ),
            str(
                item.get(
                    "via_edge",
                    "",
                )
            ),
        )
    )

    authority_lookup = _authority_lookup(
        authority_payload
    )

    authority_sources: set[str] = set()
    dependencies: set[str] = set()
    contradictions: set[str] = set()
    uncertainty_regions: set[str] = set()
    recovery_routes: set[str] = set()

    for node_id in sorted(
        traversed_nodes
    ):
        node = index.node(
            node_id
        )

        authority_record = (
            authority_lookup.get(
                node_id
            )
        )

        if authority_record:
            if (
                authority_record.get(
                    "explicit_authority",
                    False,
                )
                or int(
                    authority_record.get(
                        "authority_score",
                        0,
                    )
                    or 0
                )
                >= 75
            ):
                authority_sources.add(
                    node_id
                )

            authority_sources.update(
                str(value)
                for value
                in authority_record.get(
                    "direct_authority_sources",
                    []
                )
            )

        elif node.get(
            "authority",
            False,
        ):
            authority_sources.add(
                node_id
            )

        for edge in index.incoming_edges(
            node_id,
            roles=[
                "dependency"
            ],
            active_only=False,
        ):
            dependencies.add(
                str(
                    edge["source"]
                )
            )

            traversed_edges.add(
                str(
                    edge["id"]
                )
            )

        metadata = node.get(
            "metadata"
        )

        if (
            isinstance(
                metadata,
                Mapping,
            )
            and metadata.get(
                "lineage_placeholder",
                False,
            )
        ):
            uncertainty_regions.add(
                node_id
            )

        if not node.get(
            "provenance"
        ):
            uncertainty_regions.add(
                node_id
            )

        contradictions.update(
            _metadata_contradictions(
                node
            )
        )

        routes = node.get(
            "recovery_routes",
            []
        )

        if isinstance(
            routes,
            str,
        ):
            routes = [
                routes
            ]

        if isinstance(
            routes,
            list,
        ):
            recovery_routes.update(
                str(route)
                for route in routes
                if str(
                    route
                ).strip()
            )

    packet_identity = stable_hash({
        "title": title,
        "objective": objective,
        "starting_nodes": (
            resolved_starts
        ),
        "direction": direction,
        "roles": (
            role_filter
            or []
        ),
        "depth": max(
            0,
            depth,
        ),
        "source_runtime_hash": (
            index.deterministic_hash
        ),
        "source_lineage_hash": (
            index.source_lineage_hash
        ),
    })[:24]

    authority_hash = ""

    if isinstance(
        authority_payload,
        Mapping,
    ):
        authority_hash = str(
            authority_payload.get(
                "deterministic_hash",
                "",
            )
        )

    packet = InvestigationPacket(
        id=(
            "investigation."
            + packet_identity
        ),
        title=title,
        objective=objective,
        source_runtime_hash=(
            index.deterministic_hash
        ),
        source_lineage_hash=(
            index.source_lineage_hash
        ),
        source_authority_hash=(
            authority_hash
        ),
        starting_nodes=(
            resolved_starts
        ),
        traversed_nodes=sorted(
            traversed_nodes
        ),
        traversed_edges=sorted(
            traversed_edges
        ),
        authority_sources=sorted(
            authority_sources
        ),
        dependencies=sorted(
            dependencies
        ),
        contradictions=sorted(
            contradictions
        ),
        uncertainty_regions=sorted(
            uncertainty_regions
        ),
        recovery_routes=sorted(
            recovery_routes
        ),
        traversal=traversal,
        notes=[
            str(note)
            for note in notes
        ],
        metadata={
            "direction": direction,
            "roles": (
                role_filter
                or []
            ),
            "depth": max(
                0,
                depth,
            ),
            "node_count": len(
                traversed_nodes
            ),
            "edge_count": len(
                traversed_edges
            ),
        },
    )

    return packet.finalize()


def write_investigation(
    packet: InvestigationPacket,
    output_root: Path = (
        DEFAULT_OUTPUT_ROOT
    ),
) -> tuple[
    Path,
    Path,
]:
    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    packet_path = (
        output_root
        / f"{packet.id}.json"
    )

    payload = packet.to_dict()

    packet_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    latest_path = (
        output_root
        / "latest.json"
    )

    latest_payload = {
        "schema": (
            "savant."
            "investigation_pointer.v1"
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "id": packet.id,
        "path": str(
            packet_path
        ),
        "deterministic_hash": (
            packet.deterministic_hash
        ),
        "source_runtime_hash": (
            packet.source_runtime_hash
        ),
        "source_lineage_hash": (
            packet.source_lineage_hash
        ),
        "source_authority_hash": (
            packet.source_authority_hash
        ),
    }

    latest_path.write_text(
        json.dumps(
            latest_payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return (
        packet_path,
        latest_path,
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a graph-addressable "
            "Palaver investigation packet."
        )
    )

    parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_GRAPH,
    )

    parser.add_argument(
        "--authority",
        type=Path,
        default=DEFAULT_AUTHORITY,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )

    parser.add_argument(
        "--title",
        default=(
            "runtime investigation"
        ),
    )

    parser.add_argument(
        "--objective",
        default=(
            "discover structural truth"
        ),
    )

    parser.add_argument(
        "--start",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--direction",
        choices=[
            "parents",
            "children",
            "both",
        ],
        default="both",
    )

    parser.add_argument(
        "--role",
        action="append",
        default=None,
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--note",
        action="append",
        default=[],
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    graph_payload = read_json(
        args.graph
    )

    authority_payload = read_json(
        args.authority,
        required=False,
    )

    index = RuntimeGraphIndex(
        graph_payload
    )

    packet = build_investigation(
        index,
        title=args.title,
        objective=args.objective,
        starting_nodes=args.start,
        direction=args.direction,
        roles=args.role,
        depth=max(
            0,
            args.depth,
        ),
        authority_payload=(
            authority_payload
        ),
        notes=args.note,
    )

    packet_path, latest_path = (
        write_investigation(
            packet,
            args.output_root,
        )
    )

    print(
        json.dumps(
            {
                "packet": str(
                    packet_path
                ),
                "latest": str(
                    latest_path
                ),
                "id": packet.id,
                "deterministic_hash": (
                    packet.deterministic_hash
                ),
                "starting_nodes": (
                    packet.starting_nodes
                ),
                "traversed_node_count": len(
                    packet.traversed_nodes
                ),
                "traversed_edge_count": len(
                    packet.traversed_edges
                ),
                "authority_source_count": len(
                    packet.authority_sources
                ),
                "uncertainty_region_count": len(
                    packet.uncertainty_regions
                ),
            },
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
