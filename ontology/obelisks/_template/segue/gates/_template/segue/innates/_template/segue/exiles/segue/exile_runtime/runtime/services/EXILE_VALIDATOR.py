#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from EXILE_REGISTRY import (
    EXILES_ROOT,
    EXPECTED_EXILE_COUNT,
    ExileRegistryError,
    load_exile_registry,
    validate_registry,
)


KNOWN_FACILITIES = (
    "apps",
    "authority",
    "cache",
    "canon",
    "composition",
    "dynamic",
    "evolution",
    "facets",
    "graph",

    "interface",
    "introspection",
    "lifecycle",
    "lineage",
    "metrics",
    "observatory",
    "registry",
    "runtime",
    "sessions",

    "state",
    "static",
    "tests",
    "validation",
    "segue",

    "rubric",
    "cabal",
    "kindred",
    "moods",
    "slots",
    "attachments",
    "projections",
    "history",
    "tasks",
)


MANIFEST_NAME = (
    "facility.manifest.json"
)


EXPECTED_MANIFEST_SCHEMA = (
    "savant://ontology/"
    "exile/facilities/1.0.0"
)


VALID_MANIFEST_KEYS = {
    "schema",
    "owner",
    "materialized",
    "optional",
    "compatibility",
}


ALLOWED_NON_EXILE_ROOTS = {
    "segue",
}


class ExileValidationError(
    RuntimeError
):
    pass


def load_manifest(
    path: Path,
) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ExileValidationError(
            "invalid facility "
            f"manifest JSON: "
            f"{path}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise ExileValidationError(
            "facility manifest "
            "must be an object"
        )

    unknown_keys = (
        set(
            payload
        )
        - VALID_MANIFEST_KEYS
    )

    if unknown_keys:
        raise ExileValidationError(
            "unknown facility "
            "manifest keys: "
            + ", ".join(
                sorted(
                    unknown_keys
                )
            )
        )

    if (
        payload.get(
            "schema"
        )
        != EXPECTED_MANIFEST_SCHEMA
    ):
        raise ExileValidationError(
            "invalid facility "
            "manifest schema"
        )

    owner = payload.get(
        "owner"
    )

    if (
        not isinstance(
            owner,
            str,
        )
        or not owner.strip()
    ):
        raise ExileValidationError(
            "facility manifest "
            "owner is required"
        )

    category_sets: list[
        set[str]
    ] = []

    for field in (
        "materialized",
        "optional",
        "compatibility",
    ):
        values = payload.get(
            field,
            [],
        )

        if not isinstance(
            values,
            list,
        ):
            raise ExileValidationError(
                f"{field} must "
                "be an array"
            )

        if (
            len(
                values
            )
            != len(
                set(
                    values
                )
            )
        ):
            raise ExileValidationError(
                f"{field} contains "
                "duplicate facilities"
            )

        normalized: set[
            str
        ] = set()

        for value in values:
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value.strip()
            ):
                raise ExileValidationError(
                    f"{field} contains "
                    "an invalid facility"
                )

            if (
                value
                != value.strip()
            ):
                raise ExileValidationError(
                    f"{field} contains "
                    "whitespace-normalized "
                    "facility names"
                )

            normalized.add(
                value
            )

        category_sets.append(
            normalized
        )

    materialized_set, (
        optional_set
    ), compatibility_set = (
        category_sets
    )

    if (
        materialized_set
        & optional_set
        or materialized_set
        & compatibility_set
        or optional_set
        & compatibility_set
    ):
        raise ExileValidationError(
            "facility categories "
            "must not overlap"
        )

    return payload


def present_facilities(
    base: Path,
) -> tuple[
    str,
    ...,
]:
    return tuple(
        sorted(
            path.name
            for path
            in base.iterdir()
            if path.is_dir()
        )
    )


def empty_directory(
    path: Path,
) -> bool:
    try:
        next(
            path.iterdir()
        )

    except StopIteration:
        return True

    return False


def validate_exile(
    exile: str,
) -> dict[str, Any]:
    base = (
        EXILES_ROOT
        / exile
    )

    errors: list[
        dict[str, Any]
    ] = []

    observations: list[
        dict[str, Any]
    ] = []

    if not base.is_dir():
        return {
            "exile":
                exile,
            "path":
                str(
                    base
                ),
            "valid":
                False,
            "manifest":
                None,
            "materialized":
                [],
            "present":
                [],
            "errors": [
                {
                    "error":
                        "missing_exile_directory",
                    "path":
                        str(
                            base
                        ),
                }
            ],
            "observations":
                [],
        }

    entity_path = (
        base
        / "entity.json"
    )

    if not entity_path.is_file():
        errors.append(
            {
                "error":
                    "missing_entity_json",
                "path":
                    str(
                        entity_path
                    ),
            }
        )

    present = (
        present_facilities(
            base
        )
    )

    manifest_path = (
        base
        / MANIFEST_NAME
    )

    manifest: (
        dict[str, Any]
        | None
    ) = None

    if manifest_path.is_file():
        try:
            manifest = (
                load_manifest(
                    manifest_path
                )
            )

        except ExileValidationError as exc:
            errors.append(
                {
                    "error":
                        "invalid_facility_manifest",
                    "path":
                        str(
                            manifest_path
                        ),
                    "message":
                        str(
                            exc
                        ),
                }
            )

    if manifest is not None:
        expected_owner = (
            "exile:"
            + exile
        )

        if (
            manifest[
                "owner"
            ]
            != expected_owner
        ):
            errors.append(
                {
                    "error":
                        "manifest_owner_mismatch",
                    "expected":
                        expected_owner,
                    "observed":
                        manifest[
                            "owner"
                        ],
                }
            )

        materialized = tuple(
            manifest.get(
                "materialized",
                [],
            )
        )

        optional = tuple(
            manifest.get(
                "optional",
                [],
            )
        )

        compatibility = tuple(
            manifest.get(
                "compatibility",
                [],
            )
        )

        declared = (
            set(
                materialized
            )
            | set(
                optional
            )
            | set(
                compatibility
            )
        )

        for facility in materialized:
            path = (
                base
                / facility
            )

            if not path.is_dir():
                errors.append(
                    {
                        "error":
                            "missing_declared_facility",
                        "facility":
                            facility,
                        "path":
                            str(
                                path
                            ),
                    }
                )

        undeclared_present = (
            tuple(
                sorted(
                    set(
                        present
                    )
                    - declared
                )
            )
        )

        for facility in (
            undeclared_present
        ):
            observations.append(
                {
                    "observation":
                        "undeclared_existing_facility",
                    "facility":
                        facility,
                    "compatibility_preserved":
                        True,
                }
            )

    else:
        materialized = ()

        observations.append(
            {
                "observation":
                    "legacy_layout_without_manifest",
                "meaning": (
                    "existing directories "
                    "remain compatibility "
                    "surfaces; no fixed "
                    "facility set is required"
                ),
            }
        )

    known = set(
        KNOWN_FACILITIES
    )

    for facility in present:
        path = (
            base
            / facility
        )

        if (
            facility in known
            and empty_directory(
                path
            )
        ):
            observations.append(
                {
                    "observation":
                        "empty_legacy_or_reserved_facility",
                    "facility":
                        facility,
                    "path":
                        str(
                            path
                        ),
                    "removal_authorized":
                        False,
                }
            )

    return {
        "exile":
            exile,
        "path":
            str(
                base
            ),
        "valid":
            not errors,
        "manifest": (
            str(
                manifest_path
            )
            if manifest_path.is_file()
            else None
        ),
        "materialized":
            list(
                materialized
            ),
        "present":
            list(
                present
            ),
        "errors":
            errors,
        "observations":
            observations,
    }


def invalid_root_directories(
    exile_names:
        tuple[
            str,
            ...,
        ],
) -> list[str]:
    allowed = (
        set(
            exile_names
        )
        | ALLOWED_NON_EXILE_ROOTS
    )

    return [
        str(
            path
        )
        for path
        in sorted(
            EXILES_ROOT.iterdir(),
            key=lambda value:
                value.name,
        )
        if (
            path.is_dir()
            and path.name
            not in allowed
        )
    ]


def validate(
) -> dict[str, Any]:
    registry_report = (
        validate_registry()
    )

    if not registry_report.get(
        "valid",
        False,
    ):
        return {
            "schema": (
                "savant://assurance/"
                "exile-layout/2.1.0"
            ),
            "policy":
                "capability-materialized",
            "registry":
                registry_report,
            "valid":
                False,
            "errors": [
                {
                    "error":
                        "invalid_exile_registry"
                }
            ],
        }

    try:
        registry = (
            load_exile_registry()
        )

    except ExileRegistryError as exc:
        return {
            "schema": (
                "savant://assurance/"
                "exile-layout/2.1.0"
            ),
            "policy":
                "capability-materialized",
            "valid":
                False,
            "errors": [
                {
                    "error":
                        "exile_registry_load_failure",
                    "message":
                        str(
                            exc
                        ),
                }
            ],
        }

    reports = [
        validate_exile(
            exile
        )
        for exile
        in registry.names
    ]

    errors = [
        {
            "exile":
                report[
                    "exile"
                ],
            **error,
        }
        for report
        in reports
        for error
        in report[
            "errors"
        ]
    ]

    bad_root = (
        invalid_root_directories(
            registry.names
        )
    )

    for path in bad_root:
        errors.append(
            {
                "error":
                    "unexpected_root_directory",
                "path":
                    path,
            }
        )

    report = {
        "schema": (
            "savant://assurance/"
            "exile-layout/2.1.0"
        ),
        "policy":
            "capability-materialized",

        "registry_source":
            str(
                registry.source
            ),

        "registry_digest":
            registry
            .source_digest,

        "exile_count":
            registry.count,

        "expected_exile_count":
            EXPECTED_EXILE_COUNT,

        "hardcoded_exile_list":
            False,

        "fixed_folder_requirement":
            False,

        "empty_folder_requirement":
            False,

        "manifest_name":
            MANIFEST_NAME,

        "known_facility_count":
            len(
                KNOWN_FACILITIES
            ),

        "physical_migration_authorized":
            False,

        "destructive_mutation_authorized":
            False,

        "bad_root_directories":
            bad_root,

        "registry":
            registry_report,

        "errors":
            errors,

        "exiles":
            reports,

        "valid": (
            registry.count
            == EXPECTED_EXILE_COUNT
            and len(
                reports
            )
            == EXPECTED_EXILE_COUNT
            and not errors
        ),
    }

    return report


def main() -> int:
    result = validate()

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result[
            "valid"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
