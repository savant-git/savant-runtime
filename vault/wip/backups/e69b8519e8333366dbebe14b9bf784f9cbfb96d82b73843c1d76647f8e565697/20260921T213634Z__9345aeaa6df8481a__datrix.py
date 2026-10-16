#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any

from .dependency import (
    StraubDependencyIndex,
)
from .isotope import isotope
from .projection_refresh import (
    ContentionSafeIsotope,
)
from .query import StraubQuery
from .registry import StraubRegistry
from .resilience import (
    ResilientCapsulePersistence,
)


schema = "savant.carbon.straub.datrix.v5"
owner = "carbon"
module = "straub"
authority_effect = "none"


IMPLEMENTED_COMPONENTS = (
    "dyad",
    "umbra",
    "membrane",
    "isotope",
)

STRUCTURAL_COMPONENTS = (
    "dyad",
    "umbra",
    "membrane",
    "isotope",
)


class StraubDatrix:
    """
    A datrix created and operated by Carbon's Straub module.

    Isotopes are deterministic projections of canonical
    datrix substance.

    A datrix remembers the durable capsule digest from
    which its mutable in-memory registry was opened.

    Checkpointing uses that digest as an optimistic
    concurrency token. If another writer has checkpointed
    a different state first, the stale checkpoint is
    rejected rather than silently overwriting or merging
    the newer state.
    """

    exile = "carbon"
    module = "straub"
    kind = "datrix"

    def __init__(
        self,
        *,
        registry: StraubRegistry,
        persistence: ResilientCapsulePersistence,
        isotope: ContentionSafeIsotope,
        path: Path,
        loaded_digest: str | None,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._isotope = isotope

        self._path = Path(
            path
        ).resolve()

        self._loaded_digest = (
            loaded_digest
        )

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

        capsule = (
            persistence.load_capsule()
        )

        if capsule is None:
            registry = StraubRegistry()
            loaded_digest = None
        else:
            registry = (
                StraubRegistry.from_capsule(
                    capsule
                )
            )

            loaded_digest = str(
                capsule[
                    "digest"
                ]
            )

        isotope_surface = (
            ContentionSafeIsotope(
                capsule_path.with_name(
                    capsule_path.name
                    + ".isotope"
                )
            )
        )

        return cls(
            registry=registry,
            persistence=persistence,
            isotope=isotope_surface,
            path=capsule_path,
            loaded_digest=loaded_digest,
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

    @property
    def loaded_digest(
        self,
    ) -> str | None:
        return self._loaded_digest

    def capsule(
        self,
    ) -> dict[str, Any]:
        return (
            self._registry
            .export_capsule()
        )

    def project_isotope(
        self,
        *,
        projection: dict[str, Any],
        projection_type: str,
        source_ids: list[str] | None = None,
        dependencies: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        return isotope(
            source_ids=(
                source_ids
                or []
            ),
            projection=projection,
            projection_type=projection_type,
            source_capsule_digest=(
                capsule[
                    "digest"
                ]
            ),
            dependencies=dependencies,
            provenance=provenance,
        )

    def checkpoint(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        expected_previous_digest = (
            self._loaded_digest
        )

        saved_digest = (
            self._persistence
            .save_capsule_if_current(
                capsule,
                expected_previous_digest,
            )
        )

        self._loaded_digest = (
            saved_digest
        )

        refresh = (
            self._isotope.refresh(
                capsule
            )
        )

        materialized_projection = (
            refresh[
                "projection"
            ]
        )

        materialized_isotope = (
            self.project_isotope(
                projection=(
                    materialized_projection
                ),
                projection_type=(
                    "materialized-index"
                ),
                source_ids=[],
                dependencies=[],
                provenance={
                    "source":
                        "straub:"
                        "materialized-projection",
                    "projection_surface":
                        "isotope",
                },
            )
        )

        history = capsule[
            "history"
        ]

        return {
            "schema":
                "savant.carbon.straub."
                "datrix-checkpoint.v5",
            "kind":
                "datrix.checkpoint",
            "owner_exile":
                "carbon",
            "owner_module":
                "straub",
            "capsule_digest":
                saved_digest,
            "expected_previous_digest":
                expected_previous_digest,
            "history_head":
                history[
                    "head_digest"
                ],
            "history_event_count":
                history[
                    "event_count"
                ],
            "isotope_digest":
                materialized_isotope[
                    "digest"
                ],
            "isotope_id":
                materialized_isotope[
                    "id"
                ],
            "projection_primitive":
                "isotope",
            "materialized_projection_digest":
                materialized_projection[
                    "digest"
                ],
            "materialized_projection_action":
                refresh[
                    "action"
                ],
            "durable":
                True,
            "stale_writer_protection":
                True,
            "automatic_merge":
                False,
            "semantic_mutation":
                False,
            "authority_effect":
                "none",
        }

    def materialized_isotope(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        refresh = (
            self._isotope.refresh(
                capsule
            )
        )

        return self.project_isotope(
            projection=(
                refresh[
                    "projection"
                ]
            ),
            projection_type=(
                "materialized-index"
            ),
            provenance={
                "source":
                    "straub:"
                    "materialized-projection",
                "projection_surface":
                    "isotope",
            },
        )

    def refresh_isotope(
        self,
    ) -> dict[str, Any]:
        return self._isotope.refresh(
            self.capsule()
        )

    def rebuild_isotope(
        self,
    ) -> dict[str, Any]:
        return self.refresh_isotope()[
            "projection"
        ]

    def isotope_status(
        self,
    ) -> dict[str, Any]:
        capsule = self.capsule()

        status = (
            self._isotope.status(
                capsule_digest=(
                    capsule[
                        "digest"
                    ]
                )
            )
        )

        status[
            "projection_primitive"
        ] = "isotope"

        return status

    def query(
        self,
    ) -> StraubQuery:
        return StraubQuery(
            self.capsule()
        )

    def dependencies(
        self,
    ) -> StraubDependencyIndex:
        return (
            StraubDependencyIndex(
                self.capsule()
            )
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
                    StraubRegistry
                    .from_capsule(
                        capsule
                    )
                )

                self._loaded_digest = (
                    str(
                        capsule[
                            "digest"
                        ]
                    )
                )

        return repaired

    def reload(
        self,
    ) -> dict[str, Any]:
        capsule = (
            self._persistence
            .load_capsule()
        )

        if capsule is None:
            self._registry = (
                StraubRegistry()
            )

            self._loaded_digest = None

            return {
                "schema":
                    "savant.carbon.straub."
                    "datrix-reload.v1",
                "loaded":
                    False,
                "capsule_digest":
                    None,
                "authority_effect":
                    "none",
            }

        self._registry = (
            StraubRegistry.from_capsule(
                capsule
            )
        )

        self._loaded_digest = str(
            capsule[
                "digest"
            ]
        )

        return {
            "schema":
                "savant.carbon.straub."
                "datrix-reload.v1",
            "loaded":
                True,
            "capsule_digest":
                self._loaded_digest,
            "authority_effect":
                "none",
        }

    def component_status(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                "savant.carbon.straub."
                "datrix-components.v3",
            "implemented": [
                "dyad",
                "umbra",
                "membrane",
                "isotope",
            ],
            "structural_membership": [
                "dyad",
                "umbra",
                "membrane",
                "isotope",
            ],
            "projection_primitive":
                "isotope",
            "isotope_meaning":
                "deterministic projection",
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
            "loaded_capsule_digest":
                self._loaded_digest,
            "components":
                self.component_status(),
            "registry":
                self._registry.health(),
            "custody":
                self._persistence.health(),
            "isotope":
                self.isotope_status(),
            "stale_writer_protection":
                True,
            "compare_and_swap":
                True,
            "automatic_merge":
                False,
            "local_interprocess_coordination":
                True,
            "distributed_consensus":
                False,
            "query_default_time":
                None,
            "implicit_wall_clock":
                False,
            "semantic_authority":
                "canonical datrix substance",
            "projection_primitive":
                "isotope",
            "projection_semantics":
                "deterministic projection",
            "storage_engine_selected":
                False,
            "database_engine":
                None,
            "authority_effect":
                authority_effect,
        }
