#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


schema = (
    "savant://runtime/utility/"
    "utility-edifice/1.0.0"
)

selftest_schema = (
    "savant://runtime/utility/"
    "utility-edifice-selftest/1.0.0"
)

owner = "utility"
authority_effect = "none"

accepted_decision = (
    "AD-20260926-002-utility-edifice"
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
    "droplet",
    "stream",
    "flow",
    "current",
    "tide",
    "surge",
    "torrent",
    "sea",
)


class utility_edifice_error(
    RuntimeError
):
    pass


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
            raise utility_edifice_error(
                "unknown utility edifice "
                f"level: {self.level}"
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
            "level":
                self.level,
            "ordinal":
                self.ordinal,
        }


def edifice_projection(
) -> dict[str, Any]:
    projection = {
        "schema":
            schema,
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "authoritative":
            False,
        "rebuildable":
            True,
        "accepted_decision":
            accepted_decision,
        "levels":
            list(
                levels
            ),
        "atomic_level":
            "glyph",
        "terminal_level":
            "oeuvre",
        "superseded_levels":
            list(
                superseded_levels
            ),
        "supersedes": {
            level: None
            for level
            in superseded_levels
        },
        "ordinal_mapping":
            False,
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
    return level in superseded_levels


def require_current_level(
    level: str,
) -> str:
    if level not in levels:
        raise utility_edifice_error(
            "utility edifice level is "
            f"not current: {level}"
        )

    return level


def migrate_level(
    level: str,
    *,
    semantic_level: str | None = None,
) -> str:
    if level in levels:
        return level

    if level not in superseded_levels:
        raise utility_edifice_error(
            "unknown utility edifice "
            f"level: {level}"
        )

    if semantic_level is None:
        raise utility_edifice_error(
            "superseded utility level "
            "requires explicit semantic "
            "classification; ordinal "
            "migration is forbidden"
        )

    return require_current_level(
        semantic_level
    )


def validate_projection(
    projection: dict[
        str,
        Any,
    ],
) -> bool:
    expected = (
        edifice_projection()
    )

    return (
        projection
        == expected
    )


def selftest(
) -> dict[str, Any]:
    first = (
        edifice_projection()
    )

    second = (
        edifice_projection()
    )

    ordinal_migration_rejected = (
        False
    )

    try:
        migrate_level(
            "current"
        )
    except utility_edifice_error:
        ordinal_migration_rejected = (
            True
        )

    semantic_migration = (
        migrate_level(
            "current",
            semantic_level=
                "epiphany",
        )
        == "epiphany"
    )

    checks = {
        "authority_none":
            first[
                "authority_effect"
            ]
            == "none",
        "deterministic":
            first == second,
        "glyph_atomic":
            first[
                "atomic_level"
            ]
            == "glyph",
        "glyph_not_superseded":
            "glyph"
            not in superseded_levels,
        "edifice_exact":
            tuple(
                first[
                    "levels"
                ]
            )
            == levels,
        "identity_ordinal":
            identity(
                "spasm"
            ).ordinal
            == 2,
        "nine_levels":
            len(
                levels
            )
            == 9,
        "no_ordinal_mapping":
            first[
                "ordinal_mapping"
            ]
            is False,
        "non_authoritative_projection":
            first[
                "authoritative"
            ]
            is False,
        "oeuvre_terminal":
            first[
                "terminal_level"
            ]
            == "oeuvre",
        "ordinal_migration_rejected":
            ordinal_migration_rejected,
        "projection_validated":
            validate_projection(
                first
            ),
        "rebuildable_projection":
            first[
                "rebuildable"
            ]
            is True,
        "semantic_migration":
            semantic_migration,
        "superseded_current_detected":
            is_superseded_level(
                "current"
            ),
        "unique_levels":
            len(
                set(
                    levels
                )
            )
            == len(
                levels
            ),
    }

    return {
        "schema":
            selftest_schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "projection_digest":
            first[
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
        if result[
            "ok"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
