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
    "masterplan-index-projection.v1"
)

authority_effect = "none"

owner = "exile:niche"


class MasterplanIndexProjectionError(
    RuntimeError
):
    pass


def index_projection() -> dict[
    str,
    Any,
]:
    source = (
        masterplan_projection()
    )

    identities = source.get(
        "identity_index"
    )

    duplicates = source.get(
        "duplicate_identities"
    )

    if not isinstance(
        identities,
        list,
    ):
        raise (
            MasterplanIndexProjectionError(
                "masterplan identity index "
                "unavailable"
            )
        )

    if not isinstance(
        duplicates,
        list,
    ):
        raise (
            MasterplanIndexProjectionError(
                "masterplan duplicate "
                "identity projection unavailable"
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
        "identity_count":
            len(
                identities
            ),
        "duplicate_identity_group_count":
            len(
                duplicates
            ),
        "identity_index":
            identities,
        "duplicate_identities":
            duplicates,
    }

    projection[
        "projection_digest"
    ] = canonical_digest(
        projection
    )

    return projection


def self_check() -> dict[
    str,
    Any,
]:
    first = index_projection()
    second = index_projection()

    if first != second:
        raise (
            MasterplanIndexProjectionError(
                "index projection is "
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
            MasterplanIndexProjectionError(
                "index projection acquired "
                "mutation authority"
            )
        )

    identities = first[
        "identity_index"
    ]

    ordering = [
        (
            str(
                item.get(
                    "identity",
                    "",
                )
            ),
            str(
                item.get(
                    "field",
                    "",
                )
            ),
            str(
                item.get(
                    "pointer",
                    "",
                )
            ),
        )
        for item in identities
        if isinstance(
            item,
            dict,
        )
    ]

    if ordering != sorted(
        ordering
    ):
        raise (
            MasterplanIndexProjectionError(
                "identity index order "
                "is not deterministic"
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
        "identity_count":
            first[
                "identity_count"
            ],
        "duplicate_identity_group_count":
            first[
                "duplicate_identity_group_count"
            ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=(
            "project",
            "self-check",
        ),
    )

    arguments = parser.parse_args()

    try:
        if (
            arguments.command
            == "project"
        ):
            result = (
                index_projection()
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
