#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


COALESCE_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce"
).resolve()

RECIPES_PATH = (
    COALESCE_ROOT
    / "registry"
    / "recipes.json"
)

CAPABILITIES_PATH = (
    COALESCE_ROOT
    / "interface"
    / "capabilities"
    / "capabilities.json"
)

SLIVER_SCHEMA = (
    "savant://coalesce/sliver/1"
)

POOL_SCHEMA = (
    "savant://coalesce/sliver-pool/1.1"
)


class SliverPoolError(
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
        raise SliverPoolError(
            f"missing required file: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise SliverPoolError(
            f"expected object: {path}"
        )

    return payload


def normalize_id(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def slab_parts(
    slab_id: str,
) -> tuple[str, str]:
    parts = slab_id.split(
        ":"
    )

    if (
        len(parts) < 4
        or parts[0] != "slab"
        or parts[1] != "coalesce"
    ):
        raise SliverPoolError(
            f"invalid historical slab id: {slab_id}"
        )

    domain = parts[2]

    capability = ":".join(
        parts[3:]
    )

    return (
        domain,
        capability,
    )


def recipe_identities(
    row: dict[str, Any],
) -> tuple[str, ...]:
    values = {
        normalize_id(
            row.get(
                "id"
            )
        ),
        normalize_id(
            row.get(
                "recipe_id"
            )
        ),
    }

    return tuple(
        sorted(
            value
            for value in values
            if value
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class Sliver:
    sliver_id: str
    capability: str
    historical_slabs: tuple[str, ...]
    owner: str = (
        "prodigal:modus:coalesce"
    )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SLIVER_SCHEMA,
            "id": self.sliver_id,
            "owner": self.owner,
            "capability": (
                self.capability
            ),
            "historical_slabs": list(
                self.historical_slabs
            ),
            "canonical_substance": (
                "reference-only"
            ),
            "authoritative": False,
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


class SliverPool:
    def __init__(
        self,
        *,
        recipes_path: Path = (
            RECIPES_PATH
        ),
    ) -> None:
        self.recipes_path = (
            recipes_path.resolve()
        )

        self.recipes = load_json(
            self.recipes_path
        )

        self._historical_slabs = (
            self._discover_historical_slabs()
        )

        self._slivers = (
            self._normalize_slivers()
        )

    def _recipe_rows(
        self,
    ) -> tuple[dict[str, Any], ...]:
        candidates = (
            self.recipes.get(
                "recipes"
            )
            or self.recipes.get(
                "applications"
            )
            or self.recipes.get(
                "items"
            )
            or ()
        )

        if not isinstance(
            candidates,
            list,
        ):
            raise SliverPoolError(
                "recipes collection is invalid"
            )

        return tuple(
            row
            for row in candidates
            if isinstance(
                row,
                dict,
            )
        )

    def _discover_historical_slabs(
        self,
    ) -> tuple[str, ...]:
        result: set[str] = set()

        def walk(
            value: Any,
        ) -> None:
            if isinstance(
                value,
                str,
            ):
                if value.startswith(
                    "slab:coalesce:"
                ):
                    result.add(
                        value
                    )
                return

            if isinstance(
                value,
                dict,
            ):
                for child in (
                    value.values()
                ):
                    walk(
                        child
                    )
                return

            if isinstance(
                value,
                list,
            ):
                for child in value:
                    walk(
                        child
                    )

        walk(
            self.recipes
        )

        return tuple(
            sorted(
                result
            )
        )

    def _normalize_slivers(
        self,
    ) -> tuple[Sliver, ...]:
        grouped: dict[
            str,
            list[str],
        ] = {}

        for slab_id in (
            self._historical_slabs
        ):
            domain, _ = slab_parts(
                slab_id
            )

            grouped.setdefault(
                domain,
                [],
            ).append(
                slab_id
            )

        result = []

        for domain in sorted(
            grouped
        ):
            result.append(
                Sliver(
                    sliver_id=(
                        "sliver:coalesce:"
                        + domain
                    ),
                    capability=domain,
                    historical_slabs=tuple(
                        sorted(
                            grouped[
                                domain
                            ]
                        )
                    ),
                )
            )

        return tuple(
            result
        )

    @property
    def historical_slabs(
        self,
    ) -> tuple[str, ...]:
        return (
            self._historical_slabs
        )

    @property
    def slivers(
        self,
    ) -> tuple[Sliver, ...]:
        return (
            self._slivers
        )

    def get(
        self,
        sliver_id: str,
    ) -> Sliver:
        target = normalize_id(
            sliver_id
        )

        for sliver in (
            self._slivers
        ):
            if (
                sliver.sliver_id
                == target
            ):
                return sliver

        raise SliverPoolError(
            f"unknown sliver: {target}"
        )

    def resolve_historical_slab(
        self,
        slab_id: str,
    ) -> Sliver:
        target = normalize_id(
            slab_id
        )

        for sliver in (
            self._slivers
        ):
            if target in (
                sliver.historical_slabs
            ):
                return sliver

        raise SliverPoolError(
            "historical slab is not "
            f"mapped: {target}"
        )

    def resolve_recipe_row(
        self,
        application_id: str,
    ) -> dict[str, Any]:
        target = normalize_id(
            application_id
        )

        if not target:
            raise SliverPoolError(
                "application recipe identity is required"
            )

        for row in (
            self._recipe_rows()
        ):
            if target in recipe_identities(
                row
            ):
                return row

        raise SliverPoolError(
            "unknown application recipe: "
            f"{target}"
        )

    def application_slivers(
        self,
        application_id: str,
    ) -> tuple[str, ...]:
        matched = self.resolve_recipe_row(
            application_id
        )

        slab_ids: set[str] = set()

        def walk(
            value: Any,
        ) -> None:
            if isinstance(
                value,
                str,
            ):
                if value.startswith(
                    "slab:coalesce:"
                ):
                    slab_ids.add(
                        value
                    )
                return

            if isinstance(
                value,
                list,
            ):
                for child in value:
                    walk(
                        child
                    )
                return

            if isinstance(
                value,
                dict,
            ):
                for child in (
                    value.values()
                ):
                    walk(
                        child
                    )

        walk(
            matched
        )

        sliver_ids = {
            self.resolve_historical_slab(
                slab_id
            ).sliver_id
            for slab_id
            in slab_ids
        }

        return tuple(
            sorted(
                sliver_ids
            )
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": POOL_SCHEMA,
            "owner": (
                "prodigal:modus:coalesce"
            ),
            "source": str(
                self.recipes_path
            ),
            "historical_slab_count": (
                len(
                    self._historical_slabs
                )
            ),
            "sliver_count": len(
                self._slivers
            ),
            "fixed_pool_size": False,
            "slivers": [
                sliver.projection()
                for sliver
                in self._slivers
            ],
            "compatibility": {
                "historical_slab_ids": True,
                "historical_recipes": True,
                "canonical_recipe_ids": True,
                "short_recipe_ids": True,
                "destructive_migration": False,
            },
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def build_pool() -> SliverPool:
    return SliverPool()


def selftest() -> dict[str, Any]:
    pool = build_pool()

    rows = pool._recipe_rows()

    if not rows:
        raise SliverPoolError(
            "recipe registry is empty"
        )

    checked = 0

    for row in rows:
        identities = recipe_identities(
            row
        )

        if not identities:
            raise SliverPoolError(
                "recipe lacks identity"
            )

        expected = (
            pool.application_slivers(
                identities[0]
            )
        )

        for identity in identities:
            actual = (
                pool.application_slivers(
                    identity
                )
            )

            if actual != expected:
                raise SliverPoolError(
                    "recipe aliases resolve differently: "
                    f"{identities}"
                )

            checked += 1

    short = (
        pool.application_slivers(
            "chronology-explorer"
        )
    )

    if not short:
        raise SliverPoolError(
            "chronology-explorer resolved "
            "to no Slivers"
        )

    if len(short) > 9:
        raise SliverPoolError(
            "chronology-explorer exceeds "
            "the nine-Sliver Alloy limit"
        )

    return {
        "ok": True,
        "schema": POOL_SCHEMA,
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "historical_slab_count": len(
            pool.historical_slabs
        ),
        "sliver_count": len(
            pool.slivers
        ),
        "recipe_identity_checks": checked,
        "short_recipe_identity": True,
        "canonical_recipe_identity": True,
        "authority_effect": "none",
    }


def main() -> int:
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
