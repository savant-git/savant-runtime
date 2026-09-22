#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from masterplan_projection import (
    masterplan_projection,
)
from projection_primitives import canonical_digest


schema_version = (
    "savant.niche."
    "masterplan-lineage-projection.v1"
)

authority_effect = "none"

owner = "exile:niche"


class MasterplanLineageProjectionError(
    RuntimeError
):
    pass


def lineage_projection() -> dict[
    str,
    Any,
]:
    source = masterplan_projection()

    identity_index = source.get(
        "identity_index"
    )

    if not isinstance(
        identity_index,
        list,
    ):
        raise (
            MasterplanLineageProjectionError(
                "masterplan identity index "
                "unavailable"
            )
        )

    lineage = []

    for item in identity_index:
        if not isinstance(
            item,
            dict,
        ):
            continue

        identity = item.get(
            "identity"
        )

        pointer = item.get(
            "pointer"
        )

        field = item.get(
            "field"
        )

        digest = item.get(
            "digest"
        )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in (
                identity,
                pointer,
                field,
                digest,
            )
        ):
            continue

        lineage.append(
            {
                "identity":
                    identity,
                "identity_field":
                    field,
                "source_pointer":
                    pointer,
                "substance_digest":
                    digest,
                "source_graph_digest":
                    source.get(
                        "graph_digest"
                    ),
            }
        )

    lineage.sort(
        key=lambda item: (
            item[
                "identity"
            ],
            item[
                "identity_field"
            ],
            item[
                "source_pointer"
            ],
            item[
                "substance_digest"
            ],
        )
    )

    projection = {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "projection":
            True,
        "mutation_authority":
            False,
        "source_schema":
            source.get(
                "schema"
            ),
        "source_graph_digest":
            source.get(
                "graph_digest"
            ),
        "source_projection_digest":
            source.get(
                "projection_digest"
            ),
        "lineage_count":
            len(
                lineage
            ),
        "lineage":
            lineage,
    }

    projection[
        "projection_digest"
    ] = canonical_digest(
        projection
    )

    return projection


def identity_lineage_projection(
    identity: str,
) -> dict[
    str,
    Any,
]:
    projection = lineage_projection()

    matches = [
        item
        for item
        in projection[
            "lineage"
        ]
        if item[
            "identity"
        ] == identity
    ]

    result = {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "projection":
            True,
        "mutation_authority":
            False,
        "identity":
            identity,
        "match_count":
            len(
                matches
            ),
        "matches":
            matches,
        "source_graph_digest":
            projection[
                "source_graph_digest"
            ],
    }

    result[
        "projection_digest"
    ] = canonical_digest(
        result
    )

    return result


def self_check() -> dict[
    str,
    Any,
]:
    first = lineage_projection()
    second = lineage_projection()

    if first != second:
        raise (
            MasterplanLineageProjectionError(
                "lineage projection is "
                "not deterministic"
            )
        )

    if (
        first.get(
            "mutation_authority"
        )
        is not False
    ):
        raise (
            MasterplanLineageProjectionError(
                "lineage projection acquired "
                "mutation authority"
            )
        )

    ordering = [
        (
            item[
                "identity"
            ],
            item[
                "identity_field"
            ],
            item[
                "source_pointer"
            ],
            item[
                "substance_digest"
            ],
        )
        for item
        in first[
            "lineage"
        ]
    ]

    if ordering != sorted(
        ordering
    ):
        raise (
            MasterplanLineageProjectionError(
                "lineage ordering is not "
                "deterministic"
            )
        )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "self_check":
            "passed",
        "determinism":
            "passed",
        "mutation_authority":
            False,
        "source_graph_digest":
            first[
                "source_graph_digest"
            ],
        "projection_digest":
            first[
                "projection_digest"
            ],
        "lineage_count":
            first[
                "lineage_count"
            ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=(
            "project",
            "identity",
            "self-check",
        ),
    )

    parser.add_argument(
        "value",
        nargs="?",
    )

    arguments = parser.parse_args()

    try:
        if arguments.command == "project":
            result = lineage_projection()

        elif arguments.command == "identity":
            if arguments.value is None:
                raise (
                    MasterplanLineageProjectionError(
                        "identity value required"
                    )
                )

            result = (
                identity_lineage_projection(
                    arguments.value
                )
            )

        else:
            result = self_check()

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "error":
                        str(
                            exc
                        ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
