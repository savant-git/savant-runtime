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


schema = "savant.straub.datrix.v2"
owner = "savant"
authority_effect = "none"


class StraubDatrix:
    """
    Straub's universal datrix lifecycle.

    Canonical substance and metadata remain in Straub's
    registry/capsule model. Durable custody and radia are
    operational mechanisms, never parallel semantic
    authority.
    """

    def __init__(
        self,
        *,
        registry: StraubRegistry,
        persistence: ResilientCapsulePersistence,
        radia: ContentionSafeRadia,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._radia = radia

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
                "savant.straub."
                "datrix-checkpoint.v2",
            "kind":
                "datrix.checkpoint",
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

    def health(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        return {
            "schema":
                schema,
            "name":
                "straub",
            "class":
                "datrix",
            "definition": (
                "universal deterministic "
                "metadata-native semantic "
                "data substrate"
            ),
            "status":
                "ok",
            "capsule_digest":
                capsule[
                    "digest"
                ],
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
                "canonical straub substance",
            "storage_engine_selected":
                False,
            "database_engine":
                None,
            "projection_term":
                "radia",
            "authority_effect":
                authority_effect,
        }
