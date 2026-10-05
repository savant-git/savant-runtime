#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from lexicon.kindred.constitutional_relationship_projection import (
    project as project_constitutional_relationships,
)
from lexicon.kindred.kindred_engine import (
    KindredEngine,
)
from lexicon.kindred.relationship_resolver import (
    KindredRelationshipResolver,
)


schema = "savant.kindred.runtime-contract.v1"
authority_effect = "none"
owner = "kindred"


class KindredRuntimeContractError(
    RuntimeError
):
    pass


def contract() -> dict[str, Any]:
    resolver = (
        KindredRelationshipResolver()
    )

    kindred_engine = (
        KindredEngine()
    )

    relationship_projection = (
        project_constitutional_relationships()
    )

    registry_graph = (
        kindred_engine.graph()
    )

    if (
        relationship_projection.get(
            "projection_only"
        )
        is not True
    ):
        raise KindredRuntimeContractError(
            "relationship projection must "
            "remain projection-only"
        )

    if (
        relationship_projection.get(
            "mutation_authority"
        )
        is not False
    ):
        raise KindredRuntimeContractError(
            "relationship projection acquired "
            "mutation authority"
        )

    lineage_authority = (
        registry_graph.get(
            "lineage_authority",
            {}
        )
    )

    if (
        lineage_authority.get(
            "primitive"
        )
        != "lineage_segue"
    ):
        raise KindredRuntimeContractError(
            "Kindred lineage primitive is no "
            "longer lineage_segue"
        )

    if (
        lineage_authority.get(
            "inverse_views"
        )
        != "projection"
    ):
        raise KindredRuntimeContractError(
            "Kindred inverse lineage views "
            "are no longer projections"
        )

    resolver_projection = (
        resolver.projection()
    )

    return {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "mutation_authority":
            False,
        "relationship_authority_created":
            False,
        "relationship_authority": {
            "owner":
                "constitutional-relationships",
            "source":
                resolver_projection[
                    "constitutional_source"
                ],
            "adapter":
                (
                    "lexicon.kindred."
                    "relationship_resolver."
                    "KindredRelationshipResolver"
                ),
            "kindred_aliases":
                "compatibility-projection",
            "kindred_only_extensions":
                "non-authoritative-projection",
        },
        "kindred_registry": {
            "source":
                str(
                    kindred_engine.registry_path
                ),
            "lineage_primitive":
                "lineage_segue",
            "inverse_lineage_views":
                "projection",
            "registry_id":
                registry_graph.get(
                    "registry_id"
                ),
            "version":
                registry_graph.get(
                    "version"
                ),
        },
        "boundaries": {
            "constitutional_relationship_definition":
                "constitutional-authority",
            "kindred_relationship_alias":
                "projection",
            "kindred_extension_relationship":
                "projection",
            "kindred_lineage_segue":
                "kindred-registry-primitive",
            "kindred_parent_child_inverse":
                "projection",
            "kindred_graph":
                "projection",
            "discipline_relationship_vocabulary":
                "non-authoritative-projection",
        },
        "relationship_projection":
            relationship_projection,
    }


def self_check() -> dict[str, Any]:
    first = contract()
    second = contract()

    first_encoded = json.dumps(
        first,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    second_encoded = json.dumps(
        second,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    if first_encoded != second_encoded:
        raise KindredRuntimeContractError(
            "Kindred runtime contract is "
            "not deterministic"
        )

    if (
        first[
            "relationship_authority_created"
        ]
        is not False
    ):
        raise KindredRuntimeContractError(
            "Kindred runtime contract created "
            "relationship authority"
        )

    if (
        first[
            "boundaries"
        ][
            "kindred_lineage_segue"
        ]
        != "kindred-registry-primitive"
    ):
        raise KindredRuntimeContractError(
            "Kindred lineage primitive "
            "boundary changed"
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
        "mutation_authority":
            False,
        "relationship_authority_created":
            False,
        "relationship_authority_source":
            first[
                "relationship_authority"
            ][
                "source"
            ],
        "kindred_registry_source":
            first[
                "kindred_registry"
            ][
                "source"
            ],
        "canonical_relationship_count":
            first[
                "relationship_projection"
            ][
                "canonical_relationship_count"
            ],
        "projected_extension_count":
            first[
                "relationship_projection"
            ][
                "projected_extension_count"
            ],
        "lineage_primitive":
            first[
                "kindred_registry"
            ][
                "lineage_primitive"
            ],
        "inverse_lineage_views":
            first[
                "kindred_registry"
            ][
                "inverse_lineage_views"
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
