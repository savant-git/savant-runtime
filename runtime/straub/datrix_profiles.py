#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


schema = "savant.carbon.straub.datrix-profiles.v1"
owner = "carbon"
module = "straub"
authority_effect = "none"

exact_source_recovery = False
reconstruction_basis = "verified behavioral contract"

DEFAULT_PROFILE = "knowledge"

PROFILE_NAMES = (
    "artifact",
    "chronicle",
    "knowledge",
    "workflow",
    "world",
)

_PROFILE_DEFINITIONS = {
    name: {
        "name": name,
        "status": "active",
        "authority_effect": authority_effect,
    }
    for name in PROFILE_NAMES
}

PROFILES = _PROFILE_DEFINITIONS
PROFILE_DEFINITIONS = _PROFILE_DEFINITIONS


class DatrixProfileError(
    ValueError
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


def normalize_profile_name(
    value: Any,
) -> str:
    name = str(
        value or ""
    ).strip().casefold()

    if not name:
        raise DatrixProfileError(
            "datrix profile name is required"
        )

    if name not in _PROFILE_DEFINITIONS:
        raise DatrixProfileError(
            "unknown datrix profile: "
            f"{name}"
        )

    return name


def profile_names(
) -> tuple[str, ...]:
    return PROFILE_NAMES


def names(
) -> tuple[str, ...]:
    return profile_names()


def get_profile(
    name: Any,
) -> dict[str, Any]:
    normalized = normalize_profile_name(
        name
    )

    return dict(
        _PROFILE_DEFINITIONS[
            normalized
        ]
    )


def profile(
    name: Any,
) -> dict[str, Any]:
    return get_profile(
        name
    )


def resolve_profile(
    name: Any,
) -> dict[str, Any]:
    return get_profile(
        name
    )


def _profile_input(
    values: (
        str
        | Iterable[Any]
        | None
    ),
) -> tuple[Any, ...]:
    if values is None:
        return (
            DEFAULT_PROFILE,
        )

    if isinstance(
        values,
        str,
    ):
        return tuple(
            part.strip()
            for part
            in values.split(",")
            if part.strip()
        )

    return tuple(
        values
    )


def validate_profile_names(
    values: (
        str
        | Iterable[Any]
        | None
    ),
) -> tuple[str, ...]:
    source = _profile_input(
        values
    )

    if not source:
        source = (
            DEFAULT_PROFILE,
        )

    result: list[str] = []
    seen: set[str] = set()

    for value in source:
        name = normalize_profile_name(
            value
        )

        if name in seen:
            continue

        seen.add(
            name
        )

        result.append(
            name
        )

    return tuple(
        result
    )


def validate_profiles(
    values: (
        str
        | Iterable[Any]
        | None
    ),
) -> tuple[str, ...]:
    return validate_profile_names(
        values
    )


def resolve_profile_names(
    values: (
        str
        | Iterable[Any]
        | None
    ),
) -> tuple[str, ...]:
    return validate_profile_names(
        values
    )


def resolve_profiles(
    values: (
        str
        | Iterable[Any]
        | None
    ) = None,
) -> tuple[
    dict[str, Any],
    ...,
]:
    return tuple(
        get_profile(
            name
        )
        for name
        in validate_profile_names(
            values
        )
    )


def resolve(
    values: (
        str
        | Iterable[Any]
        | None
    ) = None,
) -> tuple[
    dict[str, Any],
    ...,
]:
    return resolve_profiles(
        values
    )


def compose_profiles(
    values: (
        str
        | Iterable[Any]
        | None
    ) = None,
) -> dict[str, Any]:
    resolved_names = (
        validate_profile_names(
            values
        )
    )

    payload = {
        "schema":
            (
                "savant.carbon.straub."
                "datrix-profile-composition.v1"
            ),

        "owner":
            owner,

        "module":
            module,

        "profiles":
            list(
                resolved_names
            ),

        "profile_count":
            len(
                resolved_names
            ),

        "default_profile":
            DEFAULT_PROFILE,

        "rebuildable":
            True,

        "authoritative":
            False,

        "authority_effect":
            authority_effect,

        "provenance":
            {
                "exact_source_recovery":
                    exact_source_recovery,

                "basis":
                    reconstruction_basis,
            },
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def compose(
    values: (
        str
        | Iterable[Any]
        | None
    ) = None,
) -> dict[str, Any]:
    return compose_profiles(
        values
    )


def manifest(
) -> dict[str, Any]:
    payload = {
        "schema":
            schema,

        "kind":
            "datrix-profile-family",

        "owner":
            owner,

        "module":
            module,

        "profiles":
            [
                dict(
                    _PROFILE_DEFINITIONS[
                        name
                    ]
                )
                for name
                in PROFILE_NAMES
            ],

        "profile_names":
            list(
                PROFILE_NAMES
            ),

        "profile_count":
            len(
                PROFILE_NAMES
            ),

        "default_profile":
            DEFAULT_PROFILE,

        "composition":
            {
                "multiple_profiles":
                    True,

                "deduplicate":
                    True,

                "preserve_input_order":
                    True,

                "one_straub_substrate":
                    True,

                "separate_database_per_profile":
                    False,
            },

        "rebuildable":
            True,

        "authoritative":
            False,

        "authority_effect":
            authority_effect,

        "provenance":
            {
                "exact_source_recovery":
                    exact_source_recovery,

                "basis":
                    reconstruction_basis,
            },
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def selftest(
) -> dict[str, Any]:
    composition = compose_profiles(
        (
            "workflow",
            "chronicle",
            "workflow",
        )
    )

    first = manifest()
    second = manifest()

    checks = {
        "five_profiles":
            (
                len(
                    PROFILE_NAMES
                )
                == 5
            ),

        "profile_names_exact":
            (
                PROFILE_NAMES
                == (
                    "artifact",
                    "chronicle",
                    "knowledge",
                    "workflow",
                    "world",
                )
            ),

        "default_knowledge":
            (
                DEFAULT_PROFILE
                == "knowledge"
            ),

        "default_resolution":
            (
                validate_profile_names(
                    None
                )
                == (
                    "knowledge",
                )
            ),

        "composition_deduplicates":
            (
                composition[
                    "profiles"
                ]
                == [
                    "workflow",
                    "chronicle",
                ]
            ),

        "composition_ordered":
            (
                composition[
                    "profiles"
                ][0]
                == "workflow"
            ),

        "one_substrate":
            (
                first[
                    "composition"
                ][
                    "one_straub_substrate"
                ]
                is True
            ),

        "not_separate_databases":
            (
                first[
                    "composition"
                ][
                    "separate_database_per_profile"
                ]
                is False
            ),

        "authority_none":
            (
                first[
                    "authority_effect"
                ]
                == "none"
            ),

        "non_authoritative":
            (
                first[
                    "authoritative"
                ]
                is False
            ),

        "rebuildable":
            (
                first[
                    "rebuildable"
                ]
                is True
            ),

        "deterministic_manifest":
            (
                first
                == second
            ),

        "unknown_rejected":
            False,
    }

    try:
        validate_profile_names(
            (
                "knowledge",
                "unknown-profile",
            )
        )

    except DatrixProfileError:
        checks[
            "unknown_rejected"
        ] = True

    return {
        "schema":
            (
                "savant.carbon.straub."
                "datrix-profiles-selftest.v1"
            ),

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "manifest_digest":
            first[
                "digest"
            ],
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
