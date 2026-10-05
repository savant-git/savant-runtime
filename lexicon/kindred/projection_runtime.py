#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any, Mapping

from relationship_projection import (
    project as project_relationships,
)
from semantic_runtime import (
    KindredSemanticRuntime,
)


schema = "savant.kindred.projection-runtime.v1"
authority_effect = "none"
owner = "kindred"


class KindredProjectionRuntimeError(
    RuntimeError
):
    pass


class KindredProjectionRuntime:
    """
    Read-only composition of canonical Kindred semantics with
    disposable relationship projections.

    Derived structures never become relationship authority.
    """

    def __init__(
        self,
    ) -> None:
        self.semantic = (
            KindredSemanticRuntime()
        )

    def project(
        self,
        substance: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        relationship_projection = (
            project_relationships(
                substance
            )
        )

        if relationship_projection.get(
            "projection_only"
        ) is not True:
            raise KindredProjectionRuntimeError(
                "relationship projection "
                "is not projection-only"
            )

        if relationship_projection.get(
            "mutation_authority"
        ) is not False:
            raise KindredProjectionRuntimeError(
                "relationship projection "
                "acquired mutation authority"
            )

        semantic_manifest = (
            self.semantic.manifest()
        )

        result = {
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
            "semantic_runtime":
                semantic_manifest,
            "relationship_projection":
                relationship_projection,
        }

        return result


def self_check() -> dict[str, Any]:
    runtime = KindredProjectionRuntime()

    sample = {
        "direct_relationships": [
            {
                "subject":
                    "instance:a",
                "relation":
                    "parent",
                "object":
                    "instance:b",
                "admitted":
                    True,
                "provenance": [
                    "evidence:1",
                ],
            },
            {
                "subject":
                    "instance:b",
                "relation":
                    "sibling",
                "object":
                    "instance:c",
                "admitted":
                    False,
                "provenance": [
                    "evidence:2",
                ],
            },
        ]
    }

    first = runtime.project(
        sample
    )

    second = runtime.project(
        sample
    )

    first_bytes = json.dumps(
        first,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode(
        "utf-8"
    )

    second_bytes = json.dumps(
        second,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode(
        "utf-8"
    )

    if first_bytes != second_bytes:
        raise KindredProjectionRuntimeError(
            "Kindred composed projection "
            "is not deterministic"
        )

    relationship_projection = first[
        "relationship_projection"
    ]

    if len(
        relationship_projection[
            "direct_relationships"
        ]
    ) != 1:
        raise KindredProjectionRuntimeError(
            "unadmitted relationship entered "
            "derived projection"
        )

    if first[
        "relationship_authority_created"
    ] is not False:
        raise KindredProjectionRuntimeError(
            "projection runtime manufactured "
            "relationship authority"
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
        "relationship_authority_created":
            False,
        "canonical_module_count":
            len(
                first[
                    "semantic_runtime"
                ][
                    "canonical_modules"
                ]
            ),
        "quarantined_modules":
            first[
                "semantic_runtime"
            ][
                "quarantined_modules"
            ],
        "admitted_relationship_count":
            len(
                relationship_projection[
                    "direct_relationships"
                ]
            ),
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
