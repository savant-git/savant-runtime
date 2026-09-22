#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from oriel_capabilities import collect as collect_capabilities


owner = "carbon"
component = "oriel-introspection"
authority_effect = "none"
schema = "savant.carbon.oriel-introspection.v1"

carbon_root = Path(__file__).resolve().parent.parent

required_registry_paths = (
    "registry/manifests/oriel.json",
    "registry/capabilities/oriel.json",
)

protected_capability_values = {
    "owner": "carbon",
    "execution_owner": "carbon",
    "authority_effect": "none",
}


class oriel_introspection_error(
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


def load_json(
    relative_path: str,
) -> dict[str, Any]:
    path = carbon_root / relative_path

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise oriel_introspection_error(
            (
                "cannot read "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_introspection_error(
            (
                "invalid json in "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_introspection_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def carbon_capability_ids() -> set[str]:
    registry = load_json(
        "interface/capabilities/capabilities.json"
    )

    return {
        str(
            value.get(
                "id",
                "",
            )
        ).strip()
        for value
        in registry.get(
            "capabilities",
            [],
        )
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
            ).strip()
        )
    }


def dependency_resolution(
    surface: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    carbon_ids = (
        carbon_capability_ids()
    )

    externally_resolved = []
    unresolved = []

    for value in surface.get(
        "unresolved_dependencies",
        [],
    ):
        if not isinstance(
            value,
            Mapping,
        ):
            continue

        dependency = str(
            value.get(
                "depends_on",
                "",
            )
        ).strip()

        row = {
            "capability":
                str(
                    value.get(
                        "capability",
                        "",
                    )
                ).strip(),

            "depends_on":
                dependency,
        }

        if dependency in carbon_ids:
            row[
                "resolution"
            ] = "carbon_capability"

            externally_resolved.append(
                row
            )

        else:
            row[
                "resolution"
            ] = "unresolved"

            unresolved.append(
                row
            )

    return {
        "carbon_capability_count":
            len(
                carbon_ids
            ),

        "externally_resolved":
            externally_resolved,

        "unresolved":
            unresolved,
    }


def registry_state() -> dict[str, Any]:
    rows = []

    for relative_path in (
        required_registry_paths
    ):
        path = (
            carbon_root
            / relative_path
        )

        state = "missing"
        identifier = None
        error = None

        if path.is_file():
            try:
                value = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )

                if not isinstance(
                    value,
                    dict,
                ):
                    raise ValueError(
                        "root is not an object"
                    )

                state = "available"
                identifier = value.get(
                    "id"
                )

            except (
                OSError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                state = "invalid"
                error = str(
                    exc
                )

        rows.append(
            {
                "path":
                    relative_path,

                "state":
                    state,

                "id":
                    identifier,

                "error":
                    error,
            }
        )

    return {
        "entries":
            rows,

        "available":
            all(
                value[
                    "state"
                ]
                == "available"
                for value
                in rows
            ),
    }


def capability_invariants(
    surface: Mapping[
        str,
        Any,
    ],
) -> list[dict[str, Any]]:
    violations = []

    for capability in surface.get(
        "capabilities",
        [],
    ):
        if not isinstance(
            capability,
            Mapping,
        ):
            violations.append(
                {
                    "capability":
                        None,

                    "field":
                        "capability",

                    "expected":
                        "object",

                    "actual":
                        type(
                            capability
                        ).__name__,
                }
            )

            continue

        identifier = str(
            capability.get(
                "id",
                "",
            )
        ).strip()

        for field, expected in (
            protected_capability_values.items()
        ):
            actual = str(
                capability.get(
                    field,
                    "",
                )
            ).strip().lower()

            if actual != expected:
                violations.append(
                    {
                        "capability":
                            identifier,

                        "field":
                            field,

                        "expected":
                            expected,

                        "actual":
                            actual,
                    }
                )

    return violations


def provider_state(
    surface: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    unavailable = []
    errored = []
    unready = []
    healthy = []

    for provider in surface.get(
        "providers",
        [],
    ):
        if not isinstance(
            provider,
            Mapping,
        ):
            continue

        module = str(
            provider.get(
                "module",
                "",
            )
        ).strip()

        if not provider.get(
            "imported",
            False,
        ):
            unavailable.append(
                module
            )

            continue

        if (
            provider.get(
                "manifest_state"
            )
            == "error"
            or provider.get(
                "status_state"
            )
            == "error"
        ):
            errored.append(
                module
            )

            continue

        status_value = provider.get(
            "status"
        )

        if (
            isinstance(
                status_value,
                Mapping,
            )
            and status_value.get(
                "ready"
            )
            is False
        ):
            unready.append(
                module
            )

        else:
            healthy.append(
                module
            )

    return {
        "healthy":
            sorted(
                healthy
            ),

        "unready":
            sorted(
                unready
            ),

        "unavailable":
            sorted(
                unavailable
            ),

        "errored":
            sorted(
                errored
            ),
    }


def snapshot() -> dict[str, Any]:
    static_health = load_json(
        "introspection/health.json"
    )

    static_dependencies = load_json(
        "introspection/dependencies.json"
    )

    surface = collect_capabilities()

    registry = registry_state()

    providers = provider_state(
        surface
    )

    dependencies = (
        dependency_resolution(
            surface
        )
    )

    invariant_violations = (
        capability_invariants(
            surface
        )
    )

    blocking_reasons = []
    degraded_reasons = []

    if not registry[
        "available"
    ]:
        blocking_reasons.append(
            (
                "oriel registry integration "
                "is missing or invalid"
            )
        )

    if surface.get(
        "unavailable_modules"
    ):
        blocking_reasons.append(
            (
                "one or more oriel capability "
                "providers are unavailable"
            )
        )

    if surface.get(
        "provider_errors"
    ):
        blocking_reasons.append(
            (
                "one or more oriel capability "
                "providers errored"
            )
        )

    if surface.get(
        "unmanifested_modules"
    ):
        blocking_reasons.append(
            (
                "one or more oriel providers "
                "lack a capability manifest"
            )
        )

    if invariant_violations:
        blocking_reasons.append(
            (
                "protected oriel capability "
                "metadata is invalid"
            )
        )

    if dependencies[
        "unresolved"
    ]:
        degraded_reasons.append(
            (
                "one or more oriel capability "
                "dependencies remain unresolved"
            )
        )

    if providers[
        "unready"
    ]:
        degraded_reasons.append(
            (
                "one or more imported oriel "
                "providers report not ready"
            )
        )

    if blocking_reasons:
        oriel_state = "blocked"
        carbon_effect = "degraded"

    elif degraded_reasons:
        oriel_state = "degraded"
        carbon_effect = "degraded"

    else:
        oriel_state = "healthy"
        carbon_effect = "healthy"

    result = {
        "schema":
            schema,

        "kind":
            "oriel-introspection-snapshot",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "oriel_state":
            oriel_state,

        "carbon_effect":
            carbon_effect,

        "oriel_required_for_generalized_carbon":
            False,

        "blocking_reasons":
            blocking_reasons,

        "degraded_reasons":
            degraded_reasons,

        "registry":
            registry,

        "providers":
            providers,

        "capability_surface_id":
            surface.get(
                "id"
            ),

        "capability_count":
            surface.get(
                "capability_count",
                0,
            ),

        "provider_count":
            surface.get(
                "provider_count",
                0,
            ),

        "unmanifested_modules":
            clone(
                surface.get(
                    "unmanifested_modules",
                    [],
                )
            ),

        "unavailable_modules":
            clone(
                surface.get(
                    "unavailable_modules",
                    [],
                )
            ),

        "provider_errors":
            clone(
                surface.get(
                    "provider_errors",
                    [],
                )
            ),

        "dependency_resolution":
            dependencies,

        "capability_invariant_violations":
            invariant_violations,

        "static_health_projection":
            static_health,

        "static_dependency_projection":
            static_dependencies,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "authority_transfer":
            False,
    }

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
    value = snapshot()

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

        "oriel_state":
            value[
                "oriel_state"
            ],

        "carbon_effect":
            value[
                "carbon_effect"
            ],

        "capability_count":
            value[
                "capability_count"
            ],

        "provider_count":
            value[
                "provider_count"
            ],

        "blocking_reason_count":
            len(
                value[
                    "blocking_reasons"
                ]
            ),

        "degraded_reason_count":
            len(
                value[
                    "degraded_reasons"
                ]
            ),

        "unresolved_dependency_count":
            len(
                value[
                    "dependency_resolution"
                ][
                    "unresolved"
                ]
            ),

        "externally_resolved_dependency_count":
            len(
                value[
                    "dependency_resolution"
                ][
                    "externally_resolved"
                ]
            ),

        "authority_transfer":
            False,

        "ready":
            value[
                "oriel_state"
            ]
            != "blocked",
    }


def selftest() -> dict[str, Any]:
    health = load_json(
        "introspection/health.json"
    )

    dependencies = load_json(
        "introspection/dependencies.json"
    )

    specialization = dependencies.get(
        "specializations",
        [],
    )

    if not any(
        (
            isinstance(
                value,
                Mapping,
            )
            and value.get(
                "id"
            )
            == "oriel"
        )
        for value
        in specialization
    ):
        raise oriel_introspection_error(
            (
                "carbon dependency projection "
                "does not expose oriel"
            )
        )

    required_checks = {
        "specializations_exposed",
        "oriel_specialization_discoverable",
        "oriel_capability_surface_derived",
        "oriel_authority_effect_none",
    }

    if not required_checks.issubset(
        set(
            health.get(
                "checks",
                [],
            )
        )
    ):
        raise oriel_introspection_error(
            (
                "carbon health projection lacks "
                "required oriel checks"
            )
        )

    value = snapshot()

    if (
        value[
            "oriel_state"
        ]
        == "blocked"
    ):
        raise oriel_introspection_error(
            (
                "oriel introspection is blocked: "
                + "; ".join(
                    value[
                        "blocking_reasons"
                    ]
                )
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

        "oriel_state":
            value[
                "oriel_state"
            ],

        "carbon_effect":
            value[
                "carbon_effect"
            ],

        "registry_available":
            value[
                "registry"
            ][
                "available"
            ],

        "capability_count":
            value[
                "capability_count"
            ],

        "provider_count":
            value[
                "provider_count"
            ],

        "protected_capability_metadata_valid":
            not value[
                "capability_invariant_violations"
            ],

        "unresolved_dependency_count":
            len(
                value[
                    "dependency_resolution"
                ][
                    "unresolved"
                ]
            ),

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "snapshot",
    "status",
    "selftest",
]
