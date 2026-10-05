#!/usr/bin/env python3

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from .contracts import (
        AssertionInstance,
        AuthorityState,
        NexusContractError,
        NexusInstance,
        NexusSegue,
        SourceInstance,
        canonical_json,
        digest,
        normalize_id,
    )
except ImportError:
    from contracts import (
        AssertionInstance,
        AuthorityState,
        NexusContractError,
        NexusInstance,
        NexusSegue,
        SourceInstance,
        canonical_json,
        digest,
        normalize_id,
    )


class NexusModelError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NexusValidation:
    valid: bool
    errors: tuple[str, ...]
    instance_count: int
    segue_count: int

    def projection(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "instance_count": self.instance_count,
            "segue_count": self.segue_count,
        }


class NexusMatter:
    schema = "savant://nexus/matter-runtime/1.0.0"
    owner = "application:nexus"

    def __init__(
        self,
        *,
        matter_id: str,
        title: str,
        matter_type: str = "generic",
        provenance: Iterable[str] = (),
    ) -> None:
        self.matter_id = normalize_id(
            matter_id,
            "matter_id",
        )

        if not title.strip():
            raise NexusModelError(
                "matter title is required"
            )

        if not matter_type.strip():
            raise NexusModelError(
                "matter_type is required"
            )

        self.title = title
        self.matter_type = matter_type
        self.provenance = tuple(
            dict.fromkeys(
                str(value).strip()
                for value in provenance
                if str(value).strip()
            )
        )

        self._instances: dict[
            str,
            NexusInstance,
        ] = {}

        self._sources: dict[
            str,
            SourceInstance,
        ] = {}

        self._assertions: dict[
            str,
            AssertionInstance,
        ] = {}

        self._segues: dict[
            str,
            NexusSegue,
        ] = {}

        matter = NexusInstance(
            id=self.matter_id,
            kind="matter",
            type=self.matter_type,
            title=self.title,
            authority=AuthorityState(
                state="provisional",
                source="current-user-directive",
                effect="matter-identity",
            ),
            provenance=self.provenance,
            future_extensions=(
                "matter-adapters",
                "matter-views",
                "matter-ai-policies",
            ),
            metadata={
                "dataset_agnostic": True,
                "application": "nexus",
            },
        )

        self.add_instance(matter)

    @property
    def instances(self) -> tuple[NexusInstance, ...]:
        return tuple(
            self._instances[key]
            for key in sorted(self._instances)
        )

    @property
    def sources(self) -> tuple[SourceInstance, ...]:
        return tuple(
            self._sources[key]
            for key in sorted(self._sources)
        )

    @property
    def assertions(
        self,
    ) -> tuple[AssertionInstance, ...]:
        return tuple(
            self._assertions[key]
            for key in sorted(self._assertions)
        )

    @property
    def segues(self) -> tuple[NexusSegue, ...]:
        return tuple(
            self._segues[key]
            for key in sorted(self._segues)
        )

    def add_instance(
        self,
        instance: NexusInstance,
    ) -> NexusInstance:
        existing = self._instances.get(instance.id)

        if existing is not None:
            if existing == instance:
                return existing

            raise NexusModelError(
                "nexus instance identity conflict: "
                + instance.id
            )

        self._instances[instance.id] = instance
        return instance

    def add_source(
        self,
        source: SourceInstance,
    ) -> SourceInstance:
        self.add_instance(source.instance)

        existing = self._sources.get(
            source.instance.id
        )

        if existing is not None:
            if existing == source:
                return existing

            raise NexusModelError(
                "nexus source identity conflict: "
                + source.instance.id
            )

        self._sources[
            source.instance.id
        ] = source

        return source

    def add_assertion(
        self,
        assertion: AssertionInstance,
    ) -> AssertionInstance:
        self.add_instance(assertion.instance)

        for source_id in assertion.source_ids:
            if source_id not in self._sources:
                raise NexusModelError(
                    "assertion references unknown source: "
                    + source_id
                )

        existing = self._assertions.get(
            assertion.instance.id
        )

        if existing is not None:
            if existing == assertion:
                return existing

            raise NexusModelError(
                "nexus assertion identity conflict: "
                + assertion.instance.id
            )

        self._assertions[
            assertion.instance.id
        ] = assertion

        return assertion

    def add_segue(
        self,
        segue: NexusSegue,
    ) -> NexusSegue:
        if segue.source not in self._instances:
            raise NexusModelError(
                "segue source does not exist: "
                + segue.source
            )

        if segue.target not in self._instances:
            raise NexusModelError(
                "segue target does not exist: "
                + segue.target
            )

        existing = self._segues.get(segue.id)

        if existing is not None:
            if existing == segue:
                return existing

            raise NexusModelError(
                "nexus segue identity conflict: "
                + segue.id
            )

        self._segues[segue.id] = segue

        return segue

    def create_source(
        self,
        *,
        source_id: str,
        source_kind: str,
        title: str,
        original_name: str | None = None,
        original_location: str | None = None,
        source_digest: str | None = None,
        mime_type: str | None = None,
        source_time: str | None = None,
        ingestion_time: str | None = None,
        custodian: str | None = None,
        provider: str | None = None,
        original_content_reference: str | None = None,
        provenance: Iterable[str] = (),
    ) -> SourceInstance:
        instance = NexusInstance(
            id=source_id,
            kind="source",
            type=source_kind,
            title=title,
            authority=AuthorityState(
                state="unreviewed",
                source="source-ingestion",
                effect="provenance-only",
            ),
            lineage=(self.matter_id,),
            provenance=tuple(provenance),
            dependencies=(),
            relationships=(),
            segues=(),
            projections=(),
            future_extensions=(
                "authentication",
                "custody",
                "attachments",
                "normalization",
            ),
        )

        source = SourceInstance(
            instance=instance,
            source_kind=source_kind,
            original_name=original_name,
            original_location=original_location,
            source_digest=source_digest,
            mime_type=mime_type,
            source_time=source_time,
            ingestion_time=ingestion_time,
            custodian=custodian,
            provider=provider,
            original_content_reference=(
                original_content_reference
            ),
        )

        self.add_source(source)

        self.add_segue(
            NexusSegue.create(
                type="composition",
                source=self.matter_id,
                target=source.instance.id,
                authority=AuthorityState(
                    state="accepted",
                    source="matter-composition",
                    effect="composition",
                ),
                provenance=(
                    "application:nexus",
                    self.matter_id,
                ),
            )
        )

        return source

    def create_assertion(
        self,
        *,
        assertion_id: str,
        proposition: str,
        evidentiary_state: str,
        source_ids: Iterable[str] = (),
        source_ranges: Iterable[str] = (),
        asserted_by: Iterable[str] = (),
        asserted_at: str | None = None,
        confidence: float | None = None,
        provenance: Iterable[str] = (),
    ) -> AssertionInstance:
        source_ids = tuple(source_ids)

        instance = NexusInstance(
            id=assertion_id,
            kind="assertion",
            type="proposition",
            title=proposition[:160],
            authority=AuthorityState(
                state="unreviewed",
                source="nexus-assertion",
                effect="none",
            ),
            lineage=(self.matter_id,),
            provenance=tuple(provenance),
            dependencies=source_ids,
            future_extensions=(
                "corroboration",
                "authentication",
                "authority-review",
                "ai-analysis",
            ),
        )

        assertion = AssertionInstance(
            instance=instance,
            proposition=proposition,
            evidentiary_state=evidentiary_state,
            confidence=confidence,
            source_ids=source_ids,
            source_ranges=tuple(source_ranges),
            asserted_by=tuple(asserted_by),
            asserted_at=asserted_at,
        )

        self.add_assertion(assertion)

        self.add_segue(
            NexusSegue.create(
                type="composition",
                source=self.matter_id,
                target=assertion.instance.id,
                authority=AuthorityState(
                    state="accepted",
                    source="matter-composition",
                    effect="composition",
                ),
                provenance=(
                    "application:nexus",
                    self.matter_id,
                ),
            )
        )

        for source_id in source_ids:
            self.add_segue(
                NexusSegue.create(
                    type="substantiates",
                    source=source_id,
                    target=assertion.instance.id,
                    authority=AuthorityState(
                        state="unreviewed",
                        source="nexus-evidence-link",
                        effect="none",
                    ),
                    provenance=tuple(provenance),
                )
            )

        return assertion

    def create_record(
        self,
        *,
        record_id: str,
        kind: str,
        type: str,
        title: str,
        provenance: Iterable[str] = (),
        dependencies: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> NexusInstance:
        if kind in {
            "matter",
            "source",
            "assertion",
        }:
            raise NexusModelError(
                "use the specialized constructor for "
                + kind
            )

        instance = NexusInstance(
            id=record_id,
            kind=kind,
            type=type,
            title=title,
            authority=AuthorityState(
                state="unreviewed",
                source="nexus-record",
                effect="none",
            ),
            lineage=(self.matter_id,),
            provenance=tuple(provenance),
            dependencies=tuple(dependencies),
            future_extensions=(
                "annotations",
                "ai-analysis",
                "projection-metadata",
            ),
            metadata=(
                {}
                if metadata is None
                else metadata
            ),
        )

        self.add_instance(instance)

        self.add_segue(
            NexusSegue.create(
                type="composition",
                source=self.matter_id,
                target=instance.id,
                authority=AuthorityState(
                    state="accepted",
                    source="matter-composition",
                    effect="composition",
                ),
                provenance=(
                    "application:nexus",
                    self.matter_id,
                ),
            )
        )

        return instance

    def relate(
        self,
        *,
        type: str,
        source: str,
        target: str,
        provenance: Iterable[str] = (),
        authority: AuthorityState | None = None,
    ) -> NexusSegue:
        return self.add_segue(
            NexusSegue.create(
                type=type,
                source=source,
                target=target,
                provenance=tuple(provenance),
                authority=(
                    authority
                    if authority is not None
                    else AuthorityState()
                ),
            )
        )

    def validate(self) -> NexusValidation:
        errors: list[str] = []

        if self.matter_id not in self._instances:
            errors.append(
                "matter root instance missing"
            )

        for source in self.sources:
            if source.instance.kind != "source":
                errors.append(
                    "non-source in source registry: "
                    + source.instance.id
                )

        for assertion in self.assertions:
            if assertion.instance.kind != "assertion":
                errors.append(
                    "non-assertion in assertion registry: "
                    + assertion.instance.id
                )

            for source_id in assertion.source_ids:
                if source_id not in self._sources:
                    errors.append(
                        "assertion has missing source: "
                        + assertion.instance.id
                        + " -> "
                        + source_id
                    )

        for segue in self.segues:
            if segue.source not in self._instances:
                errors.append(
                    "segue source missing: "
                    + segue.id
                )

            if segue.target not in self._instances:
                errors.append(
                    "segue target missing: "
                    + segue.id
                )

        return NexusValidation(
            valid=not errors,
            errors=tuple(errors),
            instance_count=len(self._instances),
            segue_count=len(self._segues),
        )

    def projection(self) -> dict[str, Any]:
        validation = self.validate()

        payload = {
            "schema": self.schema,
            "owner": self.owner,
            "authoritative": False,
            "authority_effect": "none",
            "mutation_authorized": False,
            "rebuildable": True,
            "matter": {
                "id": self.matter_id,
                "title": self.title,
                "matter_type": self.matter_type,
            },
            "instances": [
                instance.projection()
                for instance in self.instances
                if instance.id not in self._sources
                and instance.id not in self._assertions
            ],
            "sources": [
                source.projection()
                for source in self.sources
            ],
            "assertions": [
                assertion.projection()
                for assertion in self.assertions
            ],
            "segues": [
                segue.projection()
                for segue in self.segues
            ],
            "validation": validation.projection(),
            "provenance": list(self.provenance),
        }

        payload["digest"] = digest(payload)

        return payload

    def to_json(self) -> str:
        return json.dumps(
            self.projection(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"
