#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from itertools import combinations
from typing import Any, Iterable, Mapping

from .model import (
    AllianceContract,
    DirectLineageEdge,
    KinshipLookupError,
    KinshipNode,
    KinshipValidationError,
    stable_alliance_id,
)
from .registry import KinshipRegistry


ACTIVE_STATES = {
    "active",
    "accepted",
    "current",
    "example",
    "provisional",
}


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return deepcopy(
            dict(value)
        )

    return {}


def _strings(
    value: Any,
) -> tuple[str, ...]:
    if isinstance(
        value,
        str,
    ):
        value = [
            value
        ]

    if not isinstance(
        value,
        (list, tuple, set),
    ):
        return ()

    result: list[str] = []

    for item in value:
        normalized = str(
            item
        ).strip()

        if (
            normalized
            and normalized not in result
        ):
            result.append(
                normalized
            )

    return tuple(
        result
    )


class KinshipGraph:
    def __init__(
        self,
        *,
        nodes: Mapping[
            str,
            KinshipNode,
        ],
        lineage_edges: Mapping[
            str,
            DirectLineageEdge,
        ],
        alliances: Mapping[
            str,
            AllianceContract,
        ],
        other_edges: Iterable[
            Mapping[str, Any]
        ] = (),
        source_runtime_hash: str = "",
        source_lineage_hash: str = "",
    ) -> None:
        self.nodes = dict(
            nodes
        )

        self.lineage_edges = dict(
            lineage_edges
        )

        self.alliances = dict(
            alliances
        )

        self.other_edges = tuple(
            deepcopy(
                dict(edge)
            )
            for edge in other_edges
        )

        self.source_runtime_hash = (
            source_runtime_hash
        )

        self.source_lineage_hash = (
            source_lineage_hash
        )

        self._incoming: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self._outgoing: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self._alliances_by_node: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self._aliases: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for node_id, node in self.nodes.items():
            aliases = {
                node_id,
                node.canonical_id,
                node.label,
            }

            if node.path:
                aliases.add(
                    node.path
                )

            for alias in aliases:
                normalized = str(
                    alias
                ).strip()

                if normalized:
                    self._aliases[
                        normalized.casefold()
                    ].add(
                        node_id
                    )

        for edge_id, edge in (
            self.lineage_edges.items()
        ):
            if edge.parent not in self.nodes:
                raise KinshipValidationError(
                    "lineage parent missing "
                    f"from graph: {edge.parent}"
                )

            if edge.child not in self.nodes:
                raise KinshipValidationError(
                    "lineage child missing "
                    f"from graph: {edge.child}"
                )

            self._outgoing[
                edge.parent
            ].append(
                edge_id
            )

            self._incoming[
                edge.child
            ].append(
                edge_id
            )

        for alliance_id, alliance in (
            self.alliances.items()
        ):
            for partner in alliance.partners:
                if partner not in self.nodes:
                    raise KinshipValidationError(
                        "alliance partner missing "
                        f"from graph: {partner}"
                    )

                self._alliances_by_node[
                    partner
                ].append(
                    alliance_id
                )

        for node_id in self.nodes:
            self._incoming[
                node_id
            ].sort()

            self._outgoing[
                node_id
            ].sort()

            self._alliances_by_node[
                node_id
            ].sort()

    @classmethod
    def from_runtime_graph(
        cls,
        payload: Mapping[
            str,
            Any,
        ],
        *,
        registry: KinshipRegistry,
    ) -> "KinshipGraph":
        raw_nodes = payload.get(
            "nodes",
            [],
        )

        raw_edges = payload.get(
            "edges",
            [],
        )

        if not isinstance(
            raw_nodes,
            list,
        ):
            raise KinshipValidationError(
                "runtime graph nodes "
                "must be an array"
            )

        if not isinstance(
            raw_edges,
            list,
        ):
            raise KinshipValidationError(
                "runtime graph edges "
                "must be an array"
            )

        nodes: dict[
            str,
            KinshipNode,
        ] = {}

        for raw_node in raw_nodes:
            if not isinstance(
                raw_node,
                Mapping,
            ):
                raise KinshipValidationError(
                    "runtime graph node "
                    "must be an object"
                )

            node_id = str(
                raw_node.get(
                    "id",
                    "",
                )
            ).strip()

            if not node_id:
                raise KinshipValidationError(
                    "runtime graph node "
                    "lacks id"
                )

            if node_id in nodes:
                raise KinshipValidationError(
                    "duplicate runtime node "
                    f"id: {node_id}"
                )

            nodes[
                node_id
            ] = KinshipNode(
                id=node_id,
                canonical_id=str(
                    raw_node.get(
                        "canonical_id",
                        node_id,
                    )
                ),
                label=str(
                    raw_node.get(
                        "label",
                        node_id,
                    )
                ),
                kind=str(
                    raw_node.get(
                        "kind",
                        "instance",
                    )
                ),
                authority=bool(
                    raw_node.get(
                        "authority",
                        False,
                    )
                ),
                path=(
                    str(
                        raw_node[
                            "path"
                        ]
                    )
                    if raw_node.get(
                        "path"
                    )
                    else None
                ),
                metadata=_mapping(
                    raw_node.get(
                        "metadata"
                    )
                ),
                provenance=_mapping(
                    raw_node.get(
                        "provenance"
                    )
                ),
            )

        lineage_edges: dict[
            str,
            DirectLineageEdge,
        ] = {}

        alliances: dict[
            str,
            AllianceContract,
        ] = {}

        other_edges: list[
            dict[str, Any]
        ] = []

        for index, raw_edge in enumerate(
            raw_edges
        ):
            if not isinstance(
                raw_edge,
                Mapping,
            ):
                raise KinshipValidationError(
                    "runtime graph edge "
                    "must be an object"
                )

            edge = deepcopy(
                dict(raw_edge)
            )

            edge_id = str(
                edge.get(
                    "id",
                    "",
                )
            ).strip() or (
                f"runtime-edge-"
                f"{index:08d}"
            )

            plane = str(
                edge.get(
                    "relationship_plane",
                    "lineage",
                )
            ).strip() or "lineage"

            if plane == "alliance":
                partners = _strings(
                    edge.get(
                        "partners"
                    )
                )

                if not partners:
                    partners = _strings([
                        edge.get(
                            "source"
                        ),
                        edge.get(
                            "target"
                        ),
                    ])

                profile = str(
                    edge.get(
                        "alliance_profile",
                        "partner",
                    )
                )

                registry.alliance_profile(
                    profile
                )

                domains = _strings(
                    edge.get(
                        "domains",
                        edge.get(
                            "domain"
                        ),
                    )
                )

                alliance_id = (
                    edge_id
                    or stable_alliance_id(
                        partners,
                        profile,
                        domains,
                    )
                )

                alliances[
                    alliance_id
                ] = AllianceContract(
                    id=alliance_id,
                    partners=partners,
                    profile=profile,
                    domains=domains,
                    status=str(
                        edge.get(
                            "status",
                            "active",
                        )
                    ),
                    contract=_mapping(
                        edge.get(
                            "contract"
                        )
                    ),
                    provenance=_mapping(
                        edge.get(
                            "provenance"
                        )
                    ),
                    metadata=_mapping(
                        edge.get(
                            "metadata"
                        )
                    ),
                )

                continue

            if plane != "lineage":
                other_edges.append(
                    edge
                )
                continue

            parent = str(
                edge.get(
                    "source",
                    edge.get(
                        "parent",
                        "",
                    ),
                )
            ).strip()

            child = str(
                edge.get(
                    "target",
                    edge.get(
                        "child",
                        "",
                    ),
                )
            ).strip()

            if not parent or not child:
                raise KinshipValidationError(
                    "lineage edge requires "
                    "parent/source and "
                    "child/target"
                )

            role = str(
                edge.get(
                    "role",
                    edge.get(
                        "kind",
                        "generic",
                    ),
                )
            ).strip() or "generic"

            continuation = str(
                edge.get(
                    "continuation",
                    "neutral",
                )
            ).strip() or "neutral"

            kinship = _mapping(
                edge.get(
                    "kinship"
                )
            )

            metadata = _mapping(
                edge.get(
                    "metadata"
                )
            )

            metadata_kinship = (
                _mapping(
                    metadata.get(
                        "kinship"
                    )
                )
            )

            parent_profile = str(
                kinship.get(
                    "parent_profile"
                )
                or metadata_kinship.get(
                    "parent_profile"
                )
                or edge.get(
                    "symbolic_parent_alias"
                )
                or registry
                .default_parent_profile(
                    role
                )
            )

            child_profile = str(
                kinship.get(
                    "child_profile"
                )
                or metadata_kinship.get(
                    "child_profile"
                )
                or edge.get(
                    "symbolic_child_alias"
                )
                or registry
                .default_child_profile(
                    continuation
                )
            )

            registry.parent_profile(
                parent_profile
            )

            registry.child_profile(
                child_profile
            )

            function = _mapping(
                edge.get(
                    "function"
                )
            )

            domain = str(
                function.get(
                    "domain"
                )
                or edge.get(
                    "domain"
                )
                or metadata.get(
                    "domain"
                )
                or edge.get(
                    "scope",
                    "global",
                )
            )

            lineage_edges[
                edge_id
            ] = DirectLineageEdge(
                id=edge_id,
                parent=parent,
                child=child,
                role=role,
                axis=str(
                    function.get(
                        "axis"
                    )
                    or edge.get(
                        "axis",
                        "unspecified",
                    )
                ),
                domain=domain,
                parent_profile=(
                    parent_profile
                ),
                child_profile=(
                    child_profile
                ),
                continuation=(
                    continuation
                ),
                scope=str(
                    edge.get(
                        "scope",
                        "global",
                    )
                ),
                order=int(
                    edge.get(
                        "order",
                        0,
                    )
                ),
                status=str(
                    edge.get(
                        "status",
                        "active",
                    )
                ),
                inheritance=_mapping(
                    edge.get(
                        "inheritance"
                    )
                ),
                propagation=_mapping(
                    edge.get(
                        "propagation"
                    )
                ),
                contribution=_mapping(
                    edge.get(
                        "contribution"
                    )
                ),
                generation_event=(
                    str(
                        kinship.get(
                            "generation_event"
                        )
                    )
                    if kinship.get(
                        "generation_event"
                    )
                    else None
                ),
                provenance=_mapping(
                    edge.get(
                        "provenance"
                    )
                ),
                metadata=metadata,
            )

        raw_alliances = payload.get(
            "alliances",
            [],
        )

        if raw_alliances is None:
            raw_alliances = []

        if not isinstance(
            raw_alliances,
            list,
        ):
            raise KinshipValidationError(
                "runtime graph alliances "
                "must be an array"
            )

        for raw_alliance in raw_alliances:
            if not isinstance(
                raw_alliance,
                Mapping,
            ):
                raise KinshipValidationError(
                    "alliance must be "
                    "an object"
                )

            partners = _strings(
                raw_alliance.get(
                    "partners"
                )
            )

            profile = str(
                raw_alliance.get(
                    "alliance_profile",
                    raw_alliance.get(
                        "profile",
                        "partner",
                    ),
                )
            )

            registry.alliance_profile(
                profile
            )

            domains = _strings(
                raw_alliance.get(
                    "domains"
                )
            )

            alliance_id = str(
                raw_alliance.get(
                    "id",
                    "",
                )
            ).strip() or (
                stable_alliance_id(
                    partners,
                    profile,
                    domains,
                )
            )

            alliances[
                alliance_id
            ] = AllianceContract(
                id=alliance_id,
                partners=partners,
                profile=profile,
                domains=domains,
                status=str(
                    raw_alliance.get(
                        "status",
                        "active",
                    )
                ),
                contract=_mapping(
                    raw_alliance.get(
                        "contract"
                    )
                ),
                provenance=_mapping(
                    raw_alliance.get(
                        "provenance"
                    )
                ),
                metadata=_mapping(
                    raw_alliance.get(
                        "metadata"
                    )
                ),
            )

        return cls(
            nodes=nodes,
            lineage_edges=(
                lineage_edges
            ),
            alliances=alliances,
            other_edges=other_edges,
            source_runtime_hash=str(
                payload.get(
                    "deterministic_hash",
                    "",
                )
            ),
            source_lineage_hash=str(
                payload.get(
                    "source_lineage_hash",
                    "",
                )
            ),
        )

    def resolve_node_id(
        self,
        identifier: str,
    ) -> str:
        raw = str(
            identifier
        ).strip()

        if raw in self.nodes:
            return raw

        candidates = sorted(
            self._aliases.get(
                raw.casefold(),
                set(),
            )
        )

        if not candidates:
            raise KinshipLookupError(
                "kinship node not found: "
                f"{identifier}"
            )

        if len(
            candidates
        ) > 1:
            raise KinshipLookupError(
                "kinship node identifier "
                f"is ambiguous: {identifier} "
                "-> "
                + ", ".join(
                    candidates
                )
            )

        return candidates[0]

    def node(
        self,
        identifier: str,
    ) -> KinshipNode:
        return self.nodes[
            self.resolve_node_id(
                identifier
            )
        ]

    def incoming_edges(
        self,
        identifier: str,
        *,
        active_only: bool = True,
        domain: str | None = None,
    ) -> list[
        DirectLineageEdge
    ]:
        node_id = self.resolve_node_id(
            identifier
        )

        result: list[
            DirectLineageEdge
        ] = []

        for edge_id in self._incoming[
            node_id
        ]:
            edge = self.lineage_edges[
                edge_id
            ]

            if (
                active_only
                and edge.status
                not in ACTIVE_STATES
            ):
                continue

            if (
                domain is not None
                and edge.domain != domain
            ):
                continue

            result.append(
                edge
            )

        return result

    def outgoing_edges(
        self,
        identifier: str,
        *,
        active_only: bool = True,
        domain: str | None = None,
    ) -> list[
        DirectLineageEdge
    ]:
        node_id = self.resolve_node_id(
            identifier
        )

        result: list[
            DirectLineageEdge
        ] = []

        for edge_id in self._outgoing[
            node_id
        ]:
            edge = self.lineage_edges[
                edge_id
            ]

            if (
                active_only
                and edge.status
                not in ACTIVE_STATES
            ):
                continue

            if (
                domain is not None
                and edge.domain != domain
            ):
                continue

            result.append(
                edge
            )

        return result

    def parents(
        self,
        identifier: str,
        *,
        active_only: bool = True,
        domain: str | None = None,
    ) -> list[str]:
        return sorted({
            edge.parent
            for edge in self.incoming_edges(
                identifier,
                active_only=active_only,
                domain=domain,
            )
        })

    def children(
        self,
        identifier: str,
        *,
        active_only: bool = True,
        domain: str | None = None,
    ) -> list[str]:
        return sorted({
            edge.child
            for edge in self.outgoing_edges(
                identifier,
                active_only=active_only,
                domain=domain,
            )
        })

    def alliance_contracts(
        self,
        identifier: str,
        *,
        active_only: bool = True,
    ) -> list[
        AllianceContract
    ]:
        node_id = self.resolve_node_id(
            identifier
        )

        result: list[
            AllianceContract
        ] = []

        for alliance_id in (
            self._alliances_by_node[
                node_id
            ]
        ):
            alliance = self.alliances[
                alliance_id
            ]

            if (
                active_only
                and alliance.status
                not in ACTIVE_STATES
            ):
                continue

            result.append(
                alliance
            )

        return result

    def partners(
        self,
        identifier: str,
        *,
        active_only: bool = True,
    ) -> list[str]:
        node_id = self.resolve_node_id(
            identifier
        )

        result: set[str] = set()

        for alliance in (
            self.alliance_contracts(
                node_id,
                active_only=active_only,
            )
        ):
            result.update(
                partner
                for partner
                in alliance.partners
                if partner != node_id
            )

        return sorted(
            result
        )

    def sibling_candidates(
        self,
        identifier: str,
        *,
        active_only: bool = True,
        domain: str | None = None,
    ) -> list[str]:
        node_id = self.resolve_node_id(
            identifier
        )

        result: set[str] = set()

        for parent in self.parents(
            node_id,
            active_only=active_only,
            domain=domain,
        ):
            result.update(
                self.children(
                    parent,
                    active_only=active_only,
                    domain=domain,
                )
            )

        result.discard(
            node_id
        )

        return sorted(
            result
        )

    def alliance_pairs(
        self,
    ) -> list[
        tuple[
            AllianceContract,
            str,
            str,
        ]
    ]:
        result: list[
            tuple[
                AllianceContract,
                str,
                str,
            ]
        ] = []

        for alliance in sorted(
            self.alliances.values(),
            key=lambda item: item.id,
        ):
            for left, right in combinations(
                sorted(
                    alliance.partners
                ),
                2,
            ):
                result.append(
                    (
                        alliance,
                        left,
                        right,
                    )
                )

        return result


__all__ = [
    "ACTIVE_STATES",
    "KinshipGraph",
]
