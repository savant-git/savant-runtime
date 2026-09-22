#!/usr/bin/env python3

from __future__ import annotations

import hashlib
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

from lexicon.kindred.relationship_resolver import (
    KindredRelationshipResolver,
)


schema = "savant.kindred.constitutional-relationship-projection.v1"
authority_effect = "none"
owner = "kindred"

constitutional_source = (
    ROOT
    / "canon-system"
    / "authority"
    / "constitution"
    / "relationships.json"
)


class KindredConstitutionalProjectionError(
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


def project() -> dict[str, Any]:
    resolver = (
        KindredRelationshipResolver()
    )

    resolution = (
        resolver.projection()
    )

    if (
        Path(
            resolution[
                "constitutional_source"
            ]
        ).resolve()
        != constitutional_source.resolve()
    ):
        raise (
            KindredConstitutionalProjectionError(
                "Kindred resolver constitutional "
                "source does not match canonical "
                "relationship authority"
            )
        )

    constitutional_ids = sorted(
        resolver._constitutional
    )

    relationships = []

    for relationship_id in (
        constitutional_ids
    ):
        resolved = resolver.resolve(
            relationship_id
        )

        if (
            resolved.get(
                "authoritative"
            )
            is not True
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "constitutional relationship "
                    f"{relationship_id!r} did not "
                    "resolve as authoritative"
                )
            )

        if (
            resolved.get(
                "authority"
            )
            != "constitutional"
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "constitutional relationship "
                    f"{relationship_id!r} resolved "
                    "with incorrect authority"
                )
            )

        relationships.append(
            {
                "constitutional_id":
                    resolved[
                        "constitutional_id"
                    ],
                "kindred_id":
                    resolved[
                        "kindred_id"
                    ],
                "authority":
                    "constitutional",
                "authoritative":
                    True,
                "definition":
                    resolved[
                        "definition"
                    ],
            }
        )

    projected_extensions = []

    for relationship_id in sorted(
        resolution.get(
            "projected_extensions",
            []
        )
    ):
        resolved = resolver.resolve(
            relationship_id
        )

        if (
            resolved.get(
                "authoritative"
            )
            is not False
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "Kindred-only extension "
                    f"{relationship_id!r} acquired "
                    "relationship authority"
                )
            )

        if (
            resolved.get(
                "constitutional_id"
            )
            is not None
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "projected-only relationship "
                    f"{relationship_id!r} unexpectedly "
                    "resolved constitutionally"
                )
            )

        projected_extensions.append(
            {
                "kindred_id":
                    resolved[
                        "kindred_id"
                    ],
                "constitutional_id":
                    None,
                "authority":
                    "kindred-projection",
                "authoritative":
                    False,
                "definition":
                    resolved[
                        "definition"
                    ],
            }
        )

    matched_extensions = []

    for relationship_id in sorted(
        resolution.get(
            "constitutionally_resolved",
            []
        )
    ):
        resolved = resolver.resolve(
            relationship_id
        )

        if (
            resolved.get(
                "authoritative"
            )
            is not True
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "constitutionally matched "
                    "Kindred relation lost "
                    "constitutional authority"
                )
            )

        matched_extensions.append(
            {
                "kindred_id":
                    resolved[
                        "kindred_id"
                    ],
                "constitutional_id":
                    resolved[
                        "constitutional_id"
                    ],
                "authority":
                    "constitutional",
                "authoritative":
                    True,
                "discipline_extension":
                    resolved.get(
                        "discipline_extension"
                    ),
            }
        )

    substance = {
        "constitutional_relationships":
            relationships,
        "constitutionally_resolved_extensions":
            matched_extensions,
        "projected_extensions":
            projected_extensions,
    }

    return {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "constitutional_source":
            str(
                constitutional_source
            ),
        "authority_owner":
            "constitutional-relationships",
        "projection_only":
            True,
        "mutation_authority":
            False,
        "creates_relationship_authority":
            False,
        "canonical_relationship_count":
            len(
                relationships
            ),
        "constitutionally_resolved_extension_count":
            len(
                matched_extensions
            ),
        "projected_extension_count":
            len(
                projected_extensions
            ),
        "projection_digest":
            digest(
                substance
            ),
        **substance,
    }


def self_check() -> dict[str, Any]:
    first = project()
    second = project()

    if (
        canonical_bytes(
            first
        )
        != canonical_bytes(
            second
        )
    ):
        raise (
            KindredConstitutionalProjectionError(
                "constitutional relationship "
                "projection is not deterministic"
            )
        )

    if (
        first[
            "projection_only"
        ]
        is not True
    ):
        raise (
            KindredConstitutionalProjectionError(
                "constitutional relationship "
                "projection is not projection-only"
            )
        )

    if (
        first[
            "mutation_authority"
        ]
        is not False
    ):
        raise (
            KindredConstitutionalProjectionError(
                "constitutional relationship "
                "projection acquired mutation authority"
            )
        )

    if (
        first[
            "creates_relationship_authority"
        ]
        is not False
    ):
        raise (
            KindredConstitutionalProjectionError(
                "Kindred manufactured relationship "
                "authority"
            )
        )

    for relationship in first[
        "constitutional_relationships"
    ]:
        if (
            relationship[
                "authoritative"
            ]
            is not True
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "constitutional relationship "
                    "lost authoritative state"
                )
            )

        if (
            relationship[
                "authority"
            ]
            != "constitutional"
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "constitutional relationship "
                    "authority classification changed"
                )
            )

    for relationship in first[
        "projected_extensions"
    ]:
        if (
            relationship[
                "authoritative"
            ]
            is not False
        ):
            raise (
                KindredConstitutionalProjectionError(
                    "projected extension acquired "
                    "authority"
                )
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
        "constitutional_source":
            first[
                "constitutional_source"
            ],
        "projection_only":
            True,
        "mutation_authority":
            False,
        "creates_relationship_authority":
            False,
        "canonical_relationship_count":
            first[
                "canonical_relationship_count"
            ],
        "constitutionally_resolved_extension_count":
            first[
                "constitutionally_resolved_extension_count"
            ],
        "projected_extension_count":
            first[
                "projected_extension_count"
            ],
        "projection_digest":
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
