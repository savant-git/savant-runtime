#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from EXILE_REGISTRY import (
    EXILES_ROOT,
    EXPECTED_EXILE_COUNT,
    ExileRegistry,
    ExileRegistryError,
    load_exile_registry,
)


class ExileDiscoveryError(
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
class DiscoveredExile:
    name: str
    identity: str
    path: Path
    entity_path: Path
    registry_source: Path
    registry_digest: str
    exists: bool
    entity_present: bool

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "name":
                self.name,
            "identity":
                self.identity,
            "path":
                str(
                    self.path
                ),
            "entity_path":
                str(
                    self.entity_path
                ),
            "exists":
                self.exists,
            "entity_present":
                self.entity_present,
            "registry_source":
                str(
                    self.registry_source
                ),
            "registry_digest":
                self.registry_digest,
            "discovered_from_filesystem":
                False,
            "authoritative_projection":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def _registry(
) -> ExileRegistry:
    try:
        registry = (
            load_exile_registry()
        )

    except ExileRegistryError as exc:
        raise ExileDiscoveryError(
            "unable to load "
            "canonical Exile registry: "
            + str(
                exc
            )
        ) from exc

    if (
        registry.count
        != EXPECTED_EXILE_COUNT
    ):
        raise ExileDiscoveryError(
            "Exile registry cardinality "
            f"must be "
            f"{EXPECTED_EXILE_COUNT}; "
            f"found {registry.count}"
        )

    return registry


def discover(
) -> list[Path]:
    """
    Compatibility API.

    Return canonical Exile paths in registry order.

    Historical callers expected Path objects.
    That contract is preserved.

    Filesystem scanning does not define the
    population.
    """
    registry = _registry()

    return [
        registry.path_for(
            name
        )
        for name
        in registry.names
    ]


def discover_records(
) -> tuple[
    DiscoveredExile,
    ...,
]:
    registry = _registry()

    result: list[
        DiscoveredExile
    ] = []

    for name in (
        registry.names
    ):
        path = (
            EXILES_ROOT
            / name
        )

        entity_path = (
            path
            / "entity.json"
        )

        result.append(
            DiscoveredExile(
                name=name,
                identity=(
                    "exile:"
                    + name
                ),
                path=path,
                entity_path=(
                    entity_path
                ),
                registry_source=(
                    registry.source
                ),
                registry_digest=(
                    registry
                    .source_digest
                ),
                exists=(
                    path.is_dir()
                ),
                entity_present=(
                    entity_path
                    .is_file()
                ),
            )
        )

    return tuple(
        result
    )


def discover_names(
) -> tuple[
    str,
    ...,
]:
    return tuple(
        record.name
        for record
        in discover_records()
    )


def discover_existing(
) -> tuple[
    DiscoveredExile,
    ...,
]:
    return tuple(
        record
        for record
        in discover_records()
        if record.exists
    )


def discover_missing(
) -> tuple[
    DiscoveredExile,
    ...,
]:
    return tuple(
        record
        for record
        in discover_records()
        if not record.exists
    )


def filesystem_extras(
) -> tuple[
    Path,
    ...,
]:
    """
    Observe unexpected directories only.

    Filesystem extras never become Exiles
    through discovery.
    """
    registry = _registry()

    expected = set(
        registry.names
    )

    allowed_non_exile = {
        "segue",
    }

    if not EXILES_ROOT.is_dir():
        return ()

    return tuple(
        sorted(
            (
                path
                for path
                in EXILES_ROOT.iterdir()
                if (
                    path.is_dir()
                    and path.name
                    not in expected
                    and path.name
                    not in allowed_non_exile
                )
            ),
            key=lambda path:
                path.name,
        )
    )


def iter_discovered(
) -> Iterator[
    DiscoveredExile
]:
    yield from (
        discover_records()
    )


def validate_discovery(
) -> dict[str, Any]:
    registry = _registry()

    records = (
        discover_records()
    )

    missing = [
        record.name
        for record
        in records
        if not record.exists
    ]

    missing_entities = [
        record.name
        for record
        in records
        if (
            record.exists
            and not record.entity_present
        )
    ]

    extras = [
        str(
            path
        )
        for path
        in filesystem_extras()
    ]

    names = tuple(
        record.name
        for record
        in records
    )

    checks = {
        "registry_cardinality": (
            registry.count
            == EXPECTED_EXILE_COUNT
        ),
        "discovery_cardinality": (
            len(
                records
            )
            == EXPECTED_EXILE_COUNT
        ),
        "registry_order_preserved": (
            names
            == registry.names
        ),
        "unique_identity": (
            len(
                names
            )
            == len(
                set(
                    names
                )
            )
        ),
        "roots_present": (
            not missing
        ),
        "entity_records_present": (
            not missing_entities
        ),
        "filesystem_not_authority":
            True,
        "extras_not_admitted": (
            all(
                Path(
                    value
                ).name
                not in names
                for value
                in extras
            )
        ),
        "mutation_boundary":
            True,
    }

    payload = {
        "schema": (
            "savant://assurance/"
            "exile-discovery/2.0.0"
        ),
        "valid":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "count":
            len(
                records
            ),
        "expected_count":
            EXPECTED_EXILE_COUNT,
        "registry_source":
            str(
                registry.source
            ),
        "registry_digest":
            registry
            .source_digest,
        "filesystem_defines_population":
            False,
        "missing":
            missing,
        "missing_entity_records":
            missing_entities,
        "filesystem_extras":
            extras,
        "mutation_performed":
            False,
        "physical_migration_performed":
            False,
        "records": [
            record.projection()
            for record
            in records
        ],
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def main() -> int:
    report = (
        validate_discovery()
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if report[
            "valid"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
