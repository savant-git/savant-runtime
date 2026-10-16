#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any

from .dependency import (
    StraubDependencyIndex,
)
from .projection_refresh import (
    ContentionSafeRadia,
)
from .query import StraubQuery
from .registry import StraubRegistry
from .resilience import (
    ResilientCapsulePersistence,
)


schema = "savant.carbon.straub.datrix.v3"
owner = "carbon"
module = "straub"
authority_effect = "none"


IMPLEMENTED_COMPONENTS = (
    "dyad",
    "umbra",
    "membrane",
    "radia",
)

STRUCTURAL_COMPONENTS = (
    "dyad",
    "umbra",
    "membrane",
    "radia",
    "isotopes",
)


class StraubDatrix:
    """
    A datrix created and operated by Carbon's Straub module.

    Straub is the module.
    This object is the datrix.

    Canonical substance, recursive metadata, typed relations,
    temporal semantics, lineage, replay, and representations
    belong to the datrix.

    Radia is a datrix component for deterministic derived
    projection.

    Isotopes are established as datrix components by current
    authority, but their behavioral contract remains pending
    and is not fabricated here.

    Durable custody and materialized radia remain operational
    mechanisms rather than competing semantic authority.
    """

    exile = "carbon"
    module = "straub"
    kind = "datrix"

    def __init__(
        self,
        *,
        registry: StraubRegistry,
        persistence: ResilientCapsulePersistence,
        radia: ContentionSafeRadia,
        path: Path,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._radia = radia
        self._path = Path(
            path
        ).resolve()

    @classmethod
    def open(
        cls,
        path: str | Path,
    ) -> "StraubDatrix":
        capsule_path = Path(
            path
        ).resolve()

        persistence = (
            ResilientCapsulePersistence(
                capsule_path
            )
        )

        capsule = persistence.load_capsule()

        if capsule is None:
            registry = StraubRegistry()
        else:
            registry = (
                StraubRegistry.from_capsule(
                    capsule
                )
            )

        radia = ContentionSafeRadia(
            capsule_path.with_name(
                capsule_path.name
                + ".radia"
            )
        )

        return cls(
            registry=registry,
            persistence=persistence,
            radia=radia,
            path=capsule_path,
        )

    @property
    def registry(
        self,
    ) -> StraubRegistry:
        return self._registry

    @property
    def persistence(
        self,
    ) -> ResilientCapsulePersistence:
        return self._persistence

    @property
    def path(
        self,
    ) -> Path:
        return self._path

    def capsule(
        self,
    ) -> dict[str, Any]:
        return self._registry.export_capsule()

    def checkpoint(
        self,
    ) -> dict[str, Any]:
        checkpoint = (
            self._registry.checkpoint(
                self._persistence
            )
        )

        capsule = self.capsule()

        refresh = self._radia.refresh(
            capsule
        )

        projection = refresh[
            "projection"
        ]

        return {
            "schema":
                "savant.carbon.straub."
                "datrix-checkpoint.v3",
            "kind":
                "datrix.checkpoint",
            "owner_exile":
                "carbon",
            "owner_module":
                "straub",
            "capsule_digest":
                capsule[
                    "digest"
                ],
            "history_head":
                checkpoint[
                    "history_head"
                ],
            "history_event_count":
                checkpoint[
                    "event_count"
                ],
            "radia_digest":
                projection[
                    "digest"
                ],
            "radia_action":
                refresh[
                    "action"
                ],
            "durable":
                True,
            "projection_only_radia":
                True,
            "semantic_mutation":
                False,
            "authority_effect":
                "none",
        }

    def refresh_radia(
        self,
    ) -> dict[str, Any]:
        return self._radia.refresh(
            self.capsule()
        )

    def rebuild_radia(
        self,
    ) -> dict[str, Any]:
        return self.refresh_radia()[
            "projection"
        ]

    def radia_status(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        return self._radia.status(
            capsule_digest=(
                capsule[
                    "digest"
                ]
            )
        )

    def query(
        self,
    ) -> StraubQuery:
        return StraubQuery(
            self.capsule()
        )

    def dependencies(
        self,
    ) -> StraubDependencyIndex:
        return StraubDependencyIndex(
            self.capsule()
        )

    def recover_primary(
        self,
    ) -> bool:
        repaired = (
            self._persistence
            .repair_primary_from_backup()
        )

        if repaired:
            capsule = (
                self._persistence
                .load_capsule()
            )

            if capsule is not None:
                self._registry = (
                    StraubRegistry.from_capsule(
                        capsule
                    )
                )

        return repaired

    def component_status(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                "savant.carbon.straub."
                "datrix-components.v1",
            "implemented": [
                "dyad",
                "umbra",
                "membrane",
                "radia",
            ],
            "structural_membership": [
                "dyad",
                "umbra",
                "membrane",
                "radia",
                "isotopes",
            ],
            "pending_semantics": [
                "isotopes",
            ],
            "authority_effect":
                "none",
        }

    def health(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        return {
            "schema":
                schema,
            "status":
                "ok",
            "kind":
                "datrix",
            "created_by":
                "straub",
            "owner_module":
                "straub",
            "owner_exile":
                "carbon",
            "straub_is_datrix":
                False,
            "path":
                str(
                    self._path
                ),
            "capsule_digest":
                capsule[
                    "digest"
                ],
            "components":
                self.component_status(),
            "registry":
                self._registry.health(),
            "custody":
                self._persistence.health(),
            "radia":
                self.radia_status(),
            "query_default_time":
                None,
            "implicit_wall_clock":
                False,
            "semantic_authority":
                "canonical datrix substance",
            "storage_engine_selected":
                False,
            "database_engine":
                None,
            "projection_term":
                "radia",
            "authority_effect":
                authority_effect,
        }
