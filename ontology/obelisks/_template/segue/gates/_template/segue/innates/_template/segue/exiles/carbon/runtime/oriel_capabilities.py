#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib
import json

from typing import Any, Mapping, Sequence


owner = "carbon"
component = "oriel-capabilities"
authority_effect = "none"
schema = "savant.carbon.oriel-capabilities.v2"


provider_modules = (
    "oriel",
    "oriel_quantum_capabilities",
    "oriel_inverse",
    "oriel_reality",
    "oriel_simulation",
    "oriel_causality",
    "oriel_consequence",
    "oriel_horizon",
    "oriel_worldline",
)


protected_fields = {
    "id",
    "owner",
    "authority_effect",
    "execution_owner",
    "projection_owner",
    "transformation_owner",
}


class oriel_capabilities_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


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


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        prefix
        + ":"
        + digest(
            value
        )[:24]
    )


def strings(
    value: Sequence[Any] | None,
) -> list[str]:
    return sorted(
        {
            str(
                item
            ).strip()
            for item
            in (
                value
                or []
            )
            if str(
                item
            ).strip()
        }
    )


def provider_state(
    module_name: str,
) -> dict[str, Any]:
    try:
        module = importlib.import_module(
            module_name
        )

    except Exception as exc:
        return {
            "module":
                module_name,
            "imported":
                False,
            "manifest_state":
                "unavailable",
            "status_state":
                "unavailable",
            "error":
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
        }

    manifest_fn = getattr(
        module,
        "capability_manifest",
        None,
    )

    status_fn = getattr(
        module,
        "status",
        None,
    )

    manifest_value = None
    manifest_error = None

    if callable(
        manifest_fn
    ):
        try:
            manifest_value = (
                manifest_fn()
            )

        except Exception as exc:
            manifest_error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    status_value = None
    status_error = None

    if callable(
        status_fn
    ):
        try:
            status_value = (
                status_fn()
            )

        except Exception as exc:
            status_error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    return {
        "module":
            module_name,
        "imported":
            True,
        "manifest_state":
            (
                "available"
                if isinstance(
                    manifest_value,
                    Mapping,
                )
                else (
                    "error"
                    if manifest_error
                    else "absent"
                )
            ),
        "status_state":
            (
                "available"
                if isinstance(
                    status_value,
                    Mapping,
                )
                else (
                    "error"
                    if status_error
                    else "absent"
                )
            ),
        "manifest":
            (
                clone(
                    dict(
                        manifest_value
                    )
                )
                if isinstance(
                    manifest_value,
                    Mapping,
                )
                else None
            ),
        "status":
            (
                clone(
                    dict(
                        status_value
                    )
                )
                if isinstance(
                    status_value,
                    Mapping,
                )
                else None
            ),
        "manifest_error":
            manifest_error,
        "status_error":
            status_error,
    }


def normalize_capability(
    raw: Mapping[str, Any],
    *,
    provider: str,
    manifest_schema: str | None,
) -> dict[str, Any]:
    identifier = str(
        raw.get(
            "id",
            "",
        )
    ).strip()

    if not identifier:
        raise oriel_capabilities_error(
            (
                "capability id is required "
                "from provider: "
                + provider
            )
        )

    capability_owner = str(
        raw.get(
            "owner",
            owner,
        )
    ).strip().lower()

    if capability_owner != owner:
        raise oriel_capabilities_error(
            (
                "Oriel capability owner "
                "must remain carbon: "
                + identifier
            )
        )

    effect = str(
        raw.get(
            "authority_effect",
            "none",
        )
    ).strip().lower()

    if effect != "none":
        raise oriel_capabilities_error(
            (
                "Oriel capability may not "
                "create authority: "
                + identifier
            )
        )

    execution_owner = str(
        raw.get(
            "execution_owner",
            owner,
        )
    ).strip().lower()

    if execution_owner != owner:
        raise oriel_capabilities_error(
            (
                "Oriel execution owner "
                "must remain carbon: "
                + identifier
            )
        )

    projection_owner = str(
        raw.get(
            "projection_owner",
            "filament",
        )
    ).strip().lower()

    transformation_owner = str(
        raw.get(
            "transformation_owner",
            "modus",
        )
    ).strip().lower()

    projection = raw.get(
        "projection",
        {},
    )

    if not isinstance(
        projection,
        Mapping,
    ):
        raise oriel_capabilities_error(
            (
                "capability projection "
                "must be an object: "
                + identifier
            )
        )

    result = {
        "id":
            identifier,
        "owner":
            owner,
        "component":
            str(
                raw.get(
                    "component",
                    provider,
                )
            ).strip().lower(),
        "kind":
            str(
                raw.get(
                    "kind",
                    "capability",
                )
            ).strip().lower(),
        "purpose":
            str(
                raw.get(
                    "purpose",
                    "",
                )
            ).strip(),
        "version":
            str(
                raw.get(
                    "version",
                    "1.0.0",
                )
            ).strip(),
        "status":
            str(
                raw.get(
                    "status",
                    "active",
                )
            ).strip().lower(),
        "authority_effect":
            "none",
        "execution_owner":
            owner,
        "projection_owner":
            projection_owner,
        "transformation_owner":
            transformation_owner,
        "operations":
            strings(
                raw.get(
                    "operations"
                )
            ),
        "dependencies":
            strings(
                raw.get(
                    "dependencies"
                )
            ),
        "deterministic":
            bool(
                raw.get(
                    "deterministic",
                    True,
                )
            ),
        "side_effects":
            strings(
                raw.get(
                    "side_effects"
                )
            ),
        "projection":
            clone(
                dict(
                    projection
                )
            ),
        "provider_module":
            provider,
        "provider_manifest_schema":
            manifest_schema,
    }

    result[
        "digest"
    ] = digest(
        result
    )

    return result


def collect() -> dict[str, Any]:
    providers = [
        provider_state(
            name
        )
        for name
        in provider_modules
    ]

    capability_index = {}
    provider_index = {}

    for provider in providers:
        manifest = provider.get(
            "manifest"
        )

        if not isinstance(
            manifest,
            Mapping,
        ):
            continue

        manifest_owner = str(
            manifest.get(
                "owner",
                owner,
            )
        ).strip().lower()

        if manifest_owner != owner:
            raise oriel_capabilities_error(
                (
                    "provider manifest owner "
                    "must remain carbon: "
                    + str(
                        provider[
                            "module"
                        ]
                    )
                )
            )

        effect = str(
            manifest.get(
                "authority_effect",
                "none",
            )
        ).strip().lower()

        if effect != "none":
            raise oriel_capabilities_error(
                (
                    "provider manifest may "
                    "not create authority: "
                    + str(
                        provider[
                            "module"
                        ]
                    )
                )
            )

        capabilities = manifest.get(
            "capabilities",
            [],
        )

        if not isinstance(
            capabilities,
            list,
        ):
            raise oriel_capabilities_error(
                (
                    "provider capabilities "
                    "must be a list: "
                    + str(
                        provider[
                            "module"
                        ]
                    )
                )
            )

        for raw in capabilities:
            if not isinstance(
                raw,
                Mapping,
            ):
                raise oriel_capabilities_error(
                    (
                        "provider capability "
                        "must be an object: "
                        + str(
                            provider[
                                "module"
                            ]
                        )
                    )
                )

            normalized = normalize_capability(
                raw,
                provider=
                    str(
                        provider[
                            "module"
                        ]
                    ),
                manifest_schema=(
                    str(
                        manifest.get(
                            "schema"
                        )
                    )
                    if manifest.get(
                        "schema"
                    )
                    is not None
                    else None
                ),
            )

            identifier = normalized[
                "id"
            ]

            previous = capability_index.get(
                identifier
            )

            if previous is None:
                capability_index[
                    identifier
                ] = normalized

                provider_index[
                    identifier
                ] = [
                    str(
                        provider[
                            "module"
                        ]
                    )
                ]

                continue

            previous_comparable = {
                key:
                    value
                for key, value
                in previous.items()
                if key
                not in {
                    "provider_module",
                    "provider_manifest_schema",
                    "digest",
                }
            }

            current_comparable = {
                key:
                    value
                for key, value
                in normalized.items()
                if key
                not in {
                    "provider_module",
                    "provider_manifest_schema",
                    "digest",
                }
            }

            if (
                previous_comparable
                != current_comparable
            ):
                raise oriel_capabilities_error(
                    (
                        "conflicting capability id: "
                        + identifier
                    )
                )

            provider_index[
                identifier
            ].append(
                str(
                    provider[
                        "module"
                    ]
                )
            )

    capabilities = sorted(
        capability_index.values(),
        key=lambda value:
            value[
                "id"
            ],
    )

    known_ids = {
        value[
            "id"
        ]
        for value
        in capabilities
    }

    dependency_edges = []
    unresolved_dependencies = []

    for capability in capabilities:
        for dependency in capability[
            "dependencies"
        ]:
            resolved = (
                dependency
                in known_ids
            )

            edge = {
                "capability":
                    capability[
                        "id"
                    ],
                "depends_on":
                    dependency,
                "resolved":
                    resolved,
            }

            dependency_edges.append(
                edge
            )

            if not resolved:
                unresolved_dependencies.append(
                    {
                        "capability":
                            capability[
                                "id"
                            ],
                        "depends_on":
                            dependency,
                    }
                )

    unmanifested = sorted(
        str(
            value[
                "module"
            ]
        )
        for value
        in providers
        if (
            value.get(
                "imported"
            )
            and value.get(
                "manifest_state"
            )
            == "absent"
        )
    )

    unavailable = sorted(
        str(
            value[
                "module"
            ]
        )
        for value
        in providers
        if not value.get(
            "imported"
        )
    )

    provider_errors = [
        {
            "module":
                value[
                    "module"
                ],
            "manifest_error":
                value.get(
                    "manifest_error"
                ),
            "status_error":
                value.get(
                    "status_error"
                ),
            "import_error":
                value.get(
                    "error"
                ),
        }
        for value
        in providers
        if (
            value.get(
                "manifest_state"
            )
            in {
                "error",
                "unavailable",
            }
            or value.get(
                "status_state"
            )
            == "error"
        )
    ]

    result = {
        "schema":
            schema,
        "kind":
            "derived-capability-surface",
        "owner":
            owner,
        "component":
            component,
        "authority_effect":
            authority_effect,
        "authoritative_registry":
            False,
        "derivation":
            "provider capability manifests",
        "projection_owner":
            "filament",
        "transformation_owner":
            "modus",
        "provider_count":
            len(
                providers
            ),
        "providers":
            providers,
        "capability_count":
            len(
                capabilities
            ),
        "capabilities":
            capabilities,
        "dependency_edges":
            sorted(
                dependency_edges,
                key=lambda value: (
                    value[
                        "capability"
                    ],
                    value[
                        "depends_on"
                    ],
                ),
            ),
        "unresolved_dependencies":
            sorted(
                unresolved_dependencies,
                key=lambda value: (
                    value[
                        "capability"
                    ],
                    value[
                        "depends_on"
                    ],
                ),
            ),
        "unmanifested_modules":
            unmanifested,
        "unavailable_modules":
            unavailable,
        "provider_errors":
            provider_errors,
        "duplicate_provider_ids": {
            key:
                sorted(
                    value
                )
            for key, value
            in sorted(
                provider_index.items()
            )
            if len(
                value
            )
            > 1
        },
        "source_state_mutated":
            False,
        "canon_effect":
            "none",
        "evidence_admission":
            False,
    }

    result[
        "id"
    ] = stable_id(
        "carbon-oriel-capabilities",
        {
            "providers":
                list(
                    provider_modules
                ),
            "capabilities": [
                value[
                    "digest"
                ]
                for value
                in capabilities
            ],
        },
    )

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def capability_by_id(
    surface: Mapping[str, Any],
    identifier: str,
) -> dict[str, Any]:
    for value in surface.get(
        "capabilities",
        [],
    ):
        if (
            isinstance(
                value,
                Mapping,
            )
            and str(
                value.get(
                    "id",
                    "",
                )
            )
            == identifier
        ):
            return clone(
                dict(
                    value
                )
            )

    raise oriel_capabilities_error(
        (
            "unknown capability: "
            + identifier
        )
    )


def closure(
    surface: Mapping[str, Any],
    identifiers: Sequence[str],
) -> dict[str, Any]:
    requested = strings(
        identifiers
    )

    index = {
        str(
            value.get(
                "id",
                "",
            )
        ):
            value
        for value
        in surface.get(
            "capabilities",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    missing = [
        identifier
        for identifier
        in requested
        if identifier
        not in index
    ]

    if missing:
        raise oriel_capabilities_error(
            (
                "unknown requested capabilities: "
                + ", ".join(
                    missing
                )
            )
        )

    resolved = set()
    unresolved = set()
    stack = list(
        reversed(
            requested
        )
    )

    while stack:
        identifier = stack.pop()

        if identifier in resolved:
            continue

        capability = index.get(
            identifier
        )

        if capability is None:
            unresolved.add(
                identifier
            )

            continue

        resolved.add(
            identifier
        )

        for dependency in reversed(
            strings(
                capability.get(
                    "dependencies"
                )
            )
        ):
            if dependency not in resolved:
                stack.append(
                    dependency
                )

    ordered = [
        clone(
            dict(
                index[
                    identifier
                ]
            )
        )
        for identifier
        in sorted(
            resolved
        )
    ]

    return {
        "schema":
            schema,
        "kind":
            "capability-dependency-closure",
        "owner":
            owner,
        "component":
            component,
        "authority_effect":
            authority_effect,
        "surface_id":
            surface.get(
                "id"
            ),
        "requested":
            requested,
        "resolved": [
            value[
                "id"
            ]
            for value
            in ordered
        ],
        "unresolved":
            sorted(
                unresolved
            ),
        "capabilities":
            ordered,
        "source_state_mutated":
            False,
    }


def masked_capabilities(
    surface: Mapping[str, Any],
    mask: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    values = [
        clone(
            dict(
                value
            )
        )
        for value
        in surface.get(
            "capabilities",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    ]

    if not mask:
        return values

    allow_ids = set(
        strings(
            mask.get(
                "allow_ids"
            )
        )
    )

    deny_ids = set(
        strings(
            mask.get(
                "deny_ids"
            )
        )
    )

    allow_components = set(
        strings(
            mask.get(
                "allow_components"
            )
        )
    )

    allow_operations = set(
        strings(
            mask.get(
                "allow_operations"
            )
        )
    )

    allow_status = set(
        strings(
            mask.get(
                "allow_status"
            )
        )
    )

    output = []

    for value in values:
        if (
            allow_ids
            and value[
                "id"
            ]
            not in allow_ids
        ):
            continue

        if (
            value[
                "id"
            ]
            in deny_ids
        ):
            continue

        if (
            allow_components
            and value.get(
                "component"
            )
            not in allow_components
        ):
            continue

        if (
            allow_status
            and value.get(
                "status"
            )
            not in allow_status
        ):
            continue

        if (
            allow_operations
            and not (
                set(
                    value.get(
                        "operations",
                        [],
                    )
                )
                & allow_operations
            )
        ):
            continue

        output.append(
            value
        )

    return output


def projection_packet(
    surface: Mapping[str, Any],
    *,
    target_exile: str,
    mask: Mapping[str, Any] | None = None,
    include_dependencies: bool = True,
) -> dict[str, Any]:
    target = str(
        target_exile
    ).strip().lower()

    if not target:
        raise oriel_capabilities_error(
            "target_exile is required"
        )

    selected = masked_capabilities(
        surface,
        mask,
    )

    selected_ids = [
        value[
            "id"
        ]
        for value
        in selected
    ]

    unresolved = []

    if (
        include_dependencies
        and selected_ids
    ):
        closure_value = closure(
            surface,
            selected_ids,
        )

        index = {
            str(
                value.get(
                    "id",
                    "",
                )
            ):
                clone(
                    dict(
                        value
                    )
                )
            for value
            in surface.get(
                "capabilities",
                [],
            )
            if isinstance(
                value,
                Mapping,
            )
        }

        selected = [
            index[
                identifier
            ]
            for identifier
            in closure_value[
                "resolved"
            ]
            if identifier
            in index
        ]

        unresolved = closure_value[
            "unresolved"
        ]

    for value in selected:
        if (
            value.get(
                "owner"
            )
            != owner
            or value.get(
                "authority_effect"
            )
            != "none"
            or value.get(
                "execution_owner"
            )
            != owner
        ):
            raise oriel_capabilities_error(
                (
                    "protected capability "
                    "metadata changed: "
                    + str(
                        value.get(
                            "id"
                        )
                    )
                )
            )

    result = {
        "schema":
            schema,
        "kind":
            "capability-projection-packet",
        "owner":
            owner,
        "component":
            component,
        "authority_effect":
            authority_effect,
        "surface_id":
            surface.get(
                "id"
            ),
        "source_exile":
            "carbon",
        "source_component":
            "oriel",
        "target_exile":
            target,
        "projection_owner":
            "filament",
        "transformation_owner":
            "modus",
        "apply_projection":
            False,
        "projection_mode":
            "reference",
        "include_dependencies":
            bool(
                include_dependencies
            ),
        "mask":
            (
                clone(
                    dict(
                        mask
                    )
                )
                if isinstance(
                    mask,
                    Mapping,
                )
                else {}
            ),
        "capability_count":
            len(
                selected
            ),
        "capabilities":
            selected,
        "unresolved_dependencies":
            unresolved,
        "protected_fields":
            sorted(
                protected_fields
            ),
        "ownership_transfer":
            False,
        "authority_transfer":
            False,
        "source_state_mutated":
            False,
        "canon_effect":
            "none",
    }

    result[
        "id"
    ] = stable_id(
        "carbon-oriel-projection",
        {
            "surface_id":
                surface.get(
                    "id"
                ),
            "target_exile":
                target,
            "capabilities": [
                value[
                    "id"
                ]
                for value
                in selected
            ],
            "mask":
                result[
                    "mask"
                ],
        },
    )

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def status() -> dict[str, Any]:
    surface = collect()

    ready = (
        not surface[
            "unmanifested_modules"
        ]
        and not surface[
            "unavailable_modules"
        ]
        and not surface[
            "provider_errors"
        ]
    )

    return {
        "schema":
            schema,
        "kind":
            "status",
        "owner":
            owner,
        "component":
            component,
        "authority_effect":
            authority_effect,
        "authoritative_registry":
            False,
        "capability_count":
            surface[
                "capability_count"
            ],
        "provider_count":
            surface[
                "provider_count"
            ],
        "unmanifested_modules":
            surface[
                "unmanifested_modules"
            ],
        "unavailable_modules":
            surface[
                "unavailable_modules"
            ],
        "provider_error_count":
            len(
                surface[
                    "provider_errors"
                ]
            ),
        "unresolved_dependency_count":
            len(
                surface[
                    "unresolved_dependencies"
                ]
            ),
        "projection_owner":
            "filament",
        "transformation_owner":
            "modus",
        "authority_transfer":
            False,
        "ready":
            ready,
    }


def selftest() -> dict[str, Any]:
    synthetic = {
        "schema":
            schema,
        "id":
            "synthetic",
        "capabilities": [
            {
                "id":
                    "a",
                "owner":
                    "carbon",
                "execution_owner":
                    "carbon",
                "component":
                    "oriel",
                "authority_effect":
                    "none",
                "dependencies": [
                    "b"
                ],
                "operations": [
                    "x"
                ],
            },
            {
                "id":
                    "b",
                "owner":
                    "carbon",
                "execution_owner":
                    "carbon",
                "component":
                    "oriel",
                "authority_effect":
                    "none",
                "dependencies":
                    [],
                "operations": [
                    "y"
                ],
            },
        ],
    }

    closure_value = closure(
        synthetic,
        [
            "a"
        ],
    )

    if (
        closure_value[
            "resolved"
        ]
        != [
            "a",
            "b",
        ]
    ):
        raise oriel_capabilities_error(
            (
                "dependency closure "
                "selftest failed"
            )
        )

    packet = projection_packet(
        synthetic,
        target_exile=
            "palaver",
        mask={
            "allow_ids": [
                "a"
            ]
        },
        include_dependencies=
            True,
    )

    packet_ids = [
        value[
            "id"
        ]
        for value
        in packet[
            "capabilities"
        ]
    ]

    if packet_ids != [
        "a",
        "b",
    ]:
        raise oriel_capabilities_error(
            (
                "projection dependency "
                "selftest failed"
            )
        )

    if (
        packet[
            "authority_transfer"
        ]
        or packet[
            "ownership_transfer"
        ]
    ):
        raise oriel_capabilities_error(
            (
                "projection selftest "
                "transferred protected authority"
            )
        )

    live = collect()

    quantum_ids = {
        value[
            "id"
        ]
        for value
        in live[
            "capabilities"
        ]
        if value.get(
            "component"
        )
        == "oriel-quantum"
    }

    required_quantum = {
        "oriel_quantum_superposition",
        "oriel_quantum_frontier",
        "oriel_quantum_branch_comparison",
        "oriel_quantum_counterfactual_packet",
        "oriel_quantum_collapse",
    }

    if not required_quantum.issubset(
        quantum_ids
    ):
        raise oriel_capabilities_error(
            (
                "live quantum capability "
                "provider is incomplete"
            )
        )

    worldline_ids = {
        value[
            "id"
        ]
        for value
        in live[
            "capabilities"
        ]
        if value.get(
            "component"
        )
        == "oriel-worldline"
    }

    if (
        "oriel_entity_worldline"
        not in worldline_ids
    ):
        raise oriel_capabilities_error(
            (
                "live worldline capability "
                "provider is missing"
            )
        )

    return {
        "schema":
            schema,
        "kind":
            "selftest",
        "owner":
            owner,
        "component":
            component,
        "authority_effect":
            authority_effect,
        "ok":
            True,
        "dependency_closure":
            True,
        "projection_dependency_inclusion":
            True,
        "quantum_manifest_integrated":
            True,
        "worldline_manifest_integrated":
            True,
        "authority_transfer":
            False,
        "ownership_transfer":
            False,
        "live_capability_count":
            live[
                "capability_count"
            ],
        "live_provider_count":
            live[
                "provider_count"
            ],
        "live_unmanifested_modules":
            live[
                "unmanifested_modules"
            ],
        "live_unavailable_modules":
            live[
                "unavailable_modules"
            ],
        "live_provider_error_count":
            len(
                live[
                    "provider_errors"
                ]
            ),
        "live_unresolved_dependency_count":
            len(
                live[
                    "unresolved_dependencies"
                ]
            ),
        "source_state_mutated":
            False,
        "canon_effect":
            "none",
    }


__all__ = [
    "capability_by_id",
    "closure",
    "collect",
    "projection_packet",
    "selftest",
    "status",
]
