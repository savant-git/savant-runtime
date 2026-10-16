#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence


OWNER = "carbon"
SPECIALIZATION = "guise"
SCHEMA = "savant://carbon/guise/1"

ROOT = Path("/root/savant-runtime").resolve()

GUISE_ROOT = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "carbon"
).resolve()

MANIFEST_PATH = (
    GUISE_ROOT
    / "registry"
    / "manifests"
    / "guise.json"
).resolve()


class GuiseError(ValueError):
    pass


class GuiseProviderError(GuiseError):
    pass


class GuiseInvariantError(GuiseError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def stable_id(
    kind: str,
    payload: Mapping[str, Any],
) -> str:
    normalized_kind = str(kind).strip().lower()

    if not normalized_kind:
        raise GuiseError("stable identity kind is required")

    return (
        f"guise:{normalized_kind}:"
        f"{digest(dict(payload))[:24]}"
    )


def _required_text(
    value: Any,
    field_name: str,
) -> str:
    normalized = str(value or "").strip()

    if not normalized:
        raise GuiseError(
            f"{field_name} is required"
        )

    return normalized


def _optional_text(
    value: Any,
) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _unique_strings(
    values: Iterable[Any],
) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = str(value or "").strip()

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        output.append(normalized)

    return tuple(output)


def load_manifest() -> dict[str, Any]:
    try:
        value = json.loads(
            MANIFEST_PATH.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise GuiseInvariantError(
            f"guise manifest not found: "
            f"{MANIFEST_PATH}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise GuiseInvariantError(
            "guise manifest is invalid json"
        ) from exc

    if not isinstance(value, dict):
        raise GuiseInvariantError(
            "guise manifest must be a mapping"
        )

    return value


def validate_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(manifest)

    domains = value.get("domains")

    if not isinstance(domains, dict):
        raise GuiseInvariantError(
            "guise domains must be a mapping"
        )

    if len(domains) != 20:
        raise GuiseInvariantError(
            "guise requires exactly 20 domains"
        )

    placements: list[str] = []

    for domain, categories in domains.items():
        if not isinstance(domain, str):
            raise GuiseInvariantError(
                "domain identifiers must be strings"
            )

        if not isinstance(categories, list):
            raise GuiseInvariantError(
                f"domain {domain} categories "
                f"must be a list"
            )

        if len(categories) != 5:
            raise GuiseInvariantError(
                f"domain {domain} requires "
                f"exactly five categories"
            )

        for category in categories:
            normalized = _required_text(
                category,
                f"{domain} category",
            )

            if " " in normalized:
                raise GuiseInvariantError(
                    f"category tag must be one word: "
                    f"{normalized}"
                )

            placements.append(normalized)

    if len(placements) != 100:
        raise GuiseInvariantError(
            "guise requires exactly "
            "100 category placements"
        )

    value["category_placements"] = 100
    value["distinct_categories"] = len(
        set(placements)
    )
    value["manifest_digest"] = digest(value)

    return value


@dataclass(frozen=True)
class TemporalScope:
    valid_from: str | None = None
    valid_to: str | None = None
    known_from: str | None = None
    known_to: str | None = None
    phase: str | None = None
    scene: str | None = None

    def projection(self) -> dict[str, Any]:
        return {
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "known_from": self.known_from,
            "known_to": self.known_to,
            "phase": self.phase,
            "scene": self.scene,
        }


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    location: str | None = None
    source_kind: str = "imported_source"
    authority_class: str = "source"
    content_digest: str | None = None

    def projection(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "location": self.location,
            "source_kind": self.source_kind,
            "authority_class": (
                self.authority_class
            ),
            "content_digest": (
                self.content_digest
            ),
        }


@dataclass(frozen=True)
class Evidence:
    subject_id: str
    observation: str
    source: SourceReference
    epistemic_class: str = "observation"
    temporal: TemporalScope = field(
        default_factory=TemporalScope
    )
    evidence_state: str = "observed"
    tags: tuple[str, ...] = ()
    notes: str | None = None
    id: str = ""

    def __post_init__(self) -> None:
        subject = _required_text(
            self.subject_id,
            "evidence subject_id",
        )
        observation = _required_text(
            self.observation,
            "evidence observation",
        )

        material = {
            "subject_id": subject,
            "observation": observation,
            "source": self.source.projection(),
            "epistemic_class": (
                self.epistemic_class
            ),
            "temporal": self.temporal.projection(),
            "evidence_state": (
                self.evidence_state
            ),
            "tags": list(self.tags),
        }

        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "evidence",
                    material,
                ),
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_evidence",
            "subject_id": self.subject_id,
            "observation": self.observation,
            "source": self.source.projection(),
            "epistemic_class": (
                self.epistemic_class
            ),
            "temporal": self.temporal.projection(),
            "evidence_state": (
                self.evidence_state
            ),
            "tags": list(self.tags),
            "notes": self.notes,
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class CategorySubstantiation:
    character_id: str
    domain: str
    category: str
    formulation: str
    epistemic_class: str = "hypothesis"
    evidence_refs: tuple[str, ...] = ()
    counterevidence_refs: tuple[str, ...] = ()
    alternative_explanations: tuple[str, ...] = ()
    contradiction_refs: tuple[str, ...] = ()
    relationship_refs: tuple[str, ...] = ()
    confidence: str = "unknown"
    temporal: TemporalScope = field(
        default_factory=TemporalScope
    )
    id: str = ""

    def __post_init__(self) -> None:
        material = {
            "character_id": _required_text(
                self.character_id,
                "character_id",
            ),
            "domain": _required_text(
                self.domain,
                "domain",
            ),
            "category": _required_text(
                self.category,
                "category",
            ),
            "formulation": _required_text(
                self.formulation,
                "formulation",
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "counterevidence_refs": list(
                self.counterevidence_refs
            ),
            "alternatives": list(
                self.alternative_explanations
            ),
            "contradictions": list(
                self.contradiction_refs
            ),
            "relationships": list(
                self.relationship_refs
            ),
            "temporal": self.temporal.projection(),
        }

        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "category-substantiation",
                    material,
                ),
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": (
                "character_category_substantiation"
            ),
            "character_id": self.character_id,
            "semantic_ref": (
                f"psychology.category."
                f"{self.category}"
            ),
            "domain_ref": (
                f"psychology.domain."
                f"{self.domain}"
            ),
            "formulation": self.formulation,
            "epistemic_class": (
                self.epistemic_class
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "counterevidence_refs": list(
                self.counterevidence_refs
            ),
            "alternative_explanations": list(
                self.alternative_explanations
            ),
            "contradiction_refs": list(
                self.contradiction_refs
            ),
            "relationship_refs": list(
                self.relationship_refs
            ),
            "confidence": self.confidence,
            "temporal": self.temporal.projection(),
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class Relationship:
    left_id: str
    segue: str
    right_id: str
    scope: str | None = None
    temporal: TemporalScope = field(
        default_factory=TemporalScope
    )
    evidence_refs: tuple[str, ...] = ()
    epistemic_class: str = "hypothesis"
    id: str = ""

    def __post_init__(self) -> None:
        material = {
            "left_id": _required_text(
                self.left_id,
                "left_id",
            ),
            "segue": _required_text(
                self.segue,
                "segue",
            ),
            "right_id": _required_text(
                self.right_id,
                "right_id",
            ),
            "scope": self.scope,
            "temporal": self.temporal.projection(),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
        }

        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "relationship",
                    material,
                ),
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "typed_character_segue",
            "left_id": self.left_id,
            "segue": self.segue,
            "right_id": self.right_id,
            "scope": self.scope,
            "temporal": self.temporal.projection(),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class Contradiction:
    character_id: str
    contradiction_class: str
    left_ref: str
    right_ref: str
    interpretation: str | None = None
    unresolved: bool = True
    id: str = ""

    def __post_init__(self) -> None:
        material = {
            "character_id": self.character_id,
            "contradiction_class": (
                self.contradiction_class
            ),
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "interpretation": (
                self.interpretation
            ),
            "unresolved": self.unresolved,
        }

        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "contradiction",
                    material,
                ),
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_contradiction",
            "character_id": self.character_id,
            "contradiction_class": (
                self.contradiction_class
            ),
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "interpretation": (
                self.interpretation
            ),
            "unresolved": self.unresolved,
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class KnowledgeAssertion:
    character_id: str
    proposition_ref: str
    knowledge_state: str
    temporal: TemporalScope = field(
        default_factory=TemporalScope
    )
    evidence_refs: tuple[str, ...] = ()
    id: str = ""

    def __post_init__(self) -> None:
        material = {
            "character_id": self.character_id,
            "proposition_ref": (
                self.proposition_ref
            ),
            "knowledge_state": (
                self.knowledge_state
            ),
            "temporal": self.temporal.projection(),
            "evidence_refs": list(
                self.evidence_refs
            ),
        }

        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "knowledge",
                    material,
                ),
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_knowledge",
            "character_id": self.character_id,
            "proposition_ref": (
                self.proposition_ref
            ),
            "knowledge_state": (
                self.knowledge_state
            ),
            "temporal": self.temporal.projection(),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class CharacterState:
    character_id: str
    at: str | None = None
    phase: str | None = None
    relationship_state: Mapping[str, Any] = field(
        default_factory=dict
    )
    knowledge_refs: tuple[str, ...] = ()
    physiological: Mapping[str, Any] = field(
        default_factory=dict
    )
    emotional: Mapping[str, Any] = field(
        default_factory=dict
    )
    pressures: tuple[str, ...] = ()
    goals: tuple[str, ...] = ()
    incentives: tuple[str, ...] = ()
    recent_event_refs: tuple[str, ...] = ()
    id: str = ""

    def __post_init__(self) -> None:
        material = {
            "character_id": self.character_id,
            "at": self.at,
            "phase": self.phase,
            "relationship_state": dict(
                self.relationship_state
            ),
            "knowledge_refs": list(
                self.knowledge_refs
            ),
            "physiological": dict(
                self.physiological
            ),
            "emotional": dict(
                self.emotional
            ),
            "pressures": list(self.pressures),
            "goals": list(self.goals),
            "incentives": list(self.incentives),
            "recent_event_refs": list(
                self.recent_event_refs
            ),
        }

        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "state",
                    material,
                ),
            )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_state",
            "character_id": self.character_id,
            "at": self.at,
            "phase": self.phase,
            "relationship_state": dict(
                self.relationship_state
            ),
            "knowledge_refs": list(
                self.knowledge_refs
            ),
            "physiological": dict(
                self.physiological
            ),
            "emotional": dict(
                self.emotional
            ),
            "pressures": list(self.pressures),
            "goals": list(self.goals),
            "incentives": list(self.incentives),
            "recent_event_refs": list(
                self.recent_event_refs
            ),
            "authority_effect": "none",
        }


class ExtractionProvider(Protocol):
    provider_id: str

    def extract(
        self,
        *,
        character_id: str,
        text: str,
        source: SourceReference,
        manifest: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...


class GenerationProvider(Protocol):
    provider_id: str

    def generate(
        self,
        *,
        character_id: str,
        request: Mapping[str, Any],
        manifest: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...


@dataclass
class CharacterGraph:
    character_id: str
    display_name: str | None = None
    evidence: dict[str, Evidence] = field(
        default_factory=dict
    )
    categories: dict[
        str,
        CategorySubstantiation,
    ] = field(default_factory=dict)
    relationships: dict[
        str,
        Relationship,
    ] = field(default_factory=dict)
    contradictions: dict[
        str,
        Contradiction,
    ] = field(default_factory=dict)
    knowledge: dict[
        str,
        KnowledgeAssertion,
    ] = field(default_factory=dict)
    states: dict[
        str,
        CharacterState,
    ] = field(default_factory=dict)
    physical: dict[str, Any] = field(
        default_factory=dict
    )
    chronology: list[dict[str, Any]] = field(
        default_factory=list
    )
    unresolved: list[str] = field(
        default_factory=list
    )
    lineage: list[str] = field(
        default_factory=list
    )
    provenance: list[dict[str, Any]] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.character_id = _required_text(
            self.character_id,
            "character_id",
        )

    def add_evidence(
        self,
        item: Evidence,
    ) -> Evidence:
        if item.subject_id != self.character_id:
            raise GuiseInvariantError(
                "evidence subject does not match "
                "character graph"
            )

        self.evidence[item.id] = item
        return item

    def add_category(
        self,
        item: CategorySubstantiation,
    ) -> CategorySubstantiation:
        if item.character_id != self.character_id:
            raise GuiseInvariantError(
                "category character does not match "
                "character graph"
            )

        self.categories[item.id] = item
        return item

    def add_relationship(
        self,
        item: Relationship,
    ) -> Relationship:
        self.relationships[item.id] = item
        return item

    def add_contradiction(
        self,
        item: Contradiction,
    ) -> Contradiction:
        if item.character_id != self.character_id:
            raise GuiseInvariantError(
                "contradiction character mismatch"
            )

        self.contradictions[item.id] = item
        return item

    def add_knowledge(
        self,
        item: KnowledgeAssertion,
    ) -> KnowledgeAssertion:
        if item.character_id != self.character_id:
            raise GuiseInvariantError(
                "knowledge character mismatch"
            )

        self.knowledge[item.id] = item
        return item

    def add_state(
        self,
        item: CharacterState,
    ) -> CharacterState:
        if item.character_id != self.character_id:
            raise GuiseInvariantError(
                "state character mismatch"
            )

        self.states[item.id] = item
        return item

    def evidence_for(
        self,
        category: CategorySubstantiation,
    ) -> dict[str, list[dict[str, Any]]]:
        supporting = [
            self.evidence[ref].projection()
            for ref in category.evidence_refs
            if ref in self.evidence
        ]

        counter = [
            self.evidence[ref].projection()
            for ref in category.counterevidence_refs
            if ref in self.evidence
        ]

        return {
            "supporting": supporting,
            "counter": counter,
        }

    def falsify(
        self,
        category_id: str,
    ) -> dict[str, Any]:
        if category_id not in self.categories:
            raise GuiseError(
                f"unknown category substantiation: "
                f"{category_id}"
            )

        category = self.categories[
            category_id
        ]
        evidence = self.evidence_for(category)

        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "falsify",
            "character_id": self.character_id,
            "category": category.projection(),
            "supporting_evidence": (
                evidence["supporting"]
            ),
            "counterevidence": (
                evidence["counter"]
            ),
            "alternative_explanations": list(
                category.alternative_explanations
            ),
            "survived_counterevidence": bool(
                evidence["counter"]
            ),
            "authority_effect": "none",
        }

    def minimum_differential(
        self,
        *,
        proposed_behavior: str,
        conflicts: Sequence[str],
        candidate_changes: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        normalized = [
            dict(change)
            for change in candidate_changes
            if isinstance(change, Mapping)
        ]

        ranked = sorted(
            normalized,
            key=lambda item: (
                int(item.get("change_count", 1)),
                canonical_json(item),
            ),
        )

        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "character_differential",
            "character_id": self.character_id,
            "proposed_behavior": (
                proposed_behavior
            ),
            "conflicts": list(conflicts),
            "candidate_changes": ranked,
            "minimum_candidate": (
                ranked[0] if ranked else None
            ),
            "mutates_character": False,
            "authority_effect": "none",
        }

    def domain_projection(
        self,
        domain: str,
        manifest: Mapping[str, Any],
    ) -> dict[str, Any]:
        domains = manifest.get(
            "domains",
            {}
        )

        if domain not in domains:
            raise GuiseError(
                f"unknown guise domain: {domain}"
            )

        expected = set(domains[domain])

        categories = [
            item
            for item in self.categories.values()
            if (
                item.domain == domain
                and item.category in expected
            )
        ]

        categories.sort(
            key=lambda item: (
                item.category,
                item.id,
            )
        )

        evidence_refs: set[str] = set()
        counter_refs: set[str] = set()
        contradiction_refs: set[str] = set()

        for item in categories:
            evidence_refs.update(
                item.evidence_refs
            )
            counter_refs.update(
                item.counterevidence_refs
            )
            contradiction_refs.update(
                item.contradiction_refs
            )

        projection = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "projection_type": "domain_profile",
            "character_id": self.character_id,
            "domain": domain,
            "expected_categories": (
                list(domains[domain])
            ),
            "substantiations": [
                item.projection()
                for item in categories
            ],
            "evidence_refs": sorted(
                evidence_refs
            ),
            "counterevidence_refs": sorted(
                counter_refs
            ),
            "contradiction_refs": sorted(
                contradiction_refs
            ),
            "complete": (
                len(
                    {
                        item.category
                        for item in categories
                    }
                )
                == 5
            ),
            "authority_effect": "none",
        }

        projection["projection_digest"] = (
            digest(projection)
        )

        return projection

    def projection(
        self,
        manifest: Mapping[str, Any],
    ) -> dict[str, Any]:
        domains = {
            domain: self.domain_projection(
                domain,
                manifest,
            )
            for domain in manifest["domains"]
        }

        projection = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "projection_type": (
                "character_graph"
            ),
            "character_id": self.character_id,
            "display_name": self.display_name,
            "physical": dict(self.physical),
            "domains": domains,
            "evidence": [
                item.projection()
                for item in sorted(
                    self.evidence.values(),
                    key=lambda value: value.id,
                )
            ],
            "relationships": [
                item.projection()
                for item in sorted(
                    self.relationships.values(),
                    key=lambda value: value.id,
                )
            ],
            "contradictions": [
                item.projection()
                for item in sorted(
                    self.contradictions.values(),
                    key=lambda value: value.id,
                )
            ],
            "knowledge": [
                item.projection()
                for item in sorted(
                    self.knowledge.values(),
                    key=lambda value: value.id,
                )
            ],
            "states": [
                item.projection()
                for item in sorted(
                    self.states.values(),
                    key=lambda value: value.id,
                )
            ],
            "chronology": list(
                self.chronology
            ),
            "unresolved": list(
                self.unresolved
            ),
            "lineage": list(self.lineage),
            "provenance": list(
                self.provenance
            ),
            "authority_effect": "none",
            "authoritative": False,
        }

        projection["projection_digest"] = (
            digest(projection)
        )

        return projection


class Guise:
    def __init__(
        self,
        *,
        extraction_provider: (
            ExtractionProvider | None
        ) = None,
        generation_provider: (
            GenerationProvider | None
        ) = None,
    ) -> None:
        self.manifest = validate_manifest(
            load_manifest()
        )
        self.extraction_provider = (
            extraction_provider
        )
        self.generation_provider = (
            generation_provider
        )

    def new_character(
        self,
        character_id: str,
        *,
        display_name: str | None = None,
    ) -> CharacterGraph:
        return CharacterGraph(
            character_id=character_id,
            display_name=display_name,
        )

    def ingest_text(
        self,
        graph: CharacterGraph,
        *,
        text: str,
        source_id: str,
        location: str | None = None,
        source_kind: str = "imported_writing",
        authority_class: str = "source",
    ) -> dict[str, Any]:
        content = _required_text(
            text,
            "text",
        )

        source = SourceReference(
            source_id=_required_text(
                source_id,
                "source_id",
            ),
            location=location,
            source_kind=source_kind,
            authority_class=authority_class,
            content_digest=hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest(),
        )

        receipt = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "ingest_text",
            "character_id": (
                graph.character_id
            ),
            "source": source.projection(),
            "characters": len(content),
            "authority_effect": "none",
            "source_authority_preserved": True,
        }

        if self.extraction_provider is None:
            receipt["extraction"] = {
                "status": "provider_not_attached",
                "candidate_count": 0,
                "automatic_canonization": False,
            }
            receipt["receipt_digest"] = digest(
                receipt
            )
            return receipt

        try:
            extracted = dict(
                self.extraction_provider.extract(
                    character_id=(
                        graph.character_id
                    ),
                    text=content,
                    source=source,
                    manifest=self.manifest,
                )
            )
        except Exception as exc:
            raise GuiseProviderError(
                "guise extraction provider failed"
            ) from exc

        receipt["extraction"] = {
            "status": "derived_candidates",
            "provider_id": getattr(
                self.extraction_provider,
                "provider_id",
                "unknown",
            ),
            "payload": extracted,
            "automatic_canonization": False,
        }
        receipt["receipt_digest"] = digest(
            receipt
        )

        return receipt

    def generate_character_candidates(
        self,
        graph: CharacterGraph,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if self.generation_provider is None:
            return {
                "schema": SCHEMA,
                "owner": OWNER,
                "specialization": SPECIALIZATION,
                "operation": (
                    "generate_character_candidates"
                ),
                "character_id": (
                    graph.character_id
                ),
                "status": (
                    "provider_not_attached"
                ),
                "generated": [],
                "authoritative": False,
                "authority_effect": "none",
            }

        try:
            generated = dict(
                self.generation_provider.generate(
                    character_id=(
                        graph.character_id
                    ),
                    request=dict(request),
                    manifest=self.manifest,
                )
            )
        except Exception as exc:
            raise GuiseProviderError(
                "guise generation provider failed"
            ) from exc

        projection = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "generate_character_candidates"
            ),
            "character_id": graph.character_id,
            "provider_id": getattr(
                self.generation_provider,
                "provider_id",
                "unknown",
            ),
            "request": dict(request),
            "generated": generated,
            "epistemic_class": "hypothesis",
            "authoritative": False,
            "requires_acceptance": True,
            "authority_effect": "none",
        }

        projection["projection_digest"] = (
            digest(projection)
        )

        return projection

    def behavioral_alternatives(
        self,
        graph: CharacterGraph,
        *,
        situation: Mapping[str, Any],
        candidates: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        allowed = set(
            self.manifest[
                "behavior_classes"
            ]
        )

        normalized: list[dict[str, Any]] = []

        for candidate in candidates:
            item = dict(candidate)

            classification = str(
                item.get(
                    "classification",
                    "requires_substantiation",
                )
            )

            if classification not in allowed:
                raise GuiseInvariantError(
                    "invalid behavioral "
                    "classification"
                )

            normalized.append(item)

        projection = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "behavioral_alternatives"
            ),
            "character_id": (
                graph.character_id
            ),
            "situation": dict(situation),
            "alternatives": normalized,
            "single_deterministic_answer": False,
            "mutates_character": False,
            "authority_effect": "none",
        }

        projection["projection_digest"] = (
            digest(projection)
        )

        return projection

    def compare(
        self,
        left: CharacterGraph,
        right: CharacterGraph,
    ) -> dict[str, Any]:
        left_categories = {
            (
                item.domain,
                item.category,
            ): item
            for item in left.categories.values()
        }
        right_categories = {
            (
                item.domain,
                item.category,
            ): item
            for item in right.categories.values()
        }

        keys = sorted(
            set(left_categories)
            | set(right_categories)
        )

        comparison = []

        for key in keys:
            left_item = left_categories.get(
                key
            )
            right_item = right_categories.get(
                key
            )

            comparison.append(
                {
                    "domain": key[0],
                    "category": key[1],
                    "left": (
                        left_item.projection()
                        if left_item
                        else None
                    ),
                    "right": (
                        right_item.projection()
                        if right_item
                        else None
                    ),
                }
            )

        projection = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "character_compare",
            "left_character_id": (
                left.character_id
            ),
            "right_character_id": (
                right.character_id
            ),
            "comparison": comparison,
            "mutates_inputs": False,
            "authority_effect": "none",
        }

        projection["projection_digest"] = (
            digest(projection)
        )

        return projection


def health() -> dict[str, Any]:
    manifest = validate_manifest(
        load_manifest()
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "specialization": SPECIALIZATION,
        "status": "ok",
        "domains": len(
            manifest["domains"]
        ),
        "category_placements": (
            manifest["category_placements"]
        ),
        "distinct_categories": (
            manifest["distinct_categories"]
        ),
        "manifest_digest": (
            manifest["manifest_digest"]
        ),
        "character_specific_data_hardcoded": (
            False
        ),
        "authority_effect": "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            health(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
