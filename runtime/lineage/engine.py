#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .model import (
    LineageBinding,
    LineageValidationError,
    merge_values,
    select_top_level_fields,
    stable_hash,
)

from .registry import (
    DEFAULT_ROLE_REGISTRY,
    LineageRoleRegistry,
)


ACTIVE_STATUSES = {
    "active",
    "accepted",
    "current",
    "example",
}


class LineageGraph:
    def __init__(
        self,
        registry: LineageRoleRegistry,
    ) -> None:
        self.registry = registry

        self.nodes: dict[
            str,
            dict[str, Any],
        ] = {}

        self.bindings: dict[
            str,
            LineageBinding,
        ] = {}

        self._signatures: dict[
            tuple[str, str, str, str, int],
            str,
        ] = {}

        self._incoming: dict[
            str,
            set[str],
        ] = defaultdict(set)

        self._outgoing: dict[
            str,
            set[str],
        ] = defaultdict(set)

    def add_node(
        self,
        node_id: str,
        payload: Mapping[str, Any] | None = None,
        *,
        placeholder: bool = False,
    ) -> None:
        node_id = str(
            node_id
        ).strip()

        if not node_id:
            raise LineageValidationError(
                "node id may not be empty"
            )

        incoming = deepcopy(
            dict(
                payload
                or {}
            )
        )

        incoming.setdefault(
            "id",
            node_id,
        )

        incoming.setdefault(
            "kind",
            (
                "reference"
                if placeholder
                else "instance"
            ),
        )

        incoming[
            "_lineage_placeholder"
        ] = bool(placeholder)

        existing = self.nodes.get(
            node_id
        )

        if existing is None:
            self.nodes[node_id] = incoming
            return

        if (
            existing.get(
                "_lineage_placeholder"
            )
            and not placeholder
        ):
            self.nodes[node_id] = incoming
            return

        if not placeholder:
            merged = merge_values(
                existing,
                incoming,
                conflict_policy="child_wins",
            )

            merged[
                "_lineage_placeholder"
            ] = False

            self.nodes[node_id] = merged

    def add_binding(
        self,
        raw: Mapping[str, Any],
    ) -> LineageBinding:
        raw_role = str(
            raw.get(
                "role",
                "generic",
            )
        )

        role = self.registry.get(
            raw_role
        )

        binding = LineageBinding.from_mapping(
            raw,
            canonical_role=role.name,
            axis=role.axis,
            default_inheritance=(
                role.default_inheritance
            ),
            default_propagation=(
                role.propagates_changes
            ),
        )

        if binding.id in self.bindings:
            if (
                self.bindings[
                    binding.id
                ].to_dict()
                == binding.to_dict()
            ):
                return self.bindings[
                    binding.id
                ]

            raise LineageValidationError(
                "duplicate lineage id: "
                f"{binding.id}"
            )

        signature = binding.signature()

        existing_id = (
            self._signatures.get(
                signature
            )
        )

        if existing_id is not None:
            raise LineageValidationError(
                "duplicate lineage "
                "relationship: "
                f"{existing_id} "
                f"and {binding.id}"
            )

        self.add_node(
            binding.parent,
            placeholder=True,
        )

        self.add_node(
            binding.child,
            placeholder=True,
        )

        self.bindings[
            binding.id
        ] = binding

        self._signatures[
            signature
        ] = binding.id

        self._outgoing[
            binding.parent
        ].add(
            binding.id
        )

        self._incoming[
            binding.child
        ].add(
            binding.id
        )

        try:
            self._assert_cycle_policy(
                binding
            )
        except Exception:
            self._outgoing[
                binding.parent
            ].discard(
                binding.id
            )

            self._incoming[
                binding.child
            ].discard(
                binding.id
            )

            self._signatures.pop(
                signature,
                None,
            )

            self.bindings.pop(
                binding.id,
                None,
            )

            raise

        return binding

    def _binding_sort_key(
        self,
        binding: LineageBinding,
    ) -> tuple[int, int, str]:
        role = self.registry.get(
            binding.role
        )

        return (
            role.precedence,
            binding.order,
            binding.id,
        )

    def _role_filter(
        self,
        roles: Iterable[str] | None,
    ) -> set[str] | None:
        if roles is None:
            return None

        return {
            self.registry.canonical_name(
                role
            )
            for role in roles
        }

    def incoming_bindings(
        self,
        child_id: str,
        *,
        roles: Iterable[str] | None = None,
        active_only: bool = True,
    ) -> list[LineageBinding]:
        role_filter = self._role_filter(
            roles
        )

        bindings = [
            self.bindings[item]
            for item
            in self._incoming.get(
                child_id,
                set(),
            )
        ]

        return sorted(
            [
                binding
                for binding in bindings
                if (
                    not active_only
                    or binding.status
                    in ACTIVE_STATUSES
                )
                and (
                    role_filter is None
                    or binding.role
                    in role_filter
                )
            ],
            key=self._binding_sort_key,
        )

    def outgoing_bindings(
        self,
        parent_id: str,
        *,
        roles: Iterable[str] | None = None,
        active_only: bool = True,
    ) -> list[LineageBinding]:
        role_filter = self._role_filter(
            roles
        )

        bindings = [
            self.bindings[item]
            for item
            in self._outgoing.get(
                parent_id,
                set(),
            )
        ]

        return sorted(
            [
                binding
                for binding in bindings
                if (
                    not active_only
                    or binding.status
                    in ACTIVE_STATUSES
                )
                and (
                    role_filter is None
                    or binding.role
                    in role_filter
                )
            ],
            key=self._binding_sort_key,
        )

    def parents(
        self,
        child_id: str,
        *,
        roles: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        for binding in self.incoming_bindings(
            child_id,
            roles=roles,
        ):
            item = binding.to_dict()

            item[
                "symbolic_parent_alias"
            ] = (
                self.registry
                .symbolic_parent_alias(
                    binding.role
                )
            )

            item[
                "symbolic_child_alias"
            ] = (
                self.registry
                .symbolic_child_alias(
                    binding.continuation
                )
            )

            result.append(item)

        return result

    def children(
        self,
        parent_id: str,
        *,
        roles: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        for binding in self.outgoing_bindings(
            parent_id,
            roles=roles,
        ):
            item = binding.to_dict()

            item[
                "symbolic_parent_alias"
            ] = (
                self.registry
                .symbolic_parent_alias(
                    binding.role
                )
            )

            item[
                "symbolic_child_alias"
            ] = (
                self.registry
                .symbolic_child_alias(
                    binding.continuation
                )
            )

            result.append(item)

        return result

    def ancestors(
        self,
        node_id: str,
        *,
        roles: Iterable[str] | None = None,
        include_self: bool = False,
    ) -> list[str]:
        role_filter = self._role_filter(
            roles
        )

        seen = {
            node_id
        }

        queue = deque(
            [node_id]
        )

        result: list[str] = (
            [node_id]
            if include_self
            else []
        )

        while queue:
            current = queue.popleft()

            for binding in self.incoming_bindings(
                current,
                roles=role_filter,
            ):
                if binding.parent in seen:
                    continue

                seen.add(
                    binding.parent
                )

                result.append(
                    binding.parent
                )

                queue.append(
                    binding.parent
                )

        return result

    def descendants(
        self,
        node_id: str,
        *,
        roles: Iterable[str] | None = None,
        include_self: bool = False,
        propagation_channel: str | None = None,
    ) -> list[str]:
        role_filter = self._role_filter(
            roles
        )

        seen = {
            node_id
        }

        queue = deque(
            [node_id]
        )

        result: list[str] = (
            [node_id]
            if include_self
            else []
        )

        while queue:
            current = queue.popleft()

            for binding in self.outgoing_bindings(
                current,
                roles=role_filter,
            ):
                if not binding.propagation.enabled:
                    continue

                if (
                    propagation_channel is not None
                    and propagation_channel
                    not in binding.propagation.channels
                ):
                    continue

                if binding.child in seen:
                    continue

                seen.add(
                    binding.child
                )

                result.append(
                    binding.child
                )

                queue.append(
                    binding.child
                )

        return result

    def affected_by(
        self,
        changed_ids: Iterable[str],
        *,
        channel: str = "regeneration",
        include_changed: bool = True,
    ) -> list[str]:
        affected: set[str] = set()

        for node_id in sorted(
            set(changed_ids)
        ):
            if include_changed:
                affected.add(
                    node_id
                )

            affected.update(
                self.descendants(
                    node_id,
                    include_self=False,
                    propagation_channel=channel,
                )
            )

        return sorted(
            affected
        )

    def _assert_cycle_policy(
        self,
        newest: LineageBinding,
    ) -> None:
        role = self.registry.get(
            newest.role
        )

        if (
            not role.acyclic
            or newest.status
            not in ACTIVE_STATUSES
        ):
            return

        adjacency: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for binding in self.bindings.values():
            definition = self.registry.get(
                binding.role
            )

            if (
                binding.status
                in ACTIVE_STATUSES
                and definition.acyclic
                and definition.cycle_domain
                == role.cycle_domain
            ):
                adjacency[
                    binding.parent
                ].add(
                    binding.child
                )

        stack = [
            newest.child
        ]

        visited: set[str] = set()

        while stack:
            current = stack.pop()

            if current == newest.parent:
                raise LineageValidationError(
                    "lineage cycle rejected "
                    "in domain "
                    f"{role.cycle_domain}: "
                    f"{newest.parent} -> "
                    f"{newest.child}"
                )

            if current in visited:
                continue

            visited.add(
                current
            )

            stack.extend(
                sorted(
                    adjacency.get(
                        current,
                        set(),
                    ),
                    reverse=True,
                )
            )

    def resolve_node(
        self,
        node_id: str,
        *,
        recursive: bool = True,
        _stack: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if node_id not in self.nodes:
            raise LineageValidationError(
                "unknown lineage node: "
                f"{node_id}"
            )

        if node_id in _stack:
            chain = " -> ".join(
                (
                    *_stack,
                    node_id,
                )
            )

            raise LineageValidationError(
                "inheritance recursion cycle: "
                f"{chain}"
            )

        child_payload = {
            key: deepcopy(value)
            for key, value
            in self.nodes[node_id].items()
            if key != "_lineage_placeholder"
        }

        inherited: dict[
            str,
            Any,
        ] = {}

        parent_locks: list[
            tuple[
                dict[str, Any],
                str,
            ]
        ] = []

        for binding in self.incoming_bindings(
            node_id
        ):
            policy = binding.inheritance

            if policy.mode in {
                "none",
                "reference",
            }:
                continue

            if recursive:
                parent_payload = self.resolve_node(
                    binding.parent,
                    recursive=True,
                    _stack=(
                        *_stack,
                        node_id,
                    ),
                )
            else:
                parent_payload = {
                    key: deepcopy(value)
                    for key, value
                    in self.nodes[
                        binding.parent
                    ].items()
                    if key
                    != "_lineage_placeholder"
                }

            selected = select_top_level_fields(
                parent_payload,
                policy.fields,
                policy.exclude,
            )

            if policy.mode == "replace":
                for key, value in selected.items():
                    inherited[key] = deepcopy(
                        value
                    )
            else:
                parent_merge_policy = (
                    policy.conflict_policy
                    if policy.conflict_policy
                    in {
                        "collect",
                        "error",
                    }
                    else "child_wins"
                )

                inherited = merge_values(
                    inherited,
                    selected,
                    conflict_policy=(
                        parent_merge_policy
                    ),
                )

            if (
                policy.conflict_policy
                == "parent_wins"
            ):
                parent_locks.append(
                    (
                        selected,
                        "parent_wins",
                    )
                )

        resolved = merge_values(
            inherited,
            child_payload,
            conflict_policy="child_wins",
        )

        for locked, policy in parent_locks:
            resolved = merge_values(
                locked,
                resolved,
                conflict_policy=policy,
            )

        resolved["_lineage"] = {
            "node": node_id,
            "parents": self.parents(
                node_id
            ),
            "children": self.children(
                node_id
            ),
            "resolved_recursively": recursive,
        }

        return resolved

    def validate(
        self,
    ) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []

        for node_id, payload in sorted(
            self.nodes.items()
        ):
            if payload.get(
                "_lineage_placeholder"
            ):
                warnings.append(
                    "unresolved node reference: "
                    f"{node_id}"
                )

        for binding in sorted(
            self.bindings.values(),
            key=lambda item: item.id,
        ):
            if binding.parent not in self.nodes:
                errors.append(
                    "missing parent node: "
                    f"{binding.parent}"
                )

            if binding.child not in self.nodes:
                errors.append(
                    "missing child node: "
                    f"{binding.child}"
                )

            if (
                binding.axis
                != self.registry.get(
                    binding.role
                ).axis
            ):
                errors.append(
                    "axis mismatch for "
                    f"{binding.id}: "
                    f"{binding.axis}"
                )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "node_count": len(
                self.nodes
            ),
            "binding_count": len(
                self.bindings
            ),
        }

    def project(
        self,
    ) -> dict[str, Any]:
        node_records: list[
            dict[str, Any]
        ] = []

        for node_id in sorted(
            self.nodes
        ):
            payload = {
                key: deepcopy(value)
                for key, value
                in self.nodes[
                    node_id
                ].items()
                if key
                != "_lineage_placeholder"
            }

            payload.setdefault(
                "id",
                node_id,
            )

            payload[
                "lineage_projection"
            ] = {
                "parents": self.parents(
                    node_id
                ),
                "children": self.children(
                    node_id
                ),
            }

            node_records.append(
                payload
            )

        binding_records = [
            binding.to_dict()
            for binding in sorted(
                self.bindings.values(),
                key=lambda item: item.id,
            )
        ]

        role_registry = (
            self.registry.to_dict()
        )

        hash_registry = deepcopy(
            role_registry
        )

        hash_registry.pop(
            "source",
            None,
        )

        hash_core = {
            "role_registry": hash_registry,
            "nodes": node_records,
            "bindings": binding_records,
        }

        return {
            "schema": (
                "savant."
                "functional_lineage_graph.v1"
            ),
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "deterministic_hash": stable_hash(
                hash_core
            ),
            "node_count": len(
                node_records
            ),
            "binding_count": len(
                binding_records
            ),
            "role_registry": role_registry,
            "nodes": node_records,
            "bindings": binding_records,
        }

    def ingest_document(
        self,
        document: Any,
        *,
        source: str = "",
        include_legacy: bool = False,
    ) -> None:
        if isinstance(
            document,
            list,
        ):
            for item in document:
                self.ingest_document(
                    item,
                    source=source,
                    include_legacy=(
                        include_legacy
                    ),
                )

            return

        if not isinstance(
            document,
            Mapping,
        ):
            return

        if (
            document.get("kind")
            == "segue"
            and document.get("type")
            == "lineage"
        ):
            self.add_binding(
                document
            )

            return

        node_id = document.get(
            "id"
        )

        if (
            isinstance(
                node_id,
                str,
            )
            and node_id.strip()
        ):
            self.add_node(
                node_id,
                document,
            )

        for key in (
            "bindings",
            "lineage_bindings",
            "segues",
        ):
            nested = document.get(
                key
            )

            if not isinstance(
                nested,
                list,
            ):
                continue

            for item in nested:
                if (
                    isinstance(
                        item,
                        Mapping,
                    )
                    and item.get("kind")
                    == "segue"
                    and item.get("type")
                    == "lineage"
                ):
                    self.add_binding(
                        item
                    )

        if (
            include_legacy
            and isinstance(
                node_id,
                str,
            )
            and node_id.strip()
        ):
            self._ingest_legacy(
                document,
                source=source,
            )

    def _ingest_legacy(
        self,
        document: Mapping[str, Any],
        *,
        source: str,
    ) -> None:
        node_id = str(
            document["id"]
        )

        lineage = document.get(
            "lineage"
        )

        composition = document.get(
            "composition"
        )

        if isinstance(
            lineage,
            Mapping,
        ):
            for parent in _legacy_ids(
                lineage.get(
                    "parents"
                )
            ):
                self.add_binding(
                    _legacy_binding(
                        parent,
                        node_id,
                        "generic",
                        source,
                    )
                )

            for child in _legacy_ids(
                lineage.get(
                    "children"
                )
            ):
                self.add_binding(
                    _legacy_binding(
                        node_id,
                        child,
                        "generic",
                        source,
                    )
                )

            for parent in _legacy_ids(
                lineage.get(
                    "composed_from"
                )
            ):
                self.add_binding(
                    _legacy_binding(
                        parent,
                        node_id,
                        "source",
                        source,
                    )
                )

        if isinstance(
            composition,
            Mapping,
        ):
            for child in _legacy_ids(
                composition.get(
                    "children"
                )
            ):
                self.add_binding(
                    _legacy_binding(
                        node_id,
                        child,
                        "composition",
                        source,
                    )
                )

        for parent in _legacy_ids(
            document.get(
                "parents"
            )
        ):
            self.add_binding(
                _legacy_binding(
                    parent,
                    node_id,
                    "generic",
                    source,
                )
            )

        for child in _legacy_ids(
            document.get(
                "children"
            )
        ):
            self.add_binding(
                _legacy_binding(
                    node_id,
                    child,
                    "generic",
                    source,
                )
            )

        parent_id = document.get(
            "parent_id"
        )

        if (
            isinstance(
                parent_id,
                str,
            )
            and parent_id.strip()
        ):
            self.add_binding(
                _legacy_binding(
                    parent_id,
                    node_id,
                    "generic",
                    source,
                )
            )

    @classmethod
    def from_projection(
        cls,
        payload: Mapping[str, Any],
        *,
        registry: LineageRoleRegistry,
    ) -> "LineageGraph":
        graph = cls(
            registry
        )

        for node in payload.get(
            "nodes",
            [],
        ):
            if (
                isinstance(
                    node,
                    Mapping,
                )
                and isinstance(
                    node.get("id"),
                    str,
                )
            ):
                clean = dict(
                    node
                )

                clean.pop(
                    "lineage_projection",
                    None,
                )

                graph.add_node(
                    str(
                        node["id"]
                    ),
                    clean,
                )

        for binding in payload.get(
            "bindings",
            [],
        ):
            if isinstance(
                binding,
                Mapping,
            ):
                graph.add_binding(
                    binding
                )

        return graph


def _legacy_ids(
    value: Any,
) -> list[str]:
    if isinstance(
        value,
        str,
    ):
        return (
            [value]
            if value.strip()
            else []
        )

    if not isinstance(
        value,
        Sequence,
    ) or isinstance(
        value,
        (bytes, bytearray),
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
            and item not in result
        ):
            result.append(
                item
            )

    return result


def _legacy_binding(
    parent: str,
    child: str,
    role: str,
    source: str,
) -> dict[str, Any]:
    return {
        "kind": "segue",
        "type": "lineage",
        "parent": parent,
        "child": child,
        "role": role,
        "provenance": {
            "created_by": (
                "legacy_lineage_projection"
            ),
            "source_files": (
                [source]
                if source
                else []
            ),
        },
        "metadata": {
            "legacy_projection": True
        },
    }


def iter_json_files(
    paths: Iterable[
        Path | str
    ],
) -> Iterable[Path]:
    seen: set[Path] = set()

    for raw in paths:
        path = Path(raw)

        candidates = (
            [path]
            if path.is_file()
            else sorted(
                path.rglob(
                    "*.json"
                )
            )
        )

        for candidate in candidates:
            resolved = candidate.resolve()

            if (
                resolved in seen
                or not candidate.is_file()
            ):
                continue

            seen.add(
                resolved
            )

            yield candidate


def compile_lineage(
    inputs: Iterable[
        Path | str
    ],
    *,
    role_registry: Path | str = (
        DEFAULT_ROLE_REGISTRY
    ),
    include_legacy: bool = False,
) -> LineageGraph:
    registry = (
        LineageRoleRegistry.load(
            role_registry
        )
    )

    graph = LineageGraph(
        registry
    )

    for path in iter_json_files(
        inputs
    ):
        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ):
            continue

        graph.ingest_document(
            payload,
            source=str(path),
            include_legacy=(
                include_legacy
            ),
        )

    return graph


def write_projection(
    graph: LineageGraph,
    output: Path | str,
) -> dict[str, Any]:
    target = Path(
        output
    )

    payload = graph.project()

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return payload
