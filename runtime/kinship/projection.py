#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from .algebra import KindredAlgebra
from .graph import KindredGraph
from .model import FamilyTreeProjection
from .registry import KindredRegistry


class FamilyTreeProjector:
    def __init__(
        self,
        graph: KindredGraph,
        registry: KindredRegistry,
    ) -> None:
        self.graph = graph
        self.registry = registry
        self.algebra = KindredAlgebra(
            graph,
            registry,
        )

    def project(
        self,
        focus_identifier: str,
        *,
        max_depth: int = 3,
        active_only: bool = True,
        domain: str | None = None,
        include_extended: bool = True,
        include_derived_edges: bool = True,
    ) -> FamilyTreeProjection:
        focus = self.graph.resolve_node_id(
            focus_identifier
        )

        determinations = (
            self.algebra
            .family_determinations(
                focus,
                max_depth=max_depth,
                active_only=active_only,
                domain=domain,
                include_extended=(
                    include_extended
                ),
            )
        )

        included_nodes: set[str] = {
            focus
        }

        relation_map: dict[
            str,
            list[dict[str, Any]],
        ] = defaultdict(list)

        generation_candidates: dict[
            str,
            list[int],
        ] = defaultdict(list)

        generation_candidates[
            focus
        ].append(
            0
        )

        for determination in (
            determinations
        ):
            included_nodes.add(
                determination.relative
            )

            included_nodes.update(
                determination.shared_ancestors
            )

            included_nodes.update(
                determination.shared_parents
            )

            relation_map[
                determination.relative
            ].append(
                determination.to_dict()
            )

            generation_candidates[
                determination.relative
            ].append(
                determination
                .generation_offset
            )

            for ancestor in (
                determination
                .shared_ancestors
            ):
                generation_candidates[
                    ancestor
                ].append(
                    min(
                        -1,
                        determination
                        .generation_offset
                        - 1,
                    )
                )

            for parent in (
                determination
                .shared_parents
            ):
                generation_candidates[
                    parent
                ].append(
                    -1
                )

            for step in determination.path:
                included_nodes.add(
                    step.source
                )

                included_nodes.add(
                    step.target
                )

        for node_id in list(
            included_nodes
        ):
            included_nodes.update(
                self.graph.partners(
                    node_id,
                    active_only=active_only,
                )
            )

        generation: dict[
            str,
            int,
        ] = {}

        for node_id in sorted(
            included_nodes
        ):
            candidates = (
                generation_candidates.get(
                    node_id,
                    []
                )
            )

            if candidates:
                generation[
                    node_id
                ] = min(
                    candidates,
                    key=lambda value: (
                        abs(
                            value
                        ),
                        value,
                    ),
                )
            else:
                generation[
                    node_id
                ] = 0

        nodes: list[
            dict[str, Any]
        ] = []

        for node_id in sorted(
            included_nodes,
            key=lambda item: (
                generation.get(
                    item,
                    0,
                ),
                self.graph.nodes[
                    item
                ].label.casefold(),
                item,
            ),
        ):
            node = self.graph.nodes[
                node_id
            ]

            nodes.append({
                **node.to_dict(),
                "generation": generation.get(
                    node_id,
                    0,
                ),
                "focus": (
                    node_id == focus
                ),
                "relationships_to_focus": (
                    relation_map.get(
                        node_id,
                        []
                    )
                ),
            })

        edges: list[
            dict[str, Any]
        ] = []

        for edge in sorted(
            self.graph
            .lineage_edges
            .values(),
            key=lambda item: (
                item.parent,
                item.child,
                item.order,
                item.id,
            ),
        ):
            if (
                edge.parent
                not in included_nodes
                or edge.child
                not in included_nodes
            ):
                continue

            if (
                active_only
                and edge.status
                not in {
                    "active",
                    "accepted",
                    "current",
                    "example",
                    "provisional",
                }
            ):
                continue

            if (
                domain is not None
                and edge.domain != domain
            ):
                continue

            edges.append({
                "id": edge.id,
                "kind": (
                    "direct_lineage"
                ),
                "source": edge.parent,
                "target": edge.child,
                "directed": True,
                "role": edge.role,
                "axis": edge.axis,
                "domain": edge.domain,
                "parent_profile": (
                    edge.parent_profile
                ),
                "child_profile": (
                    edge.child_profile
                ),
                "continuation": (
                    edge.continuation
                ),
                "status": edge.status,
                "generation_event": (
                    edge.generation_event
                ),
                "inheritance": deepcopy(
                    dict(
                        edge.inheritance
                    )
                ),
                "propagation": deepcopy(
                    dict(
                        edge.propagation
                    )
                ),
                "contribution": deepcopy(
                    dict(
                        edge.contribution
                    )
                ),
                "provenance": deepcopy(
                    dict(
                        edge.provenance
                    )
                ),
            })

        for alliance, left, right in (
            self.graph.alliance_pairs()
        ):
            if (
                left not in included_nodes
                or right
                not in included_nodes
            ):
                continue

            if (
                active_only
                and alliance.status
                not in {
                    "active",
                    "accepted",
                    "current",
                    "example",
                    "provisional",
                }
            ):
                continue

            edges.append({
                "id": (
                    alliance.id
                    + ":"
                    + left
                    + ":"
                    + right
                ),
                "alliance_id": (
                    alliance.id
                ),
                "kind": "alliance",
                "source": left,
                "target": right,
                "directed": False,
                "alliance_profile": (
                    alliance.profile
                ),
                "domains": list(
                    alliance.domains
                ),
                "status": (
                    alliance.status
                ),
                "contract": deepcopy(
                    dict(
                        alliance.contract
                    )
                ),
                "provenance": deepcopy(
                    dict(
                        alliance.provenance
                    )
                ),
            })

        if include_derived_edges:
            for determination in (
                determinations
            ):
                if determination.relative == focus:
                    continue

                if (
                    determination
                    .generation_offset
                    in {
                        -1,
                        1,
                    }
                    and determination.path
                ):
                    continue

                edges.append({
                    "id": (
                        "derived:"
                        + determination
                        .deterministic_hash
                    ),
                    "kind": (
                        "derived_kindred"
                    ),
                    "source": focus,
                    "target": (
                        determination.relative
                    ),
                    "directed": False,
                    "relationship": (
                        determination
                        .relationship
                    ),
                    "generation_offset": (
                        determination
                        .generation_offset
                    ),
                    "domains": list(
                        determination.domains
                    ),
                    "shared_ancestors": list(
                        determination
                        .shared_ancestors
                    ),
                    "shared_parents": list(
                        determination
                        .shared_parents
                    ),
                    "alliance_ids": list(
                        determination
                        .alliance_ids
                    ),
                    "proof_path": [
                        step.to_dict()
                        for step
                        in determination.path
                    ],
                    "rule": (
                        determination.rule
                    ),
                    "confidence": (
                        determination.confidence
                    ),
                })

        edges.sort(
            key=lambda item: (
                item[
                    "kind"
                ],
                item[
                    "source"
                ],
                item[
                    "target"
                ],
                item[
                    "id"
                ],
            )
        )

        generations: dict[
            str,
            list[str],
        ] = defaultdict(list)

        for node_id in sorted(
            included_nodes,
            key=lambda item: (
                generation.get(
                    item,
                    0,
                ),
                self.graph.nodes[
                    item
                ].label.casefold(),
                item,
            ),
        ):
            generations[
                str(
                    generation.get(
                        node_id,
                        0,
                    )
                )
            ].append(
                node_id
            )

        return FamilyTreeProjection(
            focus=focus,
            nodes=nodes,
            edges=edges,
            generations={
                key: value
                for key, value
                in sorted(
                    generations.items(),
                    key=lambda item: int(
                        item[0]
                    ),
                )
            },
            determinations=[
                determination.to_dict()
                for determination
                in determinations
            ],
            source_runtime_hash=(
                self.graph
                .source_runtime_hash
            ),
            source_lineage_hash=(
                self.graph
                .source_lineage_hash
            ),
            registry_id=(
                self.registry.registry_id
            ),
            registry_version=(
                self.registry.version
            ),
            options={
                "max_depth": max_depth,
                "active_only": (
                    active_only
                ),
                "domain": domain,
                "include_extended": (
                    include_extended
                ),
                "include_derived_edges": (
                    include_derived_edges
                ),
            },
        )


__all__ = [
    "FamilyTreeProjector",
]
