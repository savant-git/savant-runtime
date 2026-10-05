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

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )


from sliver_pool import (
    Sliver,
    SliverPool,
    SliverPoolError,
    build_pool,
    normalize_id,
    recipe_identities,
)


SCHEMA = (
    "savant://coalesce/"
    "identity-resolution/1.1"
)

OWNER = "prodigal:modus:coalesce"

HISTORICAL_PREFIX = (
    "slab:coalesce:"
)

SLIVER_PREFIX = (
    "sliver:coalesce:"
)


class IdentityResolutionError(
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


def sliver_projection(
    sliver: Sliver,
    *,
    requested_identity: str,
    identity_kind: str,
) -> dict[str, Any]:
    canonical = sliver.projection()

    payload = {
        "schema":
            SCHEMA,
        "owner":
            OWNER,
        "requested_identity":
            requested_identity,
        "requested_identity_kind":
            identity_kind,
        "canonical_identity":
            sliver.sliver_id,
        "canonical_identity_kind":
            "sliver",
        "capability":
            sliver.capability,
        "historical_identities":
            list(
                sliver.historical_slabs
            ),
        "canonical_projection":
            canonical,
        "compatibility": {
            "historical_identity_preserved":
                True,
            "canonical_identity_referenced":
                True,
            "substance_copied":
                False,
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


class IdentityResolver:
    def __init__(
        self,
        pool: SliverPool | None = None,
    ) -> None:
        self.pool = (
            pool
            or build_pool()
        )

    def resolve_sliver(
        self,
        sliver_id: str,
    ) -> dict[str, Any]:
        target = normalize_id(
            sliver_id
        )

        try:
            sliver = self.pool.get(
                target
            )
        except SliverPoolError as exc:
            raise IdentityResolutionError(
                str(exc)
            ) from exc

        return sliver_projection(
            sliver,
            requested_identity=target,
            identity_kind="sliver",
        )

    def resolve_historical(
        self,
        slab_id: str,
    ) -> dict[str, Any]:
        target = normalize_id(
            slab_id
        )

        try:
            sliver = (
                self.pool
                .resolve_historical_slab(
                    target
                )
            )
        except SliverPoolError as exc:
            raise IdentityResolutionError(
                str(exc)
            ) from exc

        return sliver_projection(
            sliver,
            requested_identity=target,
            identity_kind="historical-slab",
        )

    def resolve_recipe(
        self,
        recipe_id: str,
    ) -> dict[str, Any]:
        target = normalize_id(
            recipe_id
        )

        try:
            recipe = (
                self.pool
                .resolve_recipe_row(
                    target
                )
            )

            sliver_ids = (
                self.pool
                .application_slivers(
                    target
                )
            )
        except SliverPoolError as exc:
            raise IdentityResolutionError(
                str(exc)
            ) from exc

        if not (
            1
            <= len(
                sliver_ids
            )
            <= 9
        ):
            raise IdentityResolutionError(
                "recipe resolves outside "
                "the 1-9 Sliver Alloy limit: "
                f"{target}"
            )

        identities = (
            recipe_identities(
                recipe
            )
        )

        canonical_identity = (
            normalize_id(
                recipe.get(
                    "id"
                )
            )
            or target
        )

        short_identity = (
            normalize_id(
                recipe.get(
                    "recipe_id"
                )
            )
            or target
        )

        payload = {
            "schema":
                SCHEMA,
            "owner":
                OWNER,
            "requested_identity":
                target,
            "requested_identity_kind":
                "recipe",
            "canonical_identity":
                canonical_identity,
            "short_identity":
                short_identity,
            "recipe_identities":
                list(
                    identities
                ),
            "canonical_identity_kind":
                "alloy-recipe",
            "slivers":
                list(
                    sliver_ids
                ),
            "sliver_count":
                len(
                    sliver_ids
                ),
            "maximum_slivers":
                9,
            "compatibility": {
                "canonical_recipe_identity":
                    True,
                "short_recipe_identity":
                    True,
                "historical_recipe_preserved":
                    True,
                "canonical_slivers_referenced":
                    True,
                "substance_copied":
                    False,
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

    def resolve(
        self,
        identity: str,
    ) -> dict[str, Any]:
        target = normalize_id(
            identity
        )

        if not target:
            raise IdentityResolutionError(
                "identity is required"
            )

        if target.startswith(
            HISTORICAL_PREFIX
        ):
            return self.resolve_historical(
                target
            )

        if target.startswith(
            SLIVER_PREFIX
        ):
            return self.resolve_sliver(
                target
            )

        return self.resolve_recipe(
            target
        )

    def status(
        self,
    ) -> dict[str, Any]:
        projection = (
            self.pool
            .projection()
        )

        return {
            "schema":
                SCHEMA,
            "owner":
                OWNER,
            "historical_identity_count":
                len(
                    self.pool
                    .historical_slabs
                ),
            "canonical_sliver_count":
                len(
                    self.pool
                    .slivers
                ),
            "recipe_count":
                len(
                    self.pool
                    ._recipe_rows()
                ),
            "historical_resolution":
                True,
            "canonical_resolution":
                True,
            "canonical_recipe_resolution":
                True,
            "short_recipe_resolution":
                True,
            "fixed_pool_size":
                projection.get(
                    "fixed_pool_size"
                ),
            "destructive_migration":
                False,
            "authority_effect":
                "none",
        }


def resolver() -> IdentityResolver:
    return IdentityResolver()


def selftest() -> dict[str, Any]:
    instance = resolver()

    historical = (
        instance.pool
        .historical_slabs
    )

    slivers = (
        instance.pool
        .slivers
    )

    if len(
        historical
    ) != 81:
        raise IdentityResolutionError(
            "historical identity baseline "
            "must remain 81"
        )

    for slab_id in historical:
        instance.resolve_historical(
            slab_id
        )

    for sliver in slivers:
        instance.resolve_sliver(
            sliver.sliver_id
        )

    short = instance.resolve_recipe(
        "chronology-explorer"
    )

    canonical = instance.resolve_recipe(
        short[
            "canonical_identity"
        ]
    )

    if (
        short[
            "canonical_identity"
        ]
        != canonical[
            "canonical_identity"
        ]
    ):
        raise IdentityResolutionError(
            "recipe aliases do not converge"
        )

    result = instance.status()

    result[
        "ok"
    ] = True

    return result


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
