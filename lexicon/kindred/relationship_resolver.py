#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


RELATIONSHIP_AUTHORITY = (
    ROOT
    / "canon-system"
    / "authority"
    / "constitution"
    / "relationships.json"
)


class KindredRelationshipResolutionError(ValueError):
    pass


class KindredRelationshipResolver:
    """
    Kindred compatibility adapter over constitutional relationship
    authority.

    Authority remains:
        canon-system/authority/constitution/relationships.json

    This adapter:
    - does not create relationship authority;
    - does not modify constitutional definitions;
    - does not persist projections;
    - accepts Kindred's `relation:*` spelling as a compatibility alias;
    - resolves canonical semantics from constitutional authority first;
    - permits discipline-local extension relations only as explicitly
      non-authoritative projected vocabulary.
    """

    def __init__(
        self,
        authority_path: Path | str = RELATIONSHIP_AUTHORITY,
        discipline_registry: Path | str | None = None,
    ) -> None:
        self.authority_path = Path(
            authority_path
        ).resolve()

        self.discipline_registry = (
            Path(discipline_registry).resolve()
            if discipline_registry
            else (
                ROOT
                / "lexicon"
                / "kindred"
                / "discipline_registry.yaml"
            )
        )

        self._constitutional = (
            self._load_constitutional()
        )

        self._extensions = (
            self._load_extensions()
        )

    def _load_constitutional(
        self,
    ) -> dict[str, Mapping[str, Any]]:
        if not self.authority_path.exists():
            raise KindredRelationshipResolutionError(
                "constitutional relationship authority "
                f"not found: {self.authority_path}"
            )

        with self.authority_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            payload = json.load(handle)

        relationships = payload.get(
            "relationships"
        )

        if not isinstance(
            relationships,
            list,
        ):
            raise KindredRelationshipResolutionError(
                "relationships.json must contain "
                "a relationships list"
            )

        result: dict[
            str,
            Mapping[str, Any],
        ] = {}

        for definition in relationships:
            if not isinstance(
                definition,
                Mapping,
            ):
                raise KindredRelationshipResolutionError(
                    "relationship definition must be an object"
                )

            relationship_id = str(
                definition.get(
                    "id",
                    "",
                )
            ).strip()

            if not relationship_id:
                raise KindredRelationshipResolutionError(
                    "relationship id is required"
                )

            if relationship_id in result:
                raise KindredRelationshipResolutionError(
                    "duplicate constitutional relationship: "
                    f"{relationship_id}"
                )

            result[relationship_id] = (
                MappingProxyType(
                    dict(definition)
                )
            )

        return result

    def _load_extensions(
        self,
    ) -> dict[str, Mapping[str, Any]]:
        if not self.discipline_registry.exists():
            return {}

        try:
            import yaml
        except ImportError as exc:
            raise KindredRelationshipResolutionError(
                "PyYAML is required by the existing "
                "Kindred registry surface"
            ) from exc

        with self.discipline_registry.open(
            "r",
            encoding="utf-8",
        ) as handle:
            payload = yaml.safe_load(handle)

        if not isinstance(
            payload,
            Mapping,
        ):
            return {}

        relations = payload.get(
            "relations",
            {},
        )

        if not isinstance(
            relations,
            Mapping,
        ):
            return {}

        return {
            str(key): MappingProxyType(
                dict(value)
            )
            for key, value in relations.items()
            if isinstance(
                value,
                Mapping,
            )
        }

    @staticmethod
    def constitutional_id(
        relationship_id: str,
    ) -> str:
        value = str(
            relationship_id
        ).strip()

        if value.startswith(
            "relation:"
        ):
            return (
                "relationship:"
                + value.split(
                    ":",
                    1,
                )[1]
            )

        return value

    @staticmethod
    def kindred_id(
        relationship_id: str,
    ) -> str:
        value = str(
            relationship_id
        ).strip()

        if value.startswith(
            "relationship:"
        ):
            return (
                "relation:"
                + value.split(
                    ":",
                    1,
                )[1]
            )

        return value

    def constitutional(
        self,
        relationship_id: str,
    ) -> Mapping[str, Any] | None:
        return self._constitutional.get(
            self.constitutional_id(
                relationship_id
            )
        )

    def extension(
        self,
        relationship_id: str,
    ) -> Mapping[str, Any] | None:
        return self._extensions.get(
            self.kindred_id(
                relationship_id
            )
        )

    def exists(
        self,
        relationship_id: str,
    ) -> bool:
        return bool(
            self.constitutional(
                relationship_id
            )
            or self.extension(
                relationship_id
            )
        )

    def resolve(
        self,
        relationship_id: str,
    ) -> dict[str, Any]:
        canonical = self.constitutional(
            relationship_id
        )

        kindred_id = self.kindred_id(
            relationship_id
        )

        extension = self.extension(
            relationship_id
        )

        if canonical is not None:
            return {
                "requested_id": (
                    relationship_id
                ),
                "kindred_id": (
                    kindred_id
                ),
                "constitutional_id": (
                    canonical["id"]
                ),
                "authority": (
                    "constitutional"
                ),
                "authoritative": True,
                "definition": dict(
                    canonical
                ),
                "discipline_extension": (
                    dict(extension)
                    if extension
                    else None
                ),
            }

        if extension is not None:
            return {
                "requested_id": (
                    relationship_id
                ),
                "kindred_id": (
                    kindred_id
                ),
                "constitutional_id": None,
                "authority": (
                    "kindred-projection"
                ),
                "authoritative": False,
                "definition": dict(
                    extension
                ),
                "discipline_extension": (
                    dict(extension)
                ),
            }

        raise KindredRelationshipResolutionError(
            "unknown relationship: "
            f"{relationship_id}"
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        constitutional_ids = sorted(
            self._constitutional
        )

        extension_ids = sorted(
            self._extensions
        )

        matched: list[str] = []
        projected_only: list[str] = []

        for kindred_id in extension_ids:
            if self.constitutional(
                kindred_id
            ):
                matched.append(
                    kindred_id
                )
            else:
                projected_only.append(
                    kindred_id
                )

        return {
            "schema": (
                "savant.kindred."
                "relationship-resolution.v1"
            ),
            "authority_effect": "none",
            "constitutional_source": str(
                self.authority_path
            ),
            "constitutional_count": len(
                constitutional_ids
            ),
            "discipline_relation_count": len(
                extension_ids
            ),
            "constitutionally_resolved": (
                matched
            ),
            "projected_extensions": (
                projected_only
            ),
        }
