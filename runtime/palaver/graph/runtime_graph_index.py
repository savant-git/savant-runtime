#!/usr/bin/env python3
from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
    deque,
)
from copy import deepcopy
import json
from pathlib import Path
from typing import (
    Any,
    Iterable,
    Mapping,
    Sequence,
)


class RuntimeGraphError(Exception):
    """Base runtime-graph index error."""


class RuntimeGraphValidationError(
    RuntimeGraphError
):
    """Raised when a runtime graph is malformed."""


class RuntimeGraphLookupError(
    RuntimeGraphError
):
    """Raised when a node identifier is unresolved or ambiguous."""


def _string_values(
    value: Any,
) -> list[str]:
    if isinstance(
        value,
        str,
    ):
        stripped = value.strip()

        return (
            [stripped]
            if stripped
            else []
        )

    if (
        not isinstance(
            value,
            Sequence,
        )
        or isinstance(
            value,
            (
                bytes,
                bytearray,
            ),
        )
    ):
        return []

    result: list[str] = []

    for item in value:
        if (
            isinstance(
                item,
                str,
            )
            and item.strip()
            and item.strip()
            not in result
        ):
            result.append(
                item.strip()
            )

    return result


def _casefold(
    value: Any,
) -> str:
    return str(
        value
        if value is not None
        else ""
    ).casefold()


class RuntimeGraphIndex:
    def __init__(
        self,
        payload: Mapping[
            str,
            Any,
        ],
    ) -> None:
        if not isinstance(
            payload,
            Mapping,
        ):
            raise RuntimeGraphValidationError(
                "runtime graph must be an object"
            )

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
            raise RuntimeGraphValidationError(
                "runtime graph nodes must be an array"
            )

        if not isinstance(
            raw_edges,
            list,
        ):
            raise RuntimeGraphValidationError(
                "runtime graph edges must be an array"
            )

        self.payload = deepcopy(
            dict(payload)
        )

        self.schema = str(
            payload.get(
                "schema",
                "",
            )
        )

        self.source_lineage_hash = str(
            payload.get(
                "source_lineage_hash",
                "",
            )
        )

        self.deterministic_hash = str(
            payload.get(
                "deterministic_hash",
                "",
            )
        )

        self._nodes: dict[
            str,
            dict[str, Any],
        ] = {}

        self._edges: dict[
            str,
            dict[str, Any],
        ] = {}

        self._incoming: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self._outgoing: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self._aliases: dict[
            str,
            set[str],
        ] = defaultdict(set)

        self._roles_by_node: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for raw_node in raw_nodes:
            if not isinstance(
                raw_node,
                Mapping,
            ):
                raise RuntimeGraphValidationError(
                    "runtime graph node must be an object"
                )

            node = deepcopy(
                dict(raw_node)
            )

            node_id = str(
                node.get(
                    "id",
                    "",
                )
            ).strip()

            if not node_id:
                raise RuntimeGraphValidationError(
                    "runtime graph node is missing id"
                )

            if node_id in self._nodes:
                raise RuntimeGraphValidationError(
                    "duplicate runtime graph node id: "
                    f"{node_id}"
                )

            self._nodes[
                node_id
            ] = node

            aliases = {
                node_id,
            }

            for key in (
                "canonical_id",
                "legacy_id",
                "path",
                "label",
            ):
                value = node.get(
                    key
                )

                if (
                    isinstance(
                        value,
                        str,
                    )
                    and value.strip()
                ):
                    aliases.add(
                        value.strip()
                    )

            metadata = node.get(
                "metadata"
            )

            if isinstance(
                metadata,
                Mapping,
            ):
                for key in (
                    "canonical_id",
                    "projected_id",
                    "source_path",
                ):
                    value = metadata.get(
                        key
                    )

                    if (
                        isinstance(
                            value,
                            str,
                        )
                        and value.strip()
                    ):
                        aliases.add(
                            value.strip()
                        )

            for alias in aliases:
                self._aliases[
                    alias.casefold()
                ].add(
                    node_id
                )

        for index, raw_edge in enumerate(
            raw_edges
        ):
            if not isinstance(
                raw_edge,
                Mapping,
            ):
                raise RuntimeGraphValidationError(
                    "runtime graph edge must be an object"
                )

            edge = deepcopy(
                dict(raw_edge)
            )

            edge_id = str(
                edge.get(
                    "id",
                    "",
                )
            ).strip()

            if not edge_id:
                edge_id = (
                    "runtime-edge-"
                    f"{index:08d}"
                )

                edge[
                    "id"
                ] = edge_id

            if edge_id in self._edges:
                raise RuntimeGraphValidationError(
                    "duplicate runtime graph edge id: "
                    f"{edge_id}"
                )

            source = str(
                edge.get(
                    "source",
                    "",
                )
            ).strip()

            target = str(
                edge.get(
                    "target",
                    "",
                )
            ).strip()

            if not source or not target:
                raise RuntimeGraphValidationError(
                    "runtime graph edge requires "
                    "source and target"
                )

            if source not in self._nodes:
                raise RuntimeGraphValidationError(
                    "runtime graph edge source "
                    f"is missing: {source}"
                )

            if target not in self._nodes:
                raise RuntimeGraphValidationError(
                    "runtime graph edge target "
                    f"is missing: {target}"
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

            edge[
                "role"
            ] = role

            self._edges[
                edge_id
            ] = edge

            self._outgoing[
                source
            ].append(
                edge_id
            )

            self._incoming[
                target
            ].append(
                edge_id
            )

            self._roles_by_node[
                source
            ].add(
                role
            )

            self._roles_by_node[
                target
            ].add(
                role
            )

        for node_id in self._nodes:
            self._incoming[
                node_id
            ].sort()

            self._outgoing[
                node_id
            ].sort()

    @classmethod
    def load(
        cls,
        path: Path | str,
    ) -> "RuntimeGraphIndex":
        source = Path(
            path
        ).expanduser().absolute()

        if not source.is_file():
            raise RuntimeGraphLookupError(
                "runtime graph missing: "
                f"{source}"
            )

        try:
            payload = json.loads(
                source.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeGraphValidationError(
                "cannot read runtime graph "
                f"{source}: {exc}"
            ) from exc

        return cls(
            payload
        )

    def node_records(
        self,
    ) -> list[dict[str, Any]]:
        return [
            deepcopy(
                self._nodes[
                    node_id
                ]
            )
            for node_id in sorted(
                self._nodes
            )
        ]

    def edge_records(
        self,
    ) -> list[dict[str, Any]]:
        return [
            deepcopy(
                self._edges[
                    edge_id
                ]
            )
            for edge_id in sorted(
                self._edges
            )
        ]

    def node_ids(
        self,
    ) -> list[str]:
        return sorted(
            self._nodes
        )

    def edge_ids(
        self,
    ) -> list[str]:
        return sorted(
            self._edges
        )

    def resolve_node_id(
        self,
        identifier: str,
    ) -> str:
        raw = str(
            identifier
        ).strip()

        if not raw:
            raise RuntimeGraphLookupError(
                "node identifier may not be empty"
            )

        if raw in self._nodes:
            return raw

        candidates = sorted(
            self._aliases.get(
                raw.casefold(),
                set(),
            )
        )

        if not candidates:
            raise RuntimeGraphLookupError(
                "runtime graph node not found: "
                f"{identifier}"
            )

        if len(
            candidates
        ) > 1:
            raise RuntimeGraphLookupError(
                "runtime graph node identifier "
                f"is ambiguous: {identifier} -> "
                + ", ".join(
                    candidates
                )
            )

        return candidates[0]

    def maybe_resolve_node_id(
        self,
        identifier: str,
    ) -> str | None:
        try:
            return self.resolve_node_id(
                identifier
            )
        except RuntimeGraphLookupError:
            return None

    def node(
        self,
        identifier: str,
    ) -> dict[str, Any]:
        node_id = self.resolve_node_id(
            identifier
        )

        return deepcopy(
            self._nodes[
                node_id
            ]
        )

    def incoming_edges(
        self,
        identifier: str,
        *,
        roles: Iterable[
            str
        ] | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        node_id = self.resolve_node_id(
            identifier
        )

        role_filter = (
            {
                str(role).strip()
                for role in roles
                if str(role).strip()
            }
            if roles is not None
            else None
        )

        result: list[
            dict[str, Any]
        ] = []

        for edge_id in self._incoming[
            node_id
        ]:
            edge = self._edges[
                edge_id
            ]

            if (
                active_only
                and str(
                    edge.get(
                        "status",
                        "active",
                    )
                )
                not in {
                    "active",
                    "accepted",
                    "current",
                    "example",
                }
            ):
                continue

            if (
                role_filter is not None
                and edge.get(
                    "role"
                )
                not in role_filter
            ):
                continue

            result.append(
                deepcopy(
                    edge
                )
            )

        return result

    def outgoing_edges(
        self,
        identifier: str,
        *,
        roles: Iterable[
            str
        ] | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        node_id = self.resolve_node_id(
            identifier
        )

        role_filter = (
            {
                str(role).strip()
                for role in roles
                if str(role).strip()
            }
            if roles is not None
            else None
        )

        result: list[
            dict[str, Any]
        ] = []

        for edge_id in self._outgoing[
            node_id
        ]:
            edge = self._edges[
                edge_id
            ]

            if (
                active_only
                and str(
                    edge.get(
                        "status",
                        "active",
                    )
                )
                not in {
                    "active",
                    "accepted",
                    "current",
                    "example",
                }
            ):
                continue

            if (
                role_filter is not None
                and edge.get(
                    "role"
                )
                not in role_filter
            ):
                continue

            result.append(
                deepcopy(
                    edge
                )
            )

        return result

    def roles(
        self,
        identifier: str,
    ) -> list[str]:
        node_id = self.resolve_node_id(
            identifier
        )

        return sorted(
            self._roles_by_node[
                node_id
            ]
        )

    def family(
        self,
        identifier: str,
    ) -> dict[str, Any]:
        node_id = self.resolve_node_id(
            identifier
        )

        node = self._nodes[
            node_id
        ]

        incoming = self.incoming_edges(
            node_id
        )

        outgoing = self.outgoing_edges(
            node_id
        )

        incoming_by_role: dict[
            str,
            list[str],
        ] = defaultdict(list)

        outgoing_by_role: dict[
            str,
            list[str],
        ] = defaultdict(list)

        for edge in incoming:
            incoming_by_role[
                edge["role"]
            ].append(
                edge["source"]
            )

        for edge in outgoing:
            outgoing_by_role[
                edge["role"]
            ].append(
                edge["target"]
            )

        return {
            "id": node_id,
            "canonical_id": node.get(
                "canonical_id",
                node_id,
            ),
            "parents": _string_values(
                node.get(
                    "parents",
                    [
                        edge["source"]
                        for edge in incoming
                    ],
                )
            ),
            "mothers": _string_values(
                node.get(
                    "mothers",
                    [],
                )
            ),
            "fathers": _string_values(
                node.get(
                    "fathers",
                    [],
                )
            ),
            "children": _string_values(
                node.get(
                    "children",
                    [
                        edge["target"]
                        for edge in outgoing
                    ],
                )
            ),
            "daughters": _string_values(
                node.get(
                    "daughters",
                    [],
                )
            ),
            "sons": _string_values(
                node.get(
                    "sons",
                    [],
                )
            ),
            "incoming_by_role": {
                role: sorted(
                    set(values)
                )
                for role, values
                in sorted(
                    incoming_by_role.items()
                )
            },
            "outgoing_by_role": {
                role: sorted(
                    set(values)
                )
                for role, values
                in sorted(
                    outgoing_by_role.items()
                )
            },
            "incoming_edges": incoming,
            "outgoing_edges": outgoing,
        }

    def neighbors(
        self,
        identifier: str,
        *,
        roles: Iterable[
            str
        ] | None = None,
    ) -> list[str]:
        node_id = self.resolve_node_id(
            identifier
        )

        result: set[str] = set()

        for edge in self.incoming_edges(
            node_id,
            roles=roles,
        ):
            result.add(
                edge["source"]
            )

        for edge in self.outgoing_edges(
            node_id,
            roles=roles,
        ):
            result.add(
                edge["target"]
            )

        return sorted(
            result
        )

    def traverse(
        self,
        identifier: str,
        *,
        direction: str = "both",
        roles: Iterable[
            str
        ] | None = None,
        max_depth: int = 1,
        include_start: bool = False,
    ) -> list[dict[str, Any]]:
        if direction not in {
            "parents",
            "children",
            "both",
        }:
            raise ValueError(
                "direction must be parents, "
                "children, or both"
            )

        start = self.resolve_node_id(
            identifier
        )

        maximum = max(
            0,
            int(
                max_depth
            ),
        )

        queue = deque([
            (
                start,
                0,
            )
        ])

        visited = {
            start
        }

        result: list[
            dict[str, Any]
        ] = []

        if include_start:
            result.append({
                "id": start,
                "depth": 0,
                "via_edge": None,
                "direction": "self",
            })

        while queue:
            current, depth = (
                queue.popleft()
            )

            if depth >= maximum:
                continue

            candidates: list[
                tuple[
                    str,
                    dict[str, Any],
                    str,
                ]
            ] = []

            if direction in {
                "parents",
                "both",
            }:
                for edge in self.incoming_edges(
                    current,
                    roles=roles,
                ):
                    candidates.append(
                        (
                            edge["source"],
                            edge,
                            "parent",
                        )
                    )

            if direction in {
                "children",
                "both",
            }:
                for edge in self.outgoing_edges(
                    current,
                    roles=roles,
                ):
                    candidates.append(
                        (
                            edge["target"],
                            edge,
                            "child",
                        )
                    )

            candidates.sort(
                key=lambda item: (
                    item[0],
                    item[1]["id"],
                    item[2],
                )
            )

            for (
                neighbor,
                edge,
                relation_direction,
            ) in candidates:
                if neighbor in visited:
                    continue

                visited.add(
                    neighbor
                )

                next_depth = (
                    depth
                    + 1
                )

                result.append({
                    "id": neighbor,
                    "depth": next_depth,
                    "via_edge": (
                        edge["id"]
                    ),
                    "role": edge.get(
                        "role",
                        "generic",
                    ),
                    "axis": edge.get(
                        "axis",
                        "unspecified",
                    ),
                    "continuation": (
                        edge.get(
                            "continuation",
                            "neutral",
                        )
                    ),
                    "direction": (
                        relation_direction
                    ),
                })

                queue.append(
                    (
                        neighbor,
                        next_depth,
                    )
                )

        return result

    def search(
        self,
        query: str = "",
        *,
        kinds: Iterable[
            str
        ] | None = None,
        roles: Iterable[
            str
        ] | None = None,
        authority: bool | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        normalized_query = (
            str(
                query
            )
            .strip()
            .casefold()
        )

        tokens = [
            token
            for token
            in normalized_query.split()
            if token
        ]

        kind_filter = (
            {
                str(kind).casefold()
                for kind in kinds
                if str(kind).strip()
            }
            if kinds is not None
            else None
        )

        role_filter = (
            {
                str(role).strip()
                for role in roles
                if str(role).strip()
            }
            if roles is not None
            else None
        )

        results: list[
            dict[str, Any]
        ] = []

        for node_id in sorted(
            self._nodes
        ):
            node = self._nodes[
                node_id
            ]

            node_kind = str(
                node.get(
                    "kind",
                    "unknown",
                )
            )

            node_authority = bool(
                node.get(
                    "authority",
                    False,
                )
            )

            node_roles = sorted(
                self._roles_by_node[
                    node_id
                ]
            )

            if (
                kind_filter is not None
                and node_kind.casefold()
                not in kind_filter
            ):
                continue

            if (
                role_filter is not None
                and not role_filter.intersection(
                    node_roles
                )
            ):
                continue

            if (
                authority is not None
                and node_authority
                is not authority
            ):
                continue

            label = str(
                node.get(
                    "label",
                    node_id,
                )
            )

            canonical_id = str(
                node.get(
                    "canonical_id",
                    node_id,
                )
            )

            path = str(
                node.get(
                    "path",
                    "",
                )
                or ""
            )

            legacy_id = str(
                node.get(
                    "legacy_id",
                    "",
                )
                or ""
            )

            searchable = " ".join(
                (
                    node_id,
                    canonical_id,
                    label,
                    path,
                    legacy_id,
                    node_kind,
                    " ".join(
                        node_roles
                    ),
                )
            ).casefold()

            if (
                tokens
                and not all(
                    token in searchable
                    for token in tokens
                )
            ):
                continue

            score = (
                10
                if node_authority
                else 0
            )

            if normalized_query:
                if (
                    normalized_query
                    == node_id.casefold()
                ):
                    score += 1000

                if (
                    normalized_query
                    == canonical_id.casefold()
                ):
                    score += 950

                if (
                    normalized_query
                    == label.casefold()
                ):
                    score += 800

                if node_id.casefold().startswith(
                    normalized_query
                ):
                    score += 250

                if label.casefold().startswith(
                    normalized_query
                ):
                    score += 200

                for token in tokens:
                    if token in (
                        node_id.casefold()
                    ):
                        score += 90

                    if token in (
                        canonical_id.casefold()
                    ):
                        score += 80

                    if token in (
                        label.casefold()
                    ):
                        score += 70

                    if token in (
                        path.casefold()
                    ):
                        score += 50

                    if token in {
                        role.casefold()
                        for role in node_roles
                    }:
                        score += 40

            family = self.family(
                node_id
            )

            results.append({
                "id": node_id,
                "canonical_id": (
                    canonical_id
                ),
                "legacy_id": (
                    legacy_id
                    or None
                ),
                "label": label,
                "path": (
                    path
                    or None
                ),
                "kind": node_kind,
                "authority": (
                    node_authority
                ),
                "roles": node_roles,
                "score": score,
                "parents": (
                    family[
                        "parents"
                    ]
                ),
                "mothers": (
                    family[
                        "mothers"
                    ]
                ),
                "fathers": (
                    family[
                        "fathers"
                    ]
                ),
                "children": (
                    family[
                        "children"
                    ]
                ),
                "daughters": (
                    family[
                        "daughters"
                    ]
                ),
                "sons": (
                    family[
                        "sons"
                    ]
                ),
            })

        results.sort(
            key=lambda item: (
                -item["score"],
                not item["authority"],
                item["label"].casefold(),
                item["id"],
            )
        )

        return results[
            :max(
                0,
                int(
                    limit
                ),
            )
        ]

    def role_counts(
        self,
    ) -> dict[str, int]:
        counts = Counter(
            edge.get(
                "role",
                "generic",
            )
            for edge in self._edges.values()
        )

        return dict(
            sorted(
                counts.items()
            )
        )

    def axis_counts(
        self,
    ) -> dict[str, int]:
        counts = Counter(
            edge.get(
                "axis",
                "unspecified",
            )
            for edge in self._edges.values()
        )

        return dict(
            sorted(
                counts.items()
            )
        )
