#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Sequence

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: PyYAML\n"
        "Install with: python3 -m pip install pyyaml"
    ) from exc


LEXICON_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = LEXICON_ROOT / "registry.yaml"
DEFAULT_PROJECTION_REGISTRY_PATH = (
    LEXICON_ROOT / "projections" / "projection_registry.yaml"
)

LEXEME_ID_PATTERN = re.compile(
    r"^lex:[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*$"
)

VALID_STATUSES = {
    "active",
    "deprecated",
    "superseded",
    "reserved",
}

VALID_LAYERS = {
    "shard00",
    "shard0",
    "shard1",
    "shard2",
    "shard3",
    "shard4",
    "shard5",
    "shard6",
    "shard7",
}


class LexiconError(Exception):
    pass


class RegistryLoadError(LexiconError):
    pass


class ResolutionError(LexiconError):
    pass


class ProjectionError(LexiconError):
    pass


class GraphCycleError(LexiconError):
    pass


@dataclass(frozen=True)
class AuthorityRecord:
    source: str | None = None
    revision: str | None = None
    timestamp: str | None = None
    predecessor: str | None = None

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any] | None,
    ) -> "AuthorityRecord":
        value = value or {}

        return cls(
            source=optional_string(value.get("source")),
            revision=optional_string(value.get("revision")),
            timestamp=optional_string(value.get("timestamp")),
            predecessor=optional_string(value.get("predecessor")),
        )

    def to_dict(self) -> dict[str, Any]:
        return compact_mapping(
            {
                "source": self.source,
                "revision": self.revision,
                "timestamp": self.timestamp,
                "predecessor": self.predecessor,
            }
        )


@dataclass(frozen=True)
class ProvenanceRecord:
    source: str | None = None
    evidence: tuple[str, ...] = ()
    confidence: str | None = None

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any] | None,
    ) -> "ProvenanceRecord":
        value = value or {}

        return cls(
            source=optional_string(value.get("source")),
            evidence=tuple(string_list(value.get("evidence"))),
            confidence=optional_string(value.get("confidence")),
        )

    def to_dict(self) -> dict[str, Any]:
        return compact_mapping(
            {
                "source": self.source,
                "evidence": list(self.evidence),
                "confidence": self.confidence,
            }
        )


@dataclass(frozen=True)
class LineageRecord:
    introduced: AuthorityRecord = field(
        default_factory=AuthorityRecord
    )
    superseded_by: str | None = None
    supersedes: tuple[str, ...] = ()
    history: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any] | None,
    ) -> "LineageRecord":
        value = value or {}

        raw_history = value.get("history") or []
        history: list[Mapping[str, Any]] = []

        if isinstance(raw_history, list):
            for event in raw_history:
                if isinstance(event, Mapping):
                    history.append(dict(event))

        return cls(
            introduced=AuthorityRecord.from_mapping(
                mapping_or_empty(value.get("introduced"))
            ),
            superseded_by=optional_string(
                value.get("superseded_by")
            ),
            supersedes=tuple(
                string_list(value.get("supersedes"))
            ),
            history=tuple(history),
        )

    def to_dict(self) -> dict[str, Any]:
        return compact_mapping(
            {
                "introduced": self.introduced.to_dict(),
                "superseded_by": self.superseded_by,
                "supersedes": list(self.supersedes),
                "history": [
                    dict(event)
                    for event in self.history
                ],
            }
        )


@dataclass(frozen=True)
class Relationship:
    type: str
    target: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(
        cls,
        value: Any,
    ) -> "Relationship":
        if isinstance(value, str):
            return cls(
                type="related_to",
                target=value,
                metadata={},
            )

        if not isinstance(value, Mapping):
            raise RegistryLoadError(
                f"Invalid relationship value: {value!r}"
            )

        relationship_type = optional_string(
            value.get("type")
        )
        target = optional_string(value.get("target"))

        if not relationship_type or not target:
            raise RegistryLoadError(
                "Relationship requires type and target."
            )

        metadata = {
            key: item
            for key, item in value.items()
            if key not in {"type", "target"}
        }

        return cls(
            type=relationship_type,
            target=target,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "target": self.target,
            **dict(self.metadata),
        }


@dataclass(frozen=True)
class Lexeme:
    id: str
    canonical: str
    concept: str
    layer: str
    status: str
    description: str | None = None
    aliases: tuple[str, ...] = ()
    reserved_spellings: tuple[str, ...] = ()
    parents: tuple[str, ...] = ()
    children: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    depended_by: tuple[str, ...] = ()
    projections: tuple[str, ...] = ()
    validators: tuple[str, ...] = ()
    ontology: tuple[str, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    lineage: LineageRecord = field(
        default_factory=LineageRecord
    )
    provenance: ProvenanceRecord = field(
        default_factory=ProvenanceRecord
    )
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "Lexeme":
        required = {
            "id",
            "canonical",
            "concept",
            "layer",
            "status",
        }

        missing = [
            key
            for key in required
            if value.get(key) in (None, "")
        ]

        if missing:
            raise RegistryLoadError(
                "Lexeme missing required fields: "
                + ", ".join(sorted(missing))
            )

        relationships = tuple(
            Relationship.from_value(item)
            for item in list_or_empty(
                value.get("relationships")
            )
        )

        known_fields = {
            "id",
            "canonical",
            "concept",
            "description",
            "layer",
            "status",
            "aliases",
            "reserved_spellings",
            "parents",
            "children",
            "dependencies",
            "depended_by",
            "projections",
            "validators",
            "ontology",
            "relationships",
            "lineage",
            "provenance",
            "metadata",
        }

        metadata: dict[str, Any] = {}

        explicit_metadata = value.get("metadata")

        if isinstance(explicit_metadata, Mapping):
            metadata.update(explicit_metadata)

        for key, item in value.items():
            if key not in known_fields:
                metadata[key] = item

        return cls(
            id=str(value["id"]).strip(),
            canonical=str(value["canonical"]).strip(),
            concept=str(value["concept"]).strip(),
            description=optional_string(
                value.get("description")
            ),
            layer=str(value["layer"]).strip(),
            status=str(value["status"]).strip(),
            aliases=tuple(
                string_list(value.get("aliases"))
            ),
            reserved_spellings=tuple(
                string_list(
                    value.get("reserved_spellings")
                )
            ),
            parents=tuple(
                string_list(value.get("parents"))
            ),
            children=tuple(
                string_list(value.get("children"))
            ),
            dependencies=tuple(
                string_list(value.get("dependencies"))
            ),
            depended_by=tuple(
                string_list(value.get("depended_by"))
            ),
            projections=tuple(
                string_list(value.get("projections"))
            ),
            validators=tuple(
                string_list(value.get("validators"))
            ),
            ontology=tuple(
                string_list(value.get("ontology"))
            ),
            relationships=relationships,
            lineage=LineageRecord.from_mapping(
                mapping_or_empty(value.get("lineage"))
            ),
            provenance=ProvenanceRecord.from_mapping(
                mapping_or_empty(
                    value.get("provenance")
                )
            ),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "canonical": self.canonical,
            "concept": self.concept,
            "description": self.description,
            "layer": self.layer,
            "status": self.status,
            "aliases": list(self.aliases),
            "reserved_spellings": list(
                self.reserved_spellings
            ),
            "parents": list(self.parents),
            "children": list(self.children),
            "dependencies": list(
                self.dependencies
            ),
            "depended_by": list(self.depended_by),
            "projections": list(self.projections),
            "validators": list(self.validators),
            "ontology": list(self.ontology),
            "relationships": [
                relationship.to_dict()
                for relationship in self.relationships
            ],
            "lineage": self.lineage.to_dict(),
            "provenance": self.provenance.to_dict(),
            "metadata": dict(self.metadata),
        }

        return compact_mapping(result)


@dataclass(frozen=True)
class Registry:
    registry_id: str
    version: int
    authority: AuthorityRecord
    constitution: str | None
    schema: str | None
    policies: tuple[str, ...]
    validators: tuple[str, ...]
    projections: tuple[str, ...]
    lexemes: tuple[Lexeme, ...]
    reserved: tuple[str, ...]
    metadata: Mapping[str, Any]
    source_path: Path

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        source_path: Path,
    ) -> "Registry":
        raw_lexemes = value.get("lexemes")

        if not isinstance(raw_lexemes, list):
            raise RegistryLoadError(
                "Registry lexemes must be a list."
            )

        lexemes = tuple(
            Lexeme.from_mapping(item)
            for item in raw_lexemes
            if isinstance(item, Mapping)
        )

        if len(lexemes) != len(raw_lexemes):
            raise RegistryLoadError(
                "Every registry lexeme must be an object."
            )

        known_fields = {
            "registry_id",
            "version",
            "authority",
            "constitution",
            "schema",
            "policies",
            "validators",
            "projections",
            "lexemes",
            "reserved",
            "metadata",
        }

        metadata: dict[str, Any] = {}

        explicit_metadata = value.get("metadata")

        if isinstance(explicit_metadata, Mapping):
            metadata.update(explicit_metadata)

        for key, item in value.items():
            if key not in known_fields:
                metadata[key] = item

        registry_id = optional_string(
            value.get("registry_id")
        )

        if not registry_id:
            raise RegistryLoadError(
                "Registry requires registry_id."
            )

        try:
            version = int(value.get("version"))
        except (TypeError, ValueError) as exc:
            raise RegistryLoadError(
                "Registry version must be an integer."
            ) from exc

        return cls(
            registry_id=registry_id,
            version=version,
            authority=AuthorityRecord.from_mapping(
                mapping_or_empty(value.get("authority"))
            ),
            constitution=optional_string(
                value.get("constitution")
            ),
            schema=optional_string(value.get("schema")),
            policies=tuple(
                string_list(value.get("policies"))
            ),
            validators=tuple(
                string_list(value.get("validators"))
            ),
            projections=tuple(
                string_list(value.get("projections"))
            ),
            lexemes=lexemes,
            reserved=tuple(
                string_list(value.get("reserved"))
            ),
            metadata=metadata,
            source_path=source_path,
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "registry_id": self.registry_id,
            "version": self.version,
            "authority": self.authority.to_dict(),
            "constitution": self.constitution,
            "schema": self.schema,
            "policies": list(self.policies),
            "validators": list(self.validators),
            "projections": list(self.projections),
            "lexemes": [
                lexeme.to_dict()
                for lexeme in self.lexemes
            ],
            "reserved": list(self.reserved),
            "metadata": dict(self.metadata),
        }

        return compact_mapping(result)


@dataclass
class DirectedGraph:
    adjacency: dict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    def add_node(self, node: str) -> None:
        self.adjacency.setdefault(node, set())

    def add_edge(
        self,
        source: str,
        target: str,
    ) -> None:
        self.add_node(source)
        self.add_node(target)
        self.adjacency[source].add(target)

    def nodes(self) -> list[str]:
        return sorted(self.adjacency)

    def edges(self) -> list[tuple[str, str]]:
        return sorted(
            (
                source,
                target,
            )
            for source, targets
            in self.adjacency.items()
            for target in targets
        )

    def successors(self, node: str) -> list[str]:
        return sorted(self.adjacency.get(node, set()))

    def predecessors(self, node: str) -> list[str]:
        result = [
            source
            for source, targets
            in self.adjacency.items()
            if node in targets
        ]

        return sorted(result)

    def reverse(self) -> "DirectedGraph":
        graph = DirectedGraph()

        for node in self.adjacency:
            graph.add_node(node)

        for source, target in self.edges():
            graph.add_edge(target, source)

        return graph

    def transitive_closure(
        self,
        start: str,
    ) -> list[str]:
        visited: set[str] = set()
        queue: deque[str] = deque(
            self.successors(start)
        )

        while queue:
            node = queue.popleft()

            if node in visited:
                continue

            visited.add(node)

            for successor in self.successors(node):
                if successor not in visited:
                    queue.append(successor)

        return sorted(visited)

    def shortest_path(
        self,
        source: str,
        target: str,
    ) -> list[str] | None:
        if source == target:
            return [source]

        queue: deque[list[str]] = deque([[source]])
        visited = {source}

        while queue:
            path = queue.popleft()
            current = path[-1]

            for successor in self.successors(current):
                if successor in visited:
                    continue

                next_path = [*path, successor]

                if successor == target:
                    return next_path

                visited.add(successor)
                queue.append(next_path)

        return None

    def topological_order(self) -> list[str]:
        indegree = {
            node: 0
            for node in self.adjacency
        }

        for targets in self.adjacency.values():
            for target in targets:
                indegree[target] = (
                    indegree.get(target, 0) + 1
                )

        ready = deque(
            sorted(
                node
                for node, count
                in indegree.items()
                if count == 0
            )
        )

        result: list[str] = []

        while ready:
            node = ready.popleft()
            result.append(node)

            for target in self.successors(node):
                indegree[target] -= 1

                if indegree[target] == 0:
                    ready.append(target)

            ready = deque(sorted(ready))

        if len(result) != len(indegree):
            cycle = self.find_cycle()

            raise GraphCycleError(
                "Graph contains cycle: "
                + " -> ".join(cycle or [])
            )

        return result

    def find_cycle(self) -> list[str] | None:
        state: dict[str, int] = {}
        stack: list[str] = []
        stack_index: dict[str, int] = {}

        def visit(node: str) -> list[str] | None:
            state[node] = 1
            stack_index[node] = len(stack)
            stack.append(node)

            for target in self.successors(node):
                target_state = state.get(target, 0)

                if target_state == 0:
                    cycle = visit(target)

                    if cycle:
                        return cycle

                elif target_state == 1:
                    start_index = stack_index[target]

                    return [
                        *stack[start_index:],
                        target,
                    ]

            stack.pop()
            stack_index.pop(node, None)
            state[node] = 2

            return None

        for node in self.nodes():
            if state.get(node, 0) == 0:
                cycle = visit(node)

                if cycle:
                    return cycle

        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes(),
            "edges": [
                {
                    "source": source,
                    "target": target,
                }
                for source, target in self.edges()
            ],
            "adjacency": {
                node: self.successors(node)
                for node in self.nodes()
            },
        }


class LexiconEngine:
    def __init__(
        self,
        registry_path: Path | str = DEFAULT_REGISTRY_PATH,
        projection_registry_path: (
            Path | str
        ) = DEFAULT_PROJECTION_REGISTRY_PATH,
    ) -> None:
        self.registry_path = Path(
            registry_path
        ).expanduser().resolve()

        self.projection_registry_path = Path(
            projection_registry_path
        ).expanduser().resolve()

        self.registry = load_registry(
            self.registry_path
        )

        self.lexemes_by_id: dict[str, Lexeme] = {}
        self.canonical_index: dict[str, str] = {}
        self.alias_index: dict[str, str] = {}
        self.reserved_index: dict[str, dict[str, Any]] = {}
        self.concept_index: dict[str, list[str]] = (
            defaultdict(list)
        )

        self.graphs: dict[str, DirectedGraph] = {
            "dependency": DirectedGraph(),
            "inheritance": DirectedGraph(),
            "ontology": DirectedGraph(),
            "relationship": DirectedGraph(),
            "supersession": DirectedGraph(),
            "projection": DirectedGraph(),
            "validator": DirectedGraph(),
            "cross_reference": DirectedGraph(),
        }

        self._projection_config = (
            self._load_projection_registry()
        )

        self._build_indexes()
        self._build_graphs()

    def _load_projection_registry(
        self,
    ) -> Mapping[str, Any]:
        if not self.projection_registry_path.exists():
            return {}

        data = load_yaml(
            self.projection_registry_path
        )

        if not isinstance(data, Mapping):
            raise ProjectionError(
                "Projection registry must be an object."
            )

        return data

    def _build_indexes(self) -> None:
        for lexeme in self.registry.lexemes:
            self.lexemes_by_id[lexeme.id] = lexeme

            normalized_canonical = normalize_term(
                lexeme.canonical
            )

            self.canonical_index[
                normalized_canonical
            ] = lexeme.id

            normalized_concept = normalize_concept(
                lexeme.concept
            )

            self.concept_index[
                normalized_concept
            ].append(lexeme.id)

            self._reserve(
                lexeme.canonical,
                lexeme.id,
                "canonical",
            )

            for alias in lexeme.aliases:
                normalized_alias = normalize_term(alias)

                self.alias_index[
                    normalized_alias
                ] = lexeme.id

                self._reserve(
                    alias,
                    lexeme.id,
                    "alias",
                )

            for reserved in lexeme.reserved_spellings:
                self._reserve(
                    reserved,
                    lexeme.id,
                    "lexeme_reserved",
                )

            if lexeme.status in {
                "superseded",
                "reserved",
            }:
                self._reserve(
                    lexeme.canonical,
                    lexeme.id,
                    lexeme.status,
                )

                for alias in lexeme.aliases:
                    self._reserve(
                        alias,
                        lexeme.id,
                        lexeme.status,
                    )

        for reserved in self.registry.reserved:
            self._reserve(
                reserved,
                None,
                "registry_reserved",
            )

    def _reserve(
        self,
        spelling: str,
        lexeme_id: str | None,
        reason: str,
    ) -> None:
        normalized = normalize_term(spelling)

        existing = self.reserved_index.get(
            normalized
        )

        record = {
            "spelling": spelling,
            "normalized": normalized,
            "lexeme_id": lexeme_id,
            "reason": reason,
        }

        if existing is None:
            self.reserved_index[
                normalized
            ] = record
            return

        reasons = set(
            string_list(existing.get("reasons"))
        )

        previous_reason = existing.get("reason")

        if previous_reason:
            reasons.add(str(previous_reason))

        reasons.add(reason)

        owners = set(
            string_list(existing.get("owners"))
        )

        previous_owner = existing.get("lexeme_id")

        if previous_owner:
            owners.add(str(previous_owner))

        if lexeme_id:
            owners.add(lexeme_id)

        self.reserved_index[normalized] = {
            "spelling": existing.get(
                "spelling",
                spelling,
            ),
            "normalized": normalized,
            "owners": sorted(owners),
            "reasons": sorted(reasons),
        }

    def _build_graphs(self) -> None:
        for lexeme in self.registry.lexemes:
            for graph in self.graphs.values():
                graph.add_node(lexeme.id)

            for dependency in lexeme.dependencies:
                self.graphs["dependency"].add_edge(
                    lexeme.id,
                    dependency,
                )

                self.graphs[
                    "cross_reference"
                ].add_edge(
                    lexeme.id,
                    dependency,
                )

            for parent in lexeme.parents:
                self.graphs["inheritance"].add_edge(
                    lexeme.id,
                    parent,
                )

                self.graphs[
                    "cross_reference"
                ].add_edge(
                    lexeme.id,
                    parent,
                )

            for child in lexeme.children:
                self.graphs["inheritance"].add_edge(
                    child,
                    lexeme.id,
                )

                self.graphs[
                    "cross_reference"
                ].add_edge(
                    lexeme.id,
                    child,
                )

            for ontology_target in lexeme.ontology:
                self.graphs["ontology"].add_edge(
                    lexeme.id,
                    ontology_target,
                )

                self.graphs[
                    "cross_reference"
                ].add_edge(
                    lexeme.id,
                    ontology_target,
                )

            for relationship in lexeme.relationships:
                relationship_node = (
                    f"relation:{relationship.type}:"
                    f"{relationship.target}"
                )

                self.graphs[
                    "relationship"
                ].add_edge(
                    lexeme.id,
                    relationship.target,
                )

                self.graphs[
                    "cross_reference"
                ].add_edge(
                    lexeme.id,
                    relationship.target,
                )

                self.graphs[
                    "relationship"
                ].add_node(relationship_node)

            for predecessor in lexeme.lineage.supersedes:
                self.graphs[
                    "supersession"
                ].add_edge(
                    lexeme.id,
                    predecessor,
                )

                self.graphs[
                    "cross_reference"
                ].add_edge(
                    lexeme.id,
                    predecessor,
                )

            if lexeme.lineage.superseded_by:
                self.graphs[
                    "supersession"
                ].add_edge(
                    lexeme.lineage.superseded_by,
                    lexeme.id,
                )

                self.graphs[
                    "cross_reference"
                ].add_edge(
                    lexeme.id,
                    lexeme.lineage.superseded_by,
                )

            for projection in lexeme.projections:
                node = f"projection:{projection}"

                self.graphs["projection"].add_edge(
                    lexeme.id,
                    node,
                )

            for validator in lexeme.validators:
                node = f"validator:{validator}"

                self.graphs["validator"].add_edge(
                    lexeme.id,
                    node,
                )

    def resolve(
        self,
        reference: str,
        include_inactive: bool = True,
    ) -> Lexeme:
        candidate = reference.strip()

        if candidate in self.lexemes_by_id:
            lexeme = self.lexemes_by_id[candidate]
        else:
            normalized = normalize_term(candidate)
            lexeme_id = (
                self.canonical_index.get(normalized)
                or self.alias_index.get(normalized)
            )

            if not lexeme_id:
                raise ResolutionError(
                    f"Unknown lexeme reference: {reference}"
                )

            lexeme = self.lexemes_by_id[lexeme_id]

        if (
            not include_inactive
            and lexeme.status != "active"
        ):
            raise ResolutionError(
                f"Lexeme is not active: {lexeme.id}"
            )

        return lexeme

    def try_resolve(
        self,
        reference: str,
        include_inactive: bool = True,
    ) -> Lexeme | None:
        try:
            return self.resolve(
                reference,
                include_inactive=include_inactive,
            )
        except ResolutionError:
            return None

    def canonicalize(
        self,
        reference: str,
    ) -> str:
        return self.resolve(reference).canonical

    def canonical_id(
        self,
        reference: str,
    ) -> str:
        return self.resolve(reference).id

    def is_reserved(
        self,
        spelling: str,
    ) -> bool:
        return (
            normalize_term(spelling)
            in self.reserved_index
        )

    def reserved_record(
        self,
        spelling: str,
    ) -> Mapping[str, Any] | None:
        return self.reserved_index.get(
            normalize_term(spelling)
        )

    def dependencies(
        self,
        reference: str,
        recursive: bool = False,
    ) -> list[Lexeme]:
        lexeme = self.resolve(reference)
        graph = self.graphs["dependency"]

        ids = (
            graph.transitive_closure(lexeme.id)
            if recursive
            else graph.successors(lexeme.id)
        )

        return [
            self.lexemes_by_id[item]
            for item in ids
            if item in self.lexemes_by_id
        ]

    def dependents(
        self,
        reference: str,
        recursive: bool = False,
    ) -> list[Lexeme]:
        lexeme = self.resolve(reference)
        graph = self.graphs[
            "dependency"
        ].reverse()

        ids = (
            graph.transitive_closure(lexeme.id)
            if recursive
            else graph.successors(lexeme.id)
        )

        return [
            self.lexemes_by_id[item]
            for item in ids
            if item in self.lexemes_by_id
        ]

    def ancestors(
        self,
        reference: str,
        recursive: bool = True,
    ) -> list[Lexeme]:
        lexeme = self.resolve(reference)
        graph = self.graphs["inheritance"]

        ids = (
            graph.transitive_closure(lexeme.id)
            if recursive
            else graph.successors(lexeme.id)
        )

        return [
            self.lexemes_by_id[item]
            for item in ids
            if item in self.lexemes_by_id
        ]

    def descendants(
        self,
        reference: str,
        recursive: bool = True,
    ) -> list[Lexeme]:
        lexeme = self.resolve(reference)
        graph = self.graphs[
            "inheritance"
        ].reverse()

        ids = (
            graph.transitive_closure(lexeme.id)
            if recursive
            else graph.successors(lexeme.id)
        )

        return [
            self.lexemes_by_id[item]
            for item in ids
            if item in self.lexemes_by_id
        ]

    def supersession_chain(
        self,
        reference: str,
    ) -> dict[str, Any]:
        lexeme = self.resolve(reference)
        graph = self.graphs["supersession"]
        reverse = graph.reverse()

        predecessors = graph.transitive_closure(
            lexeme.id
        )
        successors = reverse.transitive_closure(
            lexeme.id
        )

        return {
            "lexeme": lexeme.to_dict(),
            "supersedes": [
                self.lexemes_by_id[item].to_dict()
                for item in predecessors
                if item in self.lexemes_by_id
            ],
            "superseded_by": [
                self.lexemes_by_id[item].to_dict()
                for item in successors
                if item in self.lexemes_by_id
            ],
        }

    def search(
        self,
        query: str,
        statuses: Sequence[str] | None = None,
        layers: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        normalized_query = normalize_search(query)

        status_filter = set(statuses or [])
        layer_filter = set(layers or [])

        results: list[dict[str, Any]] = []

        for lexeme in self.registry.lexemes:
            if (
                status_filter
                and lexeme.status not in status_filter
            ):
                continue

            if (
                layer_filter
                and lexeme.layer not in layer_filter
            ):
                continue

            score, matches = self._score_search(
                lexeme,
                normalized_query,
            )

            if score <= 0:
                continue

            results.append(
                {
                    "score": score,
                    "matches": matches,
                    "lexeme": lexeme.to_dict(),
                }
            )

        results.sort(
            key=lambda item: (
                -item["score"],
                item["lexeme"]["canonical"].casefold(),
                item["lexeme"]["id"],
            )
        )

        if limit is not None:
            return results[: max(limit, 0)]

        return results

    def _score_search(
        self,
        lexeme: Lexeme,
        normalized_query: str,
    ) -> tuple[int, list[str]]:
        if not normalized_query:
            return 1, ["all"]

        matches: list[str] = []
        score = 0

        normalized_id = normalize_search(lexeme.id)
        normalized_canonical = normalize_search(
            lexeme.canonical
        )
        normalized_concept = normalize_search(
            lexeme.concept
        )
        normalized_description = normalize_search(
            lexeme.description or ""
        )

        if normalized_query == normalized_id:
            score += 100
            matches.append("id_exact")

        elif normalized_query in normalized_id:
            score += 35
            matches.append("id_partial")

        if normalized_query == normalized_canonical:
            score += 100
            matches.append("canonical_exact")

        elif normalized_canonical.startswith(
            normalized_query
        ):
            score += 75
            matches.append("canonical_prefix")

        elif normalized_query in normalized_canonical:
            score += 55
            matches.append("canonical_partial")

        for alias in lexeme.aliases:
            normalized_alias = normalize_search(alias)

            if normalized_query == normalized_alias:
                score += 90
                matches.append(f"alias_exact:{alias}")

            elif normalized_alias.startswith(
                normalized_query
            ):
                score += 65
                matches.append(f"alias_prefix:{alias}")

            elif normalized_query in normalized_alias:
                score += 45
                matches.append(f"alias_partial:{alias}")

        if normalized_query == normalized_concept:
            score += 80
            matches.append("concept_exact")

        elif normalized_query in normalized_concept:
            score += 40
            matches.append("concept_partial")

        if normalized_query in normalized_description:
            score += 20
            matches.append("description")

        metadata_text = normalize_search(
            json.dumps(
                lexeme.metadata,
                sort_keys=True,
                ensure_ascii=False,
            )
        )

        if normalized_query in metadata_text:
            score += 10
            matches.append("metadata")

        return score, sorted(set(matches))

    def export_canonical(
        self,
    ) -> dict[str, Any]:
        lexemes = sorted(
            self.registry.lexemes,
            key=lambda item: item.id,
        )

        payload = {
            "registry_id": self.registry.registry_id,
            "version": self.registry.version,
            "authority": self.registry.authority.to_dict(),
            "generated_at": utc_now(),
            "source": str(self.registry_path),
            "lexemes": [
                lexeme.to_dict()
                for lexeme in lexemes
            ],
            "reserved": sorted(
                self.registry.reserved,
                key=normalize_term,
            ),
        }

        payload["digest"] = digest_payload(payload)

        return payload

    def project_all(
        self,
        output_root: Path | str | None = None,
    ) -> dict[str, Path]:
        root = (
            Path(output_root).expanduser().resolve()
            if output_root
            else LEXICON_ROOT
        )

        projection_specs = self._projection_specs()
        outputs: dict[str, Path] = {}

        projectors = {
            "canonical_index": (
                self.project_canonical_index
            ),
            "alias_index": self.project_alias_index,
            "dependency_graph": lambda: (
                self.project_graph("dependency")
            ),
            "reverse_dependency_graph": lambda: (
                self.project_graph(
                    "dependency",
                    reverse=True,
                )
            ),
            "inheritance_graph": lambda: (
                self.project_graph("inheritance")
            ),
            "ontology_graph": lambda: (
                self.project_graph("ontology")
            ),
            "relationship_graph": lambda: (
                self.project_graph("relationship")
            ),
            "supersession_graph": lambda: (
                self.project_graph("supersession")
            ),
            "projection_graph": lambda: (
                self.project_graph("projection")
            ),
            "validator_graph": lambda: (
                self.project_graph("validator")
            ),
            "cross_reference_graph": lambda: (
                self.project_graph("cross_reference")
            ),
            "search_index": self.project_search_index,
            "reserved_index": (
                self.project_reserved_index
            ),
            "audit_index": self.project_audit_index,
            "canonical_export": (
                self.export_canonical
            ),
        }

        for name, spec in projection_specs.items():
            if not spec.get("enabled", True):
                continue

            projector = projectors.get(name)

            if projector is None:
                raise ProjectionError(
                    f"Unknown projection: {name}"
                )

            relative_output = optional_string(
                spec.get("output")
            )

            if not relative_output:
                relative_output = (
                    f"runtime/{name}.json"
                )

            output_path = safe_join(
                root,
                relative_output,
            )

            payload = projector()
            write_json_atomic(
                output_path,
                payload,
            )

            outputs[name] = output_path

        manifest_path = root / "runtime" / (
            "projection_manifest.json"
        )

        manifest = self._projection_manifest(
            outputs
        )

        write_json_atomic(
            manifest_path,
            manifest,
        )

        outputs["projection_manifest"] = (
            manifest_path
        )

        return outputs

    def _projection_specs(
        self,
    ) -> Mapping[str, Mapping[str, Any]]:
        raw = self._projection_config.get(
            "projections",
            {},
        )

        if not isinstance(raw, Mapping):
            raise ProjectionError(
                "Projection registry projections "
                "must be an object."
            )

        result: dict[str, Mapping[str, Any]] = {}

        for name, spec in raw.items():
            if spec is None:
                result[str(name)] = {}
            elif isinstance(spec, Mapping):
                result[str(name)] = dict(spec)
            else:
                raise ProjectionError(
                    f"Projection {name} must be an object."
                )

        return result

    def project_canonical_index(
        self,
    ) -> dict[str, Any]:
        entries = {
            lexeme.canonical: {
                "id": lexeme.id,
                "canonical": lexeme.canonical,
                "concept": lexeme.concept,
                "layer": lexeme.layer,
                "status": lexeme.status,
            }
            for lexeme in sorted(
                self.registry.lexemes,
                key=lambda item: (
                    normalize_term(item.canonical),
                    item.id,
                ),
            )
        }

        return projection_payload(
            name="canonical_index",
            registry=self.registry,
            data=entries,
        )

    def project_alias_index(
        self,
    ) -> dict[str, Any]:
        entries: dict[str, Any] = {}

        for lexeme in sorted(
            self.registry.lexemes,
            key=lambda item: item.id,
        ):
            for alias in sorted(
                lexeme.aliases,
                key=normalize_term,
            ):
                entries[alias] = {
                    "id": lexeme.id,
                    "canonical": lexeme.canonical,
                    "normalized": normalize_term(alias),
                    "status": lexeme.status,
                }

        return projection_payload(
            name="alias_index",
            registry=self.registry,
            data=entries,
        )

    def project_reserved_index(
        self,
    ) -> dict[str, Any]:
        entries = {
            key: value
            for key, value
            in sorted(self.reserved_index.items())
        }

        return projection_payload(
            name="reserved_index",
            registry=self.registry,
            data=entries,
        )

    def project_graph(
        self,
        name: str,
        reverse: bool = False,
    ) -> dict[str, Any]:
        graph = self.graphs[name]

        if reverse:
            graph = graph.reverse()

        graph_name = (
            f"reverse_{name}"
            if reverse
            else name
        )

        return projection_payload(
            name=f"{graph_name}_graph",
            registry=self.registry,
            data=graph.to_dict(),
        )

    def project_search_index(
        self,
    ) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []

        for lexeme in sorted(
            self.registry.lexemes,
            key=lambda item: item.id,
        ):
            terms = [
                lexeme.id,
                lexeme.canonical,
                lexeme.concept,
                lexeme.description or "",
                *lexeme.aliases,
                *lexeme.reserved_spellings,
            ]

            entries.append(
                {
                    "id": lexeme.id,
                    "canonical": lexeme.canonical,
                    "status": lexeme.status,
                    "layer": lexeme.layer,
                    "terms": sorted(
                        {
                            normalize_search(term)
                            for term in terms
                            if term
                        }
                    ),
                    "raw_terms": [
                        term
                        for term in terms
                        if term
                    ],
                }
            )

        return projection_payload(
            name="search_index",
            registry=self.registry,
            data=entries,
        )

    def project_audit_index(
        self,
    ) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []

        for lexeme in sorted(
            self.registry.lexemes,
            key=lambda item: item.id,
        ):
            source_record = lexeme.to_dict()

            entries.append(
                {
                    "id": lexeme.id,
                    "canonical": lexeme.canonical,
                    "status": lexeme.status,
                    "layer": lexeme.layer,
                    "lineage": lexeme.lineage.to_dict(),
                    "provenance": (
                        lexeme.provenance.to_dict()
                    ),
                    "dependencies": sorted(
                        lexeme.dependencies
                    ),
                    "parents": sorted(lexeme.parents),
                    "relationships": [
                        relation.to_dict()
                        for relation
                        in lexeme.relationships
                    ],
                    "digest": digest_payload(
                        source_record
                    ),
                }
            )

        return projection_payload(
            name="audit_index",
            registry=self.registry,
            data=entries,
        )

    def _projection_manifest(
        self,
        outputs: Mapping[str, Path],
    ) -> dict[str, Any]:
        files: dict[str, Any] = {}

        for name, path in sorted(outputs.items()):
            files[name] = {
                "path": str(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }

        payload = {
            "registry_id": self.registry.registry_id,
            "registry_version": self.registry.version,
            "registry_source": str(self.registry_path),
            "registry_sha256": sha256_file(
                self.registry_path
            ),
            "generated_at": utc_now(),
            "files": files,
        }

        payload["digest"] = digest_payload(payload)

        return payload

    def describe(
        self,
        reference: str,
    ) -> dict[str, Any]:
        lexeme = self.resolve(reference)

        return {
            "lexeme": lexeme.to_dict(),
            "dependencies": [
                item.to_dict()
                for item in self.dependencies(
                    lexeme.id,
                    recursive=False,
                )
            ],
            "dependency_closure": [
                item.to_dict()
                for item in self.dependencies(
                    lexeme.id,
                    recursive=True,
                )
            ],
            "dependents": [
                item.to_dict()
                for item in self.dependents(
                    lexeme.id,
                    recursive=False,
                )
            ],
            "ancestors": [
                item.to_dict()
                for item in self.ancestors(
                    lexeme.id,
                    recursive=True,
                )
            ],
            "descendants": [
                item.to_dict()
                for item in self.descendants(
                    lexeme.id,
                    recursive=True,
                )
            ],
            "supersession": (
                self.supersession_chain(
                    lexeme.id
                )
            ),
            "reserved": self.reserved_record(
                lexeme.canonical
            ),
        }

    def integrity_snapshot(
        self,
    ) -> dict[str, Any]:
        registry_payload = self.registry.to_dict()

        graph_digests = {
            name: digest_payload(graph.to_dict())
            for name, graph
            in sorted(self.graphs.items())
        }

        payload = {
            "registry_id": self.registry.registry_id,
            "registry_version": self.registry.version,
            "registry_path": str(self.registry_path),
            "registry_sha256": sha256_file(
                self.registry_path
            ),
            "registry_digest": digest_payload(
                registry_payload
            ),
            "lexeme_count": len(
                self.registry.lexemes
            ),
            "canonical_count": len(
                self.canonical_index
            ),
            "alias_count": len(self.alias_index),
            "reserved_count": len(
                self.reserved_index
            ),
            "graph_digests": graph_digests,
            "generated_at": utc_now(),
        }

        payload["digest"] = digest_payload(payload)

        return payload


def load_registry(
    path: Path | str,
) -> Registry:
    resolved = Path(path).expanduser().resolve()
    data = load_yaml(resolved)

    if not isinstance(data, Mapping):
        raise RegistryLoadError(
            "Registry root must be an object."
        )

    return Registry.from_mapping(
        data,
        source_path=resolved,
    )


def load_yaml(
    path: Path | str,
) -> Any:
    resolved = Path(path).expanduser().resolve()

    if not resolved.exists():
        raise RegistryLoadError(
            f"File not found: {resolved}"
        )

    try:
        with resolved.open(
            "r",
            encoding="utf-8",
        ) as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise RegistryLoadError(
            f"Invalid YAML in {resolved}: {exc}"
        ) from exc
    except OSError as exc:
        raise RegistryLoadError(
            f"Unable to read {resolved}: {exc}"
        ) from exc


def write_json_atomic(
    path: Path | str,
    payload: Any,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_name(
        f".{destination.name}.tmp.{os.getpid()}"
    )

    serialized = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"

    try:
        temporary.write_text(
            serialized,
            encoding="utf-8",
        )

        os.replace(
            temporary,
            destination,
        )
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

        raise ProjectionError(
            f"Unable to write {destination}: {exc}"
        ) from exc


def normalize_term(value: str) -> str:
    normalized = unicodedata.normalize(
        "NFKC",
        str(value),
    )

    normalized = normalize_punctuation(normalized)
    normalized = collapse_whitespace(normalized)

    return normalized.casefold()


def normalize_concept(value: str) -> str:
    normalized = normalize_term(value)

    normalized = re.sub(
        r"[^\w\s-]",
        " ",
        normalized,
    )

    return collapse_whitespace(normalized)


def normalize_search(value: str) -> str:
    normalized = unicodedata.normalize(
        "NFKC",
        str(value),
    )

    normalized = normalize_punctuation(normalized)
    normalized = normalized.casefold()

    normalized = re.sub(
        r"[_:/\\|]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"[^\w\s.-]",
        " ",
        normalized,
    )

    return collapse_whitespace(normalized)


def normalize_punctuation(value: str) -> str:
    translations = {
        ord("‐"): "-",
        ord("-"): "-",
        ord("‒"): "-",
        ord("–"): "-",
        ord("—"): "-",
        ord("―"): "-",
        ord("‘"): "'",
        ord("’"): "'",
        ord("‚"): "'",
        ord("‛"): "'",
        ord("“"): '"',
        ord("”"): '"',
        ord("„"): '"',
        ord("‟"): '"',
    }

    return value.translate(translations)


def collapse_whitespace(value: str) -> str:
    return " ".join(str(value).strip().split())


def optional_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def string_list(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        text = value.strip()

        return [text] if text else []

    if isinstance(value, Sequence):
        result: list[str] = []

        for item in value:
            if item is None:
                continue

            text = str(item).strip()

            if text:
                result.append(text)

        return result

    return [str(value).strip()]


def list_or_empty(
    value: Any,
) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def mapping_or_empty(
    value: Any,
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value

    return {}


def compact_mapping(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, item in value.items():
        if item is None:
            continue

        if item == "":
            continue

        if item == []:
            continue

        if item == {}:
            continue

        result[key] = item

    return result


def safe_join(
    root: Path,
    relative: str,
) -> Path:
    candidate = (
        root / relative
    ).expanduser().resolve()

    root_resolved = root.resolve()

    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ProjectionError(
            f"Projection escapes root: {relative}"
        ) from exc

    return candidate


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def canonical_json(
    payload: Any,
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def digest_payload(
    payload: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(payload)
    ).hexdigest()


def sha256_file(
    path: Path | str,
) -> str:
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def projection_payload(
    name: str,
    registry: Registry,
    data: Any,
) -> dict[str, Any]:
    payload = {
        "projection": name,
        "registry_id": registry.registry_id,
        "registry_version": registry.version,
        "authority": registry.authority.to_dict(),
        "generated_at": utc_now(),
        "data": data,
    }

    payload["digest"] = digest_payload(payload)

    return payload


def print_json(
    value: Any,
) -> None:
    json.dump(
        value,
        sys.stdout,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lexicon-engine",
        description=(
            "Savant constitutional lexicon runtime."
        ),
    )

    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY_PATH),
    )

    parser.add_argument(
        "--projection-registry",
        default=str(
            DEFAULT_PROJECTION_REGISTRY_PATH
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    resolve_parser = subparsers.add_parser(
        "resolve"
    )

    resolve_parser.add_argument("reference")

    canonicalize_parser = subparsers.add_parser(
        "canonicalize"
    )

    canonicalize_parser.add_argument("reference")

    describe_parser = subparsers.add_parser(
        "describe"
    )

    describe_parser.add_argument("reference")

    search_parser = subparsers.add_parser(
        "search"
    )

    search_parser.add_argument("query")
    search_parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
    )
    search_parser.add_argument(
        "--layer",
        action="append",
        dest="layers",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
    )

    dependencies_parser = subparsers.add_parser(
        "dependencies"
    )

    dependencies_parser.add_argument("reference")
    dependencies_parser.add_argument(
        "--recursive",
        action="store_true",
    )

    dependents_parser = subparsers.add_parser(
        "dependents"
    )

    dependents_parser.add_argument("reference")
    dependents_parser.add_argument(
        "--recursive",
        action="store_true",
    )

    ancestors_parser = subparsers.add_parser(
        "ancestors"
    )

    ancestors_parser.add_argument("reference")
    ancestors_parser.add_argument(
        "--direct",
        action="store_true",
    )

    descendants_parser = subparsers.add_parser(
        "descendants"
    )

    descendants_parser.add_argument("reference")
    descendants_parser.add_argument(
        "--direct",
        action="store_true",
    )

    reserved_parser = subparsers.add_parser(
        "reserved"
    )

    reserved_parser.add_argument("spelling")

    graph_parser = subparsers.add_parser("graph")

    graph_parser.add_argument(
        "name",
        choices=[
            "dependency",
            "inheritance",
            "ontology",
            "relationship",
            "supersession",
            "projection",
            "validator",
            "cross_reference",
        ],
    )

    graph_parser.add_argument(
        "--reverse",
        action="store_true",
    )

    export_parser = subparsers.add_parser(
        "export"
    )

    export_parser.add_argument(
        "--output",
    )

    project_parser = subparsers.add_parser(
        "project"
    )

    project_parser.add_argument(
        "--output-root",
    )

    snapshot_parser = subparsers.add_parser(
        "snapshot"
    )

    snapshot_parser.add_argument(
        "--output",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        engine = LexiconEngine(
            registry_path=args.registry,
            projection_registry_path=(
                args.projection_registry
            ),
        )

        if args.command == "resolve":
            print_json(
                engine.resolve(
                    args.reference
                ).to_dict()
            )

        elif args.command == "canonicalize":
            print(
                engine.canonicalize(
                    args.reference
                )
            )

        elif args.command == "describe":
            print_json(
                engine.describe(
                    args.reference
                )
            )

        elif args.command == "search":
            print_json(
                engine.search(
                    args.query,
                    statuses=args.statuses,
                    layers=args.layers,
                    limit=args.limit,
                )
            )

        elif args.command == "dependencies":
            print_json(
                [
                    item.to_dict()
                    for item
                    in engine.dependencies(
                        args.reference,
                        recursive=args.recursive,
                    )
                ]
            )

        elif args.command == "dependents":
            print_json(
                [
                    item.to_dict()
                    for item
                    in engine.dependents(
                        args.reference,
                        recursive=args.recursive,
                    )
                ]
            )

        elif args.command == "ancestors":
            print_json(
                [
                    item.to_dict()
                    for item
                    in engine.ancestors(
                        args.reference,
                        recursive=not args.direct,
                    )
                ]
            )

        elif args.command == "descendants":
            print_json(
                [
                    item.to_dict()
                    for item
                    in engine.descendants(
                        args.reference,
                        recursive=not args.direct,
                    )
                ]
            )

        elif args.command == "reserved":
            record = engine.reserved_record(
                args.spelling
            )

            print_json(
                {
                    "spelling": args.spelling,
                    "reserved": record is not None,
                    "record": record,
                }
            )

        elif args.command == "graph":
            print_json(
                engine.project_graph(
                    args.name,
                    reverse=args.reverse,
                )
            )

        elif args.command == "export":
            payload = engine.export_canonical()

            if args.output:
                write_json_atomic(
                    args.output,
                    payload,
                )
            else:
                print_json(payload)

        elif args.command == "project":
            outputs = engine.project_all(
                args.output_root
            )

            print_json(
                {
                    key: str(value)
                    for key, value
                    in outputs.items()
                }
            )

        elif args.command == "snapshot":
            payload = engine.integrity_snapshot()

            if args.output:
                write_json_atomic(
                    args.output,
                    payload,
                )
            else:
                print_json(payload)

        else:
            parser.error(
                f"Unknown command: {args.command}"
            )

        return 0

    except LexiconError as exc:
        print(
            f"lexicon-engine: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
