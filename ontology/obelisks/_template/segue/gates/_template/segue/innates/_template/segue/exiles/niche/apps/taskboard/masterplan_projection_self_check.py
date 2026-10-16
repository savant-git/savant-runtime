#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from masterplan_index_projection import (
    index_projection,
)
from masterplan_lineage_projection import (
    lineage_projection,
)
from masterplan_projection import (
    masterplan_projection,
    summary_projection,
)


schema_version = (
    "savant.niche."
    "masterplan-projection-self-check.v1"
)

authority_effect = "none"

owner = "exile:niche"


class MasterplanProjectionSelfCheckError(
    RuntimeError
):
    pass


def canonical_digest(
    value: Any,
) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def require_mapping(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        dict,
    ):
        raise (
            MasterplanProjectionSelfCheckError(
                f"{name} must be an object"
            )
        )

    return value


def require_equal(
    left: Any,
    right: Any,
    name: str,
) -> None:
    if left != right:
        raise (
            MasterplanProjectionSelfCheckError(
                f"{name} mismatch"
            )
        )


def require_false(
    value: Any,
    name: str,
) -> None:
    if value is not False:
        raise (
            MasterplanProjectionSelfCheckError(
                f"{name} must be false"
            )
        )


def projection_snapshot() -> dict[
    str,
    Any,
]:
    full = require_mapping(
        masterplan_projection(),
        "masterplan projection",
    )

    summary = require_mapping(
        summary_projection(),
        "summary projection",
    )

    index = require_mapping(
        index_projection(),
        "index projection",
    )

    lineage = require_mapping(
        lineage_projection(),
        "lineage projection",
    )

    graph_digest = full.get(
        "graph_digest"
    )

    require_equal(
        summary.get(
            "graph_digest"
        ),
        graph_digest,
        "summary graph digest",
    )

    require_equal(
        index.get(
            "source_graph_digest"
        ),
        graph_digest,
        "index graph digest",
    )

    require_equal(
        lineage.get(
            "source_graph_digest"
        ),
        graph_digest,
        "lineage graph digest",
    )

    require_false(
        full.get(
            "mutation_authority"
        ),
        "masterplan mutation authority",
    )

    require_false(
        summary.get(
            "mutation_authority"
        ),
        "summary mutation authority",
    )

    require_false(
        index.get(
            "mutation_authority"
        ),
        "index mutation authority",
    )

    require_false(
        lineage.get(
            "mutation_authority"
        ),
        "lineage mutation authority",
    )

    identity_index = full.get(
        "identity_index"
    )

    if not isinstance(
        identity_index,
        list,
    ):
        raise (
            MasterplanProjectionSelfCheckError(
                "masterplan identity index "
                "must be an array"
            )
        )

    index_identity_index = index.get(
        "identity_index"
    )

    require_equal(
        index_identity_index,
        identity_index,
        "identity index projection",
    )

    lineage_records = lineage.get(
        "lineage"
    )

    if not isinstance(
        lineage_records,
        list,
    ):
        raise (
            MasterplanProjectionSelfCheckError(
                "lineage projection must "
                "contain a lineage array"
            )
        )

    require_equal(
        index.get(
            "identity_count"
        ),
        len(
            identity_index
        ),
        "identity count",
    )

    require_equal(
        lineage.get(
            "lineage_count"
        ),
        len(
            lineage_records
        ),
        "lineage count",
    )

    duplicate_identities = full.get(
        "duplicate_identities"
    )

    if not isinstance(
        duplicate_identities,
        list,
    ):
        raise (
            MasterplanProjectionSelfCheckError(
                "duplicate identities must "
                "be an array"
            )
        )

    require_equal(
        index.get(
            "duplicate_identities"
        ),
        duplicate_identities,
        "duplicate identity projection",
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
        "source_graph_digest":
            graph_digest,
        "source_projection_digest":
            full.get(
                "projection_digest"
            ),
        "identity_count":
            len(
                identity_index
            ),
        "lineage_count":
            len(
                lineage_records
            ),
        "duplicate_identity_group_count":
            len(
                duplicate_identities
            ),
        "component_digests": {
            "masterplan":
                canonical_digest(
                    full
                ),
            "summary":
                canonical_digest(
                    summary
                ),
            "index":
                canonical_digest(
                    index
                ),
            "lineage":
                canonical_digest(
                    lineage
                ),
        },
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
    first = projection_snapshot()
    second = projection_snapshot()

    require_equal(
        first,
        second,
        "projection snapshot determinism",
    )

    require_false(
        first.get(
            "mutation_authority"
        ),
        "aggregate mutation authority",
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
        "cross_projection_consistency":
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
        "lineage_count":
            first[
                "lineage_count"
            ],
        "duplicate_identity_group_count":
            first[
                "duplicate_identity_group_count"
            ],
        "component_digests":
            first[
                "component_digests"
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
                projection_snapshot()
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
