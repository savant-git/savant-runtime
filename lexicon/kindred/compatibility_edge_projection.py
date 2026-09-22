#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from lexicon.kindred.relationship_resolver import (
    KindredRelationshipResolutionError,
    KindredRelationshipResolver,
)


schema = "savant.kindred.compatibility-edge-projection.v1"
authority_effect = "none"
owner = "kindred"


class KindredCompatibilityProjectionError(
    ValueError
):
    pass


def _stable_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _stable_id(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    digest = hashlib.sha256(
        _stable_json(
            dict(payload)
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        f"{prefix}:"
        f"{digest[:24]}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class KindredCompatibilityEdge:
    subject: str
    relation: str
    object: str
    basis: str
    authority_state: str = "projected"
    valid_from: str | None = None
    valid_until: str | None = None
    provenance: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] | None = None
    id: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        payload = {
            "subject":
                self.subject,
            "relation":
                self.relation,
            "object":
                self.object,
            "basis":
                self.basis,
            "authority_state":
                self.authority_state,
            "valid_from":
                self.valid_from,
            "valid_until":
                self.valid_until,
            "provenance":
                dict(
                    self.provenance
                    or {}
                ),
            "metadata":
                dict(
                    self.metadata
                    or {}
                ),
        }

        payload["id"] = (
            self.id
            or _stable_id(
                "kindred-edge",
                {
                    "subject":
                        self.subject,
                    "relation":
                        self.relation,
                    "object":
                        self.object,
                    "basis":
                        self.basis,
                    "valid_from":
                        self.valid_from,
                    "valid_until":
                        self.valid_until,
                },
            )
        )

        return payload


class KindredCompatibilityEdgeProjector:
    """
    Non-authoritative compatibility projector.

    Relationship authority is resolved only through
    KindredRelationshipResolver.

    Legacy registry metadata may be surfaced by that resolver as a
    compatibility extension, but this projector does not treat that
    metadata as relationship authority.
    """

    def __init__(
        self,
        resolver: (
            KindredRelationshipResolver
            | None
        ) = None,
    ) -> None:
        self.relationships = (
            resolver
            or KindredRelationshipResolver()
        )

    def _resolution(
        self,
        relation_id: str,
    ) -> dict[str, Any]:
        try:
            return self.relationships.resolve(
                relation_id
            )

        except (
            KindredRelationshipResolutionError
        ) as exc:
            raise (
                KindredCompatibilityProjectionError(
                    str(
                        exc
                    )
                )
            ) from exc

    def _compatibility_definition(
        self,
        resolution: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        extension = resolution.get(
            "discipline_extension"
        )

        if isinstance(
            extension,
            Mapping,
        ):
            return dict(
                extension
            )

        definition = resolution.get(
            "definition"
        )

        if isinstance(
            definition,
            Mapping,
        ):
            return dict(
                definition
            )

        return {}

    def validate_edge(
        self,
        edge: KindredCompatibilityEdge,
    ) -> None:
        if not edge.subject.strip():
            raise (
                KindredCompatibilityProjectionError(
                    "edge subject is required"
                )
            )

        if not edge.object.strip():
            raise (
                KindredCompatibilityProjectionError(
                    "edge object is required"
                )
            )

        if not edge.relation.strip():
            raise (
                KindredCompatibilityProjectionError(
                    "edge relation is required"
                )
            )

        resolution = self._resolution(
            edge.relation
        )

        definition = (
            self._compatibility_definition(
                resolution
            )
        )

        if (
            edge.subject
            == edge.object
            and definition.get(
                "cycle_policy"
            )
            == "forbid"
        ):
            raise (
                KindredCompatibilityProjectionError(
                    "self-edge forbidden for "
                    f"{edge.relation}"
                )
            )

        if not edge.basis.strip():
            raise (
                KindredCompatibilityProjectionError(
                    "edge basis is required"
                )
            )

    def normalize_edge(
        self,
        edge: KindredCompatibilityEdge,
    ) -> dict[str, Any]:
        self.validate_edge(
            edge
        )

        payload = edge.to_dict()

        resolution = self._resolution(
            edge.relation
        )

        definition = (
            self._compatibility_definition(
                resolution
            )
        )

        payload[
            "discipline"
        ] = definition.get(
            "discipline"
        )

        payload[
            "steward"
        ] = definition.get(
            "steward"
        )

        payload[
            "directionality"
        ] = definition.get(
            "directionality",
            "directed",
        )

        payload[
            "inverse"
        ] = definition.get(
            "inverse"
        )

        payload[
            "derived"
        ] = False

        payload[
            "relationship_authority"
        ] = resolution[
            "authority"
        ]

        payload[
            "relationship_authoritative"
        ] = resolution[
            "authoritative"
        ]

        payload[
            "constitutional_relationship"
        ] = resolution[
            "constitutional_id"
        ]

        return payload

    def inverse_edge(
        self,
        edge: KindredCompatibilityEdge,
    ) -> dict[str, Any] | None:
        direct = self.normalize_edge(
            edge
        )

        resolution = self._resolution(
            edge.relation
        )

        definition = (
            self._compatibility_definition(
                resolution
            )
        )

        inverse = definition.get(
            "inverse"
        )

        if not inverse:
            return None

        if (
            definition.get(
                "directionality"
            )
            == "symmetric"
            and edge.subject
            == edge.object
        ):
            return None

        inverse_edge = (
            KindredCompatibilityEdge(
                subject=edge.object,
                relation=str(
                    inverse
                ),
                object=edge.subject,
                basis=(
                    "derived_inverse:"
                    f"{direct['id']}"
                ),
                authority_state=(
                    "projected"
                ),
                valid_from=(
                    edge.valid_from
                ),
                valid_until=(
                    edge.valid_until
                ),
                provenance={
                    "derived_from":
                        direct[
                            "id"
                        ],
                },
                metadata={
                    "projection":
                        "inverse",
                },
            )
        )

        payload = self.normalize_edge(
            inverse_edge
        )

        payload[
            "derived"
        ] = True

        payload[
            "derivation"
        ] = {
            "type":
                "inverse",
            "source_edge":
                direct[
                    "id"
                ],
        }

        return payload

    def project_edges(
        self,
        edges: Iterable[
            KindredCompatibilityEdge
        ],
        include_inverses: bool = True,
    ) -> list[
        dict[str, Any]
    ]:
        projected: dict[
            str,
            dict[str, Any],
        ] = {}

        for edge in edges:
            direct = self.normalize_edge(
                edge
            )

            projected[
                direct[
                    "id"
                ]
            ] = direct

            if include_inverses:
                inverse = (
                    self.inverse_edge(
                        edge
                    )
                )

                if inverse is not None:
                    projected.setdefault(
                        inverse[
                            "id"
                        ],
                        inverse,
                    )

        return [
            projected[
                key
            ]
            for key in sorted(
                projected
            )
        ]

    def manifest(
        self,
    ) -> dict[str, Any]:
        projection = (
            self.relationships.projection()
        )

        return {
            "schema":
                schema,
            "authority_effect":
                authority_effect,
            "owner":
                owner,
            "projection_only":
                True,
            "mutation_authority":
                False,
            "relationship_authority_created":
                False,
            "relationship_authority_source":
                projection[
                    "constitutional_source"
                ],
            "relationship_resolution":
                projection,
            "legacy_registry_authority":
                False,
            "legacy_registry_role":
                "compatibility-metadata-only",
        }


def self_check() -> dict[str, Any]:
    projector = (
        KindredCompatibilityEdgeProjector()
    )

    manifest = projector.manifest()

    if (
        manifest[
            "projection_only"
        ]
        is not True
    ):
        raise (
            KindredCompatibilityProjectionError(
                "compatibility projector "
                "is not projection-only"
            )
        )

    if (
        manifest[
            "mutation_authority"
        ]
        is not False
    ):
        raise (
            KindredCompatibilityProjectionError(
                "compatibility projector "
                "acquired mutation authority"
            )
        )

    if (
        manifest[
            "relationship_authority_created"
        ]
        is not False
    ):
        raise (
            KindredCompatibilityProjectionError(
                "compatibility projector "
                "created relationship authority"
            )
        )

    if (
        manifest[
            "legacy_registry_authority"
        ]
        is not False
    ):
        raise (
            KindredCompatibilityProjectionError(
                "legacy registry metadata "
                "became authoritative"
            )
        )

    return {
        **manifest,
        "status":
            "passed",
    }


def main() -> int:
    try:
        print(
            json.dumps(
                self_check(),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "authority_effect":
                        authority_effect,
                    "owner":
                        owner,
                    "status":
                        "failed",
                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
