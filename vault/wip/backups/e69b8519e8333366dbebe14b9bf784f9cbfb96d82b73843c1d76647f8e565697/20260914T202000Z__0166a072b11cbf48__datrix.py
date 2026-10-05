#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any

from .dependency import StraubDependencyIndex
from .materialized import (
    AtomicRadiaCache,
    StraubRadiaIndex,
)
from .query import StraubQuery
from .registry import StraubRegistry
from .resilience import (
    ResilientCapsulePersistence,
)


schema = "savant.straub.datrix.v1"
owner = "savant"
authority_effect = "none"


class StraubDatrix:
    """
    Straub's universal datrix lifecycle.

    The datrix composes canonical substance, metadata,
    lineage, relations, replay, dependency projection,
    durable custody, and rebuildable radia.

    It is not a database engine and does not create a
    second authority layer.
    """

    def __init__(
        self,
        *,
        registry: StraubRegistry,
        persistence: ResilientCapsulePersistence,
        radia_cache: AtomicRadiaCache,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._radia_cache = radia_cache

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

        radia_cache = AtomicRadiaCache(
            capsule_path.with_name(
                capsule_path.name
                + ".radia"
            )
        )

        return cls(
            registry=registry,
            persistence=persistence,
            radia_cache=radia_cache,
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
        checkpoint = self._registry.checkpoint(
            self._persistence
        )

        capsule = self.capsule()

        materialized = (
            StraubRadiaIndex(
                capsule
            ).materialize()
        )

        self._radia_cache.save(
            materialized
        )

        return {
            "schema":
                "savant.straub."
                "datrix-checkpoint.v1",
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
                materialized[
                    "digest"
                ],
            "durable":
                True,
            "projection_only_radia":
                True,
            "authority_effect":
                "none",
        }

    def rebuild_radia(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        projection = (
            self._radia_cache.rebuild(
                capsule
            )
        )

        return projection

    def radia_status(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        loaded = self._radia_cache.load(
            capsule_digest=(
                capsule[
                    "digest"
                ]
            )
        )

        if loaded is None:
            return {
                "schema":
                    "savant.straub."
                    "datrix-radia-status.v1",
                "present":
                    False,
                "fresh":
                    False,
                "rebuild_required":
                    True,
                "authority_effect":
                    "none",
            }

        return {
            "schema":
                "savant.straub."
                "datrix-radia-status.v1",
            "present":
                True,
            "fresh":
                loaded[
                    "status"
                ][
                    "fresh"
                ],
            "rebuild_required":
                loaded[
                    "status"
                ][
                    "rebuild_required"
                ],
            "projection_digest":
                loaded[
                    "projection"
                ][
                    "digest"
                ],
            "authority_effect":
                "none",
        }

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
            "definition":
                (
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
