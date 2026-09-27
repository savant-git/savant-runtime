#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


schema = (
    "savant://runtime/sieve/"
    "utility-hierarchy/1.0.0"
)

owner = "sieve"

authority_effect = "none"

accepted_decision = (
    "AD-20260926-002-utility-hierarchy"
)

levels = (
    "glyph",
    "iota",
    "spasm",
    "vagary",
    "epiphany",
    "tactic",
    "artifice",
    "agenda",
    "oeuvre",
)

superseded_levels = (
    "glyph",
    "droplet",
    "stream",
    "flow",
    "current",
    "tide",
    "surge",
    "torrent",
    "sea",
)


class utility_hierarchy_error(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class utility_identity:
    level: str

    def __post_init__(
        self,
    ) -> None:
        if self.level not in levels:
            raise utility_hierarchy_error(
                "unknown utility level: "
                f"{self.level}"
            )

    @property
    def ordinal(
        self,
    ) -> int:
        return levels.index(
            self.level
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": schema,
            "owner": owner,
            "authority_effect":
                authority_effect,
            "accepted_decision":
                accepted_decision,
            "level": self.level,
            "ordinal":
                self.ordinal,
            "hierarchy":
                list(levels),
        }


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def hierarchy_projection(
) -> dict[str, Any]:
    projection = {
        "schema": schema,
        "owner": owner,
        "authority_effect":
            authority_effect,
        "accepted_decision":
            accepted_decision,
        "levels":
            list(levels),
        "level_count":
            len(levels),
        "supersedes": {
            "hierarchy":
                list(
                    superseded_levels
                ),
            "mapping":
                None,
            "ordinal_mapping":
                False,
        },
        "classification_rule":
            (
                "semantic classification "
                "is required; superseded "
                "ordinal position does not "
                "determine current level"
            ),
        "authoritative":
            False,
        "rebuildable":
            True,
    }

    projection[
        "projection_digest"
    ] = digest(
        projection
    )

    return projection


def identity(
    level: str,
) -> utility_identity:
    return utility_identity(
        level=level
    )


def is_current_level(
    level: str,
) -> bool:
    return level in levels


def is_superseded_level(
    level: str,
) -> bool:
    return (
        level
        in superseded_levels
        and level
        not in levels
    )


def require_current_level(
    level: str,
) -> str:
    if not is_current_level(
        level
    ):
        raise utility_hierarchy_error(
            "utility level requires "
            "semantic reclassification "
            "under current hierarchy: "
            f"{level}"
        )

    return level


def migrate_level(
    level: str,
    *,
    semantic_level:
        str | None = None,
) -> str:
    if is_current_level(
        level
    ):
        return level

    if not is_superseded_level(
        level
    ):
        raise utility_hierarchy_error(
            "unknown utility level: "
            f"{level}"
        )

    if semantic_level is None:
        raise utility_hierarchy_error(
            "superseded utility level "
            "cannot be migrated by "
            "ordinal position; provide "
            "semantic_level"
        )

    return require_current_level(
        semantic_level
    )


def validate_projection(
    value: Mapping[
        str,
        Any,
    ],
) -> None:
    if (
        value.get(
            "accepted_decision"
        )
        != accepted_decision
    ):
        raise utility_hierarchy_error(
            "utility hierarchy projection "
            "does not identify current "
            "accepted decision"
        )

    if tuple(
        value.get(
            "levels",
            (),
        )
    ) != levels:
        raise utility_hierarchy_error(
            "utility hierarchy projection "
            "does not match current levels"
        )


def selftest(
) -> dict[str, Any]:
    projection = (
        hierarchy_projection()
    )

    checks: dict[
        str,
        bool,
    ] = {}

    checks[
        "hierarchy_exact"
    ] = tuple(
        projection[
            "levels"
        ]
    ) == levels

    checks[
        "nine_levels"
    ] = (
        len(levels)
        == 9
    )

    checks[
        "glyph_atomic"
    ] = (
        levels[0]
        == "glyph"
    )

    checks[
        "oeuvre_terminal"
    ] = (
        levels[-1]
        == "oeuvre"
    )

    checks[
        "unique_levels"
    ] = (
        len(
            set(levels)
        )
        == len(levels)
    )

    checks[
        "authority_none"
    ] = (
        projection[
            "authority_effect"
        ]
        == "none"
    )

    checks[
        "non_authoritative_projection"
    ] = (
        projection[
            "authoritative"
        ]
        is False
    )

    checks[
        "rebuildable_projection"
    ] = (
        projection[
            "rebuildable"
        ]
        is True
    )

    checks[
        "no_ordinal_mapping"
    ] = (
        projection[
            "supersedes"
        ][
            "ordinal_mapping"
        ]
        is False
    )

    checks[
        "superseded_current_detected"
    ] = (
        is_superseded_level(
            "current"
        )
        is True
    )

    checks[
        "glyph_not_superseded"
    ] = (
        is_superseded_level(
            "glyph"
        )
        is False
    )

    checks[
        "identity_ordinal"
    ] = (
        identity(
            "epiphany"
        ).ordinal
        == 4
    )

    rejected_ordinal_migration = (
        False
    )

    try:
        migrate_level(
            "current"
        )
    except (
        utility_hierarchy_error
    ):
        rejected_ordinal_migration = (
            True
        )

    checks[
        "ordinal_migration_rejected"
    ] = (
        rejected_ordinal_migration
    )

    checks[
        "semantic_migration"
    ] = (
        migrate_level(
            "current",
            semantic_level=
                "tactic",
        )
        == "tactic"
    )

    validation_passed = False

    try:
        validate_projection(
            projection
        )

        validation_passed = True
    except (
        utility_hierarchy_error
    ):
        validation_passed = False

    checks[
        "projection_validated"
    ] = (
        validation_passed
    )

    deterministic = (
        hierarchy_projection()
        == hierarchy_projection()
    )

    checks[
        "deterministic"
    ] = deterministic

    return {
        "schema":
            "savant://runtime/sieve/"
            "utility-hierarchy-selftest/"
            "1.0.0",
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "projection_digest":
            projection[
                "projection_digest"
            ],
    }


def main() -> int:
    result = selftest()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return (
        0
        if result["ok"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
