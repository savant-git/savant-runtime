#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


schema = (
    "savant://runtime/programming/"
    "programming-edifice/1.0.0"
)

selftest_schema = (
    "savant://runtime/programming/"
    "programming-edifice-selftest/1.0.0"
)

owner = "programming"
authority_effect = "none"

composition_decision = (
    "AD-20260813-006-programming-"
    "composition-hierarchy"
)

terminology_decision = (
    "ad-20260928-001-three-primary-edifices"
)

atomic_decision = (
    "AD-20260923-001-glyph-atomic-"
    "programming-level"
)

levels = (
    "glyph",
    "line",
    "segment",
    "snippet",
    "script",
    "engine",
    "subsystem",
    "system",
    "application",
)


class programming_edifice_error(
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
class programming_identity:
    level: str

    def __post_init__(
        self,
    ) -> None:
        if self.level not in levels:
            raise programming_edifice_error(
                "unknown programming "
                "edifice level: "
                f"{self.level}"
            )

    @property
    def ordinal(
        self,
    ) -> int:
        return levels.index(
            self.level
        )

    @property
    def lower(
        self,
    ) -> str | None:
        if self.ordinal == 0:
            return None

        return levels[
            self.ordinal - 1
        ]

    @property
    def upper(
        self,
    ) -> str | None:
        if (
            self.ordinal
            == len(levels) - 1
        ):
            return None

        return levels[
            self.ordinal + 1
        ]

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "level":
                self.level,
            "ordinal":
                self.ordinal,
            "lower":
                self.lower,
            "upper":
                self.upper,
        }


def identity(
    level: str,
) -> programming_identity:
    return programming_identity(
        level=level
    )


def is_level(
    level: str,
) -> bool:
    return level in levels


def require_level(
    level: str,
) -> str:
    if level not in levels:
        raise programming_edifice_error(
            "programming edifice level "
            "is not current: "
            f"{level}"
        )

    return level


def contains(
    lower: str,
    upper: str,
) -> bool:
    lower_identity = identity(
        lower
    )

    upper_identity = identity(
        upper
    )

    return (
        lower_identity.ordinal
        < upper_identity.ordinal
    )


def adjacent(
    lower: str,
    upper: str,
) -> bool:
    lower_identity = identity(
        lower
    )

    upper_identity = identity(
        upper
    )

    return (
        upper_identity.ordinal
        - lower_identity.ordinal
        == 1
    )


def composition_path(
    lower: str,
    upper: str,
) -> tuple[str, ...]:
    lower_identity = identity(
        lower
    )

    upper_identity = identity(
        upper
    )

    if (
        lower_identity.ordinal
        > upper_identity.ordinal
    ):
        raise programming_edifice_error(
            "composition path cannot "
            "descend"
        )

    return levels[
        lower_identity.ordinal:
        upper_identity.ordinal + 1
    ]


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
        "authority": {
            "composition":
                composition_decision,
            "terminology":
                terminology_decision,
            "atomic":
                atomic_decision,
        },
        "levels":
            list(
                levels
            ),
        "atomic_level":
            "glyph",
        "terminal_level":
            "application",
        "composition_direction":
            "lower-to-higher",
        "composition": [
            {
                "lower":
                    levels[index],
                "upper":
                    levels[
                        index + 1
                    ],
            }
            for index
            in range(
                len(levels) - 1
            )
        ],
    }

    projection[
        "projection_digest"
    ] = digest(
        projection
    )

    return projection


def validate_projection(
    projection: dict[
        str,
        Any,
    ],
) -> bool:
    return (
        projection
        == edifice_projection()
    )


def selftest(
) -> dict[str, Any]:
    first = (
        edifice_projection()
    )

    second = (
        edifice_projection()
    )

    invalid_rejected = False

    try:
        identity(
            "character"
        )
    except programming_edifice_error:
        invalid_rejected = True

    descending_rejected = False

    try:
        composition_path(
            "engine",
            "glyph",
        )
    except programming_edifice_error:
        descending_rejected = True

    checks = {
        "authority_none":
            first[
                "authority_effect"
            ]
            == "none",
        "deterministic":
            first == second,
        "nine_levels":
            len(
                levels
            )
            == 9,
        "unique_levels":
            len(
                set(
                    levels
                )
            )
            == len(
                levels
            ),
        "edifice_exact":
            tuple(
                first[
                    "levels"
                ]
            )
            == levels,
        "glyph_atomic":
            first[
                "atomic_level"
            ]
            == "glyph",
        "application_terminal":
            first[
                "terminal_level"
            ]
            == "application",
        "character_not_level":
            "character"
            not in levels,
        "invalid_rejected":
            invalid_rejected,
        "identity_ordinal":
            identity(
                "snippet"
            ).ordinal
            == 3,
        "adjacent":
            adjacent(
                "glyph",
                "line",
            ),
        "nonadjacent":
            not adjacent(
                "glyph",
                "segment",
            ),
        "composition_direction":
            contains(
                "glyph",
                "application",
            ),
        "composition_path":
            composition_path(
                "segment",
                "engine",
            )
            == (
                "segment",
                "snippet",
                "script",
                "engine",
            ),
        "descending_rejected":
            descending_rejected,
        "eight_edges":
            len(
                first[
                    "composition"
                ]
            )
            == 8,
        "non_authoritative_projection":
            first[
                "authoritative"
            ]
            is False,
        "rebuildable_projection":
            first[
                "rebuildable"
            ]
            is True,
        "projection_validated":
            validate_projection(
                first
            ),
        "composition_authority":
            first[
                "authority"
            ][
                "composition"
            ]
            == composition_decision,
        "terminology_authority":
            first[
                "authority"
            ][
                "terminology"
            ]
            == terminology_decision,
        "atomic_authority":
            first[
                "authority"
            ][
                "atomic"
            ]
            == atomic_decision,
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
