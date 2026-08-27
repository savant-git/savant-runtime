#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "1.0.0"

EVIDENTIARY_STATES = (
    "corroborated",
    "reported",
    "inferred",
    "disputed",
    "unknown",
)

AUTHORITY_STATES = (
    "none",
    "unreviewed",
    "provisional",
    "admitted",
    "accepted",
    "superseded",
    "rejected",
)

INSTANCE_KINDS = (
    "matter",
    "source",
    "assertion",
    "event",
    "evidence",
    "claim",
    "entity",
    "media",
    "transcript",
    "authority",
    "note",
    "action",
)

SEGUE_TYPES = (
    "composition",
    "substantiates",
    "supports",
    "contradicts",
    "locates",
    "involves",
    "derived_from",
    "precedes",
    "follows",
    "mentions",
    "created_by",
    "sent_to",
    "used_in",
    "depends_on",
    "depicts",
    "transcribes",
    "governed_by",
    "relates_to",
)

STATUS_PRESENTATION = {
    "corroborated": "gold",
    "reported": "pink",
    "inferred": "pink",
    "disputed": "gray",
    "unknown": "gray",
}


class NexusContractError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalize_id(value: Any, field_name: str = "id") -> str:
    text = str(value if value is not None else "").strip()

    if not text:
        raise NexusContractError(
            f"{field_name} is required"
        )

    if text != text.lower():
        raise NexusContractError(
            f"{field_name} must be lowercase: {text}"
        )

    return text


def unique_strings(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    result: list[str] = []

    for raw in values:
        value = str(raw).strip()

        if not value:
            continue

        if value not in result:
            result.append(value)

    return tuple(result)


def mapping_copy(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if value is None:
        return {}

    return dict(value)


@dataclass(frozen=True, slots=True)
class AuthorityState:
    state: str = "none"
    source: str | None = None
    effect: str = "none"

    def __post_init__(self) -> None:
        if self.state not in AUTHORITY_STATES:
            raise NexusContractError(
                f"unsupported authority state: {self.state}"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "source": self.source,
            "effect": self.effect,
        }


@dataclass(frozen=True, slots=True)
class NexusSegue:
    id: str
    type: str
    source: str
    target: str
    authority: AuthorityState = field(
        default_factory=AuthorityState
    )
    provenance: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )
    extensions: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalize_id(self.id),
        )
        object.__setattr__(
            self,
            "source",
            normalize_id(self.source, "source"),
        )
        object.__setattr__(
            self,
            "target",
            normalize_id(self.target, "target"),
        )

        if self.type not in SEGUE_TYPES:
            raise NexusContractError(
                f"unsupported nexus segue type: {self.type}"
            )

        if self.source == self.target:
            raise NexusContractError(
                "nexus segue cannot self-reference"
            )

        object.__setattr__(
            self,
            "provenance",
            unique_strings(self.provenance),
        )
        object.__setattr__(
            self,
            "metadata",
            mapping_copy(self.metadata),
        )
        object.__setattr__(
            self,
            "extensions",
            mapping_copy(self.extensions),
        )

    @classmethod
    def create(
        cls,
        *,
        type: str,
        source: str,
        target: str,
        authority: AuthorityState | None = None,
        provenance: Iterable[str] = (),
        metadata: Mapping[str, Any] | None = None,
        extensions: Mapping[str, Any] | None = None,
    ) -> "NexusSegue":
        source_id = normalize_id(source, "source")
        target_id = normalize_id(target, "target")

        material = {
            "type": type,
            "source": source_id,
            "target": target_id,
        }

        return cls(
            id=(
                "nexus.segue."
                + digest(material)[:24]
            ),
            type=type,
            source=source_id,
            target=target_id,
            authority=(
                authority
                if authority is not None
                else AuthorityState()
            ),
            provenance=unique_strings(provenance),
            metadata=mapping_copy(metadata),
            extensions=mapping_copy(extensions),
        )

    def projection(self) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://nexus/segue/"
                + SCHEMA_VERSION
            ),
            "id": self.id,
            "kind": "segue",
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "authority": self.authority.projection(),
            "provenance": list(self.provenance),
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
            "authoritative": False,
            "authority_effect": "none",
        }

        payload["digest"] = digest(payload)

        return payload


@dataclass(frozen=True, slots=True)
class NexusInstance:
    id: str
    kind: str
    type: str
    title: str = ""
    status: str = "active"
    authority: AuthorityState = field(
        default_factory=AuthorityState
    )
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    relationships: tuple[str, ...] = ()
    segues: tuple[str, ...] = ()
    projections: tuple[str, ...] = ()
    extensions: Mapping[str, Any] = field(
        default_factory=dict
    )
    future_extensions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalize_id(self.id),
        )

        if self.kind not in INSTANCE_KINDS:
            raise NexusContractError(
                f"unsupported nexus instance kind: {self.kind}"
            )

        if not self.type.strip():
            raise NexusContractError(
                "instance type is required"
            )

        object.__setattr__(
            self,
            "lineage",
            unique_strings(self.lineage),
        )
        object.__setattr__(
            self,
            "provenance",
            unique_strings(self.provenance),
        )
        object.__setattr__(
            self,
            "dependencies",
            unique_strings(self.dependencies),
        )
        object.__setattr__(
            self,
            "relationships",
            unique_strings(self.relationships),
        )
        object.__setattr__(
            self,
            "segues",
            unique_strings(self.segues),
        )
        object.__setattr__(
            self,
            "projections",
            unique_strings(self.projections),
        )
        object.__setattr__(
            self,
            "future_extensions",
            unique_strings(
                self.future_extensions
            ),
        )
        object.__setattr__(
            self,
            "extensions",
            mapping_copy(self.extensions),
        )
        object.__setattr__(
            self,
            "metadata",
            mapping_copy(self.metadata),
        )

    def projection(self) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://nexus/instance/"
                + SCHEMA_VERSION
            ),
            "id": self.id,
            "kind": self.kind,
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "authority": self.authority.projection(),
            "lineage": list(self.lineage),
            "provenance": list(self.provenance),
            "dependencies": list(self.dependencies),
            "relationships": list(self.relationships),
            "segues": list(self.segues),
            "projections": list(self.projections),
            "extensions": dict(self.extensions),
            "future_extensions": list(
                self.future_extensions
            ),
            "metadata": dict(self.metadata),
            "authoritative": False,
            "authority_effect": "none",
            "owner": "application:nexus",
        }

        payload["digest"] = digest(payload)

        return payload


@dataclass(frozen=True, slots=True)
class SourceInstance:
    instance: NexusInstance
    source_kind: str
    original_name: str | None = None
    original_location: str | None = None
    source_digest: str | None = None
    mime_type: str | None = None
    source_time: str | None = None
    ingestion_time: str | None = None
    custodian: str | None = None
    provider: str | None = None
    original_content_reference: str | None = None
    transformations: tuple[str, ...] = ()
    attachments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.instance.kind != "source":
            raise NexusContractError(
                "source wrapper requires source instance"
            )

        if not self.source_kind.strip():
            raise NexusContractError(
                "source_kind is required"
            )

        object.__setattr__(
            self,
            "transformations",
            unique_strings(self.transformations),
        )
        object.__setattr__(
            self,
            "attachments",
            unique_strings(self.attachments),
        )

    def projection(self) -> dict[str, Any]:
        payload = self.instance.projection()
        payload["source"] = {
            "source_kind": self.source_kind,
            "original_name": self.original_name,
            "original_location": self.original_location,
            "source_digest": self.source_digest,
            "mime_type": self.mime_type,
            "source_time": self.source_time,
            "ingestion_time": self.ingestion_time,
            "custodian": self.custodian,
            "provider": self.provider,
            "original_content_reference": (
                self.original_content_reference
            ),
            "transformations": list(
                self.transformations
            ),
            "attachments": list(self.attachments),
        }
        payload["digest"] = digest(
            {
                key: value
                for key, value in payload.items()
                if key != "digest"
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class AssertionInstance:
    instance: NexusInstance
    proposition: str
    evidentiary_state: str
    confidence: float | None = None
    source_ids: tuple[str, ...] = ()
    source_ranges: tuple[str, ...] = ()
    asserted_by: tuple[str, ...] = ()
    asserted_at: str | None = None

    def __post_init__(self) -> None:
        if self.instance.kind != "assertion":
            raise NexusContractError(
                "assertion wrapper requires assertion instance"
            )

        if not self.proposition.strip():
            raise NexusContractError(
                "assertion proposition is required"
            )

        if (
            self.evidentiary_state
            not in EVIDENTIARY_STATES
        ):
            raise NexusContractError(
                "unsupported evidentiary state: "
                + self.evidentiary_state
            )

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise NexusContractError(
                    "confidence must be between 0 and 1"
                )

        object.__setattr__(
            self,
            "source_ids",
            unique_strings(self.source_ids),
        )
        object.__setattr__(
            self,
            "source_ranges",
            unique_strings(self.source_ranges),
        )
        object.__setattr__(
            self,
            "asserted_by",
            unique_strings(self.asserted_by),
        )

    @property
    def presentation_state(self) -> str:
        return STATUS_PRESENTATION[
            self.evidentiary_state
        ]

    def projection(self) -> dict[str, Any]:
        payload = self.instance.projection()

        payload["assertion"] = {
            "proposition": self.proposition,
            "evidentiary_state": (
                self.evidentiary_state
            ),
            "presentation_state": (
                self.presentation_state
            ),
            "confidence": self.confidence,
            "source_ids": list(self.source_ids),
            "source_ranges": list(
                self.source_ranges
            ),
            "asserted_by": list(self.asserted_by),
            "asserted_at": self.asserted_at,
        }

        payload["digest"] = digest(
            {
                key: value
                for key, value in payload.items()
                if key != "digest"
            }
        )

        return payload
