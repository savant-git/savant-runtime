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
            historical
