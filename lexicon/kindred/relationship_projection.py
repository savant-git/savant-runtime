#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


schema = "savant.kindred.relationship-projection.v1"
authority_effect = "none"
owner = "kindred"

canonical_semantic_chain = (
    "direct_admitted_relationship",
    "reusable_role_profile_semantics",
    "purpose_specific_policy",
    "deterministic_family_algebra",
    "explainable_derived_relationship",
    "disposable_tree_graph_views",
)

canonical_modules = (
    "adoption_step_guardian",
    "alliance_affinity",
    "collateral_calculus",
    "descent_policy",
    "generational_calculus",
    "propagation_policy",
    "relationship_resolver",
    "role_calculus",
)

quarantined_modules = (
    "discipline_engine",
    "discipline_registry",
)


class KindredProjectionError(
    RuntimeError
):
    pass


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            value
        )
    ).hexdigest()


def stable_id(
    namespace: str,
    value: Any,
) -> str:
    return (
        namespace
        + ":"
        + digest(
            value
        )[:24]
    )


def normalize_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    return text


def normalize_string_list(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        candidates: Iterable[Any] = (
            value,
        )

    elif isinstance(
        value,
        Iterable,
    ):
        candidates = value

    else:
        candidates = (
            value,
        )

    normalized = {
        text
        for candidate in candidates
        if (
            text := normalize_text(
                candidate
            )
        )
    }

    return tuple(
        sorted(
            normalized
        )
    )


def require_mapping(
    value: Any,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise KindredProjectionError(
            f"{label} must be an object"
        )

    return value


@dataclass(
    frozen=True,
)
class DirectRelationship:
    subject: str
    relation: str
    object: str
    provenance: tuple[str, ...]
    admitted: bool

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "DirectRelationship":
        subject = normalize_text(
            value.get(
                "subject"
            )
        )

        relation = normalize_text(
            value.get(
                "relation"
            )
        )

        object_value = normalize_text(
            value.get(
                "object"
            )
        )

        if subject is None:
            raise KindredProjectionError(
                "direct relationship subject is required"
            )

        if relation is None:
            raise KindredProjectionError(
                "direct relationship relation is required"
            )

        if object_value is None:
            raise KindredProjectionError(
                "direct relationship object is required"
            )

        return cls(
            subject=subject,
            relation=relation,
            object=object_value,
            provenance=normalize_string_list(
                value.get(
                    "provenance"
                )
            ),
            admitted=(
                value.get(
                    "admitted"
                )
                is True
            ),
        )

    def primitive(
        self,
    ) -> dict[str, Any]:
        return {
            "subject":
                self.subject,
            "relation":
                self.relation,
            "object":
                self.object,
            "provenance":
                list(
                    self.provenance
                ),
            "admitted":
                self.admitted,
        }


def admitted_relationships(
    relationships: Iterable[
        DirectRelationship
    ],
) -> tuple[
    DirectRelationship,
    ...,
]:
    return tuple(
        sorted(
            (
                relationship
                for relationship
                in relationships
                if relationship.admitted
            ),
            key=lambda relationship: (
                relationship.subject,
                relationship.relation,
                relationship.object,
                relationship.provenance,
            ),
        )
    )


def role_profiles(
    relationships: Iterable[
        DirectRelationship
    ],
) -> list[
    dict[str, Any]
]:
    subjects: dict[
        str,
        dict[
            str,
            set[str],
        ],
    ] = {}

    for relationship in relationships:
        subject_roles = subjects.setdefault(
            relationship.subject,
            {},
        )

        targets = subject_roles.setdefault(
            relationship.relation,
            set(),
        )

        targets.add(
            relationship.object
        )

    projection = []

    for subject in sorted(
        subjects
    ):
        roles = {
            relation: sorted(
                targets
            )
            for relation, targets
            in sorted(
                subjects[
                    subject
                ].items()
            )
        }

        substance = {
            "subject":
                subject,
            "roles":
                roles,
        }

        projection.append(
            {
                "id":
                    stable_id(
                        "kindred-role-profile",
                        substance,
                    ),
                **substance,
            }
        )

    return projection


def adjacency(
    relationships: Iterable[
        DirectRelationship
    ],
) -> dict[
    str,
    tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]
]:
    graph: dict[
        str,
        set[
            tuple[
                str,
                str,
            ]
        ],
    ] = {}

    for relationship in relationships:
        graph.setdefault(
            relationship.subject,
            set(),
        ).add(
            (
                relationship.relation,
                relationship.object,
            )
        )

    return {
        subject: tuple(
            sorted(
                edges
            )
        )
        for subject, edges
        in sorted(
            graph.items()
        )
    }


def disposable_graph_view(
    relationships: Iterable[
        DirectRelationship
    ],
) -> dict[str, Any]:
    nodes: set[str] = set()

    edges = []

    for relationship in relationships:
        nodes.add(
            relationship.subject
        )

        nodes.add(
            relationship.object
        )

        substance = {
            "subject":
                relationship.subject,
            "relation":
                relationship.relation,
            "object":
                relationship.object,
        }

        edges.append(
            {
                "id":
                    stable_id(
                        "kindred-edge",
                        substance,
                    ),
                "source":
                    relationship.subject,
                "target":
                    relationship.object,
                "relation":
                    relationship.relation,
            }
        )

    return {
        "nodes": [
            {
                "id":
                    node,
            }
            for node in sorted(
                nodes
            )
        ],
        "edges": sorted(
            edges,
            key=lambda edge: (
                edge[
                    "source"
                ],
                edge[
                    "relation"
                ],
                edge[
                    "target"
                ],
            ),
        ),
    }


def project(
    substance: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    direct_raw = substance.get(
        "direct_relationships",
        (),
    )

    if direct_raw is None:
        direct_raw = ()

    if not isinstance(
        direct_raw,
        (
            list,
            tuple,
        ),
    ):
        raise KindredProjectionError(
            "direct_relationships must be an array"
        )

    relationships = tuple(
        DirectRelationship.from_mapping(
            require_mapping(
                item,
                "direct_relationship",
            )
        )
        for item in direct_raw
    )

    admitted = admitted_relationships(
        relationships
    )

    primitives = [
        relationship.primitive()
        for relationship in admitted
    ]

    profiles = role_profiles(
        admitted
    )

    graph = disposable_graph_view(
        admitted
    )

    projection_substance = {
        "direct_relationships":
            primitives,
        "role_profiles":
            profiles,
        "adjacency":
            {
                subject: [
                    {
                        "relation":
                            relation,
                        "object":
                            object_value,
                    }
                    for relation, object_value
                    in edges
                ]
                for subject, edges
                in adjacency(
                    admitted
                ).items()
            },
        "graph":
            graph,
    }

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
        "semantic_chain":
            list(
                canonical_semantic_chain
            ),
        "canonical_modules":
            list(
                canonical_modules
            ),
        "quarantined_modules":
            list(
                quarantined_modules
            ),
        "projection_digest":
            digest(
                projection_substance
            ),
        **projection_substance,
    }


def self_check() -> dict[str, Any]:
    sample = {
        "direct_relationships": [
            {
                "subject":
                    "a",
                "relation":
                    "parent",
                "object":
                    "b",
                "admitted":
                    True,
                "provenance": [
                    "source:1",
                ],
            },
            {
                "subject":
                    "b",
                "relation":
                    "sibling",
                "object":
                    "c",
                "admitted":
                    False,
                "provenance": [
                    "source:2",
                ],
            },
        ]
    }

    first = project(
        sample
    )

    second = project(
        sample
    )

    if canonical_bytes(
        first
    ) != canonical_bytes(
        second
    ):
        raise KindredProjectionError(
            "kindred relationship projection "
            "is not deterministic"
        )

    if first[
        "mutation_authority"
    ] is not False:
        raise KindredProjectionError(
            "kindred projection acquired "
            "mutation authority"
        )

    if len(
        first[
            "direct_relationships"
        ]
    ) != 1:
        raise KindredProjectionError(
            "unadmitted relationship escaped "
            "into projection"
        )

    return {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "status":
            "passed",
        "projection_only":
            True,
        "mutation_authority":
            False,
        "semantic_chain":
            list(
                canonical_semantic_chain
            ),
        "canonical_modules":
            list(
                canonical_modules
            ),
        "quarantined_modules":
            list(
                quarantined_modules
            ),
        "sample_projection_digest":
            first[
                "projection_digest"
            ],
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
