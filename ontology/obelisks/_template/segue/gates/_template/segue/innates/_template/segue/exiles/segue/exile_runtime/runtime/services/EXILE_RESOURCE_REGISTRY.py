#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from EXILE_REGISTRY import (
    EXPECTED_EXILE_COUNT,
    ExileRegistryError,
    load_exile_registry,
)


REGISTRY_AREAS = (
    "capabilities",
    "contracts",
    "defaults",
    "interfaces",
    "manifests",
    "schemas",
    "templates",
    "versions",
)


DIRECT_AREAS = (
    "authority",
    "canon",
    "graph",
    "health",
    "interface",
    "lineage",
    "observatory",
    "runtime",
    "validation",
)


class ExileResourceRegistryError(
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
class ResourceArea:
    exile: str
    area: str
    path: Path
    registry_area: bool
    exists: bool
    files: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "owner":
                self.exile,
            "identity":
                "exile:"
                + self.exile,
            "area":
                self.area,
            "path":
                str(
                    self.path
                ),
            "registry_area":
                self.registry_area,
            "exists":
                self.exists,
            "files":
                list(
                    self.files
                ),
            "filesystem_establishes_authority":
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


def _registry():
    try:
        registry = (
            load_exile_registry()
        )

    except ExileRegistryError as exc:
        raise ExileResourceRegistryError(
            "unable to load canonical "
            "Exile registry: "
            + str(
                exc
            )
        ) from exc

    if (
        registry.count
        != EXPECTED_EXILE_COUNT
    ):
        raise ExileResourceRegistryError(
            "Exile registry cardinality "
            f"must be "
            f"{EXPECTED_EXILE_COUNT}; "
            f"found {registry.count}"
        )

    return registry


def area_path(
    exile: str,
    area: str,
    *,
    registry_area: bool,
) -> Path:
    registry = _registry()

    root = (
        registry.path_for(
            exile
        )
    )

    if registry_area:
        return (
            root
            / "registry"
            / area
        )

    return (
        root
        / area
    )


def files_in(
    path: Path,
) -> tuple[str, ...]:
    if not path.is_dir():
        return ()

    return tuple(
        str(
            item
        )
        for item
        in sorted(
            path.iterdir(),
            key=lambda value:
                value.name,
        )
        if item.is_file()
    )


def collect_area(
    area: str,
    *,
    registry_area: bool,
) -> dict[str, dict[str, Any]]:
    registry = _registry()

    rows: dict[
        str,
        dict[str, Any],
    ] = {}

    for exile in (
        registry.names
    ):
        path = area_path(
            exile,
            area,
            registry_area=(
                registry_area
            ),
        )

        record = ResourceArea(
            exile=exile,
            area=area,
            path=path,
            registry_area=(
                registry_area
            ),
            exists=(
                path.is_dir()
            ),
            files=files_in(
                path
            ),
        )

        rows[
            exile
        ] = (
            record.projection()
        )

    return rows


def collect_registry_area(
    area: str,
) -> dict[str, dict[str, Any]]:
    if (
        area
        not in REGISTRY_AREAS
    ):
        raise ExileResourceRegistryError(
            "unknown registry area: "
            + area
        )

    return collect_area(
        area,
        registry_area=True,
    )


def collect_direct_area(
    area: str,
) -> dict[str, dict[str, Any]]:
    if (
        area
        not in DIRECT_AREAS
    ):
        raise ExileResourceRegistryError(
            "unknown direct area: "
            + area
        )

    return collect_area(
        area,
        registry_area=False,
    )


def collect_many(
    areas: Iterable[str],
    *,
    registry_area: bool,
) -> dict[
    str,
    dict[
        str,
        dict[str, Any],
    ],
]:
    return {
        area: collect_area(
            area,
            registry_area=(
                registry_area
            ),
        )
        for area
        in areas
    }


def collect_all(
) -> dict[str, Any]:
    registry = _registry()

    payload = {
        "schema": (
            "savant://runtime/"
            "exile-resource-registry/"
            "1.0.0"
        ),
        "registry_source":
            str(
                registry.source
            ),
        "registry_digest":
            registry.source_digest,
        "exile_count":
            registry.count,
        "registry_areas":
            collect_many(
                REGISTRY_AREAS,
                registry_area=True,
            ),
        "direct_areas":
            collect_many(
                DIRECT_AREAS,
                registry_area=False,
            ),
        "filesystem_defines_population":
            False,
        "mutation_performed":
            False,
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def validate(
) -> dict[str, Any]:
    registry = _registry()

    registry_projection = (
        collect_many(
            REGISTRY_AREAS,
            registry_area=True,
        )
    )

    direct_projection = (
        collect_many(
            DIRECT_AREAS,
            registry_area=False,
        )
    )

    all_rows = [
        row
        for group
        in (
            registry_projection,
            direct_projection,
        )
        for area_rows
        in group.values()
        for row
        in area_rows.values()
    ]

    checks = {
        "exile_count": (
            registry.count
            == EXPECTED_EXILE_COUNT
        ),
        "registry_area_count": (
            len(
                REGISTRY_AREAS
            )
            == 8
        ),
        "direct_area_count": (
            len(
                DIRECT_AREAS
            )
            == 9
        ),
        "registry_population_consistent": (
            all(
                len(
                    rows
                )
                == EXPECTED_EXILE_COUNT
                for rows
                in registry_projection.values()
            )
        ),
        "direct_population_consistent": (
            all(
                len(
                    rows
                )
                == EXPECTED_EXILE_COUNT
                for rows
                in direct_projection.values()
            )
        ),
        "filesystem_not_authority": (
            all(
                row[
                    "filesystem_establishes_authority"
                ]
                is False
                for row
                in all_rows
            )
        ),
        "projections_non_authoritative": (
            all(
                row[
                    "authoritative_projection"
                ]
                is False
                for row
                in all_rows
            )
        ),
        "stable_identity": (
            all(
                row[
                    "identity"
                ]
                == (
                    "exile:"
                    + row[
                        "owner"
                    ]
                )
                for row
                in all_rows
            )
        ),
        "mutation_boundary":
            True,
    }

    payload = {
        "schema": (
            "savant://assurance/"
            "exile-resource-registry/"
            "1.0.0"
        ),
        "valid":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "exile_count":
            registry.count,
        "registry_area_count":
            len(
                REGISTRY_AREAS
            ),
        "direct_area_count":
            len(
                DIRECT_AREAS
            ),
        "mutation_performed":
            False,
        "physical_migration_performed":
            False,
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def main() -> int:
    report = validate()

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
