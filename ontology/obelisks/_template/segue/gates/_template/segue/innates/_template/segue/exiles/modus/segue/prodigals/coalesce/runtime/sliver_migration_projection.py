#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


COALESCE_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce"
).resolve()

RUNTIME_ROOT = (
    COALESCE_ROOT
    / "runtime"
)

PIECES_PATH = (
    COALESCE_ROOT
    / "registry"
    / "pieces.json"
)

RECIPES_PATH = (
    COALESCE_ROOT
    / "registry"
    / "recipes.json"
)

for value in (
    str(RUNTIME_ROOT),
):
    if value not in sys.path:
        sys.path.insert(
            0,
            value,
        )


from sliver_pool import (
    SliverPool,
    build_pool,
)


SCHEMA = (
    "savant://coalesce/"
    "sliver-migration-projection/1"
)

OWNER = "prodigal:modus:coalesce"

SOURCE_MODEL = (
    "historical-81-piece"
)

TARGET_MODEL = (
    "extensible-sliver-pool"
)

DISPOSITION = (
    "merged-into-sliver"
)


class SliverMigrationProjectionError(
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
        separators=(
            ",",
            ":",
        ),
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


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise SliverMigrationProjectionError(
            f"required source missing: {path}"
        )

    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise SliverMigrationProjectionError(
            f"expected object: {path}"
        )

    return value


def source_pieces() -> tuple[
    dict[str, Any],
    ...,
]:
    payload = load_json(
        PIECES_PATH
    )

    rows = payload.get(
        "pieces"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise SliverMigrationProjectionError(
            "historical piece registry "
            "does not contain pieces[]"
        )

    pieces = tuple(
        row
        for row in rows
        if isinstance(
            row,
            dict,
        )
    )

    declared_count = payload.get(
        "piece_count"
    )

    if (
        declared_count
        != len(
            pieces
        )
    ):
        raise SliverMigrationProjectionError(
            "historical piece registry "
            "count mismatch"
        )

    return pieces


def historical_piece_id(
    row: dict[str, Any],
) -> str:
    value = str(
        row.get(
            "id"
        )
        or ""
    ).strip()

    if not value.startswith(
        "slab:coalesce:"
    ):
        raise SliverMigrationProjectionError(
            "invalid historical piece id: "
            f"{value!r}"
        )

    return value


def migration_rows(
    pool: SliverPool,
) -> tuple[
    dict[str, Any],
    ...,
]:
    rows = []

    for piece in source_pieces():
        piece_id = historical_piece_id(
            piece
        )

        sliver = (
            pool
            .resolve_historical_slab(
                piece_id
            )
        )

        rows.append(
            {
                "historical_id":
                    piece_id,
                "historical_name":
                    str(
                        piece.get(
                            "canonical_name"
                        )
                        or ""
                    ),
                "historical_service":
                    str(
                        piece.get(
                            "service"
                        )
                        or ""
                    ),
                "historical_ordinal":
                    piece.get(
                        "global_ordinal"
                    ),
                "disposition":
                    DISPOSITION,
                "target_sliver":
                    sliver.sliver_id,
                "target_capability":
                    sliver.capability,
                "substance":
                    "reference-only",
                "source_preserved":
                    True,
                "destructive_mutation":
                    False,
            }
        )

    return tuple(
        sorted(
            rows,
            key=lambda row: (
                int(
                    row.get(
                        "historical_ordinal"
                    )
                    or 0
                ),
                str(
                    row.get(
                        "historical_id"
                    )
                ),
            ),
        )
    )


def recipe_projection(
    pool: SliverPool,
) -> tuple[
    dict[str, Any],
    ...,
]:
    payload = load_json(
        RECIPES_PATH
    )

    recipes = payload.get(
        "recipes"
    )

    if not isinstance(
        recipes,
        list,
    ):
        raise SliverMigrationProjectionError(
            "recipe registry does not "
            "contain recipes[]"
        )

    projected = []

    for recipe in recipes:
        if not isinstance(
            recipe,
            dict,
        ):
            continue

        recipe_id = str(
            recipe.get(
                "id"
            )
            or ""
        ).strip()

        if not recipe_id:
            raise SliverMigrationProjectionError(
                "recipe lacks id"
            )

        sliver_ids = (
            pool
            .application_slivers(
                recipe_id
            )
        )

        if not (
            1
            <= len(
                sliver_ids
            )
            <= 9
        ):
            raise SliverMigrationProjectionError(
                "recipe violates Alloy "
                "Sliver limit: "
                f"{recipe_id}: "
                f"{len(sliver_ids)}"
            )

        projected.append(
            {
                "recipe_id":
                    recipe_id,
                "slivers":
                    list(
                        sliver_ids
                    ),
                "sliver_count":
                    len(
                        sliver_ids
                    ),
                "within_alloy_limit":
                    True,
            }
        )

    return tuple(
        sorted(
            projected,
            key=lambda row: str(
                row[
                    "recipe_id"
                ]
            ),
        )
    )


def project() -> dict[str, Any]:
    pool = build_pool()

    mappings = migration_rows(
        pool
    )

    recipes = recipe_projection(
        pool
    )

    historical_ids = {
        row[
            "historical_id"
        ]
        for row
        in mappings
    }

    pool_historical_ids = set(
        pool.historical_slabs
    )

    if (
        historical_ids
        != pool_historical_ids
    ):
        missing = sorted(
            historical_ids
            - pool_historical_ids
        )

        extra = sorted(
            pool_historical_ids
            - historical_ids
        )

        raise SliverMigrationProjectionError(
            "historical coverage mismatch: "
            f"missing={missing}, "
            f"extra={extra}"
        )

    if len(
        historical_ids
    ) != 81:
        raise SliverMigrationProjectionError(
            "verified historical baseline "
            "must contain 81 pieces"
        )

    pool_projection = (
        pool.projection()
    )

    sliver_ids = tuple(
        sorted(
            str(
                row.get(
                    "id"
                )
            )
            for row
            in pool_projection.get(
                "slivers",
                [],
            )
            if isinstance(
                row,
                dict,
            )
        )
    )

    payload = {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "source_model":
            SOURCE_MODEL,
        "target_model":
            TARGET_MODEL,
        "source_piece_count":
            len(
                historical_ids
            ),
        "sliver_count":
            len(
                sliver_ids
            ),
        "fixed_target_cardinality":
            False,
        "maximum_slivers_per_alloy":
            9,
        "slivers":
            list(
                sliver_ids
            ),
        "piece_dispositions":
            list(
                mappings
            ),
        "recipe_projection":
            list(
                recipes
            ),
        "coverage": {
            "historical_piece_count":
                len(
                    historical_ids
                ),
            "mapped_piece_count":
                len(
                    mappings
                ),
            "unmapped_piece_count":
                0,
            "all_historical_pieces_mapped":
                True,
            "recipes_projected":
                len(
                    recipes
                ),
            "recipes_within_alloy_limit":
                all(
                    row[
                        "within_alloy_limit"
                    ]
                    for row
                    in recipes
                ),
        },
        "compatibility": {
            "historical_piece_registry_preserved":
                True,
            "historical_recipe_registry_preserved":
                True,
            "historical_identifiers_resolvable":
                True,
            "filament_boundary_unchanged":
                True,
            "legacy_runtime_preserved":
                True,
            "destructive_migration":
                False,
        },
        "authority_effect":
            "none",
        "authoritative":
            False,
        "rebuildable":
            True,
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def selftest() -> dict[str, Any]:
    result = project()

    coverage = result[
        "coverage"
    ]

    if coverage[
        "historical_piece_count"
    ] != 81:
        raise SliverMigrationProjectionError(
            "historical baseline changed"
        )

    if coverage[
        "mapped_piece_count"
    ] != 81:
        raise SliverMigrationProjectionError(
            "migration mapping incomplete"
        )

    if coverage[
        "unmapped_piece_count"
    ] != 0:
        raise SliverMigrationProjectionError(
            "migration contains "
            "unmapped pieces"
        )

    if not coverage[
        "recipes_within_alloy_limit"
    ]:
        raise SliverMigrationProjectionError(
            "Alloy limit violation"
        )

    if result[
        "fixed_target_cardinality"
    ]:
        raise SliverMigrationProjectionError(
            "obsolete fixed cardinality "
            "was restored"
        )

    return {
        "ok":
            True,
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "historical_piece_count":
            81,
        "mapped_piece_count":
            81,
        "sliver_count":
            result[
                "sliver_count"
            ],
        "recipe_count":
            coverage[
                "recipes_projected"
            ],
        "maximum_slivers_per_alloy":
            9,
        "fixed_target_cardinality":
            False,
        "digest":
            result[
                "digest"
            ],
        "authority_effect":
            "none",
    }


def main() -> int:
    print(
        json.dumps(
            selftest(),
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
