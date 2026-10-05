#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


THIS_FILE = Path(
    __file__
).resolve()

SERVICES_ROOT = (
    THIS_FILE.parent
)

RUNTIME_ROOT = (
    SERVICES_ROOT.parent
)

EXILE_RUNTIME_ROOT = (
    RUNTIME_ROOT.parent
)

EXILE_SEGUE_ROOT = (
    EXILE_RUNTIME_ROOT.parent
)

EXILES_ROOT = (
    EXILE_SEGUE_ROOT.parent
)

REGISTRY_PATH = (
    EXILE_RUNTIME_ROOT
    / "registry/exiles.json"
)

EXPECTED_EXILE_COUNT = 18


class ExileRegistryError(
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
class ExileRegistry:
    names: tuple[
        str,
        ...
    ]
    source: Path
    declared_count: int
    source_digest: str

    @property
    def count(
        self,
    ) -> int:
        return len(
            self.names
        )

    def contains(
        self,
        name: str,
    ) -> bool:
        return (
            name
            in self.names
        )

    def path_for(
        self,
        name: str,
    ) -> Path:
        if not self.contains(
            name
        ):
            raise ExileRegistryError(
                "unknown Exile: "
                + name
            )

        return (
            EXILES_ROOT
            / name
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/"
                "exile-registry/1.0.0"
            ),
            "source":
                str(
                    self.source
                ),
            "source_digest":
                self.source_digest,
            "count":
                self.count,
            "declared_count":
                self.declared_count,
            "expected_count":
                EXPECTED_EXILE_COUNT,
            "exiles":
                list(
                    self.names
                ),
            "authoritative_projection":
                False,
            "mutation_authorized":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def _load_payload(
) -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise ExileRegistryError(
            "missing canonical "
            "Exile registry: "
            + str(
                REGISTRY_PATH
            )
        )

    try:
        payload = json.loads(
            REGISTRY_PATH.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ExileRegistryError(
            "invalid Exile registry "
            "JSON: "
            + str(exc)
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise ExileRegistryError(
            "Exile registry must "
            "be a JSON object"
        )

    return payload


def load_exile_registry(
) -> ExileRegistry:
    payload = _load_payload()

    declared_count = (
        payload.get(
            "count"
        )
    )

    raw_names = (
        payload.get(
            "exiles"
        )
    )

    if not isinstance(
        declared_count,
        int,
    ):
        raise ExileRegistryError(
            "registry count "
            "must be an integer"
        )

    if not isinstance(
        raw_names,
        list,
    ):
        raise ExileRegistryError(
            "registry exiles "
            "must be an array"
        )

    names: list[str] = []

    for raw_name in raw_names:
        if not isinstance(
            raw_name,
            str,
        ):
            raise ExileRegistryError(
                "Exile names "
                "must be strings"
            )

        name = (
            raw_name.strip()
        )

        if not name:
            raise ExileRegistryError(
                "Exile names "
                "must be non-empty"
            )

        if name != raw_name:
            raise ExileRegistryError(
                "Exile name contains "
                "surrounding whitespace: "
                + repr(
                    raw_name
                )
            )

        names.append(
            name
        )

    if (
        len(
            names
        )
        != len(
            set(
                names
            )
        )
    ):
        raise ExileRegistryError(
            "duplicate Exile "
            "identity in registry"
        )

    if (
        declared_count
        != len(
            names
        )
    ):
        raise ExileRegistryError(
            "declared Exile count "
            "does not match registry"
        )

    if (
        len(
            names
        )
        != EXPECTED_EXILE_COUNT
    ):
        raise ExileRegistryError(
            "canonical Exile cardinality "
            f"must be "
            f"{EXPECTED_EXILE_COUNT}; "
            f"found {len(names)}"
        )

    canonical_names = tuple(
        sorted(
            names
        )
    )

    if tuple(
        names
    ) != canonical_names:
        raise ExileRegistryError(
            "Exile registry must "
            "use deterministic "
            "lexicographic ordering"
        )

    source_digest = (
        hashlib.sha256(
            REGISTRY_PATH.read_bytes()
        ).hexdigest()
    )

    return ExileRegistry(
        names=canonical_names,
        source=REGISTRY_PATH,
        declared_count=(
            declared_count
        ),
        source_digest=(
            source_digest
        ),
    )


def validate_registry(
) -> dict[str, Any]:
    try:
        registry = (
            load_exile_registry()
        )

    except ExileRegistryError as exc:
        return {
            "schema": (
                "savant://assurance/"
                "exile-registry/1.0.0"
            ),
            "valid":
                False,
            "error":
                str(exc),
            "source":
                str(
                    REGISTRY_PATH
                ),
        }

    missing_roots: list[str] = []

    missing_entities: list[str] = []

    for name in registry.names:
        root = (
            EXILES_ROOT
            / name
        )

        if not root.is_dir():
            missing_roots.append(
                name
            )

            continue

        if not (
            root
            / "entity.json"
        ).is_file():
            missing_entities.append(
                name
            )

    checks = {
        "source_present":
            REGISTRY_PATH
            .is_file(),

        "declared_count":
            registry
            .declared_count
            == EXPECTED_EXILE_COUNT,

        "actual_count":
            registry.count
            == EXPECTED_EXILE_COUNT,

        "unique_identity":
            len(
                registry.names
            )
            == len(
                set(
                    registry.names
                )
            ),

        "deterministic_order":
            registry.names
            == tuple(
                sorted(
                    registry.names
                )
            ),

        "roots_present":
            not missing_roots,

        "identity_records_present":
            not missing_entities,

        "projection_non_authoritative":
            registry
            .projection()[
                "authoritative_projection"
            ]
            is False,

        "mutation_boundary":
            registry
            .projection()[
                "mutation_authorized"
            ]
            is False,
    }

    payload = {
        "schema": (
            "savant://assurance/"
            "exile-registry/1.0.0"
        ),
        "valid":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "missing_roots":
            missing_roots,
        "missing_entity_records":
            missing_entities,
        "registry":
            registry
            .projection(),
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def main() -> int:
    report = (
        validate_registry()
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
